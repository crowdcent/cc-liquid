"""PortfolioTable widget for displaying trading positions.

This module provides a reusable DataTable widget for displaying
portfolio positions with auto-formatting, color coding, sorting,
and portfolio totals.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from rich.style import Style
from rich.text import Text
from textual.widgets import DataTable

from cc_flow.utils.logger_config import log

if TYPE_CHECKING:
    from cc_flow.domain.account import Position


class PortfolioTable(DataTable):
    """Reusable portfolio positions table.

    A DataTable widget that displays trading positions with automatic
    formatting, color-coded PnL, sortable columns, and totals row.

    Features:
        - Auto-formatted columns (decimals, currency)
        - Color-coded PnL (green for profit, red for loss)
        - Sortable by any column (default: PnL descending)
        - Shows side (LONG/SHORT), size, prices, and PnL
        - Displays total portfolio value in footer
        - Brutalist design with zebra striping
        - Graceful error handling

    Example:
        ```python
        table = PortfolioTable()
        table.update_positions(positions)
        ```

    Attributes:
        zebra_stripes: Enable alternating row colors for brutalist design
        cursor_type: Enable cursor for navigation and sorting
        show_footer: Display footer row with totals
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the PortfolioTable.

        Args:
            **kwargs: Additional keyword arguments passed to DataTable
        """
        super().__init__(**kwargs)
        self._columns_setup = False

        # Enable brutalist design features
        self.zebra_stripes = True
        self.cursor_type = "row"
        self.show_footer = True

        log.debug("PortfolioTable initialized with brutalist styling")

    def _ensure_columns(self) -> None:
        """Ensure columns are set up (lazy initialization)."""
        if not self._columns_setup:
            self.add_columns(
                "Asset",
                "Side",
                "Size",
                "Entry",
                "Mark",
                "PnL",
                "PnL %",
            )
            self._columns_setup = True
            log.debug("PortfolioTable columns configured")

    def _sort_positions_by_pnl(self, positions: list[Position]) -> list[Position]:
        """Sort positions by unrealized PnL descending.

        Args:
            positions: List of positions to sort

        Returns:
            Sorted list with highest PnL first
        """
        try:
            return sorted(
                positions,
                key=lambda p: p.unrealized_pnl,
                reverse=True,
            )
        except Exception as e:
            log.warning(f"Error sorting positions: {e}, returning unsorted")
            return positions

    def _create_styled_pnl_text(self, pnl: Decimal, formatted_str: str) -> Text:
        """Create styled Text object for PnL with color coding.

        Args:
            pnl: Raw PnL value for determining color
            formatted_str: Formatted string to display

        Returns:
            Text object with appropriate styling (green/red/default)
        """
        if pnl > 0:
            return Text(formatted_str, style=Style(color="green", bold=True))
        elif pnl < 0:
            return Text(formatted_str, style=Style(color="red", bold=True))
        else:
            return Text(formatted_str, style=Style(color="white"))

    def update_positions(self, positions: list[Position]) -> None:
        """Update table with new positions.

        Clears existing rows and populates table with provided positions.
        Positions are sorted by PnL descending, formatted, and color-coded.
        A footer row with total PnL is added.

        Args:
            positions: List of Position objects with trading data

        Example:
            ```python
            from cc_flow.domain.account import Position
            from decimal import Decimal

            positions = [
                Position(
                    coin="BTC",
                    side="LONG",
                    size=Decimal("1.5"),
                    entry_price=Decimal("50000"),
                    mark_price=Decimal("52000"),
                    value=Decimal("78000"),
                    unrealized_pnl=Decimal("3000"),
                    return_pct=Decimal("0.04")
                )
            ]
            table.update_positions(positions)
            ```
        """
        try:
            # Ensure columns are set up
            self._ensure_columns()

            # Clear existing data
            self.clear()

            if not positions:
                log.info("No positions to display")
                return

            # Sort positions by PnL (highest first)
            sorted_positions = self._sort_positions_by_pnl(positions)

            # Track totals for footer
            total_pnl = Decimal("0")

            for pos in sorted_positions:
                # Determine side based on position side attribute
                side = pos.side
                size = pos.size

                # Calculate PnL percentage
                if pos.size != 0 and pos.entry_price != 0:
                    position_cost = pos.size * pos.entry_price
                    if position_cost != 0:
                        pnl_pct = (pos.unrealized_pnl / position_cost) * 100
                    else:
                        pnl_pct = Decimal("0")
                else:
                    pnl_pct = Decimal("0")

                # Format values
                asset = pos.coin
                side_str = side
                size_str = f"{size:.4f}"
                entry_str = f"${pos.entry_price:,.2f}"
                mark_str = f"${pos.mark_price:,.2f}"
                pnl_str = f"${pos.unrealized_pnl:+,.2f}"
                pnl_pct_str = f"{pnl_pct:+.2f}%"

                # Create styled PnL text with color coding
                pnl_text = self._create_styled_pnl_text(pos.unrealized_pnl, pnl_str)
                pnl_pct_text = self._create_styled_pnl_text(pos.unrealized_pnl, pnl_pct_str)

                # Add row to table
                self.add_row(
                    asset,
                    side_str,
                    size_str,
                    entry_str,
                    mark_str,
                    pnl_text,
                    pnl_pct_text,
                )

                # Accumulate totals
                total_pnl += pos.unrealized_pnl

            # Add footer row with totals (if show_footer is enabled)
            if self.show_footer and sorted_positions:
                total_pnl_str = f"${total_pnl:+,.2f}"
                total_pnl_text = self._create_styled_pnl_text(total_pnl, total_pnl_str)

                # Add separator row for visual clarity
                self.add_row(
                    Text("TOTAL", style=Style(bold=True)),
                    "",
                    "",
                    "",
                    "",
                    total_pnl_text,
                    "",
                )

            log.info(f"Updated portfolio table with {len(sorted_positions)} positions")

        except Exception as e:
            log.error(f"Error updating portfolio table: {e}")
            # Ensure columns exist even on error
            self._ensure_columns()
