"""Hyperliquid exchange implementation.

This module implements Hyperliquid-specific exchange clients for info (queries)
and trading (order execution).

Components:
    - HyperliquidInfo: Read-only queries (account, positions, orders, fills, prices)
    - HyperliquidTrading: Order execution and management

Design:
    - Wraps hyperliquid-python-sdk with clean async interface
    - Info client uses owner/vault address for queries
    - Trading client uses agent wallet private key for signing
    - All monetary values use Decimal for precision
    - Comprehensive error handling with logging

Hyperliquid Specifics:
    - Fixed fee rates: 2 bps maker, 5 bps taker
    - Agent wallets have independent nonce sequences
    - Vault addresses override owner for queries
    - Order modification not supported (use cancel + replace)

Example:
    >>> info = HyperliquidInfo(base_url="https://api.hyperliquid-testnet.xyz")
    >>> state = await info.get_account_state("0x123...")
    >>>
    >>> trading = HyperliquidTrading(
    ...     base_url="https://api.hyperliquid-testnet.xyz",
    ...     private_key="0x...",
    ...     account_address="0x123...",
    ... )
    >>> result = await trading.submit_order(order_request)
"""

from __future__ import annotations

from decimal import Decimal

from eth_account import Account
from hyperliquid.exchange import Exchange as HLExchange
from hyperliquid.info import Info

from cc_flow.domain.account import AccountInfo, PortfolioSnapshot, Position
from cc_flow.domain.config import ExchangeProfile
from cc_flow.domain.orders import OrderRequest, OrderResult, OrderSide, OrderStatus
from cc_flow.exchanges.base import Exchange
from cc_flow.utils.logger_config import log


class HyperliquidInfo:
    """Hyperliquid info/query client.

    Provides read-only access to Hyperliquid exchange data including account state,
    positions, orders, fills, market prices, and exchange metadata.

    All methods are async to support network I/O operations. The client uses
    the owner or vault address to query account-specific data.

    Attributes:
        base_url: Hyperliquid API endpoint URL
        client: Underlying Info SDK client

    Example:
        >>> info = HyperliquidInfo(base_url="https://api.hyperliquid-testnet.xyz")
        >>> state = await info.get_account_state("0x123...")
        >>> prices = await info.get_market_prices(["BTC", "ETH"])
    """

    def __init__(self, base_url: str):
        """Initialize Hyperliquid info client.

        Args:
            base_url: Hyperliquid API endpoint (mainnet or testnet)

        Example:
            >>> info = HyperliquidInfo("https://api.hyperliquid-testnet.xyz")
        """
        self.base_url = base_url
        self.client = Info(base_url)

    async def get_account_state(self, owner: str, vault: str | None = None) -> dict:
        """Get account state from Hyperliquid.

        Returns the complete account state including balance, margin usage,
        and leverage information in Hyperliquid's format.

        Args:
            owner: Account owner address (wallet address)
            vault: Optional vault address (overrides owner if provided)

        Returns:
            Raw account state dictionary with marginSummary and assetPositions

        Example:
            >>> state = await info.get_account_state("0x123...")
            >>> account_value = state["marginSummary"]["accountValue"]
        """
        address = vault if vault else owner
        state = self.client.user_state(address)
        return state

    async def get_open_positions(self, owner: str, vault: str | None = None) -> list[dict]:
        """Get open positions.

        Returns all currently open positions for the account.

        Args:
            owner: Account owner address
            vault: Optional vault address (overrides owner if provided)

        Returns:
            List of position dictionaries with coin, size, entry price, etc.

        Example:
            >>> positions = await info.get_open_positions("0x123...")
            >>> for pos in positions:
            ...     print(f"{pos['position']['coin']}: {pos['position']['szi']}")
        """
        address = vault if vault else owner
        state = self.client.user_state(address)
        return state.get("assetPositions", [])

    async def get_open_orders(self, owner: str) -> list[dict]:
        """Get open orders.

        Returns all currently open orders for the account.

        Args:
            owner: Account owner address

        Returns:
            List of order dictionaries with coin, side, size, limit price, etc.

        Example:
            >>> orders = await info.get_open_orders("0x123...")
            >>> print(f"Open orders: {len(orders)}")
        """
        orders = self.client.open_orders(owner)
        return orders

    async def get_fill_history(
        self,
        owner: str,
        start_time: int | None = None,  # noqa: ARG002
        end_time: int | None = None,  # noqa: ARG002
    ) -> list[dict]:
        """Get fill history.

        Returns historical order fills for the account. Note: Current implementation
        does not filter by time range (SDK limitation).

        Args:
            owner: Account owner address
            start_time: Optional start timestamp in milliseconds (not yet implemented)
            end_time: Optional end timestamp in milliseconds (not yet implemented)

        Returns:
            List of fill dictionaries with coin, price, size, timestamp, etc.

        Example:
            >>> fills = await info.get_fill_history("0x123...")
            >>> total_volume = sum(float(f["sz"]) * float(f["px"]) for f in fills)
        """
        # TODO: Add time filtering when SDK supports it
        fills = self.client.user_fills(owner)
        return fills

    async def get_market_prices(self, coins: list[str]) -> dict[str, Decimal]:
        """Get current market prices for coins.

        Returns the current mid price for requested coins.

        Args:
            coins: List of coin symbols (e.g., ["BTC", "ETH"])

        Returns:
            Dictionary mapping coin symbols to Decimal prices

        Example:
            >>> prices = await info.get_market_prices(["BTC", "ETH"])
            >>> print(f"BTC: ${prices['BTC']}")
        """
        all_mids = self.client.all_mids()
        prices = {}
        for coin in coins:
            if coin in all_mids:
                prices[coin] = Decimal(str(all_mids[coin]))
        return prices

    async def get_exchange_metadata(self) -> dict:
        """Get exchange metadata.

        Returns exchange-level configuration including available markets,
        size decimals, price decimals, max leverage, and other metadata.

        Returns:
            Exchange metadata dictionary with universe of trading pairs

        Example:
            >>> metadata = await info.get_exchange_metadata()
            >>> btc_info = next(m for m in metadata["universe"] if m["name"] == "BTC")
            >>> sz_decimals = btc_info["szDecimals"]
        """
        meta = self.client.meta()
        return meta

    async def get_fee_rates(self, owner: str) -> dict[str, Decimal]:  # noqa: ARG002
        """Get fee rates for account.

        Returns the fixed Hyperliquid fee rates. These are constant for all users
        and do not vary by volume tier.

        Args:
            owner: Account owner address (unused, kept for interface compatibility)

        Returns:
            Dictionary with 'maker' and 'taker' fee rates as Decimals

        Example:
            >>> fees = await info.get_fee_rates("0x123...")
            >>> print(f"Taker fee: {fees['taker'] * 100}%")  # 0.05%
        """
        # Hyperliquid has fixed fee rates
        return {
            "maker": Decimal("0.00020"),  # 2 bps
            "taker": Decimal("0.00050"),  # 5 bps
        }


class HyperliquidTrading:
    """Hyperliquid trading/execution client.

    Provides order submission, cancellation, and management functionality.
    Uses agent wallet private key for signing transactions.

    All methods are async to support network I/O operations. The client
    handles order format conversion between domain models and Hyperliquid SDK.

    Attributes:
        base_url: Hyperliquid API endpoint URL
        account_address: Owner account address
        vault_address: Optional vault address
        client: Underlying Exchange SDK client

    Example:
        >>> trading = HyperliquidTrading(
        ...     base_url="https://api.hyperliquid-testnet.xyz",
        ...     private_key="0x...",
        ...     account_address="0x123...",
        ... )
        >>> result = await trading.submit_order(order_request)
    """

    def __init__(
        self,
        base_url: str,
        private_key: str,
        account_address: str,
        vault_address: str | None = None,
    ):
        """Initialize Hyperliquid trading client.

        Args:
            base_url: Hyperliquid API endpoint (mainnet or testnet)
            private_key: Agent wallet private key for signing (hex string)
            account_address: Owner account address
            vault_address: Optional vault address for trading

        Example:
            >>> trading = HyperliquidTrading(
            ...     base_url="https://api.hyperliquid-testnet.xyz",
            ...     private_key="0x" + "a" * 64,
            ...     account_address="0x123...",
            ... )
        """
        self.base_url = base_url
        self.account_address = account_address
        self.vault_address = vault_address

        # Initialize exchange client with agent wallet
        account = Account.from_key(private_key)
        self.client = HLExchange(account, base_url, vault_address=vault_address)

    async def submit_order(self, order: OrderRequest) -> OrderResult:
        """Submit order to Hyperliquid.

        Converts OrderRequest to Hyperliquid format and submits to exchange.
        Returns OrderResult with execution status and details.

        Args:
            order: Order request with all parameters

        Returns:
            OrderResult with status, order ID, and error info if failed

        Example:
            >>> order = OrderRequest(
            ...     coin="BTC",
            ...     side=OrderSide.BUY,
            ...     size=Decimal("0.1"),
            ...     order_type=OrderType.MARKET,
            ... )
            >>> result = await trading.submit_order(order)
            >>> if result.is_success:
            ...     print(f"Order ID: {result.order_id}")
        """
        try:
            # Convert to Hyperliquid format
            hl_order = self._to_hyperliquid_order(order)

            # Submit order
            result = self.client.order(
                hl_order["coin"],
                hl_order["is_buy"],
                hl_order["sz"],
                hl_order["limit_px"],
                hl_order["order_type"],
                reduce_only=order.reduce_only,
            )

            # Parse result
            if result["status"] == "ok":
                # Extract order ID from response
                order_id = ""
                try:
                    statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                    if statuses:
                        order_id = str(statuses[0].get("resting", {}).get("oid", ""))
                except (KeyError, IndexError, AttributeError):
                    pass

                return OrderResult(
                    order_request=order,
                    status=OrderStatus.FILLED,
                    order_id=order_id,
                )
            else:
                return OrderResult(
                    order_request=order,
                    status=OrderStatus.FAILED,
                    error_message=str(result),
                )

        except Exception as e:
            log.error(f"Order submission failed: {e}")
            return OrderResult(
                order_request=order,
                status=OrderStatus.FAILED,
                error_message=str(e),
            )

    async def submit_batch_orders(self, orders: list[OrderRequest]) -> list[OrderResult]:
        """Submit batch of orders.

        Submits multiple orders sequentially (Hyperliquid doesn't support
        atomic batch submission).

        Args:
            orders: List of order requests

        Returns:
            List of OrderResults in same order as input

        Example:
            >>> results = await trading.submit_batch_orders([order1, order2])
            >>> successful = [r for r in results if r.is_success]
        """
        return [await self.submit_order(order) for order in orders]

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order by ID.

        Args:
            order_id: Hyperliquid order ID

        Returns:
            True if cancellation successful, False otherwise

        Example:
            >>> success = await trading.cancel_order("12345")
        """
        try:
            result = self.client.cancel(order_id)
            return result["status"] == "ok"
        except Exception as e:
            log.error(f"Cancel failed: {e}")
            return False

    async def cancel_batch_orders(self, order_ids: list[str]) -> list[bool]:
        """Cancel multiple orders.

        Cancels orders sequentially.

        Args:
            order_ids: List of Hyperliquid order IDs

        Returns:
            List of boolean results in same order as input

        Example:
            >>> results = await trading.cancel_batch_orders(["123", "456"])
            >>> success_count = sum(results)
        """
        return [await self.cancel_order(oid) for oid in order_ids]

    async def modify_order(
        self,
        order_id: str,
        new_size: Decimal | None = None,
        new_price: Decimal | None = None,
    ) -> OrderResult:
        """Modify order (not supported by Hyperliquid).

        Hyperliquid does not support order modification. Use cancel and replace
        pattern instead.

        Args:
            order_id: Order ID
            new_size: New size (unused)
            new_price: New price (unused)

        Raises:
            NotImplementedError: Always raised

        Example:
            >>> # Don't use this - will raise NotImplementedError
            >>> # Instead: cancel old order and submit new one
        """
        raise NotImplementedError(
            "Hyperliquid doesn't support order modification - use cancel and replace"
        )

    def _to_hyperliquid_order(self, order: OrderRequest) -> dict:
        """Convert OrderRequest to Hyperliquid SDK format.

        Transforms domain OrderRequest model to the dictionary format expected
        by the Hyperliquid SDK's order() method.

        Args:
            order: Domain order request

        Returns:
            Dictionary with Hyperliquid SDK parameters

        Example:
            >>> order = OrderRequest(coin="BTC", side=OrderSide.BUY, ...)
            >>> hl_order = self._to_hyperliquid_order(order)
            >>> # Returns: {"coin": "BTC", "is_buy": True, ...}
        """
        # Determine order type structure
        if order.order_type.value == "limit":
            order_type_dict = {"limit": {"tif": order.time_in_force.value}}
            limit_px = float(order.limit_price) if order.limit_price else None
        else:
            order_type_dict = {"market": {}}
            limit_px = None

        return {
            "coin": order.coin,
            "is_buy": order.side == OrderSide.BUY,
            "sz": float(order.size),
            "limit_px": limit_px,
            "order_type": order_type_dict,
        }


class HyperliquidExchange(Exchange):
    """Hyperliquid exchange implementation.

    Combines HyperliquidInfo and HyperliquidTrading clients to provide
    a complete exchange interface implementing the Exchange ABC.

    This class serves as the main entry point for interacting with Hyperliquid,
    supporting both read-only (info) and trading operations. The class handles:
    - Automatic URL selection based on testnet flag
    - Optional trading client initialization based on signer availability
    - Vault address support for managed accounts
    - Context manager protocol for async resource management

    Attributes:
        owner_address: Account owner wallet address
        vault_address: Optional vault address (overrides owner for queries)
        base_url: Hyperliquid API endpoint URL
        is_testnet: Whether this is a testnet connection
        _info: HyperliquidInfo client instance
        _trading: Optional HyperliquidTrading client (None if no signer)

    Example:
        >>> # Read-only mode
        >>> exchange = HyperliquidExchange(
        ...     owner_address="0x123...",
        ...     is_testnet=True
        ... )
        >>> state = await exchange.info.get_account_state(exchange.owner_address)
        >>>
        >>> # Trading mode
        >>> exchange = HyperliquidExchange(
        ...     owner_address="0x123...",
        ...     signer_private_key="0x...",
        ...     is_testnet=True
        ... )
        >>> result = await exchange.trading.submit_order(order)
    """

    def __init__(
        self,
        owner_address: str,
        signer_private_key: str | None = None,
        vault_address: str | None = None,
        base_url: str = "https://api.hyperliquid.xyz",
        is_testnet: bool = False,
    ):
        """Initialize Hyperliquid exchange.

        Creates info client (always) and trading client (if signer provided).
        The base_url is automatically set to testnet URL if is_testnet=True.

        Args:
            owner_address: Account owner wallet address (used for queries)
            signer_private_key: Optional agent wallet private key for signing transactions
            vault_address: Optional vault address for managed accounts
            base_url: API base URL (overridden if is_testnet=True)
            is_testnet: Whether to use testnet (changes base_url)

        Example:
            >>> # Testnet read-only
            >>> exchange = HyperliquidExchange(
            ...     owner_address="0x123...",
            ...     is_testnet=True
            ... )
            >>>
            >>> # Mainnet with trading
            >>> exchange = HyperliquidExchange(
            ...     owner_address="0x123...",
            ...     signer_private_key="0x...",
            ...     vault_address="0xabc...",
            ... )
        """
        # Store instance attributes
        self.owner_address = owner_address
        self.vault_address = vault_address
        self.is_testnet = is_testnet

        # Override base_url if testnet
        if is_testnet:
            self.base_url = "https://api.hyperliquid-testnet.xyz/info"
        else:
            self.base_url = base_url

        # Initialize base class with config dict FIRST
        config = {
            "owner_address": owner_address,
            "vault_address": vault_address,
            "base_url": self.base_url,
            "is_testnet": is_testnet,
        }
        super().__init__(config)

        # Now initialize clients (after base class init)
        # Initialize info client (always available)
        self._info = HyperliquidInfo(base_url=self.base_url)

        # Initialize trading client (only if signer provided)
        if signer_private_key:
            self._trading = HyperliquidTrading(
                base_url=self.base_url,
                private_key=signer_private_key,
                account_address=owner_address,
                vault_address=vault_address,
            )

    @property
    def info(self) -> HyperliquidInfo:
        """Get info/query client.

        The info client provides read-only access to exchange data including
        account state, positions, orders, fills, market prices, and metadata.

        Returns:
            HyperliquidInfo client instance

        Example:
            >>> exchange = HyperliquidExchange(owner_address="0x123...", is_testnet=True)
            >>> state = await exchange.info.get_account_state("0x123...")
            >>> prices = await exchange.info.get_market_prices(["BTC", "ETH"])
        """
        return self._info

    @property
    def trading(self) -> HyperliquidTrading:
        """Get trading/execution client.

        The trading client provides order submission and management functionality.
        Only available if signer_private_key was provided during initialization.

        Returns:
            HyperliquidTrading client instance

        Raises:
            ValueError: If no signer_private_key was provided during initialization

        Example:
            >>> exchange = HyperliquidExchange(
            ...     owner_address="0x123...",
            ...     signer_private_key="0x...",
            ...     is_testnet=True
            ... )
            >>> result = await exchange.trading.submit_order(order_request)
        """
        if self._trading is None:
            raise ValueError("Trading requires signer_private_key")
        return self._trading

    def is_ready_for_trading(self) -> bool:
        """Check if exchange is configured for trading.

        Returns True if a signer was provided and trading operations are available.
        Returns False if exchange is in read-only mode.

        Returns:
            True if trading is enabled, False otherwise

        Example:
            >>> readonly = HyperliquidExchange(owner_address="0x123...", is_testnet=True)
            >>> readonly.is_ready_for_trading()
            False
            >>>
            >>> trading = HyperliquidExchange(
            ...     owner_address="0x123...",
            ...     signer_private_key="0x...",
            ...     is_testnet=True
            ... )
            >>> trading.is_ready_for_trading()
            True
        """
        return self._trading is not None

    def get_effective_address(self) -> str:
        """Get the address used for queries.

        Returns the vault address if set, otherwise returns the owner address.
        This is the address that should be used for account state queries.

        Returns:
            Vault address if set, otherwise owner address

        Example:
            >>> exchange = HyperliquidExchange(
            ...     owner_address="0x111...",
            ...     vault_address="0x222...",
            ...     is_testnet=True
            ... )
            >>> exchange.get_effective_address()
            '0x222...'
            >>>
            >>> exchange_no_vault = HyperliquidExchange(
            ...     owner_address="0x111...",
            ...     is_testnet=True
            ... )
            >>> exchange_no_vault.get_effective_address()
            '0x111...'
        """
        return self.vault_address if self.vault_address else self.owner_address

    @classmethod
    def from_profile(
        cls, profile: ExchangeProfile, signer_private_key: str | None = None
    ) -> HyperliquidExchange:
        """Create exchange from configuration profile.

        Factory method to create a HyperliquidExchange instance from an
        ExchangeProfile configuration object. This is the recommended way
        to create exchanges from application configuration.

        Args:
            profile: Exchange profile configuration
            signer_private_key: Optional private key (if not loaded from env)

        Returns:
            Configured HyperliquidExchange instance

        Example:
            >>> from cc_flow.domain.config import ExchangeProfile
            >>> profile = ExchangeProfile(
            ...     name="mainnet",
            ...     exchange="hyperliquid",
            ...     owner_address="0x123...",
            ...     vault_address="0xabc...",
            ...     is_testnet=False
            ... )
            >>> exchange = HyperliquidExchange.from_profile(profile)
            >>> # Or with explicit signer:
            >>> exchange = HyperliquidExchange.from_profile(profile, signer_private_key="0x...")
        """
        return cls(
            owner_address=profile.owner_address,
            signer_private_key=signer_private_key,
            vault_address=profile.vault_address,
            is_testnet=profile.is_testnet,
        )

    async def __aenter__(self):
        """Async context manager entry.

        Supports using the exchange as an async context manager for
        automatic resource cleanup.

        Returns:
            Self (the exchange instance)

        Example:
            >>> async with HyperliquidExchange(...) as exchange:
            ...     state = await exchange.info.get_account_state("0x123...")
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit.

        Cleanup resources when exiting async context manager.
        Currently no cleanup is needed for Hyperliquid clients.

        Args:
            exc_type: Exception type (if exception occurred)
            exc_val: Exception value (if exception occurred)
            exc_tb: Exception traceback (if exception occurred)

        Example:
            >>> async with exchange:
            ...     # Resources automatically cleaned up on exit
            ...     pass
        """
        # No cleanup needed for Hyperliquid clients
        pass

    def parse_account_state(self, raw_data: dict) -> PortfolioSnapshot:
        """Parse raw Hyperliquid account state to PortfolioSnapshot.

        Converts Hyperliquid-specific account data format to standardized
        domain model. Parses margin summary and asset positions.

        Args:
            raw_data: Raw account state from Hyperliquid API

        Returns:
            PortfolioSnapshot with parsed account and position information

        Example:
            >>> raw = await exchange.info.get_account_state("0x123...")
            >>> snapshot = exchange.parse_account_state(raw)
            >>> print(f"Account value: ${snapshot.account.account_value}")
        """
        # Parse margin summary
        margin_summary = raw_data.get("marginSummary", {})
        account = AccountInfo(
            account_value=Decimal(str(margin_summary.get("accountValue", "0"))),
            total_position_value=Decimal(str(margin_summary.get("totalNtlPos", "0"))),
            margin_used=Decimal(str(margin_summary.get("totalMarginUsed", "0"))),
            free_collateral=Decimal(str(margin_summary.get("totalRawUsd", "0"))),
            cash_balance=Decimal(str(margin_summary.get("totalRawUsd", "0"))),
            withdrawable=Decimal(str(margin_summary.get("withdrawable", "0"))),
            current_leverage=Decimal(str(margin_summary.get("accountValue", "1")))
            / Decimal(str(margin_summary.get("totalNtlPos", "1")))
            if Decimal(str(margin_summary.get("totalNtlPos", "0"))) != Decimal("0")
            else Decimal("0"),
            raw_data=margin_summary,
        )

        # Parse positions
        positions = []
        for asset_pos in raw_data.get("assetPositions", []):
            pos = asset_pos.get("position", {})
            coin = pos.get("coin", "")
            szi = Decimal(str(pos.get("szi", "0")))
            entry_px = Decimal(str(pos.get("entryPx", "0")))
            position_value = Decimal(str(pos.get("positionValue", "0")))
            unrealized_pnl = Decimal(str(pos.get("unrealizedPnl", "0")))
            return_pct = Decimal(str(pos.get("returnOnEquity", "0")))
            liquidation_px = pos.get("liquidationPx")
            margin_used = Decimal(str(pos.get("marginUsed", "0")))

            # Determine side and size
            if szi > 0:
                side = "LONG"
                size = szi
            elif szi < 0:
                side = "SHORT"
                size = abs(szi)
            else:
                continue  # Skip zero positions

            # Get current mark price from position value
            mark_price = position_value / size if size != Decimal("0") else entry_px

            position = Position(
                coin=coin,
                side=side,
                size=size,
                entry_price=entry_px,
                mark_price=mark_price,
                value=position_value,
                unrealized_pnl=unrealized_pnl,
                return_pct=return_pct,
                liquidation_price=Decimal(str(liquidation_px)) if liquidation_px else None,
                margin_used=margin_used,
            )
            positions.append(position)

        return PortfolioSnapshot(account=account, positions=positions)

    def round_size(self, coin: str, size: Decimal) -> Decimal:  # noqa: ARG002
        """Round size to Hyperliquid precision.

        Uses exchange metadata to determine size decimals for the coin
        and rounds accordingly.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")
            size: Raw size value

        Returns:
            Rounded size value

        Example:
            >>> exchange.round_size("BTC", Decimal("0.123456"))
            Decimal("0.1235")  # If BTC uses 4 decimals
        """
        # TODO: Fetch from exchange metadata - for now use sensible defaults
        # Most coins use 4 decimal places for size on Hyperliquid
        decimals = 4

        # Round to specified decimals
        quantizer = Decimal("1") / (Decimal("10") ** decimals)
        return size.quantize(quantizer)

    def round_price(self, coin: str, price: Decimal) -> Decimal:  # noqa: ARG002
        """Round price to Hyperliquid precision.

        Uses exchange metadata to determine price decimals for the coin
        and rounds accordingly.

        Args:
            coin: Coin symbol (e.g., "BTC", "ETH")
            price: Raw price value

        Returns:
            Rounded price value

        Example:
            >>> exchange.round_price("BTC", Decimal("50123.456"))
            Decimal("50123.5")  # If BTC uses 1 decimal
        """
        # TODO: Fetch from exchange metadata - for now use sensible defaults
        # Most coins use 1-2 decimal places for price on Hyperliquid
        if price > Decimal("1000"):
            decimals = 1
        elif price > Decimal("10"):
            decimals = 2
        else:
            decimals = 4

        quantizer = Decimal("1") / (Decimal("10") ** decimals)
        return price.quantize(quantizer)

    def calculate_limit_price(
        self,
        coin: str,
        side: str,
        reference_price: Decimal,
        slippage_tolerance: Decimal,
    ) -> Decimal:
        """Calculate limit price with slippage tolerance.

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
            >>> slippage = Decimal("0.001")
            >>> limit = exchange.calculate_limit_price("BTC", "buy", ref_price, slippage)
            >>> print(limit)  # ~50050.0
        """
        # Normalize side to lowercase
        side_lower = side.lower()

        # Calculate limit price based on side
        if side_lower in ("buy", "long"):
            # For buy/long: add slippage (buy at higher price)
            limit_price = reference_price * (Decimal("1") + slippage_tolerance)
        else:
            # For sell/short: subtract slippage (sell at lower price)
            limit_price = reference_price * (Decimal("1") - slippage_tolerance)

        # Round to exchange precision
        return self.round_price(coin, limit_price)
