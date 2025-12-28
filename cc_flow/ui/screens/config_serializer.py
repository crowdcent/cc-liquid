"""YAML serialization utilities for configuration.

This module handles conversion of Pydantic configuration models to
YAML-compatible dictionaries and file writing.

Classes:
    ConfigSerializer: Serializes TradingConfig to YAML files

Example:
    >>> serializer = ConfigSerializer()
    >>> serializer.save(config, "config.yaml")
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from cc_flow.domain.config import TradingConfig


class ConfigSerializer:
    """Configuration YAML serializer.

    Handles conversion of TradingConfig Pydantic models to YAML-compatible
    dictionaries and writing to files.

    Features:
        - Converts Pydantic models to dicts
        - Handles Decimal and Enum types
        - Preserves nested structure
        - Writes formatted YAML files

    Example:
        >>> serializer = ConfigSerializer()
        >>> serializer.save(config, "config.yaml")
    """

    def save(self, config: TradingConfig, file_path: str | Path) -> None:
        """Save configuration to YAML file.

        Args:
            config: TradingConfig to serialize
            file_path: Path to output YAML file

        Raises:
            IOError: If file write fails
            ValueError: If config cannot be serialized
        """
        from cc_flow.utils.logger_config import log

        try:
            # Convert config to dict
            config_dict = self._to_dict(config)

            # Write to file
            path = Path(file_path)
            with open(path, "w") as f:
                yaml.safe_dump(
                    config_dict, f, default_flow_style=False, sort_keys=False
                )

            log.info(f"Configuration saved to {file_path}")

        except Exception as e:
            log.error(f"Failed to save configuration: {e}")
            raise

    def _to_dict(self, config: TradingConfig) -> dict[str, Any]:
        """Convert TradingConfig to dictionary.

        Args:
            config: TradingConfig to convert

        Returns:
            Dictionary representation suitable for YAML serialization
        """
        return {
            "active_profile": config.active_profile,
            "profiles": self._serialize_profiles(config),
            "data_source": self._serialize_data_source(config),
            "portfolio": self._serialize_portfolio(config),
            "execution": self._serialize_execution(config),
        }

    def _serialize_profiles(self, config: TradingConfig) -> dict[str, Any]:
        """Serialize exchange profiles.

        Args:
            config: TradingConfig containing profiles

        Returns:
            Dictionary of profile configurations
        """
        return {
            name: {
                "owner": profile.owner_address,
                "vault": profile.vault_address,
                "signer_env": profile.signer_env,
            }
            for name, profile in config.profiles.items()
        }

    def _serialize_data_source(self, config: TradingConfig) -> dict[str, Any]:
        """Serialize data source configuration.

        Args:
            config: TradingConfig containing data source

        Returns:
            Dictionary of data source settings
        """
        return {
            "source": config.data_source.source,
            "path": config.data_source.path,
            "crowdcent_challenge": config.data_source.crowdcent_challenge,
            "date_column": config.data_source.date_column,
            "asset_id_column": config.data_source.asset_id_column,
            "prediction_column": config.data_source.prediction_column,
        }

    def _serialize_portfolio(self, config: TradingConfig) -> dict[str, Any]:
        """Serialize portfolio configuration.

        Args:
            config: TradingConfig containing portfolio settings

        Returns:
            Dictionary of portfolio settings
        """
        portfolio = config.portfolio
        return {
            "num_long": portfolio.num_long,
            "num_short": portfolio.num_short,
            "target_leverage": float(portfolio.target_leverage),
            "rank_power": float(portfolio.rank_power),
            "rebalancing": {
                "every_n_days": portfolio.rebalancing.every_n_days,
                "at_time": portfolio.rebalancing.at_time,
            },
            "stop_loss": {
                "sides": portfolio.stop_loss.sides,
                "pct": float(portfolio.stop_loss.pct),
                "slippage": float(portfolio.stop_loss.slippage),
            },
        }

    def _serialize_execution(self, config: TradingConfig) -> dict[str, Any]:
        """Serialize execution configuration.

        Args:
            config: TradingConfig containing execution settings

        Returns:
            Dictionary of execution settings
        """
        execution = config.execution
        return {
            "slippage_tolerance": float(execution.slippage_tolerance),
            "limit_price_offset": float(execution.limit_price_offset),
            "min_trade_value": float(execution.min_trade_value),
            "order_type": execution.order_type.value,
            "time_in_force": execution.time_in_force.value,
        }
