"""Example usage of backtest domain models.

This script demonstrates how to use BacktestConfig and BacktestResult
to represent backtesting parameters and results.
"""

from datetime import UTC, datetime
from decimal import Decimal

import polars as pl

from cc_flow.domain.backtest import BacktestConfig, BacktestResult


def create_sample_backtest_config() -> BacktestConfig:
    """Create a sample BacktestConfig with custom parameters."""
    config = BacktestConfig(
        num_long=15,
        num_short=10,
        target_leverage=Decimal("1.5"),
        rank_power=Decimal("1.0"),
        rebalance_every_n_days=7,
        predictions_path="data/predictions.parquet",
        prices_path="data/prices.parquet",
        fee_rate=Decimal("0.0003"),
        slippage_bps=Decimal("10.0"),
        start_date="2024-01-01",
        end_date="2024-12-31",
        prediction_lag_days=2,
    )
    return config


def create_sample_daily_dataframe() -> pl.DataFrame:
    """Create a sample daily equity DataFrame."""
    dates = [datetime(2024, 1, i, tzinfo=UTC) for i in range(1, 11)]
    equity_values = [
        Decimal("100000"),
        Decimal("101500"),
        Decimal("103200"),
        Decimal("102800"),
        Decimal("104500"),
        Decimal("106100"),
        Decimal("105800"),
        Decimal("107300"),
        Decimal("108900"),
        Decimal("110200"),
    ]

    daily_df = pl.DataFrame({
        "date": dates,
        "equity": equity_values,
        "returns": [Decimal("0.0")] + [
            (equity_values[i] - equity_values[i - 1]) / equity_values[i - 1]
            for i in range(1, len(equity_values))
        ],
        "drawdown": [Decimal("0.0")] * len(dates),
        "cumulative_return": [
            (val - Decimal("100000")) / Decimal("100000")
            for val in equity_values
        ],
    })

    return daily_df


def create_sample_positions_dataframe() -> pl.DataFrame:
    """Create a sample positions DataFrame."""
    positions_df = pl.DataFrame({
        "date": [datetime(2024, 1, 1, tzinfo=UTC)] * 5,
        "symbol": ["BTC", "ETH", "SOL", "AVAX", "MATIC"],
        "position": [
            Decimal("2.5"),
            Decimal("25.0"),
            Decimal("500.0"),
            Decimal("-100.0"),
            Decimal("-200.0"),
        ],
        "notional": [
            Decimal("100000"),
            Decimal("75000"),
            Decimal("50000"),
            Decimal("-25000"),
            Decimal("-15000"),
        ],
        "weight": [
            Decimal("0.40"),
            Decimal("0.30"),
            Decimal("0.20"),
            Decimal("-0.10"),
            Decimal("-0.06"),
        ],
    })

    return positions_df


def create_sample_backtest_result() -> BacktestResult:
    """Create a sample BacktestResult with realistic metrics."""
    config = create_sample_backtest_config()
    daily_df = create_sample_daily_dataframe()
    positions_df = create_sample_positions_dataframe()

    result = BacktestResult(
        daily_df=daily_df,
        positions_df=positions_df,
        config=config,
        total_return=Decimal("0.102"),  # 10.2%
        cagr=Decimal("0.105"),  # 10.5% annualized
        sharpe_ratio=Decimal("1.85"),
        sortino_ratio=Decimal("2.35"),
        max_drawdown=Decimal("-0.08"),  # -8%
        calmar_ratio=Decimal("1.31"),  # CAGR / |max_drawdown|
        annual_volatility=Decimal("0.12"),  # 12%
        win_rate=Decimal("0.65"),  # 65% winning rebalances
        avg_turnover=Decimal("0.42"),  # 42% average turnover
        num_trades=156,
        num_rebalances=52,  # Weekly rebalancing for 1 year
        backtest_start=datetime(2024, 1, 1, tzinfo=UTC),
        backtest_end=datetime(2024, 12, 31, tzinfo=UTC),
    )

    return result


def print_backtest_summary(result: BacktestResult) -> None:
    """Print a formatted summary of backtest results."""
    print("\n" + "=" * 70)
    print("BACKTEST SUMMARY")
    print("=" * 70)
    print(f"\nPeriod: {result.backtest_start.date()} to {result.backtest_end.date()}")
    print(f"Run at: {result.run_at}")

    print("\n" + "-" * 70)
    print("CONFIGURATION")
    print("-" * 70)
    print(f"Long positions:  {result.config.num_long}")
    print(f"Short positions: {result.config.num_short}")
    print(f"Target leverage: {result.config.target_leverage}")
    print(f"Rank power:      {result.config.rank_power}")
    print(f"Rebalance every: {result.config.rebalance_every_n_days} days")
    print(f"Fee rate:        {result.config.fee_rate} ({float(result.config.fee_rate) * 10000:.1f} bps)")
    print(f"Slippage:        {result.config.slippage_bps} bps")

    print("\n" + "-" * 70)
    print("PERFORMANCE METRICS")
    print("-" * 70)
    print(f"Total return:       {float(result.total_return) * 100:>7.2f}%")
    print(f"CAGR:               {float(result.cagr) * 100:>7.2f}%")
    print(f"Sharpe ratio:       {float(result.sharpe_ratio):>7.2f}")
    print(f"Sortino ratio:      {float(result.sortino_ratio):>7.2f}")
    print(f"Max drawdown:       {float(result.max_drawdown) * 100:>7.2f}%")
    print(f"Calmar ratio:       {float(result.calmar_ratio):>7.2f}")
    print(f"Annual volatility:  {float(result.annual_volatility) * 100:>7.2f}%")
    print(f"Win rate:           {float(result.win_rate) * 100:>7.2f}%")
    print(f"Avg turnover:       {float(result.avg_turnover) * 100:>7.2f}%")

    print("\n" + "-" * 70)
    print("TRADING STATISTICS")
    print("-" * 70)
    print(f"Number of trades:     {result.num_trades:>6}")
    print(f"Number of rebalances: {result.num_rebalances:>6}")
    print(f"Avg trades per rebal: {result.num_trades / result.num_rebalances:>6.1f}")

    print("\n" + "-" * 70)
    print("DATA SUMMARY")
    print("-" * 70)
    print(f"Daily records:     {result.daily_df.height}")
    print(f"Position records:  {result.positions_df.height}")

    print("\n" + "=" * 70 + "\n")


def demonstrate_serialization(result: BacktestResult) -> None:
    """Demonstrate serialization capabilities."""
    print("\n" + "=" * 70)
    print("SERIALIZATION EXAMPLES")
    print("=" * 70)

    # Model dump
    dumped = result.model_dump()
    print("\nModel dump keys:", list(dumped.keys()))
    print(f"Total return from dump: {dumped['total_return']}")
    print(f"Config type from dump: {type(dumped['config'])}")

    # Config serialization
    from dataclasses import asdict

    config_dict = asdict(result.config)
    print(f"\nConfig as dict keys: {list(config_dict.keys())[:5]}...")

    # DataFrame info
    print("\nDaily DataFrame schema:")
    print(result.daily_df.schema)

    print("\n" + "=" * 70 + "\n")


def main():
    """Run example demonstrations."""
    # Create sample config
    print("\n1. Creating BacktestConfig...")
    config = create_sample_backtest_config()
    print(f"Config created: {config.num_long} long, {config.num_short} short")

    # Create sample result
    print("\n2. Creating BacktestResult...")
    result = create_sample_backtest_result()
    print(f"Result created with {result.num_trades} trades")

    # Print summary
    print("\n3. Displaying backtest summary...")
    print_backtest_summary(result)

    # Demonstrate serialization
    print("\n4. Demonstrating serialization...")
    demonstrate_serialization(result)

    # Show DataFrame samples
    print("\n5. Sample daily data (first 5 rows):")
    print(result.daily_df.head(5))

    print("\n6. Sample positions data:")
    print(result.positions_df)


if __name__ == "__main__":
    main()
