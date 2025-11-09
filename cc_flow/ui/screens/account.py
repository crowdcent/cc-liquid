"""
Account screen for cc-flow TUI.

This module implements the detailed account screen that displays comprehensive
portfolio metrics, detailed positions breakdown, and margin information with
manual refresh capability.

Components:
    - AccountScreen: Detailed account view with comprehensive metrics

Design Principles:
    - Manual refresh via button (no auto-refresh)
    - Use @work decorator for async operations
    - DataTable with 9 columns for detailed positions
    - Comprehensive margin breakdown with percentages
    - Type hints throughout
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Static

if TYPE_CHECKING:
    from cc_flow.core.orchestrator import TradingOrchestrator
    from cc_flow.domain.account import PortfolioSnapshot, Position


class AccountScreen(Screen):
    """
    Detailed account information screen.

    Displays:
    - Comprehensive account metrics
    - Detailed positions table
    - Margin breakdown with percentages
    - Manual refresh capability

    Attributes:
        orchestrator: TradingOrchestrator instance for data access

    Example:
        >>> from cc_flow.ui.screens.account import AccountScreen
        >>> screen = AccountScreen(orchestrator)
        >>> app.push_screen(screen)
    """

    def __init__(
        self,
        orchestrator: TradingOrchestrator,
        **kwargs,
    ) -> None:
        """
        Initialize account screen.

        Args:
            orchestrator: TradingOrchestrator instance
            **kwargs: Additional screen arguments
        """
        super().__init__(**kwargs)
        self.orchestrator = orchestrator

    def compose(self) -> ComposeResult:
        """
        Create account screen layout.

        Yields:
            Containers with account metrics and positions
        """
        with Container(id="account"):
            # Refresh button
            yield Button("Refresh", id="btn-refresh", variant="primary")

            # Account metrics panel
            with Vertical(classes="panel"):
                yield Static("Account Metrics", classes="section-title")
                yield Static("Loading...", id="account-metrics")

            # Margin breakdown panel
            with Vertical(classes="panel"):
                yield Static("Margin Breakdown", classes="section-title")
                yield Static("Loading...", id="margin-breakdown")

            # Detailed positions table
            with Vertical(classes="panel"):
                yield Static("Position Details", classes="section-title")
                yield DataTable(id="positions-detail-table")

    def on_mount(self) -> None:
        """
        Called when screen is mounted.

        Set up table columns and load initial data.
        """
        table = self.query_one("#positions-detail-table", DataTable)
        table.add_columns(
            "Asset",
            "Side",
            "Size",
            "Entry Price",
            "Mark Price",
            "Liq Price",
            "Unrealized PnL",
            "PnL %",
            "Margin",
        )

        # Load initial data
        self.refresh_account_data()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button clicks.

        Args:
            event: Button press event
        """
        if event.button.id == "btn-refresh":
            self.refresh_account_data()

    @work(exclusive=True)
    async def refresh_account_data(self) -> None:
        """
        Refresh account data from exchange (worker wrapper).

        This is the public method called by the button.
        It wraps _refresh_account_data_internal with the @work decorator.
        """
        await self._refresh_account_data_internal()

    async def _refresh_account_data_internal(self) -> None:
        """
        Internal refresh logic.

        Fetches current portfolio state and updates all displays.
        """
        from cc_flow.utils.logger_config import log

        try:
            # Get portfolio snapshot
            snapshot = await self.orchestrator._get_current_portfolio()

            # Update all sections
            self._update_account_metrics(snapshot)
            self._update_margin_breakdown(snapshot)
            self._update_positions_table(snapshot.positions)

        except Exception as e:
            log.error(f"Account refresh failed: {e}")

    def _update_account_metrics(self, snapshot: PortfolioSnapshot) -> None:
        """
        Update account metrics display.

        Args:
            snapshot: PortfolioSnapshot object
        """
        account = snapshot.account

        # Calculate position counts
        long_count = sum(1 for p in snapshot.positions if p.signed_size > 0)
        short_count = sum(1 for p in snapshot.positions if p.signed_size < 0)

        metrics = (
            f"Account Value:    ${account.account_value:>15,.2f}\n"
            f"Margin Used:      ${account.margin_used:>15,.2f}\n"
            f"Available Margin: ${account.withdrawable:>15,.2f}\n"
            f"Unrealized PnL:   ${snapshot.total_unrealized_pnl:>15,.2f}\n"
            f"Current Leverage: {account.current_leverage:>15.2f}x\n"
            f"\n"
            f"Total Positions:  {len(snapshot.positions):>15}\n"
            f"Long Positions:   {long_count:>15}\n"
            f"Short Positions:  {short_count:>15}"
        )

        metrics_widget = self.query_one("#account-metrics", Static)
        metrics_widget.update(metrics)

    def _update_margin_breakdown(self, snapshot: PortfolioSnapshot) -> None:
        """
        Update margin breakdown display.

        Args:
            snapshot: PortfolioSnapshot object
        """
        account = snapshot.account

        # Calculate percentages
        total = account.account_value
        if total > 0:
            used_pct = (account.margin_used / total) * 100
            avail_pct = (account.withdrawable / total) * 100
        else:
            used_pct = avail_pct = Decimal("0")

        breakdown = (
            f"Total Account Value: ${total:,.2f}\n"
            f"\n"
            f"Margin Used:         ${account.margin_used:>12,.2f}  ({used_pct:>5.1f}%)\n"
            f"Available Margin:    ${account.withdrawable:>12,.2f}  ({avail_pct:>5.1f}%)\n"
            f"\n"
            f"Maintenance Margin:  Information not available\n"
            f"Initial Margin:      Information not available"
        )

        breakdown_widget = self.query_one("#margin-breakdown", Static)
        breakdown_widget.update(breakdown)

    def _update_positions_table(self, positions: list[Position]) -> None:
        """
        Update detailed positions table.

        Args:
            positions: List of Position objects
        """
        table = self.query_one("#positions-detail-table", DataTable)
        table.clear()

        if not positions:
            return

        for pos in positions:
            # Calculate values
            side = "LONG" if pos.signed_size > 0 else "SHORT"
            size = abs(pos.signed_size)

            # PnL percentage
            if pos.signed_size != 0:
                pnl_pct = (
                    pos.unrealized_pnl / abs(pos.signed_size * pos.entry_price)
                ) * 100
            else:
                pnl_pct = Decimal("0")

            # Position margin (notional / leverage implied)
            position_margin = abs(pos.signed_size * pos.mark_price)

            # Liquidation price
            liq_price_str = (
                f"${pos.liquidation_price:,.2f}"
                if pos.liquidation_price
                else "N/A"
            )

            table.add_row(
                pos.coin,
                side,
                f"{size:.4f}",
                f"${pos.entry_price:,.2f}",
                f"${pos.mark_price:,.2f}",
                liq_price_str,
                f"${pos.unrealized_pnl:+,.2f}",
                f"{pnl_pct:+.2f}%",
                f"${position_margin:,.2f}",
            )
