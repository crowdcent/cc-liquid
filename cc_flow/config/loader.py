"""Configuration loader for trading system.

This module provides the ConfigLoader class which loads configuration from
YAML files and .env files, with support for CLI overrides.

The loader handles:
- Loading YAML configuration files
- Loading environment variables from .env files
- Validating that required secrets exist
- Applying CLI overrides to configuration values
- Type conversion for override values

Example:
    >>> loader = ConfigLoader("cc-liquid-config.yaml", ".env")
    >>> config = loader.load_config()
    >>> overrides = {"portfolio.num_long": "15"}
    >>> updated_config = loader.apply_overrides(config, overrides)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from cc_flow.domain.config import TradingConfig


class ConfigLoader:
    """Loads configuration from YAML and .env files.

    This class provides functionality to load trading configuration from
    YAML files, load secrets from .env files, validate required secrets,
    and apply CLI overrides to configuration values.

    Attributes:
        config_path: Path to YAML configuration file
        env_path: Path to .env file for secrets

    Example:
        >>> loader = ConfigLoader()
        >>> config = loader.load_config()
        >>> print(config.active_profile)
        default
    """

    def __init__(self, config_path: str = "cc-liquid-config.yaml", env_path: str = ".env"):
        """Initialize config loader.

        Args:
            config_path: Path to YAML config file
            env_path: Path to .env file
        """
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)

    def load_config(self) -> TradingConfig:
        """Load complete configuration.

        Loads configuration from YAML file and .env file, validates that
        required secrets exist, and returns a validated TradingConfig object.

        Returns:
            TradingConfig object with all configuration loaded

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config invalid or required secrets missing
        """
        # Load environment variables
        self._load_env()

        # Load YAML config
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path) as f:
            config_dict = yaml.safe_load(f)

        # Parse into Pydantic model
        config = TradingConfig(**config_dict)

        # Validate secrets exist
        self._validate_secrets(config)

        return config

    def _load_env(self) -> None:
        """Load .env file if exists.

        Loads environment variables from the .env file. If the file
        doesn't exist, this method silently continues (env file is optional).
        """
        if self.env_path.exists():
            load_dotenv(self.env_path)

    def _validate_secrets(self, config: TradingConfig) -> None:
        """Validate required secrets exist in environment.

        Checks that the private key for the active profile exists in
        environment variables.

        Args:
            config: Trading configuration

        Raises:
            ValueError: If required secrets missing or active profile not found
        """
        # Check active profile's signer key
        try:
            profile = config.current_profile
            private_key = os.getenv(profile.signer_env)

            if not private_key:
                raise ValueError(
                    f"Private key not found. Set {profile.signer_env} in .env file.\n"
                    f"Example: {profile.signer_env}=0x..."
                )
        except ValueError as e:
            # Re-raise if it's our error
            if "Private key" in str(e):
                raise
            # Otherwise it's profile not found error
            raise ValueError(
                f"Active profile '{config.active_profile}' not found in config.\n"
                f"Available profiles: {', '.join(config.profiles.keys())}"
            ) from None

    def apply_overrides(self, config: TradingConfig, overrides: dict[str, str]) -> TradingConfig:
        """Apply CLI overrides to configuration.

        Takes a base configuration and applies overrides specified as
        dotted paths. Values are converted to appropriate types based
        on the existing config values.

        Args:
            config: Base configuration
            overrides: Dict of dotted paths to values
                      (e.g., {"portfolio.num_long": "15"})

        Returns:
            Updated configuration with overrides applied

        Raises:
            ValueError: If override path is invalid

        Example:
            >>> overrides = {
            ...     "portfolio.num_long": "15",
            ...     "execution.min_trade_value": "20.0"
            ... }
            >>> updated = loader.apply_overrides(config, overrides)
        """
        config_dict = config.model_dump()

        for path, value in overrides.items():
            self._set_nested_value(config_dict, path, value)

        # Re-validate with Pydantic
        return TradingConfig(**config_dict)

    def _set_nested_value(self, d: dict[str, Any], path: str, value: str) -> None:
        """Set nested dictionary value from dotted path.

        Navigates the nested dictionary structure using the dotted path
        and sets the final value, converting it to the appropriate type.

        Args:
            d: Dictionary to modify (modified in-place)
            path: Dotted path (e.g., "portfolio.num_long")
            value: String value to set (will be converted to proper type)

        Raises:
            ValueError: If path is invalid
        """
        keys = path.split(".")
        current = d

        for key in keys[:-1]:
            if key not in current:
                raise ValueError(f"Invalid config path: {path}")
            current = current[key]

        final_key = keys[-1]
        if final_key not in current:
            raise ValueError(f"Invalid config path: {path}")

        # Convert value to appropriate type
        current[final_key] = self._convert_value(value, type(current[final_key]))

    def _convert_value(self, value: str, target_type: type) -> Any:
        """Convert string value to target type.

        Handles conversion of string values to various Python types including
        bool, int, float, and str. For bool, accepts various common
        representations like "true", "1", "yes".

        Args:
            value: String value to convert
            target_type: Target Python type

        Returns:
            Converted value of the target type

        Example:
            >>> loader._convert_value("15", int)
            15
            >>> loader._convert_value("true", bool)
            True
            >>> loader._convert_value("2.5", float)
            2.5
        """
        if target_type is bool:
            return value.lower() in ("true", "1", "yes")
        elif target_type is int:
            return int(value)
        elif target_type is float:
            return float(value)
        else:
            return value
