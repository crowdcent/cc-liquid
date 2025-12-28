"""Parameter optimization framework for backtesting.

This module provides grid search optimization for finding optimal
portfolio parameters.
"""

from __future__ import annotations

import itertools
from decimal import Decimal

import polars as pl
from loguru import logger as log

from cc_flow.core.backtester import BacktestDataLoader, BacktestEngine
from cc_flow.domain.backtest import BacktestConfig, BacktestResult
from cc_flow.domain.config import ExecutionConfig, PortfolioConfig


class BacktestOptimizer:
    """Optimize portfolio parameters using grid search.

    Searches across parameter space to find optimal portfolio configuration
    based on a target metric (e.g., Sharpe ratio).

    Attributes:
        data_loader: DataLoader for preparing backtest data
        base_config: Base backtest configuration
        optimization_metric: Metric to optimize (default: "sharpe_ratio")

    Example:
        >>> optimizer = BacktestOptimizer(loader, config, "sharpe_ratio")
        >>> param_grid = {"num_long": [5, 10], "num_short": [5, 10]}
        >>> results = optimizer.optimize(param_grid)
        >>> best = optimizer.get_best_parameters(results)
    """

    def __init__(
        self,
        data_loader: BacktestDataLoader,
        base_config: BacktestConfig,
        optimization_metric: str = "sharpe_ratio",
    ):
        """Initialize BacktestOptimizer.

        Args:
            data_loader: DataLoader instance for preparing backtest data
            base_config: Base backtest configuration to modify
            optimization_metric: Metric to optimize (sharpe_ratio, total_return, etc.)
        """
        self.data_loader = data_loader
        self.base_config = base_config
        self.optimization_metric = optimization_metric

    def optimize(self, param_grid: dict[str, list]) -> pl.DataFrame:
        """Run grid search optimization.

        Tests all combinations of parameters and returns results sorted
        by optimization metric.

        Args:
            param_grid: Dict mapping parameter names to lists of values to test
                Example: {
                    "num_long": [5, 10, 15],
                    "num_short": [5, 10, 15],
                    "target_leverage": [Decimal("1.0"), Decimal("1.5")]
                }

        Returns:
            DataFrame with columns for each parameter plus all performance metrics,
            sorted by optimization_metric (descending)

        Example:
            >>> results = optimizer.optimize(param_grid)
            >>> assert len(results) == 18  # 3 * 3 * 2 combinations
        """
        log.info(f"Starting grid search optimization on {self.optimization_metric}")

        # Generate all parameter combinations
        combinations = self._generate_parameter_combinations(param_grid)
        log.info(f"Testing {len(combinations)} parameter combinations")

        # Run backtest for each combination
        results = []
        for i, params in enumerate(combinations):
            log.debug(f"Testing combination {i+1}/{len(combinations)}: {params}")

            try:
                result = self._run_single_backtest(params)

                # Extract metrics and parameters
                row = {
                    **params,  # Add all parameter values
                    "total_return": float(result.total_return),
                    "cagr": float(result.cagr),
                    "sharpe_ratio": float(result.sharpe_ratio),
                    "sortino_ratio": float(result.sortino_ratio),
                    "max_drawdown": float(result.max_drawdown),
                    "calmar_ratio": float(result.calmar_ratio),
                    "volatility": float(result.annual_volatility),
                    "win_rate": float(result.win_rate),
                    "num_trades": result.num_trades,
                    "num_rebalances": result.num_rebalances,
                }

                results.append(row)

            except Exception as e:
                log.error(f"Failed to backtest {params}: {e}")
                continue

        # Convert to DataFrame
        if not results:
            log.warning("No successful backtests completed")
            return pl.DataFrame()

        results_df = pl.DataFrame(results)

        # Sort by optimization metric (descending)
        if self.optimization_metric in results_df.columns:
            results_df = results_df.sort(self.optimization_metric, descending=True)

        log.info(f"Optimization complete. Best {self.optimization_metric}: "
                f"{results_df[self.optimization_metric][0]:.4f}")

        return results_df

    def _generate_parameter_combinations(self, param_grid: dict[str, list]) -> list[dict]:
        """Generate all parameter combinations from grid.

        Args:
            param_grid: Dict mapping parameter names to lists of values

        Returns:
            List of dicts, each representing one parameter combination

        Example:
            >>> grid = {"a": [1, 2], "b": [3, 4]}
            >>> combos = optimizer._generate_parameter_combinations(grid)
            >>> assert len(combos) == 4
        """
        # Get parameter names and value lists
        param_names = list(param_grid.keys())
        value_lists = [param_grid[name] for name in param_names]

        # Generate all combinations using itertools.product
        combinations = []
        for values in itertools.product(*value_lists):
            combo = dict(zip(param_names, values))
            combinations.append(combo)

        return combinations

    def _run_single_backtest(self, params: dict) -> BacktestResult:
        """Run single backtest with given parameters.

        Args:
            params: Dict of parameter values to override in base_config

        Returns:
            BacktestResult from simulation

        Example:
            >>> params = {"num_long": 10, "num_short": 5}
            >>> result = optimizer._run_single_backtest(params)
            >>> assert isinstance(result, BacktestResult)
        """
        # Create modified configs
        portfolio_config = PortfolioConfig(
            num_long=params.get("num_long", self.base_config.num_long),
            num_short=params.get("num_short", self.base_config.num_short),
            target_leverage=params.get("target_leverage", self.base_config.target_leverage),
            rank_power=params.get("rank_power", self.base_config.rank_power),
        )

        execution_config = ExecutionConfig(
            slippage_tolerance=params.get("slippage_tolerance", Decimal("0.005")),
            min_trade_value=params.get("min_trade_value", Decimal("10.0")),
        )

        # Update backtest config if needed
        backtest_config = self.base_config
        if "rebalance_every_n_days" in params:
            # Create new config with updated value
            backtest_config = BacktestConfig(
                num_long=portfolio_config.num_long,
                num_short=portfolio_config.num_short,
                target_leverage=portfolio_config.target_leverage,
                rank_power=portfolio_config.rank_power,
                rebalance_every_n_days=params["rebalance_every_n_days"],
                predictions_path=self.base_config.predictions_path,
                prices_path=self.base_config.prices_path,
                fee_rate=self.base_config.fee_rate,
                slippage_bps=self.base_config.slippage_bps,
                start_date=self.base_config.start_date,
                end_date=self.base_config.end_date,
                prediction_lag_days=self.base_config.prediction_lag_days,
            )

        # Load predictions (would normally be cached)
        # For now, we'll create dummy predictions
        # In production, this should load actual prediction data
        from datetime import date, timedelta

        start = date(2024, 1, 1) if backtest_config.start_date is None else date.fromisoformat(backtest_config.start_date)
        end = date(2024, 1, 30) if backtest_config.end_date is None else date.fromisoformat(backtest_config.end_date)

        # Create dummy predictions
        dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        assets = ["BTC", "ETH", "SOL", "AVAX", "MATIC"]

        pred_rows = []
        for d in dates:
            for i, asset in enumerate(assets):
                pred_rows.append({
                    "date": d,
                    "asset_id": asset,
                    "prediction": 0.5 - (i * 0.2)
                })

        predictions = pl.DataFrame(pred_rows)

        # Prepare backtest data
        backtest_data = self.data_loader.prepare_backtest_data(predictions)

        # Run backtest
        engine = BacktestEngine(
            config=backtest_config,
            portfolio_config=portfolio_config,
            execution_config=execution_config,
        )

        result = engine.simulate(backtest_data)
        return result

    def get_best_parameters(self, results: pl.DataFrame) -> dict:
        """Extract best parameters from optimization results.

        Args:
            results: DataFrame returned by optimize()

        Returns:
            Dict of parameter values from best result

        Example:
            >>> best_params = optimizer.get_best_parameters(results)
            >>> assert "num_long" in best_params
        """
        if len(results) == 0:
            log.warning("No results to extract best parameters from")
            return {}

        # Results are already sorted by optimization metric
        best_row = results.row(0, named=True)

        # Extract only parameter columns (exclude metric columns)
        metric_columns = {
            "total_return", "cagr", "sharpe_ratio", "sortino_ratio",
            "max_drawdown", "calmar_ratio", "volatility", "win_rate",
            "num_trades", "num_rebalances"
        }

        best_params = {k: v for k, v in best_row.items() if k not in metric_columns}

        log.info(f"Best parameters: {best_params}")
        return best_params
