"""Builder for creating common metric configurations.

This module provides convenience methods for building common
metric panel configurations for live trading and backtesting.

Design Principles:
    - Builder pattern for flexible metric creation
    - Separation of concerns from MetricsPanel display logic
    - Type-safe with complete type hints
"""

from __future__ import annotations

from decimal import Decimal

from cc_flow.ui.widgets.metrics_panel import MetricsPanel


class MetricsPanelBuilder:
    """Builder for creating common metric configurations.

    This class provides convenience methods for building common
    metric panel configurations for live trading and backtesting.

    Example:
        ```python
        # For live trading
        builder = MetricsPanelBuilder()
        metrics = builder.build_live_metrics(
            account_value=Decimal("100000.00"),
            total_pnl=Decimal("5000.00"),
            daily_pnl=Decimal("500.00"),
            leverage=Decimal("1.5"),
            max_leverage=Decimal("3.0")
        )
        panel.update_metrics(metrics)

        # For backtest results
        metrics = builder.build_backtest_metrics(
            final_value=Decimal("150000.00"),
            total_return=Decimal("50.00"),
            win_rate=Decimal("65.5"),
            sharpe_ratio=1.85,
            max_drawdown=Decimal("15.5")
        )
        panel.update_metrics(metrics)
        ```

    Attributes:
        panel: MetricsPanel instance for formatting methods
    """

    def __init__(self) -> None:
        """Initialize the builder."""
        self.panel = MetricsPanel()

    def build_live_metrics(
        self,
        account_value: Decimal,
        total_pnl: Decimal,
        daily_pnl: Decimal,
        leverage: Decimal,
        max_leverage: Decimal | None = None,
    ) -> dict[str, str]:
        """Build metrics for live trading display.

        Args:
            account_value: Current account value
            total_pnl: Total unrealized PnL
            daily_pnl: PnL for current day
            leverage: Current leverage
            max_leverage: Optional max leverage to display

        Returns:
            Dictionary of formatted metrics

        Example:
            ```python
            builder = MetricsPanelBuilder()
            metrics = builder.build_live_metrics(
                account_value=Decimal("100000.00"),
                total_pnl=Decimal("5000.00"),
                daily_pnl=Decimal("500.00"),
                leverage=Decimal("1.5"),
                max_leverage=Decimal("3.0")
            )
            # Returns: {
            #     "Account Value": "$100,000.00",
            #     "Total PnL": "[green]+$5,000.00[/green]",
            #     "Daily PnL": "[green]+$500.00[/green]",
            #     "Leverage": "1.50x / 3.00x"
            # }
            ```
        """
        metrics = {
            "Account Value": MetricsPanel.format_currency(account_value),
            "Total PnL": self.panel.format_pnl(total_pnl),
            "Daily PnL": self.panel.format_pnl(daily_pnl),
        }

        if max_leverage:
            leverage_str = (
                f"{MetricsPanel.format_leverage(leverage)} / "
                f"{MetricsPanel.format_leverage(max_leverage)}"
            )
        else:
            leverage_str = MetricsPanel.format_leverage(leverage)

        metrics["Leverage"] = leverage_str

        return metrics

    def build_backtest_metrics(
        self,
        final_value: Decimal,
        total_return: Decimal,
        win_rate: Decimal,
        sharpe_ratio: float,
        max_drawdown: Decimal,
    ) -> dict[str, str]:
        """Build metrics for backtest results display.

        Args:
            final_value: Final portfolio value
            total_return: Total return percentage
            win_rate: Win rate percentage
            sharpe_ratio: Sharpe ratio
            max_drawdown: Maximum drawdown percentage (negative)

        Returns:
            Dictionary of formatted metrics

        Example:
            ```python
            builder = MetricsPanelBuilder()
            metrics = builder.build_backtest_metrics(
                final_value=Decimal("150000.00"),
                total_return=Decimal("50.00"),
                win_rate=Decimal("65.5"),
                sharpe_ratio=1.85,
                max_drawdown=Decimal("-15.5")
            )
            # Returns: {
            #     "Final Value": "$150,000.00",
            #     "Total Return": "[green]+50.00%[/green]",
            #     "Win Rate": "65.50%",
            #     "Sharpe Ratio": "1.85",
            #     "Max Drawdown": "[red]-15.50%[/red]"
            # }
            ```
        """
        return {
            "Final Value": MetricsPanel.format_currency(final_value),
            "Total Return": self.panel.format_pnl_percentage(total_return),
            "Win Rate": MetricsPanel.format_percentage(win_rate),
            "Sharpe Ratio": f"{sharpe_ratio:.2f}",
            "Max Drawdown": self.panel.format_pnl_percentage(max_drawdown),
        }
