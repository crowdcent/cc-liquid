"""MetricsPanel widget for displaying key performance metrics.

This module provides a reusable Static-based widget for displaying
key performance metrics in a formatted, color-coded layout suitable
for dashboards and live monitoring.

Features:
    - Displays key metrics: Account Value, PnL, Win Rate, Sharpe Ratio
    - Shows leverage usage (current/max)
    - Color-coded values (green for positive, red for negative)
    - Handles both live and backtest metrics
    - Compact, brutalist design matching theme

Design Philosophy:
    - High information density (Edward Tufte principles)
    - Stark color contrast for quick visual parsing
    - Functional over decorative
    - Real-time updates without flickering
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from loguru import logger
from rich.table import Table
from textual.containers import Grid
from textual.widgets import Static

# Brutalist color scheme
COLOR_CYAN = "#62e4fb"
COLOR_PURPLE = "#4152A8"
COLOR_GREEN = "#00ff00"
COLOR_RED = "#ff0000"
COLOR_YELLOW = "#ffaa00"
COLOR_WHITE = "#ffffff"


class MetricsPanel(Grid):
    """Reusable metrics panel with color-coded display.

    A Grid widget that displays key-value pairs of metrics
    using Rich panels and tables with color-coding for visual clarity.

    Features:
        - Color-coded PnL (green positive, red negative)
        - Auto-formatting helpers for currency, percentage, leverage
        - Dynamic updates via update_metrics
        - Handles missing or error states gracefully
        - Brutalist design theme (high contrast)

    Example:
        ```python
        panel = MetricsPanel()
        panel.update_metrics({
            "Account Value": "$100,000.00",
            "Total PnL": panel.format_pnl(Decimal("5000.00")),
            "Leverage": "1.5x / 3.0x",
            "Win Rate": "65.50%"
        })
        ```

    Attributes:
        metrics: Dictionary of current metrics {label: value}
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the MetricsPanel.

        Args:
            **kwargs: Additional keyword arguments passed to Grid
        """
        super().__init__(**kwargs)
        self.metrics: dict[str, str] = {}
        self._widgets: list[Static] = []

    def update_metrics(self, metrics: dict[str, str]) -> None:
        """Update metrics display.

        Creates individual Static widgets for each label-value pair
        arranged in a grid layout.

        Args:
            metrics: Dictionary of {label: formatted_value} pairs

        Example:
            ```python
            panel.update_metrics({
                "Account Value": "$100,000.00",
                "Total PnL": panel.format_pnl(Decimal("5000.00")),
                "Daily PnL": panel.format_pnl(Decimal("-500.00")),
                "Leverage": "1.5x / 3.0x",
                "Win Rate": "65.50%",
                "Sharpe Ratio": "1.85"
            })
            ```
        """
        self.metrics = metrics

        try:
            # Clear existing widgets
            self._widgets.clear()

            # Create Static widgets for each label-value pair
            for label, value in metrics.items():
                # Label widget (cyan, right-aligned)
                label_widget = Static(
                    f"[{COLOR_CYAN}]{label}:[/{COLOR_CYAN}]",
                    classes="metric-label"
                )

                # Value widget (white, left-aligned)
                value_widget = Static(
                    f"[{COLOR_WHITE}]{value}[/{COLOR_WHITE}]",
                    classes="metric-value"
                )

                self._widgets.extend([label_widget, value_widget])

            # If we're mounted, update the children
            if self.is_mounted:
                # Remove existing children
                for child in list(self.children):
                    child.remove()

                # Mount new widgets
                if self._widgets:
                    self.mount(*self._widgets)

        except Exception as e:
            logger.error(f"Failed to update metrics panel: {e}")

    @property
    def children(self):
        """Override children property to return _widgets when not mounted."""
        if self.is_mounted:
            return super().children
        # Return _widgets as a simple iterable when not mounted (for testing)
        return self._widgets

    def _create_metrics_table(self, metrics: dict[str, str]) -> Table:
        """Create Rich table from metrics dict.

        Args:
            metrics: Dictionary of {label: value} pairs

        Returns:
            Rich Table with formatted metrics

        Note:
            Labels are right-aligned in cyan, values are left-aligned
            in white (or pre-colored by format methods).
        """
        table = Table.grid(padding=(0, 2))
        table.add_column(justify="right", style=COLOR_CYAN)
        table.add_column(justify="left", style=COLOR_WHITE)

        if not metrics:
            table.add_row("No data", "—")
            return table

        for label, value in metrics.items():
            # Value may contain Rich markup from format_pnl, etc.
            table.add_row(f"{label}:", value)

        return table

    @staticmethod
    def format_currency(value: Decimal) -> str:
        """Format decimal as currency with $ and commas.

        Args:
            value: Decimal value to format

        Returns:
            Formatted string like "$1,234.56" or "$-1,234.56"

        Example:
            ```python
            formatted = MetricsPanel.format_currency(Decimal("100000.50"))
            # Returns: "$100,000.50"
            ```
        """
        return f"${value:,.2f}"

    @staticmethod
    def format_percentage(value: Decimal) -> str:
        """Format decimal as percentage.

        Args:
            value: Decimal value to format (e.g., 15.5 for 15.5%)

        Returns:
            Formatted string like "15.50%" or "-5.25%"

        Example:
            ```python
            formatted = MetricsPanel.format_percentage(Decimal("15.5"))
            # Returns: "15.50%"
            ```
        """
        return f"{value:.2f}%"

    @staticmethod
    def format_leverage(value: Decimal) -> str:
        """Format leverage value.

        Args:
            value: Decimal leverage value (e.g., 1.5)

        Returns:
            Formatted string like "1.50x"

        Example:
            ```python
            formatted = MetricsPanel.format_leverage(Decimal("1.5"))
            # Returns: "1.50x"
            ```
        """
        return f"{value:.2f}x"

    def format_pnl(self, value: Decimal) -> str:
        """Format PnL with color-coding.

        Positive values are green with + sign.
        Negative values are red with - sign.
        Zero is neutral white.

        Args:
            value: Decimal PnL value

        Returns:
            Rich markup string with color-coded value

        Example:
            ```python
            panel = MetricsPanel()
            formatted = panel.format_pnl(Decimal("5000.00"))
            # Returns: "[green]+$5,000.00[/green]"
            ```
        """
        if value > 0:
            return f"[green]+${value:,.2f}[/green]"
        elif value < 0:
            return f"[red]-${abs(value):,.2f}[/red]"
        else:
            return f"${value:,.2f}"

    def format_pnl_percentage(self, value: Decimal) -> str:
        """Format PnL percentage with color-coding.

        Positive values are green with + sign.
        Negative values are red with - sign.
        Zero is neutral white.

        Args:
            value: Decimal percentage value (e.g., 15.5 for +15.5%)

        Returns:
            Rich markup string with color-coded percentage

        Example:
            ```python
            panel = MetricsPanel()
            formatted = panel.format_pnl_percentage(Decimal("15.5"))
            # Returns: "[green]+15.50%[/green]"
            ```
        """
        if value > 0:
            return f"[green]+{value:.2f}%[/green]"
        elif value < 0:
            return f"[red]{value:.2f}%[/red]"
        else:
            return f"{value:.2f}%"
