"""Formatting utilities.

This module provides formatting functions for currency, percentages, dates, and decimals.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal


def format_currency(value: Decimal, decimals: int = 2, symbol: str = "$") -> str:
    """Format as currency.

    Args:
        value: Decimal value
        decimals: Number of decimal places
        symbol: Currency symbol

    Returns:
        Formatted string like "$1,234.56"
    """
    return f"{symbol}{value:,.{decimals}f}"


def format_percentage(value: Decimal, decimals: int = 2, include_sign: bool = False) -> str:
    """Format as percentage.

    Args:
        value: Decimal value (0.15 for 15%)
        decimals: Decimal places
        include_sign: Include +/- sign

    Returns:
        Formatted string like "15.00%" or "+15.00%"
    """
    pct = value * 100
    if include_sign:
        return f"{pct:+.{decimals}f}%"
    return f"{pct:.{decimals}f}%"


def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime.

    Args:
        dt: Datetime to format
        format: Format string

    Returns:
        Formatted datetime string
    """
    return dt.strftime(format)


def format_decimal(value: Decimal, decimals: int = 4, strip_trailing: bool = True) -> str:
    """Format decimal number.

    Args:
        value: Decimal value
        decimals: Decimal places
        strip_trailing: Remove trailing zeros

    Returns:
        Formatted string
    """
    formatted = f"{value:.{decimals}f}"
    if strip_trailing:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted
