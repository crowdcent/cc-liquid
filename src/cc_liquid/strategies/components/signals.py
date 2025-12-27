"""Signal generation components."""

from typing import Protocol
import polars as pl


class SignalGenerator(Protocol):
    """Interface for generating trading signals from predictions.

    Signals determine WHICH assets to trade (selection logic).
    Does not determine position sizes - that's handled by PositionSizer.
    """

    def generate_signals(
        self,
        predictions: pl.DataFrame,
        date_col: str,
        asset_col: str,
        pred_col: str,
    ) -> tuple[list[str], list[str]]:
        """Generate long and short asset lists.

        Args:
            predictions: DataFrame with predictions
            date_col: Name of date column
            asset_col: Name of asset ID column
            pred_col: Name of prediction column

        Returns:
            Tuple of (long_assets, short_assets)
        """
        ...


class TopNSignals:
    """Select top N assets by prediction strength.

    This is the standard signal used by both full and rolling modes.
    Higher predictions = stronger longs, lower predictions = stronger shorts.
    """

    def __init__(self, num_long: int, num_short: int):
        """
        Args:
            num_long: Number of long positions
            num_short: Number of short positions
        """
        self.num_long = num_long
        self.num_short = num_short

    def generate_signals(
        self,
        predictions: pl.DataFrame,
        date_col: str,
        asset_col: str,
        pred_col: str,
    ) -> tuple[list[str], list[str]]:
        """Select top/bottom N by prediction value."""
        # Get latest predictions only
        latest = predictions.group_by(asset_col).agg(
            pl.col(date_col).max().alias("latest_date"),
            pl.col(pred_col).last().alias("latest_pred"),
        )

        # Sort by prediction strength
        sorted_preds = latest.sort("latest_pred", descending=True)

        # Select top N longs
        long_assets = sorted_preds.head(self.num_long)[asset_col].to_list()

        # Select bottom N shorts
        short_assets = (
            sorted_preds.tail(self.num_short)[asset_col].to_list()
            if self.num_short > 0
            else []
        )

        return long_assets, short_assets


class MeanReversionSignals:
    """Select assets based on z-score deviation (mean reversion).

    Example of a different signal generation strategy.
    Long oversold assets, short overbought assets.
    """

    def __init__(
        self,
        lookback_days: int = 30,
        z_threshold: float = 2.0,
        max_positions: int = 20,
    ):
        """
        Args:
            lookback_days: Rolling window for mean/std calculation
            z_threshold: Z-score threshold for entry (absolute value)
            max_positions: Maximum positions per side
        """
        self.lookback_days = lookback_days
        self.z_threshold = z_threshold
        self.max_positions = max_positions

    def generate_signals(
        self,
        predictions: pl.DataFrame,
        date_col: str,
        asset_col: str,
        pred_col: str,
    ) -> tuple[list[str], list[str]]:
        """Generate mean reversion signals."""
        # Calculate rolling z-scores
        with_zscore = predictions.with_columns([
            (
                (pl.col(pred_col) - pl.col(pred_col).rolling_mean(self.lookback_days))
                / pl.col(pred_col).rolling_std(self.lookback_days)
            ).alias("z_score")
        ])

        # Get latest for each asset
        latest = with_zscore.group_by(asset_col).agg([
            pl.col("z_score").last(),
            pl.col(date_col).max(),
        ])

        # Long oversold (z < -threshold), short overbought (z > +threshold)
        long_candidates = latest.filter(
            pl.col("z_score") < -self.z_threshold
        ).sort("z_score")  # Most oversold first

        short_candidates = latest.filter(
            pl.col("z_score") > self.z_threshold
        ).sort("z_score", descending=True)  # Most overbought first

        long_assets = long_candidates.head(self.max_positions)[asset_col].to_list()
        short_assets = short_candidates.head(self.max_positions)[asset_col].to_list()

        return long_assets, short_assets
