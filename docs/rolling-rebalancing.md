---
title: Rolling Rebalancing
---

# Rolling Vintage Rebalancing

Rolling rebalancing is a time-diversified trading strategy that spreads position entries across multiple days. Instead of rebalancing the entire portfolio at once, it creates daily "vintages" - each containing a fraction of the target allocation.

## Why Use Rolling Mode?

### Time Diversification
In full mode, you rebalance everything on a single day. If that day happens to be a local peak (for longs) or trough (for shorts), your entire portfolio suffers. Rolling mode spreads entries across N days, reducing timing risk.

### Matches Prediction Horizon
If your predictions have a 30-day forward horizon (like `pred_30d`), each prediction captures expected alpha over 30 days. After 30 days, that prediction has "expired" - the alpha window has closed. Rolling mode naturally aligns with this by closing positions after `rolling_days`.

### Reduced Turnover
When the same asset appears in consecutive vintages, the system automatically nets the trades. Instead of closing and reopening, it only trades the difference.

## How It Works

### The Vintage Model

```
Day 1:  Create Vintage_1 with 1/30 of target allocation
Day 2:  Create Vintage_2 with 1/30 of target allocation
...
Day 30: Create Vintage_30 with 1/30 of target allocation
        → Portfolio now at full allocation

Day 31: Vintage_1 expires (positions close)
        Create Vintage_31 (new positions open)
        → Steady state: 1/30 expires, 1/30 opens daily
```

### Target-Sum Calculation

The portfolio's target position is the sum of all active vintage positions:

| Vintage | BTC | ETH | SOL |
|---------|-----|-----|-----|
| Day 1   | 0.01 | -0.5 | — |
| Day 2   | 0.02 | — | 10.0 |
| Day 3   | — | -0.3 | 5.0 |
| **Total** | **0.03** | **-0.8** | **15.0** |

The system then calculates: `Trade = Target - Current Wallet` for each asset.

### Unit-Based Tracking

Vintages store asset quantities (units), not USD values. This prevents drift issues:

- You buy 0.1 BTC at $50k ($5,000)
- BTC rises to $100k (now worth $10,000)
- When vintage expires, you sell 0.1 BTC (the original units)
- No leftover position from price appreciation

## Configuration

```yaml
portfolio:
  num_long: 60
  num_short: 60
  target_leverage: 3.0
  rebalancing:
    mode: rolling           # Enable rolling mode
    rolling_days: 30        # Match to prediction horizon
    seed_full: true         # Full deployment from day 1
    at_time: "18:15"        # Daily rebalance time (UTC)
```

### Key Parameters

| Parameter | Description |
|-----------|-------------|
| `mode` | `"full"` (default) or `"rolling"` |
| `rolling_days` | Vintage lifespan. Match to prediction horizon. |
| `seed_full` | If true, seeds all vintages on first run using historical predictions. If false, gradually ramps up. |
| `every_n_days` | Ignored in rolling mode (always daily) |

## Cold Start Options

### Gradual Ramp-Up (seed_full: false)

- Day 1: 1/30 of target leverage
- Day 15: 50% of target leverage
- Day 30: Full target leverage
- Day 31+: Steady state

**Pros**: Conservative, reduces timing risk on deployment
**Cons**: Underinvested for first N days

### Immediate Full Deployment (seed_full: true)

- Day 1: System loads last 30 days of predictions
- Creates 30 vintages with staggered "birth dates"
- Immediately at full target leverage
- Day 2: Oldest vintage expires, new one opens

**Pros**: Fully invested from day 1, time-diversified from start
**Cons**: Requires historical prediction data

## CLI Usage

### Rebalance with Rolling Mode

```bash
# Use config settings
cc-liquid rebalance

# Override mode from CLI
cc-liquid rebalance --set portfolio.rebalancing.mode=rolling
```

### View Active Vintages

```bash
cc-liquid vintages
```

Output:
```
┌──────────────────────────────────────────────────────────┐
│               Active Vintages (30-day rolling)           │
├────────────┬─────┬────────────┬───────────┬─────────────┤
│ Birth Date │ Age │ Expires In │ Positions │ Value       │
├────────────┼─────┼────────────┼───────────┼─────────────┤
│ 2024-11-01 │ 29d │ 1d         │ 4         │ $1,234.56   │
│ 2024-11-02 │ 28d │ 2d         │ 4         │ $1,345.67   │
│ ...        │ ... │ ...        │ ...       │ ...         │
│ 2024-11-30 │ 0d  │ 30d        │ 4         │ $1,456.78   │
└────────────┴─────┴────────────┴───────────┴─────────────┘

Total vintage value: $42,000.00
Active vintages: 30 of 30
```

### Backtest Rolling Mode

```bash
# Use config mode
cc-liquid analyze

# Override from CLI using --set
cc-liquid analyze --set portfolio.rebalancing.mode=rolling --set portfolio.rebalancing.rolling_days=30

# Compare strategies
cc-liquid analyze --set portfolio.rebalancing.mode=full    # Then compare to:
cc-liquid analyze --set portfolio.rebalancing.mode=rolling
```

## Position Sizing

With rolling mode, each vintage contains `1/rolling_days` of the target allocation:

- **Total positions**: `num_long + num_short = 120`
- **Rolling days**: `30`
- **Positions per vintage**: `120 / 30 = 4` (2 long, 2 short)
- **Leverage per vintage**: `target_leverage / 30`

### Minimum Account Size

Ensure your account can support the vintage granularity:

```
Daily allocation = Account Value / rolling_days
Per-position size = Daily allocation / (num_positions_per_vintage)
```

If per-position size falls below `min_trade_value` ($10), trades will be skipped.

**Example**: With $10,000 account, 30-day rolling, 4 positions per vintage:
- Daily allocation: $333
- Per position: $83 ✓ (above minimum)

With $1,000 account:
- Daily allocation: $33
- Per position: $8.25 ✗ (below minimum, trades may fail)

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Missed rebalance day | Target-sum self-corrects on next run |
| Stale predictions | Warning if latest prediction > 1 day old |
| Asset delisted | Skipped in target sum, position closes naturally |
| Manual intervention | Target-diff approach handles any wallet state |

## Comparing Full vs Rolling

| Aspect | Full Mode | Rolling Mode |
|--------|-----------|--------------|
| Timing Risk | Higher (single entry point) | Lower (spread across N days) |
| Turnover | Higher (full rebalance) | Lower (only 1/N changes daily) |
| Complexity | Simple | Requires state tracking |
| Cold Start | Immediate full deployment | Gradual or seeded |
| Best For | Infrequent rebalancing | Daily trading with horizon-matched predictions |


