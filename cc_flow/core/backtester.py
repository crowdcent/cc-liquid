"""Backtesting system for portfolio strategies.

This module provides a complete backtesting framework for testing portfolio
strategies using historical data. It includes data loading, simulation,
performance calculation, and parameter optimization.

Classes:
    BacktestDataLoader: Load and prepare historical price data
    BacktestEngine: Core simulation engine for backtesting
    PerformanceCalculator: Calculate performance metrics
    BacktestOptimizer: Grid search optimization framework

Example:
    >>> loader = BacktestDataLoader(price_data_path=Path("prices.parquet"))
    >>> backtest_data = loader.prepare_backtest_data(predictions=predictions_df)
    >>> engine = BacktestEngine(config=config, portfolio_config=portfolio_config)
    >>> result = engine.simulate(backtest_data=backtest_data)
    >>> print(f"Sharpe Ratio: {result.sharpe_ratio}")
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import polars as pl
from loguru import logger as log

from cc_flow.core.portfolio import PortfolioManager
from cc_flow.domain.backtest import BacktestConfig, BacktestResult
from cc_flow.domain.config import ExecutionConfig, PortfolioConfig
from cc_flow.domain.orders import OrderSide, Trade


class BacktestDataLoader:
    """Load and prepare historical price data for backtesting.

    This class handles loading price data from parquet files, merging with
    predictions, and ensuring proper data alignment for backtesting.

    Attributes:
        price_data_path: Path to historical price data parquet file

    Example:
        >>> loader = BacktestDataLoader(price_data_path=Path("prices.parquet"))
        >>> backtest_data = loader.prepare_backtest_data(predictions=predictions_df)
        >>> print(f"Loaded {len(backtest_data)} rows")
    """

    def __init__(self, price_data_path: Path):
        """Initialize BacktestDataLoader.

        Args:
            price_data_path: Path to historical price data (parquet file)
                Expected columns: date, asset_id, close, volume
        """
        self.price_data_path = price_data_path

    def load_price_data(self, start_date: date, end_date: date) -> pl.DataFrame:
        """Load price data for specified date range.

        Args:
            start_date: Start date for price data
            end_date: End date for price data

        Returns:
            DataFrame with columns: date, asset_id, close, volume

        Example:
            >>> loader = BacktestDataLoader(Path("prices.parquet"))
            >>> prices = loader.load_price_data(date(2024, 1, 1), date(2024, 1, 31))
            >>> assert "close" in prices.columns
        """
        log.debug(f"Loading price data from {self.price_data_path}")

        prices = pl.read_parquet(self.price_data_path)

        # Filter by date range
        prices = prices.filter(
            (pl.col("date") >= start_date) & (pl.col("date") <= end_date)
        )

        # Sort by date
        prices = prices.sort("date")

        log.debug(f"Loaded {len(prices)} price records")
        return prices

    def merge_predictions_with_prices(
        self, predictions: pl.DataFrame, prices: pl.DataFrame
    ) -> pl.DataFrame:
        """Merge predictions with price data.

        Performs inner join on (date, asset_id) to ensure we only keep
        predictions where we have corresponding price data.

        Args:
            predictions: DataFrame with columns: date, asset_id, prediction
            prices: DataFrame with columns: date, asset_id, close, volume

        Returns:
            Merged DataFrame with columns: date, asset_id, prediction, close

        Example:
            >>> merged = loader.merge_predictions_with_prices(predictions, prices)
            >>> assert "prediction" in merged.columns and "close" in merged.columns
        """
        log.debug("Merging predictions with prices")

        # Inner join to only keep predictions with available prices
        merged = predictions.join(
            prices.select(["date", "asset_id", "close"]),
            on=["date", "asset_id"],
            how="inner"
        )

        log.debug(f"Merged data has {len(merged)} rows")
        return merged

    def prepare_backtest_data(self, predictions: pl.DataFrame) -> pl.DataFrame:
        """Prepare complete backtest data.

        Main entry point that loads prices for the prediction date range,
        merges with predictions, and validates data integrity.

        Args:
            predictions: DataFrame with columns: date, asset_id, prediction

        Returns:
            Ready-to-use DataFrame with columns: date, asset_id, prediction, close

        Example:
            >>> loader = BacktestDataLoader(Path("prices.parquet"))
            >>> backtest_data = loader.prepare_backtest_data(predictions)
            >>> assert len(backtest_data) > 0
        """
        log.info("Preparing backtest data")

        # Get date range from predictions
        start_date = predictions["date"].min()
        end_date = predictions["date"].max()

        log.debug(f"Prediction date range: {start_date} to {end_date}")

        # Load prices
        prices = self.load_price_data(start_date=start_date, end_date=end_date)

        # Merge
        backtest_data = self.merge_predictions_with_prices(
            predictions=predictions,
            prices=prices
        )

        # Validate
        if len(backtest_data) == 0:
            log.warning("No data after merging predictions with prices!")

        log.info(f"Prepared {len(backtest_data)} backtest records")
        return backtest_data.sort("date")


class BacktestEngine:
    """Core backtesting simulation engine.

    Simulates portfolio rebalancing over historical data with realistic
    transaction costs, leverage scaling, and daily return tracking.

    Attributes:
        config: Backtest configuration
        portfolio_config: Portfolio construction configuration
        execution_config: Execution parameters

    Example:
        >>> engine = BacktestEngine(config, portfolio_config, execution_config)
        >>> result = engine.simulate(backtest_data)
        >>> print(f"Total Return: {result.total_return:.2%}")
    """

    def __init__(
        self,
        config: BacktestConfig,
        portfolio_config: PortfolioConfig,
        execution_config: ExecutionConfig,
    ):
        """Initialize BacktestEngine.

        Args:
            config: Backtest configuration with rebalancing schedule and costs
            portfolio_config: Portfolio construction parameters
            execution_config: Execution settings (slippage, min trade value)
        """
        self.config = config
        self.portfolio_config = portfolio_config
        self.execution_config = execution_config
        self.portfolio_manager = PortfolioManager(config=portfolio_config)

    def simulate(self, backtest_data: pl.DataFrame) -> BacktestResult:
        """Run complete backtest simulation.

        Simulates periodic rebalancing, transaction costs, and tracks
        daily portfolio returns.

        Args:
            backtest_data: DataFrame with date, asset_id, prediction, close

        Returns:
            BacktestResult with performance metrics and time series data

        Example:
            >>> result = engine.simulate(backtest_data)
            >>> assert result.num_rebalances > 0
        """
        log.info("Starting backtest simulation")

        # Get date range
        start_date = backtest_data["date"].min()
        end_date = backtest_data["date"].max()

        # Calculate rebalance dates
        rebalance_dates = self._calculate_rebalance_dates(
            start_date=start_date,
            end_date=end_date,
            every_n_days=self.config.rebalance_every_n_days
        )

        log.info(f"Simulating {len(rebalance_dates)} rebalances")

        # Initialize portfolio state
        current_portfolio: dict[str, Decimal] = {}  # {asset_id: size}
        portfolio_value = Decimal("100000")  # Start with 100k
        daily_equity: list[dict] = []
        position_snapshots: list[dict] = []
        num_trades = 0

        # Simulate each rebalancing period
        for i, rebal_date in enumerate(rebalance_dates):
            log.debug(f"Processing rebalance {i+1}/{len(rebalance_dates)} on {rebal_date}")

            # Get predictions for this date
            rebal_predictions = backtest_data.filter(pl.col("date") == rebal_date)

            if len(rebal_predictions) == 0:
                log.warning(f"No predictions for {rebal_date}, skipping")
                continue

            # Select positions
            selected_long, selected_short = self._select_positions_split(
                predictions=rebal_predictions,
                num_long=self.portfolio_config.num_long,
                num_short=self.portfolio_config.num_short
            )

            # Combine for price lookups
            selected = pl.concat([selected_long, selected_short])

            # Calculate target weights using portfolio manager
            target_weights = self._calculate_weights(
                long_predictions=selected_long,
                short_predictions=selected_short,
                account_value=portfolio_value
            )

            # Generate trades
            trades = self._generate_trades(
                current_portfolio=current_portfolio,
                target_weights=target_weights,
                prices=selected
            )

            # Calculate and deduct transaction costs
            costs = self._calculate_transaction_costs(trades)
            portfolio_value -= costs

            # Execute trades (update portfolio)
            for trade in trades:
                # Calculate actual target size from target_value and current price
                price_map = {row["asset_id"]: Decimal(str(row["close"]))
                            for row in selected.iter_rows(named=True)}
                price = price_map.get(trade.coin, trade.reference_price)
                target_size = trade.target_value / price
                current_portfolio[trade.coin] = target_size

            num_trades += len(trades)

            # Save snapshot
            position_snapshots.append({
                "date": rebal_date,
                "num_positions": len([s for s in current_portfolio.values() if s != 0]),
                "portfolio_value": portfolio_value
            })

            # Track daily returns until next rebalance
            next_rebal_date = rebalance_dates[i + 1] if i < len(rebalance_dates) - 1 else end_date

            daily_returns = self._calculate_daily_returns(
                current_portfolio=current_portfolio,
                start_date=rebal_date,
                end_date=next_rebal_date,
                backtest_data=backtest_data
            )

            # Update portfolio value from returns
            for day_data in daily_returns:
                portfolio_value = Decimal(str(day_data["portfolio_value"]))
                daily_equity.append(day_data)

        # Convert to DataFrames
        daily_df = pl.DataFrame(daily_equity) if daily_equity else pl.DataFrame()
        positions_df = pl.DataFrame(position_snapshots) if position_snapshots else pl.DataFrame()

        # Calculate performance metrics
        from cc_flow.core.backtest_performance import PerformanceCalculator
        calculator = PerformanceCalculator()
        metrics = calculator.calculate_metrics(returns=daily_df) if len(daily_df) > 0 else {}

        # Create result
        result = BacktestResult(
            daily_df=daily_df,
            positions_df=positions_df,
            config=self.config,
            total_return=metrics.get("total_return", Decimal("0")),
            cagr=metrics.get("annualized_return", Decimal("0")),
            sharpe_ratio=metrics.get("sharpe_ratio", Decimal("0")),
            sortino_ratio=metrics.get("sortino_ratio", Decimal("0")),
            max_drawdown=metrics.get("max_drawdown", Decimal("0")),
            calmar_ratio=metrics.get("calmar_ratio", Decimal("0")),
            annual_volatility=metrics.get("volatility", Decimal("0")),
            win_rate=metrics.get("win_rate", Decimal("0")),
            avg_turnover=Decimal("0"),  # TODO: Calculate turnover
            num_trades=num_trades,
            num_rebalances=len(rebalance_dates),
            backtest_start=datetime.combine(start_date, datetime.min.time()),
            backtest_end=datetime.combine(end_date, datetime.min.time())
        )

        log.info(f"Backtest complete: Sharpe={result.sharpe_ratio:.2f}, Return={result.total_return:.2%}")
        return result

    def _calculate_rebalance_dates(
        self, start_date: date, end_date: date, every_n_days: int
    ) -> list[date]:
        """Calculate list of rebalancing dates.

        Args:
            start_date: First rebalancing date
            end_date: Last possible rebalancing date
            every_n_days: Days between rebalancing

        Returns:
            List of rebalancing dates

        Example:
            >>> dates = engine._calculate_rebalance_dates(
            ...     date(2024, 1, 1), date(2024, 1, 31), 10
            ... )
            >>> assert len(dates) == 4
        """
        rebalance_dates = []
        current = start_date

        while current <= end_date:
            rebalance_dates.append(current)
            current += timedelta(days=every_n_days)

        return rebalance_dates

    def _select_positions(
        self, predictions: pl.DataFrame, num_long: int, num_short: int
    ) -> pl.DataFrame:
        """Select top long and bottom short positions.

        Args:
            predictions: DataFrame with asset_id, prediction, close
            num_long: Number of long positions to select
            num_short: Number of short positions to select

        Returns:
            DataFrame with selected positions (longs first, then shorts)

        Example:
            >>> selected = engine._select_positions(predictions, 5, 5)
            >>> assert len(selected) <= 10
        """
        sorted_preds = predictions.sort("prediction", descending=True)

        # Get top N for longs
        top_long = sorted_preds.head(num_long)

        # Get bottom N for shorts (lowest predictions)
        top_short = sorted_preds.tail(num_short)

        # Combine
        selected = pl.concat([top_long, top_short])

        return selected

    def _select_positions_split(
        self, predictions: pl.DataFrame, num_long: int, num_short: int
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Select top long and bottom short positions separately.

        Args:
            predictions: DataFrame with asset_id, prediction, close
            num_long: Number of long positions to select
            num_short: Number of short positions to select

        Returns:
            Tuple of (top_long_df, top_short_df)

        Example:
            >>> long, short = engine._select_positions_split(predictions, 5, 5)
            >>> assert len(long) <= 5 and len(short) <= 5
        """
        sorted_preds = predictions.sort("prediction", descending=True)

        # Get top N for longs
        top_long = sorted_preds.head(num_long)

        # Get bottom N for shorts (lowest predictions)
        top_short = sorted_preds.tail(num_short)

        return top_long, top_short

    def _calculate_weights(
        self,
        long_predictions: pl.DataFrame,
        short_predictions: pl.DataFrame,
        account_value: Decimal
    ) -> dict[str, Decimal]:
        """Calculate target weights for selected positions.

        Args:
            long_predictions: DataFrame with long position candidates
            short_predictions: DataFrame with short position candidates
            account_value: Total account value

        Returns:
            Dict mapping asset_id to target weight (positive for long, negative for short)

        Example:
            >>> weights = engine._calculate_weights(long_df, short_df, Decimal("10000"))
            >>> assert sum(abs(w) for w in weights.values()) <= 2.0
        """
        # Combine predictions for portfolio manager
        combined = pl.concat([long_predictions, short_predictions])

        # Use PortfolioManager to calculate weights
        target_positions = self.portfolio_manager.calculate_target_positions(
            predictions=combined,
            account_value=account_value
        )

        # Convert to weights dict
        weights = {}
        for pos in target_positions:
            # Keep sign from target_value
            weight = pos.weight if pos.target_value > 0 else -pos.weight
            weights[pos.coin] = weight

        return weights

    def _generate_trades(
        self,
        current_portfolio: dict[str, Decimal],
        target_weights: dict[str, Decimal],
        prices: pl.DataFrame
    ) -> list[Trade]:
        """Generate trades to reach target weights.

        Args:
            current_portfolio: Current position sizes by asset
            target_weights: Target weights by asset
            prices: DataFrame with asset_id, close prices

        Returns:
            List of Trade objects

        Example:
            >>> trades = engine._generate_trades(portfolio, weights, prices)
            >>> assert all(isinstance(t, Trade) for t in trades)
        """
        trades = []
        price_map = {row["asset_id"]: Decimal(str(row["close"]))
                    for row in prices.iter_rows(named=True)}

        # Calculate target sizes
        for asset_id, weight in target_weights.items():
            price = price_map.get(asset_id)
            if price is None:
                continue

            # Target size based on weight
            # Positive weight = long, negative = short
            target_value = weight * Decimal("100000")  # Simplified: weight * portfolio value
            target_size = target_value / price

            current_size = current_portfolio.get(asset_id, Decimal("0"))
            current_value = current_size * price
            delta_size = target_size - current_size
            delta_value = delta_size * price

            if abs(delta_value) < self.execution_config.min_trade_value:
                continue

            # Determine trade type
            if current_size == 0:
                trade_type = "open"
            elif target_size == 0:
                trade_type = "close"
            elif (current_size > 0 and target_size > 0) or (current_size < 0 and target_size < 0):
                trade_type = "increase" if abs(target_size) > abs(current_size) else "reduce"
            else:
                trade_type = "flip"

            # Calculate fees
            fee_rate = self.config.fee_rate
            estimated_fee = abs(delta_value) * fee_rate

            trade = Trade(
                coin=asset_id,
                side=OrderSide.BUY if delta_size > 0 else OrderSide.SELL,
                size=abs(delta_size),
                reference_price=price,
                current_value=current_value,
                target_value=target_value,
                delta_value=delta_value,
                trade_type=trade_type,
                estimated_fee=estimated_fee,
            )
            trades.append(trade)

        return trades

    def _calculate_transaction_costs(self, trades: list[Trade]) -> Decimal:
        """Calculate total transaction costs for trades.

        Includes both fees and slippage.

        Args:
            trades: List of trades to execute

        Returns:
            Total transaction costs in USD

        Example:
            >>> costs = engine._calculate_transaction_costs(trades)
            >>> assert costs >= 0
        """
        total_costs = Decimal("0")

        for trade in trades:
            # Fee = abs(delta_value) * fee_rate
            fee = abs(trade.delta_value) * self.config.fee_rate

            # Slippage = abs(delta_value) * slippage_bps / 10000
            slippage = abs(trade.delta_value) * self.config.slippage_bps / Decimal("10000")

            total_costs += fee + slippage

        return total_costs

    def _calculate_daily_returns(
        self,
        current_portfolio: dict[str, Decimal],
        start_date: date,
        end_date: date,
        backtest_data: pl.DataFrame
    ) -> list[dict]:
        """Calculate daily returns for current portfolio.

        Args:
            current_portfolio: Current position sizes
            start_date: Start date
            end_date: End date
            backtest_data: Full backtest data with prices

        Returns:
            List of dicts with date, portfolio_value, daily_return

        Example:
            >>> daily = engine._calculate_daily_returns(portfolio, start, end, data)
            >>> assert all("daily_return" in d for d in daily)
        """
        daily_data = []

        # Get prices for date range
        period_data = backtest_data.filter(
            (pl.col("date") >= start_date) & (pl.col("date") <= end_date)
        )

        unique_dates = sorted(period_data["date"].unique().to_list())

        prev_value = None

        for current_date in unique_dates:
            # Get prices for this date
            day_prices = period_data.filter(pl.col("date") == current_date)

            # Calculate portfolio value
            portfolio_value = Decimal("0")
            for asset_id, size in current_portfolio.items():
                if size == 0:
                    continue

                asset_price_data = day_prices.filter(pl.col("asset_id") == asset_id)
                if len(asset_price_data) == 0:
                    continue

                price = Decimal(str(asset_price_data["close"][0]))
                portfolio_value += size * price

            # Calculate daily return
            if prev_value is not None and prev_value != 0:
                daily_return = float((portfolio_value - prev_value) / prev_value)
            else:
                daily_return = 0.0

            daily_data.append({
                "date": current_date,
                "portfolio_value": float(portfolio_value),
                "daily_return": daily_return
            })

            prev_value = portfolio_value

        return daily_data
