"""Utility modules for cc-flow application.

This package contains utility functions for:
- Logging configuration
- Validation (addresses, ranges, dates)
- Formatting (currency, percentages, dates, decimals)
- Financial calculations (leverage, PNL, returns, risk metrics)
"""

from cc_flow.utils.calculations import (
    calculate_leverage,
    calculate_pnl,
    calculate_return,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
)
from cc_flow.utils.formatting import (
    format_currency,
    format_datetime,
    format_decimal,
    format_percentage,
)
from cc_flow.utils.logger_config import configure_logging, log
from cc_flow.utils.validation import (
    validate_date_range,
    validate_decimal_range,
    validate_ethereum_address,
)

__all__ = [
    # Logging
    "configure_logging",
    "log",
    # Validation
    "validate_ethereum_address",
    "validate_decimal_range",
    "validate_date_range",
    # Formatting
    "format_currency",
    "format_percentage",
    "format_datetime",
    "format_decimal",
    # Calculations
    "calculate_leverage",
    "calculate_pnl",
    "calculate_return",
    "calculate_sharpe_ratio",
    "calculate_sortino_ratio",
]
