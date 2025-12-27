# Backtest Domain Models

Implementation of **task-6: Domain Models - Backtest Models** for the cc-liquid Textualize rewrite.

## Overview

This module provides Pydantic v2 models for backtesting configuration and results. It consists of:

1. **BacktestConfig** - A dataclass for backtest parameters
2. **BacktestResult** - A Pydantic model for backtest performance metrics and time-series data

## Files

```
cc_flow/domain/
├── backtest.py              # Core domain models
└── backtest_example.py      # Example usage and demonstrations

tests/unit/test_domain/
└── test_backtest.py         # Comprehensive unit tests (100% coverage)
```

## Models

### BacktestConfig

A simple dataclass for backtesting configuration. Uses dataclass instead of Pydantic for lightweight internal use.

**Key attributes:**
- Portfolio: `num_long`, `num_short`, `target_leverage`, `rank_power`
- Rebalancing: `rebalance_every_n_days`
- Data: `predictions_path`, `prices_path`
- Costs: `fee_rate`, `slippage_bps`
- Date range: `start_date`, `end_date`
- Prediction lag: `prediction_lag_days`

**Example:**
```python
from cc_flow.domain.backtest import BacktestConfig
from decimal import Decimal

config = BacktestConfig(
    num_long=15,
    num_short=10,
    target_leverage=Decimal("1.5"),
    rank_power=Decimal("1.0"),
    rebalance_every_n_days=7,
    fee_rate=Decimal("0.0003"),
    slippage_bps=Decimal("10.0"),
    start_date="2024-01-01",
    end_date="2024-12-31",
)
```

### BacktestResult

A Pydantic v2 model for backtest results with performance metrics and time-series data.

**Key features:**
- **Arbitrary types allowed**: Supports polars DataFrames
- **Mutable**: Can update fields after creation (`frozen=False`)
- **Type-safe**: Full type hints for all fields
- **Serializable**: Can dump to dict (DataFrames and Config become dicts)

**Key attributes:**
- DataFrames: `daily_df`, `positions_df`
- Config: `config` (BacktestConfig instance)
- Performance metrics: `total_return`, `cagr`, `sharpe_ratio`, `sortino_ratio`, `max_drawdown`, `calmar_ratio`, `annual_volatility`, `win_rate`, `avg_turnover`
- Trade stats: `num_trades`, `num_rebalances`
- Timestamps: `backtest_start`, `backtest_end`, `run_at`

**Example:**
```python
from cc_flow.domain.backtest import BacktestResult
from decimal import Decimal
from datetime import datetime, UTC
import polars as pl

# Create sample DataFrames
daily_df = pl.DataFrame({
    "date": [datetime(2024, 1, i, tzinfo=UTC) for i in range(1, 6)],
    "equity": [Decimal(str(100000 + i * 1000)) for i in range(5)],
    "returns": [Decimal("0.01")] * 5,
})

positions_df = pl.DataFrame({
    "date": [datetime(2024, 1, 1, tzinfo=UTC)] * 2,
    "symbol": ["BTC", "ETH"],
    "position": [Decimal("1.0"), Decimal("10.0")],
})

# Create result
result = BacktestResult(
    daily_df=daily_df,
    positions_df=positions_df,
    config=config,
    total_return=Decimal("0.102"),
    cagr=Decimal("0.105"),
    sharpe_ratio=Decimal("1.85"),
    sortino_ratio=Decimal("2.35"),
    max_drawdown=Decimal("-0.08"),
    calmar_ratio=Decimal("1.31"),
    annual_volatility=Decimal("0.12"),
    win_rate=Decimal("0.65"),
    avg_turnover=Decimal("0.42"),
    num_trades=156,
    num_rebalances=52,
    backtest_start=datetime(2024, 1, 1, tzinfo=UTC),
    backtest_end=datetime(2024, 12, 31, tzinfo=UTC),
)

# Access metrics
print(f"CAGR: {float(result.cagr) * 100:.2f}%")
print(f"Sharpe: {float(result.sharpe_ratio):.2f}")
print(f"Max DD: {float(result.max_drawdown) * 100:.2f}%")

# Serialize
dumped = result.model_dump()
print(f"Total return: {dumped['total_return']}")
```

## Type Safety

All models use comprehensive type hints:

- `Decimal` for financial values (precise arithmetic)
- `datetime` with UTC timezone for timestamps
- `pl.DataFrame` for time-series data
- `str | None` for optional string fields
- `int` for counts

## Serialization

### BacktestConfig

Use `dataclasses.asdict()` to convert to dict:

```python
from dataclasses import asdict

config_dict = asdict(config)
```

### BacktestResult

Use Pydantic's `model_dump()` methods:

```python
# Convert to dict (Config becomes dict, DataFrames stay as-is)
result_dict = result.model_dump()

# Convert to JSON-compatible dict (needs custom serializer for Decimal and polars)
result_json = result.model_dump(mode="json")
```

**Note**: Polars DataFrames are not JSON-serializable by default. You'll need custom serialization if saving to JSON:

```python
# Save DataFrames separately
result.daily_df.write_parquet("daily.parquet")
result.positions_df.write_parquet("positions.parquet")

# Save metrics as JSON (exclude DataFrames)
import json
metrics = result.model_dump(exclude={"daily_df", "positions_df"})
```

## Testing

The module has **100% test coverage** with 13 comprehensive tests:

```bash
# Run tests
uv run pytest tests/unit/test_domain/test_backtest.py -v

# Run with coverage
uv run pytest tests/unit/test_domain/test_backtest.py --cov=cc_flow/domain/backtest --cov-report=term-missing
```

**Test categories:**
- BacktestConfig: 5 tests (defaults, custom values, mutability, serialization, precision)
- BacktestResult: 8 tests (initialization, timestamps, DataFrames, mutability, serialization, edge cases, integration)

## Example Usage

Run the example script to see the models in action:

```bash
PYTHONPATH=. uv run python cc_flow/domain/backtest_example.py
```

This demonstrates:
- Creating BacktestConfig and BacktestResult instances
- Working with polars DataFrames
- Serialization and deserialization
- Formatted output of backtest metrics

## Design Decisions

### Why dataclass for BacktestConfig?

- **Simplicity**: No validation overhead for internal configuration
- **Mutability**: Easy to modify for optimization grid search
- **Lightweight**: Minimal dependencies and memory footprint
- **Standard library**: No Pydantic dependency for simple config

### Why Pydantic for BacktestResult?

- **Validation**: Ensures all required metrics are present
- **Type safety**: Strict type checking on creation
- **Arbitrary types**: Supports polars DataFrames via `arbitrary_types_allowed`
- **Serialization**: Built-in `model_dump()` and `model_dump_json()` methods
- **Future-proof**: Easy to add validators, computed fields, or JSON schema

### Why Decimal instead of float?

- **Precision**: Avoids floating-point rounding errors in financial calculations
- **Exact**: 0.1 is exactly 0.1, not 0.10000000000000001
- **Compliance**: Industry standard for financial applications
- **Predictable**: Same results across platforms and Python versions

### Why UTC timestamps?

- **Unambiguous**: No timezone confusion or DST issues
- **Standard**: ISO 8601 compliant
- **Sortable**: Direct comparison without conversion
- **Future-proof**: Easy to convert to any local timezone

## Dependencies

- **Python**: >=3.10 (uses `str | None` union syntax)
- **pydantic**: ^2.0 (v2 syntax with `ConfigDict`)
- **polars**: >=1.0 (for DataFrame support)

## Integration

These models integrate with:

- **Backtesting engine**: Consumes `BacktestConfig`, produces `BacktestResult`
- **Optimization**: Grid search over `BacktestConfig` parameters
- **UI components**: Display `BacktestResult` metrics in Textual widgets
- **Storage**: Serialize results to parquet/JSON for caching
- **Analysis**: Load historical results for comparison

## Next Steps

After implementing these models, you can:

1. Build the backtesting engine that consumes `BacktestConfig` and produces `BacktestResult`
2. Create Textual widgets to display `BacktestResult` metrics
3. Implement optimization that varies `BacktestConfig` parameters
4. Add result storage/caching using parquet files
5. Build comparison tools for multiple `BacktestResult` instances

## References

- PRD Section 7.1: Backtesting Models
- Task-6 specification: Domain Models - Backtest Models
- Pydantic v2 docs: https://docs.pydantic.dev/latest/
- Polars docs: https://docs.pola.rs/
