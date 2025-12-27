"""Formatting utilities for TradePlanWidget.

This module provides formatting functions for displaying trade plan data
with consistent styling and proper precision.

Functions:
    - format_currency: Format decimal as currency
    - format_net_exposure: Format net exposure with color coding
    - format_size: Format trade size with appropriate precision
    - format_trade_type: Format trade type for display
    - style_side: Apply color styling to order side
    - get_portfolio_bias_label: Determine portfolio bias label
    - determine_skip_reason: Determine why a trade was skipped

Design:
    - Pure functions for easy testing
    - No dependencies on widget state
    - Consistent with brutalist color scheme
"""

from __future__ import annotations

from decimal import Decimal

from cc_flow.domain.orders import OrderSide, Trade

# Trading thresholds
MIN_NOTIONAL_VALUE = Decimal("10.00")  # Minimum trade value


def format_currency(value: Decimal) -> str:
    """Format decimal as currency with $ and commas.

    Args:
        value: Decimal value to format

    Returns:
        Formatted string like "$1,234.56"

    Example:
        >>> format_currency(Decimal("1234.56"))
        '$1,234.56'
    """
    return f"${value:,.2f}"


def format_net_exposure(value: Decimal) -> str:
    """Format net exposure with color coding.

    Positive values (net long) are green.
    Negative values (net short) are red.
    Zero is neutral white.

    Args:
        value: Net exposure value

    Returns:
        Rich markup string with color-coded value

    Example:
        >>> format_net_exposure(Decimal("1000.00"))
        '[green]+$1,000.00[/green]'
    """
    if value > 0:
        return f"[green]+${value:,.2f}[/green]"
    elif value < 0:
        return f"[red]${value:,.2f}[/red]"
    else:
        return f"${value:,.2f}"


def format_size(size: Decimal) -> str:
    """Format trade size with appropriate precision.

    Small sizes (< 10) show 4 decimal places.
    Large sizes show 2 decimal places with commas.

    Args:
        size: Trade size to format

    Returns:
        Formatted size string

    Example:
        >>> format_size(Decimal("0.1234"))
        '0.1234'
        >>> format_size(Decimal("1234.5678"))
        '1,234.57'
    """
    if abs(size) < 10:
        return f"{size:.4f}"
    else:
        return f"{size:,.2f}"


def format_trade_type(trade_type: str) -> str:
    """Format trade type for display.

    Args:
        trade_type: Trade type string (e.g., "open", "close")

    Returns:
        Uppercase trade type

    Example:
        >>> format_trade_type("open")
        'OPEN'
    """
    return trade_type.upper()


def style_side(side: OrderSide) -> str:
    """Apply color styling to order side.

    BUY orders are green, SELL orders are red.

    Args:
        side: OrderSide enum value

    Returns:
        Rich markup string with colored side

    Example:
        >>> style_side(OrderSide.BUY)
        '[green]BUY[/green]'
    """
    if side == OrderSide.BUY:
        return "[green]BUY[/green]"
    else:
        return "[red]SELL[/red]"


def get_portfolio_bias_label(num_buys: int, num_sells: int) -> str:
    """Determine portfolio bias label based on buy/sell mix.

    Args:
        num_buys: Number of buy trades
        num_sells: Number of sell trades

    Returns:
        Label describing portfolio bias

    Example:
        >>> get_portfolio_bias_label(3, 0)
        'All Long Positions'
    """
    if num_buys == 0 and num_sells == 0:
        return "No Trades"
    elif num_buys > 0 and num_sells == 0:
        return "All Long Positions"
    elif num_sells > 0 and num_buys == 0:
        return "All Short Positions"
    elif num_buys == num_sells:
        return "Balanced Long/Short"
    elif num_buys > num_sells:
        return "Long Biased"
    else:
        return "Short Biased"


def determine_skip_reason(trade: Trade) -> str:
    """Determine reason why trade was skipped.

    Currently detects:
    - Below minimum notional value

    Args:
        trade: Trade object that was skipped

    Returns:
        Reason string for display

    Example:
        >>> determine_skip_reason(small_trade)
        'Below minimum notional'
    """
    # Calculate notional value
    price = trade.limit_price if trade.limit_price else trade.reference_price
    notional = abs(trade.size * price)

    if notional < MIN_NOTIONAL_VALUE:
        return "Below minimum notional"

    # Default reason if we can't determine specifics
    return "Unknown reason"
