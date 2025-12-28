"""Trading orchestrator for coordinating portfolio rebalancing.

This module provides the TradingOrchestrator class, which is the core business
logic component that coordinates all trading operations.

The orchestrator follows this workflow:
    1. Get current portfolio state from exchange
    2. Load predictions from data source
    3. Filter to tradeable assets
    4. Calculate target positions
    5. Get current market prices
    6. Calculate required trades (in next task)
    7. Execute trades (in future task)

Classes:
    TradingOrchestrator: Main orchestrator class for trading operations

Design Principles:
    - Single Responsibility: Orchestrates trading, delegates specifics
    - Dependency Injection: All dependencies passed via constructor
    - Event-driven: Emits events for UI/monitoring integration
    - Type-safe: Full type hints throughout
    - Testable: Easy to mock all dependencies

Example:
    >>> from cc_flow.core.trader import TradingOrchestrator
    >>> orchestrator = TradingOrchestrator(
    ...     exchange=exchange,
    ...     data_source=data_source,
    ...     config=config
    ... )
    >>> plan = await orchestrator.plan_rebalance()
    >>> print(f"Target positions: {len(plan.target_positions)}")
"""

from __future__ import annotations

from decimal import Decimal

import polars as pl

from cc_flow.core.portfolio import PortfolioManager
from cc_flow.core.state import EventBus, StateManager
from cc_flow.data_sources.base import DataSource
from cc_flow.domain.account import PortfolioSnapshot, Position
from cc_flow.domain.config import TradingConfig
from cc_flow.domain.orders import OrderRequest, OrderSide, Trade
from cc_flow.domain.portfolio import ExecutionResult, RebalancePlan, TargetPosition
from cc_flow.exchanges.base import Exchange
from cc_flow.utils.logger_config import log


class TradingOrchestrator:
    """Orchestrates trading operations.

    The TradingOrchestrator is the main coordinator for all trading activities.
    It integrates the exchange, data source, portfolio manager, and state
    management to execute the complete trading workflow.

    Attributes:
        exchange: Exchange implementation for trading operations
        data_source: Data source for prediction data
        config: Trading configuration including portfolio settings
        state_manager: State manager for tracking portfolio snapshots
        event_bus: Event bus for emitting events to UI/monitoring
        portfolio_manager: Portfolio manager for calculating target positions

    Methods:
        plan_rebalance: Create a rebalancing plan with target positions
        _get_current_portfolio: Fetch current portfolio state from exchange

    Example:
        >>> orchestrator = TradingOrchestrator(
        ...     exchange=hyperliquid_exchange,
        ...     data_source=crowdcent_source,
        ...     config=trading_config
        ... )
        >>> plan = await orchestrator.plan_rebalance()
        >>> print(f"Created plan with {len(plan.target_positions)} positions")
    """

    def __init__(
        self,
        exchange: Exchange,
        data_source: DataSource,
        config: TradingConfig,
        state_manager: StateManager | None = None,
        event_bus: EventBus | None = None,
    ):
        """Initialize trading orchestrator.

        Args:
            exchange: Exchange implementation for trading operations
            data_source: Data source for loading predictions
            config: Trading configuration with portfolio settings
            state_manager: Optional state manager (creates default if None)
            event_bus: Optional event bus (creates default if None)

        Example:
            >>> from cc_flow.core.state import StateManager, EventBus
            >>> state = StateManager()
            >>> bus = EventBus()
            >>> orchestrator = TradingOrchestrator(
            ...     exchange=exchange,
            ...     data_source=data_source,
            ...     config=config,
            ...     state_manager=state,
            ...     event_bus=bus
            ... )
        """
        self.exchange = exchange
        self.data_source = data_source
        self.config = config
        self.state_manager = state_manager or StateManager()
        self.event_bus = event_bus or EventBus()

        # Initialize portfolio manager with portfolio config
        self.portfolio_manager = PortfolioManager(config.portfolio)

        log.info(f"TradingOrchestrator initialized for {config.current_profile.name}")

    async def plan_rebalance(self) -> RebalancePlan:
        """Create rebalancing plan.

        Executes steps 1-6 of the rebalancing workflow:
            1. Get current portfolio state from exchange
            2. Load predictions from data source
            3. Get tradeable symbols from exchange metadata
            4. Filter predictions to only tradeable assets
            5. Calculate target positions using portfolio manager
            6. Get current market prices for target positions

        Step 7 (trade calculation) will be implemented in the next task.

        Returns:
            RebalancePlan with target positions and portfolio state

        Raises:
            ValueError: If no tradeable assets are found in predictions

        Example:
            >>> plan = await orchestrator.plan_rebalance()
            >>> print(f"Account value: ${plan.account_value}")
            >>> print(f"Target positions: {len(plan.target_positions)}")
            >>> print(f"Current leverage: {plan.current_leverage}")
            >>> print(f"Target leverage: {plan.target_leverage}")
        """
        log.info("Planning rebalance...")

        # Step 1: Get current portfolio state
        current_state = await self._get_current_portfolio()
        self.state_manager.add_portfolio_snapshot(current_state)
        log.debug(f"Current account value: ${current_state.account.account_value}")

        # Step 2: Load predictions
        predictions = await self.data_source.load_predictions()
        log.info(f"Loaded {len(predictions)} predictions")

        # Step 3: Get tradeable symbols from exchange
        metadata = await self.exchange.info.get_exchange_metadata()
        tradeable_symbols = {m["name"] for m in metadata.get("universe", [])}
        log.debug(f"Found {len(tradeable_symbols)} tradeable symbols")

        # Step 4: Filter predictions to tradeable assets
        tradeable_preds = predictions.filter(
            pl.col("asset_id").is_in(list(tradeable_symbols))
        )

        if len(tradeable_preds) == 0:
            raise ValueError("No tradeable assets found in predictions")

        log.info(f"Filtered to {len(tradeable_preds)} tradeable predictions")

        # Step 5: Calculate target positions
        target_positions = self.portfolio_manager.calculate_target_positions(
            tradeable_preds, current_state.account.account_value
        )
        log.info(f"Calculated {len(target_positions)} target positions")

        # Step 6: Get current prices
        coins = [p.coin for p in target_positions]
        current_prices = await self.exchange.info.get_market_prices(coins)
        log.debug(f"Fetched prices for {len(current_prices)} coins")

        # Step 7: Calculate trades
        executable_trades, skipped_trades = await self._calculate_trades(
            target_positions, current_state.positions, current_prices
        )
        log.info(
            f"Calculated {len(executable_trades)} executable, "
            f"{len(skipped_trades)} skipped trades"
        )

        # Create plan
        plan = RebalancePlan(
            account_value=current_state.account.account_value,
            current_leverage=current_state.account.current_leverage,
            target_leverage=self.config.portfolio.target_leverage,
            target_positions=target_positions,
            executable_trades=executable_trades,
            skipped_trades=skipped_trades,
        )

        # Emit event
        self.event_bus.emit("plan_created", plan)

        log.info(f"Plan created: {len(target_positions)} target positions")

        return plan

    async def _get_current_portfolio(self) -> PortfolioSnapshot:
        """Get current portfolio state from exchange.

        Fetches the current account state from the exchange using the
        configured profile's owner and vault addresses, then parses it
        into a standardized PortfolioSnapshot domain model.

        Returns:
            PortfolioSnapshot with current account info and positions

        Raises:
            Any exceptions from exchange API calls

        Example:
            >>> portfolio = await orchestrator._get_current_portfolio()
            >>> print(f"Account value: ${portfolio.account.account_value}")
            >>> print(f"Positions: {len(portfolio.positions)}")
        """
        profile = self.config.current_profile
        owner = profile.owner_address
        vault = profile.vault_address

        # Get account state from exchange
        raw_state = await self.exchange.info.get_account_state(owner, vault)

        # Parse to domain model using exchange-specific parser
        portfolio = self.exchange.parse_account_state(raw_state)

        log.debug(
            f"Fetched portfolio for {owner[:8]}... "
            f"(value: ${portfolio.account.account_value})"
        )

        return portfolio

    async def _calculate_trades(
        self,
        target_positions: list[TargetPosition],
        current_positions: list[Position],
        current_prices: dict[str, Decimal],
    ) -> tuple[list[Trade], list[Trade]]:
        """Calculate required trades from current to target positions.

        Args:
            target_positions: List of target positions
            current_positions: List of current positions
            current_prices: Dictionary of current prices by coin

        Returns:
            Tuple of (executable_trades, skipped_trades)
        """
        # Build lookup for current positions
        current_pos_map: dict[str, Position] = {
            pos.coin: pos for pos in current_positions
        }

        # Get fee rates for estimating costs
        owner = self.config.current_profile.owner_address
        fee_rates = await self.exchange.info.get_fee_rates(owner)
        taker_fee = fee_rates.get("taker", Decimal("0.0005"))

        all_trades: list[Trade] = []

        # Calculate trades for each target position
        for target in target_positions:
            coin = target.coin
            current_pos = current_pos_map.get(coin)
            price = current_prices.get(coin, Decimal("0"))

            if price == Decimal("0"):
                log.warning(f"Missing price for {coin}, skipping")
                continue

            # Calculate current and target values
            if current_pos is not None:
                current_value = current_pos.value if current_pos.side == "LONG" else -current_pos.value
            else:
                current_value = Decimal("0")

            target_value = target.target_value
            delta_value = target_value - current_value

            # Skip if no change needed (within tolerance)
            if abs(delta_value) < Decimal("0.01"):
                continue

            # Calculate trade size
            size = abs(delta_value) / price

            # Round size to exchange precision
            size = self.exchange.round_size(coin, size)

            # Determine trade side and type
            side, trade_type = self._determine_trade_details(
                current_value, target_value, delta_value
            )

            # Calculate limit price with slippage
            limit_price = self.exchange.calculate_limit_price(
                coin, side.value, price, self.config.execution.slippage_tolerance
            )

            # Estimate fee
            notional = size * price
            estimated_fee = notional * taker_fee

            # Create trade
            trade = Trade(
                coin=coin,
                side=side,
                size=size,
                reference_price=price,
                limit_price=limit_price,
                current_value=current_value,
                target_value=target_value,
                delta_value=delta_value,
                trade_type=trade_type,
                estimated_fee=estimated_fee,
                estimated_slippage=None,
            )

            all_trades.append(trade)

        # Also handle positions to close (not in target)
        target_coins = {t.coin for t in target_positions}
        for current_pos in current_positions:
            if current_pos.coin not in target_coins:
                # Close this position
                price = current_prices.get(current_pos.coin)
                if price is None:
                    log.warning(f"Missing price for {current_pos.coin}, cannot close")
                    continue

                current_value = (
                    current_pos.value if current_pos.side == "LONG" else -current_pos.value
                )
                side = OrderSide.SELL if current_pos.side == "LONG" else OrderSide.BUY
                size = current_pos.size

                # Round size
                size = self.exchange.round_size(current_pos.coin, size)

                limit_price = self.exchange.calculate_limit_price(
                    current_pos.coin,
                    side.value,
                    price,
                    self.config.execution.slippage_tolerance,
                )

                notional = size * price
                estimated_fee = notional * taker_fee

                trade = Trade(
                    coin=current_pos.coin,
                    side=side,
                    size=size,
                    reference_price=price,
                    limit_price=limit_price,
                    current_value=current_value,
                    target_value=Decimal("0"),
                    delta_value=-current_value,
                    trade_type="close",
                    estimated_fee=estimated_fee,
                    estimated_slippage=None,
                )

                all_trades.append(trade)

        # Filter by minimum notional
        executable: list[Trade] = []
        skipped: list[Trade] = []

        min_value = self.config.execution.min_trade_value

        for trade in all_trades:
            notional = abs(trade.size * trade.reference_price)
            if notional >= min_value:
                executable.append(trade)
            else:
                skipped.append(trade)

        return executable, skipped

    def _determine_trade_details(
        self, current_value: Decimal, target_value: Decimal, delta_value: Decimal
    ) -> tuple[OrderSide, str]:
        """Determine trade side and type.

        Args:
            current_value: Current position value (signed)
            target_value: Target position value (signed)
            delta_value: Change in value

        Returns:
            Tuple of (OrderSide, trade_type)
        """
        # Determine trade type
        if current_value == Decimal("0") and target_value != Decimal("0"):
            trade_type = "open"
        elif target_value == Decimal("0") and current_value != Decimal("0"):
            trade_type = "close"
        elif current_value * target_value < Decimal("0"):
            # Different signs = flip
            trade_type = "flip"
        elif abs(target_value) > abs(current_value):
            trade_type = "increase"
        else:
            trade_type = "reduce"

        # Determine side (BUY for increase, SELL for decrease)
        side = OrderSide.BUY if delta_value > Decimal("0") else OrderSide.SELL

        return side, trade_type  # type: ignore

    async def execute_plan(
        self, plan: RebalancePlan, skip_confirm: bool = False  # noqa: ARG002
    ) -> ExecutionResult:
        """Execute rebalancing plan.

        Args:
            plan: Rebalance plan to execute
            skip_confirm: Skip confirmation (for automated execution)

        Returns:
            ExecutionResult with execution details

        Example:
            >>> result = await orchestrator.execute_plan(plan, skip_confirm=True)
            >>> print(f"Success rate: {result.success_rate:.1%}")
        """
        log.info("Starting execution...")
        self.event_bus.emit("execution_starting", plan)

        successful_trades: list[Trade] = []
        failed_trades: list[Trade] = []
        stop_losses_applied = 0
        stop_losses_failed = 0

        # Sort trades for safety (reduce/close first, then open/increase)
        sorted_trades = self._sort_trades_for_execution(plan.executable_trades)

        # Execute each trade
        for trade in sorted_trades:
            try:
                # Create order request
                order_request = OrderRequest(
                    coin=trade.coin,
                    side=trade.side,
                    size=trade.size,
                    order_type=self.config.execution.order_type,
                    limit_price=trade.limit_price,
                    time_in_force=self.config.execution.time_in_force,
                    reduce_only=trade.trade_type in ("close", "reduce"),
                )

                # Submit order
                order_result = await self.exchange.trading.submit_order(order_request)

                # Attach result to trade
                trade.order_result = order_result

                # Track success/failure
                if order_result.is_success:
                    successful_trades.append(trade)
                    log.info(f"✓ {trade.coin} {trade.side.value} {trade.size} @ {trade.reference_price}")

                    # Apply stop loss if configured
                    if self._should_apply_stop_loss(trade):
                        try:
                            await self._apply_stop_loss(trade, order_result)
                            stop_losses_applied += 1
                        except Exception as e:
                            log.error(f"Failed to apply stop loss: {e}")
                            stop_losses_failed += 1
                else:
                    failed_trades.append(trade)
                    log.warning(
                        f"✗ {trade.coin} {trade.side.value} failed: {order_result.error_message}"
                    )

                # Emit trade executed event
                self.event_bus.emit("trade_executed", {"trade": trade, "result": order_result})

            except Exception as e:
                log.error(f"Error executing {trade.coin} {trade.side.value}: {e}")
                failed_trades.append(trade)

        # Create execution result
        result = ExecutionResult(
            plan=plan,
            successful_trades=successful_trades,
            failed_trades=failed_trades,
            stop_losses_applied=stop_losses_applied,
            stop_losses_failed=stop_losses_failed,
        )

        # Save state
        self.state_manager.add_execution_result(result)

        # Emit completion event
        self.event_bus.emit("execution_completed", result)

        log.info(
            f"Execution complete: {len(successful_trades)} success, "
            f"{len(failed_trades)} failed, {result.success_rate:.1%} success rate"
        )

        return result

    def _sort_trades_for_execution(self, trades: list[Trade]) -> list[Trade]:
        """Sort trades for safe execution (reduce leverage first).

        Args:
            trades: List of trades to sort

        Returns:
            Sorted list with reduce/close first, then increase/open
        """
        priority_order = {"reduce": 0, "close": 1, "increase": 2, "open": 3, "flip": 4}

        return sorted(trades, key=lambda t: priority_order.get(t.trade_type, 5))

    def _should_apply_stop_loss(self, trade: Trade) -> bool:
        """Check if stop loss should be applied to this trade.

        Args:
            trade: Trade to check

        Returns:
            True if stop loss should be applied
        """
        stop_loss_config = self.config.portfolio.stop_loss

        if stop_loss_config.sides == "none":
            return False

        if trade.trade_type not in ("open", "increase"):
            return False

        return (
            stop_loss_config.sides == "both"
            or (stop_loss_config.sides == "long_only" and trade.side == OrderSide.BUY)
            or (stop_loss_config.sides == "short_only" and trade.side == OrderSide.SELL)
        )

    async def _apply_stop_loss(self, trade: Trade, order_result) -> None:
        """Apply stop loss order for a trade.

        Args:
            trade: Trade that was executed
            order_result: Result of the executed order
        """
        stop_loss_config = self.config.portfolio.stop_loss
        stop_loss_pct = stop_loss_config.pct

        # Calculate stop loss price
        entry_price = order_result.average_price or trade.reference_price

        if trade.side == OrderSide.BUY:
            # Long position: stop below entry
            stop_price = entry_price * (Decimal("1") - stop_loss_pct)
            stop_side = OrderSide.SELL
        else:
            # Short position: stop above entry
            stop_price = entry_price * (Decimal("1") + stop_loss_pct)
            stop_side = OrderSide.BUY

        # Apply slippage for stop order
        stop_limit_price = self.exchange.calculate_limit_price(
            trade.coin,
            stop_side.value,
            stop_price,
            stop_loss_config.slippage,
        )

        # Create stop loss order
        # Note: This is simplified - real implementation would use exchange-specific
        # stop loss order types. For now, we just log it.
        log.info(
            f"Stop loss: {trade.coin} {stop_side.value} @ {stop_price} "
            f"(limit: {stop_limit_price})"
        )
