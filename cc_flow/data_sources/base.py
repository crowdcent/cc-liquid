"""Base classes for data source integration.

This module defines the abstract interface for loading prediction data from
various sources (CrowdCent, Numerai, local files, etc.).

Design Principles:
    - Abstract base classes define the contract
    - Caching support for performance
    - Standardized output format (Polars DataFrame)
    - Type-safe with full type hints
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

import polars as pl
from pydantic import BaseModel, ConfigDict, Field


class PredictionMetadata(BaseModel):
    """Metadata about prediction data.

    This model captures key information about a prediction dataset
    for tracking, validation, and debugging purposes.

    Attributes:
        source: Name of the data source (e.g., 'crowdcent', 'numerai')
        last_updated: Timestamp of last data refresh (auto-generated if not provided)
        num_predictions: Total number of prediction rows
        date_range: Tuple of (earliest_date, latest_date) as strings
        unique_assets: Number of unique assets in the dataset
        schema_version: Version of the data schema (default: "1.0")
    """

    model_config = ConfigDict(frozen=False)

    source: str
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    num_predictions: int
    date_range: tuple[str, str]  # (min_date, max_date)
    unique_assets: int
    schema_version: str = "1.0"


class DataSource(ABC):
    """Abstract base class for prediction data sources.

    All data sources must implement this interface to ensure consistent
    behavior across different prediction providers.

    The contract requires:
        1. load_predictions() - Return standardized DataFrame
        2. get_metadata() - Provide data source metadata
        3. validate_schema() - Verify DataFrame structure

    Example:
        ```python
        class MyDataSource(DataSource):
            async def load_predictions(self) -> pl.DataFrame:
                # Load data from source
                return df

            async def get_metadata(self) -> PredictionMetadata:
                # Return metadata
                return PredictionMetadata(...)

            async def validate_schema(self, df: pl.DataFrame) -> bool:
                # Validate schema
                return True
        ```
    """

    @abstractmethod
    async def load_predictions(self) -> pl.DataFrame:
        """Load predictions as polars DataFrame.

        The returned DataFrame must contain at minimum:
            - date: Date of the prediction
            - asset_id: Unique identifier for the asset
            - prediction: Predicted value (typically between -1 and 1)

        Returns:
            DataFrame with required columns and optional additional columns

        Raises:
            ValueError: If data cannot be loaded or is invalid
            ConnectionError: If remote data source is unreachable
        """
        ...

    @abstractmethod
    async def get_metadata(self) -> PredictionMetadata:
        """Get metadata about the data source.

        This should return information about the current state of the
        data source, including when it was last updated, how many
        predictions it contains, etc.

        Returns:
            PredictionMetadata with current source information

        Raises:
            ValueError: If metadata cannot be determined
        """
        ...

    @abstractmethod
    async def validate_schema(self, df: pl.DataFrame) -> bool:
        """Validate DataFrame has required schema.

        Implementations should check that the DataFrame contains
        all required columns and that data types are correct.

        Args:
            df: DataFrame to validate

        Returns:
            True if schema is valid

        Raises:
            ValueError: If schema is invalid (with details about what's wrong)
        """
        ...


class CachedDataSource(DataSource):
    """Base class with caching support.

    This class provides automatic caching of prediction data to avoid
    repeated expensive data loading operations. Subclasses only need
    to implement _load_predictions_impl() instead of load_predictions().

    The caching logic:
        1. On first load, calls _load_predictions_impl() and caches result
        2. Subsequent loads return cached data if within TTL
        3. After TTL expires, reloads data and updates cache

    Attributes:
        cache_ttl: Cache time-to-live in seconds (default: 3600 = 1 hour)

    Example:
        ```python
        class MyCachedSource(CachedDataSource):
            def __init__(self):
                super().__init__(cache_ttl=1800)  # 30 minutes

            async def _load_predictions_impl(self) -> pl.DataFrame:
                # Expensive data loading operation
                return load_from_api()

            async def get_metadata(self) -> PredictionMetadata:
                df = await self.load_predictions()  # Uses cache!
                return PredictionMetadata(...)
        ```
    """

    def __init__(self, cache_ttl: int = 3600):
        """Initialize with cache TTL in seconds.

        Args:
            cache_ttl: Cache time-to-live in seconds (default: 3600)
        """
        self.cache_ttl = cache_ttl
        self._cache: pl.DataFrame | None = None
        self._cache_time: datetime | None = None

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid.

        Cache is valid if:
            1. Cache exists (_cache is not None)
            2. Cache time exists (_cache_time is not None)
            3. Elapsed time since cache < cache_ttl

        Returns:
            True if cache is valid, False otherwise
        """
        if self._cache is None or self._cache_time is None:
            return False

        elapsed = (datetime.now(UTC) - self._cache_time).total_seconds()
        return elapsed < self.cache_ttl

    async def load_predictions(self) -> pl.DataFrame:
        """Load predictions with caching.

        This method checks the cache first and only calls the
        subclass implementation if cache is invalid or expired.

        Returns:
            DataFrame with predictions (from cache or fresh load)

        Raises:
            ValueError: If data cannot be loaded
            ConnectionError: If remote source is unreachable
        """
        if self._is_cache_valid():
            return self._cache  # type: ignore

        # Call subclass implementation
        df = await self._load_predictions_impl()

        # Cache result
        self._cache = df
        self._cache_time = datetime.now(UTC)

        return df

    @abstractmethod
    async def _load_predictions_impl(self) -> pl.DataFrame:
        """Subclass implements actual loading logic.

        This method should perform the actual data loading operation
        without worrying about caching - that's handled by load_predictions().

        Returns:
            DataFrame with predictions

        Raises:
            ValueError: If data cannot be loaded
            ConnectionError: If remote source is unreachable
        """
        ...

    async def validate_schema(self, df: pl.DataFrame) -> bool:
        """Default schema validation.

        Validates that the DataFrame contains the three required columns:
            - date
            - asset_id
            - prediction

        Additional columns are allowed. Subclasses can override this
        to add more specific validation logic.

        Args:
            df: DataFrame to validate

        Returns:
            True if schema is valid

        Raises:
            ValueError: If required columns are missing
        """
        required_columns = {"date", "asset_id", "prediction"}

        if not required_columns.issubset(set(df.columns)):
            missing = required_columns - set(df.columns)
            raise ValueError(f"Missing required columns: {missing}")

        return True
