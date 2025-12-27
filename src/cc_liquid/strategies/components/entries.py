"""Entry management components."""

from typing import Protocol, TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    from ...trader import CCLiquid
    from .state import StateManager


class EntryManager(Protocol):
    """Interface for managing how positions are entered.

    Entry managers control the TIMING and SCALING of entries:
    - Immediate: Enter all positions at once (full mode)
    - Vintage: Stagger entries over multiple days (rolling mode)
    """

    def calculate_target_positions(
        self,
        trader: "CCLiquid",
        long_assets: list[str],
        short_assets: list[str],
        target_leverage: float,
        rank_power: float,
        state_manager: "StateManager",
    ) -> dict[str, float]:
        """Calculate target positions in USD notional.

        Args:
            trader: CCLiquid instance for accessing utilities
            long_assets: List of assets to go long
            short_assets: List of assets to go short
            target_leverage: Total gross leverage target
            rank_power: Weighting concentration parameter
            state_manager: State manager for tracking vintages/history

        Returns:
            Dict mapping asset to target USD notional (signed)
        """
        ...


class ImmediateEntry:
    """Enter all positions immediately at full size.

    This is the entry manager for FULL MODE.
    No time diversification - everything happens at once.
    """

    def calculate_target_positions(
        self,
        trader: "CCLiquid",
        long_assets: list[str],
        short_assets: list[str],
        target_leverage: float,
        rank_power: float,
        state_manager: "StateManager",
    ) -> dict[str, float]:
        """Calculate full-size positions for immediate entry."""
        # Use trader's existing utility - this already handles rank_power weighting
        from ...portfolio import weights_from_ranks

        account_value = trader.get_account_value()

        # Get latest predictions for weighting
        predictions = trader._load_predictions()
        if predictions is None or predictions.is_empty():
            return {}

        latest_predictions = trader._get_latest_predictions(predictions)
        tradeable_predictions = trader._filter_tradeable_predictions(latest_predictions)

        if tradeable_predictions.height == 0:
            return {}

        id_col = trader.config.data.asset_id_column
        pred_col = trader.config.data.prediction_column

        # Calculate weights using shared utility
        weights = weights_from_ranks(
            latest_preds=tradeable_predictions.select([id_col, pred_col]),
            id_col=id_col,
            pred_col=pred_col,
            long_assets=long_assets,
            short_assets=short_assets,
            target_gross=target_leverage,
            power=rank_power,
        )

        # Convert leverage to USD notional
        target_positions = {
            asset: weight * account_value for asset, weight in weights.items()
        }

        return target_positions


class VintageEntry:
    """Enter positions via daily vintages for time diversification.

    This is the entry manager for ROLLING MODE.
    Spreads entries across rolling_days to reduce timing risk.
    """

    def __init__(self, rolling_days: int, seed_full: bool = False):
        """
        Args:
            rolling_days: Number of days to spread entries across
            seed_full: If True, seed all vintages on first run
        """
        self.rolling_days = rolling_days
        self.seed_full = seed_full

    def calculate_target_positions(
        self,
        trader: "CCLiquid",
        long_assets: list[str],
        short_assets: list[str],
        target_leverage: float,
        rank_power: float,
        state_manager: "StateManager",
    ) -> dict[str, float]:
        """Calculate aggregated target from all active vintages."""
        from ...portfolio import weights_from_ranks

        today = datetime.now(timezone.utc)
        today_str = today.date().isoformat()

        # Load predictions
        predictions = trader._load_predictions()
        if predictions is None or predictions.is_empty():
            return {}

        # Get or initialize vintages from state
        vintages = state_manager.get_state().get("vintages", {})

        # Prune expired vintages
        vintages = self._prune_expired_vintages(vintages, today)

        # If no vintages and seed_full enabled, seed from history
        if not vintages and self.seed_full:
            trader.callbacks.info(
                f"Seeding {self.rolling_days} vintages from historical predictions..."
            )
            vintages = self._seed_vintages_from_history(
                trader, predictions, today, long_assets, short_assets,
                target_leverage, rank_power
            )
        else:
            # Create today's vintage if not already created
            if today_str not in vintages:
                trader.callbacks.info(f"Creating vintage for {today_str}...")
                new_vintage = self._create_daily_vintage(
                    trader, predictions, long_assets, short_assets,
                    target_leverage, rank_power
                )
                if new_vintage:
                    vintages[today_str] = new_vintage

        # Save updated vintages
        state_manager.update_state({"vintages": vintages})

        # Aggregate all vintages to get global target (in units)
        global_target_units = self._aggregate_vintages(vintages)

        # Convert units to USD notional
        all_mids = trader.info.all_mids()
        global_target_usd = {}
        for coin, units in global_target_units.items():
            if coin in all_mids:
                price = float(all_mids[coin])
                global_target_usd[coin] = units * price

        return global_target_usd

    def _create_daily_vintage(
        self,
        trader,
        predictions,
        long_assets: list[str],
        short_assets: list[str],
        target_leverage: float,
        rank_power: float,
    ) -> dict[str, float]:
        """Create a single vintage with 1/N of target allocation."""
        from ...portfolio import weights_from_ranks

        # Scale leverage for single vintage
        scaled_leverage = target_leverage / self.rolling_days

        latest_predictions = trader._get_latest_predictions(predictions)
        tradeable_predictions = trader._filter_tradeable_predictions(latest_predictions)

        if tradeable_predictions.height == 0:
            return {}

        id_col = trader.config.data.asset_id_column
        pred_col = trader.config.data.prediction_column

        # Calculate weights for this vintage
        weights = weights_from_ranks(
            latest_preds=tradeable_predictions.select([id_col, pred_col]),
            id_col=id_col,
            pred_col=pred_col,
            long_assets=long_assets,
            short_assets=short_assets,
            target_gross=scaled_leverage,
            power=rank_power,
        )

        account_value = trader.get_account_value()

        # Convert to units (not USD) for vintage storage
        all_mids = trader.info.all_mids()
        vintage_units = {}
        for asset, weight in weights.items():
            if asset in all_mids:
                price = float(all_mids[asset])
                usd_notional = weight * account_value
                units = usd_notional / price
                vintage_units[asset] = units

        return vintage_units

    def _seed_vintages_from_history(
        self, trader, predictions, today, long_assets, short_assets,
        target_leverage, rank_power
    ) -> dict[str, dict[str, float]]:
        """Seed all vintages from historical predictions."""
        from datetime import timedelta

        vintages = {}
        for days_ago in range(self.rolling_days - 1, -1, -1):
            vintage_date = (today - timedelta(days=days_ago)).date()
            vintage_str = vintage_date.isoformat()

            # Filter predictions to this date
            date_col = trader.config.data.date_column
            historical_preds = predictions.filter(
                pl.col(date_col) == vintage_date
            )

            if historical_preds.is_empty():
                continue

            vintage = self._create_daily_vintage(
                trader, historical_preds, long_assets, short_assets,
                target_leverage, rank_power
            )

            if vintage:
                vintages[vintage_str] = vintage

        return vintages

    def _aggregate_vintages(self, vintages: dict) -> dict[str, float]:
        """Sum all vintage positions to get total target in units."""
        global_target = {}
        for vintage_positions in vintages.values():
            for asset, units in vintage_positions.items():
                global_target[asset] = global_target.get(asset, 0.0) + units
        return global_target

    def _prune_expired_vintages(self, vintages: dict, today: datetime) -> dict:
        """Remove vintages older than rolling_days."""
        from datetime import timedelta, date as date_type

        today_date = today.date() if isinstance(today, datetime) else today
        cutoff = today_date - timedelta(days=self.rolling_days)

        pruned = {}
        for date_str, positions in vintages.items():
            vintage_date = date_type.fromisoformat(date_str)
            if vintage_date > cutoff:
                pruned[date_str] = positions

        return pruned
