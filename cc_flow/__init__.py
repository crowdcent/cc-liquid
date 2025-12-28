"""
cc-flow: Textualize-based TUI for cc-liquid portfolio rebalancing.

This package provides a modern terminal user interface (TUI) for managing
cryptocurrency portfolio rebalancing on Hyperliquid, using predictions from
CrowdCent or Numerai.

Key Features:
    - Real-time portfolio monitoring and rebalancing
    - Multi-exchange support (starting with Hyperliquid)
    - Advanced portfolio construction strategies
    - Comprehensive backtesting capabilities
    - Beautiful terminal UI powered by Textual

Architecture:
    - core: Core business logic (portfolio, rebalancing, backtesting)
    - domain: Domain models and types
    - exchanges: Exchange connectors and adapters
    - data_sources: Prediction data source integrations
    - ui: Textual-based user interface components
    - utils: Shared utilities and helpers
    - config: Configuration management

Version: 0.1.0a1 (Pre-Alpha)

Warning:
    This software controls real financial assets. Use with extreme caution
    and always test on testnet before production use.
"""

__version__ = "0.1.0a1"
__author__ = "cc-liquid contributors"

__all__ = [
    "__version__",
    "__author__",
]
