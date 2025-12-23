"""Backtesting engine for cc-liquid.

This module provides pure backtesting logic without any UI dependencies.
All display/visualization is handled by the CLI layer.

⚠️ IMPORTANT DISCLAIMER:
Backtesting has inherent limitations. Past performance does not predict future results.
Results are hypothetical and do not account for all real-world factors including:
- Market impact and slippage beyond modeled estimates
- Changing market conditions and liquidity
- Technical failures and execution delays
- Regulatory changes and exchange rules
Always validate strategies with out-of-sample data and paper trading before live deployment.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal

import polars as pl

from .portfolio import weights_from_ranks


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""

    # Data paths
    prices_path: str = "raw_data.parquet"
    predictions_path: str = "predictions.parquet"

    # Price data columns (defaults match raw_data.parquet)
    price_date_column: str = "date"
    price_id_column: str = "id"
    price_close_column: str = "close"

    # Prediction columns (will be taken from DataSourceConfig in CLI)
    pred_date_column: str = "release_date"
    pred_id_column: str = "id"
    pred_value_column: str = "pred_30d"

    # Data provider (e.g., crowdcent, numerai, local)
    data_provider: str | None = None

    # Date range (None = use all available overlapping data)
    start_date: datetime | None = None
    end_date: datetime | None = None

    # Strategy parameters (match PortfolioConfig)
    num_long: int = 60
    num_short: int = 50
    target_leverage: float = 3.0  # Sum of abs(weights), matching trader.py
    # Weighting: power=0.0 is equal weight, higher = more concentration
    rank_power: float = 0.0

    # Rebalancing
    rebalance_every_n_days: int = 10
    prediction_lag_days: int = 1  # Use T-lag signals to trade at T
    mode: str = "full"  # "full" or "rolling"
    rolling_days: int = 30  # Vintage lifespan for rolling mode
    seed_full: bool = False  # If true, seed vintages on first day (rolling mode)

    # Costs (in basis points)
    fee_bps: float = 4.0  # Trading fee
    slippage_bps: float = 50.0  # Slippage cost

    # Initial capital
    start_capital: float = 100_000.0

    # Options
    verbose: bool = False


@dataclass
class BacktestResult:
    """Results from a backtest run."""

    # Daily time series
    daily: pl.DataFrame  # columns: date, returns, equity, drawdown, turnover

    # Position snapshots at rebalance dates
    rebalance_positions: pl.DataFrame  # columns: date, id, weight

    # Summary statistics
    stats: dict[str, float] = field(default_factory=dict)

    # Config used
    config: BacktestConfig | None = None


class Backtester:
    """Core backtesting engine."""

    def __init__(self, config: BacktestConfig):
        self.config = config

    def run(self) -> BacktestResult:
        """Run the backtest and return results."""

        # 1. Load and prepare data
        prices_long = self._load_prices()
        predictions_long = self._load_predictions()

        # 2. Compute returns matrix (use ALL available prices first)
        returns_wide_all = self._compute_returns_wide(prices_long)

        # 3. Determine valid trading dates from returns + lagged predictions
        valid_dates = self._get_valid_trading_dates_from_returns(
            returns_wide_all, predictions_long
        )
        if len(valid_dates) == 0:
            raise ValueError(
                "No valid trading dates given returns and prediction coverage"
            )

        # 4. Filter returns to valid dates only (predictions are filtered by cutoff at selection time)
        returns_wide = returns_wide_all.filter(pl.col("date").is_in(valid_dates))

        # Scope predictions to up-to-last cutoff for efficiency (do NOT drop early dates needed for lag)
        last_cutoff = max(valid_dates) - timedelta(days=self.config.prediction_lag_days)
        predictions_long = predictions_long.filter(pl.col("pred_date") <= last_cutoff)

        # 5. Determine rebalance schedule (for full mode)
        rebalance_dates = self._compute_rebalance_dates(valid_dates)

        # 6. Run simulation (dispatch based on mode)
        if self.config.mode == "rolling":
            result = self._simulate_rolling(
                returns_wide=returns_wide,
                predictions_long=predictions_long,
            )
        else:
            result = self._simulate(
                returns_wide=returns_wide,
                predictions_long=predictions_long,
                rebalance_dates=rebalance_dates,
            )

        # 7. Compute statistics
        stats = self._compute_stats(result["daily"])

        return BacktestResult(
            daily=result["daily"],
            rebalance_positions=result["positions"],
            stats=stats,
            config=self.config,
        )

    def _get_valid_trading_dates_from_returns(
        self, returns_wide_all: pl.DataFrame, predictions_long: pl.DataFrame
    ) -> list[datetime]:
        """Compute valid trading dates based on returns dates and lagged prediction availability.

        Logic:
        - Use ALL dates present in the returns matrix as candidate trading dates
        - A date D is tradable if there exists any prediction with pred_date <= D - lag
        - Apply optional user-specified start/end bounds at the end
        """
        if "date" not in returns_wide_all.columns or len(returns_wide_all) == 0:
            return []
        all_trade_dates = sorted(returns_wide_all["date"].to_list())
        if not all_trade_dates:
            return []
        pred_dates = set(predictions_long["pred_date"].unique().to_list())
        lag_td = timedelta(days=self.config.prediction_lag_days)
        valid_dates: list[datetime] = []
        for d in all_trade_dates:
            cutoff = d - lag_td
            # We need at least one prediction available on or before cutoff
            if any(pd <= cutoff for pd in pred_dates):
                valid_dates.append(d)
        # Apply explicit user bounds last
        if self.config.start_date:
            valid_dates = [d for d in valid_dates if d >= self.config.start_date]
        if self.config.end_date:
            valid_dates = [d for d in valid_dates if d <= self.config.end_date]
        return valid_dates

    def _load_prices(self) -> pl.DataFrame:
        """Load price data in long format."""
        df = pl.read_parquet(self.config.prices_path)

        # Select and rename columns
        df = df.select(
            [
                pl.col(self.config.price_date_column).alias("date"),
                pl.col(self.config.price_id_column).alias("id"),
                pl.col(self.config.price_close_column).alias("close"),
            ]
        )

        # Ensure date is datetime
        if df["date"].dtype != pl.Datetime:
            df = df.with_columns(pl.col("date").cast(pl.Date).cast(pl.Datetime))

        # Drop nulls and sort
        df = df.drop_nulls().sort(["date", "id"])

        if self.config.verbose:
            print(f"Loaded {len(df):,} price records for {df['id'].n_unique()} assets")
            print(f"Price date range: {df['date'].min()} to {df['date'].max()}")

        return df

    def _load_predictions(self) -> pl.DataFrame:
        """Load prediction data in long format."""
        df = pl.read_parquet(self.config.predictions_path)

        # Select and rename columns
        df = df.select(
            [
                pl.col(self.config.pred_date_column).alias("pred_date"),
                pl.col(self.config.pred_id_column).alias("id"),
                pl.col(self.config.pred_value_column).alias("pred"),
            ]
        )

        # Ensure date is datetime
        if df["pred_date"].dtype != pl.Datetime:
            df = df.with_columns(pl.col("pred_date").cast(pl.Date).cast(pl.Datetime))

        # Drop nulls and sort
        df = df.drop_nulls().sort(["pred_date", "id"])

        if self.config.verbose:
            print(
                f"Loaded {len(df):,} prediction records for {df['id'].n_unique()} assets"
            )
            print(
                f"Prediction date range: {df['pred_date'].min()} to {df['pred_date'].max()}"
            )

        return df

    def _get_overlapping_dates(
        self, prices: pl.DataFrame, predictions: pl.DataFrame
    ) -> list[datetime]:
        """Find dates where we have both prices and valid predictions (considering lag)."""

        # Get unique dates from each dataset
        price_dates = set(prices["date"].unique().to_list())
        pred_dates = set(predictions["pred_date"].unique().to_list())

        # For each price date, check if we have predictions from T-lag days before
        valid_dates = []
        lag_td = timedelta(days=self.config.prediction_lag_days)

        for price_date in sorted(price_dates):
            # We need predictions from this date or earlier (up to lag days before)
            required_pred_date = price_date - lag_td

            # Check if we have predictions on or before the required date
            has_valid_pred = any(pd <= required_pred_date for pd in pred_dates)

            if has_valid_pred:
                valid_dates.append(price_date)

        # Apply user-specified date bounds if any
        if self.config.start_date:
            valid_dates = [d for d in valid_dates if d >= self.config.start_date]
        if self.config.end_date:
            valid_dates = [d for d in valid_dates if d <= self.config.end_date]

        if self.config.verbose:
            print(f"Found {len(valid_dates)} valid trading dates with overlapping data")
            if valid_dates:
                print(f"Trading date range: {min(valid_dates)} to {max(valid_dates)}")

        return valid_dates

    def _compute_returns_wide(self, prices_long: pl.DataFrame) -> pl.DataFrame:
        """Compute returns matrix in wide format (dates as rows, assets as columns)."""

        # Calculate returns for each asset
        prices_long = prices_long.sort(["id", "date"])
        prices_long = prices_long.with_columns(
            pl.col("close").pct_change().over("id").alias("return")
        )

        # Pivot to wide format
        returns_wide = prices_long.pivot(index="date", on="id", values="return").sort(
            "date"
        )

        if self.config.verbose:
            n_assets = len(returns_wide.columns) - 1  # Exclude date column
            print(f"Computed returns for {n_assets} assets")

        return returns_wide

    def _compute_rebalance_dates(self, valid_dates: list[datetime]) -> list[datetime]:
        """Determine rebalance dates based on schedule."""
        if not valid_dates:
            return []

        rebalance_dates = []
        current_date = min(valid_dates)

        while current_date <= max(valid_dates):
            if current_date in valid_dates:
                rebalance_dates.append(current_date)
            current_date += timedelta(days=self.config.rebalance_every_n_days)

        if self.config.verbose:
            print(f"Scheduled {len(rebalance_dates)} rebalance dates")

        return rebalance_dates

    def _select_assets(
        self,
        predictions: pl.DataFrame,
        cutoff_date: datetime,
        available_assets: set[str],
    ) -> tuple[list[str], list[str], pl.DataFrame]:
        """Select assets and return latest predictions DataFrame for sizing."""

        latest_preds = (
            predictions.filter(pl.col("pred_date") <= cutoff_date)
            .filter(pl.col("id").is_in(available_assets))
            .sort("pred_date", descending=True)
            .group_by("id")
            .first()
        )

        if len(latest_preds) == 0:
            empty = pl.DataFrame({"id": [], "pred": []})
            return [], [], empty

        latest_sorted = latest_preds.sort("pred", descending=True)
        all_ids = latest_sorted["id"].to_list()

        num_long = min(self.config.num_long, len(all_ids))
        num_short = min(self.config.num_short, len(all_ids) - num_long)

        long_assets = all_ids[:num_long]
        short_assets = all_ids[-num_short:] if num_short > 0 else []

        return long_assets, short_assets, latest_sorted.select(["id", "pred"])

    def _simulate(
        self,
        returns_wide: pl.DataFrame,
        predictions_long: pl.DataFrame,
        rebalance_dates: list[datetime],
    ) -> dict:
        """Run the backtest simulation."""

        # Initialize tracking variables
        equity = self.config.start_capital
        peak_equity = equity

        daily_results = []
        position_snapshots = []
        current_weights = {}  # Asset -> weight

        # Convert rebalance dates to set for fast lookup
        rebalance_set = set(rebalance_dates)

        # Get all dates from returns
        all_dates = returns_wide["date"].to_list()

        for i, date in enumerate(all_dates):
            # Get today's returns
            returns_row = returns_wide.filter(pl.col("date") == date)

            # Calculate portfolio return using old weights (positions held from previous close)
            portfolio_return = 0.0
            prev_equity = equity

            if current_weights:
                for asset, weight in current_weights.items():
                    if asset in returns_row.columns:
                        asset_return = returns_row[asset][0]
                        if asset_return is not None and not math.isnan(asset_return):
                            portfolio_return += weight * asset_return

            # Apply market return first
            equity_after_return = prev_equity * (1 + portfolio_return)

            # Check if we need to rebalance
            turnover = 0.0
            if date in rebalance_set:
                # Determine cutoff date for predictions (T - lag)
                cutoff_date = date - timedelta(days=self.config.prediction_lag_days)

                # Get available assets (those with returns today)
                available_assets = set()
                for col in returns_row.columns:
                    if col != "date":
                        val = returns_row[col][0]
                        if val is not None and not math.isnan(val):
                            available_assets.add(col)

                # Determine selections and convert ranks to weights
                long_assets, short_assets, latest_preds = self._select_assets(
                    predictions_long,
                    cutoff_date,
                    available_assets,
                )

                new_weights: dict[str, float] = {}
                total_positions = len(long_assets) + len(short_assets)

                if total_positions > 0 and len(latest_preds) > 0:
                    weights = weights_from_ranks(
                        latest_preds=latest_preds,
                        id_col="id",
                        pred_col="pred",
                        long_assets=long_assets,
                        short_assets=short_assets,
                        target_gross=self.config.target_leverage,
                        power=self.config.rank_power,
                    )
                    new_weights = weights

                # Calculate turnover (L1 norm of weight changes)
                all_assets = set(current_weights.keys()) | set(new_weights.keys())
                for asset in all_assets:
                    old_w = current_weights.get(asset, 0.0)
                    new_w = new_weights.get(asset, 0.0)
                    turnover += abs(new_w - old_w)

                # Apply trading costs
                total_cost_bps = self.config.fee_bps + self.config.slippage_bps
                cost = turnover * (total_cost_bps / 10_000)

                # Deduct rebalancing costs from equity after market move
                equity = equity_after_return * (1 - cost)

                # Store position snapshot
                for asset, weight in new_weights.items():
                    position_snapshots.append(
                        {"date": date, "id": asset, "weight": weight}
                    )

                # Update weights for next period (take effect at next close)
                current_weights = new_weights.copy()
            else:
                # No rebalance; equity is just after market move
                equity = equity_after_return

            # Track peak and drawdown AFTER all effects (returns + costs)
            if equity > peak_equity:
                peak_equity = equity
            drawdown = (equity - peak_equity) / peak_equity if peak_equity > 0 else 0

            # Net daily return including costs
            net_return = (equity / prev_equity) - 1.0

            # Store daily results
            daily_results.append(
                {
                    "date": date,
                    "returns": net_return,
                    "equity": equity,
                    "drawdown": drawdown,
                    "turnover": turnover,
                }
            )

        # Convert to DataFrames
        daily_df = pl.DataFrame(daily_results)
        positions_df = (
            pl.DataFrame(position_snapshots) if position_snapshots else pl.DataFrame()
        )

        return {"daily": daily_df, "positions": positions_df}

    def _simulate_rolling(
        self,
        returns_wide: pl.DataFrame,
        predictions_long: pl.DataFrame,
    ) -> dict:
        """Run backtest simulation with rolling vintage strategy.

        In rolling mode:
        - Each day creates a new vintage with 1/N of target allocation
        - Vintages expire after rolling_days
        - Current weights = sum of all active vintage weights
        """
        rolling_days = self.config.rolling_days
        seed_full = self.config.seed_full

        # Initialize tracking variables
        equity = self.config.start_capital
        peak_equity = equity

        daily_results = []
        position_snapshots = []

        # Vintages: date -> {asset: weight}
        vintages: dict[datetime, dict[str, float]] = {}

        # Previous day's summed weights for turnover calculation
        prev_weights: dict[str, float] = {}

        # Get all dates from returns
        all_dates = returns_wide["date"].to_list()

        for i, date in enumerate(all_dates):
            prev_equity = equity

            # --- 1. Prune expired vintages ---
            cutoff = date - timedelta(days=rolling_days)
            vintages = {d: v for d, v in vintages.items() if d > cutoff}

            # --- 2. Create today's vintage (or seed on first day) ---
            cutoff_date = date - timedelta(days=self.config.prediction_lag_days)

            # Get available assets (those with returns today)
            returns_row = returns_wide.filter(pl.col("date") == date)
            available_assets = set()
            for col in returns_row.columns:
                if col != "date":
                    val = returns_row[col][0]
                    if val is not None and not math.isnan(val):
                        available_assets.add(col)

            # Seed on first day if enabled and no vintages yet
            if i == 0 and seed_full and not vintages:
                vintages = self._seed_vintages_for_backtest(
                    predictions_long, date, available_assets, rolling_days
                )
            elif date not in vintages:
                # Create today's vintage
                new_vintage = self._create_backtest_vintage(
                    predictions_long, cutoff_date, available_assets, rolling_days
                )
                if new_vintage:
                    vintages[date] = new_vintage

            # --- 3. Sum vintages to get current weights ---
            current_weights: dict[str, float] = {}
            for v in vintages.values():
                for asset, weight in v.items():
                    current_weights[asset] = current_weights.get(asset, 0) + weight

            # --- 4. Calculate portfolio return using current weights ---
            portfolio_return = 0.0
            if current_weights:
                for asset, weight in current_weights.items():
                    if asset in returns_row.columns:
                        asset_return = returns_row[asset][0]
                        if asset_return is not None and not math.isnan(asset_return):
                            portfolio_return += weight * asset_return

            # Apply market return first
            equity_after_return = prev_equity * (1 + portfolio_return)

            # --- 5. Calculate turnover ---
            all_assets = set(prev_weights.keys()) | set(current_weights.keys())
            turnover = 0.0
            for asset in all_assets:
                old_w = prev_weights.get(asset, 0.0)
                new_w = current_weights.get(asset, 0.0)
                turnover += abs(new_w - old_w)

            # Apply trading costs if there's turnover
            if turnover > 0:
                total_cost_bps = self.config.fee_bps + self.config.slippage_bps
                cost = turnover * (total_cost_bps / 10_000)
                equity = equity_after_return * (1 - cost)
            else:
                equity = equity_after_return

            # Store position snapshot
            for asset, weight in current_weights.items():
                position_snapshots.append(
                    {"date": date, "id": asset, "weight": weight}
                )

            # Update prev_weights for next iteration
            prev_weights = current_weights.copy()

            # Track peak and drawdown
            if equity > peak_equity:
                peak_equity = equity
            drawdown = (equity - peak_equity) / peak_equity if peak_equity > 0 else 0

            # Net daily return including costs
            net_return = (equity / prev_equity) - 1.0

            daily_results.append(
                {
                    "date": date,
                    "returns": net_return,
                    "equity": equity,
                    "drawdown": drawdown,
                    "turnover": turnover,
                }
            )

        # Convert to DataFrames
        daily_df = pl.DataFrame(daily_results)
        positions_df = (
            pl.DataFrame(position_snapshots) if position_snapshots else pl.DataFrame()
        )

        return {"daily": daily_df, "positions": positions_df}

    def _create_backtest_vintage(
        self,
        predictions: pl.DataFrame,
        cutoff_date: datetime,
        available_assets: set[str],
        rolling_days: int,
    ) -> dict[str, float]:
        """Create a single vintage with scaled weights for backtest."""
        # Scale leverage only (counts remain full for correct diversification)
        scaled_leverage = self.config.target_leverage / rolling_days
        
        # Use full counts
        num_long = self.config.num_long
        num_short = self.config.num_short

        # Get asset selection
        long_assets, short_assets, latest_preds = self._select_assets(
            predictions, cutoff_date, available_assets
        )

        # Limit to config counts
        long_assets = long_assets[:num_long]
        short_assets = short_assets[:num_short]

        total_positions = len(long_assets) + len(short_assets)
        if total_positions == 0 or len(latest_preds) == 0:
            return {}

        # Get weights with scaled leverage
        weights = weights_from_ranks(
            latest_preds=latest_preds,
            id_col="id",
            pred_col="pred",
            long_assets=long_assets,
            short_assets=short_assets,
            target_gross=scaled_leverage,
            power=self.config.rank_power,
        )

        return weights

    def _seed_vintages_for_backtest(
        self,
        predictions: pl.DataFrame,
        start_date: datetime,
        available_assets: set[str],
        rolling_days: int,
    ) -> dict[datetime, dict[str, float]]:
        """Seed vintages for backtest using historical predictions."""
        vintages: dict[datetime, dict[str, float]] = {}

        # Get unique prediction dates
        pred_dates = sorted(
            predictions["pred_date"].unique().to_list(),
            reverse=True
        )

        for i in range(min(rolling_days, len(pred_dates))):
            # Synthetic vintage date (staggered back from start)
            vintage_date = start_date - timedelta(days=i)
            pred_date = pred_dates[i]

            # Create vintage using this prediction date
            vintage = self._create_backtest_vintage(
                predictions, pred_date, available_assets, rolling_days
            )
            if vintage:
                vintages[vintage_date] = vintage

        return vintages

    def _compute_stats(self, daily: pl.DataFrame) -> dict[str, float]:
        """Compute summary statistics from daily results."""

        if len(daily) == 0:
            return {}

        # Basic info
        n_days = len(daily)
        start_equity = self.config.start_capital
        final_equity = daily["equity"][-1]

        # Returns
        total_return = (final_equity / start_equity) - 1

        # Annualized metrics (assuming 365 days per year for crypto)
        years = n_days / 365.0
        # Handle negative equity (can't take fractional power of negative number)
        if years > 0 and final_equity > 0:
            cagr = (final_equity / start_equity) ** (1.0 / years) - 1
        else:
            cagr = total_return  # Fallback to simple return if equity went negative

        # Risk metrics
        returns = daily["returns"]
        daily_vol = returns.std()
        annual_vol = float(daily_vol * math.sqrt(365)) if daily_vol is not None else 0.0

        # Calculate annualized arithmetic mean return for Sharpe/Sortino
        mean_daily_return = returns.mean()
        annualized_mean_return = float(mean_daily_return * 365) if mean_daily_return is not None else 0.0

        # Sharpe ratio (using arithmetic mean, not CAGR)
        sharpe = annualized_mean_return / annual_vol if annual_vol > 0 else 0.0

        # Drawdown
        max_drawdown = daily["drawdown"].min()  # Most negative value

        # Calmar ratio
        calmar = (
            cagr / abs(max_drawdown)
            if max_drawdown is not None and max_drawdown < 0
            else 0
        )

        # Win rate
        positive_days = (returns > 0).sum()
        win_rate = positive_days / n_days if n_days > 0 else 0

        # Turnover
        avg_turnover = daily.filter(pl.col("turnover") > 0)["turnover"].mean()
        if avg_turnover is None:
            avg_turnover = 0

        # Sortino ratio (downside deviation, using arithmetic mean)
        negative_returns = returns.filter(returns < 0)
        if len(negative_returns) > 0:
            downside_vol = negative_returns.std()
            annual_downside_vol = (
                downside_vol * math.sqrt(365) if downside_vol is not None else 0
            )
            sortino = annualized_mean_return / annual_downside_vol if annual_downside_vol > 0 else 0
        else:
            sortino = float("inf") if annualized_mean_return > 0 else 0

        return {
            "days": n_days,
            "total_return": total_return,
            "cagr": cagr,
            "annual_volatility": annual_vol,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": max_drawdown,
            "calmar_ratio": calmar,
            "win_rate": win_rate,
            "avg_turnover": avg_turnover,
            "final_equity": final_equity,
        }


class BacktestOptimizer:
    """Grid search optimizer for backtesting parameters with parallel execution and caching."""

    def __init__(self, base_config: BacktestConfig):
        self.base_config = base_config
        self._prices_cache = None
        self._predictions_cache = None
        self._cache_file = ".cc_liquid_optimizer_cache.json"

    def _get_cache_key(self, params: dict) -> str:
        """Generate a unique cache key for a parameter combination."""
        import hashlib
        import json

        # Include base config settings that affect results
        cache_data = {
            "params": params,
            "config": {
                "prices_path": self.base_config.prices_path,
                "predictions_path": self.base_config.predictions_path,
                "data_provider": self.base_config.data_provider,
                "start_date": str(self.base_config.start_date)
                if self.base_config.start_date
                else None,
                "end_date": str(self.base_config.end_date)
                if self.base_config.end_date
                else None,
                "prediction_lag_days": self.base_config.prediction_lag_days,
                "fee_bps": self.base_config.fee_bps,
                "slippage_bps": self.base_config.slippage_bps,
                "start_capital": self.base_config.start_capital,
                "rank_power": self.base_config.rank_power,
            },
        }

        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _load_cache(self) -> dict:
        """Load cached results from disk."""
        import json
        import os

        if not os.path.exists(self._cache_file):
            return {}

        try:
            with open(self._cache_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_cache(self, cache: dict) -> None:
        """Save cache to disk."""
        import json

        try:
            with open(self._cache_file, "w") as f:
                json.dump(cache, f)
        except Exception:
            pass  # Silently fail if can't write cache

    def _run_single_backtest(self, params: dict) -> dict | None:
        """Run a single backtest with given parameters. No cache IO here."""
        # Create config for this combination
        config = BacktestConfig(
            prices_path=self.base_config.prices_path,
            predictions_path=self.base_config.predictions_path,
            price_date_column=self.base_config.price_date_column,
            price_id_column=self.base_config.price_id_column,
            price_close_column=self.base_config.price_close_column,
            pred_date_column=self.base_config.pred_date_column,
            pred_id_column=self.base_config.pred_id_column,
            pred_value_column=self.base_config.pred_value_column,
            data_provider=self.base_config.data_provider,
            start_date=self.base_config.start_date,
            end_date=self.base_config.end_date,
            num_long=params["num_long"],
            num_short=params["num_short"],
            target_leverage=params["leverage"],
            rebalance_every_n_days=params["rebalance_days"],
            prediction_lag_days=self.base_config.prediction_lag_days,
            mode=params.get("mode", self.base_config.mode),
            rolling_days=params.get("rolling_days", self.base_config.rolling_days),
            seed_full=self.base_config.seed_full,
            fee_bps=self.base_config.fee_bps,
            slippage_bps=self.base_config.slippage_bps,
            start_capital=self.base_config.start_capital,
            verbose=False,
            rank_power=params["rank_power"],
        )

        try:
            # Run backtest
            backtester = Backtester(config)
            result = backtester.run()

            # Store results
            result_data = {
                "num_long": params["num_long"],
                "num_short": params["num_short"],
                "leverage": params["leverage"],
                "rebalance_days": params["rebalance_days"],
                "rank_power": params["rank_power"],
                "sharpe": result.stats["sharpe_ratio"],
                "cagr": result.stats["cagr"],
                "calmar": result.stats["calmar_ratio"],
                "sortino": result.stats["sortino_ratio"],
                "max_dd": result.stats["max_drawdown"],
                "volatility": result.stats["annual_volatility"],
                "win_rate": result.stats["win_rate"],
                "final_equity": result.stats["final_equity"],
            }

            return result_data

        except Exception:
            return None

    def grid_search_parallel(
        self,
        num_longs: list[int] | None = None,
        num_shorts: list[int] | None = None,
        leverages: list[float] | None = None,
        rebalance_days: list[int] | None = None,
        rank_powers: list[float] | None = None,
        metric: Literal["sharpe", "cagr", "calmar"] = "sharpe",
        max_drawdown_limit: float | None = None,
        max_workers: int | None = None,
        progress_callback: Any | None = None,
    ) -> pl.DataFrame:
        """Run grid search over parameter combinations in parallel.

        Args:
            num_longs: List of long position counts to test
            num_shorts: List of short position counts to test
            leverages: List of leverage values to test
            rebalance_days: List of rebalance frequencies to test
            rank_powers: List of rank power values to test (0=equal weight)
            metric: Optimization metric
            max_drawdown_limit: Maximum drawdown constraint
            max_workers: Number of parallel workers (None = auto)
            progress_callback: Rich Progress instance for updates

        Returns:
            DataFrame with all results sorted by metric.
        """
        from concurrent.futures import ProcessPoolExecutor, as_completed
        import multiprocessing as mp
        import time

        # Default to single values from base config if not specified
        if num_longs is None:
            num_longs = [self.base_config.num_long]
        if num_shorts is None:
            num_shorts = [self.base_config.num_short]
        if leverages is None:
            leverages = [self.base_config.target_leverage]
        if rebalance_days is None:
            rebalance_days = [self.base_config.rebalance_every_n_days]
        if rank_powers is None:
            rank_powers = [self.base_config.rank_power]

        # Generate all parameter combinations
        param_combinations = []
        for n_long in num_longs:
            for n_short in num_shorts:
                for leverage in leverages:
                    for rebal_days in rebalance_days:
                        for rank_pow in rank_powers:
                            param_combinations.append(
                                {
                                    "num_long": n_long,
                                    "num_short": n_short,
                                    "leverage": leverage,
                                    "rebalance_days": rebal_days,
                                    "rank_power": rank_pow,
                                }
                            )

        # Check cache to see which we already have
        cache = self._load_cache()
        cached_count = sum(
            1 for p in param_combinations if self._get_cache_key(p) in cache
        )

        # Get cache metadata
        cache_info = ""
        if cached_count > 0:
            import os
            import time as time_module

            if os.path.exists(self._cache_file):
                cache_size = os.path.getsize(self._cache_file) / 1024  # KB
                cache_age = time_module.time() - os.path.getmtime(self._cache_file)
                if cache_age < 3600:
                    age_str = f"{int(cache_age / 60)} min"
                elif cache_age < 86400:
                    age_str = f"{cache_age / 3600:.1f} hours"
                else:
                    age_str = f"{cache_age / 86400:.1f} days"
                cache_info = f" (cache: {cache_size:.1f}KB, {age_str} old)"

        # Always surface cache info (via progress console when available)
        if cached_count > 0:
            msg = f"Found {cached_count}/{len(param_combinations)} results in cache{cache_info}"
            if progress_callback is not None and hasattr(progress_callback, "console"):
                progress_callback.console.print(msg)
            else:
                print(msg)

        # Set up parallel execution
        if max_workers is None:
            max_workers = min(mp.cpu_count(), 24)  # Cap at 24 for memory reasons

        results = []
        best_so_far = None

        # Track rate (only for non-cached backtests)
        start_time = None
        non_cached_completed = 0

        # Separate cached and to-run combinations (load cache instantly before starting progress)
        to_run: list[dict] = []
        cached_count = 0
        for params in param_combinations:
            key = self._get_cache_key(params)
            cached = cache.get(key)
            if cached is not None:
                # Respect drawdown filter
                if (
                    max_drawdown_limit is not None
                    and cached.get("max_dd", 0) < -max_drawdown_limit
                ):
                    cached_count += 1
                    continue
                results.append(cached)
                if best_so_far is None or cached[metric] > best_so_far[metric]:
                    best_so_far = cached.copy()
                cached_count += 1
            else:
                to_run.append(params)

        # Create task AFTER loading cached results, so timer starts fresh
        task_id = None
        if progress_callback:
            task_id = progress_callback.add_task(
                "[cyan]Running backtests...", 
                total=len(param_combinations),
                completed=cached_count  # Already completed from cache
            )

        # Run remaining in parallel
        if to_run:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                future_to_params = {
                    executor.submit(self._run_single_backtest, params): params
                    for params in to_run
                }
                for future in as_completed(future_to_params):
                    params = future_to_params[future]
                    
                    # Start timer on first actual backtest completion
                    if start_time is None:
                        start_time = time.time()
                    
                    try:
                        result = future.result()
                        if result is not None:
                            # Respect drawdown filter
                            if (
                                max_drawdown_limit is not None
                                and result["max_dd"] < -max_drawdown_limit
                            ):
                                if progress_callback and task_id is not None:
                                    progress_callback.update(task_id, advance=1)
                                continue
                            results.append(result)
                            # Update best so far
                            if (
                                best_so_far is None
                                or result[metric] > best_so_far[metric]
                            ):
                                best_so_far = result.copy()
                            # Save to cache (main process only)
                            key = self._get_cache_key(params)
                            cache[key] = result
                            self._save_cache(cache)
                            # Progress update
                            if progress_callback and task_id is not None:
                                non_cached_completed += 1
                                elapsed = max(time.time() - start_time, 1e-6)
                                rate = non_cached_completed / elapsed
                                rate_str = "instant" if rate > 999 else f"{rate:.1f}/s"
                                progress_callback.update(
                                    task_id,
                                    advance=1,
                                    description=f"[cyan]Backtests[/cyan] [dim]│[/dim] Best {metric}: {best_so_far[metric]:.3f} [dim]| {rate_str}[/dim]",
                                )
                        else:
                            if progress_callback and task_id is not None:
                                non_cached_completed += 1
                                elapsed = max(time.time() - start_time, 1e-6)
                                rate = non_cached_completed / elapsed
                                rate_str = "instant" if rate > 999 else f"{rate:.1f}/s"
                                progress_callback.update(
                                    task_id,
                                    advance=1,
                                    description=f"[cyan]Backtests[/cyan] [dim]| {rate_str}[/dim]",
                                )
                    except Exception:
                        if progress_callback and task_id is not None:
                            non_cached_completed += 1
                            elapsed = max(time.time() - start_time, 1e-6)
                            rate = non_cached_completed / elapsed
                            rate_str = "instant" if rate > 999 else f"{rate:.1f}/s"
                            progress_callback.update(
                                task_id,
                                advance=1,
                                description=f"[cyan]Backtests[/cyan] [dim]| {rate_str}[/dim]",
                            )

        # Convert to DataFrame and sort by metric
        if not results:
            return pl.DataFrame()

        df = pl.DataFrame(results)
        
        # Cast numeric columns to proper float types (handles complex numbers, NaN, inf)
        numeric_cols = ["sharpe", "cagr", "calmar", "sortino", "max_dd", "volatility", "win_rate", "final_equity"]
        df = df.with_columns([
            pl.col(col).cast(pl.Float64, strict=False).fill_nan(0.0)
            for col in numeric_cols if col in df.columns
        ])
        
        df = df.sort(metric, descending=True)

        return df

    def clear_cache(self) -> None:
        """Clear the optimization cache."""
        import os

        if os.path.exists(self._cache_file):
            os.remove(self._cache_file)

    def grid_search(
        self,
        num_longs: list[int] | None = None,
        num_shorts: list[int] | None = None,
        leverages: list[float] | None = None,
        rebalance_days: list[int] | None = None,
        metric: Literal["sharpe", "cagr", "calmar"] = "sharpe",
        max_drawdown_limit: float | None = None,
    ) -> pl.DataFrame:
        """Legacy sequential grid search (kept for backwards compatibility)."""
        # Just call the parallel version with max_workers=1
        return self.grid_search_parallel(
            num_longs=num_longs,
            num_shorts=num_shorts,
            leverages=leverages,
            rebalance_days=rebalance_days,
            metric=metric,
            max_drawdown_limit=max_drawdown_limit,
            max_workers=1,
            progress_callback=None,
        )

    def get_best_params(
        self,
        results_df: pl.DataFrame,
        metric: Literal["sharpe", "cagr", "calmar"] = "sharpe",
    ) -> dict[str, Any] | None:
        """Extract best parameters from results DataFrame."""

        if len(results_df) == 0:
            return None

        # Get best row
        best_row = results_df.sort(metric, descending=True).head(1)

        return {
            "num_long": int(best_row["num_long"][0]),
            "num_short": int(best_row["num_short"][0]),
            "target_leverage": float(best_row["leverage"][0]),
            "rebalance_every_n_days": int(best_row["rebalance_days"][0]),
            "rank_power": float(best_row["rank_power"][0]),
        }
