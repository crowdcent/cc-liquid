"""Configuration field update utilities.

This module handles updating configuration field values with
validation and type conversion.

Classes:
    ConfigUpdater: Updates configuration fields safely

Example:
    >>> updater = ConfigUpdater(config, validator)
    >>> updater.update_field("portfolio.num_long", "15")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cc_flow.domain.config import TradingConfig
    from cc_flow.ui.screens.config_validators import FieldValidator


class ConfigUpdater:
    """Configuration field updater.

    Handles updating configuration fields with validation and
    type conversion. Supports nested field paths.

    Attributes:
        config: TradingConfig to update
        validator: FieldValidator for value validation

    Example:
        >>> updater = ConfigUpdater(config, validator)
        >>> result = updater.update_field("portfolio.num_long", "20")
        >>> assert result is True
    """

    def __init__(self, config: TradingConfig, validator: FieldValidator) -> None:
        """Initialize config updater.

        Args:
            config: Trading configuration to update
            validator: Field validator instance
        """
        self.config = config
        self.validator = validator

    def update_field(self, field_path: str, value: str) -> bool:
        """Update a configuration field value.

        Validates the value before updating and converts it to
        the appropriate type.

        Args:
            field_path: Dot-separated path to field (e.g., "portfolio.num_long")
            value: New value as string

        Returns:
            True if update succeeded, False if validation failed

        Example:
            >>> updater.update_field("portfolio.num_long", "15")
            True
            >>> updater.update_field("portfolio.num_long", "invalid")
            False
        """
        parts = field_path.split(".")
        field_name = parts[-1]

        # Validate value
        if not self.validator.validate(field_name, value):
            return False

        # Convert value to appropriate type
        converted_value = self.validator.convert_value(field_name, value)

        # Navigate to the config object and set the value
        obj = self.config
        for part in parts[:-1]:
            obj = getattr(obj, part)

        setattr(obj, field_name, converted_value)
        return True
