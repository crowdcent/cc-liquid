# Composition-Based Strategy Architecture Summary

## Visual Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Trading Strategy (Composed)                   │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐│
│  │ SignalGenerator  │  │  EntryManager    │  │   ExitRule(s)  ││
│  │                  │  │                  │  │                ││
│  │ - TopNSignals    │  │ - ImmediateEntry │  │ - TakeProfit   ││
│  │ - MeanReversion  │  │ - VintageEntry   │  │ - StopLoss     ││
│  │ - Momentum       │  │                  │  │ - TimeBased    ││
│  └──────────────────┘  └──────────────────┘  └────────────────┘│
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ PositionSizer    │  │  StateManager    │                     │
│  │                  │  │                  │                     │
│  │ - RankPower      │  │ - NoOpState      │                     │
│  │ - EqualWeight    │  │ - VintageState   │                     │
│  │ - VolAdjusted    │  │ - DatabaseState  │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌────────────────────────┐
                    │   ComposedStrategy     │
                    │   .plan(trader, ...)   │
                    └────────────────────────┘
                                  │
                                  ▼
                    ┌────────────────────────┐
                    │   CCLiquid (Trader)    │
                    │   - get_positions()    │
                    │   - _calculate_trades()│
                    │   - execute_plan()     │
                    └────────────────────────┘
```

## Component Responsibilities

### SignalGenerator
**Answers:** WHAT to trade?

```python
def generate_signals(...) -> tuple[list[str], list[str]]:
    """Returns (long_assets, short_assets)"""
```

**Examples:**
- `TopNSignals`: Top N by prediction value (used by all modes)
- `MeanReversionSignals`: Oversold/overbought by z-score
- `MomentumSignals`: High momentum assets

### EntryManager
**Answers:** WHEN and HOW to enter positions?

```python
def calculate_target_positions(...) -> dict[str, float]:
    """Returns {asset: target_usd_notional}"""
```

**Examples:**
- `ImmediateEntry`: All at once (full mode, take-profit)
- `VintageEntry`: Staggered over N days (rolling mode)

### ExitRule
**Answers:** WHEN to close positions?

```python
def should_exit_positions(...) -> dict[str, bool]:
    """Returns {asset: should_exit}"""
```

**Examples:**
- `TakeProfitExit`: Close if PnL > threshold
- `StopLossExit`: Close if PnL < -threshold
- `TimeBasedExit`: Close after N days

### PositionSizer
**Answers:** HOW MUCH capital per position?

```python
def calculate_weights(...) -> dict[str, float]:
    """Returns {asset: signed_leverage_weight}"""
```

**Examples:**
- `RankPowerSizer`: Concentration by rank (used by all modes)
- `EqualWeightSizer`: Same size all positions
- `VolatilityAdjustedSizer`: Inverse volatility weighting

### StateManager
**Answers:** What to persist between rebalances?

```python
def get_state() -> dict:
    """Load persisted state"""

def update_state(updates: dict):
    """Save state updates"""
```

**Examples:**
- `NoOpState`: No persistence (full mode, take-profit)
- `VintageState`: Track vintages (rolling mode)
- `DatabaseState`: Cloud persistence

## Strategy Composition Examples

### Full Mode
```python
ComposedStrategy(
    signal_generator = TopNSignals(20, 20),
    entry_manager    = ImmediateEntry(),
    exit_rules       = [FullRebalanceExit()],
    position_sizer   = RankPowerSizer(1.5),
    state_manager    = NoOpState(),
)
```

### Rolling Mode
```python
ComposedStrategy(
    signal_generator = TopNSignals(60, 60),
    entry_manager    = VintageEntry(30, seed_full=True),
    exit_rules       = [],  # Handled by vintage expiry
    position_sizer   = RankPowerSizer(1.5),
    state_manager    = VintageState(),
)
```

### Take Profit Auto
```python
ComposedStrategy(
    signal_generator = TopNSignals(15, 15),
    entry_manager    = ImmediateEntry(),
    exit_rules       = [TakeProfitExit(0.15)],
    position_sizer   = RankPowerSizer(2.0),
    state_manager    = NoOpState(),
)
```

### Rolling + Take Profit (Hybrid)
```python
ComposedStrategy(
    signal_generator = TopNSignals(40, 40),
    entry_manager    = VintageEntry(30, seed_full=True),
    exit_rules       = [TakeProfitExit(0.20)],
    position_sizer   = RankPowerSizer(1.5),
    state_manager    = VintageState(),
)
```

## Data Flow

```
1. YAML Config
   ↓
2. StrategyFactory.create(config)
   ↓
3. ComposedStrategy instance
   ↓
4. strategy.plan(trader, predictions, ...)
   ↓
5. ┌─ SignalGenerator: Generate long/short lists
   │
   ├─ EntryManager: Calculate target positions
   │
   ├─ ExitRule(s): Check if positions should close
   │
   ├─ Trader: Calculate trades (target - current)
   │
   └─ StateManager: Persist state
   ↓
6. Return plan dict: {trades, target_positions, ...}
   ↓
7. trader.execute_plan(plan)
   ↓
8. Orders placed on Hyperliquid
```

## Component Reuse Matrix

| Strategy | Signal | Entry | Exit | Sizer | State |
|----------|--------|-------|------|-------|-------|
| **Full** | TopN | Immediate | FullRebalance | RankPower | NoOp |
| **Rolling** | TopN | Vintage | - | RankPower | Vintage |
| **TakeProfit** | TopN | Immediate | TakeProfit | RankPower | NoOp |
| **TP+SL** | TopN | Immediate | TP, SL | RankPower | NoOp |
| **Rolling+TP** | TopN | Vintage | TakeProfit | RankPower | Vintage |
| **MeanRev** | MeanRev | Immediate | TakeProfit | Equal | NoOp |

**Shared components** (green = reused):
- `TopNSignals`: 83% reuse
- `RankPowerSizer`: 83% reuse
- `ImmediateEntry`: 67% reuse
- `TakeProfitExit`: 50% reuse

## Configuration Schema

```yaml
portfolio:
  strategy:
    # Strategy identifier (maps to factory)
    name: rolling_mode | full_mode | take_profit_auto | custom

    # SHARED across all strategies
    num_long: 60
    num_short: 60
    target_leverage: 3.0
    rank_power: 1.5

    # STRATEGY-SPECIFIC parameters
    params:
      # Example: rolling mode
      rolling_days: 30
      seed_full: true

      # Example: take profit
      pnl_threshold_pct: 0.15

      # Example: custom strategy
      custom_param: value

    # OPTIONAL: Explicit component overrides
    components:
      signal_generator:
        type: TopNSignals
        # params...

      entry_manager:
        type: VintageEntry
        rolling_days: 30

      exit_rules:
        - type: TakeProfitExit
          threshold_pct: 0.15

      position_sizer:
        type: RankPowerSizer
        rank_power: 1.5

      state_manager:
        type: VintageState
        state_file: .cc-liquid-state.json
```

## Key Design Decisions

### 1. Protocol-Based Components (Not Classes)

```python
class SignalGenerator(Protocol):
    def generate_signals(...) -> tuple[list[str], list[str]]: ...
```

**Why:**
- Duck typing: any object with matching methods works
- No forced inheritance
- Easy to mock for testing

### 2. Composition Over Inheritance

```python
# NOT this:
class RollingStrategy(BaseStrategy):
    def plan(self): ...

# THIS:
strategy = ComposedStrategy(
    signal_generator=TopNSignals(),
    entry_manager=VintageEntry(),
    ...
)
```

**Why:**
- Flexibility: mix and match freely
- Testability: test components in isolation
- Reusability: components shared across strategies

### 3. Strategy Receives Trader Reference

```python
def plan(self, trader: CCLiquid, ...):
    # Components can access trader utilities
    positions = trader.get_positions()
    trades = trader._calculate_trades(target, current)
```

**Why:**
- Strategies use existing trader utilities
- No code duplication
- Backward compatibility with current architecture

### 4. Exit Rules Use OR Logic

```python
exit_rules = [
    TakeProfitExit(0.15),
    StopLossExit(0.10),
]
# Exits if EITHER rule triggers
```

**Why:**
- Intuitive: "take profit OR stop loss"
- Easy to combine multiple exits
- Can extend to AND logic if needed

### 5. State Manager Abstraction

```python
state_manager.get_state()
state_manager.update_state({...})
```

**Why:**
- Swap JSON ↔ Database easily
- Testing with InMemoryState
- Cloud deployments with DatabaseState

## Comparison to Current Architecture

### Current (Hardcoded Modes)

```python
# trader.py:431
def plan_rebalance_auto(self, predictions):
    if self.config.portfolio.rebalancing.mode == "rolling":
        return self.plan_rolling_rebalance(predictions)
    return self.plan_rebalance(predictions)
```

**Problems:**
- ❌ Adding new mode requires modifying trader.py
- ❌ Logic scattered across multiple methods
- ❌ Hard to test modes in isolation
- ❌ Can't combine modes (rolling + take-profit)

### Proposed (Composition)

```python
# trader.py (updated)
def plan_rebalance_auto(self, predictions):
    return self.strategy.plan(self, predictions, target_leverage, rank_power)
```

**Benefits:**
- ✅ New strategies via factory registration
- ✅ Logic isolated in components
- ✅ Test components independently
- ✅ Mix and match freely

## Migration Path

### Phase 1: Add Composition System ✓
- [x] Create component modules
- [x] Create ComposedStrategy class
- [x] Create StrategyFactory
- [x] Create example configs

### Phase 2: Integrate with Trader
- [ ] Update Config dataclasses
- [ ] Add strategy initialization in trader.__init__
- [ ] Replace plan_rebalance_auto
- [ ] Add backward compatibility layer

### Phase 3: Testing
- [ ] Unit tests for each component
- [ ] Integration tests for composed strategies
- [ ] Backtesting comparison (old vs new)

### Phase 4: Documentation
- [ ] Update configuration docs
- [ ] Add custom strategy guide
- [ ] Migration guide for users

### Phase 5: Deployment
- [ ] Beta release with dual support
- [ ] Deprecation warnings on old format
- [ ] Full migration in v0.2.0

## Performance Considerations

### Component Overhead

**Concern:** Does composition add latency?

**Analysis:**
- Protocol dispatch: ~0.1μs (negligible)
- Component method calls: Same as current methods
- State persistence: Same as current JSON writes

**Verdict:** No measurable performance impact

### Memory Usage

**Concern:** More objects = more memory?

**Analysis:**
- Components are lightweight (mostly stateless)
- State only in StateManager (same as current)
- One strategy instance per trader (same as current)

**Verdict:** No significant memory increase

## Testing Strategy

### Component Unit Tests

```python
def test_top_n_signals():
    signals = TopNSignals(num_long=5, num_short=3)
    long, short = signals.generate_signals(mock_predictions, ...)
    assert len(long) == 5
    assert len(short) == 3

def test_take_profit_exit():
    exit_rule = TakeProfitExit(0.15)
    should_exit = exit_rule.should_exit_positions(mock_trader_with_profit)
    assert should_exit["BTC"] == True
```

### Integration Tests

```python
def test_full_mode_strategy():
    strategy = create_full_mode_strategy(10, 10, rank_power=1.5)
    plan = strategy.plan(trader, predictions, target_leverage=2.0, rank_power=1.5)
    assert len(plan["trades"]) > 0
    assert plan["target_positions"] is not None
```

### Backtesting Validation

```python
# Compare old vs new implementation
results_old = backtest_with_old_rolling_mode(config)
results_new = backtest_with_composed_rolling_mode(config)

# Should produce identical results
assert_close(results_old["sharpe"], results_new["sharpe"])
assert_close(results_old["total_return"], results_new["total_return"])
```

## Questions & Answers

### Q: Does this replace the current modes?
**A:** No, current full/rolling modes become pre-composed strategies. Users see no difference.

### Q: Can I still use simple YAML config?
**A:** Yes! Factory creates strategies from YAML. Python modules only for custom components.

### Q: Is this backward compatible?
**A:** Yes, migration layer converts old configs to new format automatically.

### Q: How do I create a custom strategy?
**A:** Write custom component (e.g., signal generator), compose with standard components, register factory.

### Q: Can strategies access trader utilities?
**A:** Yes, strategies receive trader reference and call existing utilities.

### Q: How are vintages handled in rolling mode?
**A:** Same as before - VintageEntry contains the logic, VintageState persists data.

### Q: Can I combine rolling entry with take profit exit?
**A:** Yes! That's the power of composition. See `create_rolling_with_take_profit_strategy`.

### Q: What if I want database persistence?
**A:** Use `DatabaseState` instead of `VintageState`. Same interface, different backend.

## Conclusion

The composition-based architecture provides:

1. **Extensibility** - Add strategies without modifying core
2. **Reusability** - 60-80% component reuse
3. **Testability** - Isolated component testing
4. **Flexibility** - Mix and match freely
5. **Maintainability** - Single responsibility per component

**Result:** Transform from "hardcoded modes" to "composable plugin system" while maintaining full backward compatibility.

**Files:** See `examples/` directory for complete POC implementation.
