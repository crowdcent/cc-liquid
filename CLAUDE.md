# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

cc-liquid is a **metamodel-based portfolio rebalancer for Hyperliquid** that downloads predictions from CrowdCent or Numerai, selects top long/short positions, and automatically rebalances portfolios. This is **PRE-ALPHA software** with high risk of complete loss of funds.

**Critical Safety**: This software controls real financial assets. Never skip confirmations, always validate addresses, and use testnet for development.

## Package Manager & Development Commands

This project uses **uv** as the package manager. Always use `uv run python` to execute Python scripts.

### Essential Commands

```bash
# Run CLI commands
uv run cc-liquid <command>

# Run Python scripts directly
uv run python <script.py>

# Testing
uv run pytest                           # Run all tests
uv run pytest tests/test_config.py      # Run specific test file
uv run pytest -v                        # Verbose output
uv run pytest --cov=src/cc_liquid      # With coverage

# Linting
uv run ruff check                       # Check for issues
uv run ruff check --fix                 # Auto-fix issues
uv run ruff format                      # Format code

# Documentation (mkdocs)
uv run mkdocs serve                     # Local preview at http://127.0.0.1:8000
uv run mkdocs build                     # Build static site
```

## Architecture Overview

### Core Module Structure

```
src/cc_liquid/
├── cli.py              # Click-based CLI with commands (init, rebalance, run, analyze, optimize)
├── trader.py           # Core trading logic (CCLiquid class)
├── config.py           # Configuration management (YAML + .env)
├── data_loader.py      # Downloads predictions from CrowdCent/Numerai/local
├── backtester.py       # Backtesting engine (Backtester, BacktestOptimizer)
├── callbacks.py        # Abstract callback interface for trader events
├── cli_callbacks.py    # Rich-based CLI callbacks implementation
├── cli_display.py      # Rich UI components (panels, tables, dashboards)
├── completion.py       # Shell completion utilities
└── portfolio/
    ├── __init__.py     # Portfolio construction logic
    └── sizing.py       # Position sizing and weighting schemes
```

### Key Design Patterns

1. **Configuration System**:
   - Secrets in `.env` (API keys, private keys)
   - Settings in `cc-liquid-config.yaml` (addresses, portfolio params)
   - Multi-profile support for managing personal/vault accounts
   - CLI overrides via `--set key=value`

2. **Trader → Plan → Execute Flow**:
   - `plan_rebalance()` calculates target positions without execution
   - Returns dict with `trades`, `skipped_trades`, `target_positions`, `account_value`, `leverage`
   - `execute_plan()` performs actual trading
   - Callbacks render UI at each stage

3. **Callbacks Pattern**:
   - `CCLiquidCallbacks` abstract interface
   - `RichCLICallbacks` for CLI rendering
   - `NoOpCallbacks` for silent operation
   - Used for progress, confirmations, trade plans, execution summaries

4. **Data Flow**:
   - DataLoader → predictions (polars DataFrame)
   - trader.py → Hyperliquid API (Info for reads, Exchange for writes)
   - backtester.py → pure simulation using historical price data

### Trading Logic (trader.py)

The `CCLiquid` class orchestrates all trading operations:

- **Account Queries**: Uses Hyperliquid `Info` API with owner/vault address
- **Order Execution**: Uses `Exchange` API with signer (agent wallet private key)
- **Rebalancing**:
  1. Load predictions from configured source
  2. Select top N long/bottom N short by prediction value
  3. Calculate target weights (equal-weight or rank-power)
  4. Scale to target leverage
  5. Generate delta trades from current to target
  6. Filter trades by min notional
  7. Execute via market orders

**Important**: Agent wallets (signers) are separate from owner addresses. Queries use owner, signatures use agent key.

### Configuration (config.py)

Configuration uses dataclasses with nested structure:
- `DataSourceConfig`: source, path, column mappings
- `PortfolioConfig`: num_long, num_short, target_leverage, weighting_scheme, rank_power
- `RebalancingConfig`: every_n_days, at_time (UTC)
- `ExecutionConfig`: slippage_tolerance, min_trade_value

**Profile System**: Each profile has owner, vault (optional), signer_env. The active_profile determines which addresses/keys are used.

### Backtesting (backtester.py)

- `Backtester`: Runs single backtest with given parameters
- `BacktestOptimizer`: Grid search across parameter space with caching
- Uses polars for efficient data processing
- Simulates rebalancing with realistic costs (fees + slippage)
- Tracks daily equity, returns, drawdown, turnover
- **Warning**: Backtesting has inherent limitations and overfitting risks

### CLI Structure (cli.py)

Key commands:
- `init`: Interactive setup wizard
- `config`: Show current configuration
- `account`: Display portfolio state
- `rebalance`: One-time rebalance (preview + confirm)
- `run`: Continuous monitoring with live dashboard
- `analyze`: Backtest with current config
- `optimize`: Grid search for optimal parameters
- `profile list/show/use`: Manage profiles
- `completion install`: Shell completion

**Tmux Integration**: `run --tmux` launches persistent session for background operation.

## Code Style & Conventions

### From User's Global CLAUDE.md

- Use **SOLID and KISS** principles
- Split code into reusable modules (max 300 lines, use inheritance)
- Use **loguru** for logging in Python
- Run Python scripts with `uv run python <script>`

### From style-guide.md

This project uses a **brutalist/minimalist design philosophy** for UI:
- High-contrast colors: cyan (#62e4fb), deep purple (#4152A8), dark abyss (#001926)
- Stark, functional interfaces with geometric patterns
- Rich library for terminal UI (panels, tables, progress bars)
- Edward Tufte's data visualization principles apply

## Configuration Files

- `cc-liquid-config.yaml`: All settings (addresses, portfolio params)
- `.env`: Secrets only (API keys, private keys)
- `.gitignore`: Must contain `.env` to prevent leaking secrets

## Testing

Tests use pytest and are located in `tests/`:
- `test_config.py`: Configuration loading and validation
- `test_data_loader.py`: Data loading from sources
- `test_backtester.py`: Backtesting engine
- `test_portfolio.py`: Portfolio construction and weighting

Run with `uv run pytest` (never bare `pytest`).

## Important Notes

### Security

- **Never commit secrets**: API keys and private keys must stay in `.env`
- **Agent wallets**: Use separate approved agent keys for automation (not main wallet)
- **Testnet first**: Always develop and test on testnet before mainnet
- **Address validation**: Info API uses owner/vault, Exchange API uses signer

### Hyperliquid Integration

- **Nonce isolation**: Each agent wallet has independent nonce sequence
- **Min notional**: Trades below $10 are skipped (configurable via execution.min_trade_value)
- **Slippage**: Use limit orders with slippage tolerance (execution.slippage_tolerance)
- **Rate limits**: Be mindful of API rate limits in continuous monitoring

### Data Sources

- **CrowdCent**: Requires API key, uses `release_date`, `id`, `pred_10d` columns
- **Numerai**: Free, uses `date`, `symbol`, `meta_model` columns
- **Local**: Custom parquet files with configurable column mappings

Column mappings auto-configure when using `--set data.source=<source>`.

### Common Pitfalls

1. **Using wrong address for queries**: Always use owner/vault for Info API, not agent wallet
2. **Forgetting uv run**: Must prefix Python commands with `uv run`
3. **Hardcoding secrets**: Never put API keys or private keys in code or YAML
4. **Skipping confirmations in production**: Only use `--skip-confirm` for automated bots with proper monitoring
5. **Overfitting backtests**: Always validate with out-of-sample data

## Documentation

Full documentation is in `docs/` and built with mkdocs:
- `docs/install-quickstart.md`: Installation and first run
- `docs/configuration.md`: Detailed config reference
- `docs/backtesting.md`: Backtesting guide with disclaimers
- `docs/portfolio-weighting.md`: Weighting schemes explanation
- `docs/autopilot.md`: Continuous rebalancing setup
- `docs/troubleshooting.md`: Common issues and solutions

Preview docs locally: `uv run mkdocs serve`

## Key Dependencies

- **click**: CLI framework
- **polars**: Fast dataframe processing
- **hyperliquid-python-sdk**: Exchange integration
- **rich**: Terminal UI (progress bars, tables, panels)
- **eth-account**: Wallet signing
- **pyyaml**: Config file parsing
- **python-dotenv**: Environment variable loading
- **crowdcent-challenge**: CrowdCent API client
- **pytest**: Testing framework
- **ruff**: Linting and formatting
- **mkdocs-material**: Documentation

## Repository Context

- **Main branch**: `main` (use for PRs)
- **Version**: 0.1.5a5 (pre-alpha)
- **License**: MIT
- **Git**: Clean working directory (based on init snapshot)
