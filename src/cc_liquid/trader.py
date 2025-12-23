"""Core trading logic for cc-liquid.

This module contains the core trading logic. Using this software may result in
COMPLETE LOSS of funds. CrowdCent makes NO WARRANTIES and assumes NO LIABILITY.
Users must comply with all Hyperliquid terms of service.
"""

import logging
from dataclasses import dataclass
import math
from datetime import timezone, datetime, timedelta, time
from typing import Any

import polars as pl
from eth_account.signers.local import LocalAccount
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info

from .callbacks import CCLiquidCallbacks, NoOpCallbacks
from .config import Config
from .data_loader import DataLoader
from .portfolio import weights_from_ranks

logging.basicConfig(level=logging.INFO)


@dataclass
class AccountInfo:
    """Structured account information."""

    # Account metrics
    account_value: float
    total_position_value: float
    margin_used: float
    free_collateral: float
    cash_balance: float
    withdrawable: float
    current_leverage: float

    # Cross margin info (optional)
    cross_leverage: float | None = None
    cross_margin_used: float | None = None
    cross_maintenance_margin: float | None = None

    # Raw data for advanced users
    raw_margin_summary: dict[str, Any] | None = None
    raw_cross_margin_summary: dict[str, Any] | None = None


@dataclass
class Position:
    """Structured position information."""

    coin: str
    side: str  # "LONG" or "SHORT"
    size: float
    entry_price: float
    mark_price: float
    value: float
    unrealized_pnl: float
    return_pct: float
    liquidation_price: float | None = None
    margin_used: float | None = None


@dataclass
class PortfolioInfo:
    """Complete portfolio information."""

    account: AccountInfo
    positions: list[Position]

    @property
    def total_long_value(self) -> float:
        """Calculate total long position value."""
        return sum(p.value for p in self.positions if p.side == "LONG")

    @property
    def total_short_value(self) -> float:
        """Calculate total short position value."""
        return sum(p.value for p in self.positions if p.side == "SHORT")

    @property
    def net_exposure(self) -> float:
        """Calculate net exposure (long - short)."""
        return self.total_long_value - self.total_short_value

    @property
    def total_exposure(self) -> float:
        """Calculate total exposure (long + short)."""
        return self.total_long_value + self.total_short_value

    @property
    def total_unrealized_pnl(self) -> float:
        """Calculate total unrealized PnL."""
        return sum(p.unrealized_pnl for p in self.positions)


def aggregate_pnl_by_currency(
    fills: list[dict[str, Any]], positions: list[Position]
) -> dict[str, dict[str, float]]:
    """Aggregate realized and unrealized PNL, fees, and volume by currency.

    Args:
        fills: List of fill history dictionaries from Hyperliquid API
        positions: List of current Position objects with unrealized PNL

    Returns:
        Dictionary mapping currency to {
            "realized_pnl": float,
            "unrealized_pnl": float,
            "fees": float,
            "volume": float
        }
        sorted alphabetically by currency name
    """
    # Aggregate realized PNL, fees, and volume from fills
    realized_pnl_by_coin: dict[str, float] = {}
    fees_by_coin: dict[str, float] = {}
    volume_by_coin: dict[str, float] = {}

    for fill in fills:
        coin = fill["coin"]
        closed_pnl = float(fill.get("closedPnl", 0))
        fee = float(fill.get("fee", 0))
        size = float(fill["sz"])
        price = float(fill["px"])
        value = size * price

        if coin not in realized_pnl_by_coin:
            realized_pnl_by_coin[coin] = 0.0
            fees_by_coin[coin] = 0.0
            volume_by_coin[coin] = 0.0

        realized_pnl_by_coin[coin] += closed_pnl
        fees_by_coin[coin] += fee
        volume_by_coin[coin] += value

    # Aggregate unrealized PNL from positions
    unrealized_pnl_by_coin: dict[str, float] = {}
    for position in positions:
        coin = position.coin
        unrealized_pnl_by_coin[coin] = position.unrealized_pnl

    # Combine all currencies (both from fills and positions)
    all_coins = set(realized_pnl_by_coin.keys()) | set(unrealized_pnl_by_coin.keys())

    # Build summary dict
    pnl_summary = {}
    for coin in sorted(all_coins):  # Sort alphabetically
        pnl_summary[coin] = {
            "realized_pnl": realized_pnl_by_coin.get(coin, 0.0),
            "unrealized_pnl": unrealized_pnl_by_coin.get(coin, 0.0),
            "fees": fees_by_coin.get(coin, 0.0),
            "volume": volume_by_coin.get(coin, 0.0),
        }

    return pnl_summary


class CCLiquid:
    """
    Handles all interactions with the Hyperliquid exchange.
    """

    def __init__(
        self,
        config: Config,
        callbacks: CCLiquidCallbacks | None = None,
        skip_ws: bool = True,
    ):
        self.config = config
        self.callbacks = callbacks or NoOpCallbacks()

        # Validate config for trading operations
        self.config.validate_for_trading()

        self.account: LocalAccount = self._get_account()
        self.exchange = Exchange(
            self.account,
            self.config.base_url,
            vault_address=(self.config.HYPERLIQUID_VAULT_ADDRESS or None),
            account_address=self.config.HYPERLIQUID_ADDRESS,
        )
        self.info = Info(self.config.base_url, skip_ws=skip_ws)
        self.logger = logging.getLogger(__name__)
        # Lazy-loaded map of coin -> szDecimals from Info.meta()["universe"].
        # Perps only: Hyperliquid perps use max 6 decimals for price rules.
        self._coin_to_sz_decimals: dict[str, int] | None = None

    def _get_account(self) -> LocalAccount:
        """Creates an eth_account LocalAccount object from the private key."""
        from eth_account import Account

        return Account.from_key(self.config.HYPERLIQUID_PRIVATE_KEY)

    def get_user_state(self) -> dict[str, Any]:
        """Retrieves the current state of the user's account."""
        # Always query Info using the portfolio owner: vault (if set) or master address.
        # Never use the agent/signer address for Info, as it has no balances.
        owner = self.config.HYPERLIQUID_VAULT_ADDRESS or self.config.HYPERLIQUID_ADDRESS
        if not owner:
            raise ValueError(
                "Missing portfolio owner. Set HYPERLIQUID_VAULT_ADDRESS or HYPERLIQUID_ADDRESS."
            )
        return self.info.user_state(owner)

    def get_positions(self) -> dict[str, Any]:
        """Retrieves the user's open positions as a dict."""
        user_state = self.get_user_state()
        positions = {}
        for position_data in user_state.get("assetPositions", []):
            position = position_data.get("position", {})
            if float(position.get("szi", 0)) != 0:
                positions[position["coin"]] = position
        return positions

    def get_account_value(self) -> float:
        """Retrieves the total account value in USD."""
        user_state = self.get_user_state()
        return float(user_state["marginSummary"]["accountValue"])

    def get_portfolio_info(self) -> PortfolioInfo:
        """Get complete portfolio information as structured data."""
        try:
            user_state = self.get_user_state()
        except Exception as e:
            self.logger.warning(f"Could not get user state: {e}")
            # Return empty portfolio if we can't connect
            return PortfolioInfo(
                account=AccountInfo(
                    account_value=0,
                    total_position_value=0,
                    margin_used=0,
                    free_collateral=0,
                    cash_balance=0,
                    withdrawable=0,
                    current_leverage=0,
                ),
                positions=[],
            )

        margin_summary = user_state.get("marginSummary", {}) if user_state else {}
        all_mids = self.info.all_mids() if user_state else {}

        # Build account info
        account_info = AccountInfo(
            account_value=float(margin_summary.get("accountValue", 0)),
            total_position_value=float(margin_summary.get("totalNtlPos", 0)),
            margin_used=float(margin_summary.get("totalMarginUsed", 0)),
            free_collateral=float(margin_summary.get("accountValue", 0))
            - float(margin_summary.get("totalMarginUsed", 0)),
            cash_balance=float(margin_summary.get("totalRawUsd", 0)),
            withdrawable=float(user_state.get("withdrawable", 0)),
            current_leverage=float(margin_summary.get("totalNtlPos", 0))
            / float(margin_summary.get("accountValue", 1))
            if float(margin_summary.get("accountValue", 0)) > 0
            else 0,
            raw_margin_summary=margin_summary,
        )

        # Add cross margin info if available
        cross_margin = user_state.get("crossMarginSummary")
        if cross_margin:
            account_info.cross_leverage = (
                float(cross_margin.get("accountValue", 0))
                / float(margin_summary.get("accountValue", 1))
                if float(margin_summary.get("accountValue", 0)) > 0
                else 0
            )
            account_info.cross_margin_used = float(
                cross_margin.get("totalMarginUsed", 0)
            )
            account_info.cross_maintenance_margin = float(
                cross_margin.get("totalMaintenanceMargin", 0)
            )
            account_info.raw_cross_margin_summary = cross_margin

        # Build positions list
        positions = []
        for position_data in user_state.get("assetPositions", []):
            pos = position_data.get("position", {})
            size = float(pos.get("szi", 0))

            if size == 0:
                continue

            coin = pos["coin"]
            entry_px = float(pos.get("entryPx", 0))
            mark_px = float(all_mids.get(coin, entry_px))
            position_value = abs(size * mark_px)

            # Calculate unrealized PnL
            if size > 0:
                unrealized_pnl = (mark_px - entry_px) * size
                side = "LONG"
            else:
                unrealized_pnl = (entry_px - mark_px) * abs(size)
                side = "SHORT"

            return_pct = (
                (unrealized_pnl / (abs(size) * entry_px) * 100) if entry_px > 0 else 0
            )

            positions.append(
                Position(
                    coin=coin,
                    side=side,
                    size=abs(size),
                    entry_price=entry_px,
                    mark_price=mark_px,
                    value=position_value,
                    unrealized_pnl=unrealized_pnl,
                    return_pct=return_pct,
                    liquidation_price=float(pos["liquidationPx"])
                    if "liquidationPx" in pos and pos["liquidationPx"] is not None
                    else None,
                    margin_used=float(pos["marginUsed"])
                    if "marginUsed" in pos and pos["marginUsed"] is not None
                    else None,
                )
            )

        return PortfolioInfo(account=account_info, positions=positions)

    # --- Rounding helpers (Perps only) ---
    def _load_sz_decimals_map(self, force_refresh: bool = False) -> dict[str, int]:
        """Load and cache coin -> szDecimals from exchange meta.

        Per Hyperliquid rounding guidance for orders, sizes must be rounded to a
        coin-specific number of decimals (szDecimals). We cache from `info.meta()`
        and refresh on demand.
        """
        if self._coin_to_sz_decimals is None or force_refresh:
            try:
                universe = self.info.meta().get("universe", [])
                self._coin_to_sz_decimals = {
                    asset.get("name"): int(asset.get("szDecimals", 2))
                    for asset in universe
                    if asset.get("name") and not asset.get("isDelisted", False)
                }
            except Exception as e:
                self.logger.warning(f"Failed to load szDecimals map: {e}")
                self._coin_to_sz_decimals = {}
        return self._coin_to_sz_decimals

    def _get_sz_decimals(self, coin: str) -> int | None:
        """Return szDecimals for the given coin, refreshing meta once if needed."""
        sz_map = self._load_sz_decimals_map()
        if coin not in sz_map:
            sz_map = self._load_sz_decimals_map(force_refresh=True)
        return sz_map.get(coin)

    def _round_size(self, coin: str, size: float) -> tuple[float, int] | None:
        """Round size per coin's szDecimals.

        Returns (rounded_size, sz_decimals) or None if szDecimals are unknown.
        """
        sz_decimals = self._get_sz_decimals(coin)
        if sz_decimals is None:
            return None
        return round(size, sz_decimals), sz_decimals

    def _round_price_perp(self, coin: str, px: float) -> float:
        """Round price according to Hyperliquid perp rules (used for limit orders).

        Rules (per Hyperliquid):
        - If px > 100_000: round to integer.
        - Else: round to 5 significant figures and at most (6 - szDecimals) decimals.
        Reference: Hyperliquid SDK example rounding: see rounding.py
        """
        if px > 100_000:
            return round(px)
        sz_decimals = self._get_sz_decimals(coin)
        # If unknown, still limit to 5 significant figures as a safe default.
        if sz_decimals is None:
            return float(f"{px:.5g}")
        max_decimals = 6  # perps
        return round(float(f"{px:.5g}"), max_decimals - sz_decimals)

    def plan_rebalance(self, predictions: pl.DataFrame | None = None) -> dict:
        """Compute a rebalancing plan without executing orders."""
        # Check for open orders (warning if present)
        open_orders = self.get_open_orders()
        if open_orders:
            self.callbacks.warn(
                f"Found {len(open_orders)} open order(s). These may conflict with rebalancing."
            )
        # Load predictions if not provided
        if predictions is None:
            self.callbacks.info("Loading predictions...")
            predictions = self._load_predictions()

            if predictions is None or predictions.is_empty():
                self.callbacks.error("No predictions available, cannot rebalance")
                return {
                    "target_positions": {},
                    "trades": [],
                    "skipped_trades": [],
                    "account_value": 0.0,
                    "leverage": self.config.portfolio.target_leverage,
                    "open_orders": open_orders,
                }

            # Display prediction info
            unique_assets = predictions[self.config.data.asset_id_column].n_unique()
            latest_data = predictions[self.config.data.date_column].max()
            self.callbacks.info(
                f"Loaded predictions for {unique_assets} assets (latest: {latest_data})"
            )

        # Asset Selection, Position Calculation, and Trade Generation
        target_positions = self._get_target_positions(predictions)
        current_positions = self.get_positions()
        trades, skipped_trades = self._calculate_trades(
            target_positions, current_positions
        )

        # Build plan (including skipped trades)
        account_value = self.get_account_value()
        leverage = self.config.portfolio.target_leverage
        return {
            "target_positions": target_positions,
            "trades": trades,
            "skipped_trades": skipped_trades,
            "account_value": account_value,
            "leverage": leverage,
            "open_orders": open_orders,
        }

    def plan_rebalance_auto(self, predictions: pl.DataFrame | None = None) -> dict:
        """Plan rebalance using configured mode (full or rolling)."""
        if self.config.portfolio.rebalancing.mode == "rolling":
            return self.plan_rolling_rebalance(predictions)
        return self.plan_rebalance(predictions)

    def execute_plan(self, plan: dict) -> dict:
        """Execute a precomputed plan, returning structured results."""
        trades: list[dict] = plan.get("trades", [])
        if not trades:
            # Nothing to do
            return {"successful_trades": [], "all_trades": trades}

        # Prioritize leverage reduction: execute closes/reductions (and flips) before opens
        trades = self._sort_trades_for_leverage_reduction(trades)

        self.callbacks.info(f"Starting execution of {len(trades)} trades...")
        successful_trades = self._execute_trades(trades)
        
        # Apply stop losses after execution
        sl_result = None
        if self.config.portfolio.stop_loss.sides != "none":
            self.callbacks.info("Applying stop losses to positions...")
            sl_result = self.apply_stop_losses()
            
            # Report SL results
            if sl_result.get("status") == "ok":
                applied_count = sl_result.get("total_applied", 0)
                if applied_count > 0:
                    self.callbacks.info(f"✓ Placed {applied_count} stop loss order(s)")
                
                # Warn about resting orders
                resting = [t for t in successful_trades if t.get("resting")]
                if resting:
                    self.callbacks.warn(
                        f"{len(resting)} order(s) resting on book. "
                        "Run 'cc-liquid apply-stops' after they fill to add protection."
                    )
        
        return {
            "successful_trades": successful_trades,
            "all_trades": trades,
            "stop_loss_result": sl_result
        }

    def plan_close_all_positions(self, *, force: bool = False) -> dict:
        """Plan to close all open positions (return to cash) without executing orders."""
        current_positions = self.get_positions()

        if not current_positions:
            self.callbacks.info("No open positions to close.")
            return {
                "target_positions": {},
                "trades": [],
                "skipped_trades": [],
                "account_value": self.get_account_value(),
                "leverage": self.config.portfolio.target_leverage,
            }

        self.callbacks.info("Closing all positions to return to cash...")

        # Create target positions of 0 for all current positions
        target_positions = {coin: 0 for coin in current_positions.keys()}
        trades, skipped_trades = self._calculate_trades(
            target_positions, current_positions, force=force
        )

        account_value = self.get_account_value()
        leverage = self.config.portfolio.target_leverage
        return {
            "target_positions": target_positions,
            "trades": trades,
            "skipped_trades": skipped_trades,
            "account_value": account_value,
            "leverage": leverage,
        }

    def _get_target_positions(
        self,
        predictions: pl.DataFrame,
        *,
        override_num_long: int | None = None,
        override_num_short: int | None = None,
        override_leverage: float | None = None,
        quiet: bool = False,
    ) -> dict[str, float]:
        """Calculate target notionals using configurable weighting scheme.

        Args:
            predictions: DataFrame with predictions
            override_num_long: Override config num_long (for rolling mode)
            override_num_short: Override config num_short (for rolling mode)
            override_leverage: Override config target_leverage (for rolling mode)
            quiet: If True, suppress info callbacks (for rolling mode)

        Returns:
            Dict mapping asset to target USD notional (signed: positive=long, negative=short)
        """
        latest_predictions = self._get_latest_predictions(predictions)
        tradeable_predictions = self._filter_tradeable_predictions(latest_predictions)

        if tradeable_predictions.height == 0:
            return {}

        id_col = self.config.data.asset_id_column
        pred_col = self.config.data.prediction_column

        sorted_preds = tradeable_predictions.sort(pred_col, descending=True)

        num_long = override_num_long if override_num_long is not None else self.config.portfolio.num_long
        num_short = override_num_short if override_num_short is not None else self.config.portfolio.num_short

        if sorted_preds.height < num_long + num_short and not quiet:
            self.callbacks.warn(
                f"Limited tradeable assets: {sorted_preds.height} available; "
                f"requested {num_long} longs and {num_short} shorts"
            )

        long_assets = sorted_preds.head(num_long)[id_col].to_list()
        short_assets = (
            sorted_preds.sort(pred_col, descending=False)
            .head(num_short)[id_col]
            .to_list()
            if num_short > 0
            else []
        )

        account_value = self.get_account_value()
        target_leverage = override_leverage if override_leverage is not None else self.config.portfolio.target_leverage
        total_positions = len(long_assets) + len(short_assets)

        if total_positions == 0 or account_value <= 0 or target_leverage <= 0:
            return {}

        if not quiet:
            self.callbacks.info(
                f"Target gross leverage: {target_leverage:.2f}x across {total_positions} positions"
            )

        weights = weights_from_ranks(
            latest_preds=tradeable_predictions.select([id_col, pred_col]),
            id_col=id_col,
            pred_col=pred_col,
            long_assets=long_assets,
            short_assets=short_assets,
            target_gross=target_leverage,
            power=self.config.portfolio.rank_power,
        )

        target_positions = {
            asset: weight * account_value for asset, weight in weights.items()
        }

        # Warn if resulting notionals fall below exchange minimums
        min_notional = self.config.execution.min_trade_value
        undersized = [
            asset
            for asset, weight in target_positions.items()
            if abs(weight) < min_notional
        ]
        if undersized and not quiet:
            self.callbacks.warn(
                "Some target positions fall below minimum notional: "
                + ", ".join(sorted(undersized))
            )

        return target_positions

    def _get_latest_predictions(self, predictions: pl.DataFrame) -> pl.DataFrame:
        """Filters for the latest predictions for each asset by date."""
        return (
            predictions.sort(self.config.data.date_column, descending=True)
            .group_by(self.config.data.asset_id_column)
            .first()
        )

    def _filter_tradeable_predictions(self, predictions: pl.DataFrame) -> pl.DataFrame:
        """Filter predictions to Hyperliquid-listed assets."""

        universe = self.info.meta()["universe"]
        available_assets = {
            p["name"] for p in universe if not p.get("isDelisted", False)
        }

        tradeable = predictions.filter(
            pl.col(self.config.data.asset_id_column).is_in(available_assets)
        )

        if tradeable.height == 0:
            self.logger.warning("No predictions match Hyperliquid tradeable assets!")
            self.callbacks.error(
                "Error: No predictions match Hyperliquid tradeable assets!"
            )
            self.callbacks.info(
                f"Available on Hyperliquid: {sorted(list(available_assets)[:10])}{'...' if len(available_assets) > 10 else ''}"
            )
            prediction_assets = (
                predictions[self.config.data.asset_id_column].unique().to_list()
            )
            self.callbacks.info(
                f"In predictions: {sorted(prediction_assets[:10])}{'...' if len(prediction_assets) > 10 else ''}"
            )

        return tradeable

    def _calculate_trades(
        self,
        target_positions: dict[str, float],
        current_positions: dict[str, Any],
        *,
        force: bool = False,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Calculates the trades required to reach the target portfolio using market orders.

        Returns:
            (executable_trades, skipped_trades) - trades that can be executed and those below minimum
        """
        trades = []
        skipped_trades = []  # Track trades we can't execute
        all_mids = self.info.all_mids()
        

        fee_info = self.get_fee_summary()
        taker_rate = float(fee_info.get("userCrossRate", 0.00035))

        all_assets = set(target_positions.keys()) | set(current_positions.keys())

        for asset in all_assets:
            target_value = target_positions.get(asset, 0)

            # Get current position details
            current_position = current_positions.get(asset, {})
            current_size = float(current_position.get("szi", 0))

            # Ensure we have a mid price; otherwise skip
            if asset not in all_mids:
                skipped_trades.append(
                    {
                        "coin": asset,
                        "target_value": target_value,
                        "skipped": True,
                        "skip_reason": "No mid price available",
                    }
                )
                continue

            price = float(all_mids[asset])

            # Calculate current value with proper sign
            # szi is positive for long, negative for short
            current_value = current_size * price

            # Calculate the value delta we need to achieve
            delta_value = target_value - current_value

            # Determine trade direction
            # If delta_value > 0, we need to buy (increase position or reduce short)
            # If delta_value < 0, we need to sell (decrease position or increase short)
            is_buy = delta_value > 0
            size = abs(delta_value) / price

            # Round the size using szDecimals from meta (perps only)
            coin = asset
            rounded = self._round_size(coin, size)
            if rounded is None:
                skipped_trades.append(
                    {
                        "coin": asset,
                        "target_value": target_value,
                        "skipped": True,
                        "skip_reason": "Unknown szDecimals (meta)",
                    }
                )
                continue
            size, sz_decimals = rounded

            # If rounding collapses to zero, skip
            if size == 0:
                skipped_trades.append(
                    {
                        "coin": asset,
                        "target_value": target_value,
                        "skipped": True,
                        "skip_reason": f"Rounded size is 0 at {sz_decimals} dp",
                    }
                )
                continue

            # Check if trade is below minimum value threshold
            min_trade_value = self.config.execution.min_trade_value
            # Classify the trade type for clearer downstream handling
            # Types: open, close, reduce, increase, flip
            trade_type: str
            if current_value == 0:
                trade_type = "open" if target_value != 0 else "increase"
            elif target_value == 0:
                trade_type = "close"
            else:
                same_sign = (current_value > 0 and target_value > 0) or (
                    current_value < 0 and target_value < 0
                )
                if same_sign:
                    trade_type = (
                        "reduce"
                        if abs(target_value) < abs(current_value)
                        else "increase"
                    )
                else:
                    trade_type = "flip"

            trade_data = {
                "coin": asset,
                "is_buy": is_buy,
                "sz": size,
                "price": price,
                "current_value": current_value,
                "target_value": target_value,
                "delta_value": delta_value,
                "type": trade_type,
                "estimated_fee": abs(delta_value) * taker_rate,
            }

            # Re-evaluate min notional AFTER rounding size
            if abs(size * price) < min_trade_value:
                # Below minimum. If not forcing or not a pure close-to-zero scenario, skip.
                if not force or target_value != 0:
                    trade_data["skipped"] = True
                    trade_data["skip_reason"] = f"Below minimum ${min_trade_value}"
                    skipped_trades.append(trade_data)
                else:
                    forced, reason = self._compose_force_close_trades(
                        asset, price, current_value, min_trade_value, taker_rate
                    )
                    if forced is None:
                        skipped_trades.append(
                            {
                                "coin": asset,
                                "target_value": target_value,
                                "skipped": True,
                                "skip_reason": reason
                                or "Force close composition failed",
                            }
                        )
                    else:
                        trades.extend(forced)
            else:
                # Add to executable trades
                trades.append(trade_data)

        return trades, skipped_trades

    def _sort_trades_for_leverage_reduction(
        self, trades: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Return trades ordered to reduce leverage first using explicit trade types.

        Priority: close (0), reduce/flip (1), increase (2), open (3). Stable ordering within groups.
        """
        priority = {"close": 0, "reduce": 1, "flip": 1, "increase": 2, "open": 3}

        def sort_key(t: dict[str, Any]):
            # Forced close chains must execute in sequence: increase (0) then close (1)
            if t.get("force"):
                return (0, t.get("force_id", ""), t.get("force_seq", 0))
            return (1, priority.get(t.get("type", "increase"), 2), 0)

        return sorted(trades, key=sort_key)

    def _compose_force_close_trades(
        self, coin: str, price: float, current_value: float, min_trade_value: float, taker_rate: float
    ) -> tuple[list[dict[str, Any]] | None, str | None]:
        """Compose the two-step forced close for sub-minimum closes.
        i.e. if we have a position of less than $10, we want to close it to $0, we need to increase the position
        to at least $10, then close it to $0.

        Returns (trades, None) on success or (None, reason) on failure.
        """
        rounded_up = self._round_size_up_to_min_notional(coin, min_trade_value, price)
        if rounded_up is None:
            return None, "Unknown szDecimals (meta)"
        min_increase_sz, _ = rounded_up

        increase_is_buy = current_value > 0
        force_id = f"force_close:{coin}"
        
        step1_delta = min_increase_sz * price if increase_is_buy else -(min_increase_sz * price)

        step1 = {
            "coin": coin,
            "is_buy": increase_is_buy,
            "sz": min_increase_sz,
            "price": price,
            "current_value": current_value,
            "target_value": current_value
            + (
                min_increase_sz * price
                if current_value >= 0
                else -min_increase_sz * price
            ),
            "delta_value": step1_delta,
            "type": "increase",
            "force": True,
            "force_id": force_id,
            "force_seq": 0,
            "estimated_fee": abs(step1_delta) * taker_rate,
        }

        total_notional_to_close = abs(current_value) + (min_increase_sz * price)
        close_is_buy = not increase_is_buy
        close_sz_rounded = self._round_size(coin, total_notional_to_close / price)
        if close_sz_rounded is None:
            return None, "Unknown szDecimals (meta)"
        close_sz, _ = close_sz_rounded
        
        step2_delta = total_notional_to_close if close_is_buy else -total_notional_to_close

        step2 = {
            "coin": coin,
            "is_buy": close_is_buy,
            "sz": close_sz,
            "price": price,
            "current_value": current_value
            + (
                min_increase_sz * price
                if increase_is_buy
                else -(min_increase_sz * price)
            ),
            "target_value": 0,
            "delta_value": step2_delta,
            "type": "close",
            "force": True,
            "force_id": force_id,
            "force_seq": 1,
            "estimated_fee": abs(step2_delta) * taker_rate,
        }

        # Ensure both meet minimum notional
        if (step1["sz"] * price) < min_trade_value or (
            step2["sz"] * price
        ) < min_trade_value:
            return (
                None,
                f"Below minimum even after force composition (${min_trade_value})",
            )

        return [step1, step2], None

    def _round_size_up_to_min_notional(
        self, coin: str, target_notional: float, price: float
    ) -> tuple[float, int] | None:
        """Return (size, decimals) such that size*price >= target_notional after rounding to szDecimals.

        Rounds up to the nearest step defined by szDecimals to satisfy the notional constraint.
        """
        sz_decimals = self._get_sz_decimals(coin)
        if sz_decimals is None:
            return None
        raw_size = target_notional / price if price > 0 else 0
        if raw_size <= 0:
            return (0.0, sz_decimals)
        step = 10 ** (-sz_decimals)
        # Avoid floating imprecision by working in integer steps
        steps_needed = math.ceil(raw_size / step)
        rounded_up_size = steps_needed * step
        # Round to the allowed decimals to avoid long floats
        rounded_up_size = round(rounded_up_size, sz_decimals)
        return rounded_up_size, sz_decimals

    def _execute_trades(self, trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Executes a list of trades sequentially with configurable order type and time-in-force."""
        if not trades:
            return []

        successful_trades = []
        failed_trades = []

        # Show progress during execution
        self.callbacks.info(f"Executing {len(trades)} trades...")

        for i, trade in enumerate(trades, 1):
            # Notify callback of trade start
            self.callbacks.on_trade_start(i, len(trades), trade)

            try:
                self.logger.debug(f"Executing trade: {trade}")
                
                coin = trade["coin"]
                is_buy = trade["is_buy"]
                size = trade["sz"]
                
                # Determine limit price based on order_type
                if self.config.execution.order_type == "limit":
                    # Use passive pricing: buy below mid, sell above mid
                    mid_price = float(self.info.all_mids()[coin])
                    offset = self.config.execution.limit_price_offset
                    
                    if is_buy:
                        limit_px = self._round_price_perp(coin, mid_price * (1 - offset))
                    else:
                        limit_px = self._round_price_perp(coin, mid_price * (1 + offset))
                else:  # market
                    # Use slippage price (aggressive) for market orders
                    limit_px = self.exchange._slippage_price(
                        coin, is_buy, self.config.execution.slippage_tolerance
                    )
                
                # Build single order request
                order_request = {
                    "coin": coin,
                    "is_buy": is_buy,
                    "sz": size,
                    "limit_px": limit_px,
                    "order_type": {"limit": {"tif": self.config.execution.time_in_force}},
                    "reduce_only": False,
                }
                
                # Execute single order via bulk_orders with single-item list
                result = self.exchange.bulk_orders([order_request])

                # Handle error responses
                if result.get("status") == "err":
                    error_msg = result.get("response", "Unknown error")
                    self.callbacks.on_trade_fail(trade, error_msg)
                    failed_trades.append(trade)
                    continue

                # Handle success responses
                response = result.get("response", {})
                if not isinstance(response, dict):
                    self.callbacks.on_trade_fail(trade, f"Unexpected response format: {response}")
                    failed_trades.append(trade)
                    continue

                statuses = response.get("data", {}).get("statuses", [])
                
                if not statuses:
                    self.callbacks.on_trade_fail(trade, "No status returned")
                    failed_trades.append(trade)
                    continue
                
                status = statuses[0]  # Get first (and only) status

                # Check for filled orders
                if "filled" in status:
                    filled_data = status["filled"]
                    avg_px = float(filled_data.get("avgPx", trade["price"]))

                    # Calculate slippage
                    if trade["is_buy"]:
                        slippage_pct = (
                            (avg_px - trade["price"]) / trade["price"]
                        ) * 100
                    else:
                        slippage_pct = (
                            (trade["price"] - avg_px) / trade["price"]
                        ) * 100

                    # Extract actual fee from API response
                    actual_fee = float(filled_data.get("fee", 0))

                    self.callbacks.on_trade_fill(trade, filled_data, slippage_pct)

                    successful_trades.append(
                        {
                            **trade,
                            "fill_data": filled_data,
                            "slippage_pct": slippage_pct,
                            "actual_fee": actual_fee,
                            "status": "filled",
                        }
                    )
                
                # Check for resting orders (Gtc/Alo orders posted to book)
                elif "resting" in status and self.config.execution.time_in_force in ("Gtc", "Alo"):
                    resting_data = status["resting"]
                    oid = resting_data.get("oid")
                    
                    # This is a success for Gtc/Alo - order is on the book
                    self.callbacks.info(
                        f"  {trade['coin']}: Order posted to book (OID: {oid}). "
                        f"Check with 'cc-liquid orders'"
                    )

                    successful_trades.append(
                        {
                            **trade,
                            "resting": True,
                            "oid": oid,
                            "status": "resting",
                        }
                    )
                
                # Handle errors or actual failures
                else:
                    if "error" in status:
                        error_msg = status["error"]
                    else:
                        error_msg = "Order rejected or not filled"

                    self.callbacks.on_trade_fail(trade, error_msg)
                    failed_trades.append(trade)

            except Exception as e:
                self.callbacks.on_trade_fail(trade, str(e))
                self.logger.error(f"Error executing trade for {trade['coin']}: {e}")
                failed_trades.append(trade)

        # Notify callback of batch completion
        self.callbacks.on_batch_complete(successful_trades, failed_trades)

        return successful_trades

    def load_state(self) -> datetime | None:
        """Public wrapper to load last rebalance timestamp."""
        return self._load_state()

    def save_state(self, last_rebalance_date: datetime) -> None:
        """Public wrapper to persist last rebalance timestamp."""
        self._save_state(last_rebalance_date)

    def compute_next_rebalance_time(
        self, last_rebalance_date: datetime | None, now: datetime | None = None
    ) -> datetime:
        """Compute the next scheduled rebalance timestamp in UTC.

        Rules:
        - If this is the first run (no last date): schedule for today at configured time; if
          already past that time, return "now" to indicate it is due immediately.
        - Otherwise: schedule exactly every_n_days after the last rebalance date, at the
          configured time.
        """
        cfg = self.config.portfolio.rebalancing
        now_utc = now or datetime.now(timezone.utc)

        hour, minute = map(int, cfg.at_time.split(":"))
        rebalance_time = time(hour=hour, minute=minute)

        if last_rebalance_date is None:
            today_at = datetime.combine(
                now_utc.date(), rebalance_time, tzinfo=timezone.utc
            )
            return today_at if now_utc < today_at else now_utc

        # Rolling mode = daily; full mode = every_n_days
        interval = 1 if cfg.mode == "rolling" else cfg.every_n_days
        next_date = last_rebalance_date.date() + timedelta(days=interval)
        return datetime.combine(next_date, rebalance_time, tzinfo=timezone.utc)

    def _load_state(self) -> datetime | None:
        """Load the last rebalance date from persistent state."""
        import json
        import os

        state_file = ".cc_liquid_state.json"
        if not os.path.exists(state_file):
            return None

        try:
            with open(state_file) as f:
                state = json.load(f)
                last_date = datetime.fromisoformat(state.get("last_rebalance_date"))
                return last_date
        except Exception as e:
            self.logger.warning(f"Could not load state file: {e}")
            return None

    def _save_state(self, last_rebalance_date: datetime):
        """Save the last rebalance date to persistent state."""
        import json

        state_file = ".cc_liquid_state.json"
        # Preserve existing vintages when saving
        existing_vintages = self._load_vintages()
        state = {"last_rebalance_date": last_rebalance_date.isoformat()}
        if existing_vintages:
            state["vintages"] = existing_vintages
        with open(state_file, "w") as f:
            json.dump(state, f)

    def _load_vintages(self) -> dict[str, dict[str, float]]:
        """Load vintages from state file.

        Returns:
            Dict mapping date string (YYYY-MM-DD) to {asset: units} dict.
            Units are signed: positive=long, negative=short.
        """
        import json
        import os

        state_file = ".cc_liquid_state.json"
        if not os.path.exists(state_file):
            return {}

        try:
            with open(state_file) as f:
                state = json.load(f)
                return state.get("vintages", {})
        except Exception as e:
            self.logger.warning(f"Could not load vintages from state: {e}")
            return {}

    def _save_vintages(self, vintages: dict[str, dict[str, float]]) -> None:
        """Save vintages to state file, preserving other state."""
        import json
        import os

        state_file = ".cc_liquid_state.json"

        # Load existing state to preserve other fields
        existing_state = {}
        if os.path.exists(state_file):
            try:
                with open(state_file) as f:
                    existing_state = json.load(f)
            except Exception:
                pass

        existing_state["vintages"] = vintages
        with open(state_file, "w") as f:
            json.dump(existing_state, f)

    def _prune_expired_vintages(
        self, vintages: dict[str, dict[str, float]], today: datetime, rolling_days: int
    ) -> dict[str, dict[str, float]]:
        """Remove vintages older than rolling_days."""
        from datetime import date as date_type

        if isinstance(today, datetime):
            today_date = today.date()
        else:
            today_date = today

        cutoff = today_date - timedelta(days=rolling_days)

        pruned = {}
        for date_str, positions in vintages.items():
            vintage_date = date_type.fromisoformat(date_str)
            if vintage_date > cutoff:
                pruned[date_str] = positions

        return pruned

    def plan_rolling_rebalance(self, predictions: pl.DataFrame | None = None) -> dict:
        """Compute a rolling rebalance plan using vintage-based position management.

        In rolling mode:
        - Each day creates a "vintage" with 1/N of target allocation
        - Vintages expire after rolling_days
        - Final portfolio = sum of all active vintage positions
        - Trade = diff between target sum and current positions

        Returns:
            Plan dict compatible with execute_plan()
        """
        rolling_days = self.config.portfolio.rebalancing.rolling_days
        seed_full = self.config.portfolio.rebalancing.seed_full
        today = datetime.now(timezone.utc)
        today_str = today.date().isoformat()

        # Check for open orders (warning if present)
        open_orders = self.get_open_orders()
        if open_orders:
            self.callbacks.warn(
                f"Found {len(open_orders)} open order(s). These may conflict with rebalancing."
            )

        # Load predictions if not provided
        if predictions is None:
            self.callbacks.info("Loading predictions...")
            predictions = self._load_predictions()

            if predictions is None or predictions.is_empty():
                self.callbacks.error("No predictions available, cannot rebalance")
                return {
                    "target_positions": {},
                    "trades": [],
                    "skipped_trades": [],
                    "account_value": 0.0,
                    "leverage": self.config.portfolio.target_leverage,
                    "open_orders": open_orders,
                    "vintages": {},
                }

        # Load and prune existing vintages
        vintages = self._load_vintages()
        vintages = self._prune_expired_vintages(vintages, today, rolling_days)

        # If no vintages and seed_full enabled, seed from historical predictions
        if not vintages and seed_full:
            self.callbacks.info(f"Seeding {rolling_days} vintages from historical predictions...")
            vintages = self._seed_vintages_from_history(predictions, today, rolling_days)
        else:
            # Create today's vintage (if not already created today)
            if today_str not in vintages:
                self.callbacks.info(f"Creating vintage for {today_str}...")
                new_vintage = self._create_daily_vintage(predictions, rolling_days)
                if new_vintage:
                    vintages[today_str] = new_vintage

        # Aggregate all vintages to get global target (in units)
        global_target_units = self._aggregate_vintages(vintages)

        # Convert to USD for trade calculation
        all_mids = self.info.all_mids()
        global_target_usd = {}
        for coin, units in global_target_units.items():
            if coin in all_mids:
                price = float(all_mids[coin])
                global_target_usd[coin] = units * price

        # Get current positions and calculate trades
        current_positions = self.get_positions()
        trades, skipped_trades = self._calculate_trades(global_target_usd, current_positions)

        # Save updated vintages
        self._save_vintages(vintages)

        account_value = self.get_account_value()
        return {
            "target_positions": global_target_usd,
            "trades": trades,
            "skipped_trades": skipped_trades,
            "account_value": account_value,
            "leverage": self.config.portfolio.target_leverage,
            "open_orders": open_orders,
            "vintages": vintages,
            "active_vintage_count": len(vintages),
        }

    def _create_daily_vintage(
        self, predictions: pl.DataFrame, rolling_days: int
    ) -> dict[str, float]:
        """Create a single vintage from today's predictions.

        Returns:
            Dict mapping asset to signed units (positive=long, negative=short)
        """
        # Scale parameters for single vintage
        # Note: We do NOT scale num_long/num_short. Each vintage should be a slice of the FULL strategy.
        # If full strategy wants top 10, each vintage should buy 1/30th of the top 10.
        scaled_leverage = self.config.portfolio.target_leverage / rolling_days
        
        # Get target USD values using scaled leverage but FULL counts
        vintage_targets_usd = self._get_target_positions(
            predictions,
            override_leverage=scaled_leverage,
            quiet=True,
        )

        if not vintage_targets_usd:
            return {}

        # Convert USD to units for storage
        all_mids = self.info.all_mids()
        vintage_units = {}
        for coin, usd_val in vintage_targets_usd.items():
            if coin in all_mids:
                price = float(all_mids[coin])
                if price > 0:
                    vintage_units[coin] = usd_val / price

        return vintage_units

    def _seed_vintages_from_history(
        self, predictions: pl.DataFrame, today: datetime, rolling_days: int
    ) -> dict[str, dict[str, float]]:
        """Create N vintages from historical predictions for immediate full deployment.

        This provides time-diversification from day 1 instead of gradual ramp-up.
        """
        date_col = self.config.data.date_column
        today_date = today.date()

        # Get unique prediction dates, sorted descending
        pred_dates = (
            predictions.select(pl.col(date_col).dt.date().alias("pred_date"))
            .unique()
            .sort("pred_date", descending=True)
        )
        available_dates = pred_dates["pred_date"].to_list()

        vintages = {}

        for i in range(min(rolling_days, len(available_dates))):
            # Synthetic vintage date: stagger backwards from today
            vintage_date = today_date - timedelta(days=i)
            vintage_date_str = vintage_date.isoformat()

            # Get predictions from this historical date
            pred_date = available_dates[i]
            day_preds = predictions.filter(
                pl.col(date_col).dt.date() == pred_date
            )

            if day_preds.is_empty():
                continue

            # Create vintage for this day
            vintage = self._create_daily_vintage(day_preds, rolling_days)
            if vintage:
                vintages[vintage_date_str] = vintage
                self.callbacks.info(f"  Seeded vintage {vintage_date_str} from {pred_date}")

        self.callbacks.info(f"Seeded {len(vintages)} vintages")
        return vintages

    def _aggregate_vintages(
        self, vintages: dict[str, dict[str, float]]
    ) -> dict[str, float]:
        """Sum all vintage positions to get global target in units."""
        global_target = {}
        for vintage in vintages.values():
            for coin, units in vintage.items():
                global_target[coin] = global_target.get(coin, 0.0) + units
        return global_target

    def get_vintages_summary(self) -> list[dict[str, Any]]:
        """Get summary of active vintages for display."""
        vintages = self._load_vintages()
        if not vintages:
            return []

        all_mids = self.info.all_mids()
        today = datetime.now(timezone.utc).date()
        rolling_days = self.config.portfolio.rebalancing.rolling_days

        summary = []
        for date_str, positions in sorted(vintages.items()):
            from datetime import date as date_type
            vintage_date = date_type.fromisoformat(date_str)
            age = (today - vintage_date).days
            expires_in = rolling_days - age

            # Calculate vintage value
            total_value = 0.0
            for coin, units in positions.items():
                if coin in all_mids:
                    price = float(all_mids[coin])
                    total_value += abs(units * price)

            summary.append({
                "date": date_str,
                "age_days": age,
                "expires_in_days": expires_in,
                "num_positions": len(positions),
                "value_usd": total_value,
            })

        return summary

    def get_open_orders(self) -> list[dict[str, Any]]:
        """Get current open orders.

        Returns:
            List of open orders with details like coin, size, limit price, side,
            orderType, isTrigger, triggerPx, etc.
        """
        owner = self.config.HYPERLIQUID_VAULT_ADDRESS or self.config.HYPERLIQUID_ADDRESS
        if not owner:
            raise ValueError("Missing portfolio owner address")
        return self.info.frontend_open_orders(owner)

    def cancel_open_orders(self, coin: str | None = None) -> dict[str, Any]:
        """Cancel open orders, optionally filtered by coin.

        Args:
            coin: If provided, only cancel orders for this coin. If None, cancel all.

        Returns:
            Result of the cancel operation
        """
        open_orders = self.get_open_orders()

        if not open_orders:
            return {"status": "ok", "response": "No open orders to cancel"}

        # Filter by coin if specified
        if coin:
            orders_to_cancel = [o for o in open_orders if o["coin"] == coin]
        else:
            orders_to_cancel = open_orders

        if not orders_to_cancel:
            return {
                "status": "ok",
                "response": f"No open orders found for {coin}" if coin else "No orders to cancel",
            }

        # Build cancel requests
        cancel_requests = [
            {"coin": order["coin"], "oid": order["oid"]} for order in orders_to_cancel
        ]

        # Execute bulk cancel
        self.logger.info(f"Cancelling {len(cancel_requests)} open orders...")
        result = self.exchange.bulk_cancel(cancel_requests)

        return result

    def get_fill_history(
        self, start_time: int | None = None, end_time: int | None = None
    ) -> list[dict[str, Any]]:
        """Get fill history with optional time range.

        Args:
            start_time: Unix timestamp in milliseconds (optional)
            end_time: Unix timestamp in milliseconds (optional)

        Returns:
            List of fills with execution details, prices, sizes, and fees
        """
        owner = self.config.HYPERLIQUID_VAULT_ADDRESS or self.config.HYPERLIQUID_ADDRESS
        if not owner:
            raise ValueError("Missing portfolio owner address")

        if start_time is not None:
            return self.info.user_fills_by_time(owner, start_time, end_time)
        return self.info.user_fills(owner)

    def get_fee_summary(self) -> dict[str, Any]:
        """Get fee rates and trading volume statistics.

        Returns:
            Dictionary containing fee rates (maker/taker), volume stats, and fee schedule
        """
        owner = self.config.HYPERLIQUID_VAULT_ADDRESS or self.config.HYPERLIQUID_ADDRESS
        if not owner:
            raise ValueError("Missing portfolio owner address")
        return self.info.user_fees(owner)

    def _should_apply_stop_loss(self, side: str) -> bool:
        """Check if stop loss should be applied to a position side."""
        sides_config = self.config.portfolio.stop_loss.sides
        if sides_config == "none":
            return False
        if sides_config == "both":
            return True
        if sides_config == "long_only" and side == "LONG":
            return True
        if sides_config == "short_only" and side == "SHORT":
            return True
        return False

    def cancel_all_tpsl_orders(self) -> dict[str, Any]:
        """Cancel all existing TP/SL orders across the portfolio."""
        open_orders = self.get_open_orders()
        
        if not open_orders:
            return {"status": "ok", "response": "No open orders", "cancelled": 0}
        
        # Filter for TP/SL orders using the isTrigger field from frontend_open_orders
        tpsl_orders = [o for o in open_orders if o.get("isTrigger")]
        
        if not tpsl_orders:
            self.callbacks.info(f"No existing TP/SL orders to cancel (found {len(open_orders)} other orders)")
            return {"status": "ok", "response": "No TP/SL orders to cancel", "cancelled": 0}
        
        cancel_requests = [
            {"coin": order["coin"], "oid": order["oid"]} 
            for order in tpsl_orders
        ]
        
        self.callbacks.info(f"Cancelling {len(cancel_requests)} existing TP/SL order(s)...")
        result = self.exchange.bulk_cancel(cancel_requests)
        result["cancelled"] = len(cancel_requests)
        return result

    def apply_stop_losses(self) -> dict[str, Any]:
        """Apply stop losses to all current open positions per config.
        
        Returns:
            Dict with counts of applied/skipped SLs and any errors
        """
        if self.config.portfolio.stop_loss.sides == "none":
            return {
                "status": "disabled",
                "message": "Stop losses disabled in config (stop_loss.sides=none)"
            }
        
        # Get current positions
        positions = self.get_positions()
        if not positions:
            return {
                "status": "ok",
                "applied": 0,
                "message": "No open positions to protect"
            }
        
        # Cancel existing TP/SL orders first
        self.cancel_all_tpsl_orders()
        
        applied = []
        skipped = []
        errors = []
        
        # Count eligible positions first for progress tracking
        eligible_positions = []
        for coin, position in positions.items():
            size = float(position.get("szi", 0))
            if size == 0:
                continue
            side = "LONG" if size > 0 else "SHORT"
            if self._should_apply_stop_loss(side):
                eligible_positions.append(coin)

        # Build all SL orders first
        orders_to_place = []
        order_metadata = []  # Track metadata for each order
        
        for coin, position in positions.items():
            size = float(position.get("szi", 0))
            if size == 0:
                continue
            
            side = "LONG" if size > 0 else "SHORT"
            
            # Check if this side should have SL
            if not self._should_apply_stop_loss(side):
                skipped.append({"coin": coin, "reason": f"Side {side} not configured"})
                continue
            
            # Get entry price
            entry_px = float(position.get("entryPx", 0))
            if entry_px <= 0:
                skipped.append({"coin": coin, "reason": "Invalid entry price"})
                continue
            
            # Calculate trigger price
            stop_pct = self.config.portfolio.stop_loss.pct
            if side == "LONG":
                trigger_px = entry_px * (1 - stop_pct)
                is_buy = False  # SL on long = sell
            else:  # SHORT
                trigger_px = entry_px * (1 + stop_pct)
                is_buy = True  # SL on short = buy
            
            # Calculate limit price with slippage
            slippage = self.config.portfolio.stop_loss.slippage
            if is_buy:
                limit_px = trigger_px * (1 + slippage)
            else:
                limit_px = trigger_px * (1 - slippage)
            
            # Round prices
            trigger_px = self._round_price_perp(coin, trigger_px)
            limit_px = self._round_price_perp(coin, limit_px)
            
            # Round size
            rounded = self._round_size(coin, abs(size))
            if rounded is None:
                skipped.append({"coin": coin, "reason": "Unknown szDecimals"})
                continue
            sl_size, _ = rounded
            
            # Build SL order
            sl_order = {
                "coin": coin,
                "is_buy": is_buy,
                "sz": sl_size,
                "limit_px": limit_px,
                "order_type": {
                    "trigger": {
                        "isMarket": False,  # Use limit for custom slippage
                        "triggerPx": trigger_px,  # SDK handles string conversion
                        "tpsl": "sl"
                    }
                },
                "reduce_only": True,
            }
            
            orders_to_place.append(sl_order)
            order_metadata.append({
                "coin": coin,
                "side": side,
                "entry_px": entry_px,
                "trigger_px": trigger_px,
                "limit_px": limit_px,
                "size": sl_size
            })
        
        # Place all orders in one batch
        if orders_to_place:
            self.callbacks.info(f"Placing {len(orders_to_place)} stop loss order(s) in batch...")
            
            try:
                result = self.exchange.bulk_orders(orders_to_place)
                
                if result.get("status") == "ok":
                    # Process response statuses
                    response = result.get("response", {})
                    statuses = response.get("data", {}).get("statuses", [])
                    
                    for i, status in enumerate(statuses):
                        if i >= len(order_metadata):
                            break
                        
                        metadata = order_metadata[i]
                        
                        if "resting" in status:
                            # SL order successfully placed
                            applied.append(metadata)
                        elif "error" in status:
                            errors.append({
                                "coin": metadata["coin"],
                                "error": status["error"]
                            })
                        else:
                            # Unexpected status
                            errors.append({
                                "coin": metadata["coin"],
                                "error": f"Unexpected status: {status}"
                            })
                else:
                    # Bulk operation failed entirely
                    for metadata in order_metadata:
                        errors.append({
                            "coin": metadata["coin"],
                            "error": result.get("response", "Bulk operation failed")
                        })
            except Exception as e:
                # Exception during bulk operation
                for metadata in order_metadata:
                    errors.append({
                        "coin": metadata["coin"],
                        "error": str(e)
                    })
        
        return {
            "status": "ok",
            "applied": applied,
            "skipped": skipped,
            "errors": errors,
            "total_applied": len(applied),
            "total_skipped": len(skipped),
            "total_errors": len(errors)
        }

    def _load_predictions(self) -> pl.DataFrame | None:
        """Load predictions based on configured data source."""
        try:
            if self.config.data.source == "local":
                # Use local file
                predictions = DataLoader.from_file(
                    self.config.data.path,
                    date_col=self.config.data.date_column,
                    id_col=self.config.data.asset_id_column,
                    pred_col=self.config.data.prediction_column,
                )
            elif self.config.data.source == "crowdcent":
                # Download and use CrowdCent meta model
                predictions = DataLoader.from_crowdcent_api(
                    api_key=self.config.CROWDCENT_API_KEY,
                    download_path=self.config.data.path,
                    date_col=self.config.data.date_column,
                    id_col=self.config.data.asset_id_column,
                    pred_col=self.config.data.prediction_column,
                )
            elif self.config.data.source == "numerai":
                # Download and use Numerai meta model
                predictions = DataLoader.from_numerai_api(
                    download_path=self.config.data.path,
                    date_col=self.config.data.date_column,
                    id_col=self.config.data.asset_id_column,
                    pred_col=self.config.data.prediction_column,
                )
            else:
                raise ValueError(f"Unknown data source: {self.config.data.source}")

            return predictions

        except Exception as e:
            self.logger.error(f"Error loading predictions: {e}")
            return None
