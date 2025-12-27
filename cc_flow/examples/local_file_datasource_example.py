"""Example usage of LocalFileDataSource.

This example demonstrates how to use the LocalFileDataSource to load
predictions from local parquet or CSV files with custom column mappings.

Run this example with:
    PYTHONPATH=/home/ling/workarea/numerai/cc-liquid:$PYTHONPATH uv run python cc_flow/examples/local_file_datasource_example.py

Or from the project root:
    PYTHONPATH=.:$PYTHONPATH uv run python cc_flow/examples/local_file_datasource_example.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import polars as pl
from cc_flow.data_sources.local import LocalFileDataSource


async def example_standard_format():
    """Example 1: Load file with standard column names."""
    print("=" * 70)
    print("Example 1: Loading file with standard column names")
    print("=" * 70)

    # Path to test fixture (in a real scenario, use your actual data file)
    fixtures_dir = Path(__file__).parent.parent.parent / "tests" / "fixtures"
    file_path = fixtures_dir / "standard_predictions.parquet"

    # Create data source with default column names
    source = LocalFileDataSource(file_path=str(file_path))

    # Load predictions
    df = await source.load_predictions()
    print(f"\nLoaded {len(df)} predictions")
    print(f"Columns: {df.columns}")
    print("\nFirst 5 rows:")
    print(df.head(5))

    # Get metadata
    metadata = await source.get_metadata()
    print("\nMetadata:")
    print(f"  Source: {metadata.source}")
    print(f"  Number of predictions: {metadata.num_predictions}")
    print(f"  Date range: {metadata.date_range}")
    print(f"  Unique assets: {metadata.unique_assets}")
    print(f"  Last updated: {metadata.last_updated}")


async def example_custom_column_names():
    """Example 2: Load file with custom column names."""
    print("\n" + "=" * 70)
    print("Example 2: Loading file with custom column names")
    print("=" * 70)

    # Path to test fixture with custom column names
    fixtures_dir = Path(__file__).parent.parent.parent / "tests" / "fixtures"
    file_path = fixtures_dir / "sample_predictions.parquet"

    # Create data source with custom column mapping
    source = LocalFileDataSource(
        file_path=str(file_path),
        date_column="trading_date",  # Map 'trading_date' -> 'date'
        asset_id_column="symbol",  # Map 'symbol' -> 'asset_id'
        prediction_column="score",  # Map 'score' -> 'prediction'
    )

    # Load predictions (columns will be renamed automatically)
    df = await source.load_predictions()
    print(f"\nLoaded {len(df)} predictions")
    print(f"Columns: {df.columns}")
    print("\nFirst 5 rows:")
    print(df.head(5))

    # Get metadata
    metadata = await source.get_metadata()
    print("\nMetadata:")
    print(f"  Source: {metadata.source}")
    print(f"  Number of predictions: {metadata.num_predictions}")
    print(f"  Date range: {metadata.date_range}")
    print(f"  Unique assets: {metadata.unique_assets}")


async def example_csv_file():
    """Example 3: Load CSV file instead of parquet."""
    print("\n" + "=" * 70)
    print("Example 3: Loading CSV file")
    print("=" * 70)

    # Path to CSV fixture
    fixtures_dir = Path(__file__).parent.parent.parent / "tests" / "fixtures"
    file_path = fixtures_dir / "sample_predictions.csv"

    # Create data source (works the same for CSV as parquet)
    source = LocalFileDataSource(
        file_path=str(file_path),
        date_column="trading_date",
        asset_id_column="symbol",
        prediction_column="score",
    )

    # Load predictions
    df = await source.load_predictions()
    print(f"\nLoaded {len(df)} predictions from CSV")
    print(f"Columns: {df.columns}")
    print("\nFirst 3 rows:")
    print(df.head(3))


async def example_caching():
    """Example 4: Demonstrate caching behavior."""
    print("\n" + "=" * 70)
    print("Example 4: Demonstrating caching")
    print("=" * 70)

    fixtures_dir = Path(__file__).parent.parent.parent / "tests" / "fixtures"
    file_path = fixtures_dir / "standard_predictions.parquet"

    # Create source with custom cache TTL (5 minutes)
    source = LocalFileDataSource(file_path=str(file_path), cache_ttl=300)

    # First load - reads from file
    print("\nFirst load (from file)...")
    df1 = await source.load_predictions()
    print(f"Loaded {len(df1)} rows")

    # Second load - returns cached data
    print("\nSecond load (from cache)...")
    df2 = await source.load_predictions()
    print(f"Loaded {len(df2)} rows (same instance: {df1 is df2})")

    # Metadata also uses cached data
    print("\nGetting metadata (uses cache)...")
    metadata = await source.get_metadata()
    print(f"  Number of predictions: {metadata.num_predictions}")


async def example_filtering_and_analysis():
    """Example 5: Load data and perform analysis."""
    print("\n" + "=" * 70)
    print("Example 5: Filtering and analysis")
    print("=" * 70)

    fixtures_dir = Path(__file__).parent.parent.parent / "tests" / "fixtures"
    file_path = fixtures_dir / "standard_predictions.parquet"

    source = LocalFileDataSource(file_path=str(file_path))
    df = await source.load_predictions()

    # Get predictions for a specific date
    specific_date = "2024-01-15"
    daily_preds = df.filter(pl.col("date").cast(str) == specific_date)
    print(f"\nPredictions for {specific_date}: {len(daily_preds)} assets")

    # Get top 5 long positions (highest predictions)
    top_longs = df.sort("prediction", descending=True).head(5)
    print("\nTop 5 long positions:")
    print(top_longs.select(["date", "asset_id", "prediction"]))

    # Get bottom 5 short positions (lowest predictions)
    top_shorts = df.sort("prediction", descending=False).head(5)
    print("\nTop 5 short positions:")
    print(top_shorts.select(["date", "asset_id", "prediction"]))

    # Calculate statistics
    print("\nPrediction statistics:")
    print(f"  Mean: {df['prediction'].mean():.4f}")
    print(f"  Std: {df['prediction'].std():.4f}")
    print(f"  Min: {df['prediction'].min():.4f}")
    print(f"  Max: {df['prediction'].max():.4f}")


async def example_error_handling():
    """Example 6: Demonstrate error handling."""
    print("\n" + "=" * 70)
    print("Example 6: Error handling")
    print("=" * 70)

    # Try to load nonexistent file
    print("\nTrying to load nonexistent file...")
    try:
        source = LocalFileDataSource(file_path="/nonexistent/file.parquet")
    except FileNotFoundError as e:
        print(f"  ✓ Caught expected error: {e}")

    # Try to load unsupported file type
    print("\nTrying to load unsupported file type...")
    try:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"some data")
            txt_path = f.name

        source = LocalFileDataSource(file_path=txt_path)
        await source.load_predictions()
    except ValueError as e:
        print(f"  ✓ Caught expected error: {e}")


async def main():
    """Run all examples."""
    await example_standard_format()
    await example_custom_column_names()
    await example_csv_file()
    await example_caching()
    await example_filtering_and_analysis()
    await example_error_handling()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
