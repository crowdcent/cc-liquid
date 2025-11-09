# TUI API Reference

Complete API reference for all cc-flow TUI components organized by type.

## Table of Contents

- [Application](#application)
- [Screens](#screens)
- [Widgets](#widgets)
- [Modals](#modals)
- [Utilities](#utilities)

---

## Application

### CCLiquidApp

Main application class orchestrating the TUI.

**Module**: `cc_flow.ui.app`

```python
class CCLiquidApp(App):
    """Main application for cc-liquid TUI."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `CSS_PATH` | str | Path to stylesheet ("styles/main.tcss") |
| `TITLE` | str | Application title shown in header |
| `SUB_TITLE` | str | Application subtitle |
| `BINDINGS` | list[Binding] | Key bindings for navigation |
| `exchange` | Exchange | Exchange implementation |
| `data_source` | DataSource | Data source for predictions |
| `config` | TradingConfig | Trading configuration |
| `orchestrator` | TradingOrchestrator | Trading orchestrator |
| `current_screen` | str | Name of currently displayed screen |

#### Methods

##### `__init__(exchange, data_source, config, **kwargs)`

Initialize app with core services.

**Parameters**:
- `exchange` (Exchange): Exchange implementation
- `data_source` (DataSource): Data source for predictions
- `config` (TradingConfig): Trading configuration
- `**kwargs`: Additional Textual app arguments

**Example**:
```python
app = CCLiquidApp(
    exchange=exchange,
    data_source=data_source,
    config=config
)
app.run()
```

##### `action_show_dashboard()`

Show dashboard screen. Bound to `d` key.

##### `action_show_trading()`

Show trading screen. Bound to `t` key.

##### `action_show_account()`

Show account screen. Bound to `a` key.

##### `action_show_backtest()`

Show backtest screen. Bound to `b` key.

##### `action_show_optimize()`

Show optimize screen. Bound to `o` key.

##### `action_show_history()`

Show history screen. Bound to `h` key.

##### `action_show_config()`

Show config screen. Bound to `c` key.

---

## Screens

### DashboardScreen

Live portfolio monitoring with auto-refresh.

**Module**: `cc_flow.ui.screens.dashboard`

```python
class DashboardScreen(Screen):
    """Live dashboard for portfolio monitoring."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `orchestrator` | TradingOrchestrator | Trading orchestrator instance |
| `refresh_interval` | float | Seconds between auto-refresh (default: 2.0) |

#### Methods

##### `__init__(orchestrator, **kwargs)`

Initialize dashboard screen.

**Parameters**:
- `orchestrator` (TradingOrchestrator): Trading orchestrator instance
- `**kwargs`: Additional screen arguments

##### `refresh_data()` (async)

Refresh all dashboard data. Decorated with `@work(exclusive=True)`.

**Auto-called**: Every 2 seconds by interval timer

**Fetches**:
- Account state from exchange
- Open positions
- Open orders
- Next rebalance time

---

### TradingScreen

Manual rebalancing workflow with trade plan preview.

**Module**: `cc_flow.ui.screens.trading`

```python
class TradingScreen(Screen):
    """Trading screen for manual rebalancing."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `orchestrator` | TradingOrchestrator | Trading orchestrator instance |
| `current_plan` | RebalancePlan \| None | Currently active plan |
| `execution_result` | ExecutionResult \| None | Last execution result |

#### Methods

##### `__init__(orchestrator, **kwargs)`

Initialize trading screen.

##### `action_plan_rebalance()` (async)

Generate rebalancing plan. Decorated with `@work(exclusive=True)`.

**Creates**: RebalancePlan with executable and skipped trades

**Updates**: Trade plan table and enables execute button

##### `action_execute_plan()`

Show confirmation modal before execution.

**Requires**: `current_plan` is not None

**Shows**: ConfirmExecutionModal

##### `_on_execute_confirmed(confirmed)` (async)

Callback after confirmation modal.

**Parameters**:
- `confirmed` (bool): Whether user confirmed execution

---

### AccountScreen

Detailed account view with comprehensive metrics.

**Module**: `cc_flow.ui.screens.account`

```python
class AccountScreen(Screen):
    """Detailed account information screen."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `orchestrator` | TradingOrchestrator | Trading orchestrator instance |

#### Methods

##### `__init__(orchestrator, **kwargs)`

Initialize account screen.

##### `refresh_account_data()` (async)

Refresh account data from exchange. Decorated with `@work(exclusive=True)`.

**Called**: On mount and when refresh button is clicked

**Fetches**: Current portfolio snapshot

**Updates**: Account metrics, margin breakdown, positions table

---

### BacktestScreen

Strategy backtesting with historical data.

**Module**: `cc_flow.ui.screens.backtest`

```python
class BacktestScreen(Screen):
    """Backtest screen for strategy testing."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `orchestrator` | TradingOrchestrator | Trading orchestrator instance |
| `current_results` | BacktestResults \| None | Last backtest results |

#### Methods

##### `__init__(orchestrator, **kwargs)`

Initialize backtest screen.

##### `run_backtest()` (async)

Execute backtest with current parameters. Decorated with `@work(exclusive=True)`.

**Reads**: Parameter inputs (num_long, num_short, leverage, etc.)

**Validates**: All inputs before running

**Updates**: Results metrics and charts

---

### OptimizeScreen

Parameter optimization with grid search.

**Module**: `cc_flow.ui.screens.optimize`

```python
class OptimizeScreen(Screen):
    """Optimize screen for parameter grid search."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `orchestrator` | TradingOrchestrator | Trading orchestrator instance |
| `optimization_results` | list[dict] \| None | Grid search results |

#### Methods

##### `__init__(orchestrator, **kwargs)`

Initialize optimize screen.

##### `run_optimization()` (async)

Execute parameter grid search. Decorated with `@work(exclusive=True)`.

**Reads**: Parameter ranges from inputs

**Runs**: Parallel backtests across parameter space

**Updates**: Results table sorted by selected metric

---

### HistoryScreen

Trade history analysis with filtering.

**Module**: `cc_flow.ui.screens.history`

```python
class HistoryScreen(Screen):
    """History screen for trade analysis."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `orchestrator` | TradingOrchestrator | Trading orchestrator instance |
| `trade_history` | list[dict] \| None | Loaded trade history |

#### Methods

##### `__init__(orchestrator, **kwargs)`

Initialize history screen.

##### `load_history()` (async)

Load trade history with date filters. Decorated with `@work(exclusive=True)`.

**Reads**: Start and end date from inputs

**Fetches**: Historical trades from exchange

**Updates**: History table and summary statistics

---

### ConfigScreen

Configuration viewing and editing.

**Module**: `cc_flow.ui.screens.config`

```python
class ConfigScreen(Screen):
    """Config screen for settings management."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `config` | TradingConfig | Trading configuration instance |

#### Methods

##### `__init__(config, **kwargs)`

Initialize config screen.

##### `display_config()`

Display current configuration in formatted view.

**Shows**: All config sections with syntax highlighting

---

## Widgets

### PortfolioTable

DataTable for displaying trading positions.

**Module**: `cc_flow.ui.widgets.portfolio_table`

```python
class PortfolioTable(DataTable):
    """Reusable portfolio positions table."""
```

#### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `zebra_stripes` | bool | True | Alternating row colors |
| `cursor_type` | str | "row" | Cursor style |
| `show_footer` | bool | True | Display totals footer |

#### Methods

##### `update_positions(positions)`

Update table with new positions.

**Parameters**:
- `positions` (list[Position]): List of Position objects

**Sorting**: By PnL descending (highest profit first)

**Footer**: Shows total unrealized PnL

**Example**:
```python
table = PortfolioTable()
table.update_positions(positions)
```

---

### MetricsPanel

Grid widget for key-value metrics display.

**Module**: `cc_flow.ui.widgets.metrics_panel`

```python
class MetricsPanel(Grid):
    """Reusable metrics panel with color-coded display."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `metrics` | dict[str, str] | Current metrics {label: value} |

#### Methods

##### `update_metrics(metrics)`

Update metrics display.

**Parameters**:
- `metrics` (dict[str, str]): Dictionary of {label: formatted_value}

**Example**:
```python
panel = MetricsPanel()
panel.update_metrics({
    "Account Value": "$100,000.00",
    "Total PnL": panel.format_pnl(Decimal("5000"))
})
```

##### `format_currency(value)` (static)

Format decimal as currency.

**Parameters**:
- `value` (Decimal): Value to format

**Returns**: str like "$1,234.56"

##### `format_percentage(value)` (static)

Format decimal as percentage.

**Parameters**:
- `value` (Decimal): Value to format (e.g., 15.5 for 15.5%)

**Returns**: str like "15.50%"

##### `format_leverage(value)` (static)

Format leverage value.

**Parameters**:
- `value` (Decimal): Leverage value

**Returns**: str like "1.50x"

##### `format_pnl(value)`

Format PnL with color-coding.

**Parameters**:
- `value` (Decimal): PnL value

**Returns**: Rich markup string with green (positive), red (negative), or neutral color

**Example**:
```python
panel = MetricsPanel()
formatted = panel.format_pnl(Decimal("5000"))
# Returns: "[green]+$5,000.00[/green]"
```

##### `format_pnl_percentage(value)`

Format PnL percentage with color-coding.

**Parameters**:
- `value` (Decimal): Percentage value

**Returns**: Rich markup string with color-coded percentage

---

### OrderBookWidget

Container displaying market depth with bids and asks.

**Module**: `cc_flow.ui.widgets.order_book`

```python
class OrderBookWidget(Container):
    """Order book display widget with real-time updates."""
```

#### Attributes (Reactive)

| Attribute | Type | Description |
|-----------|------|-------------|
| `spread` | Decimal \| None | Current spread (best_ask - best_bid) |
| `best_bid` | Decimal \| None | Highest bid price |
| `best_ask` | Decimal \| None | Lowest ask price |

#### Methods

##### `update_book(bids, asks)`

Update order book display.

**Parameters**:
- `bids` (Sequence[dict[str, Decimal]]): Bid orders with "price" and "size" keys
- `asks` (Sequence[dict[str, Decimal]]): Ask orders with "price" and "size" keys

**Sorting**: Bids descending, asks ascending

**Limits**: Top 10 levels per side

**Example**:
```python
order_book = OrderBookWidget()
bids = [{"price": Decimal("50000"), "size": Decimal("0.5")}]
asks = [{"price": Decimal("50100"), "size": Decimal("0.3")}]
order_book.update_book(bids, asks)
```

##### `get_spread_formatted()`

Get formatted spread string.

**Returns**: str like "$100.00" or "No spread data"

##### `get_best_bid_formatted()`

Get formatted best bid.

**Returns**: str like "$50,000.00" or "—"

##### `get_best_ask_formatted()`

Get formatted best ask.

**Returns**: str like "$50,100.00" or "—"

---

### TradePlanWidget

Static widget for trade plan preview.

**Module**: `cc_flow.ui.widgets.trade_plan`

```python
class TradePlanWidget(Static):
    """Reusable trade plan preview widget."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `_current_plan` | RebalancePlan \| None | Currently displayed plan |

#### Methods

##### `update_plan(plan)`

Update widget with new rebalance plan.

**Parameters**:
- `plan` (RebalancePlan): Rebalance plan to display

**Displays**:
- Summary statistics (buy/sell counts, notional, fees)
- Executable trades table
- Skipped trades table (if any)

**Example**:
```python
widget = TradePlanWidget()
widget.update_plan(rebalance_plan)
```

---

### ChartWidget

Static widget for ASCII sparkline charts.

**Module**: `cc_flow.ui.widgets.chart`

```python
class ChartWidget(Static):
    """ASCII chart widget for equity curves and drawdown."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `renderable` | str | Current chart content |

#### Methods

##### `plot_equity_curve(returns)`

Plot equity curve from returns data.

**Parameters**:
- `returns` (pl.DataFrame): DataFrame with "date" and "portfolio_value" columns

**Displays**: ASCII sparkline with min/max header

**Example**:
```python
chart = ChartWidget()
chart.plot_equity_curve(returns_df)
```

##### `plot_drawdown(returns)`

Plot drawdown chart.

**Parameters**:
- `returns` (pl.DataFrame): DataFrame with "drawdown" or "daily_return" column

**Calculates**: Drawdown if not present in DataFrame

**Displays**: Inverted ASCII sparkline with max drawdown header

**Example**:
```python
chart = ChartWidget()
chart.plot_drawdown(returns_df)
```

---

## Modals

### ConfirmModal

Yes/No confirmation dialog.

**Module**: `cc_flow.ui.widgets.modals`

```python
class ConfirmModal(ModalScreen[bool]):
    """Yes/No confirmation dialog with brutalist styling."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | str | Confirmation message |
| `title` | str | Modal title |

#### Methods

##### `__init__(message, title="Confirm", **kwargs)`

Initialize confirmation modal.

**Parameters**:
- `message` (str): Message to display
- `title` (str): Modal title (default: "Confirm")
- `**kwargs`: Additional arguments

**Returns**: bool (True if confirmed, False if declined)

**Example**:
```python
result = await self.app.push_screen_wait(
    ConfirmModal("Execute trades?", title="Confirm")
)
if result:
    execute_trades()
```

#### Keybindings

- `Enter`: Confirm (returns True)
- `Escape`: Cancel (returns False)
- `Tab`/`Shift+Tab`: Navigate buttons

---

### ErrorModal

Error message display with error styling.

**Module**: `cc_flow.ui.widgets.modals`

```python
class ErrorModal(ModalScreen[None]):
    """Error message display with error styling."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | str | Main error message |
| `details` | str \| None | Optional error details |
| `title` | str | Modal title |

#### Methods

##### `__init__(message, details=None, title="Error", **kwargs)`

Initialize error modal.

**Parameters**:
- `message` (str): Main error message
- `details` (str \| None): Optional detailed error info
- `title` (str): Modal title (default: "Error")
- `**kwargs`: Additional arguments

**Example**:
```python
await self.app.push_screen_wait(
    ErrorModal(
        "Trade failed",
        details="Insufficient margin",
        title="Execution Error"
    )
)
```

#### Keybindings

- `Enter`: Dismiss
- `Escape`: Dismiss

---

### InfoModal

Information message display with success styling.

**Module**: `cc_flow.ui.widgets.modals`

```python
class InfoModal(ModalScreen[None]):
    """Information message display with success styling."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | str | Main information message |
| `details` | str \| None | Optional details |
| `title` | str | Modal title |

#### Methods

##### `__init__(message, details=None, title="Information", **kwargs)`

Initialize information modal.

**Parameters**:
- `message` (str): Main information message
- `details` (str \| None): Optional detailed info
- `title` (str): Modal title (default: "Information")
- `**kwargs`: Additional arguments

**Example**:
```python
await self.app.push_screen_wait(
    InfoModal(
        "Rebalance complete",
        details="8/10 trades executed",
        title="Success"
    )
)
```

---

### InputModal

Text input dialog with validation support.

**Module**: `cc_flow.ui.widgets.modals`

```python
class InputModal(ModalScreen[str | None]):
    """Text input dialog with validation support."""
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `prompt` | str | Prompt message |
| `title` | str | Modal title |
| `default_value` | str | Default input value |
| `placeholder` | str | Placeholder text |

#### Methods

##### `__init__(prompt, title="Input", default_value="", placeholder="", **kwargs)`

Initialize input modal.

**Parameters**:
- `prompt` (str): Prompt message
- `title` (str): Modal title (default: "Input")
- `default_value` (str): Default value (default: "")
- `placeholder` (str): Placeholder text (default: "")
- `**kwargs`: Additional arguments

**Returns**: str | None (input value if confirmed, None if cancelled)

**Example**:
```python
symbol = await self.app.push_screen_wait(
    InputModal(
        "Enter symbol:",
        title="Symbol Selection",
        default_value="BTC-USD"
    )
)
if symbol:
    load_data(symbol)
```

#### Keybindings

- `Enter`: Submit input (returns value)
- `Escape`: Cancel (returns None)
- `Tab`: Move between input and buttons

---

## Utilities

### Color Constants

**Module**: `cc_flow.ui.widgets.metrics_panel`

```python
COLOR_CYAN = "#62e4fb"      # Primary accent
COLOR_PURPLE = "#4152A8"    # Headers and titles
COLOR_GREEN = "#00ff00"     # Success/positive
COLOR_RED = "#ff0000"       # Error/negative
COLOR_YELLOW = "#ffaa00"    # Warning
COLOR_WHITE = "#ffffff"     # Default text
```

### Trade Plan Formatters

**Module**: `cc_flow.ui.widgets.trade_plan_formatters`

#### Functions

##### `format_currency(value)`

Format Decimal as currency string.

**Parameters**:
- `value` (Decimal): Amount to format

**Returns**: str like "$1,234.56"

##### `format_size(value)`

Format position size with 4 decimal places.

**Parameters**:
- `value` (Decimal): Size to format

**Returns**: str like "1.5000"

##### `format_trade_type(trade_type)`

Format trade type string.

**Parameters**:
- `trade_type` (str): Trade type ("open", "close", "increase", "decrease")

**Returns**: str with capitalized, colored trade type

##### `style_side(side)`

Apply color styling to order side.

**Parameters**:
- `side` (OrderSide): Order side enum

**Returns**: Rich markup string (green for BUY, red for SELL)

##### `format_net_exposure(value)`

Format net exposure with color-coding.

**Parameters**:
- `value` (Decimal): Net exposure value

**Returns**: Colored string (green if positive, red if negative)

##### `get_portfolio_bias_label(num_buys, num_sells)`

Determine portfolio bias from trade counts.

**Parameters**:
- `num_buys` (int): Number of buy trades
- `num_sells` (int): Number of sell trades

**Returns**: str ("Long Biased", "Short Biased", "Balanced", etc.)

##### `determine_skip_reason(trade)`

Determine why a trade was skipped.

**Parameters**:
- `trade` (Trade): Skipped trade object

**Returns**: str explaining skip reason

---

## Type Definitions

### Common Types

```python
from decimal import Decimal
from typing import Sequence

# Position data
Position = {
    "coin": str,
    "side": str,  # "LONG" or "SHORT"
    "size": Decimal,
    "entry_price": Decimal,
    "mark_price": Decimal,
    "unrealized_pnl": Decimal,
    "liquidation_price": Decimal | None
}

# Order book level
OrderBookLevel = {
    "price": Decimal,
    "size": Decimal
}

# Metrics dictionary
Metrics = dict[str, str]  # {label: formatted_value}
```

---

## CSS Selectors

### Common IDs

| ID | Element | Screen |
|----|---------|--------|
| `#dashboard` | Main container | DashboardScreen |
| `#trading` | Main container | TradingScreen |
| `#account` | Main container | AccountScreen |
| `#positions-table` | DataTable | DashboardScreen |
| `#trades-table` | DataTable | TradingScreen |
| `#btn-plan` | Button | TradingScreen |
| `#btn-execute` | Button | TradingScreen |
| `#btn-refresh` | Button | AccountScreen |

### Common Classes

| Class | Purpose | Elements |
|-------|---------|----------|
| `.panel` | Panel container | Vertical/Container |
| `.section-title` | Section header | Static |
| `.button-row` | Button container | Horizontal |
| `.success` | Success text | Static |
| `.error` | Error text | Static |
| `.warning` | Warning text | Static |
| `.info` | Info text | Static |

---

## Event Types

### Button Events

```python
from textual.widgets import Button

def on_button_pressed(self, event: Button.Pressed) -> None:
    """Handle button press events."""
    button_id = event.button.id
```

### Key Events

```python
from textual.events import Key

def on_key(self, event: Key) -> None:
    """Handle keyboard events."""
    key = event.key
```

### Input Events

```python
from textual.widgets import Input

def on_input_submitted(self, event: Input.Submitted) -> None:
    """Handle input submission."""
    value = event.value
```

### DataTable Events

```python
from textual.widgets import DataTable

def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
    """Handle row selection."""
    row_key = event.row_key
```

---

## Further Reading

- [Widgets Usage Guide](widgets.md)
- [Screens Development Guide](screens.md)
- [TUI Index](index.md)
- [Textual API](https://textual.textualize.io/api/)
