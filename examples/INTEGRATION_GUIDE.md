# Composition-Based Strategy Integration Guide

This guide shows how to integrate the composition-based strategy system into `trader.py`.

## Overview

The composition system replaces the hardcoded `mode` dispatch with a flexible component-based architecture:

**Before:**
```python
if self.config.portfolio.rebalancing.mode == "rolling":
    return self.plan_rolling_rebalance(predictions)
return self.plan_rebalance(predictions)
```

**After:**
```python
strategy = StrategyFactory.create(self.config)
return strategy.plan(self, predictions, target_leverage, rank_power)
```

## Integration Steps

### Step 1: Update Config Structure

**File:** `src/cc_liquid/config.py`

```python
@dataclass
class StrategyConfig:
    """Trading strategy configuration."""
    name: str = "rolling_mode"  # Strategy identifier
    num_long: int = 10
    num_short: int = 10
    target_leverage: float = 1.0
    rank_power: float = 0.0
    params: dict = field(default_factory=dict)  # Strategy-specific params
    components: dict = field(default_factory=dict)  # Component overrides (optional)

@dataclass
class PortfolioConfig:
    """Portfolio configuration."""
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    stop_loss: StopLossConfig = field(default_factory=StopLossConfig)
    # Remove old fields: num_long, num_short, target_leverage, rank_power, rebalancing
```

### Step 2: Update Trader Class

**File:** `src/cc_liquid/trader.py`

Add strategy initialization:

```python
from .strategies.factory import StrategyFactory

class CCLiquid:
    def __init__(self, config: Config, callbacks: CCLiquidCallbacks | None = None):
        self.config = config
        self.callbacks = callbacks or NoOpCallbacks()

        # ... existing initialization ...

        # Initialize strategy from config
        self.strategy = StrategyFactory.create(config)
```

Replace `plan_rebalance_auto()`:

```python
def plan_rebalance_auto(self, predictions: pl.DataFrame | None = None) -> dict:
    """Plan rebalance using configured strategy."""
    # Delegate to composed strategy
    return self.strategy.plan(
        trader=self,
        predictions=predictions,
        target_leverage=self.config.portfolio.strategy.target_leverage,
        rank_power=self.config.portfolio.strategy.rank_power,
    )
```

Keep existing utility methods (strategies use them):
- `_get_target_positions()` - Used by entry managers
- `_calculate_trades()` - Used by composed strategies
- `_load_predictions()` - Used by strategies
- `get_positions()`, `get_account_value()` - Used by strategies

### Step 3: Migration Path for Existing Configs

To maintain backward compatibility during transition:

```python
# In Config.__post_init__()
def _migrate_legacy_config(self):
    """Convert old config format to new strategy format."""
    # Check if using old format
    if hasattr(self.portfolio, 'rebalancing'):
        old_mode = self.portfolio.rebalancing.mode

        # Map old mode to new strategy
        strategy_map = {
            "full": "full_mode",
            "rolling": "rolling_mode",
        }

        strategy_name = strategy_map.get(old_mode, "rolling_mode")

        # Convert to new format
        self.portfolio.strategy = StrategyConfig(
            name=strategy_name,
            num_long=getattr(self.portfolio, 'num_long', 10),
            num_short=getattr(self.portfolio, 'num_short', 10),
            target_leverage=getattr(self.portfolio, 'target_leverage', 1.0),
            rank_power=getattr(self.portfolio, 'rank_power', 0.0),
            params={
                "rolling_days": self.portfolio.rebalancing.rolling_days,
                "seed_full": self.portfolio.rebalancing.seed_full,
            } if old_mode == "rolling" else {},
        )
```

### Step 4: Update CLI Commands

**File:** `src/cc_liquid/cli.py`

Add strategy listing:

```python
@click.command()
def strategies():
    """List available trading strategies."""
    from .strategies.factory import StrategyFactory

    strategies = StrategyFactory.list_strategies()
    console.print("\n[cyan]Available Strategies:[/cyan]")

    for name in strategies:
        console.print(f"  • {name}")

    console.print("\nUse in config: portfolio.strategy.name = <strategy>\n")
```

Update `--set` overrides to support new structure:

```bash
# Old format
cc-liquid rebalance --set portfolio.rebalancing.mode=rolling

# New format
cc-liquid rebalance --set portfolio.strategy.name=rolling_mode
cc-liquid rebalance --set portfolio.strategy.params.rolling_days=30
```

### Step 5: Update Documentation

Update `docs/configuration.md` with new structure:

```yaml
portfolio:
  strategy:
    name: rolling_mode
    num_long: 60
    num_short: 60
    target_leverage: 3.0
    rank_power: 1.5
    params:
      rolling_days: 30
      seed_full: true
```

Add new guide: `docs/custom-strategies.md` showing how to:
1. Create custom signal generators
2. Compose new strategies
3. Register custom strategies
4. Configure via YAML

## Example: Adding a Custom Strategy

### 1. Create Custom Component

```python
# ~/.cc-liquid/custom_strategies/momentum_signals.py
from cc_liquid.strategies.components import SignalGenerator
import polars as pl

class MomentumSignals:
    """Select assets by momentum instead of meta-model."""

    def __init__(self, lookback_days: int = 14, num_long: int = 10, num_short: int = 10):
        self.lookback_days = lookback_days
        self.num_long = num_long
        self.num_short = num_short

    def generate_signals(self, predictions, date_col, asset_col, pred_col):
        # Calculate momentum (price change over lookback)
        momentum = predictions.with_columns([
            (pl.col(pred_col).pct_change(self.lookback_days)).alias("momentum")
        ])

        latest = momentum.group_by(asset_col).agg([
            pl.col("momentum").last(),
        ])

        sorted_momentum = latest.sort("momentum", descending=True)

        long_assets = sorted_momentum.head(self.num_long)[asset_col].to_list()
        short_assets = sorted_momentum.tail(self.num_short)[asset_col].to_list()

        return long_assets, short_assets
```

### 2. Register Custom Strategy

```python
# In your script or config initialization
from cc_liquid.strategies.factory import StrategyFactory
from cc_liquid.strategies.composed import ComposedStrategy
from cc_liquid.strategies.components import ImmediateEntry, RankPowerSizer, NoOpState
from custom_strategies.momentum_signals import MomentumSignals

def create_momentum_strategy(num_long, num_short, lookback_days=14, rank_power=0.0):
    return ComposedStrategy(
        signal_generator=MomentumSignals(lookback_days, num_long, num_short),
        entry_manager=ImmediateEntry(),
        exit_rules=[],
        position_sizer=RankPowerSizer(rank_power),
        state_manager=NoOpState(),
    )

# Register it
StrategyFactory.register_strategy("momentum", create_momentum_strategy)
```

### 3. Use in Config

```yaml
portfolio:
  strategy:
    name: momentum  # Your custom strategy
    num_long: 15
    num_short: 15
    target_leverage: 2.0
    params:
      lookback_days: 21
```

## Benefits of Composition Approach

### 1. Reusability
```python
# Same signal generator used by multiple strategies
TopNSignals(10, 10)  # Used by full, rolling, take-profit, etc.
```

### 2. Mix and Match
```python
# Combine any entry manager with any exit rule
rolling_with_stops = ComposedStrategy(
    signal_generator=TopNSignals(20, 20),
    entry_manager=VintageEntry(30, True),  # Rolling
    exit_rules=[StopLossExit(0.10)],        # + Stop loss
    position_sizer=RankPowerSizer(1.5),
    state_manager=VintageState(),
)
```

### 3. Testability
```python
# Test components in isolation
def test_take_profit_exit():
    exit_rule = TakeProfitExit(0.15)

    # Mock trader with position at 20% profit
    mock_trader = MockTrader(pnl_pct=0.20)

    should_exit = exit_rule.should_exit_positions(mock_trader)
    assert should_exit["BTC"] == True
```

### 4. Extensibility
```python
# Add new signal generator without touching existing code
class MLSignals:
    def generate_signals(self, predictions, ...):
        # Your ML model here
        return long_assets, short_assets
```

## Backward Compatibility

Old configs still work during migration:

```yaml
# Old format (still supported)
portfolio:
  num_long: 10
  num_short: 10
  target_leverage: 1.0
  rebalancing:
    mode: rolling
    rolling_days: 30
```

Gets auto-migrated to:

```yaml
# New format (internally)
portfolio:
  strategy:
    name: rolling_mode
    num_long: 10
    num_short: 10
    target_leverage: 1.0
    params:
      rolling_days: 30
```

## Testing Strategy

1. **Unit tests for components:**
   - `test_signals.py` - Test each signal generator
   - `test_entries.py` - Test entry managers
   - `test_exits.py` - Test exit rules
   - `test_sizing.py` - Test position sizers

2. **Integration tests for strategies:**
   - `test_full_mode.py` - Full mode end-to-end
   - `test_rolling_mode.py` - Rolling mode with vintages
   - `test_take_profit.py` - Take profit logic

3. **Backtesting:**
   ```python
   from cc_liquid.backtester import Backtester
   from cc_liquid.strategies.composed import create_rolling_with_take_profit_strategy

   strategy = create_rolling_with_take_profit_strategy(
       num_long=20, num_short=20,
       rolling_days=30, pnl_threshold_pct=0.15
   )

   backtester = Backtester(config, strategy=strategy)
   results = backtester.run()
   ```

## Migration Timeline

### Phase 1: Add Composition System (Non-breaking)
- Add all component modules
- Add StrategyFactory
- Keep existing `plan_rebalance_auto()` logic

### Phase 2: Dual Support
- Add migration layer
- Support both old and new config formats
- Add tests for both paths

### Phase 3: Deprecation
- Warn on old config format
- Update docs to new format
- Provide migration tool

### Phase 4: Full Migration
- Remove old code paths
- Clean up config structure
- Streamline trader.py
