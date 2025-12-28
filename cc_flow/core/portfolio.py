"""Portfolio construction logic for cc-flow.

This module provides the PortfolioManager class which calculates target positions
from predictions using either equal-weighting or rank-power weighting schemes.

The PortfolioManager follows these steps:
1. Select top N long and bottom N short assets from latest predictions
2. Calculate target weights using configured weighting scheme
3. Scale to target leverage
4. Generate TargetPosition instances sorted by coin

Classes:
    PortfolioManager: Manages portfolio construction from predictions

Example:
    >>> config = PortfolioConfig(
    ...     num_long=10,
    ...     num_short=5,
    ...     target_leverage=Decimal("1.5"),
    ...     rank_power=Decimal("0.0")  # Equal weighting
    ... )
    >>> manager = PortfolioManager(config=config)
    >>> positions = manager.calculate_target_positions(
    ...     predictions=predictions_df,
    ...     account_value=Decimal("50000.00")
    ... )
"""

from __future__ import annotations

from decimal import Decimal

import polars as pl

from cc_flow.domain.config import PortfolioConfig
from cc_flow.domain.portfolio import TargetPosition


class PortfolioManager:
    """Manages portfolio construction from predictions.

    The PortfolioManager takes a PortfolioConfig and uses it to calculate
    target positions from prediction data. It supports two weighting schemes:

    1. Equal weighting (rank_power = 0): All positions have equal weight
    2. Rank-power weighting (rank_power > 0): Positions weighted by 1/rank^power

    Attributes:
        config: Portfolio configuration with num_long, num_short, leverage, etc.

    Example:
        >>> config = PortfolioConfig(num_long=15, num_short=5)
        >>> manager = PortfolioManager(config=config)
        >>> positions = manager.calculate_target_positions(df, Decimal("10000"))
        >>> print(f"Created {len(positions)} positions")
        Created 20 positions
    """

    def __init__(self, config: PortfolioConfig):
        """Initialize PortfolioManager with configuration.

        Args:
            config: Portfolio configuration specifying position counts,
                    leverage, and weighting scheme
        """
        self.config = config

    def calculate_target_positions(
        self, predictions: pl.DataFrame, account_value: Decimal
    ) -> list[TargetPosition]:
        """Calculate target positions from predictions.

        Selects top long and bottom short assets from the latest predictions,
        then calculates target weights and values using the configured
        weighting scheme.

        Args:
            predictions: DataFrame with columns 'date', 'asset_id', 'prediction'
            account_value: Total account value in USD for position sizing

        Returns:
            List of TargetPosition instances sorted by coin name

        Example:
            >>> predictions = pl.DataFrame({
            ...     "date": [date(2024, 1, 10)] * 10,
            ...     "asset_id": [f"ASSET_{i}" for i in range(1, 11)],
            ...     "prediction": [0.9, 0.7, 0.5, 0.3, 0.1, -0.1, -0.3, -0.5, -0.7, -0.9]
            ... })
            >>> config = PortfolioConfig(num_long=3, num_short=2)
            >>> manager = PortfolioManager(config=config)
            >>> positions = manager.calculate_target_positions(
            ...     predictions, Decimal("10000.00")
            ... )
            >>> assert len(positions) == 5
        """
        top_long, top_short = self._select_assets(predictions)

        if self.config.rank_power == Decimal("0"):
            return self._equal_weighted_positions(top_long, top_short, account_value)
        else:
            return self._rank_weighted_positions(top_long, top_short, account_value)

    def _select_assets(self, predictions: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Select top long and bottom short assets from predictions.

        Uses the latest date in the predictions DataFrame and selects:
        - Top N assets by prediction value for long positions
        - Bottom N assets by prediction value for short positions

        If there are fewer assets than num_long + num_short, we split them
        proportionally (favoring longs if uneven).

        Args:
            predictions: DataFrame with 'date', 'asset_id', 'prediction' columns

        Returns:
            Tuple of (top_long_df, top_short_df) DataFrames

        Example:
            >>> df = pl.DataFrame({
            ...     "date": [date(2024, 1, 10)] * 5,
            ...     "asset_id": ["A", "B", "C", "D", "E"],
            ...     "prediction": [0.9, 0.5, 0.0, -0.5, -0.9]
            ... })
            >>> manager = PortfolioManager(PortfolioConfig(num_long=2, num_short=2))
            >>> top_long, top_short = manager._select_assets(df)
            >>> assert len(top_long) == 2
            >>> assert len(top_short) == 2
        """
        # Handle empty DataFrame
        if len(predictions) == 0:
            empty_df = pl.DataFrame(
                {"date": [], "asset_id": [], "prediction": []},
                schema={
                    "date": pl.Date,
                    "asset_id": pl.Utf8,
                    "prediction": pl.Float64,
                },
            )
            return empty_df, empty_df

        # Get latest date
        latest_date = predictions["date"].max()
        latest = predictions.filter(pl.col("date") == latest_date)

        # Sort by prediction descending
        sorted_preds = latest.sort("prediction", descending=True)

        # Check if we have enough assets
        total_available = len(sorted_preds)
        total_requested = self.config.num_long + self.config.num_short

        if total_available <= total_requested:
            # Not enough assets - split proportionally
            # Favor longs if uneven split
            long_ratio = self.config.num_long / total_requested if total_requested > 0 else 0.5
            num_longs = int(total_available * long_ratio)

            top_long = sorted_preds.head(num_longs)
            top_short = sorted_preds.tail(total_available - num_longs).reverse()
        else:
            # Enough assets - select as requested
            top_long = sorted_preds.head(self.config.num_long)
            # For shorts, take from the end and reverse to get ascending order (worst first)
            top_short = sorted_preds.tail(self.config.num_short).reverse()

        return top_long, top_short

    def _equal_weighted_positions(
        self, top_long: pl.DataFrame, top_short: pl.DataFrame, account_value: Decimal
    ) -> list[TargetPosition]:
        """Create equal-weighted positions.

        Each position receives an equal share of the target leverage.
        For example, with 10 long + 10 short positions and 1.0x leverage,
        each position gets 1.0 / 20 = 0.05 (5%) weight.

        Args:
            top_long: DataFrame of long position candidates
            top_short: DataFrame of short position candidates
            account_value: Account value for position sizing

        Returns:
            List of TargetPosition instances sorted by coin

        Example:
            >>> top_long = pl.DataFrame({"asset_id": ["A", "B"], "prediction": [0.9, 0.8]})
            >>> top_short = pl.DataFrame({"asset_id": ["C"], "prediction": [-0.9]})
            >>> config = PortfolioConfig(target_leverage=Decimal("1.5"))
            >>> manager = PortfolioManager(config=config)
            >>> positions = manager._equal_weighted_positions(
            ...     top_long, top_short, Decimal("10000")
            ... )
            >>> assert len(positions) == 3
            >>> assert all(p.weight == Decimal("0.5") for p in positions)
        """
        positions = []
        total_positions = len(top_long) + len(top_short)

        if total_positions == 0:
            return []

        weight_per_position = self.config.target_leverage / Decimal(str(total_positions))
        value_per_position = account_value * weight_per_position

        # Long positions
        for row in top_long.iter_rows(named=True):
            positions.append(
                TargetPosition(
                    coin=row["asset_id"],
                    target_value=value_per_position,
                    weight=weight_per_position,
                )
            )

        # Short positions (negative value)
        for row in top_short.iter_rows(named=True):
            positions.append(
                TargetPosition(
                    coin=row["asset_id"],
                    target_value=-value_per_position,
                    weight=weight_per_position,
                )
            )

        return sorted(positions, key=lambda p: p.coin)

    def _rank_weighted_positions(
        self, top_long: pl.DataFrame, top_short: pl.DataFrame, account_value: Decimal
    ) -> list[TargetPosition]:
        """Create rank-power weighted positions.

        Weights are calculated as 1 / rank^power where rank is 1, 2, 3, etc.
        Higher-ranked (better predictions) assets get higher weights.

        Args:
            top_long: DataFrame of long position candidates
            top_short: DataFrame of short position candidates
            account_value: Account value for position sizing

        Returns:
            List of TargetPosition instances sorted by coin

        Example:
            >>> top_long = pl.DataFrame({"asset_id": ["A", "B"], "prediction": [0.9, 0.8]})
            >>> top_short = pl.DataFrame({"asset_id": ["C"], "prediction": [-0.9]})
            >>> config = PortfolioConfig(rank_power=Decimal("1.0"), target_leverage=Decimal("1.0"))
            >>> manager = PortfolioManager(config=config)
            >>> positions = manager._rank_weighted_positions(
            ...     top_long, top_short, Decimal("10000")
            ... )
            >>> # First asset should have higher weight than second
            >>> assert positions[0].weight > positions[1].weight
        """
        positions = []

        # Calculate weights for each side
        long_weights = self._calculate_side_weights(len(top_long))
        short_weights = self._calculate_side_weights(len(top_short))

        # Calculate total weight
        total_weight = sum(long_weights) + sum(short_weights)
        if total_weight == 0:
            return []

        # Scale factor to achieve target leverage
        scale_factor = self.config.target_leverage / Decimal(str(total_weight))

        # Create long positions
        for i, row in enumerate(top_long.iter_rows(named=True)):
            weight = Decimal(str(long_weights[i])) * scale_factor
            positions.append(
                TargetPosition(
                    coin=row["asset_id"],
                    target_value=account_value * weight,
                    weight=weight,
                )
            )

        # Create short positions (negative value)
        for i, row in enumerate(top_short.iter_rows(named=True)):
            weight = Decimal(str(short_weights[i])) * scale_factor
            positions.append(
                TargetPosition(
                    coin=row["asset_id"],
                    target_value=-account_value * weight,
                    weight=weight,
                )
            )

        return sorted(positions, key=lambda p: p.coin)

    def _calculate_side_weights(self, n: int) -> list[float]:
        """Calculate rank-power weights for one side of the portfolio.

        Weights are calculated as: w_i = (i+1)^(-rank_power)
        where i is the index (0-based) and rank_power comes from config.

        Args:
            n: Number of positions to weight

        Returns:
            List of weight values (not yet normalized)

        Example:
            >>> config = PortfolioConfig(rank_power=Decimal("1.0"))
            >>> manager = PortfolioManager(config=config)
            >>> weights = manager._calculate_side_weights(3)
            >>> # Should be approximately [1.0, 0.5, 0.333]
            >>> assert weights[0] > weights[1] > weights[2]
        """
        if n == 0:
            return []

        rank_power = float(self.config.rank_power)
        weights = [(i + 1) ** (-rank_power) for i in range(n)]
        return weights
