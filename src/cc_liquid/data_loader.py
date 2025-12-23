"""Data loading and abstraction for cc-liquid."""

from abc import ABC, abstractmethod

import polars as pl


class DataSource(ABC):
    """Abstract base class for data sources."""

    @abstractmethod
    def load(self) -> pl.DataFrame:
        """Load data into a Polars DataFrame."""
        pass


class FileDataSource(DataSource):
    """Loads prediction data from a Parquet or CSV file."""

    def __init__(
        self,
        path: str,
        date_column: str,
        asset_id_column: str,
        prediction_column: str,
    ):
        self.path = path
        self.date_column = date_column
        self.asset_id_column = asset_id_column
        self.prediction_column = prediction_column

    def load(self) -> pl.DataFrame:
        """Loads data from the file."""
        if self.path.endswith(".parquet"):
            df = pl.read_parquet(self.path)
        elif self.path.endswith(".csv"):
            df = pl.read_csv(self.path)
        else:
            raise ValueError("Unsupported file type. Use .parquet or .csv.")

        return df


class DataFrameDataSource(DataSource):
    """Uses an existing Polars DataFrame as the data source."""

    def __init__(
        self,
        df: pl.DataFrame,
        date_column: str,
        asset_id_column: str,
        prediction_column: str,
    ):
        self.df = df
        self.date_column = date_column
        self.asset_id_column = asset_id_column
        self.prediction_column = prediction_column

    def load(self) -> pl.DataFrame:
        """Returns the existing DataFrame."""
        return self.df


class DataLoader:
    """Factory for creating data sources."""

    @staticmethod
    def from_file(path: str, date_col: str, id_col: str, pred_col: str) -> pl.DataFrame:
        """Create a file data source and load data."""
        return FileDataSource(
            path,
            date_column=date_col,
            asset_id_column=id_col,
            prediction_column=pred_col,
        ).load()

    @staticmethod
    def from_dataframe(
        df: pl.DataFrame, date_col: str, id_col: str, pred_col: str
    ) -> pl.DataFrame:
        """Create a DataFrame data source and load data."""
        return DataFrameDataSource(
            df,
            date_column=date_col,
            asset_id_column=id_col,
            prediction_column=pred_col,
        ).load()

    @staticmethod
    def from_crowdcent_api(
        api_key: str | None = None,
        challenge_slug: str = "hyperliquid-ranking",
        download_path: str | None = None,
        date_col: str = "release_date",
        id_col: str = "id",
        pred_col: str = "pred_30d",
    ) -> pl.DataFrame:
        """
        Download and load the CrowdCent meta model.

        Args:
            api_key: CrowdCent API key (if None, will try to load from env)
            challenge_slug: The challenge to download data for
            download_path: Optional path to save the downloaded file
            date_col: Date column name in the meta model
            id_col: Asset ID column name in the meta model
            pred_col: Prediction column name to use from the meta model

        Returns:
            Polars DataFrame with original column names
        """
        from crowdcent_challenge import ChallengeClient

        if api_key is None:
            import os

            api_key = os.getenv("CROWDCENT_API_KEY")
            if not api_key:
                raise ValueError("CROWDCENT_API_KEY not found in environment variables")

        client = ChallengeClient(challenge_slug=challenge_slug, api_key=api_key)

        if download_path is None:
            download_path = "predictions.parquet"

        client.download_meta_model(download_path)

        return DataLoader.from_file(
            path=download_path, date_col=date_col, id_col=id_col, pred_col=pred_col
        )

    @staticmethod
    def from_numerai_api(
        download_path: str | None = None,
        date_col: str = "date",
        id_col: str = "symbol",
        pred_col: str = "prediction",
    ) -> pl.DataFrame:
        """
        Download and load the Numerai crypto meta model.

        Args:
            download_path: Optional path to save the downloaded file
            date_col: Date column name in the meta model
            id_col: Asset ID/symbol column name in the meta model
            pred_col: Prediction column name to use from the meta model

        Returns:
            Polars DataFrame with original column names
        """
        try:
            from numerapi import CryptoAPI
        except ImportError:
            raise ImportError(
                "numerapi is required. Install with: uv add cc-liquid[numerai]"
            )

        api = CryptoAPI()

        if download_path is None:
            download_path = "predictions.parquet"

        api.download_dataset("v2.0/historical_meta_models.parquet", download_path)

        return DataLoader.from_file(
            path=download_path, date_col=date_col, id_col=id_col, pred_col=pred_col
        )
