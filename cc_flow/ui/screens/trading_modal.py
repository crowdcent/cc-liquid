"""Confirmation modal for trade execution.

This module provides the confirmation dialog shown before executing a
rebalance plan. It requires explicit user confirmation before submitting
orders to the exchange.

Components:
    - ConfirmExecutionModal: Modal dialog for execution confirmation

Design Principles:
    - Safety-first: Explicit confirmation required
    - Clear messaging: Shows trade count and warning
    - Simple interaction: Yes/No buttons
    - Type hints throughout
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label

if TYPE_CHECKING:
    from cc_flow.domain.portfolio import RebalancePlan


class ConfirmExecutionModal(ModalScreen[bool]):
    """Confirmation modal for trade execution.

    This modal shows a summary of the rebalance plan and requires explicit
    confirmation before executing trades on the exchange.

    Attributes:
        plan: RebalancePlan to display summary

    Returns:
        True if user confirms, False otherwise

    Example:
        >>> modal = ConfirmExecutionModal(plan)
        >>> result = await app.push_screen_wait(modal)
        >>> if result:
        ...     # User confirmed, execute trades
    """

    def __init__(self, plan: RebalancePlan, **kwargs) -> None:
        """Initialize confirmation modal.

        Args:
            plan: RebalancePlan to display summary
            **kwargs: Additional modal arguments
        """
        super().__init__(**kwargs)
        self.plan = plan

    def compose(self) -> ComposeResult:
        """Create modal layout.

        Yields:
            Container with message and yes/no buttons
        """
        with Container(id="confirm-modal"):
            yield Label(
                f"Execute {len(self.plan.executable_trades)} trades?\n"
                f"This will submit orders to the exchange.",
                id="confirm-message",
            )
            with Horizontal(classes="button-row"):
                yield Button("Yes", id="btn-yes", variant="success")
                yield Button("No", id="btn-no", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks.

        Args:
            event: Button press event
        """
        if event.button.id == "btn-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)
