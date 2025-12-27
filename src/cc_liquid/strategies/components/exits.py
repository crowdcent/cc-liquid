"""Exit rule components."""

from typing import Protocol, TYPE_CHECKING
from datetime import datetime, timezone, timedelta

if TYPE_CHECKING:
    from ...trader import CCLiquid


class ExitRule(Protocol):
    """Interface for position exit rules.

    Exit rules determine WHEN to close positions.
    Multiple exit rules can be combined (OR logic: exit if ANY rule triggers).
    """

    def should_exit_positions(
        self, trader: "CCLiquid"
    ) -> dict[str, bool]:
        """Determine which positions should be exited.

        Args:
            trader: CCLiquid instance

        Returns:
            Dict mapping asset to whether it should exit
        """
        ...


class FullRebalanceExit:
    """Exit all positions on every rebalance.

    This is the exit rule for FULL MODE.
    On each rebalance, the entire portfolio is replaced.
    """

    def should_exit_positions(self, trader: "CCLiquid") -> dict[str, bool]:
        """Exit all current positions (will be replaced by new signals)."""
        # In full mode, we don't explicitly exit - we just let the
        # target position calculation replace everything
        # Return empty dict to signal "let targets handle it"
        return {}


class TimeBasedExit:
    """Exit positions after holding for N days.

    This is the exit rule for ROLLING MODE (handled by vintage expiry).
    Also useful for other time-limited strategies.
    """

    def __init__(self, hold_days: int):
        """
        Args:
            hold_days: Number of days to hold positions before exit
        """
        self.hold_days = hold_days

    def should_exit_positions(self, trader: "CCLiquid") -> dict[str, bool]:
        """Exit positions held longer than hold_days."""
        # Note: For rolling mode, this is handled by vintage pruning
        # in VintageEntry, not here. This is for other strategies.

        # To implement this properly, we'd need position entry timestamps
        # stored in state. For now, return empty (handled by vintages).
        # A full implementation would track entry times in StateManager.

        # Example pseudo-code:
        # positions = trader.get_positions()
        # entry_times = state_manager.get_state().get("entry_times", {})
        # today = datetime.now(timezone.utc).date()
        #
        # should_exit = {}
        # for coin in positions.keys():
        #     entry_date = entry_times.get(coin)
        #     if entry_date:
        #         days_held = (today - entry_date).days
        #         should_exit[coin] = days_held >= self.hold_days
        #
        # return should_exit

        return {}


class TakeProfitExit:
    """Exit positions that hit profit threshold.

    This is the exit rule for TAKE_PROFIT strategies.
    Closes winning positions to lock in gains.
    """

    def __init__(self, threshold_pct: float):
        """
        Args:
            threshold_pct: Profit threshold (0.15 = 15%)
        """
        self.threshold_pct = threshold_pct

    def should_exit_positions(self, trader: "CCLiquid") -> dict[str, bool]:
        """Exit positions with unrealized PnL above threshold."""
        positions = trader.get_positions()
        if not positions:
            return {}

        # Get current prices
        all_mids = trader.info.all_mids()

        # Get user state to find entry prices
        user_state = trader.info.user_state(trader.address)
        if not user_state or "assetPositions" not in user_state:
            trader.callbacks.warn("Cannot calculate PnL - no position data")
            return {}

        should_exit = {}
        for position_data in user_state["assetPositions"]:
            coin = position_data["position"]["coin"]
            if coin not in positions:
                continue

            # Calculate unrealized PnL percentage
            entry_px = float(position_data["position"]["entryPx"])
            current_px = float(all_mids.get(coin, 0))
            size = float(position_data["position"]["szi"])

            if current_px == 0 or entry_px == 0:
                continue

            # Long: profit when price rises, Short: profit when price falls
            if size > 0:  # Long
                pnl_pct = (current_px - entry_px) / entry_px
            else:  # Short
                pnl_pct = (entry_px - current_px) / entry_px

            should_exit[coin] = pnl_pct >= self.threshold_pct

            if should_exit[coin]:
                trader.callbacks.info(
                    f"Take profit triggered for {coin}: "
                    f"{pnl_pct*100:+.2f}% (threshold: {self.threshold_pct*100:.2f}%)"
                )

        return should_exit


class StopLossExit:
    """Exit positions that hit loss threshold.

    Alternative to Hyperliquid's native stop losses.
    Closes losing positions to limit downside.
    """

    def __init__(self, threshold_pct: float):
        """
        Args:
            threshold_pct: Loss threshold as positive value (0.10 = -10% loss)
        """
        self.threshold_pct = abs(threshold_pct)

    def should_exit_positions(self, trader: "CCLiquid") -> dict[str, bool]:
        """Exit positions with unrealized PnL below -threshold."""
        positions = trader.get_positions()
        if not positions:
            return {}

        all_mids = trader.info.all_mids()
        user_state = trader.info.user_state(trader.address)

        if not user_state or "assetPositions" not in user_state:
            return {}

        should_exit = {}
        for position_data in user_state["assetPositions"]:
            coin = position_data["position"]["coin"]
            if coin not in positions:
                continue

            entry_px = float(position_data["position"]["entryPx"])
            current_px = float(all_mids.get(coin, 0))
            size = float(position_data["position"]["szi"])

            if current_px == 0 or entry_px == 0:
                continue

            # Calculate PnL
            if size > 0:  # Long
                pnl_pct = (current_px - entry_px) / entry_px
            else:  # Short
                pnl_pct = (entry_px - current_px) / entry_px

            should_exit[coin] = pnl_pct <= -self.threshold_pct

            if should_exit[coin]:
                trader.callbacks.warn(
                    f"Stop loss triggered for {coin}: "
                    f"{pnl_pct*100:+.2f}% (threshold: -{self.threshold_pct*100:.2f}%)"
                )

        return should_exit


class TrailingStopExit:
    """Exit positions that drop from peak by threshold.

    Locks in profits by trailing stop as position moves in your favor.
    """

    def __init__(self, trail_pct: float):
        """
        Args:
            trail_pct: Trailing distance from peak (0.10 = 10% from peak)
        """
        self.trail_pct = trail_pct

    def should_exit_positions(self, trader: "CCLiquid") -> dict[str, bool]:
        """Exit positions that dropped trail_pct from their peak."""
        # This would require tracking peak prices in state
        # Pseudo-implementation for reference:

        # state = state_manager.get_state()
        # peak_prices = state.get("peak_prices", {})
        # positions = trader.get_positions()
        # all_mids = trader.info.all_mids()
        #
        # should_exit = {}
        # for coin, size in positions.items():
        #     current_px = all_mids.get(coin, 0)
        #     peak_px = peak_prices.get(coin, current_px)
        #
        #     # Update peak
        #     if size > 0:  # Long
        #         peak_px = max(peak_px, current_px)
        #         drop_from_peak = (peak_px - current_px) / peak_px
        #     else:  # Short
        #         peak_px = min(peak_px, current_px) if peak_px else current_px
        #         drop_from_peak = (current_px - peak_px) / peak_px
        #
        #     peak_prices[coin] = peak_px
        #     should_exit[coin] = drop_from_peak >= self.trail_pct
        #
        # state_manager.update_state({"peak_prices": peak_prices})

        return {}
