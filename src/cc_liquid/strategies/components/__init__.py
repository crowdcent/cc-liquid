"""Composable strategy components.

This module provides reusable building blocks for creating trading strategies
through composition rather than inheritance.
"""

from .signals import SignalGenerator, TopNSignals, MeanReversionSignals
from .entries import EntryManager, ImmediateEntry, VintageEntry
from .exits import ExitRule, FullRebalanceExit, TimeBasedExit, TakeProfitExit
from .sizing import PositionSizer, RankPowerSizer, EqualWeightSizer
from .state import StateManager, NoOpState, VintageState

__all__ = [
    # Interfaces
    "SignalGenerator",
    "EntryManager",
    "ExitRule",
    "PositionSizer",
    "StateManager",
    # Signal implementations
    "TopNSignals",
    "MeanReversionSignals",
    # Entry implementations
    "ImmediateEntry",
    "VintageEntry",
    # Exit implementations
    "FullRebalanceExit",
    "TimeBasedExit",
    "TakeProfitExit",
    # Sizing implementations
    "RankPowerSizer",
    "EqualWeightSizer",
    # State implementations
    "NoOpState",
    "VintageState",
]
