# Numerai Data Source - Example Usage

This document demonstrates how to use the `NumeraiDataSource` class to fetch crypto signals from the Numerai Signals API.

## Overview

The `NumeraiDataSource` provides access to Numerai's crypto meta model predictions through their GraphQL API. It automatically handles:

- API authentication (public endpoint, no API key required)
- Data fetching and transformation
- Column mapping to standardized format
- Caching for improved performance
- Error handling

## Basic Usage

```python
import asyncio
from cc_flow.data_sources import NumeraiDataSource

async def main():
    # Initialize the data source
    source = NumeraiDataSource()

    # Load predictions
    predictions = await source.load_predictions()

    # Display basic info
    print(f"Loaded {len(predictions)} predictions")
    print(f"Columns: {predictions.columns}")
    print(f"\nFirst 5 rows:")
    print(predictions.head(5))

# Run the async function
asyncio.run(main())
```

## Getting Metadata

```python
import asyncio
from cc_flow.data_sources import NumeraiDataSource

async def main():
    source = NumeraiDataSource()

    # Get metadata about the data
    metadata = await source.get_metadata()

    print(f"Source: {metadata.source}")
    print(f"Number of predictions: {metadata.num_predictions}")
    print(f"Date range: {metadata.date_range}")
    print(f"Unique assets: {metadata.unique_assets}")
    print(f"Last updated: {metadata.last_updated}")
    print(f"Schema version: {metadata.schema_version}")

asyncio.run(main())
```

## Custom Cache TTL

```python
import asyncio
from cc_flow.data_sources import NumeraiDataSource

async def main():
    # Cache for 30 minutes instead of default 1 hour
    source = NumeraiDataSource(cache_ttl=1800)

    # First call fetches from API
    predictions1 = await source.load_predictions()
    print("Fetched from API")

    # Second call within 30 minutes uses cache
    predictions2 = await source.load_predictions()
    print("Retrieved from cache")

    # Verify they're identical
    assert predictions1.equals(predictions2)

asyncio.run(main())
```

## Data Format

The returned DataFrame has the following standardized columns:

| Column      | Type   | Description                                    |
|-------------|--------|------------------------------------------------|
| `date`      | str    | Date of the prediction (YYYY-MM-DD)            |
| `asset_id`  | str    | Asset symbol (e.g., "BTC", "ETH")              |
| `prediction`| float  | Predicted value (typically between -1 and 1)   |

### Example Data

```
shape: (5, 3)
┌────────────┬──────────┬────────────┐
│ date       ┆ asset_id ┆ prediction │
│ ---        ┆ ---      ┆ ---        │
│ str        ┆ str      ┆ f64        │
╞════════════╪══════════╪════════════╡
│ 2024-01-01 ┆ BTC      ┆ 0.652341   │
│ 2024-01-01 ┆ ETH      ┆ -0.234567  │
│ 2024-01-01 ┆ SOL      ┆ 0.123456   │
│ 2024-01-02 ┆ BTC      ┆ 0.456789   │
│ 2024-01-02 ┆ ETH      ┆ 0.345678   │
└────────────┴──────────┴────────────┘
```

## Filtering and Analysis

```python
import asyncio
from cc_flow.data_sources import NumeraiDataSource

async def main():
    source = NumeraiDataSource()
    predictions = await source.load_predictions()

    # Filter for specific assets
    btc_predictions = predictions.filter(
        predictions["asset_id"] == "BTC"
    )
    print(f"BTC predictions: {len(btc_predictions)}")

    # Get top 10 predictions
    top_10 = predictions.sort("prediction", descending=True).head(10)
    print("\nTop 10 predictions:")
    print(top_10)

    # Get bottom 10 predictions (for shorting)
    bottom_10 = predictions.sort("prediction").head(10)
    print("\nBottom 10 predictions:")
    print(bottom_10)

    # Statistics
    print(f"\nPrediction stats:")
    print(predictions["prediction"].describe())

asyncio.run(main())
```

## Error Handling

```python
import asyncio
from cc_flow.data_sources import NumeraiDataSource
import requests

async def main():
    source = NumeraiDataSource()

    try:
        predictions = await source.load_predictions()
        print(f"Successfully loaded {len(predictions)} predictions")
    except requests.exceptions.Timeout:
        print("API request timed out")
    except requests.exceptions.ConnectionError:
        print("Connection failed")
    except ValueError as e:
        print(f"API error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

asyncio.run(main())
```

## Integration with Portfolio Construction

```python
import asyncio
from cc_flow.data_sources import NumeraiDataSource

async def build_portfolio(num_long: int = 5, num_short: int = 5):
    """Build a simple long/short portfolio from Numerai signals."""
    source = NumeraiDataSource()
    predictions = await source.load_predictions()

    # Get most recent date
    latest_date = predictions["date"].max()
    latest_predictions = predictions.filter(
        predictions["date"] == latest_date
    )

    # Select top long positions
    longs = latest_predictions.sort("prediction", descending=True).head(num_long)
    print(f"Long positions ({num_long}):")
    print(longs.select(["asset_id", "prediction"]))

    # Select top short positions
    shorts = latest_predictions.sort("prediction").head(num_short)
    print(f"\nShort positions ({num_short}):")
    print(shorts.select(["asset_id", "prediction"]))

    return longs, shorts

asyncio.run(build_portfolio(num_long=10, num_short=10))
```

## Comparison with Other Sources

```python
import asyncio
from cc_flow.data_sources import NumeraiDataSource, CrowdCentDataSource

async def compare_sources():
    """Compare predictions from different sources."""
    # Numerai (free, public)
    numerai = NumeraiDataSource()
    numerai_preds = await numerai.load_predictions()

    # CrowdCent (requires API key)
    crowdcent = CrowdCentDataSource(api_key="your_key")
    crowdcent_preds = await crowdcent.load_predictions()

    print(f"Numerai predictions: {len(numerai_preds)}")
    print(f"CrowdCent predictions: {len(crowdcent_preds)}")

    # Find common assets
    numerai_assets = set(numerai_preds["asset_id"].unique())
    crowdcent_assets = set(crowdcent_preds["asset_id"].unique())
    common_assets = numerai_assets & crowdcent_assets

    print(f"Common assets: {len(common_assets)}")
    print(f"Numerai-only assets: {len(numerai_assets - crowdcent_assets)}")
    print(f"CrowdCent-only assets: {len(crowdcent_assets - numerai_assets)}")

asyncio.run(compare_sources())
```

## Performance Considerations

### Caching

The `NumeraiDataSource` implements intelligent caching:

- **Default TTL**: 1 hour (3600 seconds)
- **Cache validation**: Automatic timestamp-based expiry
- **Memory efficiency**: Stores DataFrame in memory

```python
# Adjust cache TTL based on your needs
source = NumeraiDataSource(cache_ttl=7200)  # 2 hours

# Force cache refresh by waiting for TTL expiry
# or create a new instance
source = NumeraiDataSource()  # Fresh cache
```

### Rate Limiting

Numerai's API is public and doesn't require authentication, but be mindful of:

- Not making excessive requests
- Using the built-in caching to minimize API calls
- Setting appropriate cache TTL for your use case

## Advanced Usage

### Custom Processing Pipeline

```python
import asyncio
from cc_flow.data_sources import NumeraiDataSource
import polars as pl

async def custom_pipeline():
    source = NumeraiDataSource()
    predictions = await source.load_predictions()

    # Add custom features
    processed = predictions.with_columns([
        # Normalize predictions to 0-1 range
        ((pl.col("prediction") + 1) / 2).alias("normalized_prediction"),

        # Create signal strength indicator
        pl.col("prediction").abs().alias("signal_strength"),

        # Create direction indicator
        (pl.col("prediction") > 0).alias("is_long"),
    ])

    # Filter for high-confidence signals
    high_confidence = processed.filter(
        pl.col("signal_strength") > 0.5
    )

    print(f"High confidence signals: {len(high_confidence)}")
    return high_confidence

asyncio.run(custom_pipeline())
```

### Validation

```python
import asyncio
from cc_flow.data_sources import NumeraiDataSource

async def validate_data():
    source = NumeraiDataSource()
    predictions = await source.load_predictions()

    # Validate schema
    is_valid = await source.validate_schema(predictions)
    print(f"Schema valid: {is_valid}")

    # Custom validation
    assert "date" in predictions.columns
    assert "asset_id" in predictions.columns
    assert "prediction" in predictions.columns

    # Check data quality
    assert len(predictions) > 0, "No predictions found"
    assert predictions["prediction"].null_count() == 0, "Null predictions found"

    # Check value ranges
    min_pred = predictions["prediction"].min()
    max_pred = predictions["prediction"].max()
    print(f"Prediction range: [{min_pred}, {max_pred}]")

    print("All validation checks passed!")

asyncio.run(validate_data())
```

## Troubleshooting

### Common Issues

1. **Timeout errors**: Increase the timeout or check your network connection
2. **Empty response**: Check if Numerai API is available
3. **GraphQL errors**: API may be experiencing issues - check Numerai status
4. **Cache issues**: Create a new instance to force fresh data fetch

### Debug Mode

```python
import asyncio
import logging
from cc_flow.data_sources import NumeraiDataSource

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

async def debug_fetch():
    source = NumeraiDataSource()
    try:
        predictions = await source.load_predictions()
        print(f"Success: {len(predictions)} predictions")
    except Exception as e:
        print(f"Error details: {e}")
        raise

asyncio.run(debug_fetch())
```

## API Reference

See the docstrings in `/home/ling/workarea/numerai/cc-liquid/cc_flow/data_sources/numerai.py` for full API documentation.

### Key Methods

- `__init__(cache_ttl: int = 3600)`: Initialize with optional cache TTL
- `load_predictions() -> pl.DataFrame`: Load predictions (async)
- `get_metadata() -> PredictionMetadata`: Get data metadata (async)
- `validate_schema(df: pl.DataFrame) -> bool`: Validate DataFrame schema (async)

### Key Attributes

- `api_url`: Numerai API endpoint
- `cache_ttl`: Cache time-to-live in seconds
- `_cache`: Cached DataFrame (internal)
- `_cache_time`: Cache timestamp (internal)
