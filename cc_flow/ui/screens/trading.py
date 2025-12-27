"""Trading screen for manual rebalancing.

This module implements the trading screen where users can manually trigger
portfolio rebalancing. It shows a preview of planned trades and requires
confirmation before execution.

Workflow:
    1. Click "Plan Rebalance" button
    2. View trade plan preview in table
    3. Click "Execute Plan" button (enabled after plan)
    4. Confirm execution in modal
    5. View execution results

Components:
    - TradingScreen: Main screen for trading operations

Design Principles:
    - Use @work decorator for async operations
    - Button state management (disable/enable)
    - DataTable for trades preview
    - Modal confirmation for safety
    - Type hints throughout
    - Error handling for failures
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Static

from cc_flow.ui.screens.trading_modal import ConfirmExecutionModal

if TYPE_CHECKING:
    from cc_flow.core.trader import TradingOrchestrator
    from cc_flow.domain.portfolio import ExecutionResult, RebalancePlan


class TradingScreen(Screen):
    """Trading screen for manual rebalancing.

    This screen provides the interface for manually triggering portfolio
    rebalancing. Users can generate a rebalance plan, review it, and then
    execute it after confirmation.

    Workflow:
        1. Click "Plan Rebalance" to generate plan
        2. Review trades in table
        3. Click "Execute Plan" (enabled after plan created)
        4. Confirm in modal
        5. View execution results

    Attributes:
        orchestrator: TradingOrchestrator instance for trading operations
        current_plan: Currently active RebalancePlan (None if no plan)
        execution_result: Result of last execution (None if not executed)

    Example:
        >>> from cc_flow.ui.screens.trading import TradingScreen
        >>> screen = TradingScreen(orchestrator)
        >>> app.push_screen(screen)
    """

    def __init__(self, orchestrator: TradingOrchestrator, **kwargs) -> None:
        """Initialize trading screen.

        Args:
            orchestrator: TradingOrchestrator instance
            **kwargs: Additional screen arguments
        """
        super().__init__(**kwargs)
        self.orchestrator = orchestrator
        self.current_plan: RebalancePlan | None = None
        self.execution_result: ExecutionResult | None = None

    def compose(self) -> ComposeResult:
        """Create trading screen layout.

        Yields:
            Containers with buttons and trade plan table
        """
        with Container(id="trading"):
            with Horizontal(classes="button-row"):
                yield Button("Plan Rebalance", id="btn-plan", variant="primary")
                yield Button(
                    "Execute Plan", id="btn-execute", variant="success", disabled=True
                )

            with Vertical(classes="panel"):
                yield Static("Trade Plan", classes="section-title")
                yield Static(
                    "Click 'Plan Rebalance' to generate trade plan", id="plan-status"
                )
                yield DataTable(id="trades-table")

            with Vertical(classes="panel", id="results-panel"):
                yield Static("Execution Results", classes="section-title")
                yield Static("No execution yet", id="execution-summary")

    def on_mount(self) -> None:
        """Called when screen is mounted.

        Set up table columns.
        """
        table = self.query_one("#trades-table", DataTable)
        table.add_columns("Asset", "Type", "Side", "Size", "Price", "Notional", "Fee")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks.

        Args:
            event: Button press event
        """
        button_id = event.button.id

        if button_id == "btn-plan":
            self.action_plan_rebalance()
        elif button_id == "btn-execute":
            self.action_execute_plan()

    @work(exclusive=True)
    async def action_plan_rebalance(self) -> None:
        """Generate rebalancing plan (worker wrapper).

        This is the public method called by button press.
        It wraps _perform_plan_rebalance with the @work decorator.
        """
        await self._perform_plan_rebalance()

    async def _perform_plan_rebalance(self) -> None:
        """Generate rebalancing plan (internal implementation).

        Calls orchestrator to create plan and displays results.
        This method is separated for testability.
        """
        from cc_flow.utils.logger_config import log

        # Update status
        status = self.query_one("#plan-status", Static)
        status.update("Planning rebalance...")

        try:
            # Generate plan
            plan = await self.orchestrator.plan_rebalance()
            self.current_plan = plan

            # Update UI
            self._display_trade_plan(plan)

            # Enable execute button
            self._enable_execute_button()

            log.info(f"Plan created: {len(plan.executable_trades)} trades")

        except Exception as e:
            log.error(f"Plan failed: {e}")
            status.update(f"Error: {e}")

    def action_execute_plan(self) -> None:
        """Show confirmation modal before execution."""
        if self.current_plan is None:
            return

        # Show confirmation modal
        self.app.push_screen(ConfirmExecutionModal(self.current_plan), self._on_execute_confirmed)

    async def _on_execute_confirmed(self, confirmed: bool) -> None:
        """Callback after confirmation modal.

        Args:
            confirmed: Whether user confirmed execution
        """
        if not confirmed or self.current_plan is None:
            return

        await self._perform_execute_plan(skip_confirm=True)

    async def _perform_execute_plan(self, skip_confirm: bool = False) -> None:
        """Execute the current plan (internal implementation).

        Args:
            skip_confirm: Skip confirmation modal (for testing)

        This method is separated for testability.
        """
        from cc_flow.utils.logger_config import log

        if self.current_plan is None:
            return

        status = self.query_one("#plan-status", Static)
        status.update("Executing trades...")

        try:
            # Execute plan
            result = await self.orchestrator.execute_plan(
                self.current_plan, skip_confirm=skip_confirm
            )
            self.execution_result = result

            # Display results
            self._display_execution_result(result)

            # Disable execute button (plan is consumed)
            self._disable_execute_button()

            log.info(f"Execution complete: {result.success_rate:.1%} success")

        except Exception as e:
            log.error(f"Execution failed: {e}")
            status.update(f"Error: {e}")

    def _display_trade_plan(self, plan: RebalancePlan) -> None:
        """Display trade plan in table.

        Args:
            plan: RebalancePlan object
        """
        table = self.query_one("#trades-table", DataTable)
        table.clear()

        for trade in plan.executable_trades:
            table.add_row(
                trade.coin,
                trade.trade_type.upper(),
                trade.side.value,
                f"{trade.size:.4f}",
                f"${trade.limit_price:,.2f}" if trade.limit_price else "MARKET",
                f"${abs(trade.size * trade.reference_price):,.2f}",
                f"${trade.estimated_fee:,.2f}",
            )

        # Update status
        status = self.query_one("#plan-status", Static)
        total_notional = sum(
            abs(t.size * t.reference_price) for t in plan.executable_trades
        )
        total_fees = sum(t.estimated_fee for t in plan.executable_trades)
        status.update(
            f"Plan: {len(plan.executable_trades)} trades, "
            f"${total_notional:,.2f} notional, "
            f"${total_fees:,.2f} fees"
        )

    def _display_execution_result(self, result: ExecutionResult) -> None:
        """Display execution results.

        Args:
            result: ExecutionResult object
        """
        summary = self.query_one("#execution-summary", Static)

        success_count = len(result.successful_trades)
        failed_count = len(result.failed_trades)
        success_rate = result.success_rate * 100

        text = (
            f"Executed: {success_count} successful, {failed_count} failed\n"
            f"Success Rate: {success_rate:.1f}%\n"
            f"Stop Losses: {result.stop_losses_applied} applied, "
            f"{result.stop_losses_failed} failed"
        )

        summary.update(text)

    def _enable_execute_button(self) -> None:
        """Enable the execute plan button."""
        execute_btn = self.query_one("#btn-execute", Button)
        execute_btn.disabled = False

    def _disable_execute_button(self) -> None:
        """Disable the execute plan button."""
        execute_btn = self.query_one("#btn-execute", Button)
        execute_btn.disabled = True
