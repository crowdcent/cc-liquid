"""Configuration management for cc-liquid."""

import os
from dataclasses import dataclass, field, is_dataclass
from typing import Any

import yaml
from dotenv import load_dotenv

DEFAULT_CONFIG_PATH = "cc-liquid-config.yaml"


@dataclass
class DataSourceConfig:
    """Data source configuration."""

    source: str = "crowdcent"  # "crowdcent" or "local"
    path: str = "predictions.parquet"
    date_column: str = "release_date"
    asset_id_column: str = "id"
    prediction_column: str = "pred_30d"


@dataclass
class RebalancingConfig:
    """Rebalancing schedule configuration."""

    every_n_days: int = 10  # How often to rebalance (in days). Ignored in rolling mode.
    at_time: str = "18:15"  # What time to rebalance (UTC)
    mode: str = "rolling"  # "full" (rebalance entire portfolio) or "rolling" (daily vintages)
    rolling_days: int = 30  # Vintage lifespan in days. Match to prediction horizon.
    seed_full: bool = True  # If true, seed with historical predictions on first run


@dataclass
class StopLossConfig:
    """Stop loss protection configuration."""

    sides: str = "none"  # "none", "both", "long_only", "short_only"
    pct: float = 0.17  # 17% from entry price
    slippage: float = 0.05  # Slippage tolerance for limit order


@dataclass
class PortfolioConfig:
    """Portfolio construction parameters."""

    num_long: int = 10
    num_short: int = 10
    target_leverage: float = 1.0  # Position sizing multiplier (1.0 = no leverage)
    rank_power: float = 0.0  # 0.0 = equal weight (default), higher = more concentration
    rebalancing: RebalancingConfig = field(default_factory=RebalancingConfig)
    stop_loss: StopLossConfig = field(default_factory=StopLossConfig)


@dataclass
class ExecutionConfig:
    """Order execution parameters."""

    slippage_tolerance: float = 0.005  # Market orders: aggressive (away from mid)
    limit_price_offset: float = 0.0  # Limit orders: passive offset (0.0 = exact mid, >0 = inside mid)
    min_trade_value: float = 10.0  # Exchange minimum order notional in USD
    order_type: str = "market"  # "market" or "limit"
    time_in_force: str = "Ioc"  # "Ioc" (Immediate or Cancel), "Gtc" (Good til Canceled), "Alo" (Add Liquidity Only)


@dataclass
class Config:
    """
    Manages configuration for the trading bot, loading from a YAML file
    and environment variables.
    """

    # Private Keys and API Credentials (from .env)
    CROWDCENT_API_KEY: str | None = None
    HYPERLIQUID_PRIVATE_KEY: str | None = (
        None  # Private key for signing (owner or approved agent wallet)
    )

    # Environment
    is_testnet: bool = False
    base_url: str = "https://api.hyperliquid.xyz"

    # Profiles (addresses in config; secrets remain in env)
    active_profile: str | None = "default"
    profiles: dict[str, Any] = field(default_factory=dict)

    # Resolved addresses from active profile (owner/vault)
    HYPERLIQUID_ADDRESS: str | None = None
    HYPERLIQUID_VAULT_ADDRESS: str | None = None

    # Nested Configs
    data: DataSourceConfig = field(default_factory=DataSourceConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)

    def __post_init__(self):
        """Load environment variables and YAML config after initialization."""
        self._load_env_vars()
        self._load_yaml_config()
        self._resolve_profile()  # Must come AFTER loading YAML (which loads profiles)
        self._set_base_url()
        self._validate()

    def _load_env_vars(self):
        """Load secrets-only from .env; addresses come from YAML/profiles."""
        load_dotenv()
        self.CROWDCENT_API_KEY = os.getenv("CROWDCENT_API_KEY")
        # Don't load private key here - will be resolved based on profile's signer_env

    def _load_yaml_config(self, config_path: str | None = None):
        """Loads and overrides config from a YAML file."""
        path = config_path or DEFAULT_CONFIG_PATH
        if os.path.exists(path):
            with open(path) as f:
                yaml_config: dict[str, Any] = yaml.safe_load(f) or {}

            for key, value in yaml_config.items():
                if hasattr(self, key):
                    # Handle nested dataclasses
                    if isinstance(value, dict) and is_dataclass(getattr(self, key)):
                        nested_config_obj = getattr(self, key)
                        for nested_key, nested_value in value.items():
                            if hasattr(nested_config_obj, nested_key):
                                # Handle double nested dataclasses
                                if isinstance(nested_value, dict) and is_dataclass(
                                    getattr(nested_config_obj, nested_key)
                                ):
                                    nested_dataclass = getattr(
                                        nested_config_obj, nested_key
                                    )
                                    for deep_key, deep_value in nested_value.items():
                                        if hasattr(nested_dataclass, deep_key):
                                            setattr(
                                                nested_dataclass, deep_key, deep_value
                                            )
                                else:
                                    setattr(nested_config_obj, nested_key, nested_value)
                    else:
                        # Direct assignment for non-dataclass fields (like profiles dict)
                        setattr(self, key, value)

    def _set_base_url(self):
        """Sets the base URL based on the is_testnet flag."""
        if self.is_testnet:
            self.base_url = "https://api.hyperliquid-testnet.xyz"

    def _resolve_profile(self):
        """Resolve owner/vault addresses and signer key from the active profile."""
        # If no profiles defined, skip resolution
        if not self.profiles:
            return

        active = self.active_profile or "default"
        profile = self.profiles.get(active, {})

        # Extract owner and vault from profile
        owner = profile.get("owner")
        vault = profile.get("vault")

        # Set addresses (owner is required, vault is optional)
        self.HYPERLIQUID_ADDRESS = owner
        self.HYPERLIQUID_VAULT_ADDRESS = vault

        # Resolve signer key from environment based on profile's signer_env
        signer_env = profile.get("signer_env", "HYPERLIQUID_PRIVATE_KEY")
        self.HYPERLIQUID_PRIVATE_KEY = os.getenv(signer_env)

        # Fallback to default env var if custom signer_env not found
        if not self.HYPERLIQUID_PRIVATE_KEY and signer_env != "HYPERLIQUID_PRIVATE_KEY":
            self.HYPERLIQUID_PRIVATE_KEY = os.getenv("HYPERLIQUID_PRIVATE_KEY")

    def refresh_runtime(self):
        """Refresh runtime configuration after changes (e.g., CLI overrides)."""
        self._set_base_url()
        self._resolve_profile()
        self._validate()

    def _validate(self):
        """Validate that required configuration is present.

        Note: This is lenient during initial module load to allow CLI commands
        like 'profile list' to work even without complete setup.
        """
        # Check if active profile exists
        if self.profiles and self.active_profile:
            if self.active_profile not in self.profiles:
                available = ", ".join(sorted(self.profiles.keys()))
                raise ValueError(
                    f"Active profile '{self.active_profile}' not found. Available profiles: {available}"
                )

        # Don't validate addresses/keys during module import - let individual commands handle it
        # This allows 'profile list', 'config', etc to work without full setup

    def validate_for_trading(self):
        """Strict validation for trading operations.

        Call this before any trading operations to ensure all required config is present.
        """
        # Validate we have required addresses from profile
        if not self.HYPERLIQUID_ADDRESS and not self.HYPERLIQUID_VAULT_ADDRESS:
            raise ValueError(
                "Profile must specify 'owner' or 'vault' address in cc-liquid-config.yaml"
            )

        # Validate we have a private key
        if not self.HYPERLIQUID_PRIVATE_KEY:
            # Better error message showing which env var is expected
            signer_env = "HYPERLIQUID_PRIVATE_KEY"
            if self.profiles and self.active_profile:
                profile = self.profiles.get(self.active_profile, {})
                signer_env = profile.get("signer_env", "HYPERLIQUID_PRIVATE_KEY")
            raise ValueError(
                f"Private key not found. Set '{signer_env}' in your .env file."
            )

        # Validate order type
        if self.execution.order_type not in ("market", "limit"):
            raise ValueError(
                f"Invalid order_type: {self.execution.order_type}. Must be 'market' or 'limit'"
            )

        # Validate time in force
        if self.execution.time_in_force not in ("Ioc", "Gtc", "Alo"):
            raise ValueError(
                f"Invalid time_in_force: {self.execution.time_in_force}. Must be 'Ioc', 'Gtc', or 'Alo'"
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the config."""
        portfolio_dict = self.portfolio.__dict__.copy()
        # Convert nested dataclasses to dict
        if hasattr(self.portfolio, "rebalancing"):
            portfolio_dict["rebalancing"] = self.portfolio.rebalancing.__dict__
        if hasattr(self.portfolio, "stop_loss"):
            portfolio_dict["stop_loss"] = self.portfolio.stop_loss.__dict__

        # Profile summary (non-secret)
        active_profile = self.active_profile
        prof = self.profiles.get(active_profile) if self.profiles else {}
        signer_env_name = (
            prof.get("signer_env", "HYPERLIQUID_PRIVATE_KEY")
            if prof
            else "HYPERLIQUID_PRIVATE_KEY"
        )
        profile_dict = {
            "active": active_profile,
            "owner": self.HYPERLIQUID_ADDRESS,
            "vault": self.HYPERLIQUID_VAULT_ADDRESS,
            "signer_env": signer_env_name,
        }

        return {
            "is_testnet": self.is_testnet,
            "profile": profile_dict,
            "data": self.data.__dict__,
            "portfolio": portfolio_dict,
            "execution": self.execution.__dict__,
        }


def parse_cli_overrides(set_overrides):
    """Parse --set key=value pairs into a nested dictionary.

    Args:
        set_overrides: List of strings like ["data.source=numerai", "portfolio.num_long=10"]

    Returns:
        Nested dictionary suitable for config override
    """
    overrides = {}

    for override in set_overrides:
        if "=" not in override:
            raise ValueError(f"Invalid --set format: {override}. Use key=value format.")

        key, value = override.split("=", 1)
        key_parts = key.split(".")

        # Navigate/create nested dictionary structure
        current = overrides
        for part in key_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the final value, attempting type conversion
        final_key = key_parts[-1]
        current[final_key] = _convert_value(value)

    return overrides


def _convert_value(value_str):
    """Convert string value to appropriate Python type."""
    # Try int
    try:
        return int(value_str)
    except ValueError:
        pass

    # Try float
    try:
        return float(value_str)
    except ValueError:
        pass

    # Try boolean
    if value_str.lower() in ("true", "false"):
        return value_str.lower() == "true"

    # Return as string
    return value_str


def apply_cli_overrides(config_obj, set_overrides):
    """Apply --set overrides to config using the same logic as YAML loading.

    Returns:
        List of override keys that were actually applied.
    """
    if not set_overrides:
        return []

    try:
        # Parse the overrides into nested dict
        overrides = parse_cli_overrides(set_overrides)
        applied = []

        # Apply smart defaults for data source changes
        _apply_data_source_defaults(overrides, applied)

        # Reuse the same logic as _load_yaml_config for consistency
        for key, value in overrides.items():
            if hasattr(config_obj, key) and isinstance(value, dict):
                nested_config_obj = getattr(config_obj, key)
                if is_dataclass(nested_config_obj):
                    for nested_key, nested_value in value.items():
                        if hasattr(nested_config_obj, nested_key):
                            # Handle double nested dataclasses (if any exist in future)
                            if isinstance(nested_value, dict) and is_dataclass(
                                getattr(nested_config_obj, nested_key)
                            ):
                                nested_dataclass = getattr(
                                    nested_config_obj, nested_key
                                )
                                for deep_key, deep_value in nested_value.items():
                                    if hasattr(nested_dataclass, deep_key):
                                        setattr(nested_dataclass, deep_key, deep_value)
                                        applied.append(
                                            f"{key}.{nested_key}.{deep_key}={deep_value}"
                                        )
                            else:
                                setattr(nested_config_obj, nested_key, nested_value)
                                applied.append(f"{key}.{nested_key}={nested_value}")
            elif hasattr(config_obj, key):
                setattr(config_obj, key, value)
                applied.append(f"{key}={value}")

        # Refresh runtime configuration after overrides
        config_obj.refresh_runtime()

        return applied

    except Exception as e:
        raise ValueError(f"Error applying overrides: {e}")


def _apply_data_source_defaults(overrides, applied):
    """Apply smart defaults when data source is changed.

    When switching to numerai, automatically apply numerai column defaults
    unless explicitly overridden.
    """
    # Check if data.source is being changed
    data_section = overrides.get("data", {})
    if "source" not in data_section:
        return

    source = data_section["source"]

    # Define defaults for each data source
    source_defaults = {
        "numerai": {
            "date_column": "date",
            "asset_id_column": "symbol",
            "prediction_column": "prediction",
        },
        "crowdcent": {
            "date_column": "release_date",
            "asset_id_column": "id",
        },
        # local doesn't need defaults - user provides their own columns
    }

    if source in source_defaults:
        defaults = source_defaults[source]

        # Ensure data section exists
        if "data" not in overrides:
            overrides["data"] = {}

        # Apply defaults only if not explicitly set
        for key, default_value in defaults.items():
            if key not in overrides["data"]:
                overrides["data"][key] = default_value
                applied.append(
                    f"data.{key}={default_value} (auto-applied for {source})"
                )


config = Config()
