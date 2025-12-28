"""
Core business logic module for cc-flow.

This module contains the core functionality for portfolio management,
rebalancing logic, and backtesting.

Submodules:
    - portfolio: Portfolio construction and management
    - rebalancer: Rebalancing strategies and execution
    - backtester: Backtesting engine and analytics
    - metrics: Performance metrics and analytics
    - state: State management and event bus
"""

from cc_flow.core.portfolio import PortfolioManager
from cc_flow.core.state import EventBus, StateManager

__all__ = ["PortfolioManager", "StateManager", "EventBus"]
