"""Financial calculation utilities.

This module provides financial calculation functions for leverage, PNL, returns, and risk metrics.
"""

from __future__ import annotations

from decimal import Decimal

import polars as pl


def calculate_leverage(position_value: Decimal, account_value: Decimal) -> Decimal:
    """Calculate leverage ratio.

    Args:
        position_value: Total absolute position value
        account_value: Account value

    Returns:
        Leverage ratio
    """
    if account_value == 0:
        return Decimal("0")
    return position_value / account_value


def calculate_pnl(entry_price: Decimal, current_price: Decimal, size: Decimal, side: str) -> Decimal:
    """Calculate unrealized PNL.

    Args:
        entry_price: Entry price
        current_price: Current price
        size: Position size (positive)
        side: "LONG" or "SHORT"

    Returns:
        Unrealized PNL
    """
    price_diff = current_price - entry_price
    if side == "SHORT":
        price_diff = -price_diff
    return price_diff * size


def calculate_return(entry_price: Decimal, current_price: Decimal, side: str) -> Decimal:
    """Calculate return percentage.

    Args:
        entry_price: Entry price
        current_price: Current price
        side: "LONG" or "SHORT"

    Returns:
        Return as decimal (0.15 for 15%)
    """
    if entry_price == 0:
        return Decimal("0")

    ret = (current_price - entry_price) / entry_price
    if side == "SHORT":
        ret = -ret
    return ret


def calculate_sharpe_ratio(returns: pl.Series, risk_free_rate: Decimal = Decimal("0")) -> Decimal:
    """Calculate Sharpe ratio.

    Args:
        returns: Series of returns
        risk_free_rate: Risk-free rate (annualized)

    Returns:
        Sharpe ratio
    """
    if len(returns) == 0 or returns.std() == 0:
        return Decimal("0")

    excess_returns = returns - float(risk_free_rate) / 252  # Daily
    return Decimal(str(excess_returns.mean() / returns.std() * (252**0.5)))


def calculate_sortino_ratio(returns: pl.Series, risk_free_rate: Decimal = Decimal("0")) -> Decimal:
    """Calculate Sortino ratio.

    Args:
        returns: Series of returns
        risk_free_rate: Risk-free rate (annualized)

    Returns:
        Sortino ratio
    """
    if len(returns) == 0:
        return Decimal("0")

    excess_returns = returns - float(risk_free_rate) / 252
    downside = returns.filter(returns < 0)

    if len(downside) == 0:
        return Decimal("0")

    downside_std = downside.std()
    if downside_std is None or downside_std == 0:
        return Decimal("0")

    return Decimal(str(excess_returns.mean() / downside_std * (252**0.5)))
