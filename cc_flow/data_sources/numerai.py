"""Numerai data source integration.

This module provides integration with the Numerai Signals API to download
crypto meta model predictions.

Design Principles:
    - Extends CachedDataSource for automatic caching
    - Standardizes Numerai column names to common format
    - Type-safe with full type hints
    - Handles API errors gracefully

Example:
    ```python
    from cc_flow.data_sources.numerai import NumeraiDataSource

    # Initialize with default settings
    source = NumeraiDataSource()

    # Load predictions
    df = await source.load_predictions()

    # Get metadata
    metadata = await source.get_metadata()
    print(f"Loaded {metadata.num_predictions} predictions")
    ```
"""

from __future__ import annotations

import polars as pl
import requests

from cc_flow.data_sources.base import CachedDataSource, PredictionMetadata


class NumeraiDataSource(CachedDataSource):
    """Data source that loads crypto signals from Numerai Signals API.

    This class downloads the crypto meta model predictions from Numerai's
    GraphQL API and standardizes the column names to match the common
    prediction format.

    Numerai Column Mapping:
        - symbol -> asset_id
        - meta_model -> prediction
        - date -> date (no change)

    Attributes:
        api_url: Numerai API endpoint URL
        cache_ttl: Cache time-to-live in seconds (default: 3600)

    Example:
        ```python
        # Default settings (1 hour cache)
        source = NumeraiDataSource()

        # Custom cache TTL (30 minutes)
        source = NumeraiDataSource(cache_ttl=1800)

        # Load predictions with automatic caching
        predictions = await source.load_predictions()

        # Predictions are cached for the specified TTL
        cached_predictions = await source.load_predictions()  # Uses cache
        ```
    """

    def __init__(self, cache_ttl: int = 3600):
        """Initialize Numerai data source.

        Args:
            cache_ttl: Cache TTL in seconds (default: 3600)

        Example:
            ```python
            # Default cache (1 hour)
            source = NumeraiDataSource()

            # Custom cache (30 minutes)
            source = NumeraiDataSource(cache_ttl=1800)
            ```
        """
        super().__init__(cache_ttl)
        self.api_url = "https://api-tournament.numer.ai"

    async def _load_predictions_impl(self) -> pl.DataFrame:
        """Load predictions from Numerai Signals API.

        This method queries the Numerai GraphQL API for crypto meta model
        predictions, renames columns to the standard format, and validates
        the schema.

        Returns:
            DataFrame with columns: date, asset_id, prediction

        Raises:
            ValueError: If API returns error or data is invalid
            requests.exceptions.Timeout: If API request times out
            requests.exceptions.ConnectionError: If connection fails

        Note:
            The requests library is synchronous. For async support,
            this could be wrapped with asyncio.to_thread() in the future.
        """
        # Download crypto meta model from Numerai
        df = await self._fetch_crypto_signals()

        # Standardize column names
        # Numerai columns: date, symbol, meta_model
        # Standard columns: date, asset_id, prediction
        df = df.rename({
            "symbol": "asset_id",
            "meta_model": "prediction",
        })

        # Validate schema
        await self.validate_schema(df)

        return df

    async def _fetch_crypto_signals(self) -> pl.DataFrame:
        """Fetch crypto signals from Numerai API.

        This method uses GraphQL to query the cryptoMetaModel endpoint
        which provides daily crypto predictions.

        Returns:
            DataFrame with Numerai's original column names

        Raises:
            ValueError: If API returns error, invalid data, or empty response
            requests.exceptions.Timeout: If API request times out
            requests.exceptions.ConnectionError: If connection fails

        Note:
            The requests library is synchronous. We call it directly for now,
            but this could be wrapped with asyncio.to_thread() if blocking
            becomes an issue.
        """
        # GraphQL query for crypto signals
        query = """
        query {
          cryptoMetaModel {
            date
            symbol
            meta_model
          }
        }
        """

        # Call Numerai API
        response = requests.post(
            f"{self.api_url}/graphql",
            json={"query": query},
            timeout=30,
        )

        # Check HTTP status
        if response.status_code != 200:
            raise ValueError(f"Numerai API error: {response.status_code}")

        # Parse JSON response
        data = response.json()

        # Check for GraphQL errors
        if "errors" in data:
            raise ValueError(f"Numerai API errors: {data['errors']}")

        # Extract crypto signals
        signals = data["data"]["cryptoMetaModel"]

        # Check for empty response
        if not signals:
            raise ValueError("No crypto signals returned from Numerai")

        # Convert to DataFrame
        df = pl.DataFrame(signals)

        return df

    async def get_metadata(self) -> PredictionMetadata:
        """Get metadata about the Numerai data.

        This method loads the predictions (using cache if available)
        and generates metadata including source information, date range,
        and dataset statistics.

        Returns:
            PredictionMetadata with current source information

        Raises:
            ValueError: If predictions cannot be loaded
            requests.exceptions.Timeout: If API request times out
            requests.exceptions.ConnectionError: If connection fails

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

        return PredictionMetadata(
            source="numerai:crypto",
            num_predictions=len(df),
            date_range=(str(df["date"].min()), str(df["date"].max())),
            unique_assets=df["asset_id"].n_unique(),
        )
