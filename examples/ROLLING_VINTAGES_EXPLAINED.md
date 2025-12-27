# Rolling Vintage Rebalancing - Complete Explanation

## Overview

Rolling rebalancing is a **time-diversified trading strategy** that spreads position entries across multiple days using "vintages" - think of each vintage as a mini-portfolio created on a specific day.

Instead of rebalancing your entire portfolio at once (which exposes you to timing risk), rolling mode creates daily "slices" of your target allocation that naturally rotate over time.

## What is a Vintage?

A **vintage** is a collection of positions opened on a specific date. Each vintage:
- Has a **birth date** (when it was created)
- Contains a **fraction** of your total target allocation (1/N if you have N-day rolling)
- Stores positions as **units** (e.g., 0.1 BTC), not USD values
- **Expires** after N days (positions close)

### Example: 30-Day Rolling

```
Day 1:  Create Vintage_1 with 1/30 of target allocation
Day 2:  Create Vintage_2 with 1/30 of target allocation
Day 3:  Create Vintage_3 with 1/30 of target allocation
...
Day 30: Create Vintage_30 with 1/30 of target allocation
        → Portfolio now at FULL allocation (30 vintages × 1/30 each)

Day 31: Vintage_1 EXPIRES (positions close - it's 30 days old)
        Create Vintage_31 (new positions open)
        → Steady state: 1/30 expires, 1/30 opens every day
```

## Why Use Rolling Mode?

### 1. Time Diversification (Reduces Timing Risk)

**Problem with Full Mode:**
If you rebalance everything on Tuesday and it happens to be a local peak for your long positions (or trough for shorts), your entire portfolio suffers from that single bad entry point.

**Rolling Mode Solution:**
Your positions are spread across 30 different entry days. If one day has bad timing, it only affects 1/30 of your portfolio. The other 29 vintages entered at different prices, smoothing out timing risk.

**Analogy:**
- Full mode = Going all-in on one lottery ticket
- Rolling mode = Buying 30 lottery tickets over 30 days

### 2. Matches Prediction Horizon

If your predictions have a **30-day forward horizon** (like `pred_30d`):
- Each prediction captures expected alpha over the next 30 days
- After 30 days, that prediction has "expired" - the alpha window has closed
- Rolling mode naturally aligns by closing positions after 30 days

**Example:**
- Jan 1 prediction says "BTC will outperform over next 30 days"
- You open position on Jan 1
- Jan 31: That 30-day window is over → position closes
- Fresh Jan 31 prediction determines if you re-enter BTC

### 3. Reduced Turnover

When the same asset appears in consecutive days' top predictions, the system **nets** the trades:
- Old vintage expiring: Close 0.05 BTC
- New vintage opening: Buy 0.06 BTC
- **Actual trade:** Buy 0.01 BTC (the difference)

No need to fully close and reopen - you only trade the delta.

## How Vintages Work

### The Vintage Model in Detail

Each day in rolling mode:

1. **Prune expired vintages** (older than `rolling_days`)
2. **Create new vintage** for today with 1/N of target allocation
3. **Aggregate all vintages** to get total target positions
4. **Calculate trades** = Target - Current wallet positions
5. **Save vintage state** to JSON file

### Target-Sum Calculation

Your portfolio's **total target position** is the **sum of all active vintage positions**:

| Vintage | BTC | ETH | SOL | Birth Date |
|---------|-----|-----|-----|------------|
| Day 1   | 0.01 | -0.5 | — | 2024-01-01 |
| Day 2   | 0.02 | — | 10.0 | 2024-01-02 |
| Day 3   | — | -0.3 | 5.0 | 2024-01-03 |
| ... (27 more) | ... | ... | ... | ... |
| **Total Target** | **0.03** | **-0.8** | **15.0** | - |

Then calculate: `Trade = Total Target - Current Wallet Position` for each asset.

### Unit-Based Tracking (Critical Design)

Vintages store **asset quantities (units)**, not USD values. This prevents drift from price changes:

**Example:**
1. Day 1: Buy 0.1 BTC at $50,000 → Vintage stores "0.1 BTC"
2. BTC rises to $100,000 (position now worth $10,000 instead of $5,000)
3. Day 31: Vintage expires → Sell **0.1 BTC** (the original units)
4. ✅ No leftover position from price appreciation

**Why this matters:**
If we stored USD values, we'd have drift:
- Stored: "$5,000 of BTC"
- BTC doubled: now worth $10,000
- Close $5,000 worth → Still holding $5,000 worth (drift!)

By storing units, we close the exact position we opened.

## Configuration

### Basic Rolling Mode

```yaml
portfolio:
  num_long: 60
  num_short: 60
  target_leverage: 3.0
  rebalancing:
    mode: rolling           # Enable rolling mode
    rolling_days: 30        # Match to prediction horizon (e.g., pred_30d)
    seed_full: true         # Full deployment from day 1
    at_time: "18:15"        # Daily rebalance time (UTC)
```

### Key Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `mode` | `"full"` (default) or `"rolling"` | `rolling` |
| `rolling_days` | Vintage lifespan - match your prediction horizon | `30` for pred_30d |
| `seed_full` | Seed all vintages on first run (vs gradual ramp-up) | `true` |
| `every_n_days` | Ignored in rolling mode (always daily) | - |

## Cold Start Options

### Gradual Ramp-Up (`seed_full: false`)

Starts with minimal allocation and builds up over time:

```
Day 1:  1 vintage  = 1/30 of target leverage  (3.3%)
Day 2:  2 vintages = 2/30 of target leverage  (6.7%)
Day 15: 15 vintages = 15/30 of target leverage (50%)
Day 30: 30 vintages = 30/30 of target leverage (100%)
Day 31+: Steady state (1 expires, 1 opens daily)
```

**Pros:**
- Conservative approach
- Reduces risk on initial deployment
- Natural ramp-up period

**Cons:**
- Underinvested for first 30 days
- Miss potential alpha during ramp-up

### Immediate Full Deployment (`seed_full: true`)

Loads historical predictions and creates all vintages on Day 1:

```
Day 1:  System loads last 30 days of predictions
        Creates 30 vintages with staggered "birth dates":
        - Vintage from 29 days ago
        - Vintage from 28 days ago
        - ...
        - Vintage from today
        → Immediately at FULL target leverage (100%)

Day 2:  Oldest vintage (30 days old) expires
        Create new vintage for today
        → Already in steady state
```

**Pros:**
- Fully invested from Day 1
- Time-diversified entries from the start
- No ramp-up period

**Cons:**
- Requires historical prediction data (last `rolling_days` days)
- Higher initial capital deployment

## CLI Usage

### View Active Vintages

```bash
cc-liquid vintages
```

**Output:**
```
┌──────────────────────────────────────────────────────────┐
│               Active Vintages (30-day rolling)           │
├────────────┬─────┬────────────┬───────────┬─────────────┤
│ Birth Date │ Age │ Expires In │ Positions │ Value       │
├────────────┼─────┼────────────┼───────────┼─────────────┤
│ 2024-11-01 │ 29d │ 1d         │ 4         │ $1,234.56   │
│ 2024-11-02 │ 28d │ 2d         │ 4         │ $1,345.67   │
│ 2024-11-03 │ 27d │ 3d         │ 4         │ $1,456.78   │
│ ...        │ ... │ ...        │ ...       │ ...         │
│ 2024-11-30 │ 0d  │ 30d        │ 4         │ $1,567.89   │
└────────────┴─────┴────────────┴───────────┴─────────────┘

Total vintage value: $42,000.00
Active vintages: 30 of 30
```

### Rebalance with Rolling Mode

```bash
# Use config settings
cc-liquid rebalance

# Override mode from CLI
cc-liquid rebalance --set portfolio.rebalancing.mode=rolling

# Override rolling days
cc-liquid rebalance --set portfolio.rebalancing.rolling_days=30
```

### Backtest Rolling Mode

```bash
# Use config mode
cc-liquid analyze

# Override from CLI
cc-liquid analyze --set portfolio.rebalancing.mode=rolling \
                  --set portfolio.rebalancing.rolling_days=30

# Compare strategies
cc-liquid analyze --set portfolio.rebalancing.mode=full    # Full mode
cc-liquid analyze --set portfolio.rebalancing.mode=rolling # Rolling mode
```

### Run Continuous Trading

```bash
# Live dashboard with daily rolling rebalancing
cc-liquid run

# In tmux session for background operation
cc-liquid run --tmux
```

## Position Sizing in Rolling Mode

With rolling mode, each vintage contains a fraction of the total:

**Example Setup:**
- Total positions: `num_long + num_short = 120` (60 long + 60 short)
- Rolling days: `30`
- Target leverage: `3.0x`

**Per Vintage:**
- Positions: `120 / 30 = 4` (2 long, 2 short per vintage)
- Leverage: `3.0 / 30 = 0.1x` per vintage
- Total across 30 vintages: `30 × 0.1 = 3.0x` ✓

### Minimum Account Size

Ensure your account supports the granularity:

```
Daily allocation = Account Value × Target Leverage / rolling_days
Per-position size = Daily allocation / positions_per_vintage
```

**Must be above** `min_trade_value` (default: $10)

**Example 1: $10,000 account**
- Daily allocation: $10,000 × 3.0 / 30 = $1,000
- Positions per vintage: 4
- Per position: $1,000 / 4 = $250 ✓ (above $10 minimum)

**Example 2: $1,000 account (too small)**
- Daily allocation: $1,000 × 3.0 / 30 = $100
- Positions per vintage: 4
- Per position: $100 / 4 = $25 ✓ (works, but tight)

**Example 3: $500 account (problematic)**
- Daily allocation: $500 × 3.0 / 30 = $50
- Positions per vintage: 4
- Per position: $50 / 4 = $12.50 ✓ (marginal)

If positions drop below $10, trades will be skipped with warnings.

## Edge Cases & Robustness

| Scenario | How Rolling Mode Handles It |
|----------|------------------------------|
| **Missed rebalance day** | Target-sum self-corrects on next run. Old vintage still expires based on birth date. |
| **Stale predictions** | Warning if latest prediction > 1 day old. Can still create vintage with available data. |
| **Asset delisted** | Skipped in target sum. Existing positions close naturally when vintage expires. |
| **Manual intervention** | Target-diff approach handles any wallet state. Trades delta between target sum and actual. |
| **Corrupted state file** | Starts fresh (no vintages). Either gradual ramp-up or seed from history based on config. |
| **Account value change** | Each vintage uses account value at time of creation. No retroactive adjustments. |

## Comparing Full vs Rolling Mode

| Aspect | Full Mode | Rolling Mode |
|--------|-----------|--------------|
| **Timing Risk** | High (single entry point) | Low (spread across N days) |
| **Turnover** | Higher (full rebalance every N days) | Lower (only 1/N changes daily) |
| **Complexity** | Simple (stateless) | Requires vintage state tracking |
| **Cold Start** | Immediate full deployment | Gradual ramp-up OR seed from history |
| **Rebalance Frequency** | Configurable (e.g., every 10 days) | Always daily |
| **Best For** | Infrequent rebalancing, simple strategies | Daily trading with horizon-matched predictions |
| **State Storage** | None needed | JSON file (`.cc-liquid-state.json`) |
| **Prediction Alignment** | Manual timing | Automatic (rolling_days = prediction horizon) |

## Real-World Example

### Setup
- **Predictions:** Numerai meta-model (`pred_30d` - 30-day horizon)
- **Account:** $30,000
- **Config:** 60 long, 60 short, 3.0x leverage, 30-day rolling

### Steady State (Day 35)

**Active Vintages:** 30 (each 1 day apart, ages 0-29 days)

**Sample Vintage Details:**

**Vintage: 2024-11-01** (29 days old, expires tomorrow)
- BTC: 0.02 units (long)
- ETH: -5.0 units (short)
- SOL: 10.0 units (long)
- LINK: -50.0 units (short)

**Vintage: 2024-11-30** (0 days old, created today)
- BTC: 0.015 units (long)
- ETH: -4.5 units (short)
- AVAX: 20.0 units (long)
- ARB: -100.0 units (short)

**Total Target Position (sum of 30 vintages):**
- BTC: 0.45 units (long) → $45,000 @ $100k/BTC
- ETH: -120.0 units (short) → -$360,000 @ $3k/ETH
- SOL: 200.0 units (long) → $20,000 @ $100/SOL
- ... (117 more positions)

**Total Gross Notional:** $90,000 (3.0x leverage on $30,000)

### What Happens Tomorrow (Day 36)?

1. **Vintage 2024-11-01 EXPIRES:**
   - Close: 0.02 BTC (long), -5.0 ETH (short), 10.0 SOL (long), -50.0 LINK (short)

2. **Create Vintage 2024-12-01:**
   - New predictions from latest meta-model
   - Select top 60 long, bottom 60 short
   - Calculate 1/30 of target allocation for each
   - Store as units in new vintage

3. **Net Trades:**
   - BTC: If new vintage also wants BTC long (0.018 units), and old had 0.02:
     - Net: Sell 0.002 BTC (small delta)
   - ETH: If new vintage wants ETH long (instead of short):
     - Close: -5.0 units (from old vintage)
     - Open: +4.8 units (from new vintage)
     - Net: Buy 9.8 ETH (flip from short to long)

## State Persistence

### State File: `.cc-liquid-state.json`

```json
{
  "vintages": {
    "2024-11-01": {
      "BTC": 0.02,
      "ETH": -5.0,
      "SOL": 10.0,
      "LINK": -50.0
    },
    "2024-11-02": {
      "BTC": 0.018,
      "ETH": -4.8,
      "AVAX": 15.0,
      "ARB": -80.0
    },
    ...
    "2024-11-30": {
      "BTC": 0.015,
      "ETH": -4.5,
      "AVAX": 20.0,
      "ARB": -100.0
    }
  }
}
```

**Key Features:**
- Human-readable JSON
- Date keys (ISO format)
- Unit-based position tracking
- Auto-pruned (vintages > `rolling_days` removed)

### Location

Default: Current working directory (where you run `cc-liquid` commands)

You can specify custom location in future configs:
```yaml
portfolio:
  rebalancing:
    state_file: /path/to/custom-state.json
```

## Common Questions

### Q: What if I miss a day?

**A:** No problem! The system is robust:
1. Old vintages still expire based on birth date (not rebalance count)
2. Next rebalance calculates correct target sum from active vintages
3. May skip creating a vintage for the missed day, but not critical
4. Trades will catch up to target on next run

### Q: Can I change rolling_days mid-strategy?

**A:** Not recommended, but possible:
1. Existing vintages keep their original birth dates
2. New `rolling_days` affects future vintages and pruning
3. Transition period will be messy (mixed vintage durations)
4. Better to close all positions, clear state, restart with new config

### Q: What happens if prediction horizon changes?

**A:** Mismatch between `rolling_days` and prediction horizon:
- If `rolling_days < horizon`: Close positions before alpha window ends (suboptimal)
- If `rolling_days > horizon`: Hold positions after alpha expires (stale signals)
- **Best practice:** Keep `rolling_days = prediction_horizon`

### Q: Does rolling mode work with other features?

**A:** Yes, fully compatible with:
- ✅ Rank power weighting (concentration parameter)
- ✅ Stop loss protection (native TP/SL orders)
- ✅ Different data sources (CrowdCent, Numerai, local)
- ✅ Multiple profiles (personal, vault addresses)
- ✅ Backtesting (analyze historical performance)

### Q: How do I reset rolling mode?

**A:** To start fresh:
1. Delete state file: `rm .cc-liquid-state.json`
2. Next rebalance will start new vintages
3. Choose `seed_full: true` to immediately seed from history
4. Or `seed_full: false` for gradual ramp-up

## Performance Characteristics

### Turnover Analysis

**Full mode (rebalancing every 10 days):**
- Turnover: 100% of portfolio every 10 days
- Annual turnover: ~3,650% (100% × 365/10)

**Rolling mode (30-day vintages, daily rebalancing):**
- Daily turnover: ~3.3% of portfolio (1/30)
- Annual turnover: ~1,200% (3.3% × 365)
- **Reduction: ~67% less turnover**

**Why lower?**
- Overlapping positions across vintages
- Netting of trades (only trade delta)
- Gradual rotation vs full replacement

### Risk Characteristics

**Full mode:**
- Sharpe ratio: Depends on timing luck
- Max drawdown: Exposed to single entry timing

**Rolling mode:**
- Sharpe ratio: Typically higher (smoother returns)
- Max drawdown: Typically lower (time diversification)
- Volatility: Lower (less concentrated timing risk)

## Best Practices

### 1. Match Rolling Days to Prediction Horizon
```yaml
# If using pred_30d predictions:
rolling_days: 30  # ✓ Aligned

# If using pred_10d predictions:
rolling_days: 10  # ✓ Aligned
```

### 2. Use Seed Full for Production
```yaml
seed_full: true  # Start fully invested immediately
```

### 3. Set Realistic Account Size
Ensure: `Account Value / rolling_days / positions_per_vintage > $10`

### 4. Monitor Vintage Health
```bash
# Check vintages regularly
cc-liquid vintages

# Look for:
# - All vintages present (should be rolling_days count)
# - Reasonable value distribution
# - No missing dates (gaps)
```

### 5. Backtest First
```bash
# Compare rolling vs full mode
cc-liquid analyze --set portfolio.rebalancing.mode=full
cc-liquid analyze --set portfolio.rebalancing.mode=rolling

# Optimize rolling_days
cc-liquid optimize --params portfolio.rebalancing.rolling_days=20,30,40
```

## Conclusion

Rolling vintage rebalancing provides:

✅ **Time diversification** - Spread entries across N days
✅ **Reduced timing risk** - No single entry point exposure
✅ **Prediction alignment** - Match vintage lifespan to alpha horizon
✅ **Lower turnover** - Only 1/N changes daily, netting of overlaps
✅ **Robustness** - Self-correcting on missed days or issues

**When to use:**
- Daily prediction updates
- Clear prediction horizon (e.g., 30-day)
- Want to reduce timing risk
- Sufficient account size

**When to avoid:**
- Infrequent rebalancing preference (use full mode)
- Very small account (vintage granularity issues)
- No clear prediction horizon

For most meta-model based strategies with daily predictions, **rolling mode is the recommended approach**.

---

**Further Reading:**
- `docs/rolling-rebalancing.md` - Official documentation
- `docs/backtesting.md` - Performance comparison
- `examples/strategy-configs/rolling-mode.yaml` - Sample config
