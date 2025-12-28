# MockDataSource Usage Examples

The `MockDataSource` class provides a flexible testing data source for cc-flow. It can be used in two modes:

1. **Custom mode**: Return pre-made test data
2. **Synthetic mode**: Generate random prediction data with configurable parameters

## Basic Usage

### Import

```python
from cc_flow.data_sources import MockDataSource
import polars as pl
```

## Example 1: Custom Test Data for Specific Scenarios

Use custom data when you need specific prediction values for testing portfolio logic:

```python
# Create specific test scenario
test_data = pl.DataFrame({
    "date": ["2025-01-01", "2025-01-01", "2025-01-01"],
    "asset_id": ["BTC", "ETH", "SOL"],
    "prediction": [0.95, 0.05, 0.50]  # BTC very bullish, ETH very bearish, SOL neutral
})

source = MockDataSource(predictions=test_data)
predictions = await source.load_predictions()

# Use for testing portfolio selection
# Top long should be BTC, top short should be ETH
```

## Example 2: Synthetic Data with Default Parameters

Generate 20 assets over 10 days with predictions in [0.0, 1.0]:

```python
source = MockDataSource()
predictions = await source.load_predictions()

# Returns 200 rows (20 assets * 10 dates)
# Predictions are random values between 0.0 and 1.0
```

## Example 3: Custom Asset and Date Counts

Control the size of the synthetic dataset:

```python
# Generate 50 assets over 30 days
source = MockDataSource(
    num_assets=50,
    num_dates=30
)

predictions = await source.load_predictions()
# Returns 1,500 rows (50 * 30)
```

## Example 4: Custom Prediction Range

Use different prediction ranges for different testing scenarios:

```python
# Standard normalized range [-1, 1]
source = MockDataSource(
    num_assets=100,
    num_dates=30,
    prediction_range=(-1.0, 1.0)
)

# Or any custom range
source = MockDataSource(
    num_assets=100,
    num_dates=30,
    prediction_range=(-100.0, 100.0)
)
```

## Example 5: Backtesting with Synthetic Data

Generate sufficient historical data for backtesting:

```python
# Generate 100 assets over 365 days
source = MockDataSource(
    num_assets=100,
    num_dates=365,
    prediction_range=(0.0, 1.0)
)

predictions = await source.load_predictions()

# Can now be used to:
# - Test rebalancing logic over time
# - Validate portfolio construction with daily data
# - Test performance metrics calculation
```

## Example 6: Metadata Inspection

Get information about the data source:

```python
source = MockDataSource(num_assets=50, num_dates=30)

metadata = await source.get_metadata()

print(f"Source: {metadata.source}")  # "mock"
print(f"Total predictions: {metadata.num_predictions}")  # 1500
print(f"Date range: {metadata.date_range}")  # ('2025-10-09', '2025-11-07')
print(f"Unique assets: {metadata.unique_assets}")  # 50
print(f"Last updated: {metadata.last_updated}")  # Current timestamp
```

## Example 7: Schema Validation

Validate that DataFrames have the required schema:

```python
source = MockDataSource()

# Valid DataFrame
valid_df = pl.DataFrame({
    "date": ["2025-01-01"],
    "asset_id": ["BTC"],
    "prediction": [0.8]
})

is_valid = await source.validate_schema(valid_df)  # True

# Invalid DataFrame (missing columns)
invalid_df = pl.DataFrame({
    "date": ["2025-01-01"],
    "asset_id": ["BTC"]
    # Missing 'prediction' column
})

try:
    await source.validate_schema(invalid_df)
except ValueError as e:
    print(f"Validation failed: {e}")
    # "Missing required columns: {'prediction'}"
```

## Example 8: Integration Testing

Use MockDataSource as a test double in integration tests:

```python
import pytest
from cc_flow.portfolio import PortfolioConstructor
from cc_flow.data_sources import MockDataSource

@pytest.mark.asyncio
async def test_portfolio_construction_with_mock_data():
    """Test portfolio constructor with known test data."""

    # Create test data with known top/bottom predictions
    test_data = pl.DataFrame({
        "date": ["2025-01-01"] * 10,
        "asset_id": [f"ASSET{i:02d}" for i in range(10)],
        "prediction": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    })

    source = MockDataSource(predictions=test_data)
    predictions = await source.load_predictions()

    # Test portfolio constructor
    constructor = PortfolioConstructor(num_long=3, num_short=3)
    portfolio = constructor.build(predictions)

    # Verify top 3 long positions
    long_positions = portfolio.filter(portfolio["position"] > 0)
    assert set(long_positions["asset_id"]) == {"ASSET07", "ASSET08", "ASSET09"}

    # Verify top 3 short positions
    short_positions = portfolio.filter(portfolio["position"] < 0)
    assert set(short_positions["asset_id"]) == {"ASSET00", "ASSET01", "ASSET02"}
```

## Example 9: Performance Testing with Large Datasets

Test performance with large synthetic datasets:

```python
import time

# Generate large dataset
source = MockDataSource(
    num_assets=1000,
    num_dates=365,
    prediction_range=(-1.0, 1.0)
)

start = time.time()
predictions = await source.load_predictions()
load_time = time.time() - start

print(f"Loaded {len(predictions)} rows in {load_time:.3f}s")
# Should be very fast since it's synthetic generation
```

## Example 10: Fixture for Pytest

Create a reusable fixture for tests:

```python
import pytest
from cc_flow.data_sources import MockDataSource

@pytest.fixture
def small_mock_source():
    """Small mock data source for quick tests."""
    return MockDataSource(num_assets=5, num_dates=3)

@pytest.fixture
def large_mock_source():
    """Large mock data source for performance tests."""
    return MockDataSource(num_assets=1000, num_dates=100)

@pytest.fixture
def custom_test_data():
    """Custom test data for specific scenarios."""
    df = pl.DataFrame({
        "date": ["2025-01-01", "2025-01-01"],
        "asset_id": ["BTC", "ETH"],
        "prediction": [0.9, 0.1]
    })
    return MockDataSource(predictions=df)

@pytest.mark.asyncio
async def test_with_small_data(small_mock_source):
    """Test with small dataset."""
    predictions = await small_mock_source.load_predictions()
    assert len(predictions) == 15  # 5 assets * 3 dates

@pytest.mark.asyncio
async def test_with_custom_data(custom_test_data):
    """Test with custom data."""
    predictions = await custom_test_data.load_predictions()
    assert predictions.filter(pl.col("asset_id") == "BTC")["prediction"][0] == 0.9
```

## Data Format

All MockDataSource outputs follow this schema:

```python
{
    "date": str,        # ISO format date string (e.g., "2025-01-01")
    "asset_id": str,    # Asset identifier (e.g., "BTC", "ASSET00")
    "prediction": float # Prediction value (within configured range)
}
```

## Synthetic Data Characteristics

When using synthetic generation:

- **Dates**: Generated as last N days from today, in chronological order
- **Asset IDs**: Format `ASSET00`, `ASSET01`, ..., `ASSET{N-1}` with zero-padding
- **Predictions**: Uniformly distributed random values within `prediction_range`
- **Coverage**: Complete coverage - every asset appears for every date
- **Determinism**: Each instance generates different random values (no fixed seed)

## Tips for Testing

1. **Use custom data for deterministic tests**: When you need exact prediction values
2. **Use synthetic data for volume tests**: When you need many rows of data
3. **Match prediction ranges to your use case**:
   - Use [0, 1] for probability-like predictions
   - Use [-1, 1] for normalized predictions
   - Use wider ranges for raw model outputs
4. **Consider dataset size**: Large datasets (1000+ assets, 365+ days) can test performance
5. **Validate schema explicitly**: Use `validate_schema()` in tests that depend on data format

## Common Patterns

### Pattern 1: Controlled Test Scenarios

```python
# Create extreme scenarios for edge case testing
extreme_data = pl.DataFrame({
    "date": ["2025-01-01"] * 4,
    "asset_id": ["A", "B", "C", "D"],
    "prediction": [1.0, 0.0, -1.0, 0.5]  # Max, min, negative, mid
})

source = MockDataSource(predictions=extreme_data)
```

### Pattern 2: Time Series Testing

```python
# Generate time series data for temporal tests
source = MockDataSource(
    num_assets=10,
    num_dates=100,  # 100 days of history
    prediction_range=(-1.0, 1.0)
)

predictions = await source.load_predictions()

# Can test rebalancing frequency, momentum, etc.
```

### Pattern 3: Parameterized Testing

```python
@pytest.mark.parametrize("num_assets,num_dates", [
    (5, 3),
    (10, 10),
    (50, 30),
    (100, 100),
])
@pytest.mark.asyncio
async def test_scaling(num_assets, num_dates):
    """Test with different dataset sizes."""
    source = MockDataSource(num_assets=num_assets, num_dates=num_dates)
    predictions = await source.load_predictions()
    assert len(predictions) == num_assets * num_dates
```
