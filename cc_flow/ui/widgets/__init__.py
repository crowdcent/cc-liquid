"""
Reusable Textual widget components for cc-flow.

This module contains custom widget implementations that are used across
multiple screens in the cc-flow TUI application.

Available Widgets:
    - ChartWidget: ASCII/Unicode charts for time series visualization
    - ConfirmModal: Yes/No confirmation dialogs
    - ErrorModal: Error message display with error styling
    - InfoModal: Information message display
    - InputModal: Text input dialog with validation
    - MetricsPanel: Display performance metrics with formatted values
    - MetricsPanelBuilder: Builder pattern for common metric configurations
    - OrderBookWidget: Display real-time order book bids and asks
    - PortfolioTable: Display portfolio positions in tabular format
    - TradePlanWidget: Display trade plans with executable and skipped trades

Backwards Compatibility:
    - ConfirmationModal: Alias for ConfirmModal
    - ResultModal: Alias for InfoModal

Usage:
    >>> from cc_flow.ui.widgets import PortfolioTable, ConfirmModal, InputModal
    >>> portfolio = PortfolioTable()
    >>> result = await self.app.push_screen_wait(
    ...     ConfirmModal("Execute trades?")
    ... )
    >>> symbol = await self.app.push_screen_wait(
    ...     InputModal("Enter symbol:", default_value="BTC-USD")
    ... )
"""

from __future__ import annotations

from cc_flow.ui.widgets.chart import ChartWidget
from cc_flow.ui.widgets.metrics_builder import MetricsPanelBuilder
from cc_flow.ui.widgets.metrics_panel import MetricsPanel
from cc_flow.ui.widgets.modals import (
    ConfirmModal,
    ErrorModal,
    InfoModal,
    InputModal,
)
from cc_flow.ui.widgets.modals_compat import ConfirmationModal, ResultModal
from cc_flow.ui.widgets.order_book import OrderBookWidget
from cc_flow.ui.widgets.portfolio_table import PortfolioTable
from cc_flow.ui.widgets.trade_plan import TradePlanWidget

__all__ = [
    "ChartWidget",
    "ConfirmModal",
    "ConfirmationModal",  # Backwards compatibility
    "ErrorModal",
    "InfoModal",
    "InputModal",
    "MetricsPanel",
    "MetricsPanelBuilder",
    "OrderBookWidget",
    "PortfolioTable",
    "ResultModal",  # Backwards compatibility
    "TradePlanWidget",
]
