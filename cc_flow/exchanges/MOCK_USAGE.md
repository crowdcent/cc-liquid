# MockExchange Usage Guide

Complete guide for using MockExchange in testing and development.

## Overview

`MockExchange` is a full-featured mock implementation of the Exchange protocol designed for testing trading logic without making actual API calls. It supports configurable behaviors, order tracking, and complete protocol compliance.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Configuration](#configuration)
- [Fill Behaviors](#fill-behaviors)
- [Order Tracking](#order-tracking)
- [Testing Patterns](#testing-patterns)
- [Advanced Usage](#advanced-usage)

## Basic Usage

### Simple Mock Exchange

```python
from cc_flow.exchanges import MockExchange
from decimal import Decimal

# Create with defaults
exchange = MockExchange()

# Query account state
state = await exchange.info.get_account_state("0x123")
print(state["account_value"])  # "100000.0"

# Get market prices
prices = await exchange.info.get_market_prices(["BTC", "ETH"])
print(prices["BTC"])  # Decimal("50000.0")
```

### Custom Configuration

```python
from cc_flow.domain.account import Position

# Configure custom state
exchange = MockExchange(
    account_value=Decimal("50000.00"),
    positions=[
        Position(
            coin="BTC",
            side="LONG",
            size=Decimal("1.0"),
            entry_price=Decimal("48000.00"),
            mark_price=Decimal("50000.00"),
            value=Decimal("50000.00"),
            unrealized_pnl=Decimal("2000.00"),
            return_pct=Decimal("0.0417"),
        )
    ],
    prices={
        "BTC": Decimal("50000.00"),
        "ETH": Decimal("3000.00"),
        "SOL": Decimal("100.00"),
    },
)
```

## Configuration

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `dict \| None` | `None` | Configuration dict (passed to base Exchange) |
| `account_value` | `Decimal` | `Decimal("100000.0")` | Mock account value in USD |
| `positions` | `list[Position] \| None` | `[]` | List of open positions |
| `prices` | `dict[str, Decimal] \| None` | `{"BTC": 50000, "ETH": 3000}` | Market prices by coin |
| `fill_behavior` | `Literal["always_fill", "always_fail", "random"]` | `"always_fill"` | How orders should be filled |

### Example with All Parameters

```python
exchange = MockExchange(
    config={"testnet": True},
    account_value=Decimal("25000.00"),
    positions=[],
    prices={"BTC": Decimal("45000.00")},
    fill_behavior="always_fail",
)
```

## Fill Behaviors

MockExchange supports three fill behaviors for testing different scenarios:

### 1. always_fill (Default)

Orders always execute successfully with mock data.

```python
from cc_flow.domain.orders import OrderRequest, OrderSide, OrderType

exchange = MockExchange(fill_behavior="always_fill")

order = OrderRequest(
    coin="BTC",
    side=OrderSide.BUY,
    size=Decimal("0.1"),
    order_type=OrderType.MARKET,
)

result = await exchange.trading.submit_order(order)
assert result.status == OrderStatus.FILLED
assert result.filled_size == order.size
assert result.average_price == exchange.prices["BTC"]
assert result.total_fee is not None  # Calculated as size * price * 0.0005
```

### 2. always_fail

Orders always fail with error message.

```python
exchange = MockExchange(fill_behavior="always_fail")

result = await exchange.trading.submit_order(order)
assert result.status == OrderStatus.FAILED
assert result.error_message == "Mock failure"
assert result.filled_size is None
```

### 3. random

Currently implemented as `always_fill` (can be extended for probabilistic behavior).

```python
exchange = MockExchange(fill_behavior="random")
# Currently behaves same as always_fill
```

## Order Tracking

MockExchange tracks all order operations for verification in tests.

### Submitted Orders

```python
exchange = MockExchange()

order1 = OrderRequest(coin="BTC", side=OrderSide.BUY, size=Decimal("0.1"), order_type=OrderType.MARKET)
order2 = OrderRequest(coin="ETH", side=OrderSide.SELL, size=Decimal("1.0"), order_type=OrderType.MARKET)

await exchange.trading.submit_order(order1)
await exchange.trading.submit_order(order2)

# Verify tracking
assert len(exchange.submitted_orders) == 2
assert exchange.submitted_orders[0] == order1
assert exchange.submitted_orders[1] == order2
```

### Cancelled Orders

```python
exchange = MockExchange()

order_id1 = "order-123"
order_id2 = "order-456"

await exchange.trading.cancel_order(order_id1)
await exchange.trading.cancel_order(order_id2)

# Verify tracking
assert len(exchange.cancelled_orders) == 2
assert exchange.cancelled_orders[0] == order_id1
assert exchange.cancelled_orders[1] == order_id2
```

## Testing Patterns

### Pytest Fixtures

```python
import pytest
from cc_flow.exchanges import MockExchange
from decimal import Decimal

@pytest.fixture
def mock_exchange() -> MockExchange:
    """Create mock exchange for tests."""
    return MockExchange(
        account_value=Decimal("100000.00"),
        prices={"BTC": Decimal("50000.00"), "ETH": Decimal("3000.00")},
    )

@pytest.mark.asyncio
async def test_order_submission(mock_exchange: MockExchange):
    """Test order submission logic."""
    order = OrderRequest(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("0.5"),
        order_type=OrderType.MARKET,
    )

    result = await mock_exchange.trading.submit_order(order)

    assert result.status == OrderStatus.FILLED
    assert len(mock_exchange.submitted_orders) == 1
```

### Testing Portfolio Rebalancing

```python
@pytest.mark.asyncio
async def test_rebalance_logic():
    """Test portfolio rebalancing with mock exchange."""
    # Setup initial positions
    initial_positions = [
        Position(
            coin="BTC",
            side="LONG",
            size=Decimal("1.0"),
            entry_price=Decimal("48000.00"),
            mark_price=Decimal("50000.00"),
            value=Decimal("50000.00"),
            unrealized_pnl=Decimal("2000.00"),
            return_pct=Decimal("0.0417"),
        )
    ]

    exchange = MockExchange(
        account_value=Decimal("75000.00"),
        positions=initial_positions,
        prices={"BTC": Decimal("50000.00"), "ETH": Decimal("3000.00")},
    )

    # Execute rebalance logic
    # ... your rebalancing code ...

    # Verify orders submitted
    assert len(exchange.submitted_orders) > 0

    # Verify order details
    for order in exchange.submitted_orders:
        assert order.coin in ["BTC", "ETH"]
        assert order.size > 0
```

### Testing Error Handling

```python
@pytest.mark.asyncio
async def test_order_failure_handling():
    """Test error handling when orders fail."""
    exchange = MockExchange(fill_behavior="always_fail")

    order = OrderRequest(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("1.0"),
        order_type=OrderType.MARKET,
    )

    result = await exchange.trading.submit_order(order)

    # Verify error handling
    assert result.status == OrderStatus.FAILED
    assert result.error_message is not None

    # Your error handling logic should handle this gracefully
    # ... test your error recovery code ...
```

### Testing Batch Operations

```python
@pytest.mark.asyncio
async def test_batch_order_submission():
    """Test batch order submission."""
    exchange = MockExchange()

    orders = [
        OrderRequest(coin="BTC", side=OrderSide.BUY, size=Decimal("0.1"), order_type=OrderType.MARKET),
        OrderRequest(coin="ETH", side=OrderSide.BUY, size=Decimal("1.0"), order_type=OrderType.MARKET),
        OrderRequest(coin="SOL", side=OrderSide.SELL, size=Decimal("10.0"), order_type=OrderType.MARKET),
    ]

    results = await exchange.trading.submit_batch_orders(orders)

    assert len(results) == 3
    assert all(r.status == OrderStatus.FILLED for r in results)
    assert len(exchange.submitted_orders) == 3
```

## Advanced Usage

### Custom Price Provider

```python
class DynamicMockExchange(MockExchange):
    """Mock exchange with dynamic pricing."""

    def __init__(self, price_function, **kwargs):
        super().__init__(**kwargs)
        self.price_function = price_function

    async def get_market_prices(self, coins: list[str]) -> dict[str, Decimal]:
        """Return dynamic prices."""
        return {coin: self.price_function(coin) for coin in coins}

# Usage
def get_price(coin: str) -> Decimal:
    """Dynamic price based on time or other factors."""
    import random
    base = Decimal("50000" if coin == "BTC" else "3000")
    variation = Decimal(random.uniform(-0.01, 0.01))
    return base * (Decimal("1.0") + variation)

exchange = DynamicMockExchange(price_function=get_price)
```

### Simulating Market Conditions

```python
@pytest.mark.asyncio
async def test_volatile_market():
    """Test trading logic in volatile market."""
    # Simulate high volatility with wide price swings
    exchange = MockExchange(
        prices={
            "BTC": Decimal("45000.00"),  # Down 10% from average
            "ETH": Decimal("3300.00"),   # Up 10% from average
        }
    )

    # Test your trading strategy
    # ... strategy code ...

    # Verify appropriate responses
    assert len(exchange.submitted_orders) > 0
```

### Integration Test Example

```python
@pytest.mark.asyncio
async def test_full_trading_cycle():
    """Test complete trading cycle from query to execution."""
    exchange = MockExchange(
        account_value=Decimal("100000.00"),
        prices={"BTC": Decimal("50000.00")},
    )

    # 1. Query account state
    state = await exchange.info.get_account_state("0x123")
    assert Decimal(state["account_value"]) == Decimal("100000.00")

    # 2. Get market prices
    prices = await exchange.info.get_market_prices(["BTC"])
    assert prices["BTC"] == Decimal("50000.00")

    # 3. Calculate position size
    target_allocation = Decimal("0.5")  # 50% of account
    position_value = Decimal(state["account_value"]) * target_allocation
    position_size = position_value / prices["BTC"]

    # 4. Round to exchange precision
    rounded_size = exchange.round_size("BTC", position_size)

    # 5. Submit order
    order = OrderRequest(
        coin="BTC",
        side=OrderSide.BUY,
        size=rounded_size,
        order_type=OrderType.MARKET,
    )
    result = await exchange.trading.submit_order(order)

    # 6. Verify execution
    assert result.status == OrderStatus.FILLED
    assert result.filled_size == rounded_size
    assert result.average_price == prices["BTC"]
```

## Best Practices

1. **Use Fixtures**: Create reusable pytest fixtures for common exchange configurations
2. **Test Both Success and Failure**: Use `always_fill` and `always_fail` to test both paths
3. **Verify Tracking**: Always check `submitted_orders` and `cancelled_orders` in tests
4. **Realistic Data**: Use realistic account values and prices for meaningful tests
5. **Isolation**: Each test should use a fresh MockExchange instance
6. **Type Safety**: Leverage type hints for better IDE support and error detection

## Common Pitfalls

1. **Reusing Exchange Instances**: Don't share exchange instances between tests
   ```python
   # Bad
   exchange = MockExchange()

   def test_1():
       # Uses shared instance
       pass

   # Good
   @pytest.fixture
   def exchange():
       return MockExchange()
   ```

2. **Ignoring Fill Behavior**: Remember to set appropriate fill behavior for each test scenario
   ```python
   # Test failure case
   exchange = MockExchange(fill_behavior="always_fail")
   ```

3. **Not Checking Tracking**: Verify that orders are being tracked correctly
   ```python
   await exchange.trading.submit_order(order)
   assert len(exchange.submitted_orders) == 1  # Don't forget this!
   ```

## API Reference

### MockExchange

Main mock exchange class implementing Exchange ABC.

**Methods:**
- `info` - Property returning MockExchangeInfo
- `trading` - Property returning MockExchangeTrading
- `parse_account_state(raw_data)` - Parse account state to PortfolioSnapshot
- `round_size(coin, size)` - Round size to 2 decimals
- `round_price(coin, price)` - Round price to 2 decimals
- `calculate_limit_price(coin, side, reference_price, slippage_tolerance)` - Calculate limit price

**Attributes:**
- `account_value` - Mock account value
- `positions` - List of positions
- `prices` - Market prices
- `fill_behavior` - Order fill behavior
- `submitted_orders` - List of submitted OrderRequests
- `cancelled_orders` - List of cancelled order IDs

### MockExchangeInfo

Mock info client implementing ExchangeInfo protocol.

**Methods:**
- `get_account_state(owner, vault)` - Get account state
- `get_open_positions(owner, vault)` - Get open positions
- `get_open_orders(owner)` - Get open orders
- `get_fill_history(owner, start_time, end_time)` - Get fill history
- `get_market_prices(coins)` - Get market prices
- `get_exchange_metadata()` - Get exchange metadata
- `get_fee_rates(owner)` - Get fee rates

### MockExchangeTrading

Mock trading client implementing ExchangeTrading protocol.

**Methods:**
- `submit_order(order)` - Submit single order
- `submit_batch_orders(orders)` - Submit batch of orders
- `cancel_order(order_id)` - Cancel order
- `cancel_batch_orders(order_ids)` - Cancel batch of orders
- `modify_order(order_id, new_size, new_price)` - Modify order

## See Also

- [Exchange Base Documentation](base.py) - Base exchange interfaces
- [Domain Models](../domain/) - Order and account models
- [Testing Guide](../../tests/README.md) - General testing guidelines
