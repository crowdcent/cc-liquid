"""
Base exchange interfaces for cc-flow.

This module defines abstract base classes and protocols for exchange integration,
providing a unified interface for different cryptocurrency exchanges.

Components:
    - ExchangeInfo: Protocol for exchange information/query operations
    - ExchangeTrading: Protocol for exchange trading/execution operations
    - Exchange: Abstract base class for exchange implementations

Design Principles:
    - Use Protocol for structural typing (duck typing compatibility)
    - Use ABC for concrete base class with shared logic
    - All exchange operations are async (network I/O)
    - Type-safe interfaces with complete type hints
    - Clean separation between read (info) and write (trading) operations

Architecture:
    The exchange interface is split into two protocols:
    - ExchangeInfo: Read-only operations (queries, market data)
    - ExchangeTrading: Write operations (orders, cancellations)

    This separation allows:
    - Different authentication levels (read-only vs trading access)
    - Independent testing and mocking
    - Clear separation of concerns

Example:
    >>> from cc_flow.exchanges.base import Exchange
    >>> class MyExchange(Exchange):
    ...     @property
    ...     def info(self) -> ExchangeInfo:
    ...         return self._info
    ...
    ...     @property
    ...     def trading(self) -> ExchangeTrading:
    ...         return self._trading
    ...
    ...     def parse_account_state(self, raw_data: dict) -> PortfolioSnapshot:
    ...         # Parse exchange-specific format to domain model
    ...         pass
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Protocol, runtime_checkable

from cc_flow.domain.account import PortfolioSnapshot
from cc_flow.domain.orders import OrderRequest, OrderResult


@runtime_checkable
class ExchangeInfo(Protocol):
    """
    Protocol for exchange information/query operations.

    This protocol defines read-only operations for querying exchange state,
    market data, and account information. All methods are async to support
    network I/O operations.

    Implementations must provide all methods with matching signatures.
    The @runtime_checkable decorator enables isinstance() checks at runtime.

    Methods are organized by category:
    - Account queries: get_account_state, get_open_positions
    - Order queries: get_open_orders, get_fill_history
    - Market data: get_market_prices, get_exchange_metadata, get_fee_rates

    Note:
        This is a Protocol, not an ABC. It uses structural typing, so any
        class that implements all methods with matching signatures will
        satisfy this protocol, even without explicit inheritance.
    """

    async def get_account_state(self, owner: str, vault: str | None = None) -> dict:
        """
        Get raw account state from exchange.

        Returns the complete account state including balance, margin usage,
        and leverage information in exchange-specific format.

        Args:
            owner: Account owner address (wallet address)
            vault: Optional vault address for sub-accounts

        Returns:
            Raw account state dictionary (exchange-specific format)

        Example:
            >>> info = exchange.info
            >>> state = await info.get_account_state("0x123...")
            >>> print(state["account_value"])
        """
        ...

    async def get_open_positions(self, owner: str, vault: str | None = None) -> list[dict]:
        """
        Get open positions.

        Returns all currently open positions for the account.

        Args:
            owner: Account owner address
            vault: Optional vault address for sub-accounts

        Returns:
            List of position dictionaries (exchange-specific format)

        Example:
            >>> positions = await info.get_open_positions("0x123...")
            >>> for pos in positions:
            ...     print(f"{pos['coin']}: {pos['size']}")
        """
        ...

    async def get_open_orders(self, owner: str) -> list[dict]:
        """
        Get open orders.

        Returns all currently open orders for the account.

        Args:
            owner: Account owner address

        Returns:
            List of order dictionaries (exchange-specific format)

        Example:
            >>> orders = await info.get_open_orders("0x123...")
            >>> print(f"Open orders: {len(orders)}")
        """
        ...

    async def get_fill_history(
        self,
        owner: str,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict]:
        """
        Get fill history.

        Returns historical order fills for the account, optionally filtered
        by time range.

        Args:
            owner: Account owner address
            start_time: Optional start timestamp (milliseconds)
            end_time: Optional end timestamp (milliseconds)

        Returns:
            List of fill dictionaries (exchange-specific format)

        Example:
            >>> fills = await info.get_fill_history("0x123...", start_time=1234567890000)
            >>> total_volume = sum(f["size"] * f["price"] for f in fills)
        """
        ...

    async def get_market_prices(self, coins: list[str]) -> dict[str, Decimal]:
        """
        Get current market prices for coins.

        Returns the current mark or mid price for requested coins.

        Args:
            coins: List of coin symbols (e.g., ["BTC", "ETH"])

        Returns:
            Dictionary mapping coin symbols to prices

        Example:
            >>> prices = await info.get_market_prices(["BTC", "ETH"])
            >>> print(f"BTC: ${prices['BTC']}")
        """
        ...

    async def get_exchange_metadata(self) -> dict:
        """
        Get exchange metadata.

        Returns exchange-level configuration including available markets,
        size decimals, price decimals, and other exchange-specific metadata.

        Returns:
            Exchange metadata dictionary

        Example:
            >>> metadata = await info.get_exchange_metadata()
            >>> btc_decimals = metadata["size_decimals"]["BTC"]
        """
        ...

    async def get_fee_rates(self, owner: str) -> dict[str, Decimal]:
        """
        Get fee rates for account.

        Returns the current maker/taker fee rates for the account.
        Fee rates may vary based on volume tier or other factors.

        Args:
            owner: Account owner address

        Returns:
            Dictionary with 'maker' and 'taker' fee rates

        Example:
            >>> fees = await info.get_fee_rates("0x123...")
            >>> print(f"Taker fee: {fees['taker'] * 100}%")
        """
        ...


@runtime_checkable
class ExchangeTrading(Protocol):
    """
    Protocol for exchange trading/execution operations.

    This protocol defines write operations for order submission, modification,
    and cancellation. All methods are async to support network I/O operations.

    Implementations must provide all methods with matching signatures.
    The @runtime_checkable decorator enables isinstance() checks at runtime.

    Methods are organized by category:
    - Order submission: submit_order, submit_batch_orders
    - Order cancellation: cancel_order, cancel_batch_orders
    - Order modification: modify_order

    Note:
        This is a Protocol, not an ABC. It uses structural typing, so any
        class that implements all methods with matching signatures will
        satisfy this protocol, even without explicit inheritance.
    """

    async def submit_order(self, order: OrderRequest) -> OrderResult:
        """
        Submit a single order.

        Submits an order to the exchange and returns the execution result.

        Args:
            order: Order request with all parameters

        Returns:
            OrderResult with execution details

        Example:
            >>> from cc_flow.domain.orders import OrderRequest, OrderSide, OrderType
            >>> order = OrderRequest(
            ...     coin="BTC",
            ...     side=OrderSide.BUY,
            ...     size=Decimal("0.1"),
            ...     order_type=OrderType.MARKET,
            ...     reduce_only=False
            ... )
            >>> result = await trading.submit_order(order)
            >>> print(f"Order ID: {result.order_id}")
        """
        ...

    async def submit_batch_orders(self, orders: list[OrderRequest]) -> list[OrderResult]:
        """
        Submit multiple orders in a batch.

        Submits multiple orders atomically or sequentially (exchange-dependent).
        Returns results in the same order as input.

        Args:
            orders: List of order requests

        Returns:
            List of OrderResults (same length as input)

        Example:
            >>> results = await trading.submit_batch_orders([order1, order2])
            >>> successful = [r for r in results if r.success]
            >>> print(f"{len(successful)}/{len(results)} orders succeeded")
        """
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order by ID.

        Attempts to cancel an open order. Returns True if successful.

        Args:
            order_id: Exchange-specific order identifier

        Returns:
            True if order was cancelled, False otherwise

        Example:
            >>> cancelled = await trading.cancel_order("order-123")
            >>> if cancelled:
            ...     print("Order cancelled successfully")
        """
        ...

    async def cancel_batch_orders(self, order_ids: list[str]) -> list[bool]:
        """
        Cancel multiple orders.

        Attempts to cancel multiple orders. Returns results in the same
        order as input.

        Args:
            order_ids: List of order identifiers

        Returns:
            List of boolean results (same length as input)

        Example:
            >>> results = await trading.cancel_batch_orders(["order-1", "order-2"])
            >>> success_count = sum(results)
            >>> print(f"Cancelled {success_count} orders")
        """
        ...

    async def modify_order(
        self,
        order_id: str,
        new_size: Decimal | None = None,
        new_price: Decimal | None = None,
    ) -> OrderResult:
        """
        Modify an existing order.

        Modifies the size and/or price of an open order. Not all exchanges
        support order modification (may cancel and replace instead).

        Args:
            order_id: Exchange-specific order identifier
            new_size: New order size (optional)
            new_price: New order price (optional)

        Returns:
            OrderResult with modification details

        Example:
            >>> result = await trading.modify_order(
            ...     "order-123",
            ...     new_size=Decimal("0.2")
            ... )
            >>> print(f"Modified order: {result.order_id}")
        """
        ...


class Exchange(ABC):
    """
    Abstract base class for exchange implementations.

    This ABC provides the common structure and interface for all exchange
    implementations. Subclasses must implement all abstract methods and
    properties.

    The Exchange class separates read (info) and write (trading) operations
    into two distinct clients, accessed via properties. This allows:
    - Different authentication levels
    - Independent testing/mocking
    - Clear separation of concerns

    Attributes:
        config: Exchange configuration dictionary
        _info: Internal info client instance
        _trading: Internal trading client instance

    Abstract Methods:
        - info: Property returning ExchangeInfo implementation
        - trading: Property returning ExchangeTrading implementation
        - parse_account_state: Parse raw account data to domain model
        - round_size: Round size to exchange precision
        - round_price: Round price to exchange precision
        - calculate_limit_price: Calculate limit price with slippage

    Example:
        >>> class MyExchange(Exchange):
        ...     def __init__(self, config: dict):
        ...         super().__init__(config)
        ...         self._info = MyExchangeInfo(config)
        ...         self._trading = MyExchangeTrading(config)
        ...
        ...     @property
        ...     def info(self) -> ExchangeInfo:
        ...         return self._info
        ...
        ...     # ... implement other abstract methods
    """

    def __init__(self, config: dict):
        """
        Initialize exchange with configuration.

        Args:
            config: Configuration dictionary with exchange-specific settings.
                   Typically includes API keys, endpoints, timeouts, etc.

        Example:
            >>> config = {
            ...     "api_key": "...",
            ...     "api_secret": "...",
            ...     "endpoint": "https://api.exchange.com"
            ... }
            >>> exchange = MyExchange(config)
        """
        self.config = config
        self._info: ExchangeInfo | None = None
        self._trading: ExchangeTrading | None = None

    @property
    @abstractmethod
    def info(self) -> ExchangeInfo:
        """
        Get info client.

        Returns the ExchangeInfo implementation for this exchange.
        Subclasses must implement this property to return a valid
        ExchangeInfo instance.

        Returns:
            ExchangeInfo implementation

        Example:
            >>> info = exchange.info
            >>> state = await info.get_account_state("0x123...")
        """
        ...

    @property
    @abstractmethod
    def trading(self) -> ExchangeTrading:
        """
        Get trading client.

        Returns the ExchangeTrading implementation for this exchange.
        Subclasses must implement this property to return a valid
        ExchangeTrading instance.

        Returns:
            ExchangeTrading implementation

        Example:
            >>> trading = exchange.trading
            >>> result = await trading.submit_order(order)
        """
        ...

    @abstractmethod
    def parse_account_state(self, raw_data: dict) -> PortfolioSnapshot:
        """
        Parse raw account state to domain model.

        Converts exchange-specific account data format to the standardized
        PortfolioSnapshot domain model. This method handles the transformation
        between exchange API responses and our internal data structures.

        Args:
            raw_data: Raw account state from exchange API

        Returns:
            PortfolioSnapshot with standardized account information

        Example:
            >>> raw_state = await exchange.info.get_account_state("0x123...")
            >>> snapshot = exchange.parse_account_state(raw_state)
            >>> print(f"Account value: ${snapshot.account.account_value}")
        """
        ...

    @abstractmethod
    def round_size(self, coin: str, size: Decimal) -> Decimal:
        """
        Round size to exchange precision.

        Different exchanges have different size precision requirements for
        each coin. This method rounds the size to the appropriate number
        of decimal places.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")
            size: Raw size value

        Returns:
            Rounded size value

        Example:
            >>> size = Decimal("0.123456")
            >>> rounded = exchange.round_size("BTC", size)
            >>> print(rounded)  # Decimal("0.123") if BTC uses 3 decimals
        """
        ...

    @abstractmethod
    def round_price(self, coin: str, price: Decimal) -> Decimal:
        """
        Round price to exchange precision.

        Different exchanges have different price precision requirements for
        each coin. This method rounds the price to the appropriate number
        of decimal places.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")
            price: Raw price value

        Returns:
            Rounded price value

        Example:
            >>> price = Decimal("50123.456")
            >>> rounded = exchange.round_price("BTC", price)
            >>> print(rounded)  # Decimal("50123.5") if BTC uses 1 decimal
        """
        ...

    @abstractmethod
    def calculate_limit_price(
        self,
        coin: str,
        side: str,
        reference_price: Decimal,
        slippage_tolerance: Decimal,
    ) -> Decimal:
        """
        Calculate limit price with slippage tolerance.

        For market orders, we typically use limit orders with a slippage
        tolerance to avoid excessive slippage. This method calculates the
        appropriate limit price based on the reference price and desired
        slippage tolerance.

        For buy orders: limit_price = reference_price * (1 + slippage)
        For sell orders: limit_price = reference_price * (1 - slippage)

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")
            side: Order side ("buy", "sell", "long", "short")
            reference_price: Reference price (e.g., current mark price)
            slippage_tolerance: Slippage tolerance as decimal (e.g., 0.001 = 0.1%)

        Returns:
            Calculated limit price (rounded to exchange precision)

        Example:
            >>> ref_price = Decimal("50000.00")
            >>> slippage = Decimal("0.001")  # 0.1%
            >>> limit = exchange.calculate_limit_price("BTC", "buy", ref_price, slippage)
            >>> print(limit)  # Decimal("50050.00")
        """
        ...
