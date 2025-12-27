"""Tests for TradingOrchestrator.

This module tests the core trading orchestration logic, following TDD principles.
Tests are organized by functionality and cover both success and failure scenarios.

Test Classes:
    TestTradingOrchestratorInit: Initialization tests
    TestGetCurrentPortfolio: Portfolio fetching tests
    TestPlanRebalanceSteps1to6: Plan creation tests (steps 1-6)
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import polars as pl
import pytest

from cc_flow.core.portfolio import PortfolioManager
from cc_flow.core.state import EventBus, StateManager
from cc_flow.core.trader import TradingOrchestrator
from cc_flow.data_sources.mock import MockDataSource
from cc_flow.domain.account import AccountInfo, PortfolioSnapshot, Position
from cc_flow.domain.config import (
    DataSourceConfig,
    ExchangeProfile,
    PortfolioConfig,
    TradingConfig,
)
from cc_flow.exchanges.mock import MockExchange


@pytest.fixture
def mock_exchange():
    """Create a mock exchange for testing.

    Returns:
        MockExchange with realistic test data
    """
    positions = [
        Position(
            coin="BTC",
            side="LONG",
            size=Decimal("1.0"),
            entry_price=Decimal("50000.0"),
            mark_price=Decimal("51000.0"),
            value=Decimal("51000.0"),
            unrealized_pnl=Decimal("1000.0"),
            return_pct=Decimal("0.02"),
        ),
        Position(
            coin="ETH",
            side="SHORT",
            size=Decimal("10.0"),
            entry_price=Decimal("3000.0"),
            mark_price=Decimal("2900.0"),
            value=Decimal("29000.0"),
            unrealized_pnl=Decimal("1000.0"),
            return_pct=Decimal("0.0333"),
        ),
    ]

    return MockExchange(
        account_value=Decimal("100000.0"),
        positions=positions,
        prices={
            "BTC": Decimal("51000.0"),
            "ETH": Decimal("2900.0"),
            "SOL": Decimal("100.0"),
            "AVAX": Decimal("40.0"),
            "MATIC": Decimal("1.5"),
        },
    )


@pytest.fixture
def mock_data_source():
    """Create a mock data source with test predictions.

    Returns:
        MockDataSource with 5 assets and predictions
    """
    # Create test predictions with different prediction values
    today = datetime.now(UTC).date()
    df = pl.DataFrame({
        "date": [today] * 5,
        "asset_id": ["BTC", "ETH", "SOL", "AVAX", "MATIC"],
        "prediction": [0.8, 0.6, -0.3, -0.5, 0.4],  # BTC, ETH, MATIC top longs; AVAX, SOL top shorts
    })

    return MockDataSource(predictions=df)


@pytest.fixture
def trading_config():
    """Create a trading configuration for testing.

    Returns:
        TradingConfig with test profile and settings
    """
    profile = ExchangeProfile(
        name="test",
        exchange="hyperliquid",
        owner_address="0x1234567890abcdef",
        vault_address=None,
        signer_env="TEST_PRIVATE_KEY",
        is_testnet=True,
    )

    return TradingConfig(
        active_profile="test",
        profiles={"test": profile},
        data_source=DataSourceConfig(source="local"),
        portfolio=PortfolioConfig(
            num_long=2,
            num_short=2,
            target_leverage=Decimal("1.0"),
            rank_power=Decimal("0.0"),  # Equal weighting
        ),
    )


class TestTradingOrchestratorInit:
    """Test TradingOrchestrator initialization."""

    def test_initialization_with_all_dependencies(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test initialization with all dependencies provided."""
        state_manager = StateManager()
        event_bus = EventBus()

        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
            state_manager=state_manager,
            event_bus=event_bus,
        )

        assert orchestrator.exchange is mock_exchange
        assert orchestrator.data_source is mock_data_source
        assert orchestrator.config is trading_config
        assert orchestrator.state_manager is state_manager
        assert orchestrator.event_bus is event_bus
        assert isinstance(orchestrator.portfolio_manager, PortfolioManager)
        assert orchestrator.portfolio_manager.config == trading_config.portfolio

    def test_initialization_with_default_state_manager(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test that default StateManager is created when not provided."""
        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
        )

        assert isinstance(orchestrator.state_manager, StateManager)
        assert orchestrator.state_manager is not None

    def test_initialization_with_default_event_bus(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test that default EventBus is created when not provided."""
        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
        )

        assert isinstance(orchestrator.event_bus, EventBus)
        assert orchestrator.event_bus is not None


class TestGetCurrentPortfolio:
    """Test _get_current_portfolio method."""

    @pytest.mark.asyncio
    async def test_fetching_account_state_from_exchange(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test that account state is fetched from exchange."""
        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
        )

        portfolio = await orchestrator._get_current_portfolio()

        assert isinstance(portfolio, PortfolioSnapshot)
        assert portfolio.account.account_value == Decimal("100000.0")

    @pytest.mark.asyncio
    async def test_parsing_to_portfolio_snapshot(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test that raw data is parsed to PortfolioSnapshot correctly."""
        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
        )

        portfolio = await orchestrator._get_current_portfolio()

        # Verify it's a valid PortfolioSnapshot with account info
        assert isinstance(portfolio, PortfolioSnapshot)
        assert isinstance(portfolio.account, AccountInfo)
        assert portfolio.account.account_value == Decimal("100000.0")
        assert len(portfolio.positions) == 2

    @pytest.mark.asyncio
    async def test_with_vault_address(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test fetching portfolio with vault address."""
        # Update config to use vault
        trading_config.profiles["test"].vault_address = "0xVAULTADDRESS"

        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
        )

        portfolio = await orchestrator._get_current_portfolio()

        # Should still work with vault address
        assert isinstance(portfolio, PortfolioSnapshot)
        assert portfolio.account.account_value == Decimal("100000.0")


class TestPlanRebalanceSteps1to6:
    """Test plan_rebalance method (steps 1-6 only)."""

    @pytest.mark.asyncio
    async def test_step1_get_current_portfolio(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test step 1: Get current portfolio state."""
        state_manager = StateManager()
        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
            state_manager=state_manager,
        )

        plan = await orchestrator.plan_rebalance()

        # Verify snapshot was added to state manager
        assert state_manager.get_latest_snapshot() is not None
        latest = state_manager.get_latest_snapshot()
        assert latest.account.account_value == Decimal("100000.0")

    @pytest.mark.asyncio
    async def test_step2_load_predictions(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test step 2: Load predictions from data source."""
        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
        )

        plan = await orchestrator.plan_rebalance()

        # Predictions should have been loaded (5 assets in our mock)
        # We can't directly verify this, but plan should be created successfully
        assert plan is not None

    @pytest.mark.asyncio
    async def test_step3_get_tradeable_symbols(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test step 3: Get tradeable symbols from exchange."""
        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
        )

        plan = await orchestrator.plan_rebalance()

        # All 5 assets in our mock exchange should be tradeable
        # The plan should include target positions
        assert plan is not None
        assert plan.account_value == Decimal("100000.0")

    @pytest.mark.asyncio
    async def test_step4_filter_to_tradeable_assets(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test step 4: Filter predictions to tradeable assets."""
        # Create a data source with some non-tradeable assets
        today = datetime.now(UTC).date()
        df = pl.DataFrame({
            "date": [today] * 7,
            "asset_id": ["BTC", "ETH", "SOL", "AVAX", "MATIC", "XYZ", "ABC"],
            "prediction": [0.8, 0.6, -0.3, -0.5, 0.4, 0.9, -0.7],
        })
        data_source = MockDataSource(predictions=df)

        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=data_source,
            config=trading_config,
        )

        plan = await orchestrator.plan_rebalance()

        # Plan should only include assets from our exchange (BTC, ETH, SOL, AVAX, MATIC)
        # XYZ and ABC should be filtered out
        assert plan is not None
        target_coins = {pos.coin for pos in plan.target_positions}
        assert "XYZ" not in target_coins
        assert "ABC" not in target_coins
        # Should only have tradeable assets
        assert all(coin in ["BTC", "ETH", "SOL", "AVAX", "MATIC"] for coin in target_coins)

    @pytest.mark.asyncio
    async def test_step5_calculate_target_positions(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test step 5: Calculate target positions."""
        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
        )

        plan = await orchestrator.plan_rebalance()

        # Should have 4 target positions (2 long + 2 short as per config)
        assert len(plan.target_positions) == 4

        # Verify positions are correctly identified
        # With predictions [BTC:0.8, ETH:0.6, MATIC:0.4, SOL:-0.3, AVAX:-0.5]
        # Longs should be: BTC, ETH
        # Shorts should be: AVAX, SOL
        long_positions = [p for p in plan.target_positions if p.side == "LONG"]
        short_positions = [p for p in plan.target_positions if p.side == "SHORT"]

        assert len(long_positions) == 2
        assert len(short_positions) == 2

        long_coins = {p.coin for p in long_positions}
        short_coins = {p.coin for p in short_positions}

        assert "BTC" in long_coins
        assert "ETH" in long_coins
        assert "AVAX" in short_coins
        assert "SOL" in short_coins

    @pytest.mark.asyncio
    async def test_step6_get_current_prices(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test step 6: Get current prices from exchange."""
        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
        )

        plan = await orchestrator.plan_rebalance()

        # Prices should have been fetched for target positions
        # We can verify indirectly by checking that plan was created
        assert plan is not None
        assert len(plan.target_positions) > 0

    @pytest.mark.asyncio
    async def test_event_emission(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test that plan_created event is emitted."""
        event_bus = EventBus()
        emitted_events = []

        def capture_event(data):
            emitted_events.append(data)

        event_bus.subscribe("plan_created", capture_event)

        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
            event_bus=event_bus,
        )

        plan = await orchestrator.plan_rebalance()

        # Verify event was emitted with the plan
        assert len(emitted_events) == 1
        assert emitted_events[0] is plan

    @pytest.mark.asyncio
    async def test_with_no_tradeable_assets_error(
        self, mock_exchange, trading_config
    ):
        """Test error when no tradeable assets are found."""
        # Create data source with only non-tradeable assets
        today = datetime.now(UTC).date()
        df = pl.DataFrame({
            "date": [today] * 2,
            "asset_id": ["XYZ", "ABC"],
            "prediction": [0.8, -0.5],
        })
        data_source = MockDataSource(predictions=df)

        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=data_source,
            config=trading_config,
        )

        # Should raise ValueError when no tradeable assets
        with pytest.raises(ValueError, match="No tradeable assets found"):
            await orchestrator.plan_rebalance()


class TestRebalancePlanProperties:
    """Test the RebalancePlan structure returned by plan_rebalance."""

    @pytest.mark.asyncio
    async def test_plan_has_correct_account_value(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test that plan contains correct account value."""
        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
        )

        plan = await orchestrator.plan_rebalance()

        assert plan.account_value == Decimal("100000.0")

    @pytest.mark.asyncio
    async def test_plan_has_correct_leverage_values(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test that plan contains correct leverage values."""
        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
        )

        plan = await orchestrator.plan_rebalance()

        # Current leverage from mock exchange
        assert plan.current_leverage == Decimal("0")
        # Target leverage from config
        assert plan.target_leverage == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_plan_executable_trades_empty_for_now(
        self, mock_exchange, mock_data_source, trading_config
    ):
        """Test that executable_trades is empty (will be implemented in next task)."""
        orchestrator = TradingOrchestrator(
            exchange=mock_exchange,
            data_source=mock_data_source,
            config=trading_config,
        )

        plan = await orchestrator.plan_rebalance()

        # Step 7 (trade calculation) is in next task, so should be empty for now
        assert plan.executable_trades == []
        assert plan.skipped_trades == []
