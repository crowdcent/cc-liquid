"""
Demo script showing exchange base interfaces usage.

This example demonstrates:
1. How to use the ExchangeInfo protocol
2. How to use the ExchangeTrading protocol
3. How to implement the Exchange ABC
4. Mock implementations for testing
"""

import asyncio
from decimal import Decimal

from cc_flow.domain.orders import OrderRequest, OrderSide, OrderType


async def main():
    """Demo of exchange base interfaces."""
    # Import mock implementation for demonstration
    from cc_flow.tests.unit.test_exchanges.test_base import MockExchange

    # Create exchange instance
    config = {
        "api_key": "demo_key",
        "endpoint": "https://api.demo.exchange.com",
    }
    exchange = MockExchange(config)

    print("=" * 80)
    print("Exchange Base Interfaces Demo")
    print("=" * 80)

    # 1. Query account information (ExchangeInfo protocol)
    print("\n1. Querying Account Information (ExchangeInfo)")
    print("-" * 80)
    account_state = await exchange.info.get_account_state("0x123456789")
    print(f"Account Owner: {account_state['owner']}")
    print(f"Account Value: ${account_state['margin_summary']['account_value']}")

    # 2. Get market prices
    print("\n2. Getting Market Prices")
    print("-" * 80)
    prices = await exchange.info.get_market_prices(["BTC", "ETH"])
    for coin, price in prices.items():
        print(f"{coin}: ${price:,.2f}")

    # 3. Get exchange metadata
    print("\n3. Getting Exchange Metadata")
    print("-" * 80)
    metadata = await exchange.info.get_exchange_metadata()
    print(f"Available Markets: {', '.join(metadata['markets'])}")
    print(f"BTC Size Decimals: {metadata['size_decimals']['BTC']}")

    # 4. Get fee rates
    print("\n4. Getting Fee Rates")
    print("-" * 80)
    fees = await exchange.info.get_fee_rates("0x123456789")
    print(f"Maker Fee: {fees['maker'] * 100:.3f}%")
    print(f"Taker Fee: {fees['taker'] * 100:.3f}%")

    # 5. Submit an order (ExchangeTrading protocol)
    print("\n5. Submitting Market Order (ExchangeTrading)")
    print("-" * 80)
    order = OrderRequest(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("0.1"),
        order_type=OrderType.MARKET,
        reduce_only=False,
    )
    print(f"Order: {order.side.value} {order.size} {order.coin}")
    result = await exchange.trading.submit_order(order)
    print(f"Status: {result.status.value}")
    print(f"Order ID: {result.order_id}")
    print(f"Filled Size: {result.filled_size}")
    print(f"Average Price: ${result.average_price:,.2f}")
    print(f"Total Fee: ${result.total_fee:,.4f}")

    # 6. Submit batch orders
    print("\n6. Submitting Batch Orders")
    print("-" * 80)
    orders = [
        OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.05"),
            order_type=OrderType.MARKET,
            reduce_only=False,
        ),
        OrderRequest(
            coin="ETH",
            side=OrderSide.BUY,
            size=Decimal("1.0"),
            order_type=OrderType.MARKET,
            reduce_only=False,
        ),
    ]
    results = await exchange.trading.submit_batch_orders(orders)
    print(f"Submitted {len(results)} orders")
    for i, result in enumerate(results, 1):
        print(f"  Order {i}: {result.status.value} - ID: {result.order_id}")

    # 7. Modify an order
    print("\n7. Modifying Order")
    print("-" * 80)
    modified = await exchange.trading.modify_order(
        "order-123", new_size=Decimal("0.2"), new_price=Decimal("51000.00")
    )
    print(f"Modified Order ID: {modified.order_id}")
    print(f"New Status: {modified.status.value}")

    # 8. Cancel orders
    print("\n8. Cancelling Orders")
    print("-" * 80)
    cancelled = await exchange.trading.cancel_order(result.order_id)
    print(f"Order {result.order_id} cancelled: {cancelled}")

    # 9. Parse account state to domain model
    print("\n9. Parsing Account State to Domain Model")
    print("-" * 80)
    snapshot = exchange.parse_account_state(account_state)
    print(f"Account Value: ${snapshot.account.account_value:,.2f}")
    print(f"Margin Used: ${snapshot.account.margin_used:,.2f}")
    print(f"Free Collateral: ${snapshot.account.free_collateral:,.2f}")

    # 10. Exchange helper methods
    print("\n10. Exchange Helper Methods")
    print("-" * 80)

    # Round size
    raw_size = Decimal("0.123456")
    rounded_size = exchange.round_size("BTC", raw_size)
    print(f"BTC Size Rounding: {raw_size} -> {rounded_size}")

    # Round price
    raw_price = Decimal("50123.456")
    rounded_price = exchange.round_price("BTC", raw_price)
    print(f"BTC Price Rounding: {raw_price} -> {rounded_price}")

    # Calculate limit price with slippage
    reference_price = Decimal("50000.00")
    slippage = Decimal("0.001")  # 0.1%
    buy_limit = exchange.calculate_limit_price("BTC", "buy", reference_price, slippage)
    sell_limit = exchange.calculate_limit_price("BTC", "sell", reference_price, slippage)
    print(f"Reference Price: ${reference_price:,.2f}")
    print(f"Buy Limit Price (0.1% slippage): ${buy_limit:,.2f}")
    print(f"Sell Limit Price (0.1% slippage): ${sell_limit:,.2f}")

    print("\n" + "=" * 80)
    print("Demo Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
