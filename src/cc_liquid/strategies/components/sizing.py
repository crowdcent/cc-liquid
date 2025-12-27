"""Position sizing components."""

from typing import Protocol


class PositionSizer(Protocol):
    """Interface for position sizing strategies.

    Position sizers determine HOW MUCH capital to allocate to each position.
    They take a list of assets and return relative weights.
    """

    def calculate_weights(
        self,
        long_assets: list[str],
        short_assets: list[str],
        predictions: dict[str, float],
        target_leverage: float,
    ) -> dict[str, float]:
        """Calculate position weights.

        Args:
            long_assets: Assets to go long
            short_assets: Assets to go short
            predictions: Map of asset to prediction value
            target_leverage: Total gross leverage target

        Returns:
            Dict mapping asset to signed leverage weight
            (sum of abs values = target_leverage)
        """
        ...


class EqualWeightSizer:
    """Allocate equal capital to all positions.

    Simplest sizing strategy - each position gets same notional.
    This is equivalent to rank_power=0.0 in the current system.
    """

    def calculate_weights(
        self,
        long_assets: list[str],
        short_assets: list[str],
        predictions: dict[str, float],
        target_leverage: float,
    ) -> dict[str, float]:
        """Equal weight across all positions."""
        total_positions = len(long_assets) + len(short_assets)
        if total_positions == 0:
            return {}

        weight_per_position = target_leverage / total_positions

        weights = {}
        for asset in long_assets:
            weights[asset] = weight_per_position
        for asset in short_assets:
            weights[asset] = -weight_per_position

        return weights


class RankPowerSizer:
    """Allocate capital using rank power weighting.

    This is the current system's weighting scheme.
    Higher rank_power = more concentration in top positions.
    """

    def __init__(self, rank_power: float = 0.0):
        """
        Args:
            rank_power: Concentration parameter
                        0.0 = equal weight
                        1.0-2.0 = moderate concentration
                        3.0+ = heavy concentration
        """
        self.rank_power = rank_power

    def calculate_weights(
        self,
        long_assets: list[str],
        short_assets: list[str],
        predictions: dict[str, float],
        target_leverage: float,
    ) -> dict[str, float]:
        """Weight by rank with power scaling."""
        n_long = len(long_assets)
        n_short = len(short_assets)
        total_positions = n_long + n_short

        if total_positions == 0:
            return {}

        # Split leverage between longs and shorts proportionally
        gross_long = target_leverage * (n_long / total_positions)
        gross_short = target_leverage * (n_short / total_positions)

        def _weight_side(assets: list[str], gross: float, sign: float) -> dict[str, float]:
            n = len(assets)
            if n == 0:
                return {}

            # Rank by prediction strength
            scored = sorted(
                [(predictions.get(a, 0), a) for a in assets],
                key=lambda x: x[0],
                reverse=(sign > 0),  # Descending for longs, ascending for shorts
            )

            # Calculate rank power weights
            power = max(1e-6, self.rank_power)
            raw_weights = [((n - i) / n) ** power for i in range(n)]

            # Normalize to target gross
            total_weight = sum(raw_weights)
            scale = gross / total_weight if total_weight > 0 else 0

            return {asset: sign * raw_weights[i] * scale for i, (_, asset) in enumerate(scored)}

        weights_long = _weight_side(long_assets, gross_long, +1.0)
        weights_short = _weight_side(short_assets, gross_short, -1.0)

        return {**weights_long, **weights_short}


class VolatilityAdjustedSizer:
    """Allocate capital inversely proportional to volatility.

    Lower volatility assets get larger positions (risk parity concept).
    """

    def __init__(self, target_risk: float = 0.02):
        """
        Args:
            target_risk: Target volatility contribution per position
        """
        self.target_risk = target_risk

    def calculate_weights(
        self,
        long_assets: list[str],
        short_assets: list[str],
        predictions: dict[str, float],
        target_leverage: float,
    ) -> dict[str, float]:
        """Weight inversely to volatility (higher vol = smaller position)."""
        # Placeholder - would need historical volatility data
        # For demonstration purposes, use equal weight
        # In practice, you'd:
        # 1. Calculate historical volatility for each asset
        # 2. Inverse weight: weight[i] = 1/vol[i]
        # 3. Normalize to target_leverage

        # For now, delegate to equal weight
        equal_sizer = EqualWeightSizer()
        return equal_sizer.calculate_weights(
            long_assets, short_assets, predictions, target_leverage
        )


class KellyFractionSizer:
    """Allocate capital using Kelly Criterion.

    Optimal sizing based on expected return and variance.
    More aggressive than equal weight but mathematically optimal.
    """

    def __init__(self, kelly_fraction: float = 0.5):
        """
        Args:
            kelly_fraction: Fraction of full Kelly to use (0.5 = half Kelly)
                           Reduces risk of over-leverage
        """
        self.kelly_fraction = kelly_fraction

    def calculate_weights(
        self,
        long_assets: list[str],
        short_assets: list[str],
        predictions: dict[str, float],
        target_leverage: float,
    ) -> dict[str, float]:
        """Weight by Kelly fraction (requires expected return estimates)."""
        # Placeholder - Kelly requires:
        # - Expected return per asset (from predictions or historical data)
        # - Variance/covariance estimates
        # - Win rate or probability of profit
        #
        # Kelly formula: f = (p*b - q) / b
        # where p = probability of win, b = win/loss ratio, q = 1-p

        # For demonstration, use equal weight
        # Full implementation would estimate returns from predictions
        equal_sizer = EqualWeightSizer()
        return equal_sizer.calculate_weights(
            long_assets, short_assets, predictions, target_leverage
        )
