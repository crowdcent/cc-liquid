"""Tests for Hyperliquid exchange implementation.

This module tests the HyperliquidInfo and HyperliquidTrading classes,
mocking the hyperliquid-python-sdk to avoid network calls.

Test Coverage:
    - HyperliquidInfo: All 7 methods
    - HyperliquidTrading: Order submission, cancellation, batch operations
    - Order format conversion
    - Error handling
    - Edge cases and boundary conditions
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from cc_flow.domain.orders import (
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from cc_flow.exchanges.hyperliquid import HyperliquidInfo, HyperliquidTrading

# ============================================================================
# HyperliquidInfo Tests
# ============================================================================


class TestHyperliquidInfo:
    """Test suite for HyperliquidInfo class."""

    @pytest.fixture
    def info_client(self):
        """Create HyperliquidInfo instance with mocked SDK."""
        with patch("cc_flow.exchanges.hyperliquid.Info") as mock_info:
            client = HyperliquidInfo(base_url="https://api.hyperliquid-testnet.xyz")
            client.client = mock_info.return_value
            yield client

    @pytest.mark.asyncio
    async def test_get_account_state_with_owner_only(self, info_client):
        """Test get_account_state with owner address only."""
        # Arrange
        owner = "0x1234567890abcdef"
        mock_state = {
            "marginSummary": {
                "accountValue": "10000.0",
                "totalNtlPos": "5000.0",
                "totalRawUsd": "10000.0",
            },
            "assetPositions": [],
        }
        info_client.client.user_state.return_value = mock_state

        # Act
        result = await info_client.get_account_state(owner)

        # Assert
        assert result == mock_state
        info_client.client.user_state.assert_called_once_with(owner)

    @pytest.mark.asyncio
    async def test_get_account_state_with_vault(self, info_client):
        """Test get_account_state with vault address."""
        # Arrange
        owner = "0x1234567890abcdef"
        vault = "0xvault1234567890"
        mock_state = {"marginSummary": {"accountValue": "50000.0"}}
        info_client.client.user_state.return_value = mock_state

        # Act
        result = await info_client.get_account_state(owner, vault)

        # Assert
        assert result == mock_state
        # Should use vault address, not owner
        info_client.client.user_state.assert_called_once_with(vault)

    @pytest.mark.asyncio
    async def test_get_open_positions_empty(self, info_client):
        """Test get_open_positions with no positions."""
        # Arrange
        owner = "0x1234567890abcdef"
        mock_state = {"assetPositions": []}
        info_client.client.user_state.return_value = mock_state

        # Act
        result = await info_client.get_open_positions(owner)

        # Assert
        assert result == []
        info_client.client.user_state.assert_called_once_with(owner)

    @pytest.mark.asyncio
    async def test_get_open_positions_with_positions(self, info_client):
        """Test get_open_positions with multiple positions."""
        # Arrange
        owner = "0x1234567890abcdef"
        mock_positions = [
            {"position": {"coin": "BTC", "szi": "1.5", "entryPx": "50000.0"}},
            {"position": {"coin": "ETH", "szi": "-10.0", "entryPx": "3000.0"}},
        ]
        mock_state = {"assetPositions": mock_positions}
        info_client.client.user_state.return_value = mock_state

        # Act
        result = await info_client.get_open_positions(owner)

        # Assert
        assert result == mock_positions
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_open_positions_with_vault(self, info_client):
        """Test get_open_positions uses vault when provided."""
        # Arrange
        owner = "0x1234567890abcdef"
        vault = "0xvault1234567890"
        mock_state = {"assetPositions": []}
        info_client.client.user_state.return_value = mock_state

        # Act
        await info_client.get_open_positions(owner, vault)

        # Assert
        info_client.client.user_state.assert_called_once_with(vault)

    @pytest.mark.asyncio
    async def test_get_open_orders_empty(self, info_client):
        """Test get_open_orders with no orders."""
        # Arrange
        owner = "0x1234567890abcdef"
        info_client.client.open_orders.return_value = []

        # Act
        result = await info_client.get_open_orders(owner)

        # Assert
        assert result == []
        info_client.client.open_orders.assert_called_once_with(owner)

    @pytest.mark.asyncio
    async def test_get_open_orders_with_orders(self, info_client):
        """Test get_open_orders with multiple orders."""
        # Arrange
        owner = "0x1234567890abcdef"
        mock_orders = [
            {"coin": "BTC", "side": "B", "sz": "0.1", "limitPx": "50000.0", "oid": 123},
            {"coin": "ETH", "side": "A", "sz": "1.0", "limitPx": "3000.0", "oid": 124},
        ]
        info_client.client.open_orders.return_value = mock_orders

        # Act
        result = await info_client.get_open_orders(owner)

        # Assert
        assert result == mock_orders
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_fill_history_no_time_filter(self, info_client):
        """Test get_fill_history without time filters."""
        # Arrange
        owner = "0x1234567890abcdef"
        mock_fills = [
            {"coin": "BTC", "px": "50000.0", "sz": "0.1", "time": 1234567890},
            {"coin": "ETH", "px": "3000.0", "sz": "1.0", "time": 1234567900},
        ]
        info_client.client.user_fills.return_value = mock_fills

        # Act
        result = await info_client.get_fill_history(owner)

        # Assert
        assert result == mock_fills
        info_client.client.user_fills.assert_called_once_with(owner)

    @pytest.mark.asyncio
    async def test_get_fill_history_with_time_filters(self, info_client):
        """Test get_fill_history with start and end time."""
        # Arrange
        owner = "0x1234567890abcdef"
        start_time = 1234567890000
        end_time = 1234567990000
        mock_fills = []
        info_client.client.user_fills.return_value = mock_fills

        # Act
        result = await info_client.get_fill_history(owner, start_time, end_time)

        # Assert
        assert result == mock_fills
        # Note: Current implementation doesn't pass time filters to SDK
        # This tests the interface, not SDK behavior
        info_client.client.user_fills.assert_called_once_with(owner)

    @pytest.mark.asyncio
    async def test_get_market_prices_single_coin(self, info_client):
        """Test get_market_prices for single coin."""
        # Arrange
        coins = ["BTC"]
        mock_mids = {"BTC": "50000.0", "ETH": "3000.0", "SOL": "100.0"}
        info_client.client.all_mids.return_value = mock_mids

        # Act
        result = await info_client.get_market_prices(coins)

        # Assert
        assert result == {"BTC": Decimal("50000.0")}
        assert isinstance(result["BTC"], Decimal)

    @pytest.mark.asyncio
    async def test_get_market_prices_multiple_coins(self, info_client):
        """Test get_market_prices for multiple coins."""
        # Arrange
        coins = ["BTC", "ETH", "SOL"]
        mock_mids = {"BTC": "50000.0", "ETH": "3000.0", "SOL": "100.0"}
        info_client.client.all_mids.return_value = mock_mids

        # Act
        result = await info_client.get_market_prices(coins)

        # Assert
        assert len(result) == 3
        assert result["BTC"] == Decimal("50000.0")
        assert result["ETH"] == Decimal("3000.0")
        assert result["SOL"] == Decimal("100.0")

    @pytest.mark.asyncio
    async def test_get_market_prices_missing_coin(self, info_client):
        """Test get_market_prices when coin is not in response."""
        # Arrange
        coins = ["BTC", "DOGE"]  # DOGE not in mids
        mock_mids = {"BTC": "50000.0", "ETH": "3000.0"}
        info_client.client.all_mids.return_value = mock_mids

        # Act
        result = await info_client.get_market_prices(coins)

        # Assert
        assert "BTC" in result
        assert "DOGE" not in result  # Should skip missing coins

    @pytest.mark.asyncio
    async def test_get_exchange_metadata(self, info_client):
        """Test get_exchange_metadata."""
        # Arrange
        mock_meta = {
            "universe": [
                {"name": "BTC", "szDecimals": 5, "maxLeverage": 50},
                {"name": "ETH", "szDecimals": 4, "maxLeverage": 50},
            ]
        }
        info_client.client.meta.return_value = mock_meta

        # Act
        result = await info_client.get_exchange_metadata()

        # Assert
        assert result == mock_meta
        info_client.client.meta.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_fee_rates(self, info_client):
        """Test get_fee_rates returns fixed Hyperliquid rates."""
        # Arrange
        owner = "0x1234567890abcdef"

        # Act
        result = await info_client.get_fee_rates(owner)

        # Assert
        assert result == {
            "maker": Decimal("0.00020"),  # 2 bps
            "taker": Decimal("0.00050"),  # 5 bps
        }
        assert isinstance(result["maker"], Decimal)
        assert isinstance(result["taker"], Decimal)


# ============================================================================
# HyperliquidTrading Tests
# ============================================================================


class TestHyperliquidTrading:
    """Test suite for HyperliquidTrading class."""

    @pytest.fixture
    def trading_client(self):
        """Create HyperliquidTrading instance with mocked SDK."""
        with patch("cc_flow.exchanges.hyperliquid.Account") as mock_account, \
             patch("cc_flow.exchanges.hyperliquid.HLExchange") as mock_exchange:

            mock_account.from_key.return_value = MagicMock()

            client = HyperliquidTrading(
                base_url="https://api.hyperliquid-testnet.xyz",
                private_key="0x" + "a" * 64,
                account_address="0x1234567890abcdef",
                vault_address=None,
            )
            client.client = mock_exchange.return_value
            yield client

    @pytest.mark.asyncio
    async def test_submit_order_market_buy_success(self, trading_client):
        """Test successful market buy order submission."""
        # Arrange
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
            reduce_only=False,
        )

        mock_response = {
            "status": "ok",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [{"resting": {"oid": 12345}}]
                }
            }
        }
        trading_client.client.order.return_value = mock_response

        # Act
        result = await trading_client.submit_order(order)

        # Assert
        assert result.status == OrderStatus.FILLED
        assert result.order_id == "12345"
        assert result.order_request == order
        trading_client.client.order.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_order_market_sell_success(self, trading_client):
        """Test successful market sell order submission."""
        # Arrange
        order = OrderRequest(
            coin="ETH",
            side=OrderSide.SELL,
            size=Decimal("1.0"),
            order_type=OrderType.MARKET,
        )

        mock_response = {
            "status": "ok",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [{"resting": {"oid": 67890}}]
                }
            }
        }
        trading_client.client.order.return_value = mock_response

        # Act
        result = await trading_client.submit_order(order)

        # Assert
        assert result.status == OrderStatus.FILLED
        assert result.order_id == "67890"

    @pytest.mark.asyncio
    async def test_submit_order_limit_buy(self, trading_client):
        """Test limit buy order submission."""
        # Arrange
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.LIMIT,
            limit_price=Decimal("50000.0"),
            time_in_force=TimeInForce.GTC,
        )

        mock_response = {
            "status": "ok",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [{"resting": {"oid": 11111}}]
                }
            }
        }
        trading_client.client.order.return_value = mock_response

        # Act
        result = await trading_client.submit_order(order)

        # Assert
        assert result.status == OrderStatus.FILLED
        assert result.order_id == "11111"

        # Verify correct parameters passed to SDK
        call_args = trading_client.client.order.call_args
        assert call_args[0][0] == "BTC"  # coin
        assert call_args[0][1] is True  # is_buy
        assert call_args[0][2] == 0.1  # size
        assert call_args[0][3] == 50000.0  # limit_px

    @pytest.mark.asyncio
    async def test_submit_order_reduce_only(self, trading_client):
        """Test reduce-only order submission."""
        # Arrange
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.SELL,
            size=Decimal("0.5"),
            order_type=OrderType.MARKET,
            reduce_only=True,
        )

        mock_response = {
            "status": "ok",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [{"resting": {"oid": 22222}}]
                }
            }
        }
        trading_client.client.order.return_value = mock_response

        # Act
        result = await trading_client.submit_order(order)

        # Assert
        assert result.status == OrderStatus.FILLED
        # Verify reduce_only flag passed correctly
        call_kwargs = trading_client.client.order.call_args[1]
        assert call_kwargs["reduce_only"] is True

    @pytest.mark.asyncio
    async def test_submit_order_failed_status(self, trading_client):
        """Test order submission with failed status."""
        # Arrange
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        mock_response = {
            "status": "err",
            "response": "Insufficient margin"
        }
        trading_client.client.order.return_value = mock_response

        # Act
        result = await trading_client.submit_order(order)

        # Assert
        assert result.status == OrderStatus.FAILED
        assert result.error_message is not None
        assert "err" in result.error_message or "Insufficient margin" in result.error_message

    @pytest.mark.asyncio
    async def test_submit_order_exception(self, trading_client):
        """Test order submission with exception."""
        # Arrange
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        trading_client.client.order.side_effect = Exception("Network error")

        # Act
        result = await trading_client.submit_order(order)

        # Assert
        assert result.status == OrderStatus.FAILED
        assert "Network error" in result.error_message

    @pytest.mark.asyncio
    async def test_submit_batch_orders(self, trading_client):
        """Test batch order submission."""
        # Arrange
        orders = [
            OrderRequest(
                coin="BTC",
                side=OrderSide.BUY,
                size=Decimal("0.1"),
                order_type=OrderType.MARKET,
            ),
            OrderRequest(
                coin="ETH",
                side=OrderSide.SELL,
                size=Decimal("1.0"),
                order_type=OrderType.MARKET,
            ),
        ]

        mock_response = {
            "status": "ok",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [{"resting": {"oid": 99999}}]
                }
            }
        }
        trading_client.client.order.return_value = mock_response

        # Act
        results = await trading_client.submit_batch_orders(orders)

        # Assert
        assert len(results) == 2
        assert all(r.status == OrderStatus.FILLED for r in results)
        assert trading_client.client.order.call_count == 2

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, trading_client):
        """Test successful order cancellation."""
        # Arrange
        order_id = "12345"
        trading_client.client.cancel.return_value = {"status": "ok"}

        # Act
        result = await trading_client.cancel_order(order_id)

        # Assert
        assert result is True
        trading_client.client.cancel.assert_called_once_with(order_id)

    @pytest.mark.asyncio
    async def test_cancel_order_failed(self, trading_client):
        """Test failed order cancellation."""
        # Arrange
        order_id = "12345"
        trading_client.client.cancel.return_value = {"status": "err"}

        # Act
        result = await trading_client.cancel_order(order_id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_order_exception(self, trading_client):
        """Test order cancellation with exception."""
        # Arrange
        order_id = "12345"
        trading_client.client.cancel.side_effect = Exception("Network error")

        # Act
        result = await trading_client.cancel_order(order_id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_batch_orders(self, trading_client):
        """Test batch order cancellation."""
        # Arrange
        order_ids = ["12345", "67890", "11111"]
        trading_client.client.cancel.return_value = {"status": "ok"}

        # Act
        results = await trading_client.cancel_batch_orders(order_ids)

        # Assert
        assert len(results) == 3
        assert all(r is True for r in results)
        assert trading_client.client.cancel.call_count == 3

    @pytest.mark.asyncio
    async def test_cancel_batch_orders_mixed_results(self, trading_client):
        """Test batch cancellation with mixed success/failure."""
        # Arrange
        order_ids = ["12345", "67890"]

        # First call succeeds, second fails
        trading_client.client.cancel.side_effect = [
            {"status": "ok"},
            {"status": "err"}
        ]

        # Act
        results = await trading_client.cancel_batch_orders(order_ids)

        # Assert
        assert len(results) == 2
        assert results[0] is True
        assert results[1] is False

    @pytest.mark.asyncio
    async def test_modify_order_not_supported(self, trading_client):
        """Test that modify_order raises NotImplementedError."""
        # Arrange
        order_id = "12345"

        # Act & Assert
        with pytest.raises(NotImplementedError) as exc_info:
            await trading_client.modify_order(order_id, new_size=Decimal("0.2"))

        assert "doesn't support order modification" in str(exc_info.value)

    def test_to_hyperliquid_order_market(self, trading_client):
        """Test order format conversion for market order."""
        # Arrange
        order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        # Act
        hl_order = trading_client._to_hyperliquid_order(order)

        # Assert
        assert hl_order["coin"] == "BTC"
        assert hl_order["is_buy"] is True
        assert hl_order["sz"] == 0.1
        assert hl_order["limit_px"] is None
        assert "market" in hl_order["order_type"]

    def test_to_hyperliquid_order_limit(self, trading_client):
        """Test order format conversion for limit order."""
        # Arrange
        order = OrderRequest(
            coin="ETH",
            side=OrderSide.SELL,
            size=Decimal("1.5"),
            order_type=OrderType.LIMIT,
            limit_price=Decimal("3000.0"),
            time_in_force=TimeInForce.GTC,
        )

        # Act
        hl_order = trading_client._to_hyperliquid_order(order)

        # Assert
        assert hl_order["coin"] == "ETH"
        assert hl_order["is_buy"] is False
        assert hl_order["sz"] == 1.5
        assert hl_order["limit_px"] == 3000.0
        assert "limit" in hl_order["order_type"]
        assert hl_order["order_type"]["limit"]["tif"] == "Gtc"

    def test_to_hyperliquid_order_buy_vs_sell(self, trading_client):
        """Test is_buy flag is correct for buy vs sell."""
        # Arrange
        buy_order = OrderRequest(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )
        sell_order = OrderRequest(
            coin="BTC",
            side=OrderSide.SELL,
            size=Decimal("0.1"),
            order_type=OrderType.MARKET,
        )

        # Act
        buy_hl = trading_client._to_hyperliquid_order(buy_order)
        sell_hl = trading_client._to_hyperliquid_order(sell_order)

        # Assert
        assert buy_hl["is_buy"] is True
        assert sell_hl["is_buy"] is False


# ============================================================================
# Integration Tests
# ============================================================================


class TestHyperliquidIntegration:
    """Integration tests for HyperliquidInfo and HyperliquidTrading."""

    @pytest.mark.asyncio
    async def test_info_client_initialization(self):
        """Test HyperliquidInfo initializes correctly."""
        with patch("cc_flow.exchanges.hyperliquid.Info") as mock_info:
            client = HyperliquidInfo(base_url="https://api.hyperliquid-testnet.xyz")

            assert client.base_url == "https://api.hyperliquid-testnet.xyz"
            mock_info.assert_called_once_with("https://api.hyperliquid-testnet.xyz")

    @pytest.mark.asyncio
    async def test_trading_client_initialization_without_vault(self):
        """Test HyperliquidTrading initializes without vault."""
        with patch("cc_flow.exchanges.hyperliquid.Account") as mock_account, \
             patch("cc_flow.exchanges.hyperliquid.HLExchange") as mock_exchange:

            mock_account.from_key.return_value = MagicMock()

            client = HyperliquidTrading(
                base_url="https://api.hyperliquid-testnet.xyz",
                private_key="0x" + "a" * 64,
                account_address="0x1234567890abcdef",
                vault_address=None,
            )

            assert client.base_url == "https://api.hyperliquid-testnet.xyz"
            assert client.account_address == "0x1234567890abcdef"
            assert client.vault_address is None
            mock_account.from_key.assert_called_once()

    @pytest.mark.asyncio
    async def test_trading_client_initialization_with_vault(self):
        """Test HyperliquidTrading initializes with vault."""
        with patch("cc_flow.exchanges.hyperliquid.Account") as mock_account, \
             patch("cc_flow.exchanges.hyperliquid.HLExchange") as mock_exchange:

            mock_account.from_key.return_value = MagicMock()

            client = HyperliquidTrading(
                base_url="https://api.hyperliquid-testnet.xyz",
                private_key="0x" + "a" * 64,
                account_address="0x1234567890abcdef",
                vault_address="0xvault1234567890",
            )

            assert client.vault_address == "0xvault1234567890"

            # Verify vault_address passed to Exchange constructor
            call_kwargs = mock_exchange.call_args[1]
            assert call_kwargs["vault_address"] == "0xvault1234567890"
