"""Trade Plan widget for displaying rebalancing plans.

This module provides a reusable widget for displaying trade plans including
executable trades, skipped trades, and comprehensive summary statistics.

Features:
    - Display of executable trades with color-coded buy/sell sides
    - Display of skipped trades with reasons
    - Summary statistics: buy/sell counts, notional values, net exposure, fees
    - Portfolio bias indicators (long/short balanced, etc.)
    - Brutalist design matching cc-flow theme
    - Rich table formatting with proper currency display

Design Philosophy:
    - High information density (Edward Tufte principles)
    - Color-coded visual parsing (green=buy, red=sell)
    - Clear distinction between executable and skipped trades
    - Real-time updates for plan changes

Example:
    >>> widget = TradePlanWidget()
    >>> widget.update_plan(rebalance_plan)
    >>> # Widget displays comprehensive trade plan with summary
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from loguru import logger
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from cc_flow.domain.orders import OrderSide, Trade
from cc_flow.domain.portfolio import RebalancePlan
from cc_flow.ui.widgets.trade_plan_formatters import (
    determine_skip_reason,
    format_currency,
    format_net_exposure,
    format_size,
    format_trade_type,
    get_portfolio_bias_label,
    style_side,
)

# Brutalist color scheme (matching MetricsPanel)
COLOR_CYAN = "#62e4fb"
COLOR_PURPLE = "#4152A8"
COLOR_WHITE = "#ffffff"
COLOR_YELLOW = "#ffaa00"


class TradePlanWidget(Static):
    """Reusable trade plan preview widget.

    A Static widget that displays a comprehensive trade plan including
    executable trades, skipped trades, and detailed summary statistics.

    Features:
        - Color-coded buy (green) and sell (red) sides
        - Summary metrics: trade counts, notional values, net exposure
        - Portfolio bias indicators
        - Estimated fees and costs
        - Clear visual separation of executable vs skipped trades

    Attributes:
        _current_plan: Currently displayed rebalance plan

    Example:
        ```python
        widget = TradePlanWidget()
        widget.update_plan(rebalance_plan)
        ```
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the TradePlanWidget.

        Args:
            **kwargs: Additional keyword arguments passed to Static
        """
        super().__init__(**kwargs)
        self._current_plan: RebalancePlan | None = None

    def update_plan(self, plan: RebalancePlan) -> None:
        """Update widget with new rebalance plan.

        Creates a comprehensive display including:
        - Summary statistics panel
        - Executable trades table
        - Skipped trades table (if any)

        Args:
            plan: RebalancePlan object containing trade details

        Example:
            ```python
            widget.update_plan(rebalance_plan)
            ```
        """
        self._current_plan = plan

        try:
            # Calculate summary statistics
            summary_stats = self._calculate_summary_stats(plan)

            # Build complete display
            display_content = self._build_display(plan, summary_stats)

            # Update the widget
            self.update(display_content)

        except Exception as e:
            logger.error(f"Failed to update trade plan widget: {e}")
            self.update("[red]Error loading trade plan[/red]")

    def _calculate_summary_stats(self, plan: RebalancePlan) -> dict[str, Any]:
        """Calculate summary statistics for the trade plan.

        Computes:
        - Number of buy/sell trades
        - Total buy/sell notional values
        - Net exposure change
        - Total estimated fees
        - Number of skipped trades

        Args:
            plan: RebalancePlan to analyze

        Returns:
            Dictionary with summary statistics

        Example:
            ```python
            stats = widget._calculate_summary_stats(plan)
            print(f"Net exposure: {stats['net_exposure']}")
            ```
        """
        num_buys = 0
        num_sells = 0
        buy_notional = Decimal("0")
        sell_notional = Decimal("0")
        total_fees = Decimal("0")

        for trade in plan.executable_trades:
            # Use limit price if available, otherwise reference price
            price = trade.limit_price if trade.limit_price else trade.reference_price
            notional = abs(trade.size * price)

            if trade.side == OrderSide.BUY:
                num_buys += 1
                buy_notional += notional
            else:  # SELL
                num_sells += 1
                sell_notional += notional

            total_fees += trade.estimated_fee

        net_exposure = buy_notional - sell_notional

        return {
            "num_buys": num_buys,
            "num_sells": num_sells,
            "buy_notional": buy_notional,
            "sell_notional": sell_notional,
            "net_exposure": net_exposure,
            "total_fees": total_fees,
            "num_skipped": len(plan.skipped_trades),
        }

    def _build_display(self, plan: RebalancePlan, stats: dict[str, Any]) -> Panel:
        """Build complete display panel with all sections.

        Args:
            plan: RebalancePlan to display
            stats: Pre-calculated summary statistics

        Returns:
            Rich Panel with complete trade plan display
        """
        # Build summary section
        summary_text = self._build_summary_text(stats)

        # Build executable trades table
        exec_table = self._build_executable_trades_table(plan.executable_trades)

        # Build content sections
        content_parts = [
            Text(summary_text),
            Text(""),  # Blank line
            Text("Executable Trades", style="bold cyan"),
            exec_table,
        ]

        # Add skipped trades table if any
        if plan.skipped_trades:
            skip_table = self._build_skipped_trades_table(plan.skipped_trades)
            content_parts.extend([
                Text(""),  # Blank line
                Text("Skipped Trades", style="bold yellow"),
                skip_table,
            ])

        # Combine all sections using Group
        full_content = Group(*content_parts)

        # Wrap in panel
        return Panel(
            full_content,
            title="[bold cyan]Trade Plan[/bold cyan]",
            border_style=COLOR_CYAN,
            padding=(1, 2),
        )

    def _build_summary_text(self, stats: dict[str, Any]) -> str:
        """Build summary text section.

        Args:
            stats: Pre-calculated summary statistics

        Returns:
            Formatted summary text with Rich markup
        """
        num_buys = stats["num_buys"]
        num_sells = stats["num_sells"]
        buy_notional = stats["buy_notional"]
        sell_notional = stats["sell_notional"]
        net_exposure = stats["net_exposure"]
        total_fees = stats["total_fees"]
        num_skipped = stats["num_skipped"]

        # Portfolio bias label
        bias = get_portfolio_bias_label(num_buys, num_sells)

        # Build summary lines
        summary_lines = [
            "[bold cyan]Summary[/bold cyan]",
            f"Portfolio Bias: [bold]{bias}[/bold]",
            "",
            f"Executable: {num_buys + num_sells} trades ({num_buys} buys, {num_sells} sells)",
        ]

        if num_skipped > 0:
            summary_lines.append(f"Skipped: {num_skipped} trades")

        summary_lines.extend([
            "",
            f"Buy Notional:  {format_currency(buy_notional)}",
            f"Sell Notional: {format_currency(sell_notional)}",
            f"Net Exposure:  {format_net_exposure(net_exposure)}",
            "",
            f"Estimated Fees: {format_currency(total_fees)}",
        ])

        return "\n".join(summary_lines)

    def _build_executable_trades_table(self, trades: list[Trade]) -> Table:
        """Build Rich table for executable trades.

        Args:
            trades: List of executable Trade objects

        Returns:
            Rich Table with formatted trade data
        """
        table = Table.grid(padding=(0, 2))
        table.add_column("Symbol", style=COLOR_CYAN)
        table.add_column("Side", justify="center")
        table.add_column("Type", justify="center", style=COLOR_PURPLE)
        table.add_column("Size", justify="right", style=COLOR_WHITE)
        table.add_column("Price", justify="right", style=COLOR_WHITE)
        table.add_column("Notional", justify="right", style=COLOR_WHITE)

        if not trades:
            table.add_row("No executable trades", "", "", "", "", "")
            return table

        for trade in trades:
            price = trade.limit_price if trade.limit_price else trade.reference_price
            notional = abs(trade.size * price)

            table.add_row(
                trade.coin,
                style_side(trade.side),
                format_trade_type(trade.trade_type),
                format_size(trade.size),
                format_currency(price),
                format_currency(notional),
            )

        return table

    def _build_skipped_trades_table(self, trades: list[Trade]) -> Table:
        """Build Rich table for skipped trades.

        Args:
            trades: List of skipped Trade objects

        Returns:
            Rich Table with skipped trade data and reasons
        """
        table = Table.grid(padding=(0, 2))
        table.add_column("Symbol", style=COLOR_YELLOW)
        table.add_column("Side", justify="center")
        table.add_column("Type", justify="center", style=COLOR_PURPLE)
        table.add_column("Reason", style=COLOR_YELLOW)

        for trade in trades:
            reason = determine_skip_reason(trade)

            table.add_row(
                trade.coin,
                style_side(trade.side),
                format_trade_type(trade.trade_type),
                reason,
            )

        return table
