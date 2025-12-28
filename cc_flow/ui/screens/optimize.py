"""Optimization screen for parameter grid search.

This module provides the OptimizeScreen class which allows users to:
- Define parameter ranges for optimization
- Select optimization metric
- Run grid search optimization
- View ranked results by performance metric
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import polars as pl
from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label, Select, Static

from cc_flow.ui.screens.optimize_helpers import (
    parse_csv_range,
    run_optimization_mock,
    validate_parameter_ranges,
)
from cc_flow.utils.logger_config import log

if TYPE_CHECKING:
    from cc_flow.orchestrator import Orchestrator


class OptimizeScreen(Screen):
    """Screen for running optimization grid search.

    This screen allows users to define parameter ranges, select an
    optimization metric, and run grid search to find optimal portfolio
    parameters.

    Attributes:
        orchestrator: Reference to the application orchestrator
        optimization_results: DataFrame containing optimization results
    """

    def __init__(self, orchestrator: Orchestrator, **kwargs: Any) -> None:
        """Initialize the optimization screen.

        Args:
            orchestrator: Application orchestrator instance
            **kwargs: Additional keyword arguments for Screen
        """
        super().__init__(**kwargs)
        self.orchestrator = orchestrator
        self.optimization_results: pl.DataFrame | None = None
        # Set screen ID for styling
        if "id" not in kwargs:
            self.id = "optimize"

    def compose(self) -> ComposeResult:
        """Compose the optimization screen layout.

        Yields:
            Screen widgets including parameter inputs, run button,
            status label, and results table
        """
        yield Static("Optimization", classes="screen-title")

        # Parameter range inputs in grid layout
        with Grid(id="param-ranges-grid"):
            yield Label("Num Long Range (CSV):")
            yield Input(
                placeholder="5,10,15",
                id="num-long-range",
                value="5,10,15",
            )

            yield Label("Num Short Range (CSV):")
            yield Input(
                placeholder="5,10,15",
                id="num-short-range",
                value="5,10,15",
            )

            yield Label("Leverage Range (CSV):")
            yield Input(
                placeholder="1.0,1.5,2.0",
                id="leverage-range",
                value="1.0,1.5,2.0",
            )

            yield Label("Rank Power Range (CSV):")
            yield Input(
                placeholder="0.0,0.5,1.0",
                id="rank-power-range",
                value="0.0,0.5,1.0",
            )

        # Metric selector
        with Container(id="metric-container"):
            yield Label("Optimization Metric:")
            yield Select(
                options=[
                    ("Sharpe Ratio", "sharpe_ratio"),
                    ("Sortino Ratio", "sortino_ratio"),
                    ("Calmar Ratio", "calmar_ratio"),
                ],
                value="sharpe_ratio",
                id="metric-select",
            )

        # Run button
        yield Button("Run Optimization", id="run-optimization", variant="primary")

        # Status label
        yield Label("Ready to run optimization", id="optimization-status")

        # Results table
        yield DataTable(id="results-table", zebra_stripes=True)

    def on_mount(self) -> None:
        """Set up the results table columns when screen is mounted."""
        table = self.query_one("#results-table", DataTable)
        table.add_columns(
            "Num Long",
            "Num Short",
            "Leverage",
            "Rank Power",
            "Metric Value",
        )
        log.info("OptimizeScreen mounted and table columns initialized")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button press event
        """
        if event.button.id == "run-optimization":
            log.info("Run optimization button pressed")
            self.action_run_optimization()

    @work(exclusive=True)
    async def action_run_optimization(self) -> None:
        """Run optimization with current parameter ranges.

        This is an async worker that reads parameter ranges, validates them,
        runs optimization, and displays results.
        """
        log.info("Starting optimization process")
        status_label = self.query_one("#optimization-status", Label)

        try:
            # Read and validate parameter ranges
            status_label.update("Reading parameter ranges...")
            param_grid, metric = self._read_parameter_ranges()

            # Validate ranges
            is_valid, error_msg = validate_parameter_ranges(param_grid)
            if not is_valid:
                status_label.update(f"Error: {error_msg}")
                log.error(f"Validation failed: {error_msg}")
                return

            # Calculate total combinations
            total_combinations = 1
            for values in param_grid.values():
                total_combinations *= len(values)

            status_label.update(
                f"Running optimization... 0/{total_combinations} combinations tested"
            )

            # Run optimization (mock for now)
            results = await run_optimization_mock(param_grid, metric)

            # Store results
            self.optimization_results = results

            # Display results
            self._display_results(results, metric)

            log.info("Optimization completed successfully")

        except ValueError as e:
            error_message = f"Error: {e}"
            status_label.update(error_message)
            log.error(f"Optimization error: {e}")
        except Exception as e:
            error_message = "Error: Unexpected error during optimization"
            status_label.update(error_message)
            log.exception(f"Unexpected optimization error: {e}")

    def _read_parameter_ranges(self) -> tuple[dict[str, list], str]:
        """Read parameter ranges from input widgets.

        Returns:
            Tuple of (parameter grid dict, metric name)

        Raises:
            ValueError: If input format is invalid
        """
        num_long_input = self.query_one("#num-long-range", Input)
        num_short_input = self.query_one("#num-short-range", Input)
        leverage_input = self.query_one("#leverage-range", Input)
        rank_power_input = self.query_one("#rank-power-range", Input)
        metric_select = self.query_one("#metric-select", Select)

        param_grid = {
            "num_long": parse_csv_range(num_long_input.value, int),
            "num_short": parse_csv_range(num_short_input.value, int),
            "target_leverage": parse_csv_range(leverage_input.value, float),
            "rank_power": parse_csv_range(rank_power_input.value, float),
        }

        metric = str(metric_select.value)

        log.info(f"Read parameter ranges: {param_grid}, metric: {metric}")
        return param_grid, metric

    def _display_results(self, results: pl.DataFrame, metric: str) -> None:
        """Display optimization results in the table.

        Args:
            results: DataFrame with optimization results
            metric: Name of the optimization metric
        """
        table = self.query_one("#results-table", DataTable)
        status_label = self.query_one("#optimization-status", Label)

        # Clear existing rows
        table.clear()

        # Take top 10 results
        top_results = results.head(10)

        # Add rows to table
        for row in top_results.iter_rows():
            num_long, num_short, leverage, rank_power, metric_value = row
            table.add_row(
                str(num_long),
                str(num_short),
                f"{leverage:.1f}",
                f"{rank_power:.1f}",
                f"{metric_value:.2f}",
            )

        # Update status with best result
        best_value = top_results[metric][0]
        status_label.update(
            f"Complete: Best {metric.replace('_', ' ').title()} = {best_value:.2f}"
        )

        log.info(f"Displayed top {len(top_results)} results in table")
