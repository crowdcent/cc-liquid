"""Composed strategies built from reusable components.

This module demonstrates how to build complete trading strategies
by composing signal generators, entry managers, exit rules, position
sizers, and state managers.
"""

from typing import TYPE_CHECKING
import polars as pl

from .components import (
    SignalGenerator,
    EntryManager,
    ExitRule,
    PositionSizer,
    StateManager,
    # Implementations
    TopNSignals,
    ImmediateEntry,
    VintageEntry,
    FullRebalanceExit,
    TakeProfitExit,
    StopLossExit,
    RankPowerSizer,
    NoOpState,
    VintageState,
)

if TYPE_CHECKING:
    from ..trader import CCLiquid


class ComposedStrategy:
    """Base class for strategies built from components.

    This orchestrates the components to produce a rebalancing plan.
    Each component handles one concern:
    - Signals: WHAT to trade
    - Entry: WHEN and HOW MUCH to enter
    - Exits: WHEN to close
    - Sizing: HOW to weight positions
    - State: Persistence across rebalances
    """

    def __init__(
        self,
        signal_generator: SignalGenerator,
        entry_manager: EntryManager,
        exit_rules: list[ExitRule],
        position_sizer: PositionSizer,
        state_manager: StateManager,
    ):
        """
        Args:
            signal_generator: Generates long/short asset lists
            entry_manager: Manages position entry timing/scaling
            exit_rules: List of exit conditions (OR logic)
            position_sizer: Calculates position weights
            state_manager: Persists strategy state
        """
        self.signal_gen = signal_generator
        self.entry_mgr = entry_manager
        self.exit_rules = exit_rules
        self.sizer = position_sizer
        self.state = state_manager

    def plan(
        self,
        trader: "CCLiquid",
        predictions: pl.DataFrame | None,
        target_leverage: float,
        rank_power: float,
    ) -> dict:
        """Compute rebalancing plan.

        Args:
            trader: CCLiquid instance
            predictions: Prediction DataFrame
            target_leverage: Total gross leverage
            rank_power: Position weighting concentration

        Returns:
            Plan dict with target_positions, trades, etc.
        """
        # Load predictions if not provided
        if predictions is None:
            trader.callbacks.info("Loading predictions...")
            predictions = trader._load_predictions()

            if predictions is None or predictions.is_empty():
                trader.callbacks.error("No predictions available")
                return self._empty_plan(trader)

        # Check for open orders
        open_orders = trader.get_open_orders()
        if open_orders:
            trader.callbacks.warn(
                f"Found {len(open_orders)} open order(s). May conflict with rebalancing."
            )

        # Step 1: Check exit rules
        positions_to_close = self._evaluate_exits(trader)

        # Step 2: Generate signals (what to trade)
        date_col = trader.config.data.date_column
        asset_col = trader.config.data.asset_id_column
        pred_col = trader.config.data.prediction_column

        long_assets, short_assets = self.signal_gen.generate_signals(
            predictions, date_col, asset_col, pred_col
        )

        # Step 3: Calculate target positions using entry manager
        target_positions = self.entry_mgr.calculate_target_positions(
            trader=trader,
            long_assets=long_assets,
            short_assets=short_assets,
            target_leverage=target_leverage,
            rank_power=rank_power,
            state_manager=self.state,
        )

        # Step 4: Override targets for positions that should exit
        for coin in positions_to_close:
            target_positions[coin] = 0

        # Step 5: Calculate trades
        current_positions = trader.get_positions()
        trades, skipped_trades = trader._calculate_trades(
            target_positions, current_positions
        )

        account_value = trader.get_account_value()

        return {
            "target_positions": target_positions,
            "trades": trades,
            "skipped_trades": skipped_trades,
            "account_value": account_value,
            "leverage": target_leverage,
            "open_orders": open_orders,
            "positions_closed_by_exit_rules": list(positions_to_close),
        }

    def _evaluate_exits(self, trader: "CCLiquid") -> set[str]:
        """Evaluate all exit rules and return positions to close.

        Uses OR logic: close if ANY exit rule triggers.
        """
        positions_to_close = set()

        for exit_rule in self.exit_rules:
            should_exit = exit_rule.should_exit_positions(trader)
            for coin, exit_flag in should_exit.items():
                if exit_flag:
                    positions_to_close.add(coin)

        return positions_to_close

    def _empty_plan(self, trader: "CCLiquid") -> dict:
        """Return empty plan when predictions unavailable."""
        return {
            "target_positions": {},
            "trades": [],
            "skipped_trades": [],
            "account_value": trader.get_account_value(),
            "leverage": 0,
            "open_orders": [],
        }


# ============================================================================
# PRE-COMPOSED STRATEGIES (the current "modes")
# ============================================================================


def create_full_mode_strategy(
    num_long: int,
    num_short: int,
    rank_power: float = 0.0,
) -> ComposedStrategy:
    """Create FULL MODE strategy using components.

    Full mode characteristics:
    - Signals: Top N predictions
    - Entry: Immediate (all at once)
    - Exit: Full rebalance (replace everything)
    - Sizing: Rank power weighting
    - State: None needed

    Args:
        num_long: Number of long positions
        num_short: Number of short positions
        rank_power: Weighting concentration (0.0 = equal)

    Returns:
        Composed strategy for full mode
    """
    return ComposedStrategy(
        signal_generator=TopNSignals(num_long, num_short),
        entry_manager=ImmediateEntry(),
        exit_rules=[FullRebalanceExit()],
        position_sizer=RankPowerSizer(rank_power),
        state_manager=NoOpState(),
    )


def create_rolling_mode_strategy(
    num_long: int,
    num_short: int,
    rolling_days: int,
    seed_full: bool = False,
    rank_power: float = 0.0,
) -> ComposedStrategy:
    """Create ROLLING MODE strategy using components.

    Rolling mode characteristics:
    - Signals: Top N predictions
    - Entry: Vintage-based (staggered over rolling_days)
    - Exit: Time-based (handled by vintage expiry)
    - Sizing: Rank power weighting
    - State: Vintage tracking

    Args:
        num_long: Number of long positions
        num_short: Number of short positions
        rolling_days: Vintage lifespan in days
        seed_full: Seed all vintages on first run
        rank_power: Weighting concentration (0.0 = equal)

    Returns:
        Composed strategy for rolling mode
    """
    return ComposedStrategy(
        signal_generator=TopNSignals(num_long, num_short),
        entry_manager=VintageEntry(rolling_days, seed_full),
        exit_rules=[],  # Exits handled by vintage expiry in entry manager
        position_sizer=RankPowerSizer(rank_power),
        state_manager=VintageState(),
    )


def create_take_profit_auto_strategy(
    num_long: int,
    num_short: int,
    pnl_threshold_pct: float = 0.15,
    rank_power: float = 0.0,
) -> ComposedStrategy:
    """Create TAKE PROFIT AUTO strategy using components.

    Take profit characteristics:
    - Signals: Top N predictions
    - Entry: Immediate (when positions closed)
    - Exit: Take profit when above threshold
    - Sizing: Rank power weighting
    - State: None needed (uses live PnL)

    Args:
        num_long: Number of long positions
        num_short: Number of short positions
        pnl_threshold_pct: Profit threshold (0.15 = 15%)
        rank_power: Weighting concentration (0.0 = equal)

    Returns:
        Composed strategy for take profit mode
    """
    return ComposedStrategy(
        signal_generator=TopNSignals(num_long, num_short),
        entry_manager=ImmediateEntry(),
        exit_rules=[TakeProfitExit(pnl_threshold_pct)],
        position_sizer=RankPowerSizer(rank_power),
        state_manager=NoOpState(),
    )


def create_take_profit_with_stop_loss_strategy(
    num_long: int,
    num_short: int,
    take_profit_pct: float = 0.15,
    stop_loss_pct: float = 0.10,
    rank_power: float = 0.0,
) -> ComposedStrategy:
    """Create strategy with BOTH take profit AND stop loss.

    Demonstrates combining multiple exit rules.

    Args:
        num_long: Number of long positions
        num_short: Number of short positions
        take_profit_pct: Profit threshold (0.15 = 15%)
        stop_loss_pct: Loss threshold (0.10 = 10% loss)
        rank_power: Weighting concentration

    Returns:
        Composed strategy with dual exits
    """
    return ComposedStrategy(
        signal_generator=TopNSignals(num_long, num_short),
        entry_manager=ImmediateEntry(),
        exit_rules=[
            TakeProfitExit(take_profit_pct),
            StopLossExit(stop_loss_pct),
        ],
        position_sizer=RankPowerSizer(rank_power),
        state_manager=NoOpState(),
    )


def create_rolling_with_take_profit_strategy(
    num_long: int,
    num_short: int,
    rolling_days: int,
    pnl_threshold_pct: float = 0.15,
    seed_full: bool = False,
    rank_power: float = 0.0,
) -> ComposedStrategy:
    """Create ROLLING MODE with TAKE PROFIT exits.

    Demonstrates combining vintage entry with take profit exit.
    Positions either:
    - Close after rolling_days (vintage expiry)
    - OR close early if profit threshold hit

    Args:
        num_long: Number of long positions
        num_short: Number of short positions
        rolling_days: Vintage lifespan
        pnl_threshold_pct: Profit threshold
        seed_full: Seed vintages on first run
        rank_power: Weighting concentration

    Returns:
        Composed strategy combining rolling + take profit
    """
    return ComposedStrategy(
        signal_generator=TopNSignals(num_long, num_short),
        entry_manager=VintageEntry(rolling_days, seed_full),
        exit_rules=[TakeProfitExit(pnl_threshold_pct)],
        position_sizer=RankPowerSizer(rank_power),
        state_manager=VintageState(),
    )
