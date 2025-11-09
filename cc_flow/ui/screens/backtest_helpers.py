"""Helper functions for backtest screen.

This module provides parameter validation and mock backtest execution
to keep the main BacktestScreen module under 300 lines per SOLID principles.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from cc_flow.domain.backtest import BacktestResult


def validate_and_parse_parameters(
    start_date_str: str,
    end_date_str: str,
    num_long_str: str,
    num_short_str: str,
    leverage_str: str,
    rebalance_days_str: str,
) -> dict:
    """
    Validate and parse backtest parameters from string inputs.

    Args:
        start_date_str: Start date in YYYY-MM-DD format
        end_date_str: End date in YYYY-MM-DD format
        num_long_str: Number of long positions (integer)
        num_short_str: Number of short positions (integer)
        leverage_str: Target leverage (decimal)
        rebalance_days_str: Rebalance frequency in days (integer)

    Returns:
        Dictionary with validated and parsed parameters

    Raises:
        ValueError: If any parameter is invalid with descriptive message

    Example:
        >>> params = validate_and_parse_parameters(
        ...     "2024-01-01", "2024-12-31", "10", "10", "1.0", "7"
        ... )
        >>> params['start_date']
        date(2024, 1, 1)
    """
    # Parse and validate dates
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid parameter format: Date must be YYYY-MM-DD. Got: "
            f"start={start_date_str}, end={end_date_str}"
        ) from e

    if start_date >= end_date:
        raise ValueError(
            f"Start date must be before end date. Got: "
            f"start={start_date}, end={end_date}"
        )

    # Parse and validate integers
    try:
        num_long = int(num_long_str)
        num_short = int(num_short_str)
        rebalance_days = int(rebalance_days_str)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid parameter format: Expected integers. Got: "
            f"num_long={num_long_str}, num_short={num_short_str}, "
            f"rebalance_days={rebalance_days_str}"
        ) from e

    if num_long < 0 or num_short < 0:
        raise ValueError(
            f"Position counts must be non-negative. Got: "
            f"num_long={num_long}, num_short={num_short}"
        )

    if rebalance_days <= 0:
        raise ValueError(f"Rebalance days must be positive. Got: {rebalance_days}")

    # Parse and validate leverage
    try:
        leverage = Decimal(leverage_str)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid parameter format: Leverage must be a number. "
            f"Got: {leverage_str}"
        ) from e

    if leverage <= 0:
        raise ValueError(f"Leverage must be positive. Got: {leverage}")

    return {
        "start_date": start_date,
        "end_date": end_date,
        "num_long": num_long,
        "num_short": num_short,
        "target_leverage": leverage,
        "every_n_days": rebalance_days,
    }


async def create_mock_backtest_result(params: dict) -> BacktestResult:
    """
    Create mock backtest result for testing.

    This is a placeholder for the real backtest integration.
    Real implementation will use the backtester module.

    Args:
        params: Validated parameters dict from validate_and_parse_parameters

    Returns:
        BacktestResult with mock performance metrics

    Example:
        >>> result = await create_mock_backtest_result(params)
        >>> result.total_return
        Decimal('0.15')
    """
    from cc_flow.domain.backtest import BacktestConfig, BacktestResult

    # Create backtest config
    config = BacktestConfig(
        num_long=params["num_long"],
        num_short=params["num_short"],
        target_leverage=params["target_leverage"],
        rank_power=Decimal("0.0"),
        rebalance_every_n_days=params["every_n_days"],
        predictions_path="predictions.parquet",
        prices_path="prices.parquet",
        start_date=params["start_date"].strftime("%Y-%m-%d"),
        end_date=params["end_date"].strftime("%Y-%m-%d"),
    )

    # Create mock daily data
    daily_df = pl.DataFrame(
        {
            "date": [params["start_date"], params["end_date"]],
            "portfolio_value": [100000.0, 115000.0],
            "daily_return": [0.0, 0.15],
        }
    )

    # Create mock positions data
    positions_df = pl.DataFrame(
        {
            "date": [params["start_date"]],
            "symbol": ["BTC"],
            "weight": [0.1],
        }
    )

    # Create mock result
    result = BacktestResult(
        config=config,
        daily_df=daily_df,
        positions_df=positions_df,
        total_return=Decimal("0.15"),
        cagr=Decimal("0.18"),
        sharpe_ratio=Decimal("1.5"),
        sortino_ratio=Decimal("2.0"),
        max_drawdown=Decimal("-0.12"),
        calmar_ratio=Decimal("1.5"),
        annual_volatility=Decimal("0.12"),
        win_rate=Decimal("0.58"),
        avg_turnover=Decimal("0.05"),
        num_trades=100,
        num_rebalances=52,
        backtest_start=datetime(
            params["start_date"].year,
            params["start_date"].month,
            params["start_date"].day,
            tzinfo=UTC,
        ),
        backtest_end=datetime(
            params["end_date"].year,
            params["end_date"].month,
            params["end_date"].day,
            tzinfo=UTC,
        ),
    )

    return result


def format_performance_metrics(result: BacktestResult) -> str:
    """
    Format performance metrics for display.

    Args:
        result: BacktestResult with metrics to format

    Returns:
        Formatted string with performance metrics

    Example:
        >>> text = format_performance_metrics(result)
        >>> "Total Return" in text
        True
    """
    return (
        f"Total Return: {result.total_return * 100:,.2f}%\n"
        f"Annualized Return (CAGR): {result.cagr * 100:,.2f}%\n"
        f"Sharpe Ratio: {result.sharpe_ratio:.2f}\n"
        f"Sortino Ratio: {result.sortino_ratio:.2f}\n"
        f"Calmar Ratio: {result.calmar_ratio:.2f}\n"
        f"Win Rate: {result.win_rate * 100:,.2f}%\n"
    )


def format_risk_metrics(result: BacktestResult) -> str:
    """
    Format risk metrics for display.

    Args:
        result: BacktestResult with metrics to format

    Returns:
        Formatted string with risk metrics

    Example:
        >>> text = format_risk_metrics(result)
        >>> "Max Drawdown" in text
        True
    """
    return (
        f"Max Drawdown: {result.max_drawdown * 100:,.2f}%\n"
        f"Volatility (Annual): {result.annual_volatility * 100:,.2f}%\n"
        f"Average Turnover: {result.avg_turnover * 100:,.2f}%\n"
    )
