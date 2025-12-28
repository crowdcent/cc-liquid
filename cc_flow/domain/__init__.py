"""
Domain models and types for cc-flow.

This module defines the core domain models, types, and interfaces used
throughout the application. All models use Pydantic v2 for validation
and type safety.

Key Models:
    - Position: Represents a trading position
    - Trade: Represents a trade execution
    - Portfolio: Represents a portfolio state
    - Signal: Represents a trading signal/prediction
    - Account: Represents an exchange account

Design Principles:
    - Use Pydantic BaseModel for all domain models
    - Immutable models where possible (frozen=True)
    - Complete type hints on all fields
    - Validation for business rules
"""

from .account import AccountInfo, PortfolioSnapshot, Position
from .config import (
    DataSourceConfig,
    ExchangeProfile,
    ExecutionConfig,
    PortfolioConfig,
    RebalancingConfig,
    StopLossConfig,
    TradingConfig,
)
from .orders import (
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
    Trade,
)
from .portfolio import ExecutionResult, RebalancePlan, TargetPosition

__all__ = [
    # Account models
    "AccountInfo",
    "Position",
    "PortfolioSnapshot",
    # Order models
    "OrderType",
    "TimeInForce",
    "OrderSide",
    "OrderStatus",
    "OrderRequest",
    "OrderResult",
    "Trade",
    # Portfolio models
    "TargetPosition",
    "RebalancePlan",
    "ExecutionResult",
    # Configuration models
    "DataSourceConfig",
    "StopLossConfig",
    "RebalancingConfig",
    "PortfolioConfig",
    "ExecutionConfig",
    "ExchangeProfile",
    "TradingConfig",
]
