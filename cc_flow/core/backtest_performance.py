"""Performance calculation for backtesting results.

This module provides the PerformanceCalculator class for calculating
comprehensive performance metrics from backtest returns.
"""

from __future__ import annotations

from decimal import Decimal

import polars as pl
from loguru import logger as log

from cc_flow.utils.calculations import calculate_sharpe_ratio, calculate_sortino_ratio


class PerformanceCalculator:
    """Calculate performance statistics from backtest results.

    Computes comprehensive performance metrics including returns, risk metrics,
    drawdowns, and rolling statistics.

    Example:
        >>> calculator = PerformanceCalculator()
        >>> metrics = calculator.calculate_metrics(returns_df)
        >>> print(f"Sharpe: {metrics['sharpe_ratio']:.2f}")
    """

    def calculate_metrics(self, returns: pl.DataFrame) -> dict[str, Decimal]:
        """Calculate comprehensive performance metrics.

        Args:
            returns: DataFrame with columns 'date' and 'daily_return'

        Returns:
            Dict of performance metrics including:
                - total_return: Total cumulative return
                - annualized_return: CAGR
                - volatility: Annualized volatility
                - sharpe_ratio: Risk-adjusted return
                - sortino_ratio: Downside risk-adjusted return
                - max_drawdown: Maximum peak-to-trough decline
                - calmar_ratio: CAGR / abs(max_drawdown)
                - win_rate: Fraction of positive return days
                - avg_win: Average positive return
                - avg_loss: Average negative return
                - profit_factor: sum(wins) / abs(sum(losses))

        Example:
            >>> metrics = calculator.calculate_metrics(returns_df)
            >>> assert "sharpe_ratio" in metrics
        """
        log.debug("Calculating performance metrics")

        if len(returns) == 0:
            log.warning("Empty returns DataFrame")
            return {}

        # Extract returns series
        if "daily_return" not in returns.columns:
            log.error("Missing 'daily_return' column")
            return {}

        return_series = returns["daily_return"]

        # Calculate total return (cumulative)
        cumulative = (1 + return_series).product() - 1
        total_return = Decimal(str(cumulative))

        # Calculate annualized return (CAGR)
        num_days = len(returns)
        if num_days > 0:
            years = num_days / 252  # Trading days per year
            cagr = (1 + float(total_return)) ** (1 / years) - 1
            annualized_return = Decimal(str(cagr))
        else:
            annualized_return = Decimal("0")

        # Calculate volatility (annualized)
        volatility = Decimal(str(return_series.std() * (252 ** 0.5)))

        # Calculate Sharpe ratio
        sharpe_ratio = calculate_sharpe_ratio(return_series)

        # Calculate Sortino ratio
        sortino_ratio = calculate_sortino_ratio(return_series)

        # Calculate max drawdown
        drawdown_df = self.calculate_drawdown_series(returns)
        max_drawdown = Decimal(str(drawdown_df["drawdown"].min())) if len(drawdown_df) > 0 else Decimal("0")

        # Calculate Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown < 0 else Decimal("0")

        # Calculate win/loss statistics
        wins = return_series.filter(return_series > 0)
        losses = return_series.filter(return_series < 0)

        win_rate = Decimal(str(len(wins) / len(return_series))) if len(return_series) > 0 else Decimal("0")
        avg_win = Decimal(str(wins.mean())) if len(wins) > 0 else Decimal("0")
        avg_loss = Decimal(str(losses.mean())) if len(losses) > 0 else Decimal("0")

        # Calculate profit factor
        total_wins = wins.sum()
        total_losses = abs(losses.sum())
        profit_factor = Decimal(str(total_wins / total_losses)) if total_losses > 0 else Decimal("0")

        metrics = {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "max_drawdown": max_drawdown,
            "calmar_ratio": calmar_ratio,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
        }

        log.debug(f"Calculated metrics: Sharpe={sharpe_ratio:.2f}, MaxDD={max_drawdown:.2%}")
        return metrics

    def calculate_drawdown_series(self, returns: pl.DataFrame) -> pl.DataFrame:
        """Calculate drawdown time series.

        Args:
            returns: DataFrame with 'date' and 'daily_return' columns

        Returns:
            DataFrame with columns:
                - date: Date
                - cumulative_return: Cumulative return to date
                - drawdown: Current drawdown from peak (non-positive)

        Example:
            >>> dd_df = calculator.calculate_drawdown_series(returns)
            >>> assert all(dd_df["drawdown"] <= 0)
        """
        if len(returns) == 0:
            return pl.DataFrame()

        # Calculate cumulative returns
        df = returns.with_columns([
            ((1 + pl.col("daily_return")).cum_prod() - 1).alias("cumulative_return")
        ])

        # Calculate running maximum
        df = df.with_columns([
            pl.col("cumulative_return").cum_max().alias("running_max")
        ])

        # Calculate drawdown from peak
        df = df.with_columns([
            ((pl.col("cumulative_return") - pl.col("running_max")) /
             (1 + pl.col("running_max"))).alias("drawdown")
        ])

        return df.select(["date", "cumulative_return", "drawdown"])

    def calculate_rolling_metrics(
        self, returns: pl.DataFrame, window_days: int
    ) -> pl.DataFrame:
        """Calculate rolling performance metrics.

        Args:
            returns: DataFrame with 'date' and 'daily_return' columns
            window_days: Rolling window size in days

        Returns:
            DataFrame with rolling metrics:
                - date
                - rolling_return: Rolling cumulative return
                - rolling_volatility: Rolling volatility (annualized)
                - rolling_sharpe: Rolling Sharpe ratio

        Example:
            >>> rolling = calculator.calculate_rolling_metrics(returns, window_days=20)
            >>> assert "rolling_sharpe" in rolling.columns
        """
        if len(returns) < window_days:
            log.warning(f"Not enough data for rolling window of {window_days} days")
            return pl.DataFrame()

        df = returns.with_columns([
            # Rolling return
            pl.col("daily_return").rolling_mean(window_days).alias("rolling_return"),
            # Rolling volatility (annualized)
            (pl.col("daily_return").rolling_std(window_days) * (252 ** 0.5)).alias("rolling_volatility"),
        ])

        # Calculate rolling Sharpe
        df = df.with_columns([
            (pl.col("rolling_return") / pl.col("rolling_volatility") * (252 ** 0.5)).alias("rolling_sharpe")
        ])

        # Drop first window_days-1 rows (incomplete windows)
        df = df.slice(window_days - 1, len(df))

        return df.select(["date", "rolling_return", "rolling_volatility", "rolling_sharpe"])
