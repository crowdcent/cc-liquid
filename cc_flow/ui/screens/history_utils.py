"""Utility functions for trade history processing."""

from __future__ import annotations

from decimal import Decimal


def calculate_summary_stats(fills: list[dict]) -> dict:
    """Calculate summary statistics from fills.

    Args:
        fills: List of fill dictionaries

    Returns:
        Dictionary with summary statistics containing:
            - total_trades: Number of trades
            - total_volume: Total notional volume
            - total_fees: Total fees paid
            - success_rate: Percentage of filled trades
    """
    total_trades = len(fills)

    if total_trades == 0:
        return {
            "total_trades": 0,
            "total_volume": Decimal("0"),
            "total_fees": Decimal("0"),
            "success_rate": 0.0,
        }

    # Calculate total volume (size * price)
    total_volume = Decimal("0")
    for fill in fills:
        try:
            size = fill.get("size", Decimal("0"))
            price = fill.get("price", Decimal("0"))
            total_volume += size * price
        except (TypeError, KeyError):
            continue

    # Calculate total fees
    total_fees = Decimal("0")
    for fill in fills:
        try:
            fee = fill.get("fee", Decimal("0"))
            total_fees += fee
        except (TypeError, KeyError):
            continue

    # Calculate success rate (filled / total)
    filled_count = sum(1 for fill in fills if fill.get("status", "") == "filled")
    success_rate = (filled_count / total_trades * 100) if total_trades > 0 else 0.0

    return {
        "total_trades": total_trades,
        "total_volume": total_volume,
        "total_fees": total_fees,
        "success_rate": success_rate,
    }


def format_summary_text(stats: dict) -> str:
    """Format summary statistics as text.

    Args:
        stats: Dictionary with summary statistics

    Returns:
        Formatted summary text
    """
    return f"""Trade History Summary

Total Trades: {stats['total_trades']}
Total Volume: ${stats['total_volume']:,.2f}
Total Fees: ${stats['total_fees']:,.2f}
Success Rate: {stats['success_rate']:.1f}%
"""
