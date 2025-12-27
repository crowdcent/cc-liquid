"""
Mock Exchange Demonstration

This script demonstrates the usage of MockExchange for testing trading logic.
Run with: uv run python cc_flow/exchanges/mock_demo.py
"""

import asyncio
from decimal import Decimal

from cc_flow.domain.account import Position
from cc_flow.domain.orders import OrderRequest, OrderSide, OrderStatus, OrderType
from cc_flow.exchanges.mock import MockExchange


async def demo_basic_usage():
    """Demonstrate basic MockExchange usage."""
    print("=== Basic MockExchange Demo ===\n")

    # Create mock exchange with defaults
    exchange = MockExchange()

    # Query account state
    print("1. Query account state:")
    state = await exchange.info.get_account_state("0x123")
    print(f"   Account value: ${state['account_value']}")
    print(f"   Positions: {len(state['positions'])}\n")

    # Get market prices
    print("2. Get market prices:")
    prices = await exchange.info.get_market_prices(["BTC", "ETH"])
    print(f"   BTC: ${prices['BTC']}")
    print(f"   ETH: ${prices['ETH']}\n")

    # Submit an order
    print("3. Submit buy order:")
    order = OrderRequest(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("0.5"),
        order_type=OrderType.MARKET,
    )
    result = await exchange.trading.submit_order(order)
    print(f"   Status: {result.status}")
    print(f"   Filled size: {result.filled_size}")
    print(f"   Average price: ${result.average_price}")
    print(f"   Total fee: ${result.total_fee}\n")

    # Verify tracking
    print("4. Verify order tracking:")
    print(f"   Submitted orders: {len(exchange.submitted_orders)}")
    print(f"   First order coin: {exchange.submitted_orders[0].coin}\n")


async def demo_custom_configuration():
    """Demonstrate custom configuration."""
    print("=== Custom Configuration Demo ===\n")

    # Create exchange with custom state
    positions = [
        Position(
            coin="BTC",
            side="LONG",
            size=Decimal("2.0"),
            entry_price=Decimal("48000.00"),
            mark_price=Decimal("50000.00"),
            value=Decimal("100000.00"),
            unrealized_pnl=Decimal("4000.00"),
            return_pct=Decimal("0.0417"),
        ),
        Position(
            coin="ETH",
            side="SHORT",
            size=Decimal("50.0"),
            entry_price=Decimal("3200.00"),
            mark_price=Decimal("3000.00"),
            value=Decimal("150000.00"),
            unrealized_pnl=Decimal("10000.00"),
            return_pct=Decimal("0.0625"),
        ),
    ]

    exchange = MockExchange(
        account_value=Decimal("250000.00"),
        positions=positions,
        prices={"BTC": Decimal("50000.00"), "ETH": Decimal("3000.00")},
    )

    print("1. Account state with positions:")
    state = await exchange.info.get_account_state("0x123")
    print(f"   Account value: ${state['account_value']}")
    print(f"   Number of positions: {len(state['positions'])}")
    for pos in state["positions"]:
        print(f"   - {pos['coin']}: {pos['side']} {pos['size']} @ ${pos['entry_price']}\n")


async def demo_fill_behaviors():
    """Demonstrate different fill behaviors."""
    print("=== Fill Behaviors Demo ===\n")

    order = OrderRequest(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("1.0"),
        order_type=OrderType.MARKET,
    )

    # Always fill
    print("1. Always Fill Behavior:")
    exchange_fill = MockExchange(fill_behavior="always_fill")
    result = await exchange_fill.trading.submit_order(order)
    print(f"   Status: {result.status}")
    print(f"   Filled: {result.filled_size is not None}\n")

    # Always fail
    print("2. Always Fail Behavior:")
    exchange_fail = MockExchange(fill_behavior="always_fail")
    result = await exchange_fail.trading.submit_order(order)
    print(f"   Status: {result.status}")
    print(f"   Error: {result.error_message}\n")


async def demo_batch_operations():
    """Demonstrate batch operations."""
    print("=== Batch Operations Demo ===\n")

    exchange = MockExchange()

    # Batch order submission
    print("1. Submit batch of orders:")
    orders = [
        OrderRequest(
            coin="BTC", side=OrderSide.BUY, size=Decimal("0.1"), order_type=OrderType.MARKET
        ),
        OrderRequest(
            coin="ETH", side=OrderSide.BUY, size=Decimal("1.0"), order_type=OrderType.MARKET
        ),
        OrderRequest(
            coin="BTC", side=OrderSide.SELL, size=Decimal("0.05"), order_type=OrderType.MARKET
        ),
    ]

    results = await exchange.trading.submit_batch_orders(orders)
    print(f"   Submitted: {len(orders)} orders")
    print(f"   Successful: {sum(1 for r in results if r.status == OrderStatus.FILLED)}")
    print(f"   Tracked orders: {len(exchange.submitted_orders)}\n")

    # Batch cancellation
    print("2. Cancel batch of orders:")
    order_ids = ["order-1", "order-2", "order-3"]
    cancel_results = await exchange.trading.cancel_batch_orders(order_ids)
    print(f"   Cancelled: {sum(cancel_results)} orders")
    print(f"   Tracked cancellations: {len(exchange.cancelled_orders)}\n")


async def demo_price_calculations():
    """Demonstrate price calculation utilities."""
    print("=== Price Calculations Demo ===\n")

    exchange = MockExchange()

    # Size rounding
    print("1. Size rounding:")
    size = Decimal("1.23456789")
    rounded = exchange.round_size("BTC", size)
    print(f"   Original: {size}")
    print(f"   Rounded: {rounded}\n")

    # Price rounding
    print("2. Price rounding:")
    price = Decimal("50123.456789")
    rounded = exchange.round_price("BTC", price)
    print(f"   Original: {price}")
    print(f"   Rounded: {rounded}\n")

    # Limit price calculation
    print("3. Limit price calculation:")
    ref_price = Decimal("50000.00")
    slippage = Decimal("0.001")  # 0.1%

    buy_limit = exchange.calculate_limit_price("BTC", "buy", ref_price, slippage)
    sell_limit = exchange.calculate_limit_price("BTC", "sell", ref_price, slippage)

    print(f"   Reference price: ${ref_price}")
    print(f"   Slippage tolerance: {float(slippage) * 100}%")
    print(f"   Buy limit: ${buy_limit}")
    print(f"   Sell limit: ${sell_limit}\n")


async def main():
    """Run all demos."""
    await demo_basic_usage()
    await demo_custom_configuration()
    await demo_fill_behaviors()
    await demo_batch_operations()
    await demo_price_calculations()

    print("=== Demo Complete ===")
    print("\nMockExchange provides a complete testing environment for:")
    print("  - Order submission and execution")
    print("  - Account state queries")
    print("  - Market data retrieval")
    print("  - Error handling scenarios")
    print("  - Batch operations")
    print("\nUse it in your tests to validate trading logic without real API calls!")


if __name__ == "__main__":
    asyncio.run(main())
