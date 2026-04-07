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


def weights_from_hrp_lw(
    long_assets: Sequence[str],
    short_assets: Sequence[str],
    returns_wide: pl.DataFrame,
    target_gross: float,
    lookback_days: int = 60,
    shrinkage: float | None = None,
) -> Dict[str, float]:
    """HRP with Ledoit-Wolf covariance shrinkage.

    Identical to weights_from_hrp but replaces the sample covariance matrix
    with a shrunk estimate. Shrinkage pulls the matrix toward the constant
    correlation model, improving conditioning on short samples.

    Args:
        shrinkage:  Shrinkage intensity in [0.0, 1.0]. 0.0 = sample covariance
                    (same as weights_from_hrp). 1.0 = full constant correlation
                    target. None = analytically estimated (Ledoit-Wolf oracle).
    """
    all_assets = list(long_assets) + list(short_assets)
    if not all_assets or target_gross <= 0:
        return {}

    available_cols = set(returns_wide.columns) - {"date"}
    long_valid  = [a for a in long_assets  if a in available_cols]
    short_valid = [a for a in short_assets if a in available_cols]
    all_valid   = long_valid + short_valid

    if not all_valid:
        return {}

    recent = returns_wide.tail(lookback_days).select(all_valid).drop_nulls()

    if len(recent) < 10:
        return _equal_weight(long_valid, short_valid, target_gross)

    # Use shrunk covariance instead of raw sample
    cov = _covariance_shrunk(recent, all_valid, shrinkage)

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


def _covariance_shrunk(
    returns: pl.DataFrame,
    assets: list[str],
    shrinkage: float | None = None,
) -> Dict[str, Dict[str, float]]:
    """Sample covariance matrix shrunk toward the constant correlation target.

    The constant correlation target keeps individual asset variances from the
    sample matrix but replaces all pairwise correlations with their
    cross-sectional mean. This regularizes the correlation structure while
    preserving realistic volatility estimates.

    If shrinkage is None, the optimal intensity is estimated analytically
    using the Ledoit-Wolf formula for the constant correlation target.
    """
    n = len(returns)
    cov_sample = _covariance(returns, assets)

    # Compute sample correlations and their mean
    p = len(assets)
    corr_sum = 0.0
    corr_count = 0
    for i, a in enumerate(assets):
        for j, b in enumerate(assets):
            if i < j:
                denom = math.sqrt(cov_sample[a][a] * cov_sample[b][b])
                rho = cov_sample[a][b] / denom if denom > 0 else 0.0
                corr_sum += rho
                corr_count += 1

    rho_bar = corr_sum / corr_count if corr_count > 0 else 0.0

    # Build constant correlation target matrix
    target: Dict[str, Dict[str, float]] = {a: {} for a in assets}
    for a in assets:
        for b in assets:
            if a == b:
                target[a][b] = cov_sample[a][a]
            else:
                target[a][b] = rho_bar * math.sqrt(
                    cov_sample[a][a] * cov_sample[b][b]
                )

    # Estimate shrinkage intensity analytically if not provided
    if shrinkage is None:
        shrinkage = _ledoit_wolf_intensity(returns, assets, cov_sample, target, n, p)

    shrinkage = max(0.0, min(1.0, shrinkage))

    # Blend: cov_shrunk = (1 - alpha) * cov_sample + alpha * target
    cov_shrunk: Dict[str, Dict[str, float]] = {a: {} for a in assets}
    for a in assets:
        for b in assets:
            cov_shrunk[a][b] = (
                (1.0 - shrinkage) * cov_sample[a][b]
                + shrinkage * target[a][b]
            )

    return cov_shrunk


def _ledoit_wolf_intensity(
    returns: pl.DataFrame,
    assets: list[str],
    cov_sample: Dict[str, Dict[str, float]],
    target: Dict[str, Dict[str, float]],
    n: int,
    p: int,
) -> float:
    """Analytically estimate optimal shrinkage intensity (Ledoit-Wolf oracle).

    Minimizes the expected Frobenius distance between the shrunk estimator
    and the true covariance matrix.
    """
    means = {a: sum(returns[a].to_list()) / n for a in assets}
    data = {a: returns[a].to_list() for a in assets}

    # Numerator: sum of squared sample errors scaled by n
    pi_hat = 0.0
    for a in assets:
        for b in assets:
            # Asymptotic variance of sample covariance entry
            vals = [
                (data[a][k] - means[a]) * (data[b][k] - means[b])
                - cov_sample[a][b]
                for k in range(n)
            ]
            pi_hat += sum(v ** 2 for v in vals) / n

    # Denominator: squared Frobenius norm of (sample - target)
    delta_sq = 0.0
    for a in assets:
        for b in assets:
            delta_sq += (cov_sample[a][b] - target[a][b]) ** 2

    if delta_sq == 0.0:
        return 0.0

    alpha = (pi_hat / n) / delta_sq
    return max(0.0, min(1.0, alpha))

# ===========================================================================
# Modified Hierarchical Risk Parity (MHRP)
# ---------------------------------------------------------------------------
# Based on Molyboga (2020), "A Modified Hierarchical Risk Parity Framework
# for Portfolio Management", Journal of Financial Data Science.
#
# Three enhancements over standard HRP:
#   1. Exponentially Weighted Moving Average (EWMA) covariance with
#      Ledoit-Wolf shrinkage toward the constant-correlation target.
#   2. Inverse-volatility (equal-volatility) allocation in recursive
#      bisection, replacing the original inverse-variance approach.
#   3. Optional volatility targeting: rescales weights so that the
#      portfolio's expected annualised volatility equals vol_target.
#
# Design notes
# ------------
# All helpers carry the _mhrp_ prefix so this block is fully self-contained
# and can be removed (or moved) without touching anything else in sizing.py.
# No existing function is imported, called, or modified.
#
# ewma_lambda is intentionally left as a tunable parameter with no
# hard-coded "smart" default tied to a rebalancing cadence.  The default
# of 0.97 is a conservative starting point; users should treat it like any
# other hyperparameter and sweep it through the optimizer alongside
# lookback_days.  Higher lambda = slower decay = longer effective memory.
#
# vol_target is off by default (None).  When enabled it acts as a
# multiplicative pre-scaler on the HRP weights before the target_gross
# normalisation.  target_gross remains the hard cap on gross exposure, so
# live-trading leverage limits are always respected.
# ===========================================================================


def weights_from_mhrp(
    long_assets: Sequence[str],
    short_assets: Sequence[str],
    returns_wide: pl.DataFrame,
    target_gross: float,
    lookback_days: int = 60,
    ewma_lambda: float = 0.97,
    shrinkage: float | None = None,
    vol_target: float | None = None,
    annual_factor: int = 365,
) -> Dict[str, float]:
    """Compute signed portfolio weights using Modified Hierarchical Risk Parity.

    Extends HRP with three enhancements from Molyboga (2020):
    (1) EWMA covariance with Ledoit-Wolf shrinkage replaces the flat sample
        covariance, giving more weight to recent observations while
        regularising the matrix toward the constant-correlation target.
    (2) Inverse-volatility allocation in recursive bisection produces more
        balanced diversification than the original inverse-variance split.
    (3) Optional volatility targeting rescales the portfolio so its expected
        annualised volatility equals vol_target before the target_gross cap
        is applied.

    Each side (long/short) is weighted independently using MHRP, then
    scaled so the combined absolute weights sum to target_gross.

    Args:
        long_assets:    Assets to hold long, in signal rank order (best first).
        short_assets:   Assets to hold short, in signal rank order (worst first).
        returns_wide:   Wide-format returns DataFrame (dates x assets).
        target_gross:   Target sum of absolute weights (e.g. 2.0 = 2x gross
                        leverage).  Always respected as a hard cap.
        lookback_days:  Number of recent trading days used for covariance
                        estimation.  Should be tuned alongside ewma_lambda.
        ewma_lambda:    EWMA decay factor in (0, 1).  Higher = slower decay =
                        longer effective memory.  Treat as a hyperparameter;
                        sweep via the optimizer for your rebalance cadence.
                        Default 0.97 is a conservative starting point.
        shrinkage:      Ledoit-Wolf shrinkage intensity in [0.0, 1.0].
                        0.0 = raw EWMA covariance.
                        1.0 = full constant-correlation target.
                        None = analytically estimated (oracle).
        vol_target:     Annualised volatility target, e.g. 0.15 for 15%.
                        None = disabled; weights are scaled only by
                        target_gross (identical behaviour to hrp_lw).
        annual_factor:  Trading periods per year used for annualisation.
                        365 for crypto (default); 252 for equities.

    Returns:
        Dict mapping asset id to signed weight.  Positive = long, negative =
        short.  Absolute values sum to target_gross (or less if vol_target
        constrains effective leverage below target_gross).
        Returns empty dict if insufficient data or no valid assets.
    """
    all_assets = list(long_assets) + list(short_assets)
    if not all_assets or target_gross <= 0:
        return {}

    available_cols = set(returns_wide.columns) - {"date"}
    long_valid  = [a for a in long_assets  if a in available_cols]
    short_valid = [a for a in short_assets if a in available_cols]
    all_valid   = long_valid + short_valid

    if not all_valid:
        return {}

    recent = returns_wide.tail(lookback_days).select(all_valid).drop_nulls()

    if len(recent) < 10:
        # Not enough history — fall back to equal weight
        return _mhrp_equal_weight(long_valid, short_valid, target_gross)

    # Step 1: EWMA covariance shrunk toward constant-correlation target
    cov = _mhrp_covariance_ewma_shrunk(recent, all_valid, ewma_lambda, shrinkage)

    n_long  = len(long_valid)
    n_short = len(short_valid)
    total   = n_long + n_short

    gross_long  = target_gross * (n_long  / total) if total > 0 else 0.0
    gross_short = target_gross * (n_short / total) if total > 0 else 0.0

    weights: Dict[str, float] = {}

    # Step 2: inverse-volatility HRP on each side independently
    if long_valid:
        hrp_long = _mhrp_hrp_weights_invvol(long_valid, cov)
        for asset, w in hrp_long.items():
            weights[asset] = +w * gross_long

    if short_valid:
        hrp_short = _mhrp_hrp_weights_invvol(short_valid, cov)
        for asset, w in hrp_short.items():
            weights[asset] = -w * gross_short

    # Step 3: optional volatility targeting (pre-scaler before gross cap)
    if vol_target is not None and vol_target > 0:
        scalar = _mhrp_vol_scalar(weights, cov, vol_target, annual_factor)
        weights = {a: w * scalar for a, w in weights.items()}

        # Re-normalise to target_gross after vol scaling
        gross_sum = sum(abs(w) for w in weights.values())
        if gross_sum > 0:
            scale = target_gross / gross_sum
            weights = {a: w * scale for a, w in weights.items()}

    return weights


# ---------------------------------------------------------------------------
# MHRP private helpers
# ---------------------------------------------------------------------------

def _mhrp_covariance_ewma_shrunk(
    returns: pl.DataFrame,
    assets: list[str],
    lam: float,
    shrinkage: float | None,
) -> Dict[str, Dict[str, float]]:
    """EWMA sample covariance shrunk toward the constant-correlation target.

    Combines two enhancements into one step:
    - EWMA weighting: recent observations carry more weight, controlled by lam.
    - Ledoit-Wolf shrinkage: pulls the matrix toward the constant-correlation
      target to improve conditioning on short lookback windows.

    Args:
        returns:    Wide DataFrame of asset returns (rows = observations).
        assets:     Ordered list of asset column names.
        lam:        EWMA decay factor in (0, 1).
        shrinkage:  Shrinkage intensity or None for analytic estimation.

    Returns:
        Nested dict covariance matrix, same shape as _covariance output.
    """
    n = len(returns)
    p = len(assets)

    # --- Build exponentially decaying observation weights ---
    # Index 0 = most recent (tail of DataFrame).  Weight decays as lam^k.
    raw_w = [lam ** k for k in range(n)]
    total_w = sum(raw_w)
    w = [rw / total_w for rw in raw_w]  # normalised, sum to 1.0

    # Retrieve column data as lists once to avoid repeated Polars overhead
    data: Dict[str, list[float]] = {a: returns[a].to_list() for a in assets}

    # Weighted means (most-recent observation is index 0 in the weight list,
    # but the DataFrame is ordered oldest-first, so row i maps to weight
    # w[n-1-i] — i.e. the last row gets w[0] = highest weight)
    means: Dict[str, float] = {}
    for a in assets:
        col = data[a]
        means[a] = sum(w[n - 1 - i] * col[i] for i in range(n))

    # Weighted (biased) covariance — using effective sample size correction
    # is unnecessary here; shrinkage regularises the matrix.
    cov_ewma: Dict[str, Dict[str, float]] = {a: {} for a in assets}
    for i, a in enumerate(assets):
        for j, b in enumerate(assets):
            if j < i:
                cov_ewma[a][b] = cov_ewma[b][a]
            else:
                ra, rb = data[a], data[b]
                c = sum(
                    w[n - 1 - k] * (ra[k] - means[a]) * (rb[k] - means[b])
                    for k in range(n)
                )
                cov_ewma[a][b] = c
                cov_ewma[b][a] = c

    # --- Ledoit-Wolf shrinkage toward constant-correlation target ---
    # Compute sample correlations and their cross-sectional mean
    corr_sum   = 0.0
    corr_count = 0
    for i, a in enumerate(assets):
        for j, b in enumerate(assets):
            if i < j:
                denom = math.sqrt(cov_ewma[a][a] * cov_ewma[b][b])
                rho = cov_ewma[a][b] / denom if denom > 0 else 0.0
                corr_sum   += rho
                corr_count += 1

    rho_bar = corr_sum / corr_count if corr_count > 0 else 0.0

    # Constant-correlation target: preserves EWMA variances on diagonal,
    # replaces all off-diagonal correlations with the mean rho_bar
    target: Dict[str, Dict[str, float]] = {a: {} for a in assets}
    for a in assets:
        for b in assets:
            if a == b:
                target[a][b] = cov_ewma[a][a]
            else:
                target[a][b] = rho_bar * math.sqrt(
                    cov_ewma[a][a] * cov_ewma[b][b]
                )

    # Analytically estimate shrinkage intensity if not provided
    if shrinkage is None:
        shrinkage = _mhrp_ledoit_wolf_intensity(
            data, assets, means, w, n, cov_ewma, target
        )

    shrinkage = max(0.0, min(1.0, shrinkage))

    # Blend: cov_shrunk = (1 - alpha) * cov_ewma + alpha * target
    cov_shrunk: Dict[str, Dict[str, float]] = {a: {} for a in assets}
    for a in assets:
        for b in assets:
            cov_shrunk[a][b] = (
                (1.0 - shrinkage) * cov_ewma[a][b]
                + shrinkage * target[a][b]
            )

    return cov_shrunk


def _mhrp_ledoit_wolf_intensity(
    data: Dict[str, list[float]],
    assets: list[str],
    means: Dict[str, float],
    w: list[float],
    n: int,
    cov_sample: Dict[str, Dict[str, float]],
    target: Dict[str, Dict[str, float]],
) -> float:
    """Analytically estimate optimal Ledoit-Wolf shrinkage intensity.

    Adapted from the oracle formula: minimises expected Frobenius distance
    between the shrunk estimator and the true covariance matrix.  Uses the
    EWMA-weighted residuals to be consistent with the EWMA sample covariance.

    Args:
        data:       Pre-extracted column lists keyed by asset name.
        assets:     Ordered list of asset names.
        means:      EWMA-weighted means keyed by asset name.
        w:          Normalised EWMA weights, index 0 = most recent.
        n:          Number of observations.
        cov_sample: EWMA sample covariance (the matrix being shrunk).
        target:     Constant-correlation shrinkage target.

    Returns:
        Shrinkage intensity in [0.0, 1.0].
    """
    # Numerator: weighted sum of squared deviations of outer products from
    # the sample covariance (asymptotic variance of the estimator)
    pi_hat = 0.0
    for a in assets:
        for b in assets:
            vals = [
                w[n - 1 - k] * (data[a][k] - means[a]) * (data[b][k] - means[b])
                - cov_sample[a][b]
                for k in range(n)
            ]
            pi_hat += sum(v ** 2 for v in vals)

    # Denominator: squared Frobenius norm of (sample - target)
    delta_sq = 0.0
    for a in assets:
        for b in assets:
            delta_sq += (cov_sample[a][b] - target[a][b]) ** 2

    if delta_sq == 0.0:
        return 0.0

    alpha = pi_hat / delta_sq
    return max(0.0, min(1.0, alpha))


def _mhrp_hrp_weights_invvol(
    assets: list[str],
    cov: Dict[str, Dict[str, float]],
) -> Dict[str, float]:
    """Compute MHRP weights using inverse-volatility bisection allocation.

    Identical pipeline to standard HRP (correlation → distance → single-
    linkage clustering → recursive bisection) except that the bisection
    split uses cluster volatility (sqrt of variance) rather than variance.
    This produces more balanced diversification per Molyboga (2020).

    Returns weights that sum to 1.0 (unsigned). Caller applies sign and
    scaling.
    """
    if len(assets) == 1:
        return {assets[0]: 1.0}

    # Step 1: correlation and distance matrices
    corr: Dict[str, Dict[str, float]] = {a: {} for a in assets}
    for a in assets:
        for b in assets:
            denom = math.sqrt(cov[a][a] * cov[b][b])
            corr[a][b] = cov[a][b] / denom if denom > 0 else 0.0

    dist: Dict[str, Dict[str, float]] = {a: {} for a in assets}
    for a in assets:
        for b in assets:
            dist[a][b] = math.sqrt(max(0.0, 0.5 * (1.0 - corr[a][b])))

    # Step 2: single-linkage hierarchical clustering → quasi-diagonal order
    clusters_cl = [[a] for a in assets]
    while len(clusters_cl) > 1:
        min_dist = float("inf")
        merge_i, merge_j = 0, 1
        for i in range(len(clusters_cl)):
            for j in range(i + 1, len(clusters_cl)):
                d = min(
                    dist[a][b]
                    for a in clusters_cl[i]
                    for b in clusters_cl[j]
                )
                if d < min_dist:
                    min_dist = d
                    merge_i, merge_j = i, j
        merged = clusters_cl[merge_i] + clusters_cl[merge_j]
        clusters_cl = [
            c for k, c in enumerate(clusters_cl)
            if k not in (merge_i, merge_j)
        ]
        clusters_cl.append(merged)

    ordered: list[str] = clusters_cl[0]

    # Step 3: recursive bisection with inverse-volatility split
    weights = {a: 1.0 for a in ordered}
    clusters_rb = [ordered]

    while clusters_rb:
        new_clusters: list[list[str]] = []
        for cluster in clusters_rb:
            if len(cluster) <= 1:
                continue

            mid   = len(cluster) // 2
            left  = cluster[:mid]
            right = cluster[mid:]

            var_left  = _mhrp_cluster_variance(left,  cov, weights)
            var_right = _mhrp_cluster_variance(right, cov, weights)

            # --- KEY DIFFERENCE vs standard HRP ---
            # Use volatility (sqrt of variance) not variance itself.
            # This gives equal-volatility allocation rather than
            # equal-variance, producing more balanced diversification.
            vol_left  = math.sqrt(max(0.0, var_left))
            vol_right = math.sqrt(max(0.0, var_right))
            total_vol = vol_left + vol_right

            if total_vol > 0:
                alpha = 1.0 - vol_left / total_vol  # weight for left cluster
            else:
                alpha = 0.5

            for a in left:
                weights[a] *= alpha
            for a in right:
                weights[a] *= (1.0 - alpha)

            new_clusters.extend([left, right])

        clusters_rb = new_clusters

    # Normalise to sum to 1.0
    total = sum(weights.values())
    if total > 0:
        weights = {a: w / total for a, w in weights.items()}

    return weights


def _mhrp_cluster_variance(
    cluster: list[str],
    cov: Dict[str, Dict[str, float]],
    weights: Dict[str, float],
) -> float:
    """Compute the variance of a cluster given current weights.

    Weights within the cluster are normalised before computing portfolio
    variance so that only relative allocations matter.
    """
    cluster_w = {a: weights[a] for a in cluster}
    total = sum(cluster_w.values())
    if total <= 0:
        return 0.0
    norm_w = {a: w / total for a, w in cluster_w.items()}

    variance = 0.0
    for a in cluster:
        for b in cluster:
            variance += norm_w[a] * norm_w[b] * cov[a][b]

    return max(0.0, variance)


def _mhrp_vol_scalar(
    weights: Dict[str, float],
    cov: Dict[str, Dict[str, float]],
    vol_target: float,
    annual_factor: int,
) -> float:
    """Compute the scalar that brings portfolio volatility to vol_target.

    Computes realised portfolio variance using the current weights and the
    EWMA+LW covariance, annualises it, then returns vol_target / port_vol.

    The scalar is clamped to [0.1, 10.0] to prevent extreme leverage
    adjustments when the covariance estimate is noisy — e.g. at the start
    of a backtest with a short history.

    Args:
        weights:       Signed weight dict (positive = long, negative = short).
        cov:           EWMA+LW covariance matrix (nested dict).
        vol_target:    Target annualised volatility, e.g. 0.15.
        annual_factor: Trading periods per year (365 crypto, 252 equities).

    Returns:
        Multiplicative scalar to apply to all weights.
    """
    assets = list(weights.keys())

    # Portfolio variance: w' * Sigma * w
    port_var = 0.0
    for a in assets:
        for b in assets:
            if a in cov and b in cov.get(a, {}):
                port_var += weights[a] * weights[b] * cov[a][b]

    port_var = max(0.0, port_var)

    if port_var == 0.0:
        return 1.0

    port_vol_ann = math.sqrt(port_var * annual_factor)

    if port_vol_ann == 0.0:
        return 1.0

    scalar = vol_target / port_vol_ann

    # Clamp: avoid extreme leverage adjustments on noisy short-history windows
    return max(0.1, min(10.0, scalar))


def _mhrp_equal_weight(
    long_assets: list[str],
    short_assets: list[str],
    target_gross: float,
) -> Dict[str, float]:
    """Fallback equal-weight allocation when MHRP cannot run.

    Triggered when the lookback window contains fewer than 10 clean
    observations — identical fallback logic to the other HRP variants.
    """
    total = len(long_assets) + len(short_assets)
    if total == 0 or target_gross <= 0:
        return {}
    w = target_gross / total
    result: Dict[str, float] = {}
    for a in long_assets:
        result[a] = +w
    for a in short_assets:
        result[a] = -w
    return result


# ===========================================================================
# Inverse Volatility Portfolio (IVP)
# ---------------------------------------------------------------------------
# The simplest possible risk-based allocator. Each asset receives a weight
# proportional to the inverse of its rolling volatility (standard deviation
# of returns). No clustering, no matrix inversion, no correlation structure.
#
#   w_i = (1 / σ_i) / Σ_j (1 / σ_j)
#
# This is the purest expression of the vol-parity idea: every asset
# contributes equal volatility to the portfolio, assuming zero correlation
# between assets. That assumption is obviously wrong in practice, but the
# resulting robustness to estimation error often compensates — particularly
# on short histories where correlation estimates are noisy.
#
# Design notes
# ------------
# All helpers carry the _ivp_ prefix so this block is fully self-contained
# and can be removed without touching anything else in sizing.py.
#
# Volatility is estimated as the flat rolling standard deviation over
# lookback_days, consistent with the covariance estimator used in hrp and
# hrp_lw. This keeps IVP as a clean isolated test of the vol-parity
# mechanism without introducing EWMA recency bias. An EWMA variant can be
# layered on later if needed.
#
# Each side (long/short) is weighted independently then scaled so the
# combined absolute weights sum to target_gross — identical convention to
# all other optimizers in this file.
# ===========================================================================


def weights_from_ivp(
    long_assets: Sequence[str],
    short_assets: Sequence[str],
    returns_wide: pl.DataFrame,
    target_gross: float,
    lookback_days: int = 60,
) -> Dict[str, float]:
    """Compute signed portfolio weights using Inverse Volatility weighting.

    Each asset is weighted in proportion to the inverse of its rolling
    volatility (standard deviation of returns over lookback_days). Assets
    with lower volatility receive higher weights, with the constraint that
    absolute weights sum to target_gross.

    Correlations between assets are ignored entirely — this is the key
    difference from HRP and MHRP. The approach is optimal when assets
    have similar Sharpe ratios and similar pairwise correlations. Its
    main advantage is robustness: with only N volatility estimates to
    compute (vs N² covariance entries), estimation error is minimised.

    Each side (long/short) is weighted independently using IVP, then
    scaled so the combined absolute weights sum to target_gross.

    Args:
        long_assets:    Assets to hold long, in signal rank order (best first).
        short_assets:   Assets to hold short, in signal rank order (worst first).
        returns_wide:   Wide-format returns DataFrame (dates x assets).
        target_gross:   Target sum of absolute weights (e.g. 2.0 = 2x gross
                        leverage).  Always respected as a hard cap.
        lookback_days:  Number of recent trading days used for volatility
                        estimation.  Same parameter shared with HRP variants
                        via hrp_lookback_days in config.

    Returns:
        Dict mapping asset id to signed weight.  Positive = long, negative =
        short.  Absolute values sum to target_gross.
        Returns empty dict if insufficient data or no valid assets.
    """
    all_assets = list(long_assets) + list(short_assets)
    if not all_assets or target_gross <= 0:
        return {}

    available_cols = set(returns_wide.columns) - {"date"}
    long_valid  = [a for a in long_assets  if a in available_cols]
    short_valid = [a for a in short_assets if a in available_cols]
    all_valid   = long_valid + short_valid

    if not all_valid:
        return {}

    recent = returns_wide.tail(lookback_days).select(all_valid).drop_nulls()

    if len(recent) < 10:
        # Not enough history — fall back to equal weight
        return _ivp_equal_weight(long_valid, short_valid, target_gross)

    # Compute per-asset volatilities over the lookback window
    vols = _ivp_volatilities(recent, all_valid)

    # Check all vols are usable
    if not vols or all(v <= 0 for v in vols.values()):
        return _ivp_equal_weight(long_valid, short_valid, target_gross)

    n_long  = len(long_valid)
    n_short = len(short_valid)
    total   = n_long + n_short

    gross_long  = target_gross * (n_long  / total) if total > 0 else 0.0
    gross_short = target_gross * (n_short / total) if total > 0 else 0.0

    weights: Dict[str, float] = {}

    if long_valid:
        ivp_long = _ivp_weights(long_valid, vols)
        for asset, w in ivp_long.items():
            weights[asset] = +w * gross_long

    if short_valid:
        ivp_short = _ivp_weights(short_valid, vols)
        for asset, w in ivp_short.items():
            weights[asset] = -w * gross_short

    return weights


# ---------------------------------------------------------------------------
# IVP private helpers
# ---------------------------------------------------------------------------

def _ivp_volatilities(
    returns: pl.DataFrame,
    assets: list[str],
) -> Dict[str, float]:
    """Compute rolling standard deviation for each asset.

    Uses the sample standard deviation (ddof=1) over the full window,
    consistent with the covariance estimator in _covariance.

    Args:
        returns:  Wide DataFrame of asset returns (rows = observations).
        assets:   Ordered list of asset column names.

    Returns:
        Dict mapping asset name to annualisation-free volatility estimate.
        Assets with zero or negative variance are assigned vol=0.0 and
        handled gracefully in the caller.
    """
    n = len(returns)
    if n < 2:
        return {a: 0.0 for a in assets}

    vols: Dict[str, float] = {}
    for a in assets:
        col = returns[a].to_list()
        mean = sum(col) / n
        variance = sum((x - mean) ** 2 for x in col) / (n - 1)
        vols[a] = math.sqrt(max(0.0, variance))

    return vols


def _ivp_weights(
    assets: list[str],
    vols: Dict[str, float],
) -> Dict[str, float]:
    """Compute inverse-volatility weights that sum to 1.0 for a set of assets.

    Assets with zero volatility are excluded from the inverse-vol calculation
    and receive zero weight.  If all assets have zero volatility the fallback
    is equal weighting.

    Args:
        assets:  Ordered list of asset names for this side (long or short).
        vols:    Per-asset volatility estimates from _ivp_volatilities.

    Returns:
        Dict of unsigned weights summing to 1.0.  Caller applies sign and
        gross scaling.
    """
    # Inverse volatility — zero-vol assets get zero weight
    inv_vols = {a: (1.0 / vols[a]) if vols.get(a, 0.0) > 0 else 0.0
                for a in assets}

    total_inv = sum(inv_vols.values())

    if total_inv <= 0:
        # All assets have zero vol — fall back to equal weight
        n = len(assets)
        return {a: 1.0 / n for a in assets} if n > 0 else {}

    return {a: inv_vols[a] / total_inv for a in assets}


def _ivp_equal_weight(
    long_assets: list[str],
    short_assets: list[str],
    target_gross: float,
) -> Dict[str, float]:
    """Fallback equal-weight allocation when IVP cannot run.

    Triggered when the lookback window contains fewer than 10 clean
    observations — identical fallback logic to all other variants.
    """
    total = len(long_assets) + len(short_assets)
    if total == 0 or target_gross <= 0:
        return {}
    w = target_gross / total
    result: Dict[str, float] = {}
    for a in long_assets:
        result[a] = +w
    for a in short_assets:
        result[a] = -w
    return result