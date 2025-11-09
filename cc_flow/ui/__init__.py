"""
User interface module for cc-flow.

This module contains all Textual-based TUI components including screens,
widgets, and styling.

Architecture:
    - screens: Top-level application screens
    - widgets: Reusable UI components
    - styles: CSS/TCSS styling and themes

Design Philosophy:
    - Brutalist/minimalist aesthetic
    - High-contrast colors (cyan #62e4fb, purple #4152A8, dark #001926)
    - Functional, information-dense interfaces
    - Responsive layouts
    - Keyboard-driven navigation

Key Screens:
    - Dashboard: Main portfolio overview
    - Rebalance: Rebalancing workflow
    - Backtest: Backtesting interface
    - Settings: Configuration management
"""

from cc_flow.ui.app import CCLiquidApp

__all__ = ["CCLiquidApp"]
