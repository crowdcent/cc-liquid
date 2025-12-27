"""Trade history screen for viewing past fills."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label, Static

from cc_flow.ui.screens.history_utils import (
    calculate_summary_stats,
    format_summary_text,
)
from cc_flow.utils.logger_config import log

if TYPE_CHECKING:
    from cc_flow.ui.orchestrator import Orchestrator


class HistoryScreen(Screen):
    """Screen for viewing trade execution history."""

    def __init__(self, orchestrator: Orchestrator, **kwargs) -> None:
        """Initialize the history screen.

        Args:
            orchestrator: The orchestrator instance
            **kwargs: Additional keyword arguments for Screen
        """
        super().__init__(**kwargs)
        self.orchestrator = orchestrator
        self.trade_history: list[dict] = []

    def compose(self) -> ComposeResult:
        """Compose the history screen layout.

        Yields:
            Widgets for the history screen
        """
        with Vertical(id="history"):
            # Date filter section
            with Horizontal(id="date-filters"):
                yield Label("Start Date:")
                yield Input(
                    placeholder="YYYY-MM-DD",
                    id="start-date-input",
                )
                yield Label("End Date:")
                yield Input(
                    placeholder="YYYY-MM-DD",
                    id="end-date-input",
                )
                yield Button("Refresh", id="refresh-button", variant="primary")

            # Summary statistics panel
            yield Static("Loading summary...", id="history-summary")

            # Trade history table
            yield Container(
                DataTable(id="history-table"),
            )

    def on_mount(self) -> None:
        """Set up the screen when mounted."""
        # Set up DataTable columns
        table = self.query_one("#history-table", DataTable)
        table.add_columns(
            "Date/Time",
            "Asset",
            "Side",
            "Size",
            "Price",
            "Fee",
            "Status",
        )

        # Load initial history
        self.refresh_history()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button pressed event
        """
        if event.button.id == "refresh-button":
            self.refresh_history()

    @work(exclusive=True)
    async def refresh_history(self) -> None:
        """Refresh trade history from exchange."""
        log.info("Refreshing trade history")

        # Read date filters
        start_date, end_date = self._read_date_filters()

        # Fetch fills from exchange
        fills = await self._fetch_fills(start_date, end_date)

        # Store in instance
        self.trade_history = fills

        # Update UI
        table = self.query_one("#history-table", DataTable)
        self._update_trade_table(table, fills)
        self._update_summary(fills)

    def _read_date_filters(self) -> tuple[date | None, date | None]:
        """Read and parse date filter inputs.

        Returns:
            Tuple of (start_date, end_date), each may be None
        """
        start_input = self.query_one("#start-date-input", Input)
        end_input = self.query_one("#end-date-input", Input)

        start_date = self._parse_date_string(start_input.value)
        end_date = self._parse_date_string(end_input.value)

        return start_date, end_date

    def _parse_date_string(self, date_str: str | None) -> date | None:
        """Parse a date string in YYYY-MM-DD format.

        Args:
            date_str: Date string to parse

        Returns:
            Parsed date object or None if invalid/empty
        """
        if not date_str or not date_str.strip():
            return None

        try:
            return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            log.warning(f"Invalid date format: {date_str}")
            return None

    async def _fetch_fills(
        self, start_date: date | None, end_date: date | None
    ) -> list[dict]:
        """Fetch fill history from exchange.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of fill dictionaries
        """
        try:
            # For now, return mock data
            # In production, would call:
            # self.orchestrator.exchange.info.get_fill_history()
            mock_fills = self._get_mock_fills()

            # Apply date filtering
            if start_date or end_date:
                filtered_fills = []
                for fill in mock_fills:
                    fill_date = fill["timestamp"].date()

                    # Check start date
                    if start_date and fill_date < start_date:
                        continue

                    # Check end date
                    if end_date and fill_date > end_date:
                        continue

                    filtered_fills.append(fill)

                return filtered_fills

            return mock_fills

        except Exception as e:
            log.error(f"Error fetching fills: {e}")
            return []

    def _get_mock_fills(self) -> list[dict]:
        """Get mock fill history data.

        Returns:
            List of mock fill dictionaries
        """
        return [
            {
                "timestamp": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
                "coin": "BTC",
                "side": "BUY",
                "size": Decimal("0.5"),
                "price": Decimal("50000"),
                "fee": Decimal("12.50"),
                "status": "filled",
            },
            {
                "timestamp": datetime(2024, 1, 15, 10, 32, 0, tzinfo=UTC),
                "coin": "ETH",
                "side": "SELL",
                "size": Decimal("10"),
                "price": Decimal("3000"),
                "fee": Decimal("15.00"),
                "status": "filled",
            },
            {
                "timestamp": datetime(2024, 1, 16, 14, 15, 0, tzinfo=UTC),
                "coin": "SOL",
                "side": "BUY",
                "size": Decimal("100"),
                "price": Decimal("100"),
                "fee": Decimal("5.00"),
                "status": "filled",
            },
        ]

    def _update_trade_table(self, table: DataTable, fills: list[dict]) -> None:
        """Update trade history table with fills.

        Args:
            table: DataTable widget to update
            fills: List of fill dictionaries
        """
        # Clear existing rows
        table.clear()

        # Add rows for each fill
        for fill in fills:
            try:
                # Format timestamp
                timestamp_str = fill.get("timestamp", datetime.now(UTC)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                # Get fields with defaults
                coin = str(fill.get("coin", ""))
                side = str(fill.get("side", ""))
                size = str(fill.get("size", "0"))
                price = str(fill.get("price", "0"))
                fee = str(fill.get("fee", "0"))
                status = str(fill.get("status", ""))

                table.add_row(
                    timestamp_str,
                    coin,
                    side,
                    size,
                    price,
                    fee,
                    status,
                )
            except Exception as e:
                log.warning(f"Error adding row to table: {e}")
                continue

    def _update_summary(self, fills: list[dict]) -> None:
        """Update summary statistics panel.

        Args:
            fills: List of fill dictionaries
        """
        stats = calculate_summary_stats(fills)
        summary_text = format_summary_text(stats)
        summary_widget = self.query_one("#history-summary", Static)
        summary_widget.update(summary_text)
