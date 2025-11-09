---
title: Configuration
---

cc-liquid loads configuration from `cc-liquid-config.yaml` and environment variables. Addresses, profile selection, and portfolio parameters live in the config YAML; secrets (private keys, API keys) should live in `.env`. You can override any setting via `--set` when running the CLI commands.

## Environment variables (.env)

Your env file, which should only store secrets/keys should look like this:

```env
CROWDCENT_API_KEY=zzxFake.CrowdCentKey1234567890   # (needed for CrowdCent metamodel source)
HYPERLIQUID_PRIVATE_KEY=0xdeadbeefdeadbeefdeadbeefdeadbeefdead  # (default signer key variable name)
```

!!! note 
    - You can change the default signer key variable name and provide additional, profile-specific signer keys you can reference via `signer_env` in YAML, (e.g.:`HYPER_AGENT_KEY_PERSONAL`, `HYPER_AGENT_KEY_VAULT`)

    - Do not put addresses in `.env`; keep owner/vault addresses in the configuration YAML file.

!!! warning "Loading .env variables"
    When `cc-liquid` is installed as a CLI tool (e.g., via `uv tool install`), it may not automatically load variables from `.env`. If you encounter errors about missing keys, you must load them manually in your shell session:
    ```bash
    export $(grep -v '^#' .env | xargs)
    ```

## YAML (`cc-liquid-config.yaml`)
Your yaml file, in the root of where you call `cc-liquid` should look like this:
```yaml
is_testnet: false

active_profile: default

profiles:
  default:
    owner: 0xYourMain
    vault: null                 # omit or null for personal portfolio
    signer_env: HYPERLIQUID_PRIVATE_KEY

  alternate-profile: # optional, informational
    owner: 0xYourMain           
    vault: 0xVaultAddress
    signer_env: HYPERLIQUID_AGENT_KEY_VAULT


data:
  source: crowdcent | numerai | local
  path: predictions.parquet
  date_column: release_date | date
  asset_id_column: id | symbol
  prediction_column: pred_10d | meta_model

portfolio:
  num_long: 10
  num_short: 10
  target_leverage: 1.0
  rank_power: 0.0
  stop_loss:
    sides: none                # "none", "both", "long_only", "short_only"
    pct: 0.17                  # 17% from entry price
    slippage: 0.05             # 5% slippage tolerance
  rebalancing:
    every_n_days: 10
    at_time: "18:15"   # HH:MM (UTC)

execution:
  slippage_tolerance: 0.005      # Market orders: aggressive pricing (default: 0.005)
  limit_price_offset: 0.0        # Limit orders: passive offset (default: 0.0 = exact mid)
  min_trade_value: 10.0
  order_type: market | limit
  time_in_force: Ioc | Gtc | Alo
```


## Profiles, network & credentials

- `profiles` define who you trade for and which key signs.
  - `owner`: portfolio owner (used for Info queries when `vault` not set)
  - `vault`: optional; when set, becomes the portfolio owner for Info and Exchange endpoint includes `vaultAddress`
  - `signer_env`: name of env var holding the private key for signing
- `active_profile` selects the default profile, override with `set --active_profile` at runtime
- `is_testnet: true` switches from mainnet to testnet

See more on how to generate Hyperliquid API wallets and private keys for safety: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/nonces-and-api-wallets

## Data

Source types; columns can be overridden):

### [crowdcent](https://crowdcent.com/challenge/hyperliquid-ranking/meta-model/)

```bash
cc-liquid rebalance --set data.source=crowdcent
```

Defaults: `date_column=release_date`, `asset_id_column=id`, `prediction_column=pred_10d`, `path=predictions.parquet`

### [numerai](https://crypto.numer.ai/meta-model)

Ensure you have installed extras: `uv pip install cc-liquid[numerai]`

```bash
cc-liquid rebalance --set data.source=numerai
```

Defaults: `date_column=date`, `asset_id_column=symbol`, `prediction_column=meta_model`, `path=predictions.parquet`

!!! tip
    Running commands with `--set data.source=numerai` can auto-apply column defaults for the Numerai metamodel.

### local

Bring your own Parquet/CSV:

```bash
cc-liquid rebalance \
  --set data.source=local \
  --set data.path=my_preds.parquet \
  --set data.date_column=dt \
  --set data.asset_id_column=ticker \
  --set data.prediction_column=score
```

Column rules:

- `date_column`: latest row per asset is used
- `asset_id_column`: must match Hyperliquid symbols; unmatched are skipped
- `prediction_column`: ranking for longs/shorts grouped by date

## Portfolio

- `num_long` / `num_short`: counts for top/bottom selections
- `target_leverage`: scales notional per-position like `(account_value * target_leverage) / (num_long + num_short)`.
- `rank_power`: concentration parameter (0.0 = equal weight, default; higher = more concentration in top-ranked positions) - see [Portfolio Weighting](portfolio-weighting.md)
- `rebalancing.every_n_days` / `rebalancing.at_time` (UTC)

### Stop Loss Protection

Stop losses protect your positions from adverse price moves using Hyperliquid's native TP/SL trigger orders. They're calculated from entry price (not current price) for consistent risk management.

Configuration:

- `stop_loss.sides`: which positions to protect
    - `none` (default): no stop loss protection
    - `both`: protect all positions (longs and shorts)
    - `long_only`: protect only long positions
    - `short_only`: protect only short positions
- `stop_loss.pct`: trigger distance from entry price (default: 0.17 = 17%)
    - For longs: triggers when price falls 17% below entry
    - For shorts: triggers when price rises 17% above entry
- `stop_loss.slippage`: slippage tolerance for the limit order (default: 0.05 = 5%)
    - Controls how far from trigger price the limit order can fill
    - Higher = more likely to fill but worse execution
    - Lower = better execution but may not fill in fast moves

**How it works:**

1. After each rebalance, stop losses are automatically placed on all eligible open positions
2. Stop losses use Hyperliquid's position-based TP/SL (not order-based OCO)
3. Existing TP/SL orders are cancelled and replaced with fresh ones each rebalance
4. Stop losses remain active until:
   - Triggered by price move (position closes with slippage)
   - Next rebalance (cancelled and replaced with new stops)
   - Manually cancelled

**Manual application:**

For positions opened manually or when limit orders fill after rebalance:

```bash
# Apply stop losses to all eligible open positions
cc-liquid apply-stops

# Override sides temporarily
cc-liquid apply-stops --set portfolio.stop_loss.sides=both
```

## Execution

- `slippage_tolerance`: For market orders - calculates aggressive limit prices away from mid to ensure fills (buy above mid, sell below mid). Default: 0.005 (0.5%)
- `limit_price_offset`: For limit orders - calculates passive prices inside mid for better execution (buy below mid, sell above mid). Default: 0.0 (exact mid). Higher values = further inside mid = better prices but lower fill probability.
- `min_trade_value`: trades below this absolute USD delta are skipped
- `order_type`: order execution method
    - `market` (default): uses `slippage_tolerance` for aggressive fills away from mid
    - `limit`: uses `limit_price_offset` for passive pricing (0.0 = exact mid, >0 = inside mid)
- `time_in_force`: how long orders stay active
    - `Ioc` (Immediate or Cancel, default): fills immediately or cancels, no orders stay on book
    - `Gtc` (Good til Canceled): orders stay on book until filled or manually canceled
    - `Alo` (Add Liquidity Only): only posts to book, never takes liquidity

**Note on limit orders with Ioc**: Passive limit orders (priced at or inside mid) with Ioc may not fill immediately. Consider using `Gtc` or `Alo` for limit orders if you want orders to rest on the book.

### Order Status

When orders execute, they can have different outcomes:

- **Filled** - Order executed immediately ✅
- **Resting** - Order successfully posted to book and waiting (Gtc/Alo only) ✅
- **Failed** - Order rejected or not filled ❌

### Managing Open Orders

When using `Gtc` or `Alo`, unfilled orders stay on the book. Use these commands to manage them:

```bash
# View current open orders
cc-liquid orders

# Cancel all open orders
cc-liquid cancel-orders

# Cancel orders for specific coin
cc-liquid cancel-orders --coin BTC

# Cancel orders before rebalancing
cc-liquid rebalance --cancel-open-orders
```

If you rebalance while having open orders, cc-liquid will:
1. Warn you about potential conflicts
2. Prompt you to cancel them (interactive)
3. Or you can use `--cancel-open-orders` flag to auto-cancel

### View Trade History

Track your fills and fees:

```bash
# Last 7 days
cc-liquid history --days 7

# Specific date range
cc-liquid history --start 2025-01-01 --end 2025-01-31

# Limit results
cc-liquid history --limit 100
```

Shows execution price, size, fees, and realized PnL for each fill.

## CLI overrides

Examples:

```bash
cc-liquid run --set active_portfolio=default
```

```bash
cc-liquid rebalance --set data.source=numerai --set portfolio.target_leverage=2.0 --set portfolio.num_long=12
```

Nested keys use dot-notation. Types are inferred (int/float/bool/str).

Smart defaults when switching `data.source` are applied unless explicitly overridden.

## CLI helpers

- `cc-liquid profile list | show | use <name>` – manage profiles
- `cc-liquid orders` – view current open orders
- `cc-liquid cancel-orders [--coin SYMBOL]` – cancel open orders
- `cc-liquid apply-stops` – manually apply stop losses to all open positions
- `cc-liquid history [--days N | --start DATE --end DATE]` – view trade history and fees
