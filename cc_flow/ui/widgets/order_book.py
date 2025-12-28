"""Order book widget for displaying real-time market depth.

This module provides a reusable widget for displaying order book bids and asks
with cumulative totals and color-coded sides.

Features:
    - Displays bids (green) and asks (red) in separate tables
    - Shows price, size, and cumulative total for each level
    - Limits display to top 10 levels per side
    - Calculates and displays spread between best bid/ask
    - Handles empty order books gracefully
    - Follows brutalist design philosophy (high contrast, functional)

Design Philosophy:
    - High information density (Edward Tufte principles)
    - Stark color contrast for quick visual parsing
    - Real-time updates without flickering
    - Compact layout suitable for sidebar display
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from loguru import logger
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import DataTable, Static

if TYPE_CHECKING:
    from collections.abc import Sequence

# Maximum number of order book levels to display per side
MAX_LEVELS: int = 10


class OrderBookWidget(Container):
    """Order book display widget with real-time updates.

    Displays market depth with bids and asks in a compact, color-coded format.
    Bids are shown in descending price order (highest first), asks in ascending
    price order (lowest first). Each side shows price, size, and cumulative total.

    The widget calculates and displays the spread between the best bid and ask
    prices. Empty order books are handled gracefully with appropriate messaging.

    Attributes:
        spread: Reactive property containing current spread (Decimal or None)
        best_bid: Reactive property containing best bid price (Decimal or None)
        best_ask: Reactive property containing best ask price (Decimal or None)

    Example:
        ```python
        # Create widget
        order_book = OrderBookWidget()

        # Update with market data
        bids = [
            {"price": Decimal("50000.00"), "size": Decimal("0.5")},
            {"price": Decimal("49900.00"), "size": Decimal("1.0")},
        ]
        asks = [
            {"price": Decimal("50100.00"), "size": Decimal("0.3")},
            {"price": Decimal("50200.00"), "size": Decimal("0.8")},
        ]
        order_book.update_book(bids, asks)
        ```

    Design:
        - Bids: Green title, highest price first
        - Asks: Red title, lowest price first
        - Spread: Displayed at top when data available
        - Compact: Max 10 levels per side
    """

    # Reactive properties for real-time updates
    spread: reactive[Decimal | None] = reactive(None)
    best_bid: reactive[Decimal | None] = reactive(None)
    best_ask: reactive[Decimal | None] = reactive(None)

    def compose(self) -> ComposeResult:
        """Compose the widget layout.

        Creates a horizontal layout with bids on the left (green) and asks
        on the right (red). Each side has a title and a DataTable with three
        columns: Price, Size, and Total (cumulative).

        Yields:
            Widget components for order book display
        """
        with Horizontal(classes="panel"):
            with Container(classes="order-book-side"):
                yield Static("Bids", classes="section-title success")
                yield DataTable(id="bids-table", classes="order-book-table")

            with Container(classes="order-book-side"):
                yield Static("Asks", classes="section-title error")
                yield DataTable(id="asks-table", classes="order-book-table")

    def on_mount(self) -> None:
        """Set up tables when widget is mounted.

        Initializes both bids and asks DataTables with three columns:
        - Price: Order price with $ formatting
        - Size: Order size with 4 decimal places
        - Total: Cumulative size with 4 decimal places

        Called automatically by Textual when widget is added to the screen.
        """
        try:
            # Set up bids table
            bids_table = self.query_one("#bids-table", DataTable)
            bids_table.add_columns("Price", "Size", "Total")
            logger.debug("Bids table initialized")

            # Set up asks table
            asks_table = self.query_one("#asks-table", DataTable)
            asks_table.add_columns("Price", "Size", "Total")
            logger.debug("Asks table initialized")

        except Exception as e:
            logger.error(f"Failed to initialize order book tables: {e}")
            raise

    def update_book(
        self,
        bids: Sequence[dict[str, Decimal]],
        asks: Sequence[dict[str, Decimal]],
    ) -> None:
        """Update order book display with new market data.

        Updates both bids and asks tables with the provided data. Bids are
        sorted in descending price order (highest first), asks in ascending
        price order (lowest first). Only the top 10 levels per side are shown.

        Calculates cumulative totals for each level and updates reactive
        properties for spread, best bid, and best ask.

        Args:
            bids: List of bid orders, each with "price" and "size" keys
            asks: List of ask orders, each with "price" and "size" keys

        Example:
            ```python
            bids = [
                {"price": Decimal("50000.00"), "size": Decimal("0.5")},
                {"price": Decimal("49900.00"), "size": Decimal("1.0")},
            ]
            asks = [
                {"price": Decimal("50100.00"), "size": Decimal("0.3")},
            ]
            widget.update_book(bids, asks)
            ```

        Note:
            Empty order books are handled gracefully - tables are cleared
            but no error is raised. Spread is set to None if either side
            is empty.
        """
        try:
            # Update bids table (highest price first)
            self._update_bids_table(bids)

            # Update asks table (lowest price first)
            self._update_asks_table(asks)

            # Update spread and best prices
            self._update_spread(bids, asks)

            logger.debug(
                f"Order book updated: {len(bids)} bids, {len(asks)} asks, "
                f"spread={self.spread}"
            )

        except Exception as e:
            logger.error(f"Failed to update order book: {e}")
            # Don't raise - gracefully handle errors in display

    def _update_bids_table(self, bids: Sequence[dict[str, Decimal]]) -> None:
        """Update bids table with sorted data.

        Args:
            bids: List of bid orders with "price" and "size" keys
        """
        bids_table = self.query_one("#bids-table", DataTable)
        bids_table.clear()

        if not bids:
            return

        # Sort bids descending (highest price first), limit to MAX_LEVELS
        sorted_bids = sorted(bids, key=lambda x: x["price"], reverse=True)[:MAX_LEVELS]

        cumulative = Decimal("0")
        for bid in sorted_bids:
            cumulative += bid["size"]
            bids_table.add_row(
                f"${bid['price']:,.2f}",
                f"{bid['size']:.4f}",
                f"{cumulative:.4f}",
            )

    def _update_asks_table(self, asks: Sequence[dict[str, Decimal]]) -> None:
        """Update asks table with sorted data.

        Args:
            asks: List of ask orders with "price" and "size" keys
        """
        asks_table = self.query_one("#asks-table", DataTable)
        asks_table.clear()

        if not asks:
            return

        # Sort asks ascending (lowest price first), limit to MAX_LEVELS
        sorted_asks = sorted(asks, key=lambda x: x["price"])[:MAX_LEVELS]

        cumulative = Decimal("0")
        for ask in sorted_asks:
            cumulative += ask["size"]
            asks_table.add_row(
                f"${ask['price']:,.2f}",
                f"{ask['size']:.4f}",
                f"{cumulative:.4f}",
            )

    def _update_spread(
        self,
        bids: Sequence[dict[str, Decimal]],
        asks: Sequence[dict[str, Decimal]],
    ) -> None:
        """Update spread and best bid/ask reactive properties.

        Args:
            bids: List of bid orders with "price" key
            asks: List of ask orders with "price" key
        """
        if not bids or not asks:
            self.spread = None
            self.best_bid = None
            self.best_ask = None
            return

        # Find best bid (highest price) and best ask (lowest price)
        self.best_bid = max(bid["price"] for bid in bids)
        self.best_ask = min(ask["price"] for ask in asks)

        # Calculate spread
        self.spread = self.best_ask - self.best_bid

    def get_spread_formatted(self) -> str:
        """Get formatted spread string for display.

        Returns:
            Formatted spread string like "$100.00" or "No spread data"

        Example:
            ```python
            spread_text = widget.get_spread_formatted()
            # Returns: "$100.00" or "No spread data"
            ```
        """
        if self.spread is None:
            return "No spread data"
        return f"${self.spread:,.2f}"

    def get_best_bid_formatted(self) -> str:
        """Get formatted best bid string for display.

        Returns:
            Formatted best bid like "$50,000.00" or "—"

        Example:
            ```python
            best_bid = widget.get_best_bid_formatted()
            # Returns: "$50,000.00" or "—"
            ```
        """
        if self.best_bid is None:
            return "—"
        return f"${self.best_bid:,.2f}"

    def get_best_ask_formatted(self) -> str:
        """Get formatted best ask string for display.

        Returns:
            Formatted best ask like "$50,100.00" or "—"

        Example:
            ```python
            best_ask = widget.get_best_ask_formatted()
            # Returns: "$50,100.00" or "—"
            ```
        """
        if self.best_ask is None:
            return "—"
        return f"${self.best_ask:,.2f}"
