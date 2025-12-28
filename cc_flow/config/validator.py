"""Configuration validator for trading system.

This module provides validation logic for trading configurations,
ensuring all settings are valid and identifying potential issues.

The validator performs both hard validation (raises errors) and soft validation
(returns warnings) to help users configure the system safely.

Example:
    >>> from cc_flow.config.validator import ConfigValidator
    >>> from cc_flow.config.defaults import get_default_config
    >>> validator = ConfigValidator()
    >>> config = get_default_config()
    >>> warnings = validator.validate(config)
    >>> if warnings:
    ...     for warning in warnings:
    ...         print(f"Warning: {warning}")
"""

from __future__ import annotations

import re
from decimal import Decimal

from cc_flow.domain.config import TradingConfig
from cc_flow.utils.logger_config import log


class ConfigValidator:
    """Validates trading configuration.

    This class performs comprehensive validation of TradingConfig instances,
    checking for common misconfigurations and potential issues.

    Validation is split into two categories:
    - Errors: Invalid configurations that will raise ValueError
    - Warnings: Potentially risky configurations that return warning messages

    Example:
        >>> validator = ConfigValidator()
        >>> config = get_default_config()
        >>> warnings = validator.validate(config)
        >>> # If no warnings, config is good to go
        >>> assert warnings == []
    """

    def validate(self, config: TradingConfig) -> list[str]:
        """Validate configuration and return list of warnings.

        Performs comprehensive validation of the trading configuration,
        checking profiles, leverage, positions, and schedules.

        Args:
            config: Configuration to validate

        Returns:
            List of warning messages (empty if all good)

        Raises:
            ValueError: If configuration is invalid
        """
        warnings: list[str] = []

        # Validate profile exists
        self._validate_profile(config)

        # Validate leverage limits
        warnings.extend(self._validate_leverage(config))

        # Validate position counts
        self._validate_positions(config)

        # Validate account size vs min trade value
        warnings.extend(self._validate_min_trade_value(config))

        # Validate rank_power
        self._validate_rank_power(config)

        # Validate rebalancing schedule
        self._validate_rebalancing(config)

        # Log all warnings
        for warning in warnings:
            log.warning(warning)

        return warnings

    def _validate_profile(self, config: TradingConfig) -> None:
        """Validate that the active profile exists.

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If active profile not found
        """
        if config.active_profile not in config.profiles:
            available = ", ".join(sorted(config.profiles.keys()))
            raise ValueError(
                f"Profile '{config.active_profile}' not found.\n"
                f"Available profiles: {available}"
            )

    def _validate_leverage(self, config: TradingConfig) -> list[str]:
        """Validate leverage settings.

        Args:
            config: Configuration to validate

        Returns:
            List of warning messages

        Raises:
            ValueError: If leverage is invalid
        """
        warnings: list[str] = []

        if config.portfolio.target_leverage <= Decimal("0"):
            raise ValueError("target_leverage must be > 0")

        if config.portfolio.target_leverage > Decimal("10"):
            warnings.append(
                f"High leverage detected: {config.portfolio.target_leverage}x. "
                f"Risk of liquidation is very high!"
            )

        return warnings

    def _validate_positions(self, config: TradingConfig) -> None:
        """Validate position counts.

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If position counts are invalid
        """
        total_positions = config.portfolio.num_long + config.portfolio.num_short

        if total_positions == 0:
            raise ValueError("num_long + num_short must be > 0")

    def _validate_min_trade_value(self, config: TradingConfig) -> list[str]:
        """Validate minimum trade value against position count.

        Args:
            config: Configuration to validate

        Returns:
            List of warning messages
        """
        warnings: list[str] = []

        total_positions = config.portfolio.num_long + config.portfolio.num_short
        min_total_value = config.execution.min_trade_value * Decimal(str(total_positions))

        # Arbitrary threshold - if minimum total value is very high,
        # warn that account might not have enough capital
        if min_total_value > Decimal("10000"):
            warnings.append(
                f"Minimum total position value (${min_total_value}) is quite high. "
                f"Ensure account value is sufficient."
            )

        return warnings

    def _validate_rank_power(self, config: TradingConfig) -> None:
        """Validate rank power setting.

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If rank_power is invalid
        """
        if config.portfolio.rank_power < Decimal("0"):
            raise ValueError("rank_power must be >= 0")

    def _validate_rebalancing(self, config: TradingConfig) -> None:
        """Validate rebalancing schedule.

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If rebalancing schedule is invalid
        """
        # Validate frequency
        if config.portfolio.rebalancing.every_n_days <= 0:
            raise ValueError("every_n_days must be > 0")

        # Validate time format (HH:MM)
        time_pattern = r"^\d{2}:\d{2}$"
        if not re.match(time_pattern, config.portfolio.rebalancing.at_time):
            raise ValueError(
                f"Invalid time format: {config.portfolio.rebalancing.at_time}. "
                f"Expected HH:MM"
            )
