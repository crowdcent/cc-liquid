---
title: Troubleshooting
---

Common issues and fixes.

## [Missing environment variables](configuration.md#environment-variables-env)

Error: `HYPERLIQUID_PRIVATE_KEY must be set in .env file.`
Error: `CROWDCENT_API_KEY not found in environment variables`

When `cc-liquid` is installed as a CLI tool, it may not automatically load variables from the `.env` file. You must load them into your shell session manually.

**Fix:** Run this command from your project root in each new terminal session before using `cc-liquid`:

```bash
export $(grep -v '^#' .env | xargs)
```

This command reads your `.env` file, filters out comments, and exports the key-value pairs.

- Ensure `.env` exists with `HYPERLIQUID_PRIVATE_KEY` (or a profile-specific `signer_env` key).
- Add `CROWDCENT_API_KEY` for CrowdCent data, or switch to `local`/`numerai`.

## [No tradeable assets](configuration.md#data)

Warning: `No predictions match Hyperliquid tradeable assets!`

- Ensure prediction `asset_id_column` matches Hyperliquid coins (e.g., BTC, ETH)
- Use the correct [`data.source`](configuration.md#data) smart defaults or set columns explicitly

## [Trades skipped (below minimum)](configuration.md#execution)

- Increase `account_value` or `portfolio.target_leverage`
- Reduce `portfolio.num_long/num_short`
- Lower [`execution.min_trade_value`](configuration.md#execution) with caution

## [High slippage or failed orders](configuration.md#execution)

- Increase [`execution.slippage_tolerance`](configuration.md#execution)
- Reduce position count or leverage
- Avoid illiquid symbols (see [Configuration → Execution](configuration.md#execution))


