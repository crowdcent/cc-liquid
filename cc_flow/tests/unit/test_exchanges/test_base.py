"""
Tests for exchange base interfaces.

This test module verifies:
1. ExchangeInfo Protocol compliance
2. ExchangeTrading Protocol compliance
3. Exchange ABC abstract method enforcement
4. Mock implementations for testing
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from cc_flow.domain.account import (
    AccountInfo,
    PortfolioSnapshot,
)
from cc_flow.domain.orders import OrderRequest, OrderResult, OrderSide, OrderStatus, OrderType
from cc_flow.exchanges.base import Exchange, ExchangeInfo, ExchangeTrading

if TYPE_CHECKING:
    pass


# ============================================================================
# Mock Implementations for Testing
# ============================================================================


class MockExchangeInfo:
    """Mock implementation of ExchangeInfo protocol for testing."""

    async def get_account_state(self, owner: str, vault: str | None = None) -> dict:
        """Get raw account state from exchange."""
        return {
            "owner": owner,
            "vault": vault,
            "margin_summary": {
                "account_value": "10000.00",
                "total_margin_used": "2000.00",
                "total_ntl_pos": "8000.00",
            },
            "cross_margin_summary": {
                "account_value": "10000.00",
                "total_margin_used": "2000.00",
                "total_ntl_pos": "8000.00",
            },
        }

    async def get_open_positions(self, owner: str, vault: str | None = None) -> list[dict]:
        """Get open positions."""
        return [
            {
                "coin": "BTC",
                "size": "0.5",
                "entry_price": "50000.00",
                "mark_price": "51000.00",
                "unrealized_pnl": "500.00",
            }
        ]

    async def get_open_orders(self, owner: str) -> list[dict]:
        """Get open orders."""
        return [
            {
                "order_id": "order-1",
                "coin": "ETH",
                "size": "1.0",
                "price": "3000.00",
                "side": "Buy",
            }
        ]

    async def get_fill_history(
        self,
        owner: str,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict]:
        """Get fill history."""
        return [
            {
                "fill_id": "fill-1",
                "coin": "BTC",
                "size": "0.1",
                "price": "50000.00",
                "timestamp": 1234567890,
            }
        ]

    async def get_market_prices(self, coins: list[str]) -> dict[str, Decimal]:
        """Get current market prices for coins."""
        return {
            "BTC": Decimal("51000.00"),
            "ETH": Decimal("3100.00"),
        }

    async def get_exchange_metadata(self) -> dict:
        """Get exchange metadata."""
        return {
            "markets": ["BTC", "ETH", "SOL"],
            "size_decimals": {"BTC": 3, "ETH": 2, "SOL": 1},
            "price_decimals": {"BTC": 1, "ETH": 2, "SOL": 3},
        }

    async def get_fee_rates(self, owner: str) -> dict[str, Decimal]:
        """Get fee rates for account."""
        return {
            "maker": Decimal("0.0002"),
            "taker": Decimal("0.0005"),
        }


class MockExchangeTrading:
    """Mock implementation of ExchangeTrading protocol for testing."""

    async def submit_order(self, order: OrderRequest) -> OrderResult:
        """Submit a single order."""
        return OrderResult(
            order_request=order,
            status=OrderStatus.FILLED,
            order_id="order-123",
            exchange_order_id="exch-order-123",
            filled_size=order.size,
            average_price=order.limit_price or Decimal("50000.00"),
            total_fee=Decimal("0.0005") * order.size * (order.limit_price or Decimal("50000.00")),
        )

    async def submit_batch_orders(self, orders: list[OrderRequest]) -> list[OrderResult]:
        """Submit multiple orders in a batch."""
        return [await self.submit_order(order) for order in orders]

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID."""
        return True

    async def cancel_batch_orders(self, order_ids: list[str]) -> list[bool]:
        """Cancel multiple orders."""
        return [True for _ in order_ids]

    async def modify_order(
        self,
        order_id: str,
        new_size: Decimal | None = None,
        new_price: Decimal | None = None,
    ) -> OrderResult:
        """Modify an existing order."""
        # Create a dummy order request for the modified order
        size = new_size or Decimal("1.0")
        price = new_price or Decimal("50000.00")
        dummy_order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=size,
            order_type=OrderType.LIMIT,
            limit_price=price,
            reduce_only=False,
        )
        return OrderResult(
            order_request=dummy_order,
            status=OrderStatus.RESTING,
            order_id=order_id,
            exchange_order_id=f"exch-{order_id}",
            filled_size=None,
            average_price=None,
        )


class MockExchange(Exchange):
    """Mock implementation of Exchange ABC for testing."""

    def __init__(self, config: dict):
        """Initialize mock exchange."""
        super().__init__(config)
        self._info = MockExchangeInfo()
        self._trading = MockExchangeTrading()

    @property
    def info(self) -> ExchangeInfo:
        """Get info client."""
        return self._info  # type: ignore

    @property
    def trading(self) -> ExchangeTrading:
        """Get trading client."""
        return self._trading  # type: ignore

    def parse_account_state(self, raw_data: dict) -> PortfolioSnapshot:
        """Parse raw account state to domain model."""
        margin_data = raw_data.get("margin_summary", {})
        account = AccountInfo(
            account_value=Decimal(margin_data.get("account_value", "0")),
            total_position_value=Decimal(margin_data.get("total_ntl_pos", "0")),
            margin_used=Decimal(margin_data.get("total_margin_used", "0")),
            free_collateral=Decimal(margin_data.get("account_value", "0"))
            - Decimal(margin_data.get("total_margin_used", "0")),
            cash_balance=Decimal(margin_data.get("account_value", "0")),
            withdrawable=Decimal(margin_data.get("account_value", "0")),
            current_leverage=Decimal("0"),
        )
        return PortfolioSnapshot(account=account, positions=[])

    def round_size(self, coin: str, size: Decimal) -> Decimal:
        """Round size to exchange precision."""
        decimals = {"BTC": 3, "ETH": 2, "SOL": 1}.get(coin, 2)
        return round(size, decimals)

    def round_price(self, coin: str, price: Decimal) -> Decimal:
        """Round price to exchange precision."""
        decimals = {"BTC": 1, "ETH": 2, "SOL": 3}.get(coin, 2)
        return round(price, decimals)

    def calculate_limit_price(
        self,
        coin: str,
        side: str,
        reference_price: Decimal,
        slippage_tolerance: Decimal,
    ) -> Decimal:
        """Calculate limit price with slippage tolerance."""
        if side.lower() in ("buy", "long"):
            return reference_price * (Decimal("1") + slippage_tolerance)
        else:
            return reference_price * (Decimal("1") - slippage_tolerance)


class IncompleteExchangeInfo:
    """Incomplete implementation missing required methods."""

    async def get_account_state(self, owner: str, vault: str | None = None) -> dict:
        """Get raw account state from exchange."""
        return {}

    # Missing other required methods


class IncompleteExchangeTrading:
    """Incomplete implementation missing required methods."""

    async def submit_order(self, order: OrderRequest) -> OrderResult:
        """Submit a single order."""
        return OrderResult(
            success=False,
            order_id="",
            filled_size=Decimal("0"),
            avg_fill_price=Decimal("0"),
            message="Not implemented",
        )

    # Missing other required methods


class IncompleteExchange(Exchange):
    """Incomplete Exchange implementation missing abstract methods."""

    # Not implementing any abstract methods


# ============================================================================
# Protocol Compliance Tests
# ============================================================================


class TestExchangeInfoProtocol:
    """Test ExchangeInfo protocol compliance."""

    def test_mock_implementation_satisfies_protocol(self):
        """Test that MockExchangeInfo satisfies ExchangeInfo protocol."""
        mock = MockExchangeInfo()
        assert isinstance(mock, ExchangeInfo)

    def test_incomplete_implementation_does_not_satisfy_protocol(self):
        """Test that incomplete implementation does NOT satisfy protocol."""
        incomplete = IncompleteExchangeInfo()
        # Note: Protocol checks are structural, so this will NOT pass if methods are missing
        # Since IncompleteExchangeInfo only implements get_account_state, it should fail
        assert not isinstance(incomplete, ExchangeInfo)  # Missing required methods

    @pytest.mark.asyncio
    async def test_get_account_state_signature(self):
        """Test get_account_state method signature and return type."""
        mock = MockExchangeInfo()
        result = await mock.get_account_state("owner-123")
        assert isinstance(result, dict)
        assert "owner" in result

    @pytest.mark.asyncio
    async def test_get_account_state_with_vault(self):
        """Test get_account_state with vault parameter."""
        mock = MockExchangeInfo()
        result = await mock.get_account_state("owner-123", vault="vault-456")
        assert result["vault"] == "vault-456"

    @pytest.mark.asyncio
    async def test_get_open_positions(self):
        """Test get_open_positions method."""
        mock = MockExchangeInfo()
        result = await mock.get_open_positions("owner-123")
        assert isinstance(result, list)
        assert len(result) > 0
        assert "coin" in result[0]

    @pytest.mark.asyncio
    async def test_get_open_orders(self):
        """Test get_open_orders method."""
        mock = MockExchangeInfo()
        result = await mock.get_open_orders("owner-123")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_fill_history(self):
        """Test get_fill_history method."""
        mock = MockExchangeInfo()
        result = await mock.get_fill_history("owner-123")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_fill_history_with_time_range(self):
        """Test get_fill_history with time range parameters."""
        mock = MockExchangeInfo()
        result = await mock.get_fill_history(
            "owner-123", start_time=1000000000, end_time=2000000000
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_market_prices(self):
        """Test get_market_prices method."""
        mock = MockExchangeInfo()
        result = await mock.get_market_prices(["BTC", "ETH"])
        assert isinstance(result, dict)
        assert "BTC" in result
        assert isinstance(result["BTC"], Decimal)

    @pytest.mark.asyncio
    async def test_get_exchange_metadata(self):
        """Test get_exchange_metadata method."""
        mock = MockExchangeInfo()
        result = await mock.get_exchange_metadata()
        assert isinstance(result, dict)
        assert "markets" in result

    @pytest.mark.asyncio
    async def test_get_fee_rates(self):
        """Test get_fee_rates method."""
        mock = MockExchangeInfo()
        result = await mock.get_fee_rates("owner-123")
        assert isinstance(result, dict)
        assert "maker" in result
        assert isinstance(result["maker"], Decimal)


class TestExchangeTradingProtocol:
    """Test ExchangeTrading protocol compliance."""

    def test_mock_implementation_satisfies_protocol(self):
        """Test that MockExchangeTrading satisfies ExchangeTrading protocol."""
        mock = MockExchangeTrading()
        assert isinstance(mock, ExchangeTrading)

    def test_incomplete_implementation_does_not_satisfy_protocol(self):
        """Test that incomplete implementation does NOT satisfy protocol."""
        incomplete = IncompleteExchangeTrading()
        # Structural typing will NOT pass if methods are missing
        # Since IncompleteExchangeTrading only implements submit_order, it should fail
        assert not isinstance(incomplete, ExchangeTrading)

    @pytest.mark.asyncio
    async def test_submit_order(self):
        """Test submit_order method."""
        mock = MockExchangeTrading()
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
            reduce_only=False,
        )
        result = await mock.submit_order(order)
        assert isinstance(result, OrderResult)
        assert result.is_success is True
        assert result.order_id == "order-123"

    @pytest.mark.asyncio
    async def test_submit_batch_orders(self):
        """Test submit_batch_orders method."""
        mock = MockExchangeTrading()
        orders = [
            OrderRequest(
                coin="BTC",
                side=OrderSide.BUY,
                size=Decimal("0.1"),
                order_type=OrderType.MARKET,
                reduce_only=False,
            ),
            OrderRequest(
                coin="ETH",
                side=OrderSide.SELL,
                size=Decimal("1.0"),
                order_type=OrderType.MARKET,
                reduce_only=False,
            ),
        ]
        results = await mock.submit_batch_orders(orders)
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, OrderResult) for r in results)

    @pytest.mark.asyncio
    async def test_cancel_order(self):
        """Test cancel_order method."""
        mock = MockExchangeTrading()
        result = await mock.cancel_order("order-123")
        assert isinstance(result, bool)
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_batch_orders(self):
        """Test cancel_batch_orders method."""
        mock = MockExchangeTrading()
        results = await mock.cancel_batch_orders(["order-1", "order-2", "order-3"])
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, bool) for r in results)

    @pytest.mark.asyncio
    async def test_modify_order_size(self):
        """Test modify_order with new size."""
        mock = MockExchangeTrading()
        result = await mock.modify_order("order-123", new_size=Decimal("0.5"))
        assert isinstance(result, OrderResult)
        assert result.is_success is True

    @pytest.mark.asyncio
    async def test_modify_order_price(self):
        """Test modify_order with new price."""
        mock = MockExchangeTrading()
        result = await mock.modify_order("order-123", new_price=Decimal("51000.00"))
        assert isinstance(result, OrderResult)
        assert result.is_success is True

    @pytest.mark.asyncio
    async def test_modify_order_both(self):
        """Test modify_order with both size and price."""
        mock = MockExchangeTrading()
        result = await mock.modify_order(
            "order-123", new_size=Decimal("0.5"), new_price=Decimal("51000.00")
        )
        assert isinstance(result, OrderResult)
        assert result.is_success is True


class TestExchangeABC:
    """Test Exchange ABC abstract method enforcement."""

    def test_cannot_instantiate_exchange_directly(self):
        """Test that Exchange ABC cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Exchange({"test": "config"})  # type: ignore

    def test_incomplete_subclass_cannot_be_instantiated(self):
        """Test that subclass without implementing abstract methods fails."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteExchange({"test": "config"})  # type: ignore

    def test_complete_subclass_can_be_instantiated(self):
        """Test that subclass with all methods implemented works."""
        exchange = MockExchange({"test": "config"})
        assert isinstance(exchange, Exchange)
        assert exchange.config == {"test": "config"}

    def test_info_property_access(self):
        """Test info property access."""
        exchange = MockExchange({"test": "config"})
        info = exchange.info
        assert isinstance(info, ExchangeInfo)

    def test_trading_property_access(self):
        """Test trading property access."""
        exchange = MockExchange({"test": "config"})
        trading = exchange.trading
        assert isinstance(trading, ExchangeTrading)

    def test_parse_account_state(self):
        """Test parse_account_state method."""
        exchange = MockExchange({"test": "config"})
        raw_data = {
            "margin_summary": {
                "account_value": "10000.00",
                "total_margin_used": "2000.00",
                "total_ntl_pos": "8000.00",
            }
        }
        snapshot = exchange.parse_account_state(raw_data)
        assert isinstance(snapshot, PortfolioSnapshot)
        assert snapshot.account.account_value == Decimal("10000.00")

    def test_round_size(self):
        """Test round_size method."""
        exchange = MockExchange({"test": "config"})
        btc_size = exchange.round_size("BTC", Decimal("0.12345"))
        assert btc_size == Decimal("0.123")  # 3 decimals for BTC

        eth_size = exchange.round_size("ETH", Decimal("1.2345"))
        assert eth_size == Decimal("1.23")  # 2 decimals for ETH

    def test_round_price(self):
        """Test round_price method."""
        exchange = MockExchange({"test": "config"})
        btc_price = exchange.round_price("BTC", Decimal("50123.456"))
        assert btc_price == Decimal("50123.5")  # 1 decimal for BTC

        eth_price = exchange.round_price("ETH", Decimal("3123.456"))
        assert eth_price == Decimal("3123.46")  # 2 decimals for ETH

    def test_calculate_limit_price_buy(self):
        """Test calculate_limit_price for buy orders."""
        exchange = MockExchange({"test": "config"})
        reference = Decimal("50000.00")
        slippage = Decimal("0.001")  # 0.1%

        limit_price = exchange.calculate_limit_price("BTC", "buy", reference, slippage)
        expected = Decimal("50050.00")  # 50000 * 1.001
        assert limit_price == expected

    def test_calculate_limit_price_sell(self):
        """Test calculate_limit_price for sell orders."""
        exchange = MockExchange({"test": "config"})
        reference = Decimal("50000.00")
        slippage = Decimal("0.001")  # 0.1%

        limit_price = exchange.calculate_limit_price("BTC", "sell", reference, slippage)
        expected = Decimal("49950.00")  # 50000 * 0.999
        assert limit_price == expected

    def test_calculate_limit_price_long(self):
        """Test calculate_limit_price for long (alternative to buy)."""
        exchange = MockExchange({"test": "config"})
        reference = Decimal("50000.00")
        slippage = Decimal("0.002")  # 0.2%

        limit_price = exchange.calculate_limit_price("BTC", "long", reference, slippage)
        expected = Decimal("50100.00")  # 50000 * 1.002
        assert limit_price == expected


# ============================================================================
# Integration Tests for Mock Implementations
# ============================================================================


class TestMockIntegration:
    """Integration tests using mock implementations."""

    @pytest.mark.asyncio
    async def test_full_exchange_workflow(self):
        """Test complete workflow using mock exchange."""
        exchange = MockExchange({"api_key": "test"})

        # Get account state
        account_state = await exchange.info.get_account_state("owner-123")
        assert account_state["owner"] == "owner-123"

        # Get market prices
        prices = await exchange.info.get_market_prices(["BTC", "ETH"])
        assert "BTC" in prices

        # Submit order
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.LIMIT,
            limit_price=Decimal("50000.00"),
            reduce_only=False,
        )
        result = await exchange.trading.submit_order(order)
        assert result.is_success is True

        # Cancel order
        cancelled = await exchange.trading.cancel_order(result.order_id)
        assert cancelled is True

    @pytest.mark.asyncio
    async def test_batch_operations(self):
        """Test batch operations."""
        exchange = MockExchange({"api_key": "test"})

        # Create multiple orders
        orders = [
            OrderRequest(
                coin="BTC",
                side=OrderSide.BUY,
                size=Decimal("0.1"),
                order_type=OrderType.MARKET,
                reduce_only=False,
            ),
            OrderRequest(
                coin="ETH",
                side=OrderSide.SELL,
                size=Decimal("1.0"),
                order_type=OrderType.MARKET,
                reduce_only=False,
            ),
        ]

        # Submit batch
        results = await exchange.trading.submit_batch_orders(orders)
        assert len(results) == 2

        # Cancel batch
        order_ids = [r.order_id for r in results]
        cancel_results = await exchange.trading.cancel_batch_orders(order_ids)
        assert len(cancel_results) == 2
        assert all(cancel_results)

    @pytest.mark.asyncio
    async def test_exchange_metadata_usage(self):
        """Test using exchange metadata for rounding."""
        exchange = MockExchange({"api_key": "test"})

        # Get metadata
        metadata = await exchange.info.get_exchange_metadata()
        assert "markets" in metadata
        assert "BTC" in metadata["markets"]

        # Use metadata for rounding
        raw_size = Decimal("0.12345")
        rounded = exchange.round_size("BTC", raw_size)
        assert rounded == Decimal("0.123")
