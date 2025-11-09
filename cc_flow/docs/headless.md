---
title: Headless & Custom Callbacks
---

For advanced use cases or building alternative UIs, you can also use cc-liquid as a library without the CLI UI. The core trading logic is UI-agnostic and driven by callbacks. 

## Architecture

cc-liquid follows a modular design:

- **Data Layer** - Loads predictions from various sources (CrowdCent API, Numerai, local files)
- **Strategy Layer** - Selects top/bottom assets and calculates equal-weight position sizes
- **Execution Layer** - Interfaces with Hyperliquid via SDK for order management
- **Monitoring Layer** - Provides live dashboard and scheduled rebalancing (managed via callbacks and alternative UI code)

## Callback protocol

- Implement `cc_liquid.callbacks.CCLiquidCallbacks` to receive lifecycle events (info/warn/error, trade start/fill/fail, batch complete, confirmation prompts, etc.).
- Use `cc_liquid.callbacks.NoOpCallbacks` to run headless without output, or `cc_liquid.cli_callbacks.RichCLICallbacks` for the rich TUI.

## Programmatic usage

Minimal headless run with your own predictions:

```python
import polars as pl
from cc_liquid.config import Config
from cc_liquid.trader import CCLiquid
from cc_liquid.callbacks import NoOpCallbacks

# Load env + YAML; apply any config file you have in cwd
cfg = Config()

# Example: use a local parquet with your own column names
preds = pl.read_parquet("predictions.parquet")

bot = CCLiquid(cfg, callbacks=NoOpCallbacks())

# Compute plan using provided predictions (skips loading by source)
plan = bot.plan_rebalance(predictions=preds)

# Inspect or modify plan["trades"] as needed, then execute
result = bot.execute_plan(plan)
print({
    "num_success": len(result["successful_trades"]),
    "num_total": len(result["all_trades"]),
})
```

Notes:

- If you let the bot load predictions, set `cfg.data.source` and related columns first.
- Trades below `execution.min_trade_value` are reported in `plan["skipped_trades"]`.

## Scheduling (without CLI)

The bot exposes helpers for simple scheduling and state persistence:

```python
from datetime import UTC, datetime

last = bot.load_state()  # reads .cc_liquid_state.json if present
next_time = bot.compute_next_rebalance_time(last)
if datetime.now(UTC) >= next_time:
    plan = bot.plan_rebalance()
    res = bot.execute_plan(plan)
    bot.save_state(datetime.now(UTC))
```
