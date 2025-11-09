# Utility Functions Usage Examples

This document provides practical usage examples for all utility functions in the cc_flow.utils package.

## Logging (`logging.py`)

### Basic Logging Setup

```python
from cc_flow.utils.logging import configure_logging, log

# Use default logger (already configured)
log.info("Application started")
log.debug("Debug information")
log.warning("Warning message")
log.error("Error occurred")

# Configure custom logger
custom_logger = configure_logging(
    level="DEBUG",
    log_file="/var/log/cc_flow.log",
    rotation="100 MB",
    retention="1 week"
)

custom_logger.info("Custom logger message")
```

### Different Log Levels

```python
from cc_flow.utils.logging import configure_logging

# Production: Only warnings and errors
prod_logger = configure_logging(level="WARNING")

# Development: All messages including debug
dev_logger = configure_logging(level="DEBUG")

# File logging with rotation
file_logger = configure_logging(
    level="INFO",
    log_file="app.log",
    rotation="10 MB",  # Rotate when file reaches 10MB
    retention="2 weeks"  # Keep logs for 2 weeks
)
```

### Exception Logging

```python
from cc_flow.utils.logging import log

try:
    result = risky_operation()
except Exception as e:
    log.exception("Operation failed")  # Includes stack trace
    raise
```

## Validation (`validation.py`)

### Ethereum Address Validation

```python
from cc_flow.utils.validation import validate_ethereum_address

# Valid addresses
try:
    validate_ethereum_address("0x1234567890abcdef1234567890abcdef12345678")
    print("Address is valid")
except ValueError as e:
    print(f"Invalid address: {e}")

# Invalid addresses raise ValueError
try:
    validate_ethereum_address("not_an_address")
except ValueError as e:
    print(f"Error: {e}")  # "Address must start with 0x"
```

### Decimal Range Validation

```python
from decimal import Decimal
from cc_flow.utils.validation import validate_decimal_range

# Validate leverage is within acceptable range
leverage = Decimal("3.5")
try:
    validate_decimal_range(
        leverage,
        min_value=Decimal("1"),
        max_value=Decimal("5"),
        name="leverage"
    )
    print("Leverage is valid")
except ValueError as e:
    print(f"Invalid leverage: {e}")

# Validate only minimum
position_size = Decimal("100")
validate_decimal_range(
    position_size,
    min_value=Decimal("10"),  # Minimum $10
    name="position_size"
)

# Validate only maximum
slippage = Decimal("0.05")
validate_decimal_range(
    slippage,
    max_value=Decimal("0.1"),  # Max 10% slippage
    name="slippage"
)
```

### Date Range Validation

```python
from cc_flow.utils.validation import validate_date_range

# Validate date is within backtest period
trade_date = "2024-06-15"
try:
    validate_date_range(
        trade_date,
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    print("Date is valid")
except ValueError as e:
    print(f"Invalid date: {e}")

# Custom date format
european_date = "15/06/2024"
validate_date_range(
    european_date,
    start_date="01/01/2024",
    end_date="31/12/2024",
    date_format="%d/%m/%Y"
)

# Validate with datetime
timestamp = "2024-06-15 14:30:00"
validate_date_range(
    timestamp,
    start_date="2024-01-01 00:00:00",
    end_date="2024-12-31 23:59:59",
    date_format="%Y-%m-%d %H:%M:%S"
)
```

## Formatting (`formatting.py`)

### Currency Formatting

```python
from decimal import Decimal
from cc_flow.utils.formatting import format_currency

# Basic currency formatting
pnl = Decimal("1234.56")
print(format_currency(pnl))  # "$1,234.56"

# Custom decimals
price = Decimal("123.456789")
print(format_currency(price, decimals=4))  # "$123.4568"

# Different currency symbols
eur_amount = Decimal("5000")
print(format_currency(eur_amount, symbol="€"))  # "€5,000.00"

# No symbol (just formatting)
value = Decimal("1000000")
print(format_currency(value, symbol=""))  # "1,000,000.00"

# Negative values
loss = Decimal("-500.25")
print(format_currency(loss))  # "$-500.25"
```

### Percentage Formatting

```python
from decimal import Decimal
from cc_flow.utils.formatting import format_percentage

# Basic percentage (value is decimal)
return_pct = Decimal("0.1534")
print(format_percentage(return_pct))  # "15.34%"

# With sign for display
gain = Decimal("0.05")
loss = Decimal("-0.03")
print(format_percentage(gain, include_sign=True))  # "+5.00%"
print(format_percentage(loss, include_sign=True))  # "-3.00%"

# Custom decimal places
precise_pct = Decimal("0.123456")
print(format_percentage(precise_pct, decimals=4))  # "12.3456%"

# Whole percentages
rough_pct = Decimal("0.15")
print(format_percentage(rough_pct, decimals=0))  # "15%"
```

### Datetime Formatting

```python
from datetime import datetime
from cc_flow.utils.formatting import format_datetime

now = datetime(2024, 6, 15, 14, 30, 45)

# Default format
print(format_datetime(now))  # "2024-06-15 14:30:45"

# Date only
print(format_datetime(now, format="%Y-%m-%d"))  # "2024-06-15"

# Time only
print(format_datetime(now, format="%H:%M:%S"))  # "14:30:45"

# Custom formats
print(format_datetime(now, format="%B %d, %Y"))  # "June 15, 2024"
print(format_datetime(now, format="%d/%m/%Y %I:%M %p"))  # "15/06/2024 02:30 PM"

# ISO format
print(format_datetime(now, format="%Y-%m-%dT%H:%M:%S"))  # "2024-06-15T14:30:45"
```

### Decimal Formatting

```python
from decimal import Decimal
from cc_flow.utils.formatting import format_decimal

# Basic formatting (strips trailing zeros by default)
value = Decimal("123.4500")
print(format_decimal(value))  # "123.45"

# Keep trailing zeros
print(format_decimal(value, strip_trailing=False))  # "123.4500"

# Custom decimal places
pi = Decimal("3.14159265359")
print(format_decimal(pi, decimals=2))  # "3.14"
print(format_decimal(pi, decimals=6))  # "3.141593"

# High precision
price = Decimal("0.00012345")
print(format_decimal(price, decimals=8))  # "0.00012345"

# Whole numbers
whole = Decimal("100")
print(format_decimal(whole))  # "100" (no decimal point)
```

## Financial Calculations (`calculations.py`)

### Leverage Calculation

```python
from decimal import Decimal
from cc_flow.utils.calculations import calculate_leverage

# Calculate current leverage
position_value = Decimal("10000")  # Total position size
account_value = Decimal("5000")     # Account equity
leverage = calculate_leverage(position_value, account_value)
print(f"Leverage: {leverage}x")  # "Leverage: 2x"

# Check if within limits
max_leverage = Decimal("3")
if leverage > max_leverage:
    print("Leverage too high!")
```

### PNL Calculation

```python
from decimal import Decimal
from cc_flow.utils.calculations import calculate_pnl

# Long position profit
entry_price = Decimal("100")
current_price = Decimal("110")
size = Decimal("10")
pnl = calculate_pnl(entry_price, current_price, size, "LONG")
print(f"PNL: ${pnl}")  # "PNL: $100"

# Short position profit
pnl_short = calculate_pnl(entry_price, Decimal("90"), size, "SHORT")
print(f"Short PNL: ${pnl_short}")  # "Short PNL: $100"

# Portfolio total PNL
positions = [
    {"entry": Decimal("100"), "current": Decimal("105"), "size": Decimal("10"), "side": "LONG"},
    {"entry": Decimal("50"), "current": Decimal("48"), "size": Decimal("20"), "side": "SHORT"},
]

total_pnl = sum(
    calculate_pnl(p["entry"], p["current"], p["size"], p["side"])
    for p in positions
)
print(f"Total PNL: ${total_pnl}")  # "Total PNL: $90"
```

### Return Calculation

```python
from decimal import Decimal
from cc_flow.utils.calculations import calculate_return
from cc_flow.utils.formatting import format_percentage

# Long position return
entry_price = Decimal("100")
current_price = Decimal("115")
ret = calculate_return(entry_price, current_price, "LONG")
print(format_percentage(ret, include_sign=True))  # "+15.00%"

# Short position return
ret_short = calculate_return(entry_price, Decimal("90"), "SHORT")
print(format_percentage(ret_short, include_sign=True))  # "+10.00%"
```

### Sharpe Ratio Calculation

```python
import polars as pl
from decimal import Decimal
from cc_flow.utils.calculations import calculate_sharpe_ratio

# Calculate Sharpe ratio from daily returns
daily_returns = pl.Series([
    0.001, -0.002, 0.003, -0.001, 0.002,
    0.001, -0.003, 0.004, -0.002, 0.001
])

sharpe = calculate_sharpe_ratio(daily_returns)
print(f"Sharpe Ratio: {sharpe:.2f}")

# With risk-free rate (e.g., 2% annual)
sharpe_adjusted = calculate_sharpe_ratio(
    daily_returns,
    risk_free_rate=Decimal("0.02")
)
print(f"Sharpe Ratio (adjusted): {sharpe_adjusted:.2f}")
```

### Sortino Ratio Calculation

```python
import polars as pl
from decimal import Decimal
from cc_flow.utils.calculations import calculate_sortino_ratio

# Calculate Sortino ratio (only penalizes downside volatility)
daily_returns = pl.Series([
    0.02, 0.03, -0.01, 0.01, -0.02,
    0.04, -0.015, 0.025, 0.01, -0.01
])

sortino = calculate_sortino_ratio(daily_returns)
print(f"Sortino Ratio: {sortino:.2f}")

# With risk-free rate
sortino_adjusted = calculate_sortino_ratio(
    daily_returns,
    risk_free_rate=Decimal("0.02")
)
print(f"Sortino Ratio (adjusted): {sortino_adjusted:.2f}")
```

## Combined Example: Portfolio Dashboard

```python
from decimal import Decimal
from datetime import datetime
import polars as pl

from cc_flow.utils.logging import log
from cc_flow.utils.validation import validate_ethereum_address, validate_decimal_range
from cc_flow.utils.formatting import format_currency, format_percentage, format_datetime
from cc_flow.utils.calculations import (
    calculate_leverage,
    calculate_pnl,
    calculate_return,
    calculate_sharpe_ratio,
)

# Initialize
log.info("Starting portfolio analysis")

# Validate inputs
owner_address = "0x1234567890abcdef1234567890abcdef12345678"
validate_ethereum_address(owner_address)

# Portfolio data
account_value = Decimal("100000")
position_value = Decimal("250000")
target_leverage = Decimal("2.5")

# Calculate and validate leverage
current_leverage = calculate_leverage(position_value, account_value)
try:
    validate_decimal_range(
        current_leverage,
        max_value=Decimal("3"),
        name="leverage"
    )
except ValueError as e:
    log.warning(f"Leverage exceeds limit: {e}")

# Position PNL
positions = [
    {"symbol": "BTC", "entry": Decimal("60000"), "current": Decimal("65000"),
     "size": Decimal("1"), "side": "LONG"},
    {"symbol": "ETH", "entry": Decimal("3000"), "current": Decimal("2900"),
     "size": Decimal("10"), "side": "LONG"},
]

total_pnl = Decimal("0")
for pos in positions:
    pnl = calculate_pnl(pos["entry"], pos["current"], pos["size"], pos["side"])
    ret = calculate_return(pos["entry"], pos["current"], pos["side"])
    total_pnl += pnl

    log.info(
        f"{pos['symbol']}: PNL={format_currency(pnl)}, "
        f"Return={format_percentage(ret, include_sign=True)}"
    )

# Performance metrics
daily_returns = pl.Series([0.01, -0.005, 0.015, -0.008, 0.012])
sharpe = calculate_sharpe_ratio(daily_returns)

# Summary
print("\n" + "="*50)
print("PORTFOLIO SUMMARY")
print("="*50)
print(f"Timestamp: {format_datetime(datetime.now())}")
print(f"Account Value: {format_currency(account_value)}")
print(f"Position Value: {format_currency(position_value)}")
print(f"Current Leverage: {current_leverage:.2f}x")
print(f"Total PNL: {format_currency(total_pnl)}")
print(f"Sharpe Ratio: {sharpe:.2f}")
print("="*50)

log.info("Portfolio analysis complete")
```

## Best Practices

1. **Logging**: Always use the configured logger instead of print statements
2. **Validation**: Validate user inputs and external data before processing
3. **Formatting**: Use consistent formatting for currency and percentages across UI
4. **Calculations**: Use Decimal for financial calculations to avoid floating-point errors
5. **Error Handling**: Catch ValueError from validation functions and provide user feedback

## Type Safety

All functions use comprehensive type hints:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal
    from datetime import datetime
    import polars as pl
    from loguru import Logger

# Function signatures are fully typed
def calculate_pnl(
    entry_price: Decimal,
    current_price: Decimal,
    size: Decimal,
    side: str
) -> Decimal:
    ...
```

This ensures type checkers (mypy, pyright) can catch type errors at development time.
