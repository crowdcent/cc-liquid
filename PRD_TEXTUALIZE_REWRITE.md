# Product Requirements Document: cc-liquid Textualize Reimplementation

**Version:** 1.0
**Date:** 2025-11-08
**Status:** Draft for Implementation
**Target Framework:** Textualize (Python TUI framework)
**Original Implementation:** Click + Rich CLI

---

## Executive Summary

This document specifies the complete reimplementation of cc-liquid, a metamodel-based portfolio rebalancer for cryptocurrency perpetual futures exchanges, using the Textualize framework. The rewrite introduces full abstraction layers for exchange connectivity and data sources, enabling multi-exchange support while maintaining backward compatibility with the current Hyperliquid-focused implementation.

**Key Objectives:**
1. Replace Click+Rich CLI with Textualize TUI (Terminal User Interface)
2. Abstract exchange layer to support multiple perpetual futures exchanges
3. Abstract data source layer for flexible prediction input
4. Maintain all existing functionality (trading, backtesting, optimization, monitoring)
5. Provide comprehensive test coverage for all components
6. Enable easy extension for future exchanges and data sources

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Core Domain Models](#2-core-domain-models)
3. [Exchange Abstraction Layer](#3-exchange-abstraction-layer)
4. [Data Source Abstraction Layer](#4-data-source-abstraction-layer)
5. [Trading Engine](#5-trading-engine)
6. [Portfolio Management](#6-portfolio-management)
7. [Backtesting Engine](#7-backtesting-engine)
8. [Configuration System](#8-configuration-system)
9. [Textualize TUI Specifications](#9-textualize-tui-specifications)
10. [Testing Requirements](#10-testing-requirements)
11. [Migration Strategy](#11-migration-strategy)
12. [API Reference](#12-api-reference)
13. [Edge Cases and Error Handling](#13-edge-cases-and-error-handling)

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Textualize TUI Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Dashboard   │  │   Trading    │  │  Backtest    │         │
│  │    Screen    │  │   Screen     │  │   Screen     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────────┐
│                    Application Core Layer                       │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Trading Orchestrator                      │    │
│  │  - Plan/Execute workflow                              │    │
│  │  - State management                                   │    │
│  │  - Event coordination                                 │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────┐ │
│  │ Portfolio  │  │ Backtester │  │ Optimizer  │  │ History │ │
│  │  Manager   │  │            │  │            │  │ Tracker │ │
│  └────────────┘  └────────────┘  └────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────────┐
│                  Abstraction Layer                              │
│  ┌──────────────────────────┐  ┌──────────────────────────┐   │
│  │   Exchange Interface     │  │   Data Source Interface  │   │
│  │  ┌────────────────────┐  │  │  ┌────────────────────┐  │   │
│  │  │  Info API          │  │  │  │  Prediction Loader │  │   │
│  │  │  - Account state   │  │  │  │  - CrowdCent       │  │   │
│  │  │  - Positions       │  │  │  │  - Numerai         │  │   │
│  │  │  - Market data     │  │  │  │  - Local files     │  │   │
│  │  │  - Order history   │  │  │  │  - Custom API      │  │   │
│  │  └────────────────────┘  │  │  └────────────────────┘  │   │
│  │  ┌────────────────────┐  │  │                          │   │
│  │  │  Trading API       │  │  │                          │   │
│  │  │  - Order execution │  │  │                          │   │
│  │  │  - Order cancel    │  │  │                          │   │
│  │  │  - Batch orders    │  │  │                          │   │
│  │  └────────────────────┘  │  │                          │   │
│  └──────────────────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────────┐
│              Exchange/Data Source Implementations               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Hyperliquid │  │   Binance   │  │     dYdX    │            │
│  │   Adapter   │  │   Adapter   │  │   Adapter   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Module Structure

```
src/cc_liquid_tui/
├── __init__.py
├── main.py                      # Application entry point
│
├── core/                        # Core business logic
│   ├── __init__.py
│   ├── trader.py               # Trading orchestrator
│   ├── portfolio.py            # Portfolio management
│   ├── backtester.py           # Backtesting engine
│   ├── optimizer.py            # Parameter optimization
│   ├── history.py              # Trade history tracking
│   └── state.py                # Application state management
│
├── domain/                      # Domain models (Pydantic v2)
│   ├── __init__.py
│   ├── account.py              # Account, Position models
│   ├── orders.py               # Order, Trade models
│   ├── portfolio.py            # Portfolio targets, weights
│   ├── backtest.py             # Backtest config and results
│   └── config.py               # Configuration models
│
├── exchanges/                   # Exchange abstraction
│   ├── __init__.py
│   ├── base.py                 # Abstract base classes
│   ├── hyperliquid.py          # Hyperliquid implementation
│   ├── binance.py              # Binance futures (future)
│   ├── dydx.py                 # dYdX v4 (future)
│   └── mock.py                 # Mock exchange for testing
│
├── data_sources/                # Data source abstraction
│   ├── __init__.py
│   ├── base.py                 # Abstract base classes
│   ├── crowdcent.py            # CrowdCent API
│   ├── numerai.py              # Numerai API
│   ├── local.py                # Local file loader
│   └── mock.py                 # Mock data source for testing
│
├── ui/                          # Textualize TUI
│   ├── __init__.py
│   ├── app.py                  # Main Textualize App
│   ├── screens/                # Screen definitions
│   │   ├── __init__.py
│   │   ├── dashboard.py       # Live monitoring dashboard
│   │   ├── trading.py         # Trading/rebalancing screen
│   │   ├── account.py         # Account info screen
│   │   ├── backtest.py        # Backtesting screen
│   │   ├── optimize.py        # Optimization screen
│   │   ├── config.py          # Configuration screen
│   │   └── history.py         # Trade history screen
│   ├── widgets/                # Reusable widgets
│   │   ├── __init__.py
│   │   ├── portfolio_table.py # Portfolio position table
│   │   ├── trade_plan.py      # Trade plan preview
│   │   ├── metrics_panel.py   # Performance metrics
│   │   ├── order_book.py      # Order book widget
│   │   └── chart.py           # Price/PNL charts
│   └── styles/                 # CSS/TCSS stylesheets
│       ├── __init__.py
│       └── main.tcss          # Main stylesheet
│
├── utils/                       # Utility functions
│   ├── __init__.py
│   ├── logging.py              # Loguru configuration
│   ├── validation.py           # Input validation
│   ├── formatting.py           # Number/currency formatting
│   └── calculations.py         # Financial calculations
│
└── config/                      # Configuration management
    ├── __init__.py
    ├── loader.py               # Config file loading
    ├── validator.py            # Config validation
    └── defaults.py             # Default values

tests/
├── unit/                        # Unit tests
│   ├── test_trader.py
│   ├── test_portfolio.py
│   ├── test_backtester.py
│   ├── test_exchanges/
│   │   ├── test_base.py
│   │   ├── test_hyperliquid.py
│   │   └── test_mock.py
│   └── test_data_sources/
│       ├── test_base.py
│       ├── test_crowdcent.py
│       └── test_local.py
├── integration/                 # Integration tests
│   ├── test_trading_flow.py
│   ├── test_backtest_flow.py
│   └── test_config_loading.py
└── fixtures/                    # Test data fixtures
    ├── predictions.parquet
    ├── prices.parquet
    └── config.yaml
```

---

## 2. Core Domain Models

### 2.1 Pydantic v2 Models

All models use Pydantic v2 with strict type validation and JSON serialization.

#### 2.1.1 Account Models (`domain/account.py`)

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from decimal import Decimal
from datetime import datetime

class AccountInfo(BaseModel):
    """Account-level information."""
    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)

    account_value: Decimal = Field(..., description="Total account value in USD")
    total_position_value: Decimal = Field(..., description="Sum of absolute position values")
    margin_used: Decimal = Field(..., description="Margin currently in use")
    free_collateral: Decimal = Field(..., description="Available margin")
    cash_balance: Decimal = Field(..., description="Cash balance")
    withdrawable: Decimal = Field(..., description="Amount available for withdrawal")
    current_leverage: Decimal = Field(..., description="Current leverage ratio")

    # Optional cross-margin info
    cross_leverage: Optional[Decimal] = None
    cross_margin_used: Optional[Decimal] = None
    cross_maintenance_margin: Optional[Decimal] = None

    # Raw data for debugging
    raw_data: Optional[dict] = None

    @property
    def leverage_percentage(self) -> float:
        """Current leverage as percentage."""
        return float(self.current_leverage * 100)

class Position(BaseModel):
    """Individual position information."""
    model_config = ConfigDict(frozen=False)

    coin: str = Field(..., description="Asset symbol")
    side: str = Field(..., description="LONG or SHORT")
    size: Decimal = Field(..., description="Position size (always positive)")
    entry_price: Decimal = Field(..., description="Average entry price")
    mark_price: Decimal = Field(..., description="Current mark price")
    value: Decimal = Field(..., description="Position notional value")
    unrealized_pnl: Decimal = Field(..., description="Unrealized profit/loss")
    return_pct: Decimal = Field(..., description="Return percentage")

    liquidation_price: Optional[Decimal] = None
    margin_used: Optional[Decimal] = None

    @property
    def signed_size(self) -> Decimal:
        """Size with sign (+ for long, - for short)."""
        return self.size if self.side == "LONG" else -self.size

class PortfolioSnapshot(BaseModel):
    """Complete portfolio state at a point in time."""
    model_config = ConfigDict(frozen=False)

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    account: AccountInfo
    positions: list[Position] = Field(default_factory=list)

    @property
    def total_long_value(self) -> Decimal:
        return sum(p.value for p in self.positions if p.side == "LONG")

    @property
    def total_short_value(self) -> Decimal:
        return sum(p.value for p in self.positions if p.side == "SHORT")

    @property
    def net_exposure(self) -> Decimal:
        return self.total_long_value - self.total_short_value

    @property
    def total_unrealized_pnl(self) -> Decimal:
        return sum(p.unrealized_pnl for p in self.positions)
```

#### 2.1.2 Order Models (`domain/orders.py`)

```python
from enum import Enum
from typing import Literal, Union

class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"

class TimeInForce(str, Enum):
    """Time in force options."""
    IOC = "Ioc"  # Immediate or Cancel
    GTC = "Gtc"  # Good til Canceled
    ALO = "Alo"  # Add Liquidity Only

class OrderSide(str, Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(str, Enum):
    """Order execution status."""
    PENDING = "pending"
    FILLED = "filled"
    RESTING = "resting"  # On book (Gtc/Alo)
    FAILED = "failed"
    CANCELLED = "cancelled"

class OrderRequest(BaseModel):
    """Order request to exchange."""
    model_config = ConfigDict(frozen=True)

    coin: str
    side: OrderSide
    size: Decimal
    order_type: OrderType

    # Pricing
    limit_price: Optional[Decimal] = None  # Required for limit orders

    # Execution parameters
    time_in_force: TimeInForce = TimeInForce.IOC
    reduce_only: bool = False

    # Metadata
    client_order_id: Optional[str] = None

class OrderResult(BaseModel):
    """Result of order execution."""
    model_config = ConfigDict(frozen=False)

    order_request: OrderRequest
    status: OrderStatus

    # Filled order data
    filled_size: Optional[Decimal] = None
    average_price: Optional[Decimal] = None
    total_fee: Optional[Decimal] = None

    # Exchange IDs
    order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None

    # Timestamps
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None

    # Error info
    error_message: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.status in (OrderStatus.FILLED, OrderStatus.RESTING)

class Trade(BaseModel):
    """Planned or executed trade."""
    model_config = ConfigDict(frozen=False)

    coin: str
    side: OrderSide
    size: Decimal

    # Pricing
    reference_price: Decimal  # Market price at planning time
    limit_price: Optional[Decimal] = None

    # Position context
    current_value: Decimal  # Current position value (signed)
    target_value: Decimal   # Target position value (signed)
    delta_value: Decimal    # Change in value

    # Classification
    trade_type: Literal["open", "close", "reduce", "increase", "flip"]

    # Cost estimates
    estimated_fee: Decimal
    estimated_slippage: Optional[Decimal] = None

    # Execution result
    order_result: Optional[OrderResult] = None

    @property
    def is_executed(self) -> bool:
        return self.order_result is not None

    @property
    def is_successful(self) -> bool:
        return self.order_result is not None and self.order_result.is_success
```

#### 2.1.3 Portfolio Models (`domain/portfolio.py`)

```python
class TargetPosition(BaseModel):
    """Target position specification."""
    model_config = ConfigDict(frozen=True)

    coin: str
    target_value: Decimal  # Signed notional value
    weight: Decimal  # Leverage-adjusted weight

    @property
    def side(self) -> str:
        return "LONG" if self.target_value > 0 else "SHORT"

class RebalancePlan(BaseModel):
    """Complete rebalancing plan."""
    model_config = ConfigDict(frozen=False)

    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Portfolio state
    account_value: Decimal
    current_leverage: Decimal
    target_leverage: Decimal

    # Targets
    target_positions: list[TargetPosition]

    # Trades
    executable_trades: list[Trade]
    skipped_trades: list[Trade] = Field(default_factory=list)

    # Metadata
    open_orders: list[dict] = Field(default_factory=list)

    @property
    def total_trades(self) -> int:
        return len(self.executable_trades) + len(self.skipped_trades)

    @property
    def total_trade_value(self) -> Decimal:
        return sum(abs(t.delta_value) for t in self.executable_trades)

class ExecutionResult(BaseModel):
    """Result of executing a rebalance plan."""
    model_config = ConfigDict(frozen=False)

    plan: RebalancePlan
    executed_at: datetime = Field(default_factory=datetime.utcnow)

    successful_trades: list[Trade]
    failed_trades: list[Trade] = Field(default_factory=list)

    # Stop loss info
    stop_losses_applied: int = 0
    stop_losses_failed: int = 0

    @property
    def success_rate(self) -> float:
        total = len(self.successful_trades) + len(self.failed_trades)
        return len(self.successful_trades) / total if total > 0 else 0.0
```

---

## 3. Exchange Abstraction Layer

### 3.1 Base Exchange Interface (`exchanges/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Optional, Protocol
import polars as pl

class ExchangeInfo(Protocol):
    """Exchange information/query interface."""

    @abstractmethod
    async def get_account_state(self, owner_address: str) -> dict:
        """Get account state from exchange."""
        ...

    @abstractmethod
    async def get_open_positions(self, owner_address: str) -> list[dict]:
        """Get open positions."""
        ...

    @abstractmethod
    async def get_open_orders(self, owner_address: str) -> list[dict]:
        """Get open orders."""
        ...

    @abstractmethod
    async def get_fill_history(
        self,
        owner_address: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> list[dict]:
        """Get trade fill history."""
        ...

    @abstractmethod
    async def get_market_prices(self, symbols: Optional[list[str]] = None) -> dict[str, Decimal]:
        """Get current market prices (mid prices)."""
        ...

    @abstractmethod
    async def get_exchange_metadata(self) -> dict:
        """Get exchange metadata (tradeable symbols, precision, etc)."""
        ...

    @abstractmethod
    async def get_fee_rates(self, owner_address: str) -> dict:
        """Get fee rates for account."""
        ...

class ExchangeTrading(Protocol):
    """Exchange trading/execution interface."""

    @abstractmethod
    async def submit_order(self, order: OrderRequest) -> OrderResult:
        """Submit single order."""
        ...

    @abstractmethod
    async def submit_batch_orders(self, orders: list[OrderRequest]) -> list[OrderResult]:
        """Submit multiple orders in batch."""
        ...

    @abstractmethod
    async def cancel_order(self, coin: str, order_id: str) -> dict:
        """Cancel specific order."""
        ...

    @abstractmethod
    async def cancel_batch_orders(self, cancel_requests: list[dict]) -> dict:
        """Cancel multiple orders."""
        ...

    @abstractmethod
    async def modify_order(
        self,
        coin: str,
        order_id: str,
        new_size: Optional[Decimal] = None,
        new_price: Optional[Decimal] = None
    ) -> OrderResult:
        """Modify existing order."""
        ...

class Exchange(ABC):
    """Abstract base class for exchange implementations."""

    def __init__(self, config: dict):
        self.config = config
        self.info: ExchangeInfo = self._create_info_client()
        self.trading: ExchangeTrading = self._create_trading_client()

    @abstractmethod
    def _create_info_client(self) -> ExchangeInfo:
        """Create info/query client."""
        ...

    @abstractmethod
    def _create_trading_client(self) -> ExchangeTrading:
        """Create trading client."""
        ...

    @abstractmethod
    def parse_account_state(self, raw_data: dict) -> PortfolioSnapshot:
        """Parse raw account state to domain model."""
        ...

    @abstractmethod
    def round_size(self, coin: str, size: Decimal) -> Decimal:
        """Round size to exchange precision."""
        ...

    @abstractmethod
    def round_price(self, coin: str, price: Decimal) -> Decimal:
        """Round price to exchange precision."""
        ...

    @abstractmethod
    def calculate_limit_price(
        self,
        coin: str,
        side: OrderSide,
        reference_price: Decimal,
        order_type: OrderType,
        slippage_tolerance: Decimal,
        limit_offset: Decimal
    ) -> Decimal:
        """Calculate limit price based on order type and parameters."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Exchange name."""
        ...

    @property
    @abstractmethod
    def supports_batch_orders(self) -> bool:
        """Whether exchange supports batch order submission."""
        ...
```

### 3.2 Hyperliquid Implementation (`exchanges/hyperliquid.py`)

```python
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange as HLExchange
from eth_account import Account

class HyperliquidInfo:
    """Hyperliquid info client wrapper."""

    def __init__(self, base_url: str):
        self.client = Info(base_url, skip_ws=True)
        self._metadata_cache: Optional[dict] = None

    async def get_account_state(self, owner_address: str) -> dict:
        return self.client.user_state(owner_address)

    async def get_open_positions(self, owner_address: str) -> list[dict]:
        state = await self.get_account_state(owner_address)
        positions = []
        for asset_pos in state.get("assetPositions", []):
            pos = asset_pos.get("position", {})
            if float(pos.get("szi", 0)) != 0:
                positions.append(pos)
        return positions

    async def get_open_orders(self, owner_address: str) -> list[dict]:
        return self.client.open_orders(owner_address)

    async def get_fill_history(
        self,
        owner_address: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> list[dict]:
        if start_time is not None:
            return self.client.user_fills_by_time(owner_address, start_time, end_time)
        return self.client.user_fills(owner_address)

    async def get_market_prices(self, symbols: Optional[list[str]] = None) -> dict[str, Decimal]:
        all_mids = self.client.all_mids()
        if symbols is None:
            return {k: Decimal(str(v)) for k, v in all_mids.items()}
        return {s: Decimal(str(all_mids[s])) for s in symbols if s in all_mids}

    async def get_exchange_metadata(self) -> dict:
        if self._metadata_cache is None:
            self._metadata_cache = self.client.meta()
        return self._metadata_cache

    async def get_fee_rates(self, owner_address: str) -> dict:
        return self.client.user_fees(owner_address)

class HyperliquidTrading:
    """Hyperliquid trading client wrapper."""

    def __init__(self, private_key: str, base_url: str, vault_address: Optional[str], account_address: str):
        account = Account.from_key(private_key)
        self.client = HLExchange(
            account,
            base_url,
            vault_address=vault_address,
            account_address=account_address
        )

    async def submit_order(self, order: OrderRequest) -> OrderResult:
        # Convert to HL format
        hl_order = self._convert_order_to_hl(order)
        result = self.client.order(hl_order)
        return self._parse_order_result(order, result)

    async def submit_batch_orders(self, orders: list[OrderRequest]) -> list[OrderResult]:
        hl_orders = [self._convert_order_to_hl(o) for o in orders]
        result = self.client.bulk_orders(hl_orders)
        return self._parse_batch_result(orders, result)

    # ... implementation details

class HyperliquidExchange(Exchange):
    """Hyperliquid exchange implementation."""

    def __init__(self, config: dict):
        super().__init__(config)
        self._sz_decimals_cache: Optional[dict[str, int]] = None

    def _create_info_client(self) -> ExchangeInfo:
        base_url = self.config["base_url"]
        return HyperliquidInfo(base_url)

    def _create_trading_client(self) -> ExchangeTrading:
        return HyperliquidTrading(
            private_key=self.config["private_key"],
            base_url=self.config["base_url"],
            vault_address=self.config.get("vault_address"),
            account_address=self.config["account_address"]
        )

    def parse_account_state(self, raw_data: dict) -> PortfolioSnapshot:
        """Convert Hyperliquid user_state to PortfolioSnapshot."""
        margin_summary = raw_data.get("marginSummary", {})

        account = AccountInfo(
            account_value=Decimal(str(margin_summary.get("accountValue", 0))),
            total_position_value=Decimal(str(margin_summary.get("totalNtlPos", 0))),
            margin_used=Decimal(str(margin_summary.get("totalMarginUsed", 0))),
            free_collateral=Decimal(str(margin_summary.get("accountValue", 0))) - Decimal(str(margin_summary.get("totalMarginUsed", 0))),
            cash_balance=Decimal(str(margin_summary.get("totalRawUsd", 0))),
            withdrawable=Decimal(str(raw_data.get("withdrawable", 0))),
            current_leverage=Decimal(str(margin_summary.get("totalNtlPos", 0))) / Decimal(str(margin_summary.get("accountValue", 1))),
            raw_data=raw_data
        )

        # Parse positions
        positions = []
        all_mids = await self.info.get_market_prices()

        for asset_pos in raw_data.get("assetPositions", []):
            pos_data = asset_pos.get("position", {})
            size = Decimal(str(pos_data.get("szi", 0)))

            if size == 0:
                continue

            coin = pos_data["coin"]
            entry_px = Decimal(str(pos_data.get("entryPx", 0)))
            mark_px = all_mids.get(coin, entry_px)

            position = Position(
                coin=coin,
                side="LONG" if size > 0 else "SHORT",
                size=abs(size),
                entry_price=entry_px,
                mark_price=mark_px,
                value=abs(size * mark_px),
                unrealized_pnl=(mark_px - entry_px) * size if size > 0 else (entry_px - mark_px) * abs(size),
                return_pct=((mark_px - entry_px) / entry_px * 100) if entry_px > 0 else Decimal(0),
                liquidation_price=Decimal(str(pos_data.get("liquidationPx"))) if pos_data.get("liquidationPx") else None,
                margin_used=Decimal(str(pos_data.get("marginUsed"))) if pos_data.get("marginUsed") else None
            )
            positions.append(position)

        return PortfolioSnapshot(account=account, positions=positions)

    def round_size(self, coin: str, size: Decimal) -> Decimal:
        """Round size to Hyperliquid's szDecimals precision."""
        sz_decimals = self._get_sz_decimals(coin)
        if sz_decimals is None:
            return size
        return Decimal(str(round(float(size), sz_decimals)))

    def round_price(self, coin: str, price: Decimal) -> Decimal:
        """Round price per Hyperliquid perp rules."""
        if price > 100_000:
            return Decimal(str(round(float(price))))

        sz_decimals = self._get_sz_decimals(coin)
        if sz_decimals is None:
            # Default to 5 sig figs
            return Decimal(f"{float(price):.5g}")

        max_decimals = 6  # Perps use 6 decimals max
        return Decimal(str(round(float(f"{float(price):.5g}"), max_decimals - sz_decimals)))

    def _get_sz_decimals(self, coin: str) -> Optional[int]:
        """Get szDecimals for coin from metadata."""
        if self._sz_decimals_cache is None:
            metadata = await self.info.get_exchange_metadata()
            universe = metadata.get("universe", [])
            self._sz_decimals_cache = {
                asset["name"]: asset.get("szDecimals", 2)
                for asset in universe
                if not asset.get("isDelisted", False)
            }

        return self._sz_decimals_cache.get(coin)

    @property
    def name(self) -> str:
        return "hyperliquid"

    @property
    def supports_batch_orders(self) -> bool:
        return True
```

### 3.3 Mock Exchange (`exchanges/mock.py`)

```python
class MockExchange(Exchange):
    """Mock exchange for testing with configurable behavior."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.submitted_orders: list[OrderRequest] = []
        self.cancelled_orders: list[str] = []

        # Configurable responses
        self.mock_account_value = Decimal("100000")
        self.mock_positions: dict[str, Position] = {}
        self.mock_prices: dict[str, Decimal] = {}
        self.order_fill_behavior = "always_fill"  # "always_fill", "always_fail", "random"

    # ... implementation for testing
```

---

## 4. Data Source Abstraction Layer

### 4.1 Base Data Source Interface (`data_sources/base.py`)

```python
from abc import ABC, abstractmethod
import polars as pl

class PredictionMetadata(BaseModel):
    """Metadata about prediction data."""
    model_config = ConfigDict(frozen=True)

    source: str
    num_assets: int
    date_range: tuple[datetime, datetime]
    prediction_column: str
    last_updated: datetime

class DataSource(ABC):
    """Abstract base class for prediction data sources."""

    @abstractmethod
    async def load_predictions(self) -> pl.DataFrame:
        """Load prediction data as polars DataFrame.

        Returns:
            DataFrame with columns:
            - date: datetime
            - asset_id: str
            - prediction: float
        """
        ...

    @abstractmethod
    async def get_metadata(self) -> PredictionMetadata:
        """Get metadata about the data source."""
        ...

    @abstractmethod
    async def validate_schema(self, df: pl.DataFrame) -> bool:
        """Validate that DataFrame has required schema."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Data source name."""
        ...

class CachedDataSource(DataSource):
    """Base class for data sources with caching support."""

    def __init__(self, cache_ttl: int = 3600):
        self._cache: Optional[pl.DataFrame] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = cache_ttl

    async def load_predictions(self) -> pl.DataFrame:
        if self._is_cache_valid():
            return self._cache

        df = await self._fetch_predictions()
        self._cache = df
        self._cache_time = datetime.utcnow()
        return df

    @abstractmethod
    async def _fetch_predictions(self) -> pl.DataFrame:
        """Fetch fresh predictions from source."""
        ...

    def _is_cache_valid(self) -> bool:
        if self._cache is None or self._cache_time is None:
            return False
        age = (datetime.utcnow() - self._cache_time).total_seconds()
        return age < self._cache_ttl
```

### 4.2 CrowdCent Data Source (`data_sources/crowdcent.py`)

```python
from crowdcent_challenge import ChallengeClient

class CrowdCentDataSource(CachedDataSource):
    """CrowdCent API data source."""

    def __init__(
        self,
        api_key: str,
        challenge_slug: str = "hyperliquid-ranking",
        cache_ttl: int = 3600
    ):
        super().__init__(cache_ttl)
        self.api_key = api_key
        self.challenge_slug = challenge_slug
        self.client = ChallengeClient(challenge_slug=challenge_slug, api_key=api_key)

    async def _fetch_predictions(self) -> pl.DataFrame:
        """Fetch predictions from CrowdCent API."""
        # Download meta model
        temp_path = f"/tmp/crowdcent_{self.challenge_slug}_{int(time.time())}.parquet"
        self.client.download_meta_model(temp_path)

        # Load and standardize
        df = pl.read_parquet(temp_path)
        df = df.rename({
            "release_date": "date",
            "id": "asset_id",
            "pred_10d": "prediction"
        })

        # Ensure date is datetime
        if df["date"].dtype != pl.Datetime:
            df = df.with_columns(pl.col("date").cast(pl.Date).cast(pl.Datetime))

        # Clean up temp file
        os.remove(temp_path)

        return df.select(["date", "asset_id", "prediction"]).drop_nulls()

    async def get_metadata(self) -> PredictionMetadata:
        df = await self.load_predictions()
        return PredictionMetadata(
            source="crowdcent",
            num_assets=df["asset_id"].n_unique(),
            date_range=(df["date"].min(), df["date"].max()),
            prediction_column="pred_10d",
            last_updated=datetime.utcnow()
        )

    @property
    def name(self) -> str:
        return "crowdcent"
```

### 4.3 Local File Data Source (`data_sources/local.py`)

```python
class LocalFileDataSource(DataSource):
    """Local parquet/CSV file data source."""

    def __init__(
        self,
        file_path: str,
        date_column: str = "date",
        asset_id_column: str = "asset_id",
        prediction_column: str = "prediction"
    ):
        self.file_path = file_path
        self.date_column = date_column
        self.asset_id_column = asset_id_column
        self.prediction_column = prediction_column

    async def load_predictions(self) -> pl.DataFrame:
        """Load from local file."""
        if self.file_path.endswith(".parquet"):
            df = pl.read_parquet(self.file_path)
        elif self.file_path.endswith(".csv"):
            df = pl.read_csv(self.file_path)
        else:
            raise ValueError(f"Unsupported file format: {self.file_path}")

        # Standardize columns
        df = df.rename({
            self.date_column: "date",
            self.asset_id_column: "asset_id",
            self.prediction_column: "prediction"
        })

        # Ensure date is datetime
        if df["date"].dtype != pl.Datetime:
            df = df.with_columns(pl.col("date").cast(pl.Date).cast(pl.Datetime))

        return df.select(["date", "asset_id", "prediction"]).drop_nulls()

    @property
    def name(self) -> str:
        return "local"
```

---

## 5. Trading Engine

### 5.1 Trading Orchestrator (`core/trader.py`)

The trader orchestrates the complete trading workflow:

```python
class TradingOrchestrator:
    """Main trading orchestrator."""

    def __init__(
        self,
        exchange: Exchange,
        data_source: DataSource,
        config: TradingConfig,
        state_manager: StateManager
    ):
        self.exchange = exchange
        self.data_source = data_source
        self.config = config
        self.state = state_manager

        self.portfolio_manager = PortfolioManager(config.portfolio)
        self.event_bus = EventBus()

    async def plan_rebalance(self, predictions: Optional[pl.DataFrame] = None) -> RebalancePlan:
        """Create rebalancing plan without execution.

        Workflow:
        1. Load current portfolio state
        2. Load predictions if not provided
        3. Filter tradeable assets
        4. Select top longs/shorts
        5. Calculate target weights
        6. Generate trades
        7. Apply filters (min notional, etc)
        8. Return plan
        """
        self.event_bus.emit("plan_started")

        # 1. Get current state
        portfolio = await self._get_current_portfolio()
        open_orders = await self.exchange.info.get_open_orders(self.config.owner_address)

        if open_orders:
            self.event_bus.emit("warning", f"Found {len(open_orders)} open orders")

        # 2. Load predictions
        if predictions is None:
            predictions = await self.data_source.load_predictions()
            self.event_bus.emit("predictions_loaded", predictions)

        # 3. Filter to tradeable assets
        metadata = await self.exchange.info.get_exchange_metadata()
        tradeable_symbols = self._get_tradeable_symbols(metadata)
        predictions = predictions.filter(pl.col("asset_id").is_in(tradeable_symbols))

        # 4. Select assets
        latest_preds = self._get_latest_predictions(predictions)
        long_assets, short_assets = self._select_assets(
            latest_preds,
            self.config.portfolio.num_long,
            self.config.portfolio.num_short
        )

        # 5. Calculate target weights
        target_positions = self.portfolio_manager.calculate_target_positions(
            predictions=latest_preds,
            long_assets=long_assets,
            short_assets=short_assets,
            account_value=portfolio.account.account_value,
            target_leverage=self.config.portfolio.target_leverage,
            rank_power=self.config.portfolio.rank_power
        )

        # 6. Generate trades
        current_prices = await self.exchange.info.get_market_prices()
        trades, skipped = await self._calculate_trades(
            target_positions=target_positions,
            current_positions=portfolio.positions,
            current_prices=current_prices
        )

        # 7. Create plan
        plan = RebalancePlan(
            account_value=portfolio.account.account_value,
            current_leverage=portfolio.account.current_leverage,
            target_leverage=self.config.portfolio.target_leverage,
            target_positions=[TargetPosition(**tp) for tp in target_positions],
            executable_trades=trades,
            skipped_trades=skipped,
            open_orders=open_orders
        )

        self.event_bus.emit("plan_created", plan)
        return plan

    async def execute_plan(self, plan: RebalancePlan) -> ExecutionResult:
        """Execute a rebalancing plan.

        Workflow:
        1. Sort trades for leverage reduction
        2. Submit orders (batch if supported)
        3. Track results
        4. Apply stop losses
        5. Return result
        """
        self.event_bus.emit("execution_started", plan)

        # 1. Sort trades
        sorted_trades = self._sort_trades_for_leverage_reduction(plan.executable_trades)

        # 2. Execute trades
        if self.exchange.supports_batch_orders:
            results = await self._execute_batch(sorted_trades)
        else:
            results = await self._execute_sequential(sorted_trades)

        successful = [r for r in results if r.is_successful]
        failed = [r for r in results if not r.is_successful]

        # 3. Apply stop losses
        stop_losses_applied = 0
        stop_losses_failed = 0

        if self.config.portfolio.stop_loss.sides != "none":
            sl_result = await self._apply_stop_losses()
            stop_losses_applied = sl_result["applied"]
            stop_losses_failed = sl_result["failed"]

        # 4. Create result
        result = ExecutionResult(
            plan=plan,
            successful_trades=successful,
            failed_trades=failed,
            stop_losses_applied=stop_losses_applied,
            stop_losses_failed=stop_losses_failed
        )

        self.event_bus.emit("execution_completed", result)
        return result

    async def _calculate_trades(
        self,
        target_positions: list[dict],
        current_positions: list[Position],
        current_prices: dict[str, Decimal]
    ) -> tuple[list[Trade], list[Trade]]:
        """Calculate required trades to reach target positions."""
        trades = []
        skipped = []

        # Convert current positions to dict
        current_dict = {p.coin: p for p in current_positions}
        target_dict = {t["coin"]: t["target_value"] for t in target_positions}

        all_coins = set(current_dict.keys()) | set(target_dict.keys())

        for coin in all_coins:
            current_value = Decimal(0)
            if coin in current_dict:
                pos = current_dict[coin]
                current_value = pos.signed_size * pos.mark_price

            target_value = target_dict.get(coin, Decimal(0))

            if coin not in current_prices:
                skipped.append(self._create_skipped_trade(
                    coin, target_value, "No market price available"
                ))
                continue

            price = current_prices[coin]
            delta_value = target_value - current_value

            if abs(delta_value) < self.config.execution.min_trade_value:
                skipped.append(self._create_skipped_trade(
                    coin, target_value, f"Below minimum ${self.config.execution.min_trade_value}"
                ))
                continue

            # Determine side and size
            is_buy = delta_value > 0
            size = self.exchange.round_size(coin, abs(delta_value) / price)

            if size == 0:
                skipped.append(self._create_skipped_trade(
                    coin, target_value, "Size rounds to zero"
                ))
                continue

            # Calculate limit price
            limit_price = self.exchange.calculate_limit_price(
                coin=coin,
                side=OrderSide.BUY if is_buy else OrderSide.SELL,
                reference_price=price,
                order_type=self.config.execution.order_type,
                slippage_tolerance=self.config.execution.slippage_tolerance,
                limit_offset=self.config.execution.limit_price_offset
            )

            # Classify trade type
            trade_type = self._classify_trade_type(current_value, target_value)

            # Estimate fee
            fee_rate = Decimal("0.00035")  # Default, should get from exchange
            estimated_fee = abs(delta_value) * fee_rate

            trade = Trade(
                coin=coin,
                side=OrderSide.BUY if is_buy else OrderSide.SELL,
                size=size,
                reference_price=price,
                limit_price=limit_price,
                current_value=current_value,
                target_value=target_value,
                delta_value=delta_value,
                trade_type=trade_type,
                estimated_fee=estimated_fee
            )

            trades.append(trade)

        return trades, skipped

    def _classify_trade_type(self, current_value: Decimal, target_value: Decimal) -> str:
        """Classify trade type."""
        if current_value == 0:
            return "open"
        if target_value == 0:
            return "close"

        same_sign = (current_value > 0 and target_value > 0) or (current_value < 0 and target_value < 0)

        if same_sign:
            return "reduce" if abs(target_value) < abs(current_value) else "increase"
        else:
            return "flip"

    def _sort_trades_for_leverage_reduction(self, trades: list[Trade]) -> list[Trade]:
        """Sort trades to reduce leverage first."""
        priority = {"close": 0, "reduce": 1, "flip": 1, "increase": 2, "open": 3}
        return sorted(trades, key=lambda t: priority.get(t.trade_type, 2))
```

---

## 6. Portfolio Management

### 6.1 Portfolio Manager (`core/portfolio.py`)

```python
class PortfolioManager:
    """Manages portfolio construction and weighting."""

    def __init__(self, config: PortfolioConfig):
        self.config = config

    def calculate_target_positions(
        self,
        predictions: pl.DataFrame,
        long_assets: list[str],
        short_assets: list[str],
        account_value: Decimal,
        target_leverage: Decimal,
        rank_power: Decimal = Decimal(0)
    ) -> list[dict]:
        """Calculate target positions with configurable weighting.

        Args:
            predictions: DataFrame with columns [asset_id, prediction]
            long_assets: List of assets to go long
            short_assets: List of assets to go short
            account_value: Current account value
            target_leverage: Target gross leverage
            rank_power: Rank power for weighting (0 = equal weight)

        Returns:
            List of dicts with keys: coin, target_value, weight
        """
        if rank_power == 0:
            return self._equal_weighted_positions(
                long_assets, short_assets, account_value, target_leverage
            )
        else:
            return self._rank_weighted_positions(
                predictions, long_assets, short_assets, account_value, target_leverage, rank_power
            )

    def _equal_weighted_positions(
        self,
        long_assets: list[str],
        short_assets: list[str],
        account_value: Decimal,
        target_leverage: Decimal
    ) -> list[dict]:
        """Calculate equal-weighted positions."""
        total_positions = len(long_assets) + len(short_assets)

        if total_positions == 0:
            return []

        # Split leverage between longs and shorts proportionally
        long_fraction = Decimal(len(long_assets)) / Decimal(total_positions)
        short_fraction = Decimal(len(short_assets)) / Decimal(total_positions)

        long_leverage = target_leverage * long_fraction
        short_leverage = target_leverage * short_fraction

        # Calculate per-position value
        long_position_value = (account_value * long_leverage) / Decimal(len(long_assets)) if long_assets else Decimal(0)
        short_position_value = (account_value * short_leverage) / Decimal(len(short_assets)) if short_assets else Decimal(0)

        positions = []

        for asset in long_assets:
            positions.append({
                "coin": asset,
                "target_value": long_position_value,
                "weight": long_position_value / account_value
            })

        for asset in short_assets:
            positions.append({
                "coin": asset,
                "target_value": -short_position_value,  # Negative for shorts
                "weight": -short_position_value / account_value
            })

        return positions

    def _rank_weighted_positions(
        self,
        predictions: pl.DataFrame,
        long_assets: list[str],
        short_assets: list[str],
        account_value: Decimal,
        target_leverage: Decimal,
        rank_power: Decimal
    ) -> list[dict]:
        """Calculate rank-power weighted positions.

        Uses formula: weight_i = (rank_i / n) ^ power
        Where rank is 1-indexed from best to worst
        """
        preds_dict = {
            row["asset_id"]: Decimal(str(row["prediction"]))
            for row in predictions.to_dicts()
        }

        total_positions = len(long_assets) + len(short_assets)
        long_fraction = Decimal(len(long_assets)) / Decimal(total_positions)
        short_fraction = Decimal(len(short_assets)) / Decimal(total_positions)

        long_leverage = target_leverage * long_fraction
        short_leverage = target_leverage * short_fraction

        positions = []

        # Calculate long weights
        if long_assets:
            long_weights = self._calculate_side_weights(
                assets=long_assets,
                predictions=preds_dict,
                gross_leverage=long_leverage,
                rank_power=rank_power,
                is_long=True
            )

            for asset, weight in long_weights.items():
                positions.append({
                    "coin": asset,
                    "target_value": weight * account_value,
                    "weight": weight
                })

        # Calculate short weights
        if short_assets:
            short_weights = self._calculate_side_weights(
                assets=short_assets,
                predictions=preds_dict,
                gross_leverage=short_leverage,
                rank_power=rank_power,
                is_long=False
            )

            for asset, weight in short_weights.items():
                positions.append({
                    "coin": asset,
                    "target_value": weight * account_value,
                    "weight": weight
                })

        return positions

    def _calculate_side_weights(
        self,
        assets: list[str],
        predictions: dict[str, Decimal],
        gross_leverage: Decimal,
        rank_power: Decimal,
        is_long: bool
    ) -> dict[str, Decimal]:
        """Calculate weights for one side (long or short)."""
        n = len(assets)

        # Sort by prediction (descending for longs, ascending for shorts)
        sorted_assets = sorted(
            [(predictions.get(a, Decimal(0)), a) for a in assets],
            reverse=is_long
        )

        # Calculate raw weights using rank power formula
        raw_weights = []
        for rank, (_, asset) in enumerate(sorted_assets, 1):
            # rank/n gives value between 1/n and 1
            # Raise to power to control concentration
            weight = (Decimal(rank) / Decimal(n)) ** rank_power
            raw_weights.append((asset, weight))

        # Normalize to sum to gross_leverage
        total_weight = sum(w for _, w in raw_weights)
        scale = gross_leverage / total_weight if total_weight > 0 else Decimal(1)

        # Return signed weights (negative for shorts)
        sign = Decimal(1) if is_long else Decimal(-1)
        return {
            asset: sign * weight * scale
            for asset, weight in raw_weights
        }
```

---

## 7. Backtesting Engine

### 7.1 Backtester (`core/backtester.py`)

The backtester is mostly unchanged but uses the new domain models:

```python
@dataclass
class BacktestConfig:
    """Backtesting configuration."""

    # Data paths
    prices_path: str = "raw_data.parquet"
    predictions_path: str = "predictions.parquet"

    # Column mappings
    price_date_column: str = "date"
    price_id_column: str = "id"
    price_close_column: str = "close"

    pred_date_column: str = "date"
    pred_id_column: str = "asset_id"
    pred_value_column: str = "prediction"

    # Date range
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Strategy parameters
    num_long: int = 60
    num_short: int = 50
    target_leverage: Decimal = Decimal("3.0")
    rank_power: Decimal = Decimal("0.0")

    # Rebalancing
    rebalance_every_n_days: int = 10
    prediction_lag_days: int = 1

    # Costs
    fee_bps: Decimal = Decimal("4.0")
    slippage_bps: Decimal = Decimal("50.0")

    # Initial capital
    start_capital: Decimal = Decimal("100000.0")

    # Options
    verbose: bool = False

class BacktestResult(BaseModel):
    """Backtesting results."""
    model_config = ConfigDict(frozen=False)

    # Time series data
    daily_df: pl.DataFrame  # Daily returns, equity, drawdown
    positions_df: pl.DataFrame  # Position snapshots

    # Summary statistics
    total_return: Decimal
    cagr: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    max_drawdown: Decimal
    calmar_ratio: Decimal
    annual_volatility: Decimal
    win_rate: Decimal
    avg_turnover: Decimal
    final_equity: Decimal

    # Config used
    config: BacktestConfig

class Backtester:
    """Backtesting engine."""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.portfolio_manager = PortfolioManager(None)  # Stateless

    async def run(self) -> BacktestResult:
        """Run backtest simulation."""
        # Load data
        prices = self._load_prices()
        predictions = self._load_predictions()

        # Compute returns matrix
        returns_wide = self._compute_returns(prices)

        # Determine trading dates
        valid_dates = self._get_valid_trading_dates(returns_wide, predictions)
        rebalance_dates = self._compute_rebalance_dates(valid_dates)

        # Run simulation
        daily_results, position_snapshots = await self._simulate(
            returns_wide=returns_wide,
            predictions=predictions,
            rebalance_dates=rebalance_dates
        )

        # Compute statistics
        stats = self._compute_statistics(daily_results)

        return BacktestResult(
            daily_df=daily_results,
            positions_df=position_snapshots,
            config=self.config,
            **stats
        )

    async def _simulate(
        self,
        returns_wide: pl.DataFrame,
        predictions: pl.DataFrame,
        rebalance_dates: list[datetime]
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Run the simulation loop."""
        equity = self.config.start_capital
        peak_equity = equity
        current_weights = {}

        daily_results = []
        position_snapshots = []

        rebalance_set = set(rebalance_dates)
        all_dates = returns_wide["date"].to_list()

        for date in all_dates:
            # Calculate portfolio return using old weights
            returns_row = returns_wide.filter(pl.col("date") == date)
            portfolio_return = Decimal(0)

            for asset, weight in current_weights.items():
                if asset in returns_row.columns:
                    asset_return = returns_row[asset][0]
                    if asset_return is not None:
                        portfolio_return += Decimal(str(weight)) * Decimal(str(asset_return))

            # Update equity
            equity *= (Decimal(1) + portfolio_return)

            # Track peak and drawdown
            peak_equity = max(peak_equity, equity)
            drawdown = (equity - peak_equity) / peak_equity if peak_equity > 0 else Decimal(0)

            # Rebalance if scheduled
            turnover = Decimal(0)
            if date in rebalance_set:
                new_weights = await self._rebalance(
                    date=date,
                    predictions=predictions,
                    returns_row=returns_row
                )

                # Calculate turnover
                all_assets = set(current_weights.keys()) | set(new_weights.keys())
                for asset in all_assets:
                    old_w = current_weights.get(asset, Decimal(0))
                    new_w = new_weights.get(asset, Decimal(0))
                    turnover += abs(new_w - old_w)

                # Apply costs
                cost_bps = self.config.fee_bps + self.config.slippage_bps
                cost = turnover * (cost_bps / Decimal("10000"))
                equity *= (Decimal(1) - cost)

                # Store position snapshot
                for asset, weight in new_weights.items():
                    position_snapshots.append({
                        "date": date,
                        "asset_id": asset,
                        "weight": float(weight)
                    })

                current_weights = new_weights

            # Store daily result
            daily_results.append({
                "date": date,
                "return": float(portfolio_return),
                "equity": float(equity),
                "drawdown": float(drawdown),
                "turnover": float(turnover)
            })

        return pl.DataFrame(daily_results), pl.DataFrame(position_snapshots)
```

---

## 8. Configuration System

### 8.1 Configuration Models (`domain/config.py`)

```python
class DataSourceConfig(BaseModel):
    """Data source configuration."""
    model_config = ConfigDict(frozen=False)

    source: Literal["crowdcent", "numerai", "local", "custom"]
    path: Optional[str] = "predictions.parquet"

    # CrowdCent config
    crowdcent_challenge: str = "hyperliquid-ranking"

    # Column mappings
    date_column: str = "date"
    asset_id_column: str = "asset_id"
    prediction_column: str = "prediction"

class StopLossConfig(BaseModel):
    """Stop loss configuration."""
    model_config = ConfigDict(frozen=False)

    sides: Literal["none", "both", "long_only", "short_only"] = "none"
    pct: Decimal = Decimal("0.17")  # 17% from entry
    slippage: Decimal = Decimal("0.05")  # 5% slippage tolerance

class RebalancingConfig(BaseModel):
    """Rebalancing schedule configuration."""
    model_config = ConfigDict(frozen=False)

    every_n_days: int = 10
    at_time: str = "18:15"  # UTC HH:MM

class PortfolioConfig(BaseModel):
    """Portfolio construction configuration."""
    model_config = ConfigDict(frozen=False)

    num_long: int = 10
    num_short: int = 10
    target_leverage: Decimal = Decimal("1.0")
    rank_power: Decimal = Decimal("0.0")

    stop_loss: StopLossConfig = Field(default_factory=StopLossConfig)
    rebalancing: RebalancingConfig = Field(default_factory=RebalancingConfig)

class ExecutionConfig(BaseModel):
    """Order execution configuration."""
    model_config = ConfigDict(frozen=False)

    slippage_tolerance: Decimal = Decimal("0.005")
    limit_price_offset: Decimal = Decimal("0.0")
    min_trade_value: Decimal = Decimal("10.0")
    order_type: OrderType = OrderType.MARKET
    time_in_force: TimeInForce = TimeInForce.IOC

class ExchangeProfile(BaseModel):
    """Exchange account profile."""
    model_config = ConfigDict(frozen=False)

    name: str
    exchange: str  # "hyperliquid", "binance", etc.
    owner_address: str
    vault_address: Optional[str] = None
    signer_env: str = "HYPERLIQUID_PRIVATE_KEY"
    is_testnet: bool = False

class TradingConfig(BaseModel):
    """Complete trading configuration."""
    model_config = ConfigDict(frozen=False)

    # Active profile
    active_profile: str = "default"
    profiles: dict[str, ExchangeProfile] = Field(default_factory=dict)

    # Components
    data_source: DataSourceConfig = Field(default_factory=DataSourceConfig)
    portfolio: PortfolioConfig = Field(default_factory=PortfolioConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)

    @property
    def current_profile(self) -> ExchangeProfile:
        """Get active profile."""
        if self.active_profile not in self.profiles:
            raise ValueError(f"Profile '{self.active_profile}' not found")
        return self.profiles[self.active_profile]

    @property
    def owner_address(self) -> str:
        """Get owner address from active profile."""
        return self.current_profile.owner_address

    @property
    def exchange_name(self) -> str:
        """Get exchange name from active profile."""
        return self.current_profile.exchange
```

### 8.2 Configuration Loader (`config/loader.py`)

```python
class ConfigLoader:
    """Load and validate configuration from YAML and env files."""

    DEFAULT_CONFIG_PATH = "cc-liquid-config.yaml"

    def __init__(self):
        self._load_env()

    def _load_env(self):
        """Load environment variables from .env file."""
        from dotenv import load_dotenv
        load_dotenv()

    def load_config(self, config_path: Optional[str] = None) -> TradingConfig:
        """Load complete configuration."""
        path = config_path or self.DEFAULT_CONFIG_PATH

        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            yaml_data = yaml.safe_load(f)

        # Parse into Pydantic model (validates automatically)
        config = TradingConfig.model_validate(yaml_data)

        # Validate secrets are present
        self._validate_secrets(config)

        return config

    def _validate_secrets(self, config: TradingConfig):
        """Ensure required secrets are in environment."""
        profile = config.current_profile

        # Check private key
        private_key = os.getenv(profile.signer_env)
        if not private_key:
            raise ValueError(
                f"Private key not found. Set {profile.signer_env} in .env file"
            )

        # Check data source API keys if needed
        if config.data_source.source == "crowdcent":
            api_key = os.getenv("CROWDCENT_API_KEY")
            if not api_key:
                raise ValueError("CROWDCENT_API_KEY not found in .env file")

    def apply_overrides(self, config: TradingConfig, overrides: dict[str, str]) -> TradingConfig:
        """Apply CLI overrides to configuration.

        Args:
            config: Base configuration
            overrides: Dict of overrides like {"portfolio.num_long": "15"}

        Returns:
            New config with overrides applied
        """
        config_dict = config.model_dump()

        for key, value in overrides.items():
            parts = key.split(".")
            current = config_dict

            # Navigate to nested dict
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set value with type conversion
            final_key = parts[-1]
            current[final_key] = self._convert_value(value)

        # Re-validate with Pydantic
        return TradingConfig.model_validate(config_dict)

    def _convert_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert string value to appropriate type."""
        # Try int
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Try bool
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        return value
```

---

## 9. Textualize TUI Specifications

### 9.1 Main App (`ui/app.py`)

```python
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer

class CCLiquidApp(App):
    """Main cc-liquid TUI application."""

    CSS_PATH = "styles/main.tcss"

    BINDINGS = [
        Binding("d", "show_dashboard", "Dashboard"),
        Binding("t", "show_trading", "Trading"),
        Binding("a", "show_account", "Account"),
        Binding("b", "show_backtest", "Backtest"),
        Binding("o", "show_optimize", "Optimize"),
        Binding("h", "show_history", "History"),
        Binding("c", "show_config", "Config"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        exchange: Exchange,
        data_source: DataSource,
        config: TradingConfig
    ):
        super().__init__()
        self.exchange = exchange
        self.data_source = data_source
        self.config = config

        # Core services
        self.state_manager = StateManager()
        self.trader = TradingOrchestrator(
            exchange=exchange,
            data_source=data_source,
            config=config,
            state_manager=self.state_manager
        )

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        """App mounted, show dashboard."""
        self.action_show_dashboard()

    def action_show_dashboard(self) -> None:
        """Show live dashboard screen."""
        from .screens.dashboard import DashboardScreen
        self.push_screen(DashboardScreen(self.trader, self.config))

    def action_show_trading(self) -> None:
        """Show trading/rebalancing screen."""
        from .screens.trading import TradingScreen
        self.push_screen(TradingScreen(self.trader, self.config))

    def action_show_account(self) -> None:
        """Show account info screen."""
        from .screens.account import AccountScreen
        self.push_screen(AccountScreen(self.exchange, self.config))

    def action_show_backtest(self) -> None:
        """Show backtesting screen."""
        from .screens.backtest import BacktestScreen
        self.push_screen(BacktestScreen(self.config))

    def action_show_optimize(self) -> None:
        """Show optimization screen."""
        from .screens.optimize import OptimizeScreen
        self.push_screen(OptimizeScreen(self.config))

    def action_show_history(self) -> None:
        """Show trade history screen."""
        from .screens.history import HistoryScreen
        self.push_screen(HistoryScreen(self.exchange, self.config))

    def action_show_config(self) -> None:
        """Show configuration screen."""
        from .screens.config import ConfigScreen
        self.push_screen(ConfigScreen(self.config))
```

### 9.2 Dashboard Screen (`ui/screens/dashboard.py`)

```python
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, DataTable, Label
from textual.reactive import reactive

class DashboardScreen(Screen):
    """Live monitoring dashboard with auto-refresh."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "pop_screen", "Back"),
    ]

    # Reactive properties
    portfolio = reactive(None)
    next_rebalance = reactive(None)

    def __init__(self, trader: TradingOrchestrator, config: TradingConfig):
        super().__init__()
        self.trader = trader
        self.config = config
        self.auto_refresh_interval = 1.0  # seconds

    def compose(self) -> ComposeResult:
        """Compose dashboard layout."""
        with Container(id="dashboard-container"):
            # Header with account summary
            with Vertical(id="account-summary"):
                yield Static("Account Summary", classes="section-title")
                yield Label(id="account-value")
                yield Label(id="total-exposure")
                yield Label(id="current-leverage")
                yield Label(id="unrealized-pnl")

            # Positions table
            with Vertical(id="positions-section"):
                yield Static("Positions", classes="section-title")
                yield DataTable(id="positions-table")

            # Next rebalance info
            with Vertical(id="rebalance-info"):
                yield Static("Next Rebalance", classes="section-title")
                yield Label(id="next-rebalance-time")
                yield Label(id="time-until-rebalance")

            # Open orders
            with Vertical(id="orders-section"):
                yield Static("Open Orders", classes="section-title")
                yield DataTable(id="orders-table")

    def on_mount(self) -> None:
        """Set up auto-refresh."""
        self.set_interval(self.auto_refresh_interval, self.action_refresh)
        self.action_refresh()

    async def action_refresh(self) -> None:
        """Refresh dashboard data."""
        # Fetch portfolio state
        self.portfolio = await self.trader.exchange.info.get_account_state(
            self.trader.config.owner_address
        )

        # Update UI
        self._update_account_summary()
        self._update_positions_table()
        self._update_orders_table()
        self._update_rebalance_info()

    def _update_account_summary(self) -> None:
        """Update account summary labels."""
        if not self.portfolio:
            return

        snapshot = self.trader.exchange.parse_account_state(self.portfolio)

        self.query_one("#account-value", Label).update(
            f"Account Value: ${snapshot.account.account_value:,.2f}"
        )
        self.query_one("#total-exposure", Label).update(
            f"Total Exposure: ${snapshot.account.total_position_value:,.2f}"
        )
        self.query_one("#current-leverage", Label).update(
            f"Leverage: {snapshot.account.current_leverage:.2f}x"
        )
        self.query_one("#unrealized-pnl", Label).update(
            f"Unrealized PNL: ${snapshot.total_unrealized_pnl:+,.2f}"
        )

    def _update_positions_table(self) -> None:
        """Update positions table."""
        if not self.portfolio:
            return

        snapshot = self.trader.exchange.parse_account_state(self.portfolio)
        table = self.query_one("#positions-table", DataTable)

        # Clear and set columns
        table.clear(columns=True)
        table.add_columns("Coin", "Side", "Size", "Entry", "Mark", "Value", "PNL", "Return %")

        # Add rows
        for pos in snapshot.positions:
            pnl_style = "green" if pos.unrealized_pnl > 0 else "red"
            table.add_row(
                pos.coin,
                pos.side,
                f"{pos.size:.4f}",
                f"${pos.entry_price:,.2f}",
                f"${pos.mark_price:,.2f}",
                f"${pos.value:,.2f}",
                f"${pos.unrealized_pnl:+,.2f}",
                f"{pos.return_pct:+.2f}%"
            )
```

### 9.3 Trading Screen (`ui/screens/trading.py`)

```python
class TradingScreen(Screen):
    """Trading/rebalancing screen with plan preview and execution."""

    BINDINGS = [
        ("p", "plan", "Plan Rebalance"),
        ("e", "execute", "Execute Plan"),
        ("escape", "pop_screen", "Back"),
    ]

    def __init__(self, trader: TradingOrchestrator, config: TradingConfig):
        super().__init__()
        self.trader = trader
        self.config = config
        self.current_plan: Optional[RebalancePlan] = None

    def compose(self) -> ComposeResult:
        """Compose trading screen."""
        with Container():
            # Control buttons
            with Horizontal(id="controls"):
                yield Button("Plan Rebalance", id="btn-plan", variant="primary")
                yield Button("Execute Plan", id="btn-execute", variant="success", disabled=True)

            # Plan preview
            with Vertical(id="plan-preview"):
                yield Static("Rebalance Plan", classes="section-title")
                yield Label(id="plan-summary")
                yield DataTable(id="trades-table")
                yield Label(id="skipped-summary")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "btn-plan":
            await self.action_plan()
        elif event.button.id == "btn-execute":
            await self.action_execute()

    async def action_plan(self) -> None:
        """Create rebalancing plan."""
        # Show loading spinner
        with self.app.batch_update():
            self.query_one("#plan-summary", Label).update("Planning rebalance...")

        # Create plan
        self.current_plan = await self.trader.plan_rebalance()

        # Update UI
        self._display_plan(self.current_plan)

        # Enable execute button
        self.query_one("#btn-execute", Button).disabled = False

    def _display_plan(self, plan: RebalancePlan) -> None:
        """Display rebalance plan in UI."""
        # Summary
        summary = (
            f"Account: ${plan.account_value:,.2f} | "
            f"Leverage: {plan.current_leverage:.2f}x → {plan.target_leverage:.2f}x | "
            f"Trades: {len(plan.executable_trades)} | "
            f"Total Volume: ${plan.total_trade_value:,.2f}"
        )
        self.query_one("#plan-summary", Label).update(summary)

        # Trades table
        table = self.query_one("#trades-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Coin", "Type", "Side", "Size", "Price", "Delta Value", "Fee")

        for trade in plan.executable_trades:
            table.add_row(
                trade.coin,
                trade.trade_type.upper(),
                trade.side.value.upper(),
                f"{trade.size:.4f}",
                f"${trade.limit_price or trade.reference_price:,.2f}",
                f"${trade.delta_value:+,.2f}",
                f"${trade.estimated_fee:.2f}"
            )

        # Skipped trades
        if plan.skipped_trades:
            skipped_text = f"⚠ {len(plan.skipped_trades)} trades skipped (below minimum or missing data)"
            self.query_one("#skipped-summary", Label).update(skipped_text)

    async def action_execute(self) -> None:
        """Execute the current plan."""
        if not self.current_plan:
            return

        # Confirm with modal
        def confirm_callback(confirmed: bool):
            if confirmed:
                self.app.call_later(self._execute_plan)

        self.app.push_screen(
            ConfirmationModal(
                f"Execute {len(self.current_plan.executable_trades)} trades?",
                callback=confirm_callback
            )
        )

    async def _execute_plan(self) -> None:
        """Actually execute the plan."""
        # Show progress
        with self.app.batch_update():
            self.query_one("#plan-summary", Label).update("Executing trades...")

        # Execute
        result = await self.trader.execute_plan(self.current_plan)

        # Show results modal
        self.app.push_screen(ExecutionResultModal(result))

        # Clear plan
        self.current_plan = None
        self.query_one("#btn-execute", Button).disabled = True
```

### 9.4 Account Screen (`ui/screens/account.py`)

```python
class AccountScreen(Screen):
    """Detailed account information screen."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Compose account screen."""
        with Container():
            # Account metrics
            with Vertical(id="account-metrics"):
                yield Static("Account Metrics", classes="section-title")
                yield MetricsPanel(id="metrics")

            # Detailed positions
            with Vertical(id="positions-detailed"):
                yield Static("Position Details", classes="section-title")
                yield PortfolioTable(id="portfolio-table")

            # Margin breakdown
            with Vertical(id="margin-breakdown"):
                yield Static("Margin Breakdown", classes="section-title")
                yield DataTable(id="margin-table")

    # Implementation...
```

### 9.5 Backtest Screen (`ui/screens/backtest.py`)

```python
class BacktestScreen(Screen):
    """Backtesting screen with parameter configuration."""

    BINDINGS = [
        ("r", "run_backtest", "Run"),
        ("escape", "pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Compose backtest screen."""
        with Container():
            # Left: Configuration
            with Vertical(id="backtest-config"):
                yield Static("Backtest Configuration", classes="section-title")
                yield Input(id="num-long", placeholder="Number of Longs")
                yield Input(id="num-short", placeholder="Number of Shorts")
                yield Input(id="leverage", placeholder="Target Leverage")
                yield Input(id="rebalance-days", placeholder="Rebalance Every N Days")
                yield Button("Run Backtest", id="btn-run", variant="primary")

            # Right: Results
            with Vertical(id="backtest-results"):
                yield Static("Results", classes="section-title")
                yield MetricsPanel(id="bt-metrics")
                yield DataTable(id="performance-table")
                yield ChartWidget(id="equity-chart")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle run button."""
        if event.button.id == "btn-run":
            await self.action_run_backtest()

    async def action_run_backtest(self) -> None:
        """Run backtest with current parameters."""
        # Parse inputs
        num_long = int(self.query_one("#num-long", Input).value or "10")
        num_short = int(self.query_one("#num-short", Input).value or "10")
        leverage = float(self.query_one("#leverage", Input).value or "1.0")
        rebalance_days = int(self.query_one("#rebalance-days", Input).value or "10")

        # Create config
        bt_config = BacktestConfig(
            num_long=num_long,
            num_short=num_short,
            target_leverage=Decimal(str(leverage)),
            rebalance_every_n_days=rebalance_days,
            # ... other params from main config
        )

        # Show progress
        self.query_one("#bt-metrics", MetricsPanel).update("Running backtest...")

        # Run backtest
        backtester = Backtester(bt_config)
        result = await backtester.run()

        # Display results
        self._display_results(result)

    def _display_results(self, result: BacktestResult) -> None:
        """Display backtest results."""
        # Update metrics panel
        metrics = {
            "Total Return": f"{result.total_return:.2%}",
            "CAGR": f"{result.cagr:.2%}",
            "Sharpe Ratio": f"{result.sharpe_ratio:.2f}",
            "Max Drawdown": f"{result.max_drawdown:.2%}",
            "Win Rate": f"{result.win_rate:.2%}"
        }
        self.query_one("#bt-metrics", MetricsPanel).update_metrics(metrics)

        # Update performance table
        table = self.query_one("#performance-table", DataTable)
        # ... populate table

        # Update equity chart
        chart = self.query_one("#equity-chart", ChartWidget)
        chart.plot_equity_curve(result.daily_df)
```

### 9.6 Widget Specifications

#### Portfolio Table Widget (`ui/widgets/portfolio_table.py`)

```python
from textual.widgets import DataTable

class PortfolioTable(DataTable):
    """Reusable portfolio positions table."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_type = "row"

    def update_positions(self, positions: list[Position]) -> None:
        """Update table with new positions."""
        self.clear(columns=True)
        self.add_columns(
            "Coin", "Side", "Size", "Entry", "Mark",
            "Value", "PNL", "Return %", "Liq. Price"
        )

        for pos in positions:
            pnl_color = "green" if pos.unrealized_pnl > 0 else "red"
            self.add_row(
                pos.coin,
                pos.side,
                f"{pos.size:.4f}",
                f"${pos.entry_price:,.2f}",
                f"${pos.mark_price:,.2f}",
                f"${pos.value:,.2f}",
                Text(f"${pos.unrealized_pnl:+,.2f}", style=pnl_color),
                f"{pos.return_pct:+.2f}%",
                f"${pos.liquidation_price:,.2f}" if pos.liquidation_price else "-"
            )
```

#### Metrics Panel Widget (`ui/widgets/metrics_panel.py`)

```python
from textual.containers import Grid
from textual.widgets import Static

class MetricsPanel(Grid):
    """Grid of key metrics."""

    DEFAULT_CSS = """
    MetricsPanel {
        grid-size: 2;
        grid-gutter: 1;
    }
    """

    def update_metrics(self, metrics: dict[str, str]) -> None:
        """Update metrics display."""
        self.remove_children()

        for label, value in metrics.items():
            self.mount(Static(f"{label}: {value}", classes="metric"))
```

#### Chart Widget (`ui/widgets/chart.py`)

```python
from textual.widgets import Static
import plotext as plt

class ChartWidget(Static):
    """ASCII chart widget using plotext."""

    def plot_equity_curve(self, daily_df: pl.DataFrame) -> None:
        """Plot equity curve."""
        plt.clf()

        dates = daily_df["date"].to_list()
        equity = daily_df["equity"].to_list()

        plt.plot(equity)
        plt.title("Equity Curve")
        plt.xlabel("Trading Days")
        plt.ylabel("Equity ($)")

        chart_str = plt.build()
        self.update(chart_str)
```

### 9.7 Stylesheet (`ui/styles/main.tcss`)

```css
/* Main App Styles */
Screen {
    background: $surface;
}

.section-title {
    text-style: bold;
    background: $primary;
    color: $text;
    padding: 1;
    margin-bottom: 1;
}

/* Dashboard Styles */
#dashboard-container {
    layout: grid;
    grid-size: 2 2;
    grid-gutter: 1;
}

#account-summary {
    background: $panel;
    border: solid $primary;
    padding: 1;
}

#positions-section {
    background: $panel;
    border: solid $primary;
    padding: 1;
}

#rebalance-info {
    background: $panel;
    border: solid $primary;
    padding: 1;
}

#orders-section {
    background: $panel;
    border: solid $primary;
    padding: 1;
}

/* Trading Screen */
#controls {
    dock: top;
    height: 3;
}

#plan-preview {
    border: solid $accent;
    padding: 1;
}

/* Color Scheme - Brutalist Theme */
$surface: #001926;
$panel: #002030;
$primary: #62e4fb;
$accent: #4152A8;
$text: #ffffff;
$success: #00ff00;
$warning: #ffaa00;
$error: #ff0000;
```

---

## 10. Testing Requirements

### 10.1 Unit Tests

#### Exchange Layer Tests (`tests/unit/test_exchanges/`)

```python
# test_hyperliquid.py
class TestHyperliquidExchange:
    """Tests for Hyperliquid exchange implementation."""

    @pytest.fixture
    def mock_info_client(self):
        return Mock(spec=HyperliquidInfo)

    @pytest.fixture
    def exchange(self, mock_info_client):
        config = {
            "base_url": "https://api.hyperliquid-testnet.xyz",
            "private_key": "0x1234...",
            "account_address": "0xabc...",
            "vault_address": None
        }
        exchange = HyperliquidExchange(config)
        exchange.info = mock_info_client
        return exchange

    async def test_parse_account_state(self, exchange):
        """Test parsing raw account state to domain model."""
        raw_data = {
            "marginSummary": {
                "accountValue": "100000.0",
                "totalNtlPos": "50000.0",
                "totalMarginUsed": "10000.0",
                "totalRawUsd": "90000.0"
            },
            "withdrawable": "80000.0",
            "assetPositions": [
                {
                    "position": {
                        "coin": "BTC",
                        "szi": "0.5",
                        "entryPx": "50000.0",
                        "liquidationPx": "45000.0",
                        "marginUsed": "5000.0"
                    }
                }
            ]
        }

        snapshot = exchange.parse_account_state(raw_data)

        assert snapshot.account.account_value == Decimal("100000.0")
        assert len(snapshot.positions) == 1
        assert snapshot.positions[0].coin == "BTC"
        assert snapshot.positions[0].side == "LONG"
        assert snapshot.positions[0].size == Decimal("0.5")

    async def test_round_size(self, exchange):
        """Test size rounding with szDecimals."""
        exchange._sz_decimals_cache = {"BTC": 4, "ETH": 3}

        btc_size = exchange.round_size("BTC", Decimal("0.123456"))
        assert btc_size == Decimal("0.1235")

        eth_size = exchange.round_size("ETH", Decimal("1.23456"))
        assert eth_size == Decimal("1.235")

    async def test_round_price_perp(self, exchange):
        """Test price rounding for perpetuals."""
        exchange._sz_decimals_cache = {"BTC": 4}

        # Price > 100k
        high_price = exchange.round_price("BTC", Decimal("150000.5"))
        assert high_price == Decimal("150001")

        # Price < 100k
        low_price = exchange.round_price("BTC", Decimal("50123.456789"))
        assert str(low_price) == "50123"  # 5 sig figs, max 2 decimals (6 - 4)
```

#### Data Source Tests (`tests/unit/test_data_sources/`)

```python
# test_local.py
class TestLocalFileDataSource:
    """Tests for local file data source."""

    @pytest.fixture
    def sample_parquet(self, tmp_path):
        """Create sample parquet file."""
        df = pl.DataFrame({
            "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
            "symbol": ["BTC", "ETH", "BTC"],
            "score": [0.6, 0.4, 0.7]
        })
        path = tmp_path / "predictions.parquet"
        df.write_parquet(path)
        return path

    async def test_load_predictions(self, sample_parquet):
        """Test loading predictions from parquet file."""
        source = LocalFileDataSource(
            file_path=str(sample_parquet),
            date_column="date",
            asset_id_column="symbol",
            prediction_column="score"
        )

        df = await source.load_predictions()

        assert "date" in df.columns
        assert "asset_id" in df.columns
        assert "prediction" in df.columns
        assert len(df) == 3
        assert df["asset_id"].to_list() == ["BTC", "ETH", "BTC"]

    async def test_validate_schema(self, sample_parquet):
        """Test schema validation."""
        source = LocalFileDataSource(file_path=str(sample_parquet))
        df = await source.load_predictions()

        assert await source.validate_schema(df) is True
```

#### Trading Engine Tests (`tests/unit/test_trader.py`)

```python
class TestTradingOrchestrator:
    """Tests for trading orchestrator."""

    @pytest.fixture
    def mock_exchange(self):
        return Mock(spec=Exchange)

    @pytest.fixture
    def mock_data_source(self):
        return Mock(spec=DataSource)

    @pytest.fixture
    def config(self):
        return TradingConfig(
            active_profile="test",
            profiles={
                "test": ExchangeProfile(
                    name="test",
                    exchange="mock",
                    owner_address="0xtest",
                    is_testnet=True
                )
            },
            portfolio=PortfolioConfig(
                num_long=5,
                num_short=5,
                target_leverage=Decimal("2.0")
            )
        )

    @pytest.fixture
    def trader(self, mock_exchange, mock_data_source, config):
        return TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=config,
            state_manager=StateManager()
        )

    async def test_plan_rebalance(self, trader, mock_exchange, mock_data_source):
        """Test creating rebalance plan."""
        # Mock predictions
        predictions = pl.DataFrame({
            "date": ["2024-01-01"] * 10,
            "asset_id": ["BTC", "ETH", "SOL", "AVAX", "MATIC", "LINK", "UNI", "AAVE", "CRV", "SNX"],
            "prediction": [0.9, 0.8, 0.7, 0.6, 0.5, 0.1, 0.2, 0.3, 0.4, 0.45]
        })
        mock_data_source.load_predictions.return_value = predictions

        # Mock exchange state
        mock_exchange.info.get_account_state.return_value = {
            "marginSummary": {"accountValue": "100000.0"},
            "assetPositions": []
        }
        mock_exchange.info.get_open_orders.return_value = []
        mock_exchange.info.get_exchange_metadata.return_value = {
            "universe": [{"name": coin, "szDecimals": 2} for coin in predictions["asset_id"].to_list()]
        }
        mock_exchange.info.get_market_prices.return_value = {
            coin: Decimal("1000") for coin in predictions["asset_id"].to_list()
        }

        # Create plan
        plan = await trader.plan_rebalance()

        # Assertions
        assert plan is not None
        assert plan.account_value == Decimal("100000.0")
        assert len(plan.target_positions) == 10
        assert len([p for p in plan.target_positions if p.target_value > 0]) == 5  # 5 longs
        assert len([p for p in plan.target_positions if p.target_value < 0]) == 5  # 5 shorts

    async def test_classify_trade_type(self, trader):
        """Test trade type classification."""
        assert trader._classify_trade_type(Decimal(0), Decimal(100)) == "open"
        assert trader._classify_trade_type(Decimal(100), Decimal(0)) == "close"
        assert trader._classify_trade_type(Decimal(100), Decimal(50)) == "reduce"
        assert trader._classify_trade_type(Decimal(50), Decimal(100)) == "increase"
        assert trader._classify_trade_type(Decimal(100), Decimal(-50)) == "flip"
```

### 10.2 Integration Tests

#### End-to-End Trading Flow (`tests/integration/test_trading_flow.py`)

```python
class TestTradingFlow:
    """Integration tests for complete trading workflow."""

    @pytest.fixture
    async def setup_system(self):
        """Set up complete system with mock exchange."""
        # Config
        config = TradingConfig(
            active_profile="test",
            profiles={
                "test": ExchangeProfile(
                    name="test",
                    exchange="mock",
                    owner_address="0xtest",
                    is_testnet=True
                )
            }
        )

        # Mock exchange
        exchange = MockExchange({
            "base_url": "mock://test",
            "private_key": "0xtest",
            "account_address": "0xtest"
        })

        # Mock data source
        predictions = pl.DataFrame({
            "date": ["2024-01-01"] * 10,
            "asset_id": [f"COIN{i}" for i in range(10)],
            "prediction": [0.9 - i*0.1 for i in range(10)]
        })
        data_source = MockDataSource(predictions)

        # Trader
        trader = TradingOrchestrator(
            exchange=exchange,
            data_source=data_source,
            config=config,
            state_manager=StateManager()
        )

        return trader, exchange

    async def test_full_rebalance_cycle(self, setup_system):
        """Test complete rebalance from plan to execution."""
        trader, exchange = setup_system

        # 1. Plan rebalance
        plan = await trader.plan_rebalance()
        assert plan is not None
        assert len(plan.executable_trades) > 0

        # 2. Execute plan
        result = await trader.execute_plan(plan)
        assert result is not None
        assert len(result.successful_trades) > 0

        # 3. Verify orders were submitted
        assert len(exchange.submitted_orders) == len(plan.executable_trades)

        # 4. Verify positions updated
        positions = await exchange.info.get_open_positions("0xtest")
        assert len(positions) > 0
```

### 10.3 Test Coverage Requirements

- **Minimum Coverage:** 80% overall
- **Critical Path Coverage:** 95% (trading execution, order submission, position calculation)
- **Edge Cases:** Must have explicit tests for:
  - Zero positions
  - Below minimum notional
  - Missing market data
  - API failures
  - Invalid configurations
  - Rounding edge cases
  - Leverage limits
  - Stop loss triggers

---

## 11. Migration Strategy

### 11.1 Migration Phases

**Phase 1: Core Infrastructure (Week 1-2)**
- Implement domain models (Pydantic v2)
- Create exchange abstraction layer
- Implement Hyperliquid adapter
- Create mock exchange for testing
- Set up test framework

**Phase 2: Business Logic (Week 3-4)**
- Port trading orchestrator
- Port portfolio manager
- Port backtester
- Implement data source abstraction
- Create CrowdCent/Numerai/Local adapters

**Phase 3: TUI Implementation (Week 5-6)**
- Set up Textualize app structure
- Implement dashboard screen
- Implement trading screen
- Implement account screen
- Create reusable widgets

**Phase 4: Additional Features (Week 7-8)**
- Implement backtest screen
- Implement optimize screen
- Implement history screen
- Implement configuration screen
- Add keyboard shortcuts and navigation

**Phase 5: Testing & Polish (Week 9-10)**
- Complete unit test coverage
- Integration testing
- User acceptance testing
- Performance optimization
- Documentation

### 11.2 Configuration Migration

Provide migration script to convert old config to new format:

```python
def migrate_config(old_config_path: str, new_config_path: str):
    """Migrate old YAML config to new format."""
    with open(old_config_path) as f:
        old_data = yaml.safe_load(f)

    new_data = {
        "active_profile": old_data.get("active_profile", "default"),
        "profiles": {},
        "data_source": {
            "source": old_data["data"]["source"],
            "path": old_data["data"]["path"],
            # ... map columns
        },
        "portfolio": {
            "num_long": old_data["portfolio"]["num_long"],
            # ... map all fields
        },
        "execution": {
            # ... map execution fields
        }
    }

    # Migrate profiles
    for profile_name, profile_data in old_data.get("profiles", {}).items():
        new_data["profiles"][profile_name] = {
            "name": profile_name,
            "exchange": "hyperliquid",  # Default
            "owner_address": profile_data.get("owner"),
            "vault_address": profile_data.get("vault"),
            "signer_env": profile_data.get("signer_env", "HYPERLIQUID_PRIVATE_KEY"),
            "is_testnet": old_data.get("is_testnet", False)
        }

    with open(new_config_path, "w") as f:
        yaml.safe_dump(new_data, f, sort_keys=False)
```

---

## 12. API Reference

### 12.1 Exchange API

```python
# Create exchange instance
exchange = HyperliquidExchange(config={
    "base_url": "https://api.hyperliquid.xyz",
    "private_key": os.getenv("HYPERLIQUID_PRIVATE_KEY"),
    "account_address": "0x...",
    "vault_address": None
})

# Query account state
account_data = await exchange.info.get_account_state("0x...")
portfolio = exchange.parse_account_state(account_data)

# Submit order
order = OrderRequest(
    coin="BTC",
    side=OrderSide.BUY,
    size=Decimal("0.1"),
    order_type=OrderType.LIMIT,
    limit_price=Decimal("50000"),
    time_in_force=TimeInForce.GTC
)
result = await exchange.trading.submit_order(order)

# Batch orders
results = await exchange.trading.submit_batch_orders([order1, order2, order3])
```

### 12.2 Data Source API

```python
# CrowdCent
crowdcent = CrowdCentDataSource(
    api_key=os.getenv("CROWDCENT_API_KEY"),
    challenge_slug="hyperliquid-ranking",
    cache_ttl=3600
)
predictions = await crowdcent.load_predictions()

# Numerai
numerai = NumeraiDataSource(cache_ttl=3600)
predictions = await numerai.load_predictions()

# Local file
local = LocalFileDataSource(
    file_path="predictions.parquet",
    date_column="date",
    asset_id_column="symbol",
    prediction_column="signal"
)
predictions = await local.load_predictions()
```

### 12.3 Trading API

```python
# Create trader
trader = TradingOrchestrator(
    exchange=exchange,
    data_source=data_source,
    config=config,
    state_manager=StateManager()
)

# Plan rebalance
plan = await trader.plan_rebalance()

# Execute plan
result = await trader.execute_plan(plan)

# Subscribe to events
def on_trade_complete(trade):
    print(f"Trade completed: {trade.coin}")

trader.event_bus.subscribe("trade_complete", on_trade_complete)
```

---

## 13. Edge Cases and Error Handling

### 13.1 Trading Edge Cases

**1. Below Minimum Notional**
```python
# When trade value < min_trade_value, mark as skipped
if abs(size * price) < config.execution.min_trade_value:
    skipped_trades.append(Trade(
        coin=coin,
        skipped=True,
        skip_reason=f"Below minimum ${config.execution.min_trade_value}"
    ))
```

**2. Size Rounding to Zero**
```python
# After rounding to szDecimals, size might become 0
rounded_size = exchange.round_size(coin, calculated_size)
if rounded_size == 0:
    skipped_trades.append(Trade(
        coin=coin,
        skipped=True,
        skip_reason="Size rounds to zero after applying precision"
    ))
```

**3. Missing Market Data**
```python
# Coin not in current_prices
if coin not in current_prices:
    skipped_trades.append(Trade(
        coin=coin,
        skipped=True,
        skip_reason="No market price available"
    ))
```

**4. Force Close Below Minimum**
```python
# When closing position < min notional, use two-step workaround:
# 1. Increase position to min notional
# 2. Close entire position
if target_value == 0 and abs(current_value) < min_trade_value:
    if force_close:
        trades.extend(compose_force_close_trades(coin, current_value, min_trade_value))
    else:
        skipped_trades.append(Trade(..., skip_reason="Force close required"))
```

### 13.2 API Error Handling

**1. Rate Limiting**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RateLimitError)
)
async def submit_order_with_retry(order: OrderRequest) -> OrderResult:
    return await exchange.trading.submit_order(order)
```

**2. Network Failures**
```python
try:
    result = await exchange.info.get_account_state(owner)
except NetworkError as e:
    logger.error(f"Network error: {e}")
    # Return cached state if available
    if cached_state:
        logger.warning("Using cached account state")
        return cached_state
    raise
```

**3. Invalid Responses**
```python
try:
    portfolio = exchange.parse_account_state(raw_data)
except ValidationError as e:
    logger.error(f"Invalid account state format: {e}")
    # Emit event for UI notification
    event_bus.emit("error", f"Failed to parse account state: {e}")
    return None
```

### 13.3 Configuration Edge Cases

**1. Missing Secrets**
```python
def validate_secrets(config: TradingConfig):
    profile = config.current_profile
    private_key = os.getenv(profile.signer_env)

    if not private_key:
        raise ConfigurationError(
            f"Private key not found. Set {profile.signer_env} in .env file.\n"
            f"Example: {profile.signer_env}=0x..."
        )
```

**2. Invalid Profile**
```python
if active_profile not in config.profiles:
    available = ", ".join(sorted(config.profiles.keys()))
    raise ConfigurationError(
        f"Profile '{active_profile}' not found.\n"
        f"Available profiles: {available}\n"
        f"Set active_profile in config YAML or use: cc-liquid profile use <name>"
    )
```

**3. Conflicting Parameters**
```python
# Validate leverage and position count
if config.portfolio.target_leverage > 10:
    logger.warning(
        f"High leverage detected: {config.portfolio.target_leverage}x. "
        f"Risk of liquidation is very high!"
    )

# Validate min trade value vs account size
total_positions = config.portfolio.num_long + config.portfolio.num_short
min_account_value = config.execution.min_trade_value * total_positions

if account_value < min_account_value:
    raise ValueError(
        f"Account value ${account_value} too small for {total_positions} positions "
        f"with min trade value ${config.execution.min_trade_value}. "
        f"Minimum account value: ${min_account_value}"
    )
```

### 13.4 Backtesting Edge Cases

**1. Missing Historical Data**
```python
# If prediction date doesn't align with price data
valid_dates = self._get_valid_trading_dates(returns_wide, predictions)

if len(valid_dates) == 0:
    raise ValueError(
        "No valid trading dates found. "
        "Ensure prediction dates align with price data and respect prediction lag. "
        f"Prediction date range: {predictions['date'].min()} to {predictions['date'].max()}\n"
        f"Price date range: {prices['date'].min()} to {prices['date'].max()}\n"
        f"Prediction lag: {config.prediction_lag_days} days"
    )
```

**2. Insufficient Asset Overlap**
```python
# Filter to tradeable assets
tradeable = predictions.filter(
    pl.col("asset_id").is_in(available_assets)
)

if tradeable.height == 0:
    raise ValueError(
        "No predictions match available assets. "
        f"Prediction assets: {sorted(predictions['asset_id'].unique().to_list()[:10])}...\n"
        f"Available assets: {sorted(list(available_assets)[:10])}..."
    )

if tradeable.height < config.num_long + config.num_short:
    logger.warning(
        f"Only {tradeable.height} tradeable assets available, "
        f"but {config.num_long + config.num_short} requested. "
        f"Some positions will be unfilled."
    )
```

**3. Negative Equity**
```python
# If equity goes negative (complete loss)
if equity <= 0:
    logger.error(f"Equity depleted on {date}. Simulation stopped.")
    # Return partial results
    return BacktestResult(
        daily_df=pl.DataFrame(daily_results[:i]),
        positions_df=pl.DataFrame(position_snapshots),
        config=config,
        **compute_partial_stats()
    )
```

---

## Appendix A: Complete Example Usage

### A.1 Full Application Setup

```python
# main.py
import asyncio
import os
from cc_liquid_tui.ui.app import CCLiquidApp
from cc_liquid_tui.exchanges.hyperliquid import HyperliquidExchange
from cc_liquid_tui.data_sources.crowdcent import CrowdCentDataSource
from cc_liquid_tui.config.loader import ConfigLoader

async def main():
    # Load configuration
    loader = ConfigLoader()
    config = loader.load_config("cc-liquid-config.yaml")

    # Create exchange instance
    profile = config.current_profile
    exchange = HyperliquidExchange({
        "base_url": "https://api.hyperliquid-testnet.xyz" if profile.is_testnet else "https://api.hyperliquid.xyz",
        "private_key": os.getenv(profile.signer_env),
        "account_address": profile.owner_address,
        "vault_address": profile.vault_address
    })

    # Create data source
    if config.data_source.source == "crowdcent":
        data_source = CrowdCentDataSource(
            api_key=os.getenv("CROWDCENT_API_KEY"),
            challenge_slug=config.data_source.crowdcent_challenge
        )
    elif config.data_source.source == "numerai":
        data_source = NumeraiDataSource()
    else:
        data_source = LocalFileDataSource(
            file_path=config.data_source.path,
            date_column=config.data_source.date_column,
            asset_id_column=config.data_source.asset_id_column,
            prediction_column=config.data_source.prediction_column
        )

    # Create and run TUI app
    app = CCLiquidApp(
        exchange=exchange,
        data_source=data_source,
        config=config
    )

    await app.run_async()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Appendix B: Testing Checklist

### B.1 Pre-Release Testing Checklist

- [ ] **Unit Tests**
  - [ ] All domain models validate correctly
  - [ ] Exchange adapters handle all response formats
  - [ ] Data sources load and normalize correctly
  - [ ] Portfolio calculations are accurate
  - [ ] Order generation is correct
  - [ ] Backtester produces consistent results

- [ ] **Integration Tests**
  - [ ] Full trading cycle (plan → execute → verify)
  - [ ] Configuration loading and validation
  - [ ] Multi-exchange support
  - [ ] Data source switching
  - [ ] Error recovery scenarios

- [ ] **UI Tests**
  - [ ] All screens render correctly
  - [ ] Navigation works as expected
  - [ ] Data updates in real-time
  - [ ] Keyboard shortcuts function
  - [ ] Modals and confirmations work

- [ ] **Edge Cases**
  - [ ] Zero positions handled
  - [ ] Below minimum notional handled
  - [ ] Missing data handled gracefully
  - [ ] API failures recover properly
  - [ ] Configuration errors clear

- [ ] **Performance**
  - [ ] Dashboard refresh < 1s
  - [ ] Backtesting completes in reasonable time
  - [ ] Optimization runs efficiently
  - [ ] No memory leaks

- [ ] **Security**
  - [ ] Private keys never logged
  - [ ] Secrets not in config files
  - [ ] API keys validated
  - [ ] Permission checks work

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-08 | Claude | Initial PRD creation |

---

**END OF PRD**
