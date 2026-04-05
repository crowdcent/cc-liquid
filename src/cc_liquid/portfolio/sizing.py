from __future__ import annotations

import math
from typing import Dict, Iterable, Mapping, Sequence

import polars as pl


def weights_from_ranks(
    latest_preds: pl.DataFrame | Sequence[tuple[str, float]] | Mapping[str, float],
    *,
    id_col: str = "id",
    pred_col: str = "pred",
    long_assets: Sequence[str],
    short_assets: Sequence[str],
    target_gross: float,
    power: float = 0.0,
) -> Dict[str, float]:
    """Convert ranks (higher = stronger long) to signed weights using rank power weighting.

    The output weights sum in absolute value to ``target_gross``.

    Weighting uses (rank/n)^power formula where power=0.0 produces equal weights.

    ``latest_preds`` accepts either:
    - Polars DataFrame with ``id_col``/``pred_col``
    - Iterable mapping asset id to score
    - Dict[str, float]
    """

    # Normalize predictions into a simple dict for quick lookups.
    if isinstance(latest_preds, pl.DataFrame):
        preds_dict = dict(zip(latest_preds[id_col], latest_preds[pred_col]))
    elif isinstance(latest_preds, Mapping):
        preds_dict = dict(latest_preds)
    else:
        preds_dict = {asset: score for asset, score in latest_preds}

    n_long, n_short = len(long_assets), len(short_assets)
    total_positions = n_long + n_short
    if total_positions == 0 or target_gross <= 0:
        return {}

    gross_long = target_gross * (n_long / total_positions)
    gross_short = target_gross * (n_short / total_positions)

    def _side(ids: Iterable[str], gross: float, sign: float) -> Dict[str, float]:
        ids_list = [i for i in ids if i in preds_dict]
        n = len(ids_list)
        if n == 0 or gross <= 0:
            return {}

        # Fetch scores and rank within this side (best first).
        scored = sorted(
            ((preds_dict[i], i) for i in ids_list),
            key=lambda x: x[0],
            reverse=sign > 0,
        )

        # Use rank power weighting: when power=0, all weights equal 1.0
        p = max(1e-6, float(power))
        raw: list[float] = [((n - idx) / n) ** p for idx in range(n)]

        denom = sum(raw) or 1.0
        scale = gross / denom

        return {asset: sign * raw[idx] * scale for idx, (_, asset) in enumerate(scored)}

    weights_long = _side(long_assets, gross_long, +1.0)
    weights_short = _side(short_assets, gross_short, -1.0)

    return {**weights_long, **weights_short}


def weights_from_hrp(
    long_assets: Sequence[str],
    short_assets: Sequence[str],
    returns_wide: pl.DataFrame,
    target_gross: float,
    lookback_days: int = 60,
) -> Dict[str, float]:
    """Compute signed portfolio weights using Hierarchical Risk Parity (HRP).

    HRP allocates capital based on the covariance structure of recent returns
    rather than signal rank. Assets that diversify the portfolio receive more
    weight; correlated clusters receive less.

    Each side (long/short) is weighted independently using HRP, then scaled
    so the combined absolute weights sum to target_gross.

    Args:
        long_assets:    Assets to hold long, in signal rank order (best first).
        short_assets:   Assets to hold short, in signal rank order (worst first).
        returns_wide:   Wide-format returns DataFrame (dates x assets) from backtester.
        target_gross:   Target sum of absolute weights (e.g. 2.0 = 2x gross leverage).
        lookback_days:  Number of recent trading days to use for covariance estimation.

    Returns:
        Dict mapping asset id to signed weight. Positive = long, negative = short.
        Returns empty dict if insufficient data or no valid assets.
    """
    all_assets = list(long_assets) + list(short_assets)
    if not all_assets or target_gross <= 0:
        return {}

    # Filter to assets present in returns data
    available_cols = set(returns_wide.columns) - {"date"}
    long_valid  = [a for a in long_assets  if a in available_cols]
    short_valid = [a for a in short_assets if a in available_cols]
    all_valid   = long_valid + short_valid

    if not all_valid:
        return {}

    # Use recent lookback window
    recent = returns_wide.tail(lookback_days).select(all_valid).drop_nulls()

    if len(recent) < 10:
        # Not enough data - fall back to equal weight
        return _equal_weight(long_valid, short_valid, target_gross)

    # Build covariance matrix as nested dict
    cov = _covariance(recent, all_valid)

    # Run HRP on each side independently
    n_long  = len(long_valid)
    n_short = len(short_valid)
    total   = n_long + n_short

    gross_long  = target_gross * (n_long  / total) if total > 0 else 0.0
    gross_short = target_gross * (n_short / total) if total > 0 else 0.0

    weights: Dict[str, float] = {}

    if long_valid:
        hrp_long = _hrp_weights(long_valid, cov)
        for asset, w in hrp_long.items():
            weights[asset] = +w * gross_long

    if short_valid:
        hrp_short = _hrp_weights(short_valid, cov)
        for asset, w in hrp_short.items():
            weights[asset] = -w * gross_short

    return weights


# ---------------------------------------------------------------------------
# HRP internals
# ---------------------------------------------------------------------------

def _covariance(returns: pl.DataFrame, assets: list[str]) -> Dict[str, Dict[str, float]]:
    """Compute sample covariance matrix as a nested dict."""
    n = len(returns)
    means = {a: sum(returns[a].to_list()) / n for a in assets}
    cov: Dict[str, Dict[str, float]] = {a: {} for a in assets}
    for i, a in enumerate(assets):
        for j, b in enumerate(assets):
            if j < i:
                cov[a][b] = cov[b][a]
            else:
                ra = returns[a].to_list()
                rb = returns[b].to_list()
                c = sum((ra[k] - means[a]) * (rb[k] - means[b]) for k in range(n)) / (n - 1)
                cov[a][b] = c
                cov[b][a] = c
    return cov


def _correlation(cov: Dict[str, Dict[str, float]], assets: list[str]) -> Dict[str, Dict[str, float]]:
    """Convert covariance matrix to correlation matrix."""
    corr: Dict[str, Dict[str, float]] = {a: {} for a in assets}
    for a in assets:
        for b in assets:
            denom = math.sqrt(cov[a][a] * cov[b][b])
            corr[a][b] = cov[a][b] / denom if denom > 0 else 0.0
    return corr


def _distance(corr: Dict[str, Dict[str, float]], assets: list[str]) -> Dict[str, Dict[str, float]]:
    """Convert correlation to distance matrix: d = sqrt(0.5 * (1 - corr))."""
    dist: Dict[str, Dict[str, float]] = {a: {} for a in assets}
    for a in assets:
        for b in assets:
            dist[a][b] = math.sqrt(max(0.0, 0.5 * (1.0 - corr[a][b])))
    return dist


def _cluster(assets: list[str], dist: Dict[str, Dict[str, float]]) -> list[str]:
    """Single-linkage hierarchical clustering. Returns quasi-diagonalized asset order."""
    if len(assets) == 1:
        return list(assets)

    # Start with each asset in its own cluster
    clusters = [[a] for a in assets]

    while len(clusters) > 1:
        # Find closest pair of clusters
        min_dist = float("inf")
        merge_i, merge_j = 0, 1

        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                # Single linkage: min distance between any two members
                d = min(
                    dist[a][b]
                    for a in clusters[i]
                    for b in clusters[j]
                )
                if d < min_dist:
                    min_dist = d
                    merge_i, merge_j = i, j

        # Merge the two closest clusters
        merged = clusters[merge_i] + clusters[merge_j]
        clusters = [c for k, c in enumerate(clusters) if k not in (merge_i, merge_j)]
        clusters.append(merged)

    return clusters[0]  # Final ordering


def _hrp_weights(assets: list[str], cov: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """Compute HRP weights for a set of assets using their covariance matrix.

    Returns weights that sum to 1.0 (unsigned). Caller applies sign and scaling.
    """
    if len(assets) == 1:
        return {assets[0]: 1.0}

    # Step 1: Build correlation and distance matrices
    corr = _correlation(cov, assets)
    dist = _distance(corr, assets)

    # Step 2: Cluster into quasi-diagonal order
    ordered = _cluster(assets, dist)

    # Step 3: Recursive bisection to assign weights
    weights = {a: 1.0 for a in ordered}
    clusters = [ordered]

    while clusters:
        new_clusters = []
        for cluster in clusters:
            if len(cluster) <= 1:
                continue

            # Split cluster in half
            mid = len(cluster) // 2
            left  = cluster[:mid]
            right = cluster[mid:]

            # Variance of each sub-cluster
            var_left  = _cluster_variance(left,  cov, weights)
            var_right = _cluster_variance(right, cov, weights)

            # Allocate inversely proportional to variance
            total_var = var_left + var_right
            if total_var > 0:
                alpha = 1.0 - var_left / total_var  # weight for left cluster
            else:
                alpha = 0.5

            for a in left:
                weights[a] *= alpha
            for a in right:
                weights[a] *= (1.0 - alpha)

            new_clusters.extend([left, right])

        clusters = new_clusters

    # Normalize to sum to 1.0
    total = sum(weights.values())
    if total > 0:
        weights = {a: w / total for a, w in weights.items()}

    return weights


def _cluster_variance(
    cluster: list[str],
    cov: Dict[str, Dict[str, float]],
    weights: Dict[str, float],
) -> float:
    """Compute the variance of a cluster using current weights."""
    # Normalize weights within this cluster
    cluster_w = {a: weights[a] for a in cluster}
    total = sum(cluster_w.values())
    if total <= 0:
        return 0.0
    norm_w = {a: w / total for a, w in cluster_w.items()}

    # Portfolio variance = w' * cov * w
    variance = 0.0
    for a in cluster:
        for b in cluster:
            variance += norm_w[a] * norm_w[b] * cov[a][b]

    return max(0.0, variance)


def _equal_weight(
    long_assets: list[str],
    short_assets: list[str],
    target_gross: float,
) -> Dict[str, float]:
    """Fallback equal weighting when HRP cannot run."""
    total = len(long_assets) + len(short_assets)
    if total == 0 or target_gross <= 0:
        return {}
    w = target_gross / total
    weights: Dict[str, float] = {}
    for a in long_assets:
        weights[a] = +w
    for a in short_assets:
        weights[a] = -w
    return weights