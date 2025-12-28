"""Validation utilities for configuration fields.

This module provides field-level validation for configuration values,
ensuring type safety and business rule compliance.

Classes:
    FieldValidator: Validates configuration field values

Example:
    >>> validator = FieldValidator()
    >>> validator.validate("num_long", "10")
    True
    >>> validator.validate("num_long", "invalid")
    False
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


class FieldValidator:
    """Configuration field validator.

    Provides validation for different types of configuration fields
    including integers, decimals, strings, and enum choices.

    Validation Rules:
        - Integer fields: Must be non-negative integers
        - Decimal fields: Must be valid decimal numbers
        - Choice fields: Must match predefined valid values
        - String fields: Non-empty strings

    Example:
        >>> validator = FieldValidator()
        >>> validator.validate("num_long", "15")
        True
        >>> validator.validate("source", "crowdcent")
        True
    """

    # Define field validation rules
    INTEGER_FIELDS = {
        "num_long",
        "num_short",
        "every_n_days",
    }

    DECIMAL_FIELDS = {
        "target_leverage",
        "rank_power",
        "pct",
        "slippage",
        "slippage_tolerance",
        "limit_price_offset",
        "min_trade_value",
    }

    CHOICE_FIELDS = {
        "source": ["crowdcent", "numerai", "local", "custom"],
        "order_type": ["market", "limit"],
        "time_in_force": ["Ioc", "Gtc", "Alo"],
        "sides": ["none", "both", "long_only", "short_only"],
    }

    def validate(self, field_name: str, value: str) -> bool:
        """Validate a field value.

        Args:
            field_name: Name of the configuration field
            value: String value to validate

        Returns:
            True if value is valid for the field, False otherwise

        Example:
            >>> validator = FieldValidator()
            >>> validator.validate("num_long", "10")
            True
        """
        if field_name in self.INTEGER_FIELDS:
            return self._validate_integer(value)
        elif field_name in self.DECIMAL_FIELDS:
            return self._validate_decimal(value)
        elif field_name in self.CHOICE_FIELDS:
            return self._validate_choice(field_name, value)
        else:
            # String fields - just check non-empty
            return self._validate_string(value)

    def _validate_integer(self, value: str) -> bool:
        """Validate integer field.

        Args:
            value: String value to validate

        Returns:
            True if value is a non-negative integer
        """
        try:
            int_value = int(value)
            return int_value >= 0
        except (ValueError, TypeError):
            return False

    def _validate_decimal(self, value: str) -> bool:
        """Validate decimal field.

        Args:
            value: String value to validate

        Returns:
            True if value is a valid decimal number
        """
        try:
            Decimal(value)
            return True
        except (InvalidOperation, ValueError, TypeError):
            return False

    def _validate_choice(self, field_name: str, value: str) -> bool:
        """Validate choice field against allowed values.

        Args:
            field_name: Name of the choice field
            value: String value to validate

        Returns:
            True if value is in allowed choices
        """
        allowed_values = self.CHOICE_FIELDS.get(field_name, [])
        return value in allowed_values

    def _validate_string(self, value: str) -> bool:
        """Validate string field.

        Args:
            value: String value to validate

        Returns:
            True if value is a non-empty string
        """
        return bool(value and value.strip())

    def convert_value(self, field_name: str, value: str) -> Any:
        """Convert validated string value to appropriate type.

        Args:
            field_name: Name of the configuration field
            value: Validated string value

        Returns:
            Converted value in appropriate type

        Raises:
            ValueError: If value cannot be converted

        Example:
            >>> validator = FieldValidator()
            >>> validator.convert_value("num_long", "15")
            15
            >>> validator.convert_value("target_leverage", "2.5")
            Decimal('2.5')
        """
        if field_name in self.INTEGER_FIELDS:
            return int(value)
        elif field_name in self.DECIMAL_FIELDS:
            return Decimal(value)
        else:
            return value
