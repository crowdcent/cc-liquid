"""Configuration domain models for trading system.

This module defines all configuration models for the cc-flow trading system,
including data sources, portfolio settings, execution parameters, and exchange profiles.

All models use Pydantic v2 for validation and type safety. Models are mutable
(frozen=False) to allow runtime configuration updates.

Models:
    DataSourceConfig: Configuration for prediction data sources
    StopLossConfig: Stop loss parameters for risk management
    RebalancingConfig: Rebalancing schedule configuration
    PortfolioConfig: Portfolio construction parameters
    ExecutionConfig: Order execution settings
    ExchangeProfile: Exchange account profile with credentials
    TradingConfig: Complete trading configuration with all components

Example:
    >>> profile = ExchangeProfile(
    ...     name="mainnet",
    ...     exchange="hyperliquid",
    ...     owner_address="0x123..."
    ... )
    >>> config = TradingConfig(
    ...     active_profile="mainnet",
    ...     profiles={"mainnet": profile}
    ... )
    >>> print(config.owner_address)
    0x123...
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .orders import OrderType, TimeInForce


class DataSourceConfig(BaseModel):
    """Data source configuration for predictions.

    Configures where to fetch trading predictions from and how to map
    the data columns to expected fields.

    Attributes:
        source: Data source type (crowdcent, numerai, local, or custom)
        path: Path to prediction file for local/custom sources
        crowdcent_challenge: Challenge name for CrowdCent API
        date_column: Column name for dates in prediction data
        asset_id_column: Column name for asset identifiers
        prediction_column: Column name for prediction values

    Example:
        >>> config = DataSourceConfig(
        ...     source="crowdcent",
        ...     crowdcent_challenge="hyperliquid-ranking"
        ... )
        >>> assert config.source == "crowdcent"
    """

    model_config = ConfigDict(frozen=False)

    source: Literal["crowdcent", "numerai", "local", "custom"] = "local"
    path: str | None = "predictions.parquet"

    # CrowdCent config
    crowdcent_challenge: str = "hyperliquid-ranking"

    # Column mappings
    date_column: str = "date"
    asset_id_column: str = "asset_id"
    prediction_column: str = "prediction"


class StopLossConfig(BaseModel):
    """Stop loss configuration for risk management.

    Defines stop loss parameters including which sides to apply stops to
    and the percentage loss threshold.

    Attributes:
        sides: Which position sides to apply stops to
        pct: Stop loss percentage from entry (0.17 = 17%)
        slippage: Slippage tolerance for stop orders (0.05 = 5%)

    Example:
        >>> config = StopLossConfig(sides="both", pct=Decimal("0.20"))
        >>> assert config.pct == Decimal("0.20")
    """

    model_config = ConfigDict(frozen=False)

    sides: Literal["none", "both", "long_only", "short_only"] = "none"
    pct: Decimal = Decimal("0.17")  # 17% from entry
    slippage: Decimal = Decimal("0.05")  # 5% slippage tolerance


class RebalancingConfig(BaseModel):
    """Rebalancing schedule configuration.

    Defines when and how often to rebalance the portfolio.

    Attributes:
        every_n_days: Rebalance frequency in days
        at_time: Time of day to rebalance (UTC, HH:MM format)

    Example:
        >>> config = RebalancingConfig(every_n_days=7, at_time="12:00")
        >>> assert config.every_n_days == 7
    """

    model_config = ConfigDict(frozen=False)

    every_n_days: int = 10
    at_time: str = "18:15"  # UTC HH:MM


class PortfolioConfig(BaseModel):
    """Portfolio construction configuration.

    Defines how to construct the portfolio from predictions, including
    position counts, leverage, weighting schemes, and risk management.

    Attributes:
        num_long: Number of long positions to hold
        num_short: Number of short positions to hold
        target_leverage: Target portfolio leverage (1.0 = 100%)
        rank_power: Power for rank-weighted scheme (0.0 = equal weight)
        stop_loss: Stop loss configuration
        rebalancing: Rebalancing schedule configuration

    Example:
        >>> config = PortfolioConfig(
        ...     num_long=15,
        ...     num_short=5,
        ...     target_leverage=Decimal("2.0")
        ... )
        >>> assert config.num_long == 15
    """

    model_config = ConfigDict(frozen=False)

    num_long: int = 10
    num_short: int = 10
    target_leverage: Decimal = Decimal("1.0")
    rank_power: Decimal = Decimal("0.0")

    stop_loss: StopLossConfig = Field(default_factory=StopLossConfig)
    rebalancing: RebalancingConfig = Field(default_factory=RebalancingConfig)


class ExecutionConfig(BaseModel):
    """Order execution configuration.

    Defines parameters for order execution including order types,
    slippage tolerance, and minimum trade sizes.

    Attributes:
        slippage_tolerance: Maximum acceptable slippage (0.005 = 0.5%)
        limit_price_offset: Price offset for limit orders (0.0 = market price)
        min_trade_value: Minimum trade value in USD
        order_type: Order type (MARKET or LIMIT)
        time_in_force: Order time in force (IOC, GTC, or ALO)

    Example:
        >>> config = ExecutionConfig(
        ...     order_type=OrderType.LIMIT,
        ...     time_in_force=TimeInForce.GTC
        ... )
        >>> assert config.order_type == OrderType.LIMIT
    """

    model_config = ConfigDict(frozen=False)

    slippage_tolerance: Decimal = Decimal("0.005")
    limit_price_offset: Decimal = Decimal("0.0")
    min_trade_value: Decimal = Decimal("10.0")
    order_type: OrderType = OrderType.MARKET
    time_in_force: TimeInForce = TimeInForce.IOC


class ExchangeProfile(BaseModel):
    """Exchange account profile with credentials.

    Represents a trading account on a specific exchange with all
    necessary credentials and configuration.

    Attributes:
        name: Profile name identifier
        exchange: Exchange name (e.g., "hyperliquid", "binance")
        owner_address: Account owner address
        vault_address: Optional vault address for managed accounts
        signer_env: Environment variable name for private key
        is_testnet: Whether this is a testnet account

    Example:
        >>> profile = ExchangeProfile(
        ...     name="mainnet",
        ...     exchange="hyperliquid",
        ...     owner_address="0x1234567890abcdef"
        ... )
        >>> assert profile.is_testnet is False
    """

    model_config = ConfigDict(frozen=False)

    name: str
    exchange: str  # "hyperliquid", "binance", etc.
    owner_address: str
    vault_address: str | None = None
    signer_env: str = "HYPERLIQUID_PRIVATE_KEY"
    is_testnet: bool = False


class TradingConfig(BaseModel):
    """Complete trading configuration.

    Top-level configuration model that combines all configuration
    components including profiles, data sources, portfolio settings,
    and execution parameters.

    Attributes:
        active_profile: Name of the currently active profile
        profiles: Dictionary of available exchange profiles
        data_source: Data source configuration
        portfolio: Portfolio construction configuration
        execution: Order execution configuration

    Properties:
        current_profile: Get the active ExchangeProfile
        owner_address: Get owner address from active profile
        exchange_name: Get exchange name from active profile

    Raises:
        ValueError: If active_profile is not found in profiles

    Example:
        >>> profile = ExchangeProfile(
        ...     name="default",
        ...     exchange="hyperliquid",
        ...     owner_address="0x123..."
        ... )
        >>> config = TradingConfig(
        ...     active_profile="default",
        ...     profiles={"default": profile}
        ... )
        >>> assert config.owner_address == "0x123..."
    """

    model_config = ConfigDict(frozen=False)

    # Active profile
    active_profile: str = "default"
    profiles: dict[str, ExchangeProfile] = Field(default_factory=dict)

    # Components
    data_source: DataSourceConfig = Field(default_factory=DataSourceConfig)
    portfolio: PortfolioConfig = Field(default_factory=PortfolioConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)

    @property
    def current_profile(self) -> ExchangeProfile:
        """Get active exchange profile.

        Returns:
            The ExchangeProfile corresponding to active_profile

        Raises:
            ValueError: If active_profile not found in profiles
        """
        if self.active_profile not in self.profiles:
            raise ValueError(f"Profile '{self.active_profile}' not found")
        return self.profiles[self.active_profile]

    @property
    def owner_address(self) -> str:
        """Get owner address from active profile.

        Returns:
            Owner address string from the current profile

        Raises:
            ValueError: If active_profile not found in profiles
        """
        return self.current_profile.owner_address

    @property
    def exchange_name(self) -> str:
        """Get exchange name from active profile.

        Returns:
            Exchange name string from the current profile

        Raises:
            ValueError: If active_profile not found in profiles
        """
        return self.current_profile.exchange
