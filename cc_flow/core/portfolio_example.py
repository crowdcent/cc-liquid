"""Example usage of PortfolioManager.

This script demonstrates how to use the PortfolioManager to calculate
target positions from predictions using both equal-weighting and
rank-power weighting schemes.

Run with: uv run python cc_flow/core/portfolio_example.py
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import polars as pl

from cc_flow.core.portfolio import PortfolioManager
from cc_flow.domain.config import PortfolioConfig


def create_sample_predictions() -> pl.DataFrame:
    """Create sample predictions for demonstration."""
    return pl.DataFrame(
        {
            "date": [date(2024, 11, 8)] * 20,
            "asset_id": [
                "BTC",
                "ETH",
                "SOL",
                "AVAX",
                "ATOM",
                "LINK",
                "UNI",
                "AAVE",
                "MKR",
                "SNX",
                "CRV",
                "LDO",
                "ARB",
                "OP",
                "MATIC",
                "FTM",
                "NEAR",
                "DOT",
                "ADA",
                "XRP",
            ],
            "prediction": [
                0.95,  # BTC - strongest long
                0.88,  # ETH
                0.82,  # SOL
                0.75,  # AVAX
                0.68,  # ATOM
                0.45,  # LINK
                0.32,  # UNI
                0.21,  # AAVE
                0.15,  # MKR
                0.08,  # SNX
                -0.05,  # CRV
                -0.12,  # LDO
                -0.25,  # ARB
                -0.38,  # OP
                -0.51,  # MATIC
                -0.64,  # FTM
                -0.72,  # NEAR
                -0.79,  # DOT
                -0.86,  # ADA
                -0.93,  # XRP - strongest short
            ],
        }
    )


def example_equal_weighted():
    """Example: Equal-weighted portfolio."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Equal-Weighted Portfolio")
    print("=" * 70)

    # Configuration: 10 long, 5 short, 1.5x leverage, equal weights
    config = PortfolioConfig(
        num_long=10,
        num_short=5,
        target_leverage=Decimal("1.5"),
        rank_power=Decimal("0.0"),  # 0 = equal weighting
    )

    manager = PortfolioManager(config=config)
    predictions = create_sample_predictions()
    account_value = Decimal("50000.00")

    positions = manager.calculate_target_positions(
        predictions=predictions, account_value=account_value
    )

    print(f"\nAccount Value: ${account_value:,.2f}")
    print(f"Target Leverage: {config.target_leverage}x")
    print(f"Total Positions: {len(positions)} ({config.num_long} long, {config.num_short} short)")
    print(f"\nWeighting Scheme: Equal (rank_power = {config.rank_power})")
    print(f"Weight per position: {Decimal('1.5') / Decimal('15'):.4f} ({(1.5 / 15) * 100:.2f}%)")

    print("\n" + "-" * 70)
    print(f"{'Coin':<10} {'Side':<6} {'Weight':<10} {'Target Value':<15}")
    print("-" * 70)

    for pos in positions[:5]:  # Show first 5 longs
        print(
            f"{pos.coin:<10} {pos.side:<6} {float(pos.weight):>8.4f}   ${pos.target_value:>12,.2f}"
        )

    print("...")

    for pos in positions[-5:]:  # Show all 5 shorts
        print(
            f"{pos.coin:<10} {pos.side:<6} {float(pos.weight):>8.4f}   ${pos.target_value:>12,.2f}"
        )

    print("-" * 70)

    # Verify total notional
    total_notional = sum(abs(p.target_value) for p in positions)
    total_leverage = sum(abs(p.weight) for p in positions)

    print(f"\nTotal Notional: ${total_notional:,.2f}")
    print(f"Total Leverage: {total_leverage:.4f}x")
    print(f"Expected: ${account_value * config.target_leverage:,.2f}")


def example_rank_weighted():
    """Example: Rank-power weighted portfolio."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Rank-Power Weighted Portfolio")
    print("=" * 70)

    # Configuration: 15 long, 5 short, 2.0x leverage, rank_power=1
    config = PortfolioConfig(
        num_long=15,
        num_short=5,
        target_leverage=Decimal("2.0"),
        rank_power=Decimal("1.0"),  # 1 = 1/rank weighting
    )

    manager = PortfolioManager(config=config)
    predictions = create_sample_predictions()
    account_value = Decimal("100000.00")

    positions = manager.calculate_target_positions(
        predictions=predictions, account_value=account_value
    )

    print(f"\nAccount Value: ${account_value:,.2f}")
    print(f"Target Leverage: {config.target_leverage}x")
    print(f"Total Positions: {len(positions)} ({config.num_long} long, {config.num_short} short)")
    print(f"\nWeighting Scheme: Rank-Power (rank_power = {config.rank_power})")
    print("Higher-ranked assets receive proportionally more weight")

    print("\n" + "-" * 70)
    print(f"{'Coin':<10} {'Side':<6} {'Weight':<10} {'Target Value':<15}")
    print("-" * 70)

    # Show top 5 longs (should have highest weights)
    long_positions = [p for p in positions if p.side == "LONG"]
    for pos in long_positions[:5]:
        print(
            f"{pos.coin:<10} {pos.side:<6} {float(pos.weight):>8.4f}   ${pos.target_value:>12,.2f}"
        )

    print("...")

    # Show last 3 longs (should have lower weights)
    for pos in long_positions[-3:]:
        print(
            f"{pos.coin:<10} {pos.side:<6} {float(pos.weight):>8.4f}   ${pos.target_value:>12,.2f}"
        )

    print()

    # Show shorts
    short_positions = [p for p in positions if p.side == "SHORT"]
    for pos in short_positions:
        print(
            f"{pos.coin:<10} {pos.side:<6} {float(pos.weight):>8.4f}   ${pos.target_value:>12,.2f}"
        )

    print("-" * 70)

    # Verify total notional
    total_notional = sum(abs(p.target_value) for p in positions)
    total_leverage = sum(abs(p.weight) for p in positions)

    print(f"\nTotal Notional: ${total_notional:,.2f}")
    print(f"Total Leverage: {total_leverage:.4f}x")
    print(f"Expected: ${account_value * config.target_leverage:,.2f}")


def example_compare_rank_powers():
    """Example: Compare different rank_power values."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Comparing Different Rank Powers")
    print("=" * 70)

    predictions = create_sample_predictions()
    account_value = Decimal("50000.00")

    # Test different rank powers
    rank_powers = [Decimal("0.0"), Decimal("0.5"), Decimal("1.0"), Decimal("2.0")]

    print(f"\nAccount Value: ${account_value:,.2f}")
    print("Portfolio: 5 long, 5 short, 1.0x leverage")
    print("\nTop long position (BTC) weight by rank_power:")
    print("-" * 70)

    for rank_power in rank_powers:
        config = PortfolioConfig(
            num_long=5,
            num_short=5,
            target_leverage=Decimal("1.0"),
            rank_power=rank_power,
        )

        manager = PortfolioManager(config=config)
        positions = manager.calculate_target_positions(
            predictions=predictions, account_value=account_value
        )

        # Find BTC position
        btc_pos = next(p for p in positions if p.coin == "BTC")

        print(
            f"rank_power = {rank_power:>4}  →  weight = {float(btc_pos.weight):>6.4f}  →  value = ${btc_pos.target_value:>9,.2f}"
        )

    print("-" * 70)
    print("\nInterpretation:")
    print("  rank_power = 0.0  →  Equal weighting (all positions same size)")
    print("  rank_power = 0.5  →  Moderate concentration (sqrt penalty)")
    print("  rank_power = 1.0  →  1/rank weighting (linear penalty)")
    print("  rank_power = 2.0  →  High concentration (quadratic penalty)")


def example_small_portfolio():
    """Example: Small portfolio with limited capital."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Small Portfolio ($5K account)")
    print("=" * 70)

    config = PortfolioConfig(
        num_long=3,
        num_short=2,
        target_leverage=Decimal("1.0"),
        rank_power=Decimal("0.0"),
    )

    manager = PortfolioManager(config=config)
    predictions = create_sample_predictions()
    account_value = Decimal("5000.00")

    positions = manager.calculate_target_positions(
        predictions=predictions, account_value=account_value
    )

    print(f"\nAccount Value: ${account_value:,.2f}")
    print(f"Target Leverage: {config.target_leverage}x")
    print(f"Total Positions: {len(positions)}")
    print(f"Position Size: ${account_value / Decimal('5'):,.2f} each")

    print("\n" + "-" * 70)
    print(f"{'Coin':<10} {'Side':<6} {'Target Value':<15}")
    print("-" * 70)

    for pos in positions:
        print(f"{pos.coin:<10} {pos.side:<6} ${pos.target_value:>12,.2f}")

    print("-" * 70)


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("PORTFOLIO MANAGER EXAMPLES")
    print("=" * 70)

    example_equal_weighted()
    example_rank_weighted()
    example_compare_rank_powers()
    example_small_portfolio()

    print("\n" + "=" * 70)
    print("Examples complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
