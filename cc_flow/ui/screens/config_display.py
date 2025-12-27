"""Display formatters for configuration screen.

This module provides utilities for extracting and formatting
configuration data for display in the TUI.

Classes:
    ConfigDisplayHelper: Extracts and formats config sections

Example:
    >>> helper = ConfigDisplayHelper(config)
    >>> profile_info = helper.get_profile_info()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cc_flow.domain.config import TradingConfig


class ConfigDisplayHelper:
    """Configuration display helper.

    Extracts configuration sections and formats them for display
    in the TUI with proper type conversions and formatting.

    Attributes:
        config: TradingConfig to display

    Example:
        >>> helper = ConfigDisplayHelper(config)
        >>> data = helper.get_portfolio_info()
        >>> formatted = helper.format_section("Portfolio", data)
    """

    def __init__(self, config: TradingConfig) -> None:
        """Initialize display helper.

        Args:
            config: Trading configuration to display
        """
        self.config = config

    def get_profile_info(self) -> dict[str, str | bool]:
        """Extract profile information for display.

        Returns:
            Dictionary with profile fields
        """
        profile = self.config.current_profile
        return {
            "name": profile.name,
            "exchange": profile.exchange,
            "owner_address": profile.owner_address,
            "vault_address": profile.vault_address or "None",
            "is_testnet": profile.is_testnet,
        }

    def get_data_source_info(self) -> dict[str, str]:
        """Extract data source configuration for display.

        Returns:
            Dictionary with data source fields
        """
        data = self.config.data_source
        info: dict[str, str] = {
            "source": data.source,
            "path": data.path or "None",
            "date_column": data.date_column,
            "asset_id_column": data.asset_id_column,
            "prediction_column": data.prediction_column,
        }
        if data.source == "crowdcent":
            info["crowdcent_challenge"] = data.crowdcent_challenge
        return info

    def get_portfolio_info(self) -> dict[str, str | int | float]:
        """Extract portfolio configuration for display.

        Returns:
            Dictionary with portfolio fields
        """
        portfolio = self.config.portfolio
        return {
            "num_long": portfolio.num_long,
            "num_short": portfolio.num_short,
            "target_leverage": float(portfolio.target_leverage),
            "rank_power": float(portfolio.rank_power),
            "weighting": "equal" if portfolio.rank_power == 0 else "rank-weighted",
        }

    def get_execution_info(self) -> dict[str, str | float]:
        """Extract execution configuration for display.

        Returns:
            Dictionary with execution fields
        """
        execution = self.config.execution
        return {
            "order_type": execution.order_type.value,
            "time_in_force": execution.time_in_force.value,
            "slippage_tolerance": float(execution.slippage_tolerance),
            "min_trade_value": float(execution.min_trade_value),
            "limit_price_offset": float(execution.limit_price_offset),
        }

    def get_rebalancing_info(self) -> dict[str, str | int]:
        """Extract rebalancing configuration for display.

        Returns:
            Dictionary with rebalancing fields
        """
        rebalancing = self.config.portfolio.rebalancing
        return {
            "every_n_days": rebalancing.every_n_days,
            "at_time": rebalancing.at_time,
        }

    def get_stop_loss_info(self) -> dict[str, str | float]:
        """Extract stop loss configuration for display.

        Returns:
            Dictionary with stop loss fields
        """
        stop_loss = self.config.portfolio.stop_loss
        return {
            "sides": stop_loss.sides,
            "pct": float(stop_loss.pct),
            "slippage": float(stop_loss.slippage),
        }

    @staticmethod
    def format_section(title: str, data: dict) -> str:
        """Format configuration section for display.

        Args:
            title: Section title
            data: Configuration data as key-value pairs

        Returns:
            Formatted string with title and key-value pairs
        """
        lines = [f"[bold cyan]{title}[/bold cyan]", ""]
        for key, value in data.items():
            label = key.replace("_", " ").title()
            lines.append(f"  {label}: {value}")
        return "\n".join(lines)
