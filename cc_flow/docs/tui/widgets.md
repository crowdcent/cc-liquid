# Widgets Usage Guide

This guide covers all reusable TUI widgets in cc-flow, with practical examples and best practices.

## Overview

cc-flow provides six main widget categories:

1. **Data Display**: PortfolioTable, MetricsPanel, OrderBookWidget
2. **Visualization**: ChartWidget
3. **Interactive**: TradePlanWidget
4. **Dialogs**: ConfirmModal, ErrorModal, InfoModal, InputModal

All widgets follow the brutalist design philosophy with high-contrast colors and functional layouts.

---

## PortfolioTable

A specialized DataTable for displaying trading positions with automatic formatting, color-coded PnL, and sortable columns.

### Features

- Auto-formatted columns (decimals, currency)
- Color-coded PnL (green positive, red negative)
- Sortable by any column (default: PnL descending)
- Shows side (LONG/SHORT), size, prices, and PnL
- Displays total portfolio value in footer
- Zebra striping for readability
- Graceful error handling

### Visual Example

```
┌─────────────────────────────────────────────────────────────────┐
│ Asset │ Side  │ Size   │ Entry     │ Mark      │ PnL       │ PnL %   │
├─────────────────────────────────────────────────────────────────┤
│ BTC   │ LONG  │ 1.5000 │ $50,000   │ $52,000   │ +$3,000   │ +4.00%  │
│ ETH   │ SHORT │ 10.000 │ $3,000    │ $2,900    │ +$1,000   │ +3.33%  │
│ SOL   │ LONG  │ 100.00 │ $100      │ $95       │ -$500     │ -5.00%  │
├─────────────────────────────────────────────────────────────────┤
│ TOTAL │       │        │           │           │ +$3,500   │         │
└─────────────────────────────────────────────────────────────────┘
```

### Usage

```python
from cc_flow.ui.widgets.portfolio_table import PortfolioTable
from cc_flow.domain.account import Position
from decimal import Decimal

# Create widget
table = PortfolioTable()

# Create positions data
positions = [
    Position(
        coin="BTC",
        side="LONG",
        size=Decimal("1.5"),
        entry_price=Decimal("50000"),
        mark_price=Decimal("52000"),
        value=Decimal("78000"),
        unrealized_pnl=Decimal("3000"),
        return_pct=Decimal("0.04")
    ),
    Position(
        coin="ETH",
        side="SHORT",
        size=Decimal("10.0"),
        entry_price=Decimal("3000"),
        mark_price=Decimal("2900"),
        value=Decimal("29000"),
        unrealized_pnl=Decimal("1000"),
        return_pct=Decimal("0.0333")
    )
]

# Update table with positions
table.update_positions(positions)
```

### Common Patterns

**Empty Portfolio Handling**
```python
# PortfolioTable handles empty lists gracefully
table.update_positions([])  # Clears table, no error
```

**Custom Styling**
```python
# Disable footer
table.show_footer = False

# Disable cursor
table.cursor_type = "none"

# Disable zebra stripes
table.zebra_stripes = False
```

### Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `zebra_stripes` | bool | True | Alternating row colors |
| `cursor_type` | str | "row" | Cursor style ("row", "cell", "none") |
| `show_footer` | bool | True | Display totals footer |

---

## MetricsPanel

A Grid-based widget for displaying key-value metrics with color-coded formatting and auto-formatting helpers.

### Features

- Color-coded PnL (green positive, red negative)
- Auto-formatting helpers for currency, percentage, leverage
- Dynamic updates
- Handles missing or error states gracefully
- Grid layout with label-value pairs
- Brutalist high-contrast design

### Visual Example

```
┌─────────────────────────────────────┐
│ Account Value:    $100,000.00       │
│ Total PnL:        +$5,000.00        │
│ Daily PnL:        -$500.00          │
│ Leverage:         1.5x / 3.0x       │
│ Win Rate:         65.50%            │
│ Sharpe Ratio:     1.85              │
└─────────────────────────────────────┘
```

### Usage

```python
from cc_flow.ui.widgets.metrics_panel import MetricsPanel
from decimal import Decimal

# Create widget
panel = MetricsPanel()

# Prepare metrics with formatting
metrics = {
    "Account Value": panel.format_currency(Decimal("100000.00")),
    "Total PnL": panel.format_pnl(Decimal("5000.00")),
    "Daily PnL": panel.format_pnl(Decimal("-500.00")),
    "Leverage": f"{Decimal('1.5'):.2f}x / {Decimal('3.0'):.2f}x",
    "Win Rate": panel.format_percentage(Decimal("65.50")),
    "Sharpe Ratio": f"{Decimal('1.85'):.2f}"
}

# Update panel
panel.update_metrics(metrics)
```

### Formatting Helpers

**Currency Formatting**
```python
formatted = MetricsPanel.format_currency(Decimal("100000.50"))
# Returns: "$100,000.50"
```

**PnL Formatting** (with color-coding)
```python
panel = MetricsPanel()

# Positive PnL (green)
formatted = panel.format_pnl(Decimal("5000.00"))
# Returns: "[green]+$5,000.00[/green]"

# Negative PnL (red)
formatted = panel.format_pnl(Decimal("-1500.00"))
# Returns: "[red]-$1,500.00[/red]"

# Zero PnL (neutral)
formatted = panel.format_pnl(Decimal("0"))
# Returns: "$0.00"
```

**Percentage Formatting** (with color-coding)
```python
panel = MetricsPanel()

formatted = panel.format_pnl_percentage(Decimal("15.5"))
# Returns: "[green]+15.50%[/green]"

formatted = panel.format_pnl_percentage(Decimal("-5.25"))
# Returns: "[red]-5.25%[/red]"
```

**Leverage Formatting**
```python
formatted = MetricsPanel.format_leverage(Decimal("1.5"))
# Returns: "1.50x"
```

### Common Patterns

**Building Comprehensive Metrics**
```python
from cc_flow.domain.account import PortfolioSnapshot

def build_metrics(snapshot: PortfolioSnapshot) -> dict[str, str]:
    panel = MetricsPanel()
    account = snapshot.account

    return {
        "Account Value": panel.format_currency(account.account_value),
        "Unrealized PnL": panel.format_pnl(snapshot.total_unrealized_pnl),
        "Current Leverage": panel.format_leverage(account.current_leverage),
        "Margin Used": panel.format_currency(account.margin_used),
        "Withdrawable": panel.format_currency(account.withdrawable),
    }
```

---

## OrderBookWidget

A Container widget displaying real-time market depth with bids (green) and asks (red) in separate tables.

### Features

- Displays bids and asks in color-coded tables
- Shows price, size, and cumulative total for each level
- Limits display to top 10 levels per side
- Calculates and displays spread
- Handles empty order books gracefully
- Real-time reactive updates

### Visual Example

```
┌────────────────────────────────────────────────────────────┐
│ Bids (Green)              │  Asks (Red)                    │
├───────────────────────────┼────────────────────────────────┤
│ Price      Size   Total   │  Price      Size   Total       │
│ $50,000   0.5000  0.5000  │  $50,100   0.3000  0.3000      │
│ $49,900   1.0000  1.5000  │  $50,200   0.8000  1.1000      │
│ $49,800   0.7500  2.2500  │  $50,300   0.5000  1.6000      │
└───────────────────────────┴────────────────────────────────┘
Spread: $100.00
```

### Usage

```python
from cc_flow.ui.widgets.order_book import OrderBookWidget
from decimal import Decimal

# Create widget
order_book = OrderBookWidget()

# Prepare order book data
bids = [
    {"price": Decimal("50000.00"), "size": Decimal("0.5")},
    {"price": Decimal("49900.00"), "size": Decimal("1.0")},
    {"price": Decimal("49800.00"), "size": Decimal("0.75")},
]

asks = [
    {"price": Decimal("50100.00"), "size": Decimal("0.3")},
    {"price": Decimal("50200.00"), "size": Decimal("0.8")},
    {"price": Decimal("50300.00"), "size": Decimal("0.5")},
]

# Update widget
order_book.update_book(bids, asks)

# Get formatted values
spread = order_book.get_spread_formatted()  # "$100.00"
best_bid = order_book.get_best_bid_formatted()  # "$50,000.00"
best_ask = order_book.get_best_ask_formatted()  # "$50,100.00"
```

### Common Patterns

**Real-time Updates**
```python
from textual import work

class MarketScreen(Screen):
    def on_mount(self):
        # Start auto-refresh
        self.set_interval(1.0, self.update_order_book)

    @work(exclusive=True)
    async def update_order_book(self):
        # Fetch from exchange
        bids, asks = await self.exchange.get_order_book("BTC")

        # Update widget
        order_book = self.query_one(OrderBookWidget)
        order_book.update_book(bids, asks)
```

**Empty Order Book Handling**
```python
# Widget handles empty data gracefully
order_book.update_book([], [])

# Spread will be None
assert order_book.spread is None
assert order_book.get_spread_formatted() == "No spread data"
```

### Reactive Properties

| Property | Type | Description |
|----------|------|-------------|
| `spread` | Decimal \| None | Current spread (best_ask - best_bid) |
| `best_bid` | Decimal \| None | Highest bid price |
| `best_ask` | Decimal \| None | Lowest ask price |

---

## TradePlanWidget

A Static widget displaying comprehensive trade plans including executable trades, skipped trades, and summary statistics.

### Features

- Color-coded buy (green) and sell (red) sides
- Summary metrics: trade counts, notional values, net exposure
- Portfolio bias indicators
- Estimated fees and costs
- Clear visual separation of executable vs skipped trades
- Rich table formatting

### Visual Example

```
┌──────────────────────── Trade Plan ────────────────────────┐
│ Summary                                                     │
│ Portfolio Bias: Long Biased                                 │
│                                                             │
│ Executable: 10 trades (7 buys, 3 sells)                    │
│                                                             │
│ Buy Notional:  $50,000.00                                   │
│ Sell Notional: $20,000.00                                   │
│ Net Exposure:  +$30,000.00                                  │
│                                                             │
│ Estimated Fees: $35.00                                      │
│                                                             │
│ Executable Trades                                           │
│ Symbol  Side  Type   Size    Price       Notional           │
│ BTC     BUY   OPEN   0.5000  $50,000.00  $25,000.00         │
│ ETH     SELL  CLOSE  5.0000  $3,000.00   $15,000.00         │
│                                                             │
│ Skipped Trades                                              │
│ Symbol  Side  Type   Reason                                 │
│ SOL     BUY   OPEN   Below minimum notional ($10)           │
└─────────────────────────────────────────────────────────────┘
```

### Usage

```python
from cc_flow.ui.widgets.trade_plan import TradePlanWidget
from cc_flow.domain.portfolio import RebalancePlan
from cc_flow.domain.orders import Trade, OrderSide, OrderType

# Create widget
widget = TradePlanWidget()

# Create trade plan
plan = RebalancePlan(
    executable_trades=[
        Trade(
            coin="BTC",
            side=OrderSide.BUY,
            trade_type="open",
            size=Decimal("0.5"),
            reference_price=Decimal("50000"),
            limit_price=Decimal("50100"),
            estimated_fee=Decimal("25")
        )
    ],
    skipped_trades=[
        Trade(
            coin="SOL",
            side=OrderSide.BUY,
            trade_type="open",
            size=Decimal("0.001"),
            reference_price=Decimal("100"),
            limit_price=None,
            estimated_fee=Decimal("0")
        )
    ],
    target_positions={},
    account_value=Decimal("100000"),
    leverage=Decimal("1.5")
)

# Update widget
widget.update_plan(plan)
```

### Portfolio Bias Indicators

The widget automatically determines portfolio bias:

- **Long Biased**: More buy trades than sells
- **Short Biased**: More sell trades than buys
- **Balanced**: Equal buy and sell trades
- **Long Only**: Only buy trades
- **Short Only**: Only sell trades
- **No Trades**: Empty plan

---

## ChartWidget

A Static widget for displaying time-series data as ASCII sparkline charts with auto-scaling.

### Features

- Equity curve plotting from portfolio values
- Drawdown plotting from returns data
- Auto-scaling to available data range
- Inverted mode for drawdown visualization
- Simple sparkline-style block characters

### Visual Example

```
Equity Curve ($95,000 - $105,000)
▁▂▃▄▅▆▇█████▇▆▅▄▃▂▁▂▃▄▅▆▇████

Drawdown (Max: -8.50%)
████▇▆▅▄▃▂▁▁▁▂▃▄▅▆▇████
```

### Usage

```python
from cc_flow.ui.widgets.chart import ChartWidget
import polars as pl

# Create widget
chart = ChartWidget()

# Prepare equity curve data
returns_df = pl.DataFrame({
    "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
    "portfolio_value": [100000.0, 105000.0, 103000.0],
    "daily_return": [0.0, 5000.0, -2000.0]
})

# Plot equity curve
chart.plot_equity_curve(returns_df)

# Plot drawdown
chart.plot_drawdown(returns_df)
```

### Common Patterns

**Backtest Results Visualization**
```python
from cc_flow.core.backtester import Backtester

async def display_backtest_results(backtester: Backtester):
    # Run backtest
    results = await backtester.run()

    # Create charts
    equity_chart = ChartWidget(id="equity-chart")
    dd_chart = ChartWidget(id="drawdown-chart")

    # Plot results
    equity_chart.plot_equity_curve(results.returns)
    dd_chart.plot_drawdown(results.returns)
```

**Empty Data Handling**
```python
# Widget handles empty DataFrames gracefully
empty_df = pl.DataFrame({"date": [], "portfolio_value": []})
chart.plot_equity_curve(empty_df)  # Shows "No data to plot"
```

---

## Modals

Four types of modal dialogs for user interaction: ConfirmModal, ErrorModal, InfoModal, and InputModal.

### ConfirmModal

Yes/No confirmation dialog.

**Visual Example**
```
┌────────────── Confirm Execution ───────────────┐
│                                                 │
│  Execute 10 trades?                             │
│                                                 │
│         [ Yes ]        [ No ]                   │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Usage**
```python
from cc_flow.ui.widgets.modals import ConfirmModal

# Show modal and wait for result
result = await self.app.push_screen_wait(
    ConfirmModal("Execute 10 trades?", title="Confirm Execution")
)

if result:
    # User confirmed
    execute_trades()
else:
    # User declined
    log.info("User cancelled execution")
```

**Keybindings**
- Enter: Confirm (returns True)
- Escape: Cancel (returns False)
- Tab/Shift+Tab: Navigate between buttons

---

### ErrorModal

Error message display with red border styling.

**Visual Example**
```
┌────────────── Execution Error ─────────────────┐
│                                                 │
│  Trade execution failed                         │
│                                                 │
│  Insufficient margin available                  │
│                                                 │
│                [ OK ]                           │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Usage**
```python
from cc_flow.ui.widgets.modals import ErrorModal

try:
    await execute_trade()
except InsufficientMarginError as e:
    await self.app.push_screen_wait(
        ErrorModal(
            "Trade execution failed",
            details=str(e),
            title="Execution Error"
        )
    )
```

**Keybindings**
- Enter: Dismiss
- Escape: Dismiss

---

### InfoModal

Information message display with success styling.

**Visual Example**
```
┌────────────── Execution Summary ───────────────┐
│                                                 │
│  Rebalance complete: 8/10 trades executed       │
│                                                 │
│  Portfolio value: $10,000                       │
│                                                 │
│                [ OK ]                           │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Usage**
```python
from cc_flow.ui.widgets.modals import InfoModal

await self.app.push_screen_wait(
    InfoModal(
        "Rebalance complete: 8/10 trades executed",
        details=f"Portfolio value: ${portfolio_value:,.2f}",
        title="Execution Summary"
    )
)
```

---

### InputModal

Text input dialog with validation support.

**Visual Example**
```
┌────────────── Symbol Selection ────────────────┐
│                                                 │
│  Enter trading symbol:                          │
│                                                 │
│  [ BTC-USD                    ]                 │
│                                                 │
│         [ OK ]      [ Cancel ]                  │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Usage**
```python
from cc_flow.ui.widgets.modals import InputModal

# Get input from user
symbol = await self.app.push_screen_wait(
    InputModal(
        "Enter trading symbol:",
        title="Symbol Selection",
        default_value="BTC-USD",
        placeholder="e.g., ETH-USD"
    )
)

if symbol:
    # User provided input
    load_data_for_symbol(symbol)
else:
    # User cancelled
    log.info("User cancelled input")
```

**Keybindings**
- Enter: Submit input (returns value)
- Escape: Cancel (returns None)
- Tab: Move between input field and buttons

---

## Best Practices

### Widget Lifecycle

1. **Initialization**: Create widget with default state
2. **Mounting**: Set up reactive properties and initial data
3. **Updates**: Call update methods to refresh display
4. **Cleanup**: Textual handles cleanup automatically

### Async Operations

Always use the `@work` decorator for async operations:

```python
from textual import work

@work(exclusive=True)
async def update_data(self):
    data = await fetch_from_api()
    widget.update(data)
```

### Error Handling

Widgets should handle errors gracefully:

```python
def update_positions(self, positions: list[Position]) -> None:
    try:
        # Update logic
        self._render_positions(positions)
    except Exception as e:
        log.error(f"Update failed: {e}")
        # Show error state, don't crash
        self.update("[red]Error loading positions[/red]")
```

### Performance

- Avoid updating widgets too frequently (debounce if needed)
- Use reactive properties for automatic updates
- Clear large tables before adding new data
- Limit displayed rows for large datasets

### Testing

Test widgets in isolation:

```python
from textual.app import App
import pytest

@pytest.mark.asyncio
async def test_portfolio_table():
    app = App()
    async with app.run_test():
        table = PortfolioTable()
        app.mount(table)

        # Test update
        table.update_positions(test_positions)

        # Verify state
        assert len(table.rows) == len(test_positions)
```

---

## Next Steps

- [Screens Development Guide](screens.md) - Learn to create custom screens
- [API Reference](api-reference.md) - Complete API documentation
- [Textual Documentation](https://textual.textualize.io/) - Textual framework
