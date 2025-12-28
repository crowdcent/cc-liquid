"""ChartWidget for displaying ASCII charts.

This module provides a reusable Static widget for displaying
time-series data as ASCII sparkline charts.
"""

from __future__ import annotations

from typing import Any

import polars as pl
from loguru import logger as log
from textual.widgets import Static


class ChartWidget(Static):
    """ASCII chart widget for equity curves and drawdown.

    A Static widget that displays time-series data using simple
    sparkline-style ASCII block characters.

    Features:
        - Equity curve plotting from portfolio values
        - Drawdown plotting from returns data
        - Auto-scaling to available data range
        - Inverted mode for drawdown visualization

    Example:
        ```python
        chart = ChartWidget()
        chart.plot_equity_curve(returns_df)
        ```

    Attributes:
        renderable: Current chart content (for testing access)
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize ChartWidget.

        Args:
            *args: Positional arguments passed to Static
            **kwargs: Keyword arguments passed to Static
        """
        super().__init__(*args, **kwargs)
        self.renderable: str = ""

    def plot_equity_curve(self, returns: pl.DataFrame) -> None:
        """Plot equity curve from returns data.

        Creates an ASCII sparkline chart showing portfolio value over time.
        Includes header with min/max values.

        Args:
            returns: DataFrame with 'date' and 'portfolio_value' columns

        Example:
            ```python
            df = pl.DataFrame({
                "date": ["2024-01-01", "2024-01-02"],
                "portfolio_value": [100000.0, 105000.0]
            })
            chart.plot_equity_curve(df)
            ```
        """
        log.debug(f"Plotting equity curve with {len(returns)} data points")

        if returns.is_empty():
            log.warning("No data provided for equity curve")
            self.renderable = "No data to plot"
            self.update(self.renderable)
            return

        values = returns["portfolio_value"].to_list()
        chart = self._create_sparkline(values)

        # Add header with min/max values
        min_val = min(values)
        max_val = max(values)
        header = f"Equity Curve (${min_val:,.0f} - ${max_val:,.0f})"

        self.renderable = f"{header}\n{chart}"
        self.update(self.renderable)
        log.debug(f"Equity curve updated: range ${min_val:,.0f} to ${max_val:,.0f}")

    def plot_drawdown(self, returns: pl.DataFrame) -> None:
        """Plot drawdown chart.

        Creates an ASCII sparkline chart showing drawdown over time.
        Calculates drawdown if not present in the DataFrame.

        Args:
            returns: DataFrame with drawdown data or daily_return column

        Example:
            ```python
            df = pl.DataFrame({
                "date": ["2024-01-01", "2024-01-02"],
                "daily_return": [0.0, -5.0]
            })
            chart.plot_drawdown(df)
            ```
        """
        log.debug(f"Plotting drawdown with {len(returns)} data points")

        if returns.is_empty():
            log.warning("No data provided for drawdown")
            self.renderable = "No data to plot"
            self.update(self.renderable)
            return

        # Calculate drawdown if not present
        if "drawdown" not in returns.columns:
            log.debug("Calculating drawdown from daily_return column")
            cumulative = returns["daily_return"].cum_sum()
            running_max = cumulative.cum_max()

            # Calculate drawdown as percentage
            # Handle division by zero for running_max
            drawdown_expr = pl.when(running_max != 0).then(
                (cumulative - running_max) / running_max * 100
            ).otherwise(0)

            # Materialize the expression in a new DataFrame
            returns_with_dd = returns.with_columns(drawdown_expr.alias("drawdown"))
            values = returns_with_dd["drawdown"].fill_null(0).to_list()
        else:
            log.debug("Using existing drawdown column")
            values = returns["drawdown"].to_list()

        chart = self._create_sparkline(values, inverted=True)

        max_dd = min(values)
        header = f"Drawdown (Max: {max_dd:.2f}%)"

        self.renderable = f"{header}\n{chart}"
        self.update(self.renderable)
        log.debug(f"Drawdown updated: max drawdown {max_dd:.2f}%")

    def _create_sparkline(
        self,
        values: list[float],
        inverted: bool = False
    ) -> str:
        """Create ASCII sparkline from values.

        Normalizes values to 0-8 range and maps to block characters.
        Supports inverted mode for drawdown charts.

        Args:
            values: List of numeric values to plot
            inverted: If True, flip chart (for drawdown)

        Returns:
            ASCII sparkline string using block characters

        Example:
            ```python
            sparkline = self._create_sparkline([1, 2, 3, 4, 5])
            # Returns: "▁▃▅▆█"
            ```
        """
        if not values:
            return ""

        # Normalize to 0-8 range (8 levels of ASCII blocks)
        min_val = min(values)
        max_val = max(values)

        if max_val == min_val:
            # All values are the same, use middle block
            normalized = [4] * len(values)
        else:
            normalized = [
                int((v - min_val) / (max_val - min_val) * 8)
                for v in values
            ]

        if inverted:
            normalized = [8 - n for n in normalized]

        # ASCII block characters (8 levels + space)
        blocks = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

        return "".join(blocks[n] for n in normalized)
