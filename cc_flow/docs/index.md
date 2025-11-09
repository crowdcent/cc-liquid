---
title: Overview
---

!!! danger "⚠️ PRE-ALPHA SOFTWARE - USE AT YOUR OWN RISK ⚠️"
    - Using this software may result in **COMPLETE LOSS** of funds
    - CrowdCent makes **NO WARRANTIES** and assumes **NO LIABILITY**
    - Users must comply with Hyperliquid terms of service
    - We do **NOT** endorse any strategies using this tool

`cc-liquid` is a reference implementation for simple, automated portfolio rebalancing on Hyperliquid driven by metamodel predictions.

![cc-liquid dashboard](images/dashboard.svg)


### What you can do

- Download [CrowdCent](https://crowdcent.com/challenge/hyperliquid-ranking/meta-model/) or [Numerai](https://crypto.numer.ai/meta-model) metamodel predictions
- Backtest strategies on historical data with comprehensive metrics ⚠️ *(requires your own price data)*
- Optimize portfolio parameters using parallel grid search ⚠️ *(requires your own price data)* 
- Inspect account, positions, and exposure
- Rebalance to long/short target sets with equal-weight sizing
- Run continuously on a schedule (autopilot)

### TL;DR

```bash
uv tool install cc-liquid
cc-liquid init       # interactive setup wizard
cc-liquid account    # test connection & view positions
cc-liquid analyze    # backtest with current settings
cc-liquid optimize   # find optimal parameters
cc-liquid rebalance  # plan and execute trades
cc-liquid run        # run continuously on auto-pilot
```

See [Install & Quick Start](install-quickstart.md) for setup, environment variables, and first run. New users should try testnet first: `--set is_testnet=true`.
!!! warning "Critical Disclaimers"

    The `analyze` and `optimize` commands use historical data to test strategies. Remember that past performance does not predict future results. Backtesting has inherent limitations and optimized parameters are prone to overfitting. See [backtesting documentation](backtesting.md) for important disclaimers.

    **Past performance does not guarantee future results.** Backtesting results are hypothetical and have inherent limitations:
    
    - **Overfitting Risk**: Parameters that perform well historically may fail in live trading
    - **Market Dynamics**: Conditions, liquidity, and correlations change over time
    - **Execution Reality**: Slippage, fees, and market impact may exceed modeled estimates
    - **Survivorship Bias**: Historical data may exclude delisted/failed assets
    - **Data Mining**: Testing multiple strategies increases the chance of finding spurious patterns

    THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. USERS ASSUME ALL RISKS INCLUDING COMPLETE LOSS OF FUNDS, TRADING LOSSES, TECHNICAL FAILURES, AND LIQUIDATION RISKS.