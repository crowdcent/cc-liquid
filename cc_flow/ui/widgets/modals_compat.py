"""Backwards-compatible modal dialogs for cc-flow UI.

This module provides backwards-compatible wrappers for the old modal API
to ensure existing code continues to work while new code can use the
enhanced modal classes.

Classes:
    - ConfirmationModal: Alias for ConfirmModal
    - ResultModal: Backwards-compatible result/info display
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from cc_flow.ui.widgets.modals import ConfirmModal
from cc_flow.utils.logger_config import log

# Alias for backwards compatibility
ConfirmationModal = ConfirmModal


class ResultModal(ModalScreen[None]):
    """Display execution results or informational messages (backwards compatible).

    This is a backwards-compatible wrapper that maintains the old ResultModal API
    while using the same implementation pattern as InfoModal/ErrorModal.

    The old API used (title, message, details, is_success) parameter order,
    while the new API uses (message, details, title) for InfoModal.

    Attributes:
        title: Modal title
        message: Main message to display
        details: Optional detailed information
        is_success: Whether this represents a successful operation

    Example:
        >>> await self.app.push_screen_wait(
        ...     ResultModal(
        ...         "Execution Complete",
        ...         "Trades: 8/10 successful",
        ...         details="2 trades failed due to low liquidity",
        ...         is_success=True
        ...     )
        ... )
    """

    def __init__(
        self,
        title: str,
        message: str,
        details: str | None = None,
        is_success: bool = True,
        **kwargs,
    ) -> None:
        """Initialize result modal.

        Args:
            title: Modal title
            message: Main message to display
            details: Optional detailed information
            is_success: Whether this is a success message (affects styling)
            **kwargs: Additional arguments passed to ModalScreen
        """
        super().__init__(**kwargs)
        self.title = title
        self.message = message
        self.details = details
        self.is_success = is_success
        if is_success:
            log.info(f"ResultModal displayed: {title} - {message}")
        else:
            log.error(f"ResultModal displayed: {title} - {message}")

    def compose(self) -> ComposeResult:
        """Compose the modal UI.

        Yields:
            Container with title, message, optional details, and OK button.
            Container has success-modal or error-modal class based on is_success.
        """
        modal_class = "success-modal" if self.is_success else "error-modal"

        with Container(id="result-modal", classes=modal_class):
            yield Label(self.title, id="modal-title")
            yield Label(self.message, id="modal-message")
            if self.details:
                yield Label(self.details, id="modal-details")
            yield Button("OK", id="btn-ok", variant="primary")

    def on_button_pressed(self, _event: Button.Pressed) -> None:
        """Handle OK button press.

        Args:
            _event: The button pressed event (unused)

        Dismisses the modal.
        """
        log.debug(f"ResultModal dismissed - {self.title}")
        self.dismiss()

    def on_key(self, event: Key) -> None:
        """Handle keyboard events.

        Args:
            event: The key event

        Escape dismisses the modal.
        """
        if event.key == "escape":
            log.debug(f"ResultModal dismissed via Escape - {self.title}")
            self.dismiss()
