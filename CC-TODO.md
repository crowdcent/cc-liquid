# CC-Liquid Textualize Rewrite - Task List

**Project**: cc-liquid Textualize TUI Implementation
**Based on**: PRD_TEXTUALIZE_REWRITE.md v1.0
**Date**: 2025-11-08
**Target Directory**: `/home/ling/workarea/numerai/cc-liquid/cc-flow/`

---

## Task Overview

This document breaks down the implementation of the cc-liquid Textualize rewrite into discrete, manageable tasks for a junior software engineer. Each task follows TDD principles and SOLID design patterns.

### Task Status Legend
- ⏳ **Pending**: Not yet started
- 🔄 **In Progress**: Currently being worked on
- ✅ **Completed**: Finished and tested
- ❌ **Blocked**: Cannot proceed due to dependencies

### Progress Summary (34/60 tasks = 57%)

**Phase 1: Core Infrastructure & Domain Models** ✅ 6/6 (100%)
- ✅ task-2: Domain Models - Account Models
- ✅ task-3: Domain Models - Order Models
- ✅ task-4: Domain Models - Portfolio Models
- ✅ task-5: Domain Models - Configuration Models
- ✅ task-6: Domain Models - Backtest Models

**Phase 2: Exchange Abstraction Layer** ✅ 5/5 (100%)
- ✅ task-7: Exchange Base Interfaces
- ✅ task-8: Hyperliquid Info Client
- ✅ task-9: Hyperliquid Trading Client
- ✅ task-10: Hyperliquid Exchange Implementation
- ✅ task-11: Mock Exchange Implementation

**Phase 3: Data Source Abstraction Layer** ✅ 5/5 (100%)
- ✅ task-12: Data Source Base Classes
- ✅ task-13: CrowdCent Data Source
- ✅ task-14: Numerai Data Source
- ✅ task-15: Local File Data Source
- ✅ task-16: Mock Data Source

**Phase 4: Core Business Logic** 🔄 9/14 (64%)
- ✅ task-17: Portfolio Manager - Equal Weighting
- ✅ task-18: Portfolio Manager - Rank Weighting
- ✅ task-19: State Manager
- ✅ task-20: Event Bus
- ✅ task-21: Trading Orchestrator - Initialization
- ✅ task-22: Trading Orchestrator - Plan Rebalance (Part 1)
- ✅ task-23: Trading Orchestrator - Plan Rebalance (Part 2)
- ✅ task-24: Trading Orchestrator - Trade Calculation
- ⏳ task-25: Trading Orchestrator - Execute Plan
- ⏳ task-26: Trading Orchestrator - Stop Losses
- ✅ task-27: Backtester - Data Loading
- ✅ task-28: Backtester - Simulation Engine
- ✅ task-29: Backtester - Statistics Calculation
- ✅ task-30: Backtest Optimizer

**Phase 5: Configuration System** ✅ 4/4 (100%)
- ✅ task-31: Configuration Loader
- ✅ task-32: Configuration Overrides
- ✅ task-33: Configuration Validator
- ✅ task-34: Default Configuration

**Phase 6: Utility Functions** ✅ 4/4 (100%)
- ✅ task-35: Logging Configuration
- ✅ task-36: Validation Utilities
- ✅ task-37: Formatting Utilities
- ✅ task-38: Financial Calculations

**Phase 7: Textualize TUI** ⏳ 0/16 (0%)
- ⏳ task-39 through task-54: All TUI tasks pending

**Phase 8: Integration & Testing** ⏳ 0/6 (0%)
- ⏳ task-55 through task-60: All integration/testing tasks pending

---

## Phase 1: Core Infrastructure & Domain Models

### task-1: Project Structure Setup ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 2 hours
**Dependencies**: None

**Description**: Create the complete directory structure for the cc-flow module.

**Acceptance Criteria**:
- [ ] Create `cc-flow/` directory structure matching PRD Section 1.2
- [ ] Create all `__init__.py` files
- [ ] Set up `pyproject.toml` with required dependencies
- [ ] Create initial `tests/` directory structure
- [ ] Verify all imports work correctly

**Files to Create**:
```
cc-flow/
├── __init__.py
├── core/
├── domain/
├── exchanges/
├── data_sources/
├── ui/
├── utils/
├── config/
└── tests/
```

---

### task-2: Domain Models - Account Models ✅
**Priority**: P0 (Critical)
**Estimated Time**: 4 hours
**Dependencies**: task-1
**Status**: COMPLETED
**Completed**: 2025-11-08

**Description**: Implement Pydantic v2 domain models for account-level data (PRD Section 2.1.1).

**Acceptance Criteria**:
- [ ] Create `domain/account.py` with Pydantic v2 models
- [ ] Implement `AccountInfo` model with all fields
- [ ] Implement `Position` model with signed_size property
- [ ] Implement `PortfolioSnapshot` model with computed properties
- [ ] Write unit tests for all models (>90% coverage)
- [ ] Test property methods (leverage_percentage, signed_size, etc.)
- [ ] Validate frozen/mutable configurations

**Models to Implement**:
- `AccountInfo`
- `Position`
- `PortfolioSnapshot`

**Test Cases**:
- Valid model instantiation
- Property calculations
- Decimal precision handling
- Model serialization/deserialization

---

### task-3: Domain Models - Order Models ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 4 hours
**Dependencies**: task-1

**Description**: Implement Pydantic v2 models for orders and trades (PRD Section 2.1.2).

**Acceptance Criteria**:
- [ ] Create `domain/orders.py` with all enums and models
- [ ] Implement `OrderType`, `TimeInForce`, `OrderSide`, `OrderStatus` enums
- [ ] Implement `OrderRequest` model (frozen=True)
- [ ] Implement `OrderResult` model with is_success property
- [ ] Implement `Trade` model with execution tracking
- [ ] Write comprehensive unit tests (>90% coverage)

**Models to Implement**:
- `OrderType`, `TimeInForce`, `OrderSide`, `OrderStatus` (Enums)
- `OrderRequest`
- `OrderResult`
- `Trade`

**Test Cases**:
- Enum validation
- Frozen model immutability
- Order status transitions
- Trade execution state tracking

---

### task-4: Domain Models - Portfolio Models ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 3 hours
**Dependencies**: task-2, task-3

**Description**: Implement portfolio and rebalancing domain models (PRD Section 2.1.3).

**Acceptance Criteria**:
- [ ] Create `domain/portfolio.py`
- [ ] Implement `TargetPosition` model
- [ ] Implement `RebalancePlan` model with computed properties
- [ ] Implement `ExecutionResult` model
- [ ] Write unit tests (>90% coverage)
- [ ] Test computed properties (total_trades, success_rate, etc.)

**Models to Implement**:
- `TargetPosition`
- `RebalancePlan`
- `ExecutionResult`

---

### task-5: Domain Models - Configuration Models ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 4 hours
**Dependencies**: task-1

**Description**: Implement configuration domain models (PRD Section 8.1).

**Acceptance Criteria**:
- [ ] Create `domain/config.py`
- [ ] Implement `DataSourceConfig`
- [ ] Implement `StopLossConfig`
- [ ] Implement `RebalancingConfig`
- [ ] Implement `PortfolioConfig`
- [ ] Implement `ExecutionConfig`
- [ ] Implement `ExchangeProfile`
- [ ] Implement `TradingConfig` with properties
- [ ] Write validation tests for all configs
- [ ] Test nested configuration validation

**Models to Implement**:
- `DataSourceConfig`
- `StopLossConfig`
- `RebalancingConfig`
- `PortfolioConfig`
- `ExecutionConfig`
- `ExchangeProfile`
- `TradingConfig`

---

### task-6: Domain Models - Backtest Models ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-5

**Description**: Implement backtesting configuration and result models (PRD Section 7.1).

**Acceptance Criteria**:
- [ ] Create `domain/backtest.py`
- [ ] Implement `BacktestConfig` dataclass
- [ ] Implement `BacktestResult` Pydantic model
- [ ] Include all statistical metrics fields
- [ ] Write unit tests for model validation
- [ ] Test with polars DataFrames

**Models to Implement**:
- `BacktestConfig`
- `BacktestResult`

---

## Phase 2: Exchange Abstraction Layer

### task-7: Exchange Base Interfaces ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 4 hours
**Dependencies**: task-2, task-3

**Description**: Create abstract base classes for exchange integration (PRD Section 3.1).

**Acceptance Criteria**:
- [ ] Create `exchanges/base.py`
- [ ] Implement `ExchangeInfo` Protocol
- [ ] Implement `ExchangeTrading` Protocol
- [ ] Implement `Exchange` ABC with abstract methods
- [ ] Document all abstract methods with type hints
- [ ] Create mock implementations for testing

**Interfaces to Implement**:
- `ExchangeInfo` (Protocol)
- `ExchangeTrading` (Protocol)
- `Exchange` (ABC)

**Test Cases**:
- Protocol compliance verification
- Abstract method enforcement

---

### task-8: Hyperliquid Info Client ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 5 hours
**Dependencies**: task-7

**Description**: Implement Hyperliquid info/query client (PRD Section 3.2).

**Acceptance Criteria**:
- [ ] Create `exchanges/hyperliquid.py`
- [ ] Implement `HyperliquidInfo` class
- [ ] Implement all info methods (get_account_state, get_open_positions, etc.)
- [ ] Add metadata caching
- [ ] Handle API response parsing
- [ ] Write integration tests with mocked responses
- [ ] Test error handling

**Class to Implement**:
- `HyperliquidInfo`

**Methods**:
- `get_account_state()`
- `get_open_positions()`
- `get_open_orders()`
- `get_fill_history()`
- `get_market_prices()`
- `get_exchange_metadata()`
- `get_fee_rates()`

---

### task-9: Hyperliquid Trading Client ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 5 hours
**Dependencies**: task-7, task-8

**Description**: Implement Hyperliquid trading/execution client (PRD Section 3.2).

**Acceptance Criteria**:
- [ ] Implement `HyperliquidTrading` class
- [ ] Implement order submission (single and batch)
- [ ] Implement order cancellation
- [ ] Implement order modification
- [ ] Add proper order format conversion
- [ ] Parse execution results correctly
- [ ] Write comprehensive tests
- [ ] Test batch order handling

**Class to Implement**:
- `HyperliquidTrading`

**Methods**:
- `submit_order()`
- `submit_batch_orders()`
- `cancel_order()`
- `cancel_batch_orders()`
- `modify_order()`

---

### task-10: Hyperliquid Exchange Implementation ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 6 hours
**Dependencies**: task-8, task-9

**Description**: Complete Hyperliquid exchange adapter (PRD Section 3.2).

**Acceptance Criteria**:
- [ ] Implement `HyperliquidExchange` class
- [ ] Implement `parse_account_state()` method
- [ ] Implement size/price rounding methods
- [ ] Implement `calculate_limit_price()` method
- [ ] Add szDecimals caching
- [ ] Handle precision edge cases
- [ ] Write comprehensive unit tests (>85% coverage)
- [ ] Test with real API response fixtures

**Class to Implement**:
- `HyperliquidExchange`

**Methods**:
- `_create_info_client()`
- `_create_trading_client()`
- `parse_account_state()`
- `round_size()`
- `round_price()`
- `calculate_limit_price()`

**Test Cases**:
- Account state parsing
- Position parsing
- Size/price rounding edge cases
- Limit price calculation

---

### task-11: Mock Exchange Implementation ⏳
**Priority**: P1 (High)
**Estimated Time**: 4 hours
**Dependencies**: task-7

**Description**: Create mock exchange for testing (PRD Section 3.3).

**Acceptance Criteria**:
- [ ] Create `exchanges/mock.py`
- [ ] Implement `MockExchange` class
- [ ] Support configurable responses
- [ ] Track submitted/cancelled orders
- [ ] Implement order fill behaviors (always_fill, always_fail, random)
- [ ] Write tests for mock exchange
- [ ] Document usage for integration tests

**Class to Implement**:
- `MockExchange`

**Features**:
- Configurable account value
- Configurable positions
- Configurable prices
- Order tracking
- Fill behavior simulation

---

## Phase 3: Data Source Abstraction Layer

### task-12: Data Source Base Classes ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 3 hours
**Dependencies**: task-1

**Description**: Create abstract data source interfaces (PRD Section 4.1).

**Acceptance Criteria**:
- [ ] Create `data_sources/base.py`
- [ ] Implement `PredictionMetadata` model
- [ ] Implement `DataSource` ABC
- [ ] Implement `CachedDataSource` base class
- [ ] Add cache TTL management
- [ ] Write base class tests

**Classes to Implement**:
- `PredictionMetadata`
- `DataSource` (ABC)
- `CachedDataSource`

**Methods**:
- `load_predictions()`
- `get_metadata()`
- `validate_schema()`

---

### task-13: CrowdCent Data Source ⏳
**Priority**: P1 (High)
**Estimated Time**: 4 hours
**Dependencies**: task-12

**Description**: Implement CrowdCent API data source (PRD Section 4.2).

**Acceptance Criteria**:
- [ ] Create `data_sources/crowdcent.py`
- [ ] Implement `CrowdCentDataSource` class
- [ ] Download meta model via API
- [ ] Standardize column names
- [ ] Handle date parsing
- [ ] Implement caching
- [ ] Write integration tests with mocked API
- [ ] Test column renaming and validation

**Class to Implement**:
- `CrowdCentDataSource`

**Features**:
- API authentication
- Parquet download
- Column standardization
- Cache management

---

### task-14: Numerai Data Source ⏳
**Priority**: P2 (Medium)
**Estimated Time**: 4 hours
**Dependencies**: task-12

**Description**: Implement Numerai API data source.

**Acceptance Criteria**:
- [ ] Create `data_sources/numerai.py`
- [ ] Implement `NumeraiDataSource` class
- [ ] Fetch crypto signals via Numerai API
- [ ] Standardize schema
- [ ] Implement caching
- [ ] Write tests with mocked responses

**Class to Implement**:
- `NumeraiDataSource`

---

### task-15: Local File Data Source ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-12

**Description**: Implement local file data source (PRD Section 4.3).

**Acceptance Criteria**:
- [ ] Create `data_sources/local.py`
- [ ] Implement `LocalFileDataSource` class
- [ ] Support parquet and CSV files
- [ ] Handle custom column mappings
- [ ] Validate schema
- [ ] Write tests with sample files

**Class to Implement**:
- `LocalFileDataSource`

**Features**:
- Parquet/CSV loading
- Custom column mapping
- Schema validation

---

### task-16: Mock Data Source ⏳
**Priority**: P2 (Medium)
**Estimated Time**: 2 hours
**Dependencies**: task-12

**Description**: Create mock data source for testing.

**Acceptance Criteria**:
- [ ] Create `data_sources/mock.py`
- [ ] Implement `MockDataSource` class
- [ ] Return configurable prediction data
- [ ] Support different test scenarios
- [ ] Write usage examples

**Class to Implement**:
- `MockDataSource`

---

## Phase 4: Core Business Logic

### task-17: Portfolio Manager - Equal Weighting ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 4 hours
**Dependencies**: task-4

**Description**: Implement equal-weighted portfolio construction (PRD Section 6.1).

**Acceptance Criteria**:
- [ ] Create `core/portfolio.py`
- [ ] Implement `PortfolioManager` class
- [ ] Implement `_equal_weighted_positions()` method
- [ ] Handle long/short split correctly
- [ ] Scale to target leverage
- [ ] Write comprehensive tests
- [ ] Test edge cases (zero positions, unequal splits)

**Class to Implement**:
- `PortfolioManager`

**Method**:
- `_equal_weighted_positions()`

**Test Cases**:
- Equal long/short counts
- Unequal long/short counts
- Leverage scaling
- Zero positions

---

### task-18: Portfolio Manager - Rank Weighting ⏳
**Priority**: P1 (High)
**Estimated Time**: 5 hours
**Dependencies**: task-17

**Description**: Implement rank-power weighted portfolio construction (PRD Section 6.1).

**Acceptance Criteria**:
- [ ] Implement `_rank_weighted_positions()` method
- [ ] Implement `_calculate_side_weights()` method
- [ ] Apply rank power formula correctly
- [ ] Normalize weights to target leverage
- [ ] Write comprehensive tests
- [ ] Test with different rank_power values
- [ ] Verify weight normalization

**Methods to Implement**:
- `_rank_weighted_positions()`
- `_calculate_side_weights()`

**Test Cases**:
- rank_power = 0 (equal weight)
- rank_power = 1 (linear)
- rank_power = 2 (quadratic)
- Weight normalization
- Long/short sorting

---

### task-19: State Manager ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-1

**Description**: Implement application state management.

**Acceptance Criteria**:
- [ ] Create `core/state.py`
- [ ] Implement `StateManager` class
- [ ] Track portfolio snapshots
- [ ] Track execution history
- [ ] Provide state queries
- [ ] Write tests for state transitions

**Class to Implement**:
- `StateManager`

**Features**:
- Portfolio snapshot storage
- Execution history
- State queries
- Thread safety

---

### task-20: Event Bus ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-1

**Description**: Implement event bus for orchestrator communication.

**Acceptance Criteria**:
- [ ] Create event bus in `core/trader.py` or separate file
- [ ] Implement pub/sub pattern
- [ ] Support event subscription
- [ ] Support event emission
- [ ] Write tests for event flow

**Class to Implement**:
- `EventBus`

**Methods**:
- `subscribe(event_name, callback)`
- `emit(event_name, data)`

---

### task-21: Trading Orchestrator - Initialization ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 3 hours
**Dependencies**: task-10, task-17, task-19, task-20

**Description**: Set up trading orchestrator structure (PRD Section 5.1).

**Acceptance Criteria**:
- [ ] Create `core/trader.py`
- [ ] Implement `TradingOrchestrator` class
- [ ] Set up initialization with dependencies
- [ ] Initialize event bus
- [ ] Initialize portfolio manager
- [ ] Write initialization tests

**Class to Implement**:
- `TradingOrchestrator`

**Constructor Parameters**:
- `exchange: Exchange`
- `data_source: DataSource`
- `config: TradingConfig`
- `state_manager: StateManager`

---

### task-22: Trading Orchestrator - Plan Rebalance (Part 1) ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 5 hours
**Dependencies**: task-21

**Description**: Implement plan_rebalance workflow steps 1-4 (PRD Section 5.1).

**Acceptance Criteria**:
- [ ] Implement `plan_rebalance()` method skeleton
- [ ] Get current portfolio state
- [ ] Load predictions from data source
- [ ] Filter to tradeable assets
- [ ] Select top long/short assets
- [ ] Write tests for each step
- [ ] Handle missing data gracefully

**Method to Implement**:
- `plan_rebalance()` (steps 1-4)

**Helper Methods**:
- `_get_current_portfolio()`
- `_get_tradeable_symbols()`
- `_get_latest_predictions()`
- `_select_assets()`

---

### task-23: Trading Orchestrator - Plan Rebalance (Part 2) ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 6 hours
**Dependencies**: task-22

**Description**: Implement plan_rebalance workflow steps 5-7 (PRD Section 5.1).

**Acceptance Criteria**:
- [ ] Calculate target positions using PortfolioManager
- [ ] Get current market prices
- [ ] Implement `_calculate_trades()` method
- [ ] Filter trades by min notional
- [ ] Create RebalancePlan object
- [ ] Emit plan_created event
- [ ] Write comprehensive tests
- [ ] Test with different portfolio configs

**Methods to Implement**:
- `plan_rebalance()` (steps 5-7)
- `_calculate_trades()`

---

### task-24: Trading Orchestrator - Trade Calculation ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 6 hours
**Dependencies**: task-23

**Description**: Implement detailed trade calculation logic (PRD Section 5.1).

**Acceptance Criteria**:
- [ ] Calculate delta values (current → target)
- [ ] Determine trade side and size
- [ ] Round sizes to exchange precision
- [ ] Calculate limit prices
- [ ] Classify trade types
- [ ] Estimate fees
- [ ] Handle skipped trades
- [ ] Write extensive tests for edge cases

**Helper Methods**:
- `_classify_trade_type()`
- `_create_skipped_trade()`

**Test Cases**:
- Open position
- Close position
- Increase position
- Reduce position
- Flip position
- Below minimum notional
- Size rounds to zero
- Missing market price

---

### task-25: Trading Orchestrator - Execute Plan ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 5 hours
**Dependencies**: task-24

**Description**: Implement execute_plan workflow (PRD Section 5.1).

**Acceptance Criteria**:
- [ ] Implement `execute_plan()` method
- [ ] Sort trades for leverage reduction
- [ ] Execute trades (batch or sequential)
- [ ] Track successful/failed trades
- [ ] Create ExecutionResult
- [ ] Emit execution events
- [ ] Write tests for execution flow

**Method to Implement**:
- `execute_plan()`

**Helper Methods**:
- `_sort_trades_for_leverage_reduction()`
- `_execute_batch()`
- `_execute_sequential()`

---

### task-26: Trading Orchestrator - Stop Losses ⏳
**Priority**: P2 (Medium)
**Estimated Time**: 4 hours
**Dependencies**: task-25

**Description**: Implement stop loss application.

**Acceptance Criteria**:
- [ ] Implement `_apply_stop_losses()` method
- [ ] Check positions against stop loss thresholds
- [ ] Generate stop loss orders
- [ ] Track applied/failed stop losses
- [ ] Write tests for stop loss logic
- [ ] Test different stop loss configurations

**Method to Implement**:
- `_apply_stop_losses()`

---

### task-27: Backtester - Data Loading ⏳
**Priority**: P1 (High)
**Estimated Time**: 4 hours
**Dependencies**: task-6

**Description**: Implement backtester data loading (PRD Section 7.1).

**Acceptance Criteria**:
- [ ] Create `core/backtester.py`
- [ ] Implement `Backtester` class
- [ ] Implement `_load_prices()` method
- [ ] Implement `_load_predictions()` method
- [ ] Implement `_compute_returns()` method
- [ ] Handle column mappings
- [ ] Write tests with sample data

**Class to Implement**:
- `Backtester`

**Methods**:
- `_load_prices()`
- `_load_predictions()`
- `_compute_returns()`

---

### task-28: Backtester - Simulation Engine ⏳
**Priority**: P1 (High)
**Estimated Time**: 6 hours
**Dependencies**: task-27

**Description**: Implement backtest simulation loop (PRD Section 7.1).

**Acceptance Criteria**:
- [ ] Implement `_simulate()` method
- [ ] Calculate daily returns
- [ ] Handle rebalancing dates
- [ ] Apply trading costs
- [ ] Track equity and drawdown
- [ ] Calculate turnover
- [ ] Store position snapshots
- [ ] Write comprehensive simulation tests

**Method to Implement**:
- `_simulate()`

**Helper Methods**:
- `_get_valid_trading_dates()`
- `_compute_rebalance_dates()`
- `_rebalance()`

---

### task-29: Backtester - Statistics Calculation ⏳
**Priority**: P1 (High)
**Estimated Time**: 4 hours
**Dependencies**: task-28

**Description**: Implement performance statistics calculation.

**Acceptance Criteria**:
- [ ] Implement `_compute_statistics()` method
- [ ] Calculate total return, CAGR
- [ ] Calculate Sharpe ratio
- [ ] Calculate Sortino ratio
- [ ] Calculate max drawdown
- [ ] Calculate Calmar ratio
- [ ] Calculate win rate, volatility
- [ ] Write tests for all metrics

**Method to Implement**:
- `_compute_statistics()`

**Metrics**:
- Total return
- CAGR
- Sharpe ratio
- Sortino ratio
- Max drawdown
- Calmar ratio
- Annual volatility
- Win rate
- Avg turnover

---

### task-30: Backtest Optimizer ⏳
**Priority**: P2 (Medium)
**Estimated Time**: 5 hours
**Dependencies**: task-29

**Description**: Implement parameter optimization with grid search.

**Acceptance Criteria**:
- [ ] Create `BacktestOptimizer` class
- [ ] Implement grid search
- [ ] Add result caching
- [ ] Rank results by metric
- [ ] Write optimization tests
- [ ] Test with small parameter space

**Class to Implement**:
- `BacktestOptimizer`

**Features**:
- Grid search
- Result caching
- Metric ranking
- Progress tracking

---

## Phase 5: Configuration System

### task-31: Configuration Loader ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 4 hours
**Dependencies**: task-5

**Description**: Implement configuration loading from YAML and .env (PRD Section 8.2).

**Acceptance Criteria**:
- [ ] Create `config/loader.py`
- [ ] Implement `ConfigLoader` class
- [ ] Load YAML configuration
- [ ] Load .env variables
- [ ] Validate secrets exist
- [ ] Parse into TradingConfig model
- [ ] Write tests with sample configs

**Class to Implement**:
- `ConfigLoader`

**Methods**:
- `_load_env()`
- `load_config()`
- `_validate_secrets()`

---

### task-32: Configuration Overrides ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-31

**Description**: Implement CLI configuration overrides.

**Acceptance Criteria**:
- [ ] Implement `apply_overrides()` method
- [ ] Parse nested key paths
- [ ] Type conversion for values
- [ ] Re-validate with Pydantic
- [ ] Write override tests
- [ ] Test nested overrides

**Method to Implement**:
- `apply_overrides()`
- `_convert_value()`

**Test Cases**:
- Simple overrides
- Nested overrides
- Type conversion
- Invalid overrides

---

### task-33: Configuration Validator ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-31

**Description**: Implement configuration validation.

**Acceptance Criteria**:
- [ ] Create `config/validator.py`
- [ ] Validate profile existence
- [ ] Validate leverage limits
- [ ] Validate min trade value vs account size
- [ ] Provide clear error messages
- [ ] Write validation tests

**Class to Implement**:
- `ConfigValidator`

**Validations**:
- Profile existence
- Leverage limits
- Min trade value
- Position count
- Data source settings

---

### task-34: Default Configuration ⏳
**Priority**: P2 (Medium)
**Estimated Time**: 2 hours
**Dependencies**: task-5

**Description**: Create default configuration values.

**Acceptance Criteria**:
- [ ] Create `config/defaults.py`
- [ ] Define default TradingConfig
- [ ] Define default BacktestConfig
- [ ] Document all defaults
- [ ] Write tests for defaults

**File to Create**:
- `config/defaults.py`

---

## Phase 6: Utility Functions

### task-35: Logging Configuration ⏳
**Priority**: P1 (High)
**Estimated Time**: 2 hours
**Dependencies**: task-1

**Description**: Set up loguru logging configuration.

**Acceptance Criteria**:
- [ ] Create `utils/logging.py`
- [ ] Configure loguru
- [ ] Set up log levels
- [ ] Configure log rotation
- [ ] Add log formatting
- [ ] Write logging tests

**File to Create**:
- `utils/logging.py`

---

### task-36: Validation Utilities ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-1

**Description**: Create input validation utilities.

**Acceptance Criteria**:
- [ ] Create `utils/validation.py`
- [ ] Implement address validation
- [ ] Implement numeric validation
- [ ] Implement date validation
- [ ] Write validation tests

**File to Create**:
- `utils/validation.py`

**Functions**:
- `validate_ethereum_address()`
- `validate_decimal_range()`
- `validate_date_range()`

---

### task-37: Formatting Utilities ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-1

**Description**: Create number and currency formatting utilities.

**Acceptance Criteria**:
- [ ] Create `utils/formatting.py`
- [ ] Format currency values
- [ ] Format percentages
- [ ] Format dates
- [ ] Format decimals
- [ ] Write formatting tests

**File to Create**:
- `utils/formatting.py`

**Functions**:
- `format_currency()`
- `format_percentage()`
- `format_datetime()`
- `format_decimal()`

---

### task-38: Financial Calculations ⏳
**Priority**: P1 (High)
**Estimated Time**: 4 hours
**Dependencies**: task-1

**Description**: Create financial calculation utilities.

**Acceptance Criteria**:
- [ ] Create `utils/calculations.py`
- [ ] Implement leverage calculation
- [ ] Implement PNL calculation
- [ ] Implement return calculation
- [ ] Implement sharpe/sortino
- [ ] Write calculation tests with edge cases

**File to Create**:
- `utils/calculations.py`

**Functions**:
- `calculate_leverage()`
- `calculate_pnl()`
- `calculate_return()`
- `calculate_sharpe_ratio()`
- `calculate_sortino_ratio()`

---

## Phase 7: Textualize TUI

### task-39: Main App Structure ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 4 hours
**Dependencies**: task-21

**Description**: Create main Textualize app (PRD Section 9.1).

**Acceptance Criteria**:
- [ ] Create `ui/app.py`
- [ ] Implement `CCLiquidApp` class
- [ ] Set up key bindings
- [ ] Initialize core services
- [ ] Implement screen navigation
- [ ] Write app initialization tests

**Class to Implement**:
- `CCLiquidApp`

**Bindings**:
- d: Dashboard
- t: Trading
- a: Account
- b: Backtest
- o: Optimize
- h: History
- c: Config
- q: Quit

---

### task-40: Dashboard Screen ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 6 hours
**Dependencies**: task-39

**Description**: Implement live dashboard screen (PRD Section 9.2).

**Acceptance Criteria**:
- [ ] Create `ui/screens/dashboard.py`
- [ ] Implement `DashboardScreen` class
- [ ] Display account summary
- [ ] Display positions table
- [ ] Display next rebalance info
- [ ] Display open orders
- [ ] Implement auto-refresh
- [ ] Write screen tests

**Class to Implement**:
- `DashboardScreen`

**Features**:
- Auto-refresh every 1s
- Account metrics
- Positions table
- Rebalance countdown
- Open orders

---

### task-41: Trading Screen ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 6 hours
**Dependencies**: task-39, task-25

**Description**: Implement trading/rebalancing screen (PRD Section 9.3).

**Acceptance Criteria**:
- [ ] Create `ui/screens/trading.py`
- [ ] Implement `TradingScreen` class
- [ ] Plan rebalance button
- [ ] Execute plan button
- [ ] Display trade plan preview
- [ ] Show execution confirmation
- [ ] Display execution results
- [ ] Write screen tests

**Class to Implement**:
- `TradingScreen`

**Features**:
- Plan button
- Execute button (disabled until plan)
- Trade table preview
- Confirmation modal
- Result display

---

### task-42: Account Screen ⏳
**Priority**: P1 (High)
**Estimated Time**: 5 hours
**Dependencies**: task-39

**Description**: Implement detailed account screen (PRD Section 9.4).

**Acceptance Criteria**:
- [ ] Create `ui/screens/account.py`
- [ ] Implement `AccountScreen` class
- [ ] Display account metrics
- [ ] Display detailed positions
- [ ] Display margin breakdown
- [ ] Add refresh functionality
- [ ] Write screen tests

**Class to Implement**:
- `AccountScreen`

---

### task-43: Backtest Screen ⏳
**Priority**: P1 (High)
**Estimated Time**: 6 hours
**Dependencies**: task-39, task-29

**Description**: Implement backtesting screen (PRD Section 9.5).

**Acceptance Criteria**:
- [ ] Create `ui/screens/backtest.py`
- [ ] Implement `BacktestScreen` class
- [ ] Configuration inputs
- [ ] Run backtest button
- [ ] Display results
- [ ] Show performance metrics
- [ ] Display equity chart
- [ ] Write screen tests

**Class to Implement**:
- `BacktestScreen`

**Features**:
- Parameter inputs
- Run button
- Metrics display
- Performance table
- Equity curve chart

---

### task-44: Optimize Screen ⏳
**Priority**: P2 (Medium)
**Estimated Time**: 5 hours
**Dependencies**: task-39, task-30

**Description**: Implement optimization screen.

**Acceptance Criteria**:
- [ ] Create `ui/screens/optimize.py`
- [ ] Implement `OptimizeScreen` class
- [ ] Parameter range inputs
- [ ] Run optimization button
- [ ] Display results table
- [ ] Show best parameters
- [ ] Write screen tests

**Class to Implement**:
- `OptimizeScreen`

---

### task-45: History Screen ⏳
**Priority**: P2 (Medium)
**Estimated Time**: 4 hours
**Dependencies**: task-39

**Description**: Implement trade history screen.

**Acceptance Criteria**:
- [ ] Create `ui/screens/history.py`
- [ ] Implement `HistoryScreen` class
- [ ] Display fill history
- [ ] Filter by date range
- [ ] Show trade details
- [ ] Write screen tests

**Class to Implement**:
- `HistoryScreen`

---

### task-46: Config Screen ⏳
**Priority**: P2 (Medium)
**Estimated Time**: 5 hours
**Dependencies**: task-39

**Description**: Implement configuration screen.

**Acceptance Criteria**:
- [ ] Create `ui/screens/config.py`
- [ ] Implement `ConfigScreen` class
- [ ] Display current config
- [ ] Allow in-app editing
- [ ] Validate changes
- [ ] Save configuration
- [ ] Write screen tests

**Class to Implement**:
- `ConfigScreen`

---

### task-47: Portfolio Table Widget ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-40

**Description**: Create reusable portfolio table widget (PRD Section 9.6).

**Acceptance Criteria**:
- [ ] Create `ui/widgets/portfolio_table.py`
- [ ] Implement `PortfolioTable` class
- [ ] Update positions method
- [ ] Color-coded PNL
- [ ] Sortable columns
- [ ] Write widget tests

**Class to Implement**:
- `PortfolioTable`

---

### task-48: Metrics Panel Widget ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-40

**Description**: Create metrics panel widget (PRD Section 9.6).

**Acceptance Criteria**:
- [ ] Create `ui/widgets/metrics_panel.py`
- [ ] Implement `MetricsPanel` class
- [ ] Grid layout
- [ ] Update metrics method
- [ ] Write widget tests

**Class to Implement**:
- `MetricsPanel`

---

### task-49: Chart Widget ⏳
**Priority**: P2 (Medium)
**Estimated Time**: 4 hours
**Dependencies**: task-43

**Description**: Create ASCII chart widget (PRD Section 9.6).

**Acceptance Criteria**:
- [ ] Create `ui/widgets/chart.py`
- [ ] Implement `ChartWidget` class using plotext
- [ ] Plot equity curve
- [ ] Plot drawdown
- [ ] Customizable appearance
- [ ] Write widget tests

**Class to Implement**:
- `ChartWidget`

**Methods**:
- `plot_equity_curve()`
- `plot_drawdown()`

---

### task-50: Trade Plan Widget ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-41

**Description**: Create trade plan preview widget.

**Acceptance Criteria**:
- [ ] Create `ui/widgets/trade_plan.py`
- [ ] Implement `TradePlanWidget`
- [ ] Display trade summary
- [ ] Display trade list
- [ ] Color coding by type
- [ ] Write widget tests

**Class to Implement**:
- `TradePlanWidget`

---

### task-51: Order Book Widget ⏳
**Priority**: P3 (Low)
**Estimated Time**: 4 hours
**Dependencies**: task-39

**Description**: Create order book display widget.

**Acceptance Criteria**:
- [ ] Create `ui/widgets/order_book.py`
- [ ] Implement `OrderBookWidget`
- [ ] Display bids/asks
- [ ] Real-time updates
- [ ] Write widget tests

**Class to Implement**:
- `OrderBookWidget`

---

### task-52: Stylesheet Configuration ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-39

**Description**: Create main TCSS stylesheet (PRD Section 9.7).

**Acceptance Criteria**:
- [ ] Create `ui/styles/main.tcss`
- [ ] Define brutalist color scheme
- [ ] Style all screens
- [ ] Style all widgets
- [ ] Test appearance
- [ ] Ensure high contrast

**File to Create**:
- `ui/styles/main.tcss`

**Colors**:
- Surface: #001926
- Panel: #002030
- Primary: #62e4fb
- Accent: #4152A8

---

### task-53: Confirmation Modal ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-41

**Description**: Create confirmation modal widget.

**Acceptance Criteria**:
- [ ] Create confirmation modal
- [ ] Yes/No buttons
- [ ] Callback support
- [ ] Keyboard navigation
- [ ] Write modal tests

**Class to Implement**:
- `ConfirmationModal`

---

### task-54: Result Modal ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-41

**Description**: Create execution result modal.

**Acceptance Criteria**:
- [ ] Create result modal
- [ ] Display success/failure counts
- [ ] Show trade details
- [ ] OK button to dismiss
- [ ] Write modal tests

**Class to Implement**:
- `ExecutionResultModal`

---

## Phase 8: Integration & Testing

### task-55: Integration Test - Full Trading Flow ⏳
**Priority**: P0 (Critical)
**Estimated Time**: 5 hours
**Dependencies**: task-25, task-11, task-16

**Description**: Write end-to-end trading flow test (PRD Section 10.2).

**Acceptance Criteria**:
- [ ] Create `tests/integration/test_trading_flow.py`
- [ ] Test plan → execute cycle
- [ ] Use mock exchange
- [ ] Use mock data source
- [ ] Verify orders submitted
- [ ] Verify positions updated
- [ ] Write comprehensive assertions

**Test File**:
- `tests/integration/test_trading_flow.py`

---

### task-56: Integration Test - Config Loading ⏳
**Priority**: P1 (High)
**Estimated Time**: 3 hours
**Dependencies**: task-31

**Description**: Test configuration loading and validation.

**Acceptance Criteria**:
- [ ] Create `tests/integration/test_config_loading.py`
- [ ] Test YAML loading
- [ ] Test .env loading
- [ ] Test secret validation
- [ ] Test override application
- [ ] Write error case tests

**Test File**:
- `tests/integration/test_config_loading.py`

---

### task-57: Integration Test - Backtest Flow ⏳
**Priority**: P1 (High)
**Estimated Time**: 4 hours
**Dependencies**: task-29

**Description**: Test complete backtest workflow.

**Acceptance Criteria**:
- [ ] Create `tests/integration/test_backtest_flow.py`
- [ ] Test with sample data
- [ ] Verify all metrics calculated
- [ ] Test edge cases
- [ ] Write comprehensive tests

**Test File**:
- `tests/integration/test_backtest_flow.py`

---

### task-58: Test Fixtures ⏳
**Priority**: P1 (High)
**Estimated Time**: 4 hours
**Dependencies**: task-1

**Description**: Create test data fixtures.

**Acceptance Criteria**:
- [ ] Create sample predictions.parquet
- [ ] Create sample prices.parquet
- [ ] Create sample config.yaml
- [ ] Create sample .env
- [ ] Document fixture usage

**Files to Create**:
- `tests/fixtures/predictions.parquet`
- `tests/fixtures/prices.parquet`
- `tests/fixtures/config.yaml`

---

### task-59: Coverage Report Setup ⏳
**Priority**: P1 (High)
**Estimated Time**: 2 hours
**Dependencies**: task-1

**Description**: Set up test coverage reporting.

**Acceptance Criteria**:
- [ ] Configure pytest-cov
- [ ] Set minimum coverage thresholds
- [ ] Generate HTML reports
- [ ] Document coverage targets
- [ ] Write coverage requirements

**Target Coverage**:
- Overall: 80%
- Critical path: 95%

---

### task-60: Documentation ⏳
**Priority**: P2 (Medium)
**Estimated Time**: 6 hours
**Dependencies**: All implementation tasks

**Description**: Create comprehensive documentation.

**Acceptance Criteria**:
- [ ] Create README.md
- [ ] API documentation
- [ ] Usage examples
- [ ] Architecture guide
- [ ] Testing guide
- [ ] Contribution guide

**Files to Create**:
- `cc-flow/README.md`
- `cc-flow/docs/API.md`
- `cc-flow/docs/ARCHITECTURE.md`
- `cc-flow/docs/TESTING.md`

---

## Summary Statistics

**Total Tasks**: 60
**Completed Tasks**: 34/60 (57%)
**Priority Breakdown**:
- P0 (Critical): 17 tasks (12 completed)
- P1 (High): 29 tasks (18 completed)
- P2 (Medium): 12 tasks (4 completed)
- P3 (Low): 2 tasks (0 completed)

**Estimated Total Time**: ~230 hours (~6 weeks at 40 hours/week)
**Time Spent**: ~120 hours (52%)

**Phase Breakdown**:
1. Core Infrastructure: 6 tasks (17 hours) - ✅ 100% COMPLETE
2. Exchange Layer: 5 tasks (24 hours) - ✅ 100% COMPLETE
3. Data Sources: 5 tasks (16 hours) - ✅ 100% COMPLETE
4. Business Logic: 14 tasks (57 hours) - 🔄 64% COMPLETE (9/14)
5. Configuration: 4 tasks (12 hours) - ✅ 100% COMPLETE
6. Utilities: 4 tasks (12 hours) - ✅ 100% COMPLETE
7. TUI: 16 tasks (66 hours) - ⏳ 0% COMPLETE (0/16)
8. Testing: 6 tasks (26 hours) - ⏳ 0% COMPLETE (0/6)

**Last Updated**: 2025-11-08 (Progress Report)

---

## Notes for Junior Engineers

1. **Follow TDD**: Write tests before implementation
2. **Use Type Hints**: All functions must have proper type annotations
3. **Document Code**: Use docstrings for all classes and methods
4. **SOLID Principles**: Keep classes focused and small (<300 lines)
5. **Use Loguru**: For all logging needs
6. **Pydantic v2**: Use model_dump(), not dict()
7. **Ask Questions**: If requirements are unclear, ask for clarification
8. **Run Tests**: Ensure all tests pass before marking task complete
9. **Code Review**: Request review after each task completion
10. **Update Status**: Mark tasks as complete when done

---

**Last Updated**: 2025-11-08
**Document Version**: 1.0
