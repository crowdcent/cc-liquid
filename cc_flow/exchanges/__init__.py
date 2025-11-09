"""
Exchange connector module for cc-flow.

This module provides abstract interfaces and concrete implementations
for interacting with cryptocurrency exchanges.

Architecture:
    - Base exchange interface (Protocol/ABC)
    - Exchange-specific implementations (Hyperliquid, etc.)
    - Mock exchange for testing
    - Unified API for account queries, order execution, and market data

Implementations:
    - Hyperliquid: Primary exchange integration
    - MockExchange: Testing implementation with configurable behavior
    - Future: Binance, ByBit, etc.

Design Patterns:
    - Adapter pattern for exchange-specific APIs
    - Dependency injection for testability
    - Type-safe interfaces using Protocols
"""

from cc_flow.exchanges.base import Exchange, ExchangeInfo, ExchangeTrading
from cc_flow.exchanges.mock import MockExchange

__all__ = ["Exchange", "ExchangeInfo", "ExchangeTrading", "MockExchange"]
