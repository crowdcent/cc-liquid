"""
Mock exchange implementation for testing.

This module provides a complete mock exchange that implements all ExchangeInfo
and ExchangeTrading protocols without making actual API calls. Perfect for
unit testing trading logic, order management, and portfolio calculations.

Classes:
    MockExchangeInfo: Mock implementation of ExchangeInfo protocol
    MockExchangeTrading: Mock implementation of ExchangeTrading protocol
    MockExchange: Complete mock exchange with configurable behavior

Features:
    - Configurable fill behaviors (always_fill, always_fail, random)
    - Order tracking (submitted, cancelled)
    - Customizable account state and positions
    - Configurable market prices
    - Fee calculation
    - Protocol compliance for seamless integration

Example:
    >>> from cc_flow.exchanges.mock import MockExchange
    >>> from decimal import Decimal
    >>> exchange = MockExchange(
    ...     account_value=Decimal("100000.00"),
    ...     prices={"BTC": Decimal("50000.00")},
    ...     fill_behavior="always_fill"
    ... )
    >>> # Use in tests
    >>> state = await exchange.info.get_account_state("0x123")
    >>> result = await exchange.trading.submit_order(order_request)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from cc_flow.domain.account import AccountInfo, PortfolioSnapshot, Position
from cc_flow.domain.orders import OrderRequest, OrderResult, OrderSide, OrderStatus
from cc_flow.exchanges.base import Exchange, ExchangeInfo, ExchangeTrading


class MockExchangeInfo:
    """
    Mock implementation of ExchangeInfo protocol.

    Provides all read-only exchange operations with configurable mock data.
    All methods return data from the parent MockExchange instance.

    Attributes:
        exchange: Parent MockExchange instance

    Methods match ExchangeInfo protocol exactly for seamless testing.
    """

    def __init__(self, mock_exchange: MockExchange):
        """
        Initialize with parent exchange.

        Args:
            mock_exchange: Parent MockExchange instance containing mock data
        """
        self.exchange = mock_exchange

    async def get_account_state(self, owner: str, vault: str | None = None) -> dict:  # noqa: ARG002
        """
        Return mock account state.

        Args:
            owner: Account owner address (ignored in mock)
            vault: Optional vault address (ignored in mock)

        Returns:
            Dictionary with account_value and positions

        Example:
            >>> state = await info.get_account_state("0x123")
            >>> print(state["account_value"])
            '100000.00'
        """
        return {
            "account_value": str(self.exchange.account_value),
            "positions": [
                {
                    "coin": pos.coin,
                    "size": str(pos.size),
                    "side": pos.side,
                    "entry_price": str(pos.entry_price),
                    "mark_price": str(pos.mark_price),
                }
                for pos in self.exchange.positions
            ],
        }

    async def get_open_positions(self, owner: str, vault: str | None = None) -> list[dict]:  # noqa: ARG002
        """
        Return mock open positions.

        Args:
            owner: Account owner address (ignored in mock)
            vault: Optional vault address (ignored in mock)

        Returns:
            Empty list (mock returns no positions via this method)

        Note:
            Use get_account_state to get positions in this mock.
        """
        return []

    async def get_open_orders(self, owner: str) -> list[dict]:  # noqa: ARG002
        """
        Return mock open orders.

        Args:
            owner: Account owner address (ignored in mock)

        Returns:
            List of open orders tracked by exchange

        Example:
            >>> orders = await info.get_open_orders("0x123")
            >>> print(len(orders))
            0
        """
        return self.exchange.open_orders

    async def get_fill_history(
        self,
        owner: str,  # noqa: ARG002
        start_time: int | None = None,  # noqa: ARG002
        end_time: int | None = None,  # noqa: ARG002
    ) -> list[dict]:
        """
        Return mock fill history.

        Args:
            owner: Account owner address (ignored in mock)
            start_time: Optional start timestamp in milliseconds (ignored in mock)
            end_time: Optional end timestamp in milliseconds (ignored in mock)

        Returns:
            Empty list (mock returns no historical fills)
        """
        return []

    async def get_market_prices(self, coins: list[str]) -> dict[str, Decimal]:
        """
        Return mock market prices.

        Args:
            coins: List of coin symbols

        Returns:
            Dictionary mapping coin symbols to prices.
            Unknown coins return default price of 1000.0

        Example:
            >>> prices = await info.get_market_prices(["BTC", "ETH"])
            >>> print(prices["BTC"])
            Decimal('50000.00')
        """
        return {
            coin: self.exchange.prices.get(coin, Decimal("1000.0")) for coin in coins
        }

    async def get_exchange_metadata(self) -> dict:
        """
        Return mock exchange metadata.

        Returns:
            Dictionary with universe of available coins and their decimals

        Example:
            >>> metadata = await info.get_exchange_metadata()
            >>> print(metadata["universe"][0]["name"])
            'BTC'
        """
        return {
            "universe": [
                {"name": coin, "szDecimals": 2} for coin in self.exchange.prices
            ]
        }

    async def get_fee_rates(self, owner: str) -> dict[str, Decimal]:  # noqa: ARG002
        """
        Return mock fee rates.

        Args:
            owner: Account owner address (ignored in mock)

        Returns:
            Dictionary with maker and taker fee rates

        Example:
            >>> fees = await info.get_fee_rates("0x123")
            >>> print(fees["taker"])
            Decimal('0.0005')
        """
        return {"maker": Decimal("0.0002"), "taker": Decimal("0.0005")}


class MockExchangeTrading:
    """
    Mock implementation of ExchangeTrading protocol.

    Provides all write operations with configurable behavior and tracking.
    Simulates order execution based on fill_behavior setting.

    Attributes:
        exchange: Parent MockExchange instance

    The mock tracks all submitted and cancelled orders for verification in tests.
    """

    def __init__(self, mock_exchange: MockExchange):
        """
        Initialize with parent exchange.

        Args:
            mock_exchange: Parent MockExchange instance
        """
        self.exchange = mock_exchange

    async def submit_order(self, order: OrderRequest) -> OrderResult:
        """
        Submit mock order with configurable fill behavior.

        Args:
            order: Order request to submit

        Returns:
            OrderResult with status based on fill_behavior setting

        Behavior:
            - always_fill: Returns FILLED with mock execution data
            - always_fail: Returns FAILED with error message
            - random: Currently same as always_fill (can be extended)

        Example:
            >>> result = await trading.submit_order(order)
            >>> assert result.status == OrderStatus.FILLED
        """
        self.exchange.submitted_orders.append(order)

        # Check fill behavior
        if self.exchange.fill_behavior == "always_fail":
            return OrderResult(
                order_request=order,
                status=OrderStatus.FAILED,
                error_message="Mock failure",
            )

        # Always fill or random (simplified to always fill)
        order_id = str(uuid.uuid4())
        price = self.exchange.prices.get(order.coin, Decimal("1000.0"))

        # Calculate fee (taker fee of 0.0005)
        notional = order.size * price
        fee = notional * Decimal("0.0005")

        return OrderResult(
            order_request=order,
            status=OrderStatus.FILLED,
            filled_size=order.size,
            average_price=price,
            total_fee=fee,
            order_id=order_id,
            submitted_at=datetime.now(UTC),
            filled_at=datetime.now(UTC),
        )

    async def submit_batch_orders(self, orders: list[OrderRequest]) -> list[OrderResult]:
        """
        Submit batch of orders.

        Args:
            orders: List of order requests

        Returns:
            List of OrderResults in same order as input

        Example:
            >>> results = await trading.submit_batch_orders([order1, order2])
            >>> assert len(results) == 2
        """
        return [await self.submit_order(order) for order in orders]

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel mock order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Always True (mock always succeeds)

        Example:
            >>> success = await trading.cancel_order("order-123")
            >>> assert success is True
        """
        self.exchange.cancelled_orders.append(order_id)
        return True

    async def cancel_batch_orders(self, order_ids: list[str]) -> list[bool]:
        """
        Cancel batch of orders.

        Args:
            order_ids: List of order IDs to cancel

        Returns:
            List of booleans (all True in mock)

        Example:
            >>> results = await trading.cancel_batch_orders(["id1", "id2"])
            >>> assert all(results)
        """
        return [await self.cancel_order(oid) for oid in order_ids]

    async def modify_order(
        self,
        order_id: str,
        new_size: Decimal | None = None,
        new_price: Decimal | None = None,  # noqa: ARG002
    ) -> OrderResult:
        """
        Modify mock order.

        Args:
            order_id: Order ID to modify
            new_size: New order size (optional)
            new_price: New order price (optional)

        Returns:
            OrderResult with FILLED status (simplified mock)

        Note:
            This is a simplified implementation that always succeeds.
            Real exchanges may have more complex modify logic.

        Example:
            >>> result = await trading.modify_order("id", new_size=Decimal("2.0"))
            >>> assert result.status == OrderStatus.FILLED
        """
        # Simplified: return success
        return OrderResult(
            order_request=OrderRequest(
                coin="BTC",
                side=OrderSide.BUY,
                size=new_size or Decimal("1.0"),
                order_type="market",  # type: ignore
            ),
            status=OrderStatus.FILLED,
            order_id=order_id,
        )


class MockExchange(Exchange):
    """
    Mock exchange for testing without actual API calls.

    Provides a complete exchange implementation with configurable behavior,
    perfect for unit testing trading strategies, order management, and
    portfolio calculations.

    Attributes:
        account_value: Mock account value in USD
        positions: List of mock positions
        prices: Dictionary of coin prices
        fill_behavior: How orders should be filled (always_fill/always_fail/random)
        submitted_orders: List of submitted orders (for verification)
        cancelled_orders: List of cancelled order IDs (for verification)
        open_orders: List of open orders

    Example:
        >>> exchange = MockExchange(
        ...     account_value=Decimal("50000.00"),
        ...     prices={"BTC": Decimal("45000.00")},
        ...     fill_behavior="always_fill"
        ... )
        >>> # Test trading logic
        >>> snapshot = await exchange.info.get_account_state("0x123")
        >>> result = await exchange.trading.submit_order(order)
    """

    def __init__(
        self,
        config: dict | None = None,
        account_value: Decimal = Decimal("100000.0"),
        positions: list[Position] | None = None,
        prices: dict[str, Decimal] | None = None,
        fill_behavior: Literal["always_fill", "always_fail", "random"] = "always_fill",
    ):
        """
        Initialize mock exchange.

        Args:
            config: Configuration dictionary (optional)
            account_value: Initial account value (default: 100000.0)
            positions: List of positions (default: empty)
            prices: Dictionary of coin prices (default: BTC/ETH)
            fill_behavior: Order fill behavior (default: always_fill)

        Example:
            >>> exchange = MockExchange(
            ...     account_value=Decimal("25000.00"),
            ...     fill_behavior="always_fail"
            ... )
        """
        super().__init__(config or {})
        self.account_value = account_value
        self.positions = positions or []
        self.prices = prices or {"BTC": Decimal("50000.0"), "ETH": Decimal("3000.0")}
        self.fill_behavior = fill_behavior

        # Tracking
        self.submitted_orders: list[OrderRequest] = []
        self.cancelled_orders: list[str] = []
        self.open_orders: list[dict] = []

        # Clients
        self._info = MockExchangeInfo(self)
        self._trading = MockExchangeTrading(self)

    @property
    def info(self) -> ExchangeInfo:
        """
        Get info client.

        Returns:
            MockExchangeInfo instance implementing ExchangeInfo protocol

        Example:
            >>> info = exchange.info
            >>> state = await info.get_account_state("0x123")
        """
        return self._info  # type: ignore

    @property
    def trading(self) -> ExchangeTrading:
        """
        Get trading client.

        Returns:
            MockExchangeTrading instance implementing ExchangeTrading protocol

        Example:
            >>> trading = exchange.trading
            >>> result = await trading.submit_order(order)
        """
        return self._trading  # type: ignore

    def parse_account_state(self, raw_data: dict) -> PortfolioSnapshot:
        """
        Parse mock account state to PortfolioSnapshot.

        Args:
            raw_data: Raw account data dictionary

        Returns:
            PortfolioSnapshot with account info and positions

        Example:
            >>> raw = {"account_value": "100000.00"}
            >>> snapshot = exchange.parse_account_state(raw)
            >>> print(snapshot.account.account_value)
            Decimal('100000.00')
        """
        account_info = AccountInfo(
            account_value=Decimal(raw_data.get("account_value", str(self.account_value))),
            total_position_value=Decimal("0"),
            margin_used=Decimal("0"),
            free_collateral=Decimal(raw_data.get("account_value", str(self.account_value))),
            cash_balance=Decimal(raw_data.get("account_value", str(self.account_value))),
            withdrawable=Decimal(raw_data.get("account_value", str(self.account_value))),
            current_leverage=Decimal("0"),
        )
        return PortfolioSnapshot(account=account_info, positions=self.positions)

    def round_size(self, coin: str, size: Decimal) -> Decimal:  # noqa: ARG002
        """
        Round size to 2 decimals.

        Args:
            coin: Coin symbol (ignored in mock)
            size: Size to round

        Returns:
            Size rounded to 2 decimal places

        Example:
            >>> exchange.round_size("BTC", Decimal("1.23456"))
            Decimal('1.23')
        """
        return Decimal(str(round(float(size), 2)))

    def round_price(self, coin: str, price: Decimal) -> Decimal:  # noqa: ARG002
        """
        Round price to 2 decimals.

        Args:
            coin: Coin symbol (ignored in mock)
            price: Price to round

        Returns:
            Price rounded to 2 decimal places

        Example:
            >>> exchange.round_price("BTC", Decimal("50123.456"))
            Decimal('50123.46')
        """
        return Decimal(str(round(float(price), 2)))

    def calculate_limit_price(
        self,
        coin: str,
        side: str,
        reference_price: Decimal,
        slippage_tolerance: Decimal,
    ) -> Decimal:
        """
        Calculate limit price with slippage tolerance.

        Args:
            coin: Coin symbol (ignored in mock)
            side: Order side (buy/sell/long/short)
            reference_price: Reference market price
            slippage_tolerance: Slippage tolerance as decimal (e.g., 0.001 = 0.1%)

        Returns:
            Limit price with slippage applied and rounded

        Example:
            >>> price = exchange.calculate_limit_price(
            ...     "BTC", "buy", Decimal("50000.00"), Decimal("0.001")
            ... )
            >>> print(price)
            Decimal('50050.00')
        """
        # Normalize side
        side_lower = side.lower()

        # Buy/long: add slippage, Sell/short: subtract slippage
        if side_lower in ("buy", "long"):
            limit = reference_price * (Decimal("1.0") + slippage_tolerance)
        else:
            limit = reference_price * (Decimal("1.0") - slippage_tolerance)

        return self.round_price(coin, limit)
