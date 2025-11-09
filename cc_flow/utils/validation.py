"""Validation utilities.

This module provides validation functions for addresses, ranges, and dates.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal


def validate_ethereum_address(address: str) -> bool:
    """Validate Ethereum address format.

    Args:
        address: Ethereum address to validate

    Returns:
        True if valid format

    Raises:
        ValueError: If invalid format
    """
    if not address.startswith("0x"):
        raise ValueError(f"Address must start with 0x: {address}")

    if len(address) != 42:
        raise ValueError(f"Address must be 42 characters: {address}")

    if not re.match(r"^0x[0-9a-fA-F]{40}$", address):
        raise ValueError(f"Invalid hex characters in address: {address}")

    return True


def validate_decimal_range(
    value: Decimal,
    min_value: Decimal | None = None,
    max_value: Decimal | None = None,
    name: str = "value"
) -> bool:
    """Validate decimal is within range.

    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        name: Name for error messages

    Returns:
        True if valid

    Raises:
        ValueError: If out of range
    """
    if min_value is not None and value < min_value:
        raise ValueError(f"{name} must be >= {min_value}, got {value}")

    if max_value is not None and value > max_value:
        raise ValueError(f"{name} must be <= {max_value}, got {value}")

    return True


def validate_date_range(
    date: str,
    start_date: str | None = None,
    end_date: str | None = None,
    date_format: str = "%Y-%m-%d"
) -> bool:
    """Validate date is within range.

    Args:
        date: Date string to validate
        start_date: Minimum date (inclusive)
        end_date: Maximum date (inclusive)
        date_format: Date format string

    Returns:
        True if valid

    Raises:
        ValueError: If invalid date or out of range
    """
    try:
        dt = datetime.strptime(date, date_format)
    except ValueError as e:
        raise ValueError(f"Invalid date format: {date}") from e

    if start_date:
        start_dt = datetime.strptime(start_date, date_format)
        if dt < start_dt:
            raise ValueError(f"Date {date} is before start date {start_date}")

    if end_date:
        end_dt = datetime.strptime(end_date, date_format)
        if dt > end_dt:
            raise ValueError(f"Date {date} is after end date {end_date}")

    return True
