"""Mock data source for testing.

This module provides MockDataSource, a configurable test data source that can
either return pre-made prediction DataFrames or generate synthetic data.

Key Features:
    - Custom test data support for specific scenarios
    - Synthetic data generation with configurable parameters
    - Deterministic behavior for repeatable tests
    - Full compliance with DataSource interface

Design Principles:
    - Simple and predictable behavior
    - Highly configurable for different test scenarios
    - Type-safe with full type hints
    - No external dependencies (pure generation)
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import polars as pl

from cc_flow.data_sources.base import DataSource, PredictionMetadata


class MockDataSource(DataSource):
    """Mock data source for testing purposes.

    This data source can operate in two modes:
        1. Custom mode: Return a pre-made DataFrame provided at initialization
        2. Synthetic mode: Generate random prediction data with configurable parameters

    The synthetic generation creates:
        - Dates: Last N days from today (in reverse chronological order)
        - Assets: Named ASSET00, ASSET01, etc.
        - Predictions: Random values within specified range
        - Complete coverage: Every asset has data for every date

    Attributes:
        _predictions: Optional pre-made predictions DataFrame
        num_assets: Number of assets to generate (synthetic mode)
        num_dates: Number of dates to generate (synthetic mode)
        prediction_range: (min, max) tuple for random prediction values

    Example:
        ```python
        # Custom test data
        test_df = pl.DataFrame({
            "date": ["2025-01-01"],
            "asset_id": ["BTC"],
            "prediction": [0.8]
        })
        source = MockDataSource(predictions=test_df)

        # Synthetic data
        source = MockDataSource(
            num_assets=50,
            num_dates=30,
            prediction_range=(-1.0, 1.0)
        )
        df = await source.load_predictions()
        ```
    """

    def __init__(
        self,
        predictions: pl.DataFrame | None = None,
        num_assets: int = 20,
        num_dates: int = 10,
        prediction_range: tuple[float, float] = (0.0, 1.0),
    ):
        """Initialize mock data source.

        Args:
            predictions: Optional pre-made predictions DataFrame.
                If provided, synthetic generation is skipped and this data
                is returned directly.
            num_assets: Number of assets to generate in synthetic mode.
                Ignored if predictions is provided.
            num_dates: Number of dates to generate in synthetic mode.
                Ignored if predictions is provided.
            prediction_range: (min, max) tuple for random prediction values.
                Only used in synthetic mode.

        Example:
            ```python
            # Use custom data
            custom_df = pl.DataFrame(...)
            source = MockDataSource(predictions=custom_df)

            # Generate 100 assets over 30 days with predictions in [-1, 1]
            source = MockDataSource(
                num_assets=100,
                num_dates=30,
                prediction_range=(-1.0, 1.0)
            )
            ```
        """
        self._predictions = predictions
        self.num_assets = num_assets
        self.num_dates = num_dates
        self.prediction_range = prediction_range

    async def load_predictions(self) -> pl.DataFrame:
        """Load mock predictions.

        Returns either the custom DataFrame provided at initialization,
        or generates synthetic data based on configured parameters.

        Returns:
            DataFrame with columns: date, asset_id, prediction

        Raises:
            ValueError: If synthetic generation fails (should not happen
                with valid parameters)
        """
        if self._predictions is not None:
            return self._predictions

        # Generate synthetic predictions
        return self._generate_predictions()

    def _generate_predictions(self) -> pl.DataFrame:
        """Generate synthetic prediction data.

        Creates a DataFrame with:
            - Dates: Last num_dates days (most recent first when reversed)
            - Assets: ASSET00, ASSET01, ..., ASSET{num_assets-1}
            - Predictions: Random values in prediction_range
            - Complete coverage: Every asset appears for every date

        Returns:
            DataFrame with synthetic predictions

        Implementation Notes:
            - Uses random.uniform for prediction generation
            - Dates are generated backwards from today
            - Asset IDs use zero-padded formatting (ASSET00, not ASSET0)
            - Result has num_assets * num_dates rows
        """
        dates = []
        assets = []
        predictions = []

        # Generate dates (last N days, in chronological order)
        base_date = datetime.now(UTC).date()
        date_list = [str(base_date - timedelta(days=i)) for i in range(self.num_dates)][
            ::-1
        ]  # Reverse to get chronological order

        # Generate asset IDs with zero-padding
        asset_list = [f"ASSET{i:02d}" for i in range(self.num_assets)]

        # Generate predictions for each date/asset combination
        for date in date_list:
            for asset in asset_list:
                dates.append(date)
                assets.append(asset)
                pred = random.uniform(*self.prediction_range)
                predictions.append(pred)

        df = pl.DataFrame({"date": dates, "asset_id": assets, "prediction": predictions})

        return df

    async def get_metadata(self) -> PredictionMetadata:
        """Get metadata for mock data.

        Loads the predictions (either custom or synthetic) and extracts
        metadata including row count, date range, and unique asset count.

        Returns:
            PredictionMetadata with:
                - source: "mock"
                - num_predictions: Total row count
                - date_range: (earliest_date, latest_date)
                - unique_assets: Count of unique asset_id values
                - last_updated: Current timestamp
                - schema_version: "1.0"

        Raises:
            ValueError: If predictions cannot be loaded
        """
        df = await self.load_predictions()

        return PredictionMetadata(
            source="mock",
            num_predictions=len(df),
            date_range=(str(df["date"].min()), str(df["date"].max())),
            unique_assets=df["asset_id"].n_unique(),
        )

    async def validate_schema(self, df: pl.DataFrame) -> bool:
        """Validate mock data schema.

        Checks that the DataFrame contains the three required columns:
            - date
            - asset_id
            - prediction

        Additional columns are allowed. This method does not validate
        data types or value ranges.

        Args:
            df: DataFrame to validate

        Returns:
            True if schema is valid

        Raises:
            ValueError: If required columns are missing, with message
                indicating which columns are missing
        """
        required_columns = {"date", "asset_id", "prediction"}

        if not required_columns.issubset(set(df.columns)):
            missing = required_columns - set(df.columns)
            raise ValueError(f"Missing required columns: {missing}")

        return True
