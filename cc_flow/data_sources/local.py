"""Local file data source implementation.

This module provides a data source that loads predictions from local parquet
or CSV files with configurable column mappings.

Design Principles:
    - Supports both parquet and CSV formats
    - Flexible column mapping for different data schemas
    - Inherits caching from CachedDataSource
    - Type-safe with full type hints
    - Comprehensive error handling

Example:
    ```python
    # Load with custom column names
    source = LocalFileDataSource(
        file_path="predictions.parquet",
        date_column="trading_date",
        asset_id_column="symbol",
        prediction_column="score"
    )

    df = await source.load_predictions()
    metadata = await source.get_metadata()
    ```
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from cc_flow.data_sources.base import CachedDataSource, PredictionMetadata


class LocalFileDataSource(CachedDataSource):
    """Data source from local parquet or CSV files.

    This class loads prediction data from local files and handles column
    renaming to standardize the output format. It supports both parquet
    and CSV file formats.

    The data source will:
        1. Load data from the specified file
        2. Rename columns to standard names (date, asset_id, prediction)
        3. Validate the schema has required columns
        4. Cache results for performance

    Attributes:
        file_path: Path to parquet or CSV file
        date_column: Name of date column in source file
        asset_id_column: Name of asset ID column in source file
        prediction_column: Name of prediction column in source file
        cache_ttl: Cache time-to-live in seconds (default: 3600)

    Raises:
        FileNotFoundError: If the specified file doesn't exist
        ValueError: If file type is unsupported or schema is invalid
    """

    def __init__(
        self,
        file_path: str | Path,
        date_column: str = "date",
        asset_id_column: str = "asset_id",
        prediction_column: str = "prediction",
        cache_ttl: int = 3600,
    ):
        """Initialize local file data source.

        Args:
            file_path: Path to parquet or CSV file
            date_column: Name of date column (default: "date")
            asset_id_column: Name of asset ID column (default: "asset_id")
            prediction_column: Name of prediction column (default: "prediction")
            cache_ttl: Cache time-to-live in seconds (default: 3600)

        Raises:
            FileNotFoundError: If file_path doesn't exist
        """
        super().__init__(cache_ttl)
        self.file_path = Path(file_path)
        self.date_column = date_column
        self.asset_id_column = asset_id_column
        self.prediction_column = prediction_column

        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

    async def _load_predictions_impl(self) -> pl.DataFrame:
        """Load predictions from local file.

        This method:
            1. Determines file type from extension
            2. Loads data using appropriate polars reader
            3. Renames columns to standard format
            4. Validates schema

        Returns:
            DataFrame with standardized column names

        Raises:
            ValueError: If file type is unsupported or schema is invalid
        """
        # Determine file type and load
        if self.file_path.suffix == ".parquet":
            df = pl.read_parquet(self.file_path)
        elif self.file_path.suffix == ".csv":
            df = pl.read_csv(self.file_path)
        else:
            raise ValueError(
                f"Unsupported file type: {self.file_path.suffix}. "
                "Supported types: .parquet, .csv"
            )

        # Rename columns to standard names
        # Only rename if the column name is different from standard
        rename_mapping = {}
        if self.date_column != "date" and self.date_column in df.columns:
            rename_mapping[self.date_column] = "date"
        if (
            self.asset_id_column != "asset_id"
            and self.asset_id_column in df.columns
        ):
            rename_mapping[self.asset_id_column] = "asset_id"
        if (
            self.prediction_column != "prediction"
            and self.prediction_column in df.columns
        ):
            rename_mapping[self.prediction_column] = "prediction"

        if rename_mapping:
            df = df.rename(rename_mapping)

        # Validate schema
        await self.validate_schema(df)

        return df

    async def get_metadata(self) -> PredictionMetadata:
        """Get metadata from loaded data.

        Loads the predictions (using cache if available) and generates
        metadata including date range, number of predictions, and unique assets.

        Returns:
            PredictionMetadata with current file information

        Raises:
            ValueError: If data cannot be loaded or is invalid
        """
        df = await self.load_predictions()

        return PredictionMetadata(
            source=f"local:{self.file_path.name}",
            num_predictions=len(df),
            date_range=(str(df["date"].min()), str(df["date"].max())),
            unique_assets=df["asset_id"].n_unique(),
        )
