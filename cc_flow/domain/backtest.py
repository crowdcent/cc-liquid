"""Backtest domain models.

This module defines the data models for backtesting configuration and results.
BacktestConfig is a dataclass for simplicity, while BacktestResult is a Pydantic
model that can handle polars DataFrames and provides validation.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import polars as pl
from pydantic import BaseModel, ConfigDict, Field


@dataclass
class BacktestConfig:
    """Backtesting configuration (uses dataclass not Pydantic).

    This configuration specifies all parameters needed to run a backtest,
    including portfolio construction, rebalancing schedule, cost assumptions,
    and data sources.

    Attributes:
        num_long: Number of long positions to hold.
        num_short: Number of short positions to hold.
        target_leverage: Target portfolio leverage (1.0 = no leverage).
        rank_power: Power to raise ranks to for weighting (0 = equal-weight).
        rebalance_every_n_days: Days between rebalancing.
        predictions_path: Path to predictions parquet file.
        prices_path: Path to prices parquet file.
        fee_rate: Trading fee rate (e.g., 0.00025 = 2.5 bps).
        slippage_bps: Slippage in basis points.
        start_date: Backtest start date (YYYY-MM-DD) or None for earliest.
        end_date: Backtest end date (YYYY-MM-DD) or None for latest.
        prediction_lag_days: Days to lag predictions to simulate real-world delay.
    """

    # Portfolio
    num_long: int = 10
    num_short: int = 10
    target_leverage: Decimal = Decimal("1.0")
    rank_power: Decimal = Decimal("0.0")

    # Rebalancing
    rebalance_every_n_days: int = 10

    # Data
    predictions_path: str = "predictions.parquet"
    prices_path: str = "prices.parquet"

    # Costs
    fee_rate: Decimal = Decimal("0.00025")  # 2.5 bps
    slippage_bps: Decimal = Decimal("5.0")  # 5 bps

    # Date range
    start_date: str | None = None
    end_date: str | None = None

    # Prediction lag
    prediction_lag_days: int = 1


class BacktestResult(BaseModel):
    """Backtesting result with performance metrics.

    This model encapsulates the complete results of a backtest run, including
    time-series data (daily equity and positions), performance metrics, and
    the configuration that generated these results.

    The model uses Pydantic v2 with arbitrary_types_allowed=True to support
    polars DataFrames, which are not natively JSON-serializable.

    Attributes:
        daily_df: Daily time series of equity, returns, and drawdown.
        positions_df: Position snapshots at each rebalancing.
        config: BacktestConfig that generated these results.
        total_return: Total cumulative return over backtest period.
        cagr: Compound annual growth rate.
        sharpe_ratio: Risk-adjusted return (excess return / volatility).
        sortino_ratio: Downside risk-adjusted return.
        max_drawdown: Maximum peak-to-trough decline (negative value).
        calmar_ratio: CAGR / abs(max_drawdown).
        annual_volatility: Annualized standard deviation of returns.
        win_rate: Fraction of profitable rebalancing periods.
        avg_turnover: Average portfolio turnover per rebalancing.
        num_trades: Total number of trades executed.
        num_rebalances: Total number of rebalancing events.
        backtest_start: First date in backtest period.
        backtest_end: Last date in backtest period.
        run_at: Timestamp when backtest was executed (defaults to now).
    """

    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)

    # DataFrames
    daily_df: pl.DataFrame = Field(..., description="Daily equity/returns")
    positions_df: pl.DataFrame = Field(..., description="Position snapshots")

    # Config
    config: BacktestConfig

    # Performance metrics
    total_return: Decimal
    cagr: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    max_drawdown: Decimal
    calmar_ratio: Decimal
    annual_volatility: Decimal
    win_rate: Decimal
    avg_turnover: Decimal

    # Trade stats
    num_trades: int
    num_rebalances: int

    # Timestamps
    backtest_start: datetime
    backtest_end: datetime
    run_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
