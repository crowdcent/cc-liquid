#!/usr/bin/env python3
"""Demo script showing NumeraiDataSource usage.

This script demonstrates how to use the NumeraiDataSource to fetch
crypto signals from Numerai and perform basic analysis.

Usage:
    uv run python cc_flow/data_sources/numerai_demo.py
"""

from __future__ import annotations

import asyncio

from cc_flow.data_sources import NumeraiDataSource


async def demo_basic_usage():
    """Demonstrate basic usage of NumeraiDataSource."""
    print("=" * 60)
    print("Numerai Data Source - Basic Usage Demo")
    print("=" * 60)

    # Initialize the data source
    print("\n1. Initializing NumeraiDataSource...")
    source = NumeraiDataSource(cache_ttl=3600)

    # Load predictions
    print("2. Loading predictions from Numerai API...")
    try:
        predictions = await source.load_predictions()
        print(f"   ✓ Successfully loaded {len(predictions)} predictions")
    except Exception as e:
        print(f"   ✗ Error loading predictions: {e}")
        return

    # Display basic info
    print("\n3. Data structure:")
    print(f"   Columns: {predictions.columns}")
    print(f"   Shape: {predictions.shape}")

    # Show sample data
    print("\n4. First 5 rows:")
    print(predictions.head(5))

    # Get metadata
    print("\n5. Metadata:")
    metadata = await source.get_metadata()
    print(f"   Source: {metadata.source}")
    print(f"   Number of predictions: {metadata.num_predictions}")
    print(f"   Date range: {metadata.date_range}")
    print(f"   Unique assets: {metadata.unique_assets}")
    print(f"   Last updated: {metadata.last_updated}")
    print(f"   Schema version: {metadata.schema_version}")


async def demo_analysis():
    """Demonstrate analysis capabilities."""
    print("\n" + "=" * 60)
    print("Numerai Data Source - Analysis Demo")
    print("=" * 60)

    source = NumeraiDataSource()

    print("\n1. Loading predictions...")
    try:
        predictions = await source.load_predictions()
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    # Get most recent date
    latest_date = predictions["date"].max()
    latest = predictions.filter(predictions["date"] == latest_date)

    print(f"\n2. Latest predictions (date: {latest_date}):")
    print(f"   Total signals: {len(latest)}")

    # Top 10 long positions
    top_longs = latest.sort("prediction", descending=True).head(10)
    print("\n3. Top 10 Long Positions:")
    for i, row in enumerate(top_longs.iter_rows(named=True), 1):
        print(f"   {i:2d}. {row['asset_id']:10s} prediction: {row['prediction']:7.4f}")

    # Top 10 short positions
    top_shorts = latest.sort("prediction").head(10)
    print("\n4. Top 10 Short Positions:")
    for i, row in enumerate(top_shorts.iter_rows(named=True), 1):
        print(f"   {i:2d}. {row['asset_id']:10s} prediction: {row['prediction']:7.4f}")

    # Prediction statistics
    print("\n5. Prediction Statistics:")
    stats = predictions["prediction"].describe()
    print(stats)


async def demo_caching():
    """Demonstrate caching behavior."""
    print("\n" + "=" * 60)
    print("Numerai Data Source - Caching Demo")
    print("=" * 60)

    print("\n1. Creating source with 30-second cache TTL...")
    source = NumeraiDataSource(cache_ttl=30)

    print("2. First load (fetches from API)...")
    import time

    start = time.time()
    try:
        df1 = await source.load_predictions()
        elapsed1 = time.time() - start
        print(f"   ✓ Loaded {len(df1)} predictions in {elapsed1:.2f} seconds")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    print("3. Second load (uses cache)...")
    start = time.time()
    df2 = await source.load_predictions()
    elapsed2 = time.time() - start
    print(f"   ✓ Retrieved {len(df2)} predictions in {elapsed2:.2f} seconds")

    print("\n4. Performance improvement:")
    print(f"   First load:  {elapsed1:.2f}s (API fetch)")
    print(f"   Second load: {elapsed2:.2f}s (cached)")
    if elapsed1 > 0:
        speedup = elapsed1 / elapsed2 if elapsed2 > 0 else float("inf")
        print(f"   Speedup: {speedup:.1f}x faster")

    print("\n5. Data integrity check:")
    if df1.equals(df2):
        print("   ✓ Cached data matches original data")
    else:
        print("   ✗ Warning: Data mismatch between loads")


async def demo_error_handling():
    """Demonstrate error handling."""
    print("\n" + "=" * 60)
    print("Numerai Data Source - Error Handling Demo")
    print("=" * 60)

    print("\n1. Normal operation:")
    source = NumeraiDataSource()

    try:
        predictions = await source.load_predictions()
        print(f"   ✓ Successfully loaded {len(predictions)} predictions")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

    print("\n2. Schema validation:")
    try:
        is_valid = await source.validate_schema(predictions)
        if is_valid:
            print("   ✓ Schema validation passed")
    except ValueError as e:
        print(f"   ✗ Schema validation failed: {e}")


async def main():
    """Run all demo functions."""
    print("\n")
    print("*" * 60)
    print("*" + " " * 58 + "*")
    print("*" + "  Numerai Data Source Demo".center(58) + "*")
    print("*" + " " * 58 + "*")
    print("*" * 60)

    try:
        # Basic usage
        await demo_basic_usage()

        # Analysis
        await demo_analysis()

        # Caching
        await demo_caching()

        # Error handling
        await demo_error_handling()

        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nDemo failed with error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
