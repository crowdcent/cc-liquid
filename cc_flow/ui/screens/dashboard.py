"""
Dashboard screen for cc-flow TUI.

This module implements the main dashboard screen that displays real-time
portfolio information and automatically refreshes every few seconds.

Components:
    - DashboardScreen: Main screen with account summary and positions

Design Principles:
    - Auto-refresh with set_interval for real-time updates
    - Use @work decorator for async operations
    - DataTable for structured position display
    - Graceful error handling for network failures
    - Type hints throughout
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Static

if TYPE_CHECKING:
    from cc_flow.core.orchestrator import TradingOrchestrator
    from cc_flow.domain.account import PortfolioSnapshot, Position


class DashboardScreen(Screen):
    """
    Live dashboard for portfolio monitoring.

    Displays:
    - Account summary (value, PnL, leverage)
    - Open positions table
    - Next rebalance countdown
    - Open orders count

    Auto-refreshes every 2 seconds.

    Attributes:
        orchestrator: TradingOrchestrator instance for data access
        refresh_interval: Seconds between auto-refresh (default: 2.0)

    Example:
        >>> from cc_flow.ui.screens.dashboard import DashboardScreen
        >>> screen = DashboardScreen(orchestrator)
        >>> app.push_screen(screen)
    """

    def __init__(
        self,
        orchestrator: TradingOrchestrator,
        **kwargs,
    ) -> None:
        """
        Initialize dashboard screen.

        Args:
            orchestrator: TradingOrchestrator instance
            **kwargs: Additional screen arguments
        """
        super().__init__(**kwargs)
        self.orchestrator = orchestrator
        self.refresh_interval = 2.0  # seconds

    def compose(self) -> ComposeResult:
        """
        Create dashboard layout.

        Yields:
            Container with account summary and positions table
        """
        with Container(id="dashboard"):
            with Vertical(classes="panel"):
                yield Static("Account Summary", classes="section-title")
                yield Static("Loading...", id="account-summary")

            with Vertical(classes="panel"):
                yield Static("Open Positions", classes="section-title")
                yield DataTable(id="positions-table")

            with Horizontal(classes="panel"):
                yield Static("Next Rebalance: --", id="next-rebalance")
                yield Static("Open Orders: 0", id="open-orders")

    def on_mount(self) -> None:
        """
        Called when screen is mounted.

        Set up table columns and start auto-refresh.
        """
        # Set up positions table
        table = self.query_one("#positions-table", DataTable)
        table.add_columns("Asset", "Side", "Size", "Entry", "Mark", "PnL", "PnL %")

        # Start auto-refresh
        self.set_interval(self.refresh_interval, self.refresh_data)

        # Initial load
        self.refresh_data()

    @work(exclusive=True)
    async def refresh_data(self) -> None:
        """
        Refresh all dashboard data (worker wrapper).

        This is the public method called by the interval timer.
        It wraps _refresh_data_internal with the @work decorator.
        """
        await self._refresh_data_internal()

    async def _refresh_data_internal(self) -> None:
        """
        Internal refresh logic.

        Fetches:
        - Account state from exchange
        - Open positions
        - Open orders
        - Calculates next rebalance time

        Note:
            This method is separated from refresh_data to allow testing
            without requiring an active Textual app context.
        """
        from cc_flow.utils.logger_config import log

        try:
            # Get account state
            snapshot = await self.orchestrator._get_current_portfolio()

            # Update account summary
            self._update_account_summary(snapshot)

            # Update positions table
            self._update_positions_table(snapshot.positions)

            # Update next rebalance
            self._update_next_rebalance()

            # Update open orders count
            open_orders = await self.orchestrator.exchange.info.get_open_orders(
                self.orchestrator.config.owner_address
            )
            self._update_open_orders(len(open_orders))

        except Exception as e:
            log.error(f"Dashboard refresh failed: {e}")

    def _update_account_summary(self, snapshot: PortfolioSnapshot) -> None:
        """
        Update account summary display.

        Args:
            snapshot: PortfolioSnapshot with account info
        """
        account = snapshot.account

        # Calculate unrealized PnL from positions
        unrealized_pnl = snapshot.total_unrealized_pnl

        summary = (
            f"Account Value: ${account.account_value:,.2f}\n"
            f"Margin Used: ${account.margin_used:,.2f}\n"
            f"Withdrawable: ${account.withdrawable:,.2f}\n"
            f"Unrealized PnL: ${unrealized_pnl:+,.2f}\n"
            f"Leverage: {account.current_leverage:.2f}x"
        )

        summary_widget = self.query_one("#account-summary", Static)
        summary_widget.update(summary)

    def _update_positions_table(self, positions: list[Position]) -> None:
        """
        Update positions table.

        Args:
            positions: List of Position objects
        """
        table = self.query_one("#positions-table", DataTable)
        table.clear()

        for pos in positions:
            side = "LONG" if pos.signed_size > 0 else "SHORT"
            size = abs(pos.signed_size)

            # Calculate PnL percentage
            if pos.signed_size != 0:
                pnl_pct = (
                    pos.unrealized_pnl / abs(pos.signed_size * pos.entry_price)
                ) * 100
            else:
                pnl_pct = Decimal("0")

            table.add_row(
                pos.coin,
                side,
                f"{size:.4f}",
                f"${pos.entry_price:,.2f}",
                f"${pos.mark_price:,.2f}",
                f"${pos.unrealized_pnl:+,.2f}",
                f"{pnl_pct:+.2f}%",
            )

    def _update_next_rebalance(self) -> None:
        """Update next rebalance countdown."""
        # For now, show placeholder
        # Real implementation would track last rebalance and calculate next
        next_rebalance = self.query_one("#next-rebalance", Static)
        next_rebalance.update("Next Rebalance: Manual")

    def _update_open_orders(self, count: int) -> None:
        """
        Update open orders count.

        Args:
            count: Number of open orders
        """
        orders_widget = self.query_one("#open-orders", Static)
        orders_widget.update(f"Open Orders: {count}")
