#!/usr/bin/env python3
"""Demonstration of cc_flow utilities.

This script demonstrates all utility functions in action.
Run with: uv run python cc_flow/utils/demo.py
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import polars as pl

from cc_flow.utils import (
    calculate_leverage,
    calculate_pnl,
    calculate_return,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    configure_logging,
    format_currency,
    format_datetime,
    format_decimal,
    format_percentage,
    log,
    validate_date_range,
    validate_decimal_range,
    validate_ethereum_address,
)


def demo_logging():
    """Demonstrate logging functionality."""
    print("\n" + "=" * 60)
    print("LOGGING DEMO")
    print("=" * 60)

    log.info("This is an info message")
    log.debug("This is a debug message (may not show with default level)")
    log.warning("This is a warning message")

    # Custom logger with file output
    custom_log = configure_logging(level="DEBUG", log_file="demo.log")
    custom_log.debug("This debug message will be written to demo.log")

    print("Check demo.log for the debug message!")


def demo_validation():
    """Demonstrate validation functionality."""
    print("\n" + "=" * 60)
    print("VALIDATION DEMO")
    print("=" * 60)

    # Ethereum address validation
    valid_address = "0x1234567890abcdef1234567890abcdef12345678"
    try:
        validate_ethereum_address(valid_address)
        print(f"✓ Valid address: {valid_address}")
    except ValueError as e:
        print(f"✗ Invalid: {e}")

    # Try invalid address
    try:
        validate_ethereum_address("not_an_address")
        print("✓ This shouldn't print")
    except ValueError as e:
        print(f"✓ Caught invalid address: {e}")

    # Decimal range validation
    leverage = Decimal("2.5")
    try:
        validate_decimal_range(
            leverage, min_value=Decimal("1"), max_value=Decimal("5"), name="leverage"
        )
        print(f"✓ Valid leverage: {leverage}x")
    except ValueError as e:
        print(f"✗ Invalid: {e}")

    # Date validation
    trade_date = "2024-06-15"
    try:
        validate_date_range(
            trade_date, start_date="2024-01-01", end_date="2024-12-31"
        )
        print(f"✓ Valid date: {trade_date}")
    except ValueError as e:
        print(f"✗ Invalid: {e}")


def demo_formatting():
    """Demonstrate formatting functionality."""
    print("\n" + "=" * 60)
    print("FORMATTING DEMO")
    print("=" * 60)

    # Currency formatting
    pnl = Decimal("1234567.89")
    print(f"PNL: {format_currency(pnl)}")
    print(f"EUR: {format_currency(pnl, symbol='€')}")

    # Percentage formatting
    daily_return = Decimal("0.0543")
    print(f"Return: {format_percentage(daily_return)}")
    print(f"Return (signed): {format_percentage(daily_return, include_sign=True)}")

    # Datetime formatting
    now = datetime.now()
    print(f"Timestamp: {format_datetime(now)}")
    print(f"Date only: {format_datetime(now, format='%Y-%m-%d')}")

    # Decimal formatting
    price = Decimal("123.4500")
    print(f"Price (stripped): {format_decimal(price)}")
    print(f"Price (full): {format_decimal(price, strip_trailing=False)}")


def demo_calculations():
    """Demonstrate financial calculations."""
    print("\n" + "=" * 60)
    print("CALCULATIONS DEMO")
    print("=" * 60)

    # Leverage calculation
    position_value = Decimal("50000")
    account_value = Decimal("20000")
    leverage = calculate_leverage(position_value, account_value)
    print(f"Account: {format_currency(account_value)}")
    print(f"Position: {format_currency(position_value)}")
    print(f"Leverage: {leverage}x")

    # PNL calculation
    print("\nLong Position:")
    entry = Decimal("100")
    current = Decimal("115")
    size = Decimal("10")
    pnl = calculate_pnl(entry, current, size, "LONG")
    ret = calculate_return(entry, current, "LONG")
    print(f"Entry: {format_currency(entry)}, Current: {format_currency(current)}")
    print(f"PNL: {format_currency(pnl)}")
    print(f"Return: {format_percentage(ret, include_sign=True)}")

    print("\nShort Position:")
    pnl_short = calculate_pnl(entry, Decimal("85"), size, "SHORT")
    ret_short = calculate_return(entry, Decimal("85"), "SHORT")
    print(f"Entry: {format_currency(entry)}, Current: {format_currency(Decimal('85'))}")
    print(f"PNL: {format_currency(pnl_short)}")
    print(f"Return: {format_percentage(ret_short, include_sign=True)}")

    # Risk metrics
    print("\nRisk Metrics:")
    returns = pl.Series([0.01, -0.005, 0.015, -0.008, 0.012, 0.003, -0.002, 0.008])
    sharpe = calculate_sharpe_ratio(returns)
    sortino = calculate_sortino_ratio(returns)
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Sortino Ratio: {sortino:.2f}")


def demo_combined():
    """Demonstrate utilities working together."""
    print("\n" + "=" * 60)
    print("COMBINED DEMO - Portfolio Analysis")
    print("=" * 60)

    # Portfolio setup
    owner = "0xabcdef1234567890abcdef1234567890abcdef12"
    validate_ethereum_address(owner)
    log.info(f"Analyzing portfolio for {owner[:10]}...")

    # Account state
    account_value = Decimal("100000")
    positions = [
        {
            "symbol": "BTC",
            "entry": Decimal("60000"),
            "current": Decimal("65000"),
            "size": Decimal("1"),
            "side": "LONG",
        },
        {
            "symbol": "ETH",
            "entry": Decimal("3000"),
            "current": Decimal("3150"),
            "size": Decimal("10"),
            "side": "LONG",
        },
        {
            "symbol": "SOL",
            "entry": Decimal("100"),
            "current": Decimal("95"),
            "size": Decimal("50"),
            "side": "LONG",
        },
    ]

    # Calculate metrics
    total_position_value = Decimal("0")
    total_pnl = Decimal("0")

    print("\nPositions:")
    print(f"{'Symbol':<10} {'Entry':<12} {'Current':<12} {'PNL':<15} {'Return':<10}")
    print("-" * 60)

    for pos in positions:
        pnl = calculate_pnl(pos["entry"], pos["current"], pos["size"], pos["side"])
        ret = calculate_return(pos["entry"], pos["current"], pos["side"])
        position_value = pos["current"] * pos["size"]

        total_pnl += pnl
        total_position_value += position_value

        print(
            f"{pos['symbol']:<10} "
            f"{format_currency(pos['entry']):<12} "
            f"{format_currency(pos['current']):<12} "
            f"{format_currency(pnl):<15} "
            f"{format_percentage(ret, include_sign=True):<10}"
        )

    leverage = calculate_leverage(total_position_value, account_value)

    # Validate leverage
    try:
        validate_decimal_range(leverage, max_value=Decimal("5"), name="leverage")
        leverage_status = "✓ OK"
    except ValueError:
        leverage_status = "✗ EXCEEDS LIMIT"

    print("\nSummary:")
    print(f"Total Account Value: {format_currency(account_value)}")
    print(f"Total Position Value: {format_currency(total_position_value)}")
    print(f"Total PNL: {format_currency(total_pnl)}")
    print(f"Current Leverage: {leverage:.2f}x {leverage_status}")
    print(f"Analysis Time: {format_datetime(datetime.now())}")

    log.info(f"Analysis complete. Total PNL: {format_currency(total_pnl)}")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("CC-FLOW UTILITIES DEMONSTRATION")
    print("=" * 60)

    demo_logging()
    demo_validation()
    demo_formatting()
    demo_calculations()
    demo_combined()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
