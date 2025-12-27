"""
Data source integrations for cc-flow.

This module provides integrations with prediction data sources such as
CrowdCent, Numerai, and local file sources.

Architecture:
    - Base data source interface (Protocol/ABC)
    - Source-specific implementations
    - Unified prediction data format using Polars DataFrames

Implementations:
    - CrowdCent: Metamodel predictions from CrowdCent API
    - Numerai: Metamodel predictions from Numerai API
    - LocalFile: Parquet/CSV file predictions
    - Future: Custom APIs, databases, etc.

Design Principles:
    - Lazy loading of data
    - Caching for performance
    - Standardized output format
"""

from cc_flow.data_sources.base import (
    CachedDataSource,
    DataSource,
    PredictionMetadata,
)
from cc_flow.data_sources.crowdcent import CrowdCentDataSource
from cc_flow.data_sources.local import LocalFileDataSource
from cc_flow.data_sources.mock import MockDataSource
from cc_flow.data_sources.numerai import NumeraiDataSource

__all__ = [
    "DataSource",
    "CachedDataSource",
    "PredictionMetadata",
    "LocalFileDataSource",
    "CrowdCentDataSource",
    "NumeraiDataSource",
    "MockDataSource",
]
