"""Reusable modal widgets for cc-flow UI.

This module provides four types of modal dialog components:
- ConfirmModal: Yes/No confirmation dialog
- ErrorModal: Error message display with error styling
- InfoModal: Information message display
- InputModal: Text input dialog with validation

Modals are implemented as ModalScreen widgets that overlay the main screen
and return values when dismissed. They follow the brutalist design philosophy
with stark borders and high contrast.

Example Usage:
    >>> # Confirmation dialog
    >>> result = await self.app.push_screen_wait(
    ...     ConfirmModal("Delete this item?", title="Confirm Deletion")
    ... )
    >>> if result:
    ...     perform_deletion()
    >>>
    >>> # Error display
    >>> await self.app.push_screen_wait(
    ...     ErrorModal("Trade failed", details="Insufficient liquidity")
    ... )
    >>>
    >>> # Info display
    >>> await self.app.push_screen_wait(
    ...     InfoModal("Rebalance complete", title="Success")
    ... )
    >>>
    >>> # Input dialog
    >>> symbol = await self.app.push_screen_wait(
    ...     InputModal("Enter symbol:", default_value="BTC-USD")
    ... )
    >>> if symbol:
    ...     process_symbol(symbol)
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from cc_flow.utils.logger_config import log


class ConfirmModal(ModalScreen[bool]):
    """Yes/No confirmation dialog with brutalist styling.

    This modal presents a message to the user with Yes and No buttons.
    Returns True if user confirms (Yes/Enter), False if they decline (No/Escape).

    Attributes:
        message: The confirmation message to display
        title: The modal title (default: "Confirm")

    Keybindings:
        - Enter: Confirm (returns True)
        - Escape: Cancel (returns False)
        - Tab/Shift+Tab: Navigate between buttons

    Example:
        >>> result = await self.app.push_screen_wait(
        ...     ConfirmModal("Execute 10 trades?", title="Confirm Execution")
        ... )
        >>> if result:
        ...     execute_trades()
    """

    def __init__(self, message: str, title: str = "Confirm", **kwargs) -> None:
        """Initialize confirmation modal.

        Args:
            message: Message to display to user
            title: Modal title (default: "Confirm")
            **kwargs: Additional arguments passed to ModalScreen
        """
        super().__init__(**kwargs)
        self.message = message
        self.title = title
        log.debug(f"ConfirmModal created: {title} - {message}")

    def compose(self) -> ComposeResult:
        """Compose the modal UI.

        Yields:
            Container with title, message, and Yes/No buttons
        """
        with Container(id="confirmation-modal"):
            yield Label(self.title, id="modal-title")
            yield Label(self.message, id="modal-message")
            with Horizontal(id="modal-buttons"):
                yield Button("Yes", id="btn-yes", variant="success")
                yield Button("No", id="btn-no", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button pressed event

        Dismisses modal with True for Yes, False for No.
        """
        if event.button.id == "btn-yes":
            log.debug(f"ConfirmModal: User confirmed - {self.title}")
            self.dismiss(True)
        else:
            log.debug(f"ConfirmModal: User declined - {self.title}")
            self.dismiss(False)

    def on_key(self, event: Key) -> None:
        """Handle keyboard events.

        Args:
            event: The key event

        Escape dismisses with False (cancel).
        """
        if event.key == "escape":
            log.debug(f"ConfirmModal: User cancelled via Escape - {self.title}")
            self.dismiss(False)


class ErrorModal(ModalScreen[None]):
    """Error message display with error styling.

    This modal shows an error message with optional details and an OK button.
    Features stark red border styling to indicate error state.

    Attributes:
        message: Main error message to display
        title: Modal title (default: "Error")
        details: Optional detailed error information

    Keybindings:
        - Enter: Dismiss modal
        - Escape: Dismiss modal

    Example:
        >>> await self.app.push_screen_wait(
        ...     ErrorModal(
        ...         "Trade execution failed",
        ...         details="Insufficient margin available",
        ...         title="Execution Error"
        ...     )
        ... )
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        title: str = "Error",
        **kwargs,
    ) -> None:
        """Initialize error modal.

        Args:
            message: Main error message to display
            details: Optional detailed error information
            title: Modal title (default: "Error")
            **kwargs: Additional arguments passed to ModalScreen
        """
        super().__init__(**kwargs)
        self.message = message
        self.details = details
        self.title = title
        log.error(f"ErrorModal displayed: {title} - {message}")
        if details:
            log.error(f"Error details: {details}")

    def compose(self) -> ComposeResult:
        """Compose the modal UI.

        Yields:
            Container with error-modal class, title, message, optional details,
            and OK button.
        """
        with Container(id="result-modal", classes="error-modal"):
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
        log.debug(f"ErrorModal dismissed - {self.title}")
        self.dismiss()

    def on_key(self, event: Key) -> None:
        """Handle keyboard events.

        Args:
            event: The key event

        Enter or Escape dismisses the modal.
        """
        if event.key in ("enter", "escape"):
            log.debug(f"ErrorModal dismissed via {event.key} - {self.title}")
            self.dismiss()


class InfoModal(ModalScreen[None]):
    """Information message display with success styling.

    This modal shows an informational message with optional details and an OK button.
    Features standard or success styling for positive messages.

    Attributes:
        message: Main information message to display
        title: Modal title (default: "Information")
        details: Optional detailed information

    Keybindings:
        - Enter: Dismiss modal
        - Escape: Dismiss modal

    Example:
        >>> await self.app.push_screen_wait(
        ...     InfoModal(
        ...         "Rebalance complete: 8/10 trades executed",
        ...         details="Portfolio value: $10,000",
        ...         title="Execution Summary"
        ...     )
        ... )
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        title: str = "Information",
        **kwargs,
    ) -> None:
        """Initialize information modal.

        Args:
            message: Main information message to display
            details: Optional detailed information
            title: Modal title (default: "Information")
            **kwargs: Additional arguments passed to ModalScreen
        """
        super().__init__(**kwargs)
        self.message = message
        self.details = details
        self.title = title
        log.info(f"InfoModal displayed: {title} - {message}")

    def compose(self) -> ComposeResult:
        """Compose the modal UI.

        Yields:
            Container with success-modal class, title, message, optional details,
            and OK button.
        """
        with Container(id="result-modal", classes="success-modal"):
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
        log.debug(f"InfoModal dismissed - {self.title}")
        self.dismiss()

    def on_key(self, event: Key) -> None:
        """Handle keyboard events.

        Args:
            event: The key event

        Enter or Escape dismisses the modal.
        """
        if event.key == "escape":
            log.debug(f"InfoModal dismissed via Escape - {self.title}")
            self.dismiss()


class InputModal(ModalScreen[str | None]):
    """Text input dialog with validation support.

    This modal prompts the user for text input with optional default value
    and placeholder. Returns the input string if confirmed, None if cancelled.

    Attributes:
        prompt: The prompt message to display
        title: Modal title (default: "Input")
        default_value: Default value for input field (default: "")
        placeholder: Placeholder text for empty input (default: "")

    Keybindings:
        - Enter: Submit input (returns value)
        - Escape: Cancel (returns None)
        - Tab: Move between input field and buttons

    Example:
        >>> symbol = await self.app.push_screen_wait(
        ...     InputModal(
        ...         "Enter trading symbol:",
        ...         title="Symbol Selection",
        ...         default_value="BTC-USD",
        ...         placeholder="e.g., ETH-USD"
        ...     )
        ... )
        >>> if symbol:
        ...     load_data_for_symbol(symbol)
    """

    def __init__(
        self,
        prompt: str,
        title: str = "Input",
        default_value: str = "",
        placeholder: str = "",
        **kwargs,
    ) -> None:
        """Initialize input modal.

        Args:
            prompt: The prompt message to display
            title: Modal title (default: "Input")
            default_value: Default value for input field (default: "")
            placeholder: Placeholder text for empty input (default: "")
            **kwargs: Additional arguments passed to ModalScreen
        """
        super().__init__(**kwargs)
        self.prompt = prompt
        self.title = title
        self.default_value = default_value
        self.placeholder = placeholder
        log.debug(f"InputModal created: {title} - {prompt}")

    def compose(self) -> ComposeResult:
        """Compose the modal UI.

        Yields:
            Container with title, prompt, input field, and OK/Cancel buttons
        """
        with Container(id="confirmation-modal"):
            yield Label(self.title, id="modal-title")
            yield Label(self.prompt, id="modal-message")
            yield Input(
                value=self.default_value,
                placeholder=self.placeholder,
                id="modal-input",
            )
            with Horizontal(id="modal-buttons"):
                yield Button("OK", id="btn-ok", variant="success")
                yield Button("Cancel", id="btn-cancel", variant="error")

    def on_mount(self) -> None:
        """Called when modal is mounted.

        Sets focus to the input field for immediate typing.
        """
        input_widget = self.query_one("#modal-input", Input)
        input_widget.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button pressed event

        OK button returns input value, Cancel returns None.
        """
        if event.button.id == "btn-ok":
            input_widget = self.query_one("#modal-input", Input)
            value = input_widget.value
            log.debug(f"InputModal: User submitted '{value}' - {self.title}")
            self.dismiss(value)
        else:
            log.debug(f"InputModal: User cancelled - {self.title}")
            self.dismiss(None)

    def on_input_submitted(self, _event: Input.Submitted) -> None:
        """Handle Enter key pressed in input field.

        Args:
            _event: The input submitted event (unused)

        Returns the input value.
        """
        input_widget = self.query_one("#modal-input", Input)
        value = input_widget.value
        log.debug(f"InputModal: User submitted '{value}' via Enter - {self.title}")
        self.dismiss(value)

    def on_key(self, event: Key) -> None:
        """Handle keyboard events.

        Args:
            event: The key event

        Escape dismisses with None (cancel).
        """
        if event.key == "escape":
            log.debug(f"InputModal: User cancelled via Escape - {self.title}")
            self.dismiss(None)
