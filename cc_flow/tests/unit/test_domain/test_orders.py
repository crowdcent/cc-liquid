"""Unit tests for order domain models.

Tests cover:
- Order enums (OrderType, TimeInForce, OrderSide, OrderStatus)
- OrderRequest model (frozen, immutable)
- OrderResult model with is_success property
- Trade model with execution tracking
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from cc_flow.domain.orders import (
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
    Trade,
)


class TestOrderEnums:
    """Test order enumeration types."""

    def test_order_type_values(self):
        """Test OrderType enum values."""
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"

    def test_order_type_string_enum(self):
        """Test OrderType is a string enum."""
        assert isinstance(OrderType.MARKET, str)
        assert isinstance(OrderType.LIMIT, str)

    def test_time_in_force_values(self):
        """Test TimeInForce enum values match Hyperliquid API."""
        assert TimeInForce.IOC.value == "Ioc"
        assert TimeInForce.GTC.value == "Gtc"
        assert TimeInForce.ALO.value == "Alo"

    def test_time_in_force_string_enum(self):
        """Test TimeInForce is a string enum."""
        assert isinstance(TimeInForce.IOC, str)
        assert isinstance(TimeInForce.GTC, str)
        assert isinstance(TimeInForce.ALO, str)

    def test_order_side_values(self):
        """Test OrderSide enum values."""
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"

    def test_order_side_string_enum(self):
        """Test OrderSide is a string enum."""
        assert isinstance(OrderSide.BUY, str)
        assert isinstance(OrderSide.SELL, str)

    def test_order_status_values(self):
        """Test OrderStatus enum values."""
        assert OrderStatus.PENDING.value == "pending"
        assert OrderStatus.FILLED.value == "filled"
        assert OrderStatus.RESTING.value == "resting"
        assert OrderStatus.FAILED.value == "failed"
        assert OrderStatus.CANCELLED.value == "cancelled"

    def test_order_status_string_enum(self):
        """Test OrderStatus is a string enum."""
        assert isinstance(OrderStatus.PENDING, str)
        assert isinstance(OrderStatus.FILLED, str)

    def test_enum_equality(self):
        """Test enum comparison."""
        assert OrderType.MARKET == "market"
        assert OrderSide.BUY == "buy"
        assert TimeInForce.IOC == "Ioc"
        assert OrderStatus.FILLED == "filled"


class TestOrderRequest:
    """Test OrderRequest model."""

    def test_market_order_creation(self):
        """Test creating a market order."""
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        assert order.coin == "BTC"
        assert order.side == OrderSide.BUY
        assert order.size == Decimal("0.1")
        assert order.order_type == OrderType.MARKET
        assert order.limit_price is None
        assert order.time_in_force == TimeInForce.IOC
        assert order.reduce_only is False
        assert order.client_order_id is None

    def test_limit_order_creation(self):
        """Test creating a limit order with limit_price."""
        order = OrderRequest(
            coin="ETH",
            side=OrderSide.SELL,
            size=Decimal("1.5"),
            order_type=OrderType.LIMIT,
            limit_price=Decimal("3000.50"),
        )

        assert order.coin == "ETH"
        assert order.side == OrderSide.SELL
        assert order.size == Decimal("1.5")
        assert order.order_type == OrderType.LIMIT
        assert order.limit_price == Decimal("3000.50")

    def test_order_request_frozen(self):
        """Test that OrderRequest is immutable (frozen=True)."""
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        with pytest.raises(ValidationError):
            order.size = Decimal("0.2")

    def test_all_time_in_force_options(self):
        """Test all TimeInForce options."""
        for tif in [TimeInForce.IOC, TimeInForce.GTC, TimeInForce.ALO]:
            order = OrderRequest(
                coin="BTC",
                side=OrderSide.BUY,
                size=Decimal("0.1"),
                order_type=OrderType.MARKET,
                time_in_force=tif,
            )
            assert order.time_in_force == tif

    def test_reduce_only_flag(self):
        """Test reduce_only flag."""
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.SELL,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
            reduce_only=True,
        )

        assert order.reduce_only is True

    def test_client_order_id(self):
        """Test client_order_id assignment."""
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
            client_order_id="my-order-123",
        )

        assert order.client_order_id == "my-order-123"

    def test_serialization(self):
        """Test OrderRequest serialization."""
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
            limit_price=Decimal("50000.00"),
            time_in_force=TimeInForce.GTC,
            reduce_only=True,
            client_order_id="test-123",
        )

        # Test model_dump()
        data = order.model_dump()
        assert data["coin"] == "BTC"
        assert data["side"] == OrderSide.BUY
        assert isinstance(data["size"], Decimal)

        # Test model_dump(mode="json")
        json_data = order.model_dump(mode="json")
        assert json_data["coin"] == "BTC"
        assert json_data["side"] == "buy"
        assert json_data["size"] == "0.1"

        # Test deserialization
        order2 = OrderRequest(**data)
        assert order2.coin == order.coin
        assert order2.size == order.size

    def test_zero_size_order(self):
        """Test order with zero size."""
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0"),
            order_type=OrderType.MARKET,
        )
        assert order.size == Decimal("0")

    def test_very_large_decimal(self):
        """Test order with very large decimal values."""
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("999999.123456789"),
            order_type=OrderType.MARKET,
        )
        assert order.size == Decimal("999999.123456789")


class TestOrderResult:
    """Test OrderResult model."""

    def test_pending_status(self):
        """Test OrderResult with PENDING status."""
        order_request = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        result = OrderResult(
            order_request=order_request,
            status=OrderStatus.PENDING,
        )

        assert result.status == OrderStatus.PENDING
        assert result.is_success is False
        assert result.filled_size is None
        assert result.error_message is None

    def test_filled_status(self):
        """Test OrderResult with FILLED status (is_success=True)."""
        order_request = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        result = OrderResult(
            order_request=order_request,
            status=OrderStatus.FILLED,
            filled_size=Decimal("0.1"),
            average_price=Decimal("50000.00"),
            total_fee=Decimal("5.00"),
            order_id="order-123",
            exchange_order_id="ex-456",
            submitted_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
            filled_at=datetime(2025, 1, 1, 12, 0, 5, tzinfo=UTC),
        )

        assert result.status == OrderStatus.FILLED
        assert result.is_success is True
        assert result.filled_size == Decimal("0.1")
        assert result.average_price == Decimal("50000.00")
        assert result.total_fee == Decimal("5.00")
        assert result.order_id == "order-123"
        assert result.exchange_order_id == "ex-456"

    def test_resting_status(self):
        """Test OrderResult with RESTING status (is_success=True)."""
        order_request = OrderRequest(
            coin="ETH",
            side=OrderSide.SELL,
            size=Decimal("1.0"),
            order_type=OrderType.LIMIT,
            limit_price=Decimal("3000.00"),
            time_in_force=TimeInForce.GTC,
        )

        result = OrderResult(
            order_request=order_request,
            status=OrderStatus.RESTING,
            order_id="order-789",
        )

        assert result.status == OrderStatus.RESTING
        assert result.is_success is True

    def test_failed_status(self):
        """Test OrderResult with FAILED status (is_success=False)."""
        order_request = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        result = OrderResult(
            order_request=order_request,
            status=OrderStatus.FAILED,
            error_message="Insufficient margin",
        )

        assert result.status == OrderStatus.FAILED
        assert result.is_success is False
        assert result.error_message == "Insufficient margin"

    def test_cancelled_status(self):
        """Test OrderResult with CANCELLED status (is_success=False)."""
        order_request = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        result = OrderResult(
            order_request=order_request,
            status=OrderStatus.CANCELLED,
        )

        assert result.status == OrderStatus.CANCELLED
        assert result.is_success is False

    def test_order_result_mutable(self):
        """Test that OrderResult is mutable (frozen=False)."""
        order_request = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        result = OrderResult(
            order_request=order_request,
            status=OrderStatus.PENDING,
        )

        # Should be able to update status
        result.status = OrderStatus.FILLED
        assert result.status == OrderStatus.FILLED

    def test_serialization_with_nested_order_request(self):
        """Test OrderResult serialization with nested OrderRequest."""
        order_request = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        result = OrderResult(
            order_request=order_request,
            status=OrderStatus.FILLED,
            filled_size=Decimal("0.1"),
            average_price=Decimal("50000.00"),
        )

        # Test model_dump()
        data = result.model_dump()
        assert data["order_request"]["coin"] == "BTC"
        assert isinstance(data["filled_size"], Decimal)

        # Test model_dump(mode="json")
        json_data = result.model_dump(mode="json")
        assert json_data["order_request"]["coin"] == "BTC"
        assert json_data["filled_size"] == "0.1"

        # Test deserialization
        result2 = OrderResult(**data)
        assert result2.order_request.coin == "BTC"
        assert result2.filled_size == Decimal("0.1")


class TestTrade:
    """Test Trade model."""

    def test_open_trade_type(self):
        """Test 'open' trade type."""
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
        )

        assert trade.trade_type == "open"
        assert trade.current_value == Decimal("0")
        assert trade.target_value == Decimal("5000.00")

    def test_close_trade_type(self):
        """Test 'close' trade type."""
        trade = Trade(
            coin="ETH",
            side=OrderSide.SELL,
            size=Decimal("1.0"),
            reference_price=Decimal("3000.00"),
            current_value=Decimal("3000.00"),
            target_value=Decimal("0"),
            delta_value=Decimal("-3000.00"),
            trade_type="close",
            estimated_fee=Decimal("1.50"),
        )

        assert trade.trade_type == "close"
        assert trade.current_value == Decimal("3000.00")
        assert trade.target_value == Decimal("0")

    def test_reduce_trade_type(self):
        """Test 'reduce' trade type."""
        trade = Trade(
            coin="BTC",
            side=OrderSide.SELL,
            size=Decimal("0.05"),
            reference_price=Decimal("50000.00"),
            current_value=Decimal("10000.00"),
            target_value=Decimal("7500.00"),
            delta_value=Decimal("-2500.00"),
            trade_type="reduce",
            estimated_fee=Decimal("1.25"),
        )

        assert trade.trade_type == "reduce"

    def test_increase_trade_type(self):
        """Test 'increase' trade type."""
        trade = Trade(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.05"),
            reference_price=Decimal("50000.00"),
            current_value=Decimal("5000.00"),
            target_value=Decimal("7500.00"),
            delta_value=Decimal("2500.00"),
            trade_type="increase",
            estimated_fee=Decimal("1.25"),
        )

        assert trade.trade_type == "increase"

    def test_flip_trade_type(self):
        """Test 'flip' trade type."""
        trade = Trade(
            coin="ETH",
            side=OrderSide.BUY,
            size=Decimal("2.0"),
            reference_price=Decimal("3000.00"),
            current_value=Decimal("-3000.00"),
            target_value=Decimal("3000.00"),
            delta_value=Decimal("6000.00"),
            trade_type="flip",
            estimated_fee=Decimal("3.00"),
        )

        assert trade.trade_type == "flip"

    def test_is_executed_property_before_execution(self):
        """Test is_executed property before execution."""
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
        )

        assert trade.is_executed is False
        assert trade.is_successful is False

    def test_is_executed_property_after_execution(self):
        """Test is_executed property after execution."""
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

        assert trade.is_executed is True
        assert trade.is_successful is True

    def test_is_successful_with_success(self):
        """Test is_successful property with successful execution."""
        order_request = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        order_result = OrderResult(
            order_request=order_request,
            status=OrderStatus.FILLED,
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

        assert trade.is_successful is True

    def test_is_successful_with_failure(self):
        """Test is_successful property with failed execution."""
        order_request = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        order_result = OrderResult(
            order_request=order_request,
            status=OrderStatus.FAILED,
            error_message="Insufficient margin",
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

        assert trade.is_executed is True
        assert trade.is_successful is False

    def test_with_estimated_slippage(self):
        """Test trade with estimated_slippage."""
        trade = Trade(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            reference_price=Decimal("50000.00"),
            limit_price=Decimal("50100.00"),
            current_value=Decimal("0"),
            target_value=Decimal("5000.00"),
            delta_value=Decimal("5000.00"),
            trade_type="open",
            estimated_fee=Decimal("2.50"),
            estimated_slippage=Decimal("10.00"),
        )

        assert trade.estimated_slippage == Decimal("10.00")
        assert trade.limit_price == Decimal("50100.00")

    def test_trade_mutable(self):
        """Test that Trade is mutable (frozen=False)."""
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
        )

        # Should be able to add order_result after creation
        order_request = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        trade.order_result = OrderResult(
            order_request=order_request,
            status=OrderStatus.FILLED,
        )

        assert trade.order_result is not None
        assert trade.is_executed is True

    def test_serialization_with_nested_order_result(self):
        """Test Trade serialization with nested OrderResult."""
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

        # Test model_dump()
        data = trade.model_dump()
        assert data["coin"] == "BTC"
        assert data["order_result"]["status"] == OrderStatus.FILLED

        # Test model_dump(mode="json")
        json_data = trade.model_dump(mode="json")
        assert json_data["coin"] == "BTC"
        assert json_data["order_result"]["status"] == "filled"
        assert json_data["size"] == "0.1"

        # Test deserialization
        trade2 = Trade(**data)
        assert trade2.coin == "BTC"
        assert trade2.order_result.status == OrderStatus.FILLED

    def test_negative_values_for_short_positions(self):
        """Test trade with negative values for short positions."""
        trade = Trade(
            coin="BTC",
            side=OrderSide.SELL,
            size=Decimal("0.1"),
            reference_price=Decimal("50000.00"),
            current_value=Decimal("0"),
            target_value=Decimal("-5000.00"),
            delta_value=Decimal("-5000.00"),
            trade_type="open",
            estimated_fee=Decimal("2.50"),
        )

        assert trade.target_value == Decimal("-5000.00")
        assert trade.delta_value == Decimal("-5000.00")
