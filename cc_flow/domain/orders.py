"""Order domain models for cryptocurrency trading.

This module defines order types, execution results, and trade tracking for
perpetual futures trading on exchanges like Hyperliquid.

Models:
    OrderType: Market or limit order types
    TimeInForce: Order execution timing options
    OrderSide: Buy or sell side
    OrderStatus: Order execution status
    OrderRequest: Immutable order request to exchange
    OrderResult: Result of order execution with status
    Trade: Planned or executed trade with execution tracking
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class OrderType(str, Enum):
    """Order type enumeration.

    Attributes:
        MARKET: Execute immediately at best available price
        LIMIT: Execute at specified price or better
    """
    MARKET = "market"
    LIMIT = "limit"


class TimeInForce(str, Enum):
    """Time in force options for order execution.

    These values match the Hyperliquid API specification.

    Attributes:
        IOC: Immediate or Cancel - fill immediately or cancel
        GTC: Good til Canceled - remain on book until filled or cancelled
        ALO: Add Liquidity Only - only add to order book, never take
    """
    IOC = "Ioc"  # Immediate or Cancel
    GTC = "Gtc"  # Good til Canceled
    ALO = "Alo"  # Add Liquidity Only


class OrderSide(str, Enum):
    """Order side enumeration.

    Attributes:
        BUY: Long position / buy order
        SELL: Short position / sell order
    """
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order execution status.

    Attributes:
        PENDING: Order submitted but not yet processed
        FILLED: Order completely filled
        RESTING: Order on book (for GTC/ALO orders)
        FAILED: Order rejected or failed to execute
        CANCELLED: Order cancelled by user or system
    """
    PENDING = "pending"
    FILLED = "filled"
    RESTING = "resting"  # On book (Gtc/Alo)
    FAILED = "failed"
    CANCELLED = "cancelled"


class OrderRequest(BaseModel):
    """Immutable order request to exchange.

    This model represents the parameters sent to the exchange to create an order.
    Once created, the order request should not be modified (frozen=True).

    Attributes:
        coin: Trading pair symbol (e.g., "BTC", "ETH")
        side: Order side (buy or sell)
        size: Order size in base currency units
        order_type: Market or limit order
        limit_price: Limit price (required for limit orders)
        time_in_force: Order execution timing (default: IOC)
        reduce_only: Only reduce existing position (default: False)
        client_order_id: Optional client-provided order ID for tracking

    Example:
        >>> order = OrderRequest(
        ...     coin="BTC",
        ...     side=OrderSide.BUY,
        ...     size=Decimal("0.1"),
        ...     order_type=OrderType.MARKET
        ... )
    """
    model_config = ConfigDict(frozen=True)

    coin: str
    side: OrderSide
    size: Decimal
    order_type: OrderType

    # Pricing
    limit_price: Decimal | None = None  # Required for limit orders

    # Execution parameters
    time_in_force: TimeInForce = TimeInForce.IOC
    reduce_only: bool = False

    # Metadata
    client_order_id: str | None = None


class OrderResult(BaseModel):
    """Result of order execution.

    This model represents the outcome after submitting an order to the exchange.
    It tracks execution status, fill details, and any error information.

    Attributes:
        order_request: The original order request
        status: Current order status
        filled_size: Actual filled size (for filled orders)
        average_price: Average fill price (for filled orders)
        total_fee: Total fees paid (for filled orders)
        order_id: Internal order ID
        exchange_order_id: Exchange-provided order ID
        submitted_at: Order submission timestamp
        filled_at: Order fill timestamp
        error_message: Error message (for failed orders)

    Properties:
        is_success: True if order was filled or is resting on book

    Example:
        >>> result = OrderResult(
        ...     order_request=order,
        ...     status=OrderStatus.FILLED,
        ...     filled_size=Decimal("0.1"),
        ...     average_price=Decimal("50000.00")
        ... )
        >>> assert result.is_success is True
    """
    model_config = ConfigDict(frozen=False)

    order_request: OrderRequest
    status: OrderStatus

    # Filled order data
    filled_size: Decimal | None = None
    average_price: Decimal | None = None
    total_fee: Decimal | None = None

    # Exchange IDs
    order_id: str | None = None
    exchange_order_id: str | None = None

    # Timestamps
    submitted_at: datetime | None = None
    filled_at: datetime | None = None

    # Error info
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        """Check if order execution was successful.

        Returns:
            True if status is FILLED or RESTING, False otherwise
        """
        return self.status in (OrderStatus.FILLED, OrderStatus.RESTING)


class Trade(BaseModel):
    """Planned or executed trade with execution tracking.

    This model represents a trade that is either planned (before execution)
    or executed (after order submission). It includes position context,
    cost estimates, and execution results.

    Attributes:
        coin: Trading pair symbol
        side: Order side (buy or sell)
        size: Trade size in base currency units
        reference_price: Market price at planning time
        limit_price: Limit price for order (if using limit orders)
        current_value: Current position value (signed, negative for shorts)
        target_value: Target position value (signed, negative for shorts)
        delta_value: Change in position value
        trade_type: Classification of trade (open/close/reduce/increase/flip)
        estimated_fee: Estimated trading fees
        estimated_slippage: Estimated slippage cost
        order_result: Execution result (set after order submission)

    Properties:
        is_executed: True if order has been submitted
        is_successful: True if order was executed successfully

    Trade Types:
        - open: Opening a new position from zero
        - close: Closing an existing position to zero
        - reduce: Reducing position size (same direction)
        - increase: Increasing position size (same direction)
        - flip: Reversing position direction (long to short or vice versa)

    Example:
        >>> trade = Trade(
        ...     coin="BTC",
        ...     side=OrderSide.BUY,
        ...     size=Decimal("0.1"),
        ...     reference_price=Decimal("50000.00"),
        ...     current_value=Decimal("0"),
        ...     target_value=Decimal("5000.00"),
        ...     delta_value=Decimal("5000.00"),
        ...     trade_type="open",
        ...     estimated_fee=Decimal("2.50")
        ... )
        >>> assert trade.is_executed is False
    """
    model_config = ConfigDict(frozen=False)

    coin: str
    side: OrderSide
    size: Decimal

    # Pricing
    reference_price: Decimal  # Market price at planning time
    limit_price: Decimal | None = None

    # Position context
    current_value: Decimal  # Current position value (signed)
    target_value: Decimal   # Target position value (signed)
    delta_value: Decimal    # Change in value

    # Classification
    trade_type: Literal["open", "close", "reduce", "increase", "flip"]

    # Cost estimates
    estimated_fee: Decimal
    estimated_slippage: Decimal | None = None

    # Execution result
    order_result: OrderResult | None = None

    @property
    def is_executed(self) -> bool:
        """Check if trade has been executed.

        Returns:
            True if order_result is set, False otherwise
        """
        return self.order_result is not None

    @property
    def is_successful(self) -> bool:
        """Check if trade execution was successful.

        Returns:
            True if executed and order was successful, False otherwise
        """
        return self.order_result is not None and self.order_result.is_success
