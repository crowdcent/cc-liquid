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


class HelpModal(ModalScreen[None]):
    """Context-aware help dialog with keyboard shortcuts and usage guide.

    This modal displays help information relevant to the current screen,
    including keyboard shortcuts, screen-specific functionality, and
    general usage tips. The content adapts based on which screen is active.

    Attributes:
        current_screen: Name of the currently active screen
        title: Modal title (default: "Help")

    Keybindings:
        - Escape: Dismiss modal
        - Enter: Dismiss modal
        - Arrow keys: Scroll content

    Example:
        >>> await self.app.push_screen_wait(
        ...     HelpModal(current_screen="dashboard")
        ... )
    """

    def __init__(
        self,
        current_screen: str = "dashboard",
        title: str = "Help",
        **kwargs,
    ) -> None:
        """Initialize help modal.

        Args:
            current_screen: Name of currently active screen
            title: Modal title (default: "Help")
            **kwargs: Additional arguments passed to ModalScreen
        """
        super().__init__(**kwargs)
        self.current_screen = current_screen
        self.title = title
        log.debug(f"HelpModal opened for screen: {current_screen}")

    def compose(self) -> ComposeResult:
        """Compose the modal UI.

        Yields:
            Container with help content including keyboard shortcuts,
            screen-specific help, and general tips
        """
        from textual.containers import VerticalScroll

        help_content = self._get_help_content()

        with Container(id="help-modal"):
            yield Label(self.title, id="modal-title")
            with VerticalScroll(id="help-content"):
                yield Label(help_content, markup=True)
            yield Button("Close (Esc)", id="btn-close", variant="primary")

    def _get_help_content(self) -> str:
        """Generate contextual help content based on current screen.

        Returns:
            Formatted help text with markup
        """
        # Global keyboard shortcuts
        global_shortcuts = """[bold cyan]Global Keyboard Shortcuts[/bold cyan]

[yellow]?[/yellow]  Show this help menu
[yellow]q[/yellow]  Quit application
[yellow]d[/yellow]  Dashboard screen
[yellow]t[/yellow]  Trading screen
[yellow]a[/yellow]  Account screen
[yellow]b[/yellow]  Backtest screen
[yellow]o[/yellow]  Optimize screen
[yellow]h[/yellow]  History screen
[yellow]c[/yellow]  Config screen
"""

        # Screen-specific help
        screen_help = self._get_screen_specific_help()

        # General tips
        general_tips = """
[bold cyan]General Tips[/bold cyan]

• Use Tab to navigate between interactive elements
• Press Escape to close modals and return to previous screen
• Most tables support sorting by clicking column headers
• Refresh buttons reload data from the exchange
• All monetary values are in USD unless otherwise noted
"""

        # Combine all sections
        return f"{global_shortcuts}\n{screen_help}\n{general_tips}"

    def _get_screen_specific_help(self) -> str:
        """Get help content specific to the current screen.

        Returns:
            Formatted screen-specific help text
        """
        screen_helps = {
            "dashboard": """[bold cyan]Dashboard Screen[/bold cyan]

[bold]Purpose:[/bold] Real-time portfolio monitoring with auto-refresh

[bold]Features:[/bold]
• Account summary showing value, PnL, and leverage
• Live positions table with entry/mark prices and unrealized PnL
• Next rebalance countdown
• Open orders count
• Auto-refreshes every 2 seconds

[bold]Actions:[/bold]
• View positions sorted by PnL
• Monitor account health in real-time
• Track next scheduled rebalance""",
            "trading": """[bold cyan]Trading Screen[/bold cyan]

[bold]Purpose:[/bold] Manual portfolio rebalancing

[bold]Workflow:[/bold]
1. Click "Plan Rebalance" to generate trade plan
2. Review proposed trades in the table
3. Click "Execute Plan" to confirm
4. View execution results

[bold]Features:[/bold]
• Preview trades before execution
• See estimated fees and notional values
• Confirmation modal for safety
• Detailed execution summary

[bold]Tips:[/bold]
• Always review the trade plan carefully
• Check slippage tolerance in config
• Ensure sufficient margin before executing""",
            "account": """[bold cyan]Account Screen[/bold cyan]

[bold]Purpose:[/bold] Detailed account metrics and positions

[bold]Features:[/bold]
• Comprehensive account metrics
• Margin breakdown with percentages
• Extended positions table with liquidation prices
• Manual refresh capability

[bold]Actions:[/bold]
[yellow]r[/yellow]  Refresh account data
• View detailed margin usage
• Monitor liquidation prices
• Check withdrawable balance""",
            "backtest": """[bold cyan]Backtest Screen[/bold cyan]

[bold]Purpose:[/bold] Historical strategy testing

[bold]Features:[/bold]
• Configure backtest parameters (dates, positions, leverage)
• Run simulations on historical data
• View performance metrics (Sharpe, Sortino, Calmar)
• Risk analysis (drawdown, volatility, turnover)

[bold]Parameters:[/bold]
• Start/End Date: Historical period to test
• Num Long/Short: Number of positions per side
• Target Leverage: Portfolio leverage multiplier
• Rebalance Days: Frequency of rebalancing

[bold]Tips:[/bold]
• Longer periods provide more reliable results
• Beware of overfitting to historical data
• Consider transaction costs in results""",
            "optimize": """[bold cyan]Optimize Screen[/bold cyan]

[bold]Purpose:[/bold] Parameter optimization via grid search

[bold]Features:[/bold]
• Define parameter ranges (CSV format)
• Select optimization metric (Sharpe, Sortino, Calmar)
• Run parallel grid search
• View ranked results

[bold]Parameters:[/bold]
• Num Long/Short Range: e.g., "5,10,15"
• Leverage Range: e.g., "1.0,1.5,2.0"
• Rank Power Range: e.g., "0.0,0.5,1.0"

[bold]Tips:[/bold]
• Start with small ranges to test quickly
• Use out-of-sample data for validation
• Higher Sharpe doesn't always mean better live performance""",
            "history": """[bold cyan]History Screen[/bold cyan]

[bold]Purpose:[/bold] Trade execution history and analysis

[bold]Features:[/bold]
• Filter by date range
• View all historical fills
• Performance summaries
• Trade statistics

[bold]Actions:[/bold]
• Enter start/end dates (YYYY-MM-DD format)
• Click "Refresh" to load filtered history
• Review execution quality and fees
• Export capabilities (if available)

[bold]Tips:[/bold]
• Use date filters to narrow large datasets
• Check execution prices vs. planned prices
• Monitor fee percentages""",
            "config": """[bold cyan]Config Screen[/bold cyan]

[bold]Purpose:[/bold] Configuration viewing and management

[bold]Features:[/bold]
• View current settings across all sections
• Profile information
• Data source configuration
• Portfolio construction settings
• Execution parameters
• Rebalancing schedule
• Risk management (stop loss)

[bold]Actions:[/bold]
[yellow]r[/yellow]  Refresh configuration
• Review current profile
• Check data source settings
• Verify portfolio parameters

[bold]Tips:[/bold]
• Configuration changes may require app restart
• Always backup config before major changes
• Test config changes on testnet first""",
        }

        return screen_helps.get(
            self.current_screen,
            "[bold cyan]Screen Help[/bold cyan]\n\nNo specific help available for this screen.",
        )

    def on_button_pressed(self, _event: Button.Pressed) -> None:
        """Handle Close button press.

        Args:
            _event: The button pressed event (unused)

        Dismisses the modal.
        """
        log.debug(f"HelpModal dismissed for screen: {self.current_screen}")
        self.dismiss()

    def on_key(self, event: Key) -> None:
        """Handle keyboard events.

        Args:
            event: The key event

        Enter or Escape dismisses the modal.
        """
        if event.key in ("enter", "escape"):
            log.debug(f"HelpModal dismissed via {event.key} for screen: {self.current_screen}")
            self.dismiss()
