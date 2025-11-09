# CC-Flow Utilities Module

This directory contains foundational utility functions used throughout the cc-flow application. All modules were developed following strict Test-Driven Development (TDD) principles with 100% test coverage.

## Overview

The utilities package provides four core modules:

1. **logging.py** - Loguru-based logging configuration
2. **validation.py** - Input validation for addresses, ranges, and dates
3. **formatting.py** - Display formatting for currency, percentages, dates, and decimals
4. **calculations.py** - Financial calculations including leverage, PNL, returns, and risk metrics

## Test Coverage

```
Name                            Stmts   Miss  Cover
-------------------------------------------------------------
cc_flow/utils/__init__.py           5      0   100%
cc_flow/utils/calculations.py      35      0   100%
cc_flow/utils/formatting.py        17      0   100%
cc_flow/utils/logging.py           10      0   100%
cc_flow/utils/validation.py        32      0   100%
-------------------------------------------------------------
TOTAL                              99      0   100%
```

**Total Tests: 119**
- test_logging.py: 9 tests
- test_validation.py: 32 tests
- test_formatting.py: 41 tests
- test_calculations.py: 37 tests

## Module Sizes

All modules comply with the 300-line limit:

```
106 lines - calculations.py
 70 lines - formatting.py
 54 lines - logging.py
101 lines - validation.py
 49 lines - __init__.py
```

## Design Principles

### SOLID Principles Applied

1. **Single Responsibility**: Each function has one clear purpose
   - `calculate_leverage()` only calculates leverage
   - `validate_ethereum_address()` only validates addresses

2. **Open/Closed**: Functions are open for extension, closed for modification
   - Custom formats supported via parameters
   - No need to modify code to extend functionality

3. **Dependency Inversion**: Functions depend on abstractions (type hints)
   - All parameters and returns are fully typed
   - No concrete implementation dependencies

### Type Safety

All functions use comprehensive type hints:

```python
def calculate_pnl(
    entry_price: Decimal,
    current_price: Decimal,
    size: Decimal,
    side: str
) -> Decimal:
    ...
```

This enables:
- Static type checking (mypy, pyright)
- Better IDE autocomplete
- Self-documenting code
- Catching errors at development time

### Error Handling

Validation functions raise descriptive `ValueError` exceptions:

```python
try:
    validate_ethereum_address("invalid")
except ValueError as e:
    print(f"Error: {e}")  # "Address must start with 0x: invalid"
```

## Usage

### Quick Import

```python
from cc_flow.utils import (
    log,
    validate_ethereum_address,
    format_currency,
    calculate_pnl,
)
```

### Individual Imports

```python
from cc_flow.utils.logging import configure_logging, log
from cc_flow.utils.validation import validate_decimal_range
from cc_flow.utils.formatting import format_percentage
from cc_flow.utils.calculations import calculate_sharpe_ratio
```

## Dependencies

- **loguru** (>=0.7.0): Advanced logging with colors and rotation
- **polars**: Fast dataframe operations for risk metrics
- Python standard library: `re`, `datetime`, `decimal`

## Testing

Run tests with coverage:

```bash
# All utility tests
uv run pytest tests/unit/test_utils/ -v

# With coverage report
uv run pytest tests/unit/test_utils/ --cov=cc_flow/utils --cov-report=term-missing

# Specific module
uv run pytest tests/unit/test_utils/test_calculations.py -v
```

## Documentation

- **USAGE_EXAMPLES.md**: Comprehensive examples for all functions
- **README.md** (this file): Overview and architecture
- Docstrings: All functions have detailed docstrings with examples

## API Reference

### Logging Module

```python
configure_logging(
    level: str = "INFO",
    log_file: str | None = None,
    rotation: str = "100 MB",
    retention: str = "1 week"
) -> Logger
```

### Validation Module

```python
validate_ethereum_address(address: str) -> bool
validate_decimal_range(
    value: Decimal,
    min_value: Decimal | None = None,
    max_value: Decimal | None = None,
    name: str = "value"
) -> bool
validate_date_range(
    date: str,
    start_date: str | None = None,
    end_date: str | None = None,
    date_format: str = "%Y-%m-%d"
) -> bool
```

### Formatting Module

```python
format_currency(value: Decimal, decimals: int = 2, symbol: str = "$") -> str
format_percentage(value: Decimal, decimals: int = 2, include_sign: bool = False) -> str
format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str
format_decimal(value: Decimal, decimals: int = 4, strip_trailing: bool = True) -> str
```

### Calculations Module

```python
calculate_leverage(position_value: Decimal, account_value: Decimal) -> Decimal
calculate_pnl(entry_price: Decimal, current_price: Decimal, size: Decimal, side: str) -> Decimal
calculate_return(entry_price: Decimal, current_price: Decimal, side: str) -> Decimal
calculate_sharpe_ratio(returns: pl.Series, risk_free_rate: Decimal = Decimal("0")) -> Decimal
calculate_sortino_ratio(returns: pl.Series, risk_free_rate: Decimal = Decimal("0")) -> Decimal
```

## Development Workflow

This module was developed using TDD:

1. **RED**: Write failing tests first
2. **GREEN**: Implement minimal code to pass tests
3. **REFACTOR**: Clean up code while keeping tests green

Example TDD cycle:

```python
# 1. Write test (RED)
def test_calculate_leverage_normal_case():
    position_value = Decimal("10000")
    account_value = Decimal("5000")
    leverage = calculate_leverage(position_value, account_value)
    assert leverage == Decimal("2")

# 2. Implement (GREEN)
def calculate_leverage(position_value: Decimal, account_value: Decimal) -> Decimal:
    if account_value == 0:
        return Decimal("0")
    return position_value / account_value

# 3. Refactor (maintain GREEN)
# - Add type hints
# - Add docstrings
# - Extract common patterns
# - Run tests to ensure nothing broke
```

## Best Practices

1. **Use Decimal for Money**: Always use `Decimal` for financial calculations
   ```python
   from decimal import Decimal
   pnl = calculate_pnl(Decimal("100"), Decimal("110"), Decimal("10"), "LONG")
   ```

2. **Validate Early**: Validate inputs at system boundaries
   ```python
   validate_ethereum_address(user_input)
   validate_decimal_range(leverage, min_value=Decimal("1"), max_value=Decimal("5"))
   ```

3. **Format for Display**: Use formatting functions for all user-facing output
   ```python
   print(format_currency(account_value))
   print(format_percentage(daily_return, include_sign=True))
   ```

4. **Log, Don't Print**: Use structured logging instead of print statements
   ```python
   log.info(f"Calculated PNL: {format_currency(pnl)}")
   log.warning(f"Leverage exceeds target: {leverage:.2f}x")
   ```

## Future Enhancements

Potential additions while maintaining SOLID principles:

- [ ] Additional risk metrics (max drawdown, VaR, CVaR)
- [ ] More validation functions (URL validation, API key format)
- [ ] Batch formatting functions for DataFrames
- [ ] Performance metrics caching for large datasets

## Contributing

When adding new utilities:

1. Write comprehensive tests FIRST (TDD)
2. Achieve >90% test coverage
3. Keep modules under 300 lines
4. Add type hints to all signatures
5. Write docstrings with examples
6. Update USAGE_EXAMPLES.md

## License

MIT License - See project root for details.
