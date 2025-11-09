"""Backtest screen for cc-flow TUI.

This module implements the backtest screen that allows users to configure
backtest parameters, run historical simulations, and view performance metrics.

Components:
    - BacktestScreen: Main screen with parameter inputs and results display

Design Principles:
    - Grid layout for organized parameter inputs
    - Full parameter validation with clear error messages
    - @work decorator for async backtest execution
    - Type hints throughout
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static

if TYPE_CHECKING:
    from cc_flow.core.orchestrator import TradingOrchestrator
    from cc_flow.domain.backtest import BacktestResult


class BacktestScreen(Screen):
    """
    Backtest screen for historical strategy testing.

    Displays:
    - Parameter input grid (dates, positions, leverage, rebalancing)
    - Run Backtest button
    - Performance metrics (return, Sharpe, Sortino, Calmar, win rate)
    - Risk metrics (drawdown, volatility, turnover)

    Attributes:
        orchestrator: TradingOrchestrator instance for data access
        backtest_result: BacktestResult from last run (or None)

    Example:
        >>> from cc_flow.ui.screens.backtest import BacktestScreen
        >>> screen = BacktestScreen(orchestrator)
        >>> app.push_screen(screen)
    """

    def __init__(
        self,
        orchestrator: TradingOrchestrator,
        **kwargs,
    ) -> None:
        """
        Initialize backtest screen.

        Args:
            orchestrator: TradingOrchestrator instance
            **kwargs: Additional screen arguments
        """
        super().__init__(**kwargs)
        self.orchestrator = orchestrator
        self.backtest_result: BacktestResult | None = None

    def compose(self) -> ComposeResult:
        """
        Create backtest screen layout.

        Yields:
            Container with parameter inputs, run button, and results displays
        """
        with Container(id="backtest"):
            with Vertical(classes="panel"):
                yield Static("Backtest Parameters", classes="section-title")

                with Grid(id="config-grid"):
                    # Start Date
                    yield Label("Start Date (YYYY-MM-DD):")
                    yield Input(
                        value="2024-01-01",
                        id="input-start-date",
                        placeholder="2024-01-01",
                    )

                    # End Date
                    yield Label("End Date (YYYY-MM-DD):")
                    yield Input(
                        value="2024-12-31",
                        id="input-end-date",
                        placeholder="2024-12-31",
                    )

                    # Number of Long Positions
                    yield Label("Number of Long Positions:")
                    yield Input(
                        value="10",
                        id="input-num-long",
                        placeholder="10",
                    )

                    # Number of Short Positions
                    yield Label("Number of Short Positions:")
                    yield Input(
                        value="10",
                        id="input-num-short",
                        placeholder="10",
                    )

                    # Target Leverage
                    yield Label("Target Leverage:")
                    yield Input(
                        value="1.0",
                        id="input-leverage",
                        placeholder="1.0",
                    )

                    # Rebalance Every N Days
                    yield Label("Rebalance Every N Days:")
                    yield Input(
                        value="7",
                        id="input-rebalance-days",
                        placeholder="7",
                    )

            with Horizontal(classes="button-row"):
                yield Button("Run Backtest", variant="success", id="btn-run")

            with Vertical(classes="panel"):
                yield Static("Performance Metrics", classes="section-title")
                yield Static(
                    "No backtest run yet. Configure parameters and click Run Backtest.",
                    id="performance-metrics",
                )

            with Vertical(classes="panel"):
                yield Static("Risk Metrics", classes="section-title")
                yield Static(
                    "No backtest run yet. Configure parameters and click Run Backtest.",
                    id="risk-metrics",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press events.

        Args:
            event: Button pressed event
        """
        if event.button.id == "btn-run":
            self.action_run_backtest()

    @work(exclusive=True)
    async def action_run_backtest(self) -> None:
        """
        Run backtest with current parameters.

        This method:
        1. Reads and validates parameters
        2. Executes backtest (currently mocked)
        3. Displays results or error message
        """
        from cc_flow.utils.logger_config import log

        try:
            # Read and validate parameters
            params = self._read_parameters()

            # Update displays to show we're running
            perf_widget = self.query_one("#performance-metrics", Static)
            perf_widget.update("Running backtest...")

            # Run backtest
            result = await self._run_backtest_internal(params)

            # Store result
            self.backtest_result = result

            # Display results
            self._display_performance_metrics(result)
            self._display_risk_metrics(result)

            log.info("Backtest completed successfully")

        except ValueError as e:
            # Display validation error
            perf_widget = self.query_one("#performance-metrics", Static)
            risk_widget = self.query_one("#risk-metrics", Static)

            error_msg = f"Error: {e}"
            perf_widget.update(error_msg)
            risk_widget.update("")

            log.error(f"Backtest validation failed: {e}")

        except Exception as e:
            # Display unexpected error
            perf_widget = self.query_one("#performance-metrics", Static)
            risk_widget = self.query_one("#risk-metrics", Static)

            error_msg = f"Unexpected error: {e}"
            perf_widget.update(error_msg)
            risk_widget.update("")

            log.error(f"Backtest execution failed: {e}")

    def _read_parameters(self) -> dict:
        """
        Read and validate backtest parameters from input fields.

        Returns:
            Dictionary with validated parameters

        Raises:
            ValueError: If any parameter is invalid

        Example:
            >>> params = screen._read_parameters()
            >>> params['start_date']
            date(2024, 1, 1)
        """
        from cc_flow.ui.screens.backtest_helpers import validate_and_parse_parameters

        # Read raw values
        start_date_str = self.query_one("#input-start-date", Input).value
        end_date_str = self.query_one("#input-end-date", Input).value
        num_long_str = self.query_one("#input-num-long", Input).value
        num_short_str = self.query_one("#input-num-short", Input).value
        leverage_str = self.query_one("#input-leverage", Input).value
        rebalance_days_str = self.query_one("#input-rebalance-days", Input).value

        # Validate and parse
        return validate_and_parse_parameters(
            start_date_str,
            end_date_str,
            num_long_str,
            num_short_str,
            leverage_str,
            rebalance_days_str,
        )

    async def _run_backtest_internal(self, params: dict) -> BacktestResult:
        """
        Execute backtest with given parameters.

        Currently returns mock data. Real integration will come later.

        Args:
            params: Validated parameters dict from _read_parameters

        Returns:
            BacktestResult with performance metrics

        Example:
            >>> result = await screen._run_backtest_internal(params)
            >>> result.total_return
            Decimal('0.15')
        """
        from cc_flow.ui.screens.backtest_helpers import create_mock_backtest_result

        return await create_mock_backtest_result(params)

    def _display_performance_metrics(self, result: BacktestResult) -> None:
        """
        Display performance metrics from backtest result.

        Args:
            result: BacktestResult with metrics to display

        Example:
            >>> screen._display_performance_metrics(result)
            # Updates the performance-metrics widget with formatted text
        """
        from cc_flow.ui.screens.backtest_helpers import format_performance_metrics

        metrics_text = format_performance_metrics(result)
        perf_widget = self.query_one("#performance-metrics", Static)
        perf_widget.update(metrics_text)

    def _display_risk_metrics(self, result: BacktestResult) -> None:
        """
        Display risk metrics from backtest result.

        Args:
            result: BacktestResult with metrics to display

        Example:
            >>> screen._display_risk_metrics(result)
            # Updates the risk-metrics widget with formatted text
        """
        from cc_flow.ui.screens.backtest_helpers import format_risk_metrics

        risk_text = format_risk_metrics(result)
        risk_widget = self.query_one("#risk-metrics", Static)
        risk_widget.update(risk_text)
