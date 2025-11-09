"""CrowdCent data source integration.

This module provides integration with the CrowdCent API to download
prediction data for the Hyperliquid challenge.

Design Principles:
    - Extends CachedDataSource for automatic caching
    - Standardizes CrowdCent column names to common format
    - Type-safe with full type hints
    - Handles API errors gracefully

Example:
    ```python
    from cc_flow.data_sources.crowdcent import CrowdCentDataSource

    # Initialize with API key
    source = CrowdCentDataSource(api_key="your_api_key")

    # Load predictions
    df = await source.load_predictions()

    # Get metadata
    metadata = await source.get_metadata()
    print(f"Loaded {metadata.num_predictions} predictions")
    ```
"""

from __future__ import annotations

from io import BytesIO

import polars as pl
from crowdcent_challenge import ChallengeClient

from cc_flow.data_sources.base import CachedDataSource, PredictionMetadata


class CrowdCentDataSource(CachedDataSource):
    """Data source that loads predictions from CrowdCent API.

    This class downloads the meta model predictions from CrowdCent's
    Hyperliquid ranking challenge and standardizes the column names
    to match the common prediction format.

    CrowdCent Column Mapping:
        - release_date -> date
        - id -> asset_id
        - pred_10d -> prediction

    Attributes:
        api_key: CrowdCent API key for authentication
        challenge_slug: Challenge identifier (default: "hyperliquid-ranking")
        cache_ttl: Cache time-to-live in seconds (default: 3600)
        client: ChallengeClient API client instance

    Example:
        ```python
        source = CrowdCentDataSource(
            api_key="your_api_key",
            challenge_slug="hyperliquid-ranking",
            cache_ttl=1800  # 30 minutes
        )

        # Load predictions with automatic caching
        predictions = await source.load_predictions()

        # Predictions are cached for 30 minutes
        cached_predictions = await source.load_predictions()  # Uses cache
        ```
    """

    def __init__(
        self,
        api_key: str,
        challenge_slug: str = "hyperliquid-ranking",
        cache_ttl: int = 3600,
    ):
        """Initialize CrowdCent data source.

        Args:
            api_key: CrowdCent API key for authentication
            challenge_slug: Challenge identifier (default: "hyperliquid-ranking")
            cache_ttl: Cache TTL in seconds (default: 3600)

        Example:
            ```python
            # Default settings
            source = CrowdCentDataSource(api_key="your_key")

            # Custom challenge and cache
            source = CrowdCentDataSource(
                api_key="your_key",
                challenge_slug="custom-challenge",
                cache_ttl=1800
            )
            ```
        """
        super().__init__(cache_ttl)
        self.api_key = api_key
        self.challenge_slug = challenge_slug
        self.client = ChallengeClient(api_key)

    async def _load_predictions_impl(self) -> pl.DataFrame:
        """Load predictions from CrowdCent API.

        This method downloads the meta model from CrowdCent, renames
        columns to the standard format, and validates the schema.

        Returns:
            DataFrame with columns: date, asset_id, prediction

        Raises:
            Exception: If API call fails or data is invalid
            ValueError: If schema validation fails

        Note:
            The ChallengeClient library is synchronous, so we call
            it directly. For async support, this could be wrapped with
            asyncio.to_thread() in the future.
        """
        # Download meta model from CrowdCent
        # The client returns BytesIO containing parquet data
        df = await self._fetch_meta_model()

        # Standardize column names
        # CrowdCent columns: release_date, id, pred_10d
        # Standard columns: date, asset_id, prediction
        df = df.rename({
            "release_date": "date",
            "id": "asset_id",
            "pred_10d": "prediction",
        })

        # Validate schema
        await self.validate_schema(df)

        return df

    async def _fetch_meta_model(self) -> pl.DataFrame:
        """Fetch meta model from CrowdCent API.

        This is separated into its own method for easier testing
        and potential future async wrapper implementation.

        Returns:
            DataFrame with CrowdCent's original column names

        Raises:
            Exception: If API call fails

        Note:
            The crowdcent-challenge library is synchronous.
            We call it directly for now, but this could be wrapped
            with asyncio.to_thread() if blocking becomes an issue.
        """
        # crowdcent-challenge library is synchronous
        # Call directly (can be wrapped in asyncio.to_thread if needed)
        parquet_data: BytesIO = self.client.download_meta_model(self.challenge_slug)
        df = pl.read_parquet(parquet_data)
        return df

    async def get_metadata(self) -> PredictionMetadata:
        """Get metadata about the CrowdCent data.

        This method loads the predictions (using cache if available)
        and generates metadata including source information, date range,
        and dataset statistics.

        Returns:
            PredictionMetadata with current source information

        Raises:
            Exception: If predictions cannot be loaded

        Example:
            ```python
            metadata = await source.get_metadata()
            print(f"Source: {metadata.source}")
            print(f"Predictions: {metadata.num_predictions}")
            print(f"Date range: {metadata.date_range}")
            print(f"Unique assets: {metadata.unique_assets}")
            ```
        """
        df = await self.load_predictions()

        # Handle empty dataframe
        if len(df) == 0:
            return PredictionMetadata(
                source=f"crowdcent:{self.challenge_slug}",
                num_predictions=0,
                date_range=("", ""),
                unique_assets=0,
            )

        return PredictionMetadata(
            source=f"crowdcent:{self.challenge_slug}",
            num_predictions=len(df),
            date_range=(str(df["date"].min()), str(df["date"].max())),
            unique_assets=df["asset_id"].n_unique(),
        )
