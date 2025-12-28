"""Example usage of order domain models.

This script demonstrates how to use the order models for:
1. Creating different order types
2. Order execution flow (OrderRequest → OrderResult)
3. Trade planning and execution
4. Status transitions
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from domain.orders import (
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
    Trade,
)


def example_market_order():
    """Example: Creating and executing a market order."""
    print("=" * 60)
    print("Example 1: Market Order")
    print("=" * 60)

    # Create a market order request
    order_request = OrderRequest(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("0.1"),
        order_type=OrderType.MARKET,
        client_order_id="market-order-001",
    )

    print("\nOrder Request Created:")
    print(f"  Coin: {order_request.coin}")
    print(f"  Side: {order_request.side}")
    print(f"  Size: {order_request.size}")
    print(f"  Type: {order_request.order_type}")
    print(f"  Client ID: {order_request.client_order_id}")

    # Simulate order execution (filled)
    order_result = OrderResult(
        order_request=order_request,
        status=OrderStatus.FILLED,
        filled_size=Decimal("0.1"),
        average_price=Decimal("50123.45"),
        total_fee=Decimal("5.01"),
        order_id="order-12345",
        exchange_order_id="hl-67890",
        submitted_at=datetime(2025, 1, 8, 10, 0, 0, tzinfo=UTC),
        filled_at=datetime(2025, 1, 8, 10, 0, 2, tzinfo=UTC),
    )

    print("\nOrder Result:")
    print(f"  Status: {order_result.status}")
    print(f"  Success: {order_result.is_success}")
    print(f"  Filled Size: {order_result.filled_size}")
    print(f"  Average Price: ${order_result.average_price:,.2f}")
    print(f"  Total Fee: ${order_result.total_fee:.2f}")
    print(f"  Order ID: {order_result.order_id}")
    print(f"  Exchange ID: {order_result.exchange_order_id}")

    # Demonstrate immutability of OrderRequest
    print("\nDemonstrating OrderRequest immutability:")
    try:
        order_request.size = Decimal("0.2")
        print("  ERROR: Should not be able to modify frozen model!")
    except Exception:
        print("  ✓ OrderRequest is immutable (as expected)")


def example_limit_order():
    """Example: Creating a limit order."""
    print("\n" + "=" * 60)
    print("Example 2: Limit Order (Resting on Book)")
    print("=" * 60)

    # Create a limit order request
    order_request = OrderRequest(
        coin="ETH",
        side=OrderSide.SELL,
        size=Decimal("2.5"),
        order_type=OrderType.LIMIT,
        limit_price=Decimal("3100.00"),
        time_in_force=TimeInForce.GTC,  # Good til Canceled
        client_order_id="limit-order-001",
    )

    print("\nLimit Order Request Created:")
    print(f"  Coin: {order_request.coin}")
    print(f"  Side: {order_request.side}")
    print(f"  Size: {order_request.size}")
    print(f"  Limit Price: ${order_request.limit_price:,.2f}")
    print(f"  Time in Force: {order_request.time_in_force}")

    # Order is resting on the book (not yet filled)
    order_result = OrderResult(
        order_request=order_request,
        status=OrderStatus.RESTING,
        order_id="order-54321",
        exchange_order_id="hl-98765",
        submitted_at=datetime(2025, 1, 8, 10, 5, 0, tzinfo=UTC),
    )

    print("\nOrder Result:")
    print(f"  Status: {order_result.status}")
    print(f"  Success: {order_result.is_success}")
    print(f"  Order ID: {order_result.order_id}")
    print("  Note: Order is resting on book, waiting to be filled")


def example_failed_order():
    """Example: Failed order with error message."""
    print("\n" + "=" * 60)
    print("Example 3: Failed Order")
    print("=" * 60)

    # Create an order request
    order_request = OrderRequest(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("10.0"),  # Large size
        order_type=OrderType.MARKET,
    )

    print("\nOrder Request Created:")
    print(f"  Coin: {order_request.coin}")
    print(f"  Side: {order_request.side}")
    print(f"  Size: {order_request.size} (large position)")

    # Order failed due to insufficient margin
    order_result = OrderResult(
        order_request=order_request,
        status=OrderStatus.FAILED,
        error_message="Insufficient margin: required $500,000, available $100,000",
        submitted_at=datetime(2025, 1, 8, 10, 10, 0, tzinfo=UTC),
    )

    print("\nOrder Result:")
    print(f"  Status: {order_result.status}")
    print(f"  Success: {order_result.is_success}")
    print(f"  Error: {order_result.error_message}")


def example_trade_lifecycle():
    """Example: Complete trade lifecycle from planning to execution."""
    print("\n" + "=" * 60)
    print("Example 4: Trade Lifecycle (Open Position)")
    print("=" * 60)

    # Step 1: Plan a trade to open a new position
    trade = Trade(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("0.5"),
        reference_price=Decimal("51000.00"),
        current_value=Decimal("0"),  # No current position
        target_value=Decimal("25500.00"),  # 0.5 * $51,000
        delta_value=Decimal("25500.00"),
        trade_type="open",
        estimated_fee=Decimal("12.75"),  # 0.05% fee
        estimated_slippage=Decimal("25.50"),  # ~0.1% slippage
    )

    print("\nTrade Plan:")
    print(f"  Coin: {trade.coin}")
    print(f"  Type: {trade.trade_type}")
    print(f"  Side: {trade.side}")
    print(f"  Size: {trade.size}")
    print(f"  Reference Price: ${trade.reference_price:,.2f}")
    print(f"  Current Value: ${trade.current_value:,.2f}")
    print(f"  Target Value: ${trade.target_value:,.2f}")
    print(f"  Delta Value: ${trade.delta_value:,.2f}")
    print(f"  Estimated Fee: ${trade.estimated_fee:.2f}")
    print(f"  Estimated Slippage: ${trade.estimated_slippage:.2f}")
    print(f"  Is Executed: {trade.is_executed}")
    print(f"  Is Successful: {trade.is_successful}")

    # Step 2: Create order request from trade plan
    order_request = OrderRequest(
        coin=trade.coin,
        side=trade.side,
        size=trade.size,
        order_type=OrderType.MARKET,
        client_order_id=f"trade-{trade.coin}-001",
    )

    print("\nOrder submitted...")

    # Step 3: Execute order and get result
    order_result = OrderResult(
        order_request=order_request,
        status=OrderStatus.FILLED,
        filled_size=Decimal("0.5"),
        average_price=Decimal("51025.50"),  # Slightly higher due to slippage
        total_fee=Decimal("12.76"),
        order_id="order-99999",
        exchange_order_id="hl-11111",
        submitted_at=datetime(2025, 1, 8, 10, 15, 0, tzinfo=UTC),
        filled_at=datetime(2025, 1, 8, 10, 15, 3, tzinfo=UTC),
    )

    # Step 4: Update trade with execution result
    trade.order_result = order_result

    print("\nTrade Executed:")
    print(f"  Is Executed: {trade.is_executed}")
    print(f"  Is Successful: {trade.is_successful}")
    print(f"  Filled Size: {order_result.filled_size}")
    print(f"  Average Price: ${order_result.average_price:,.2f}")
    print(f"  Actual Fee: ${order_result.total_fee:.2f}")
    print(f"  Actual Slippage: ${(order_result.average_price - trade.reference_price) * trade.size:.2f}")


def example_trade_types():
    """Example: Different trade types."""
    print("\n" + "=" * 60)
    print("Example 5: Different Trade Types")
    print("=" * 60)

    # Close trade: Closing existing long position
    close_trade = Trade(
        coin="ETH",
        side=OrderSide.SELL,
        size=Decimal("5.0"),
        reference_price=Decimal("3000.00"),
        current_value=Decimal("15000.00"),  # Long 5 ETH
        target_value=Decimal("0"),
        delta_value=Decimal("-15000.00"),
        trade_type="close",
        estimated_fee=Decimal("7.50"),
    )

    print("\nClose Trade:")
    print(f"  Type: {close_trade.trade_type}")
    print(f"  Action: Sell {close_trade.size} {close_trade.coin} to close position")
    print(f"  Current: ${close_trade.current_value:,.2f} → Target: ${close_trade.target_value:,.2f}")

    # Reduce trade: Reducing position size
    reduce_trade = Trade(
        coin="BTC",
        side=OrderSide.SELL,
        size=Decimal("0.25"),
        reference_price=Decimal("50000.00"),
        current_value=Decimal("25000.00"),  # Long 0.5 BTC
        target_value=Decimal("12500.00"),  # Long 0.25 BTC
        delta_value=Decimal("-12500.00"),
        trade_type="reduce",
        estimated_fee=Decimal("6.25"),
    )

    print("\nReduce Trade:")
    print(f"  Type: {reduce_trade.trade_type}")
    print(f"  Action: Sell {reduce_trade.size} {reduce_trade.coin} to reduce position")
    print(f"  Current: ${reduce_trade.current_value:,.2f} → Target: ${reduce_trade.target_value:,.2f}")

    # Increase trade: Increasing position size
    increase_trade = Trade(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("0.25"),
        reference_price=Decimal("50000.00"),
        current_value=Decimal("12500.00"),  # Long 0.25 BTC
        target_value=Decimal("25000.00"),  # Long 0.5 BTC
        delta_value=Decimal("12500.00"),
        trade_type="increase",
        estimated_fee=Decimal("6.25"),
    )

    print("\nIncrease Trade:")
    print(f"  Type: {increase_trade.trade_type}")
    print(f"  Action: Buy {increase_trade.size} {increase_trade.coin} to increase position")
    print(f"  Current: ${increase_trade.current_value:,.2f} → Target: ${increase_trade.target_value:,.2f}")

    # Flip trade: Reversing position (long to short)
    flip_trade = Trade(
        coin="ETH",
        side=OrderSide.SELL,
        size=Decimal("4.0"),
        reference_price=Decimal("3000.00"),
        current_value=Decimal("6000.00"),  # Long 2 ETH
        target_value=Decimal("-6000.00"),  # Short 2 ETH
        delta_value=Decimal("-12000.00"),
        trade_type="flip",
        estimated_fee=Decimal("6.00"),
    )

    print("\nFlip Trade:")
    print(f"  Type: {flip_trade.trade_type}")
    print(f"  Action: Sell {flip_trade.size} {flip_trade.coin} to flip from long to short")
    print(f"  Current: ${flip_trade.current_value:,.2f} → Target: ${flip_trade.target_value:,.2f}")


def example_serialization():
    """Example: Serialization and deserialization."""
    print("\n" + "=" * 60)
    print("Example 6: Serialization")
    print("=" * 60)

    # Create a trade with nested OrderResult
    order_request = OrderRequest(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("0.1"),
        order_type=OrderType.MARKET,
    )

    order_result = OrderResult(
        order_request=order_request,
        status=OrderStatus.FILLED,
        filled_size=Decimal("0.1"),
        average_price=Decimal("50000.00"),
        total_fee=Decimal("2.50"),
    )

    trade = Trade(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("0.1"),
        reference_price=Decimal("50000.00"),
        current_value=Decimal("0"),
        target_value=Decimal("5000.00"),
        delta_value=Decimal("5000.00"),
        trade_type="open",
        estimated_fee=Decimal("2.50"),
        order_result=order_result,
    )

    # Serialize to dict
    trade_dict = trade.model_dump()
    print("\nSerialized to dict (model_dump):")
    print(f"  coin: {trade_dict['coin']}")
    print(f"  size type: {type(trade_dict['size'])}")
    print(f"  order_result.status: {trade_dict['order_result']['status']}")

    # Serialize to JSON-compatible dict
    trade_json_dict = trade.model_dump(mode="json")
    print("\nSerialized to JSON dict (model_dump(mode='json')):")
    print(f"  coin: {trade_json_dict['coin']}")
    print(f"  size: {trade_json_dict['size']} (type: {type(trade_json_dict['size'])})")
    print(f"  order_result.status: {trade_json_dict['order_result']['status']}")

    # Serialize to JSON string
    trade_json_str = trade.model_dump_json()
    print("\nSerialized to JSON string (model_dump_json):")
    print(f"  {trade_json_str[:100]}...")

    # Deserialize from dict
    trade2 = Trade(**trade_dict)
    print("\nDeserialized from dict:")
    print(f"  coin: {trade2.coin}")
    print(f"  size: {trade2.size}")
    print(f"  order_result.status: {trade2.order_result.status}")
    print(f"  is_successful: {trade2.is_successful}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("ORDER MODELS EXAMPLES")
    print("=" * 60)

    example_market_order()
    example_limit_order()
    example_failed_order()
    example_trade_lifecycle()
    example_trade_types()
    example_serialization()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
