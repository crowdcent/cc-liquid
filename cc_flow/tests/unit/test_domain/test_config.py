"""
Unit tests for configuration domain models.

Tests for all configuration models following TDD principles with >90% coverage target.
Tests validate configuration structure, nested validation, and computed properties.
"""

from decimal import Decimal

import pytest

from cc_flow.domain.config import (
    DataSourceConfig,
    ExchangeProfile,
    ExecutionConfig,
    PortfolioConfig,
    RebalancingConfig,
    StopLossConfig,
    TradingConfig,
)
from cc_flow.domain.orders import OrderType, TimeInForce


class TestDataSourceConfig:
    """Test suite for DataSourceConfig model."""

    def test_valid_instantiation_crowdcent(self):
        """Test creating DataSourceConfig with crowdcent source."""
        config = DataSourceConfig(
            source="crowdcent",
            path="predictions.parquet",
            crowdcent_challenge="hyperliquid-ranking",
        )

        assert config.source == "crowdcent"
        assert config.path == "predictions.parquet"
        assert config.crowdcent_challenge == "hyperliquid-ranking"

    def test_valid_instantiation_numerai(self):
        """Test creating DataSourceConfig with numerai source."""
        config = DataSourceConfig(source="numerai")

        assert config.source == "numerai"

    def test_valid_instantiation_local(self):
        """Test creating DataSourceConfig with local source."""
        config = DataSourceConfig(
            source="local",
            path="/path/to/predictions.parquet",
        )

        assert config.source == "local"
        assert config.path == "/path/to/predictions.parquet"

    def test_valid_instantiation_custom(self):
        """Test creating DataSourceConfig with custom source."""
        config = DataSourceConfig(source="custom")

        assert config.source == "custom"

    def test_default_path(self):
        """Test default path is set correctly."""
        config = DataSourceConfig(source="local")

        assert config.path == "predictions.parquet"

    def test_custom_column_mappings(self):
        """Test custom column mappings."""
        config = DataSourceConfig(
            source="local",
            date_column="trade_date",
            asset_id_column="ticker",
            prediction_column="pred_score",
        )

        assert config.date_column == "trade_date"
        assert config.asset_id_column == "ticker"
        assert config.prediction_column == "pred_score"

    def test_default_column_mappings(self):
        """Test default column mappings."""
        config = DataSourceConfig(source="local")

        assert config.date_column == "date"
        assert config.asset_id_column == "asset_id"
        assert config.prediction_column == "prediction"

    def test_model_is_mutable(self):
        """Test that config is mutable (frozen=False)."""
        config = DataSourceConfig(source="local")

        config.source = "crowdcent"
        assert config.source == "crowdcent"

    def test_model_dump_serialization(self):
        """Test model_dump() returns proper dict."""
        config = DataSourceConfig(
            source="crowdcent",
            path="data.parquet",
        )

        data = config.model_dump()
        assert isinstance(data, dict)
        assert data["source"] == "crowdcent"
        assert data["path"] == "data.parquet"

    def test_model_dump_json_mode(self):
        """Test model_dump(mode='json') for JSON-compatible output."""
        config = DataSourceConfig(source="numerai")

        data = config.model_dump(mode="json")
        assert isinstance(data, dict)
        assert data["source"] == "numerai"

    def test_model_dump_json_returns_string(self):
        """Test model_dump_json() returns JSON string."""
        config = DataSourceConfig(source="local")

        json_str = config.model_dump_json()
        assert isinstance(json_str, str)
        assert "local" in json_str


class TestStopLossConfig:
    """Test suite for StopLossConfig model."""

    def test_default_instantiation(self):
        """Test creating StopLossConfig with default values."""
        config = StopLossConfig()

        assert config.sides == "none"
        assert config.pct == Decimal("0.17")
        assert config.slippage == Decimal("0.05")

    def test_sides_none(self):
        """Test sides='none' configuration."""
        config = StopLossConfig(sides="none")

        assert config.sides == "none"

    def test_sides_both(self):
        """Test sides='both' configuration."""
        config = StopLossConfig(sides="both")

        assert config.sides == "both"

    def test_sides_long_only(self):
        """Test sides='long_only' configuration."""
        config = StopLossConfig(sides="long_only")

        assert config.sides == "long_only"

    def test_sides_short_only(self):
        """Test sides='short_only' configuration."""
        config = StopLossConfig(sides="short_only")

        assert config.sides == "short_only"

    def test_custom_pct(self):
        """Test custom stop loss percentage."""
        config = StopLossConfig(pct=Decimal("0.25"))

        assert config.pct == Decimal("0.25")

    def test_custom_slippage(self):
        """Test custom slippage tolerance."""
        config = StopLossConfig(slippage=Decimal("0.10"))

        assert config.slippage == Decimal("0.10")

    def test_decimal_precision_preserved(self):
        """Test that Decimal precision is preserved."""
        config = StopLossConfig(
            pct=Decimal("0.123456789"),
            slippage=Decimal("0.0555555"),
        )

        assert config.pct == Decimal("0.123456789")
        assert config.slippage == Decimal("0.0555555")

    def test_model_is_mutable(self):
        """Test that config is mutable (frozen=False)."""
        config = StopLossConfig()

        config.sides = "both"
        assert config.sides == "both"

    def test_model_dump_serialization(self):
        """Test model_dump() returns proper dict."""
        config = StopLossConfig(sides="both", pct=Decimal("0.20"))

        data = config.model_dump()
        assert isinstance(data, dict)
        assert data["sides"] == "both"
        assert data["pct"] == Decimal("0.20")

    def test_model_dump_json_mode(self):
        """Test model_dump(mode='json') for JSON-compatible output."""
        config = StopLossConfig()

        data = config.model_dump(mode="json")
        assert isinstance(data, dict)
        # Decimals should be converted to strings or floats in JSON mode
        assert isinstance(data["pct"], (str, float))


class TestRebalancingConfig:
    """Test suite for RebalancingConfig model."""

    def test_default_instantiation(self):
        """Test creating RebalancingConfig with default values."""
        config = RebalancingConfig()

        assert config.every_n_days == 10
        assert config.at_time == "18:15"

    def test_custom_days(self):
        """Test custom rebalancing frequency."""
        config = RebalancingConfig(every_n_days=7)

        assert config.every_n_days == 7

    def test_custom_time(self):
        """Test custom rebalancing time."""
        config = RebalancingConfig(at_time="12:00")

        assert config.at_time == "12:00"

    def test_time_format_hh_mm(self):
        """Test time format is HH:MM."""
        config = RebalancingConfig(at_time="09:30")

        assert config.at_time == "09:30"
        assert len(config.at_time) == 5
        assert config.at_time[2] == ":"

    def test_model_is_mutable(self):
        """Test that config is mutable (frozen=False)."""
        config = RebalancingConfig()

        config.every_n_days = 5
        assert config.every_n_days == 5

    def test_model_dump_serialization(self):
        """Test model_dump() returns proper dict."""
        config = RebalancingConfig(every_n_days=14, at_time="15:30")

        data = config.model_dump()
        assert isinstance(data, dict)
        assert data["every_n_days"] == 14
        assert data["at_time"] == "15:30"


class TestPortfolioConfig:
    """Test suite for PortfolioConfig model."""

    def test_default_instantiation(self):
        """Test creating PortfolioConfig with default values."""
        config = PortfolioConfig()

        assert config.num_long == 10
        assert config.num_short == 10
        assert config.target_leverage == Decimal("1.0")
        assert config.rank_power == Decimal("0.0")
        assert isinstance(config.stop_loss, StopLossConfig)
        assert isinstance(config.rebalancing, RebalancingConfig)

    def test_custom_num_long_and_short(self):
        """Test custom number of long and short positions."""
        config = PortfolioConfig(num_long=15, num_short=5)

        assert config.num_long == 15
        assert config.num_short == 5

    def test_custom_target_leverage(self):
        """Test custom target leverage."""
        config = PortfolioConfig(target_leverage=Decimal("2.0"))

        assert config.target_leverage == Decimal("2.0")

    def test_custom_rank_power(self):
        """Test custom rank power."""
        config = PortfolioConfig(rank_power=Decimal("0.5"))

        assert config.rank_power == Decimal("0.5")

    def test_with_custom_stop_loss(self):
        """Test with custom StopLossConfig."""
        stop_loss = StopLossConfig(sides="both", pct=Decimal("0.20"))
        config = PortfolioConfig(stop_loss=stop_loss)

        assert config.stop_loss.sides == "both"
        assert config.stop_loss.pct == Decimal("0.20")

    def test_with_custom_rebalancing(self):
        """Test with custom RebalancingConfig."""
        rebalancing = RebalancingConfig(every_n_days=7, at_time="12:00")
        config = PortfolioConfig(rebalancing=rebalancing)

        assert config.rebalancing.every_n_days == 7
        assert config.rebalancing.at_time == "12:00"

    def test_nested_default_factory(self):
        """Test that nested configs use default_factory correctly."""
        config1 = PortfolioConfig()
        config2 = PortfolioConfig()

        # Should be different instances
        assert config1.stop_loss is not config2.stop_loss
        assert config1.rebalancing is not config2.rebalancing

    def test_decimal_precision_preserved(self):
        """Test that Decimal precision is preserved."""
        config = PortfolioConfig(
            target_leverage=Decimal("1.123456"),
            rank_power=Decimal("0.987654"),
        )

        assert config.target_leverage == Decimal("1.123456")
        assert config.rank_power == Decimal("0.987654")

    def test_model_is_mutable(self):
        """Test that config is mutable (frozen=False)."""
        config = PortfolioConfig()

        config.num_long = 20
        assert config.num_long == 20

    def test_model_dump_with_nested_models(self):
        """Test model_dump() with nested models."""
        config = PortfolioConfig()

        data = config.model_dump()
        assert isinstance(data, dict)
        assert isinstance(data["stop_loss"], dict)
        assert isinstance(data["rebalancing"], dict)
        assert data["stop_loss"]["sides"] == "none"
        assert data["rebalancing"]["every_n_days"] == 10


class TestExecutionConfig:
    """Test suite for ExecutionConfig model."""

    def test_default_instantiation(self):
        """Test creating ExecutionConfig with default values."""
        config = ExecutionConfig()

        assert config.slippage_tolerance == Decimal("0.005")
        assert config.limit_price_offset == Decimal("0.0")
        assert config.min_trade_value == Decimal("10.0")
        assert config.order_type == OrderType.MARKET
        assert config.time_in_force == TimeInForce.IOC

    def test_custom_slippage_tolerance(self):
        """Test custom slippage tolerance."""
        config = ExecutionConfig(slippage_tolerance=Decimal("0.01"))

        assert config.slippage_tolerance == Decimal("0.01")

    def test_custom_limit_price_offset(self):
        """Test custom limit price offset."""
        config = ExecutionConfig(limit_price_offset=Decimal("0.001"))

        assert config.limit_price_offset == Decimal("0.001")

    def test_custom_min_trade_value(self):
        """Test custom minimum trade value."""
        config = ExecutionConfig(min_trade_value=Decimal("25.0"))

        assert config.min_trade_value == Decimal("25.0")

    def test_with_limit_order_type(self):
        """Test with LIMIT order type."""
        config = ExecutionConfig(order_type=OrderType.LIMIT)

        assert config.order_type == OrderType.LIMIT

    def test_with_gtc_time_in_force(self):
        """Test with GTC time in force."""
        config = ExecutionConfig(time_in_force=TimeInForce.GTC)

        assert config.time_in_force == TimeInForce.GTC

    def test_with_alo_time_in_force(self):
        """Test with ALO time in force."""
        config = ExecutionConfig(time_in_force=TimeInForce.ALO)

        assert config.time_in_force == TimeInForce.ALO

    def test_decimal_precision_preserved(self):
        """Test that Decimal precision is preserved."""
        config = ExecutionConfig(
            slippage_tolerance=Decimal("0.00555555"),
            limit_price_offset=Decimal("0.00111111"),
            min_trade_value=Decimal("10.123456"),
        )

        assert config.slippage_tolerance == Decimal("0.00555555")
        assert config.limit_price_offset == Decimal("0.00111111")
        assert config.min_trade_value == Decimal("10.123456")

    def test_model_is_mutable(self):
        """Test that config is mutable (frozen=False)."""
        config = ExecutionConfig()

        config.min_trade_value = Decimal("50.0")
        assert config.min_trade_value == Decimal("50.0")

    def test_model_dump_serialization(self):
        """Test model_dump() returns proper dict."""
        config = ExecutionConfig(
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.GTC,
        )

        data = config.model_dump()
        assert isinstance(data, dict)
        assert data["order_type"] == OrderType.LIMIT
        assert data["time_in_force"] == TimeInForce.GTC

    def test_model_dump_json_mode(self):
        """Test model_dump(mode='json') for JSON-compatible output."""
        config = ExecutionConfig()

        data = config.model_dump(mode="json")
        assert isinstance(data, dict)
        # Decimals should be converted to strings or floats in JSON mode
        assert isinstance(data["slippage_tolerance"], (str, float))


class TestExchangeProfile:
    """Test suite for ExchangeProfile model."""

    def test_valid_instantiation_minimal(self):
        """Test creating ExchangeProfile with minimal required fields."""
        profile = ExchangeProfile(
            name="default",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
        )

        assert profile.name == "default"
        assert profile.exchange == "hyperliquid"
        assert profile.owner_address == "0x1234567890abcdef"
        assert profile.vault_address is None
        assert profile.signer_env == "HYPERLIQUID_PRIVATE_KEY"
        assert profile.is_testnet is False

    def test_with_vault_address(self):
        """Test ExchangeProfile with vault address."""
        profile = ExchangeProfile(
            name="vault",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
            vault_address="0xabcdef1234567890",
        )

        assert profile.vault_address == "0xabcdef1234567890"

    def test_testnet_profile(self):
        """Test testnet profile configuration."""
        profile = ExchangeProfile(
            name="testnet",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
            is_testnet=True,
        )

        assert profile.is_testnet is True

    def test_mainnet_profile(self):
        """Test mainnet profile configuration."""
        profile = ExchangeProfile(
            name="mainnet",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
            is_testnet=False,
        )

        assert profile.is_testnet is False

    def test_custom_signer_env(self):
        """Test custom signer environment variable."""
        profile = ExchangeProfile(
            name="custom",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
            signer_env="MY_CUSTOM_PRIVATE_KEY",
        )

        assert profile.signer_env == "MY_CUSTOM_PRIVATE_KEY"

    def test_different_exchange(self):
        """Test with different exchange name."""
        profile = ExchangeProfile(
            name="binance",
            exchange="binance",
            owner_address="0x1234567890abcdef",
        )

        assert profile.exchange == "binance"

    def test_model_is_mutable(self):
        """Test that profile is mutable (frozen=False)."""
        profile = ExchangeProfile(
            name="default",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
        )

        profile.is_testnet = True
        assert profile.is_testnet is True

    def test_model_dump_serialization(self):
        """Test model_dump() returns proper dict."""
        profile = ExchangeProfile(
            name="default",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
            vault_address="0xabcdef1234567890",
        )

        data = profile.model_dump()
        assert isinstance(data, dict)
        assert data["name"] == "default"
        assert data["exchange"] == "hyperliquid"
        assert data["vault_address"] == "0xabcdef1234567890"


class TestTradingConfig:
    """Test suite for TradingConfig model."""

    def test_default_instantiation(self):
        """Test creating TradingConfig with default values."""
        config = TradingConfig()

        assert config.active_profile == "default"
        assert isinstance(config.profiles, dict)
        assert len(config.profiles) == 0
        assert isinstance(config.data_source, DataSourceConfig)
        assert isinstance(config.portfolio, PortfolioConfig)
        assert isinstance(config.execution, ExecutionConfig)

    def test_with_single_profile(self):
        """Test TradingConfig with single profile."""
        profile = ExchangeProfile(
            name="default",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
        )
        config = TradingConfig(
            active_profile="default",
            profiles={"default": profile},
        )

        assert config.active_profile == "default"
        assert "default" in config.profiles
        assert config.profiles["default"] == profile

    def test_with_multiple_profiles(self):
        """Test TradingConfig with multiple profiles."""
        profile1 = ExchangeProfile(
            name="mainnet",
            exchange="hyperliquid",
            owner_address="0x1111111111111111",
        )
        profile2 = ExchangeProfile(
            name="testnet",
            exchange="hyperliquid",
            owner_address="0x2222222222222222",
            is_testnet=True,
        )
        config = TradingConfig(
            active_profile="mainnet",
            profiles={"mainnet": profile1, "testnet": profile2},
        )

        assert config.active_profile == "mainnet"
        assert len(config.profiles) == 2
        assert "mainnet" in config.profiles
        assert "testnet" in config.profiles

    def test_current_profile_property_valid(self):
        """Test current_profile property returns active profile."""
        profile = ExchangeProfile(
            name="default",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
        )
        config = TradingConfig(
            active_profile="default",
            profiles={"default": profile},
        )

        current = config.current_profile
        assert current == profile
        assert current.name == "default"

    def test_current_profile_property_raises_on_missing(self):
        """Test current_profile raises ValueError when profile not found."""
        config = TradingConfig(
            active_profile="nonexistent",
            profiles={},
        )

        with pytest.raises(ValueError) as exc_info:
            _ = config.current_profile

        assert "Profile 'nonexistent' not found" in str(exc_info.value)

    def test_owner_address_property(self):
        """Test owner_address property returns owner from active profile."""
        profile = ExchangeProfile(
            name="default",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
        )
        config = TradingConfig(
            active_profile="default",
            profiles={"default": profile},
        )

        assert config.owner_address == "0x1234567890abcdef"

    def test_exchange_name_property(self):
        """Test exchange_name property returns exchange from active profile."""
        profile = ExchangeProfile(
            name="default",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
        )
        config = TradingConfig(
            active_profile="default",
            profiles={"default": profile},
        )

        assert config.exchange_name == "hyperliquid"

    def test_active_profile_switching(self):
        """Test switching active profile."""
        profile1 = ExchangeProfile(
            name="mainnet",
            exchange="hyperliquid",
            owner_address="0x1111111111111111",
        )
        profile2 = ExchangeProfile(
            name="testnet",
            exchange="hyperliquid",
            owner_address="0x2222222222222222",
            is_testnet=True,
        )
        config = TradingConfig(
            active_profile="mainnet",
            profiles={"mainnet": profile1, "testnet": profile2},
        )

        assert config.owner_address == "0x1111111111111111"

        # Switch profile
        config.active_profile = "testnet"
        assert config.owner_address == "0x2222222222222222"

    def test_with_custom_data_source(self):
        """Test TradingConfig with custom DataSourceConfig."""
        data_source = DataSourceConfig(
            source="crowdcent",
            crowdcent_challenge="custom-challenge",
        )
        config = TradingConfig(data_source=data_source)

        assert config.data_source.source == "crowdcent"
        assert config.data_source.crowdcent_challenge == "custom-challenge"

    def test_with_custom_portfolio(self):
        """Test TradingConfig with custom PortfolioConfig."""
        portfolio = PortfolioConfig(
            num_long=20,
            num_short=5,
            target_leverage=Decimal("2.0"),
        )
        config = TradingConfig(portfolio=portfolio)

        assert config.portfolio.num_long == 20
        assert config.portfolio.num_short == 5
        assert config.portfolio.target_leverage == Decimal("2.0")

    def test_with_custom_execution(self):
        """Test TradingConfig with custom ExecutionConfig."""
        execution = ExecutionConfig(
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.GTC,
            min_trade_value=Decimal("50.0"),
        )
        config = TradingConfig(execution=execution)

        assert config.execution.order_type == OrderType.LIMIT
        assert config.execution.time_in_force == TimeInForce.GTC
        assert config.execution.min_trade_value == Decimal("50.0")

    def test_nested_config_default_factories(self):
        """Test that nested configs use default_factory correctly."""
        config1 = TradingConfig()
        config2 = TradingConfig()

        # Should be different instances
        assert config1.data_source is not config2.data_source
        assert config1.portfolio is not config2.portfolio
        assert config1.execution is not config2.execution
        assert config1.profiles is not config2.profiles

    def test_model_is_mutable(self):
        """Test that config is mutable (frozen=False)."""
        config = TradingConfig()

        config.active_profile = "new_profile"
        assert config.active_profile == "new_profile"

    def test_complete_config_serialization(self):
        """Test complete config serialization with all nested models."""
        profile = ExchangeProfile(
            name="default",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
        )
        config = TradingConfig(
            active_profile="default",
            profiles={"default": profile},
        )

        data = config.model_dump()
        assert isinstance(data, dict)
        assert "active_profile" in data
        assert "profiles" in data
        assert "data_source" in data
        assert "portfolio" in data
        assert "execution" in data
        assert isinstance(data["profiles"], dict)
        assert isinstance(data["data_source"], dict)
        assert isinstance(data["portfolio"], dict)
        assert isinstance(data["execution"], dict)

    def test_model_dump_json_mode(self):
        """Test model_dump(mode='json') for JSON-compatible output."""
        profile = ExchangeProfile(
            name="default",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
        )
        config = TradingConfig(
            active_profile="default",
            profiles={"default": profile},
        )

        data = config.model_dump(mode="json")
        assert isinstance(data, dict)
        # Nested models should also be serialized
        assert isinstance(data["portfolio"], dict)

    def test_model_dump_json_returns_string(self):
        """Test model_dump_json() returns JSON string."""
        profile = ExchangeProfile(
            name="default",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
        )
        config = TradingConfig(
            active_profile="default",
            profiles={"default": profile},
        )

        json_str = config.model_dump_json()
        assert isinstance(json_str, str)
        assert "default" in json_str
        assert "hyperliquid" in json_str

    def test_empty_profiles_accessing_properties(self):
        """Test that accessing properties with empty profiles raises error."""
        config = TradingConfig(
            active_profile="default",
            profiles={},
        )

        with pytest.raises(ValueError):
            _ = config.current_profile

        with pytest.raises(ValueError):
            _ = config.owner_address

        with pytest.raises(ValueError):
            _ = config.exchange_name

    def test_very_complex_nested_config(self):
        """Test complete config with all nested customizations."""
        profile = ExchangeProfile(
            name="mainnet",
            exchange="hyperliquid",
            owner_address="0x1234567890abcdef",
            vault_address="0xabcdef1234567890",
            signer_env="MY_PRIVATE_KEY",
            is_testnet=False,
        )

        data_source = DataSourceConfig(
            source="crowdcent",
            path="custom.parquet",
            crowdcent_challenge="custom-challenge",
            date_column="trade_date",
            asset_id_column="ticker",
            prediction_column="pred",
        )

        stop_loss = StopLossConfig(
            sides="both",
            pct=Decimal("0.25"),
            slippage=Decimal("0.10"),
        )

        rebalancing = RebalancingConfig(
            every_n_days=7,
            at_time="12:00",
        )

        portfolio = PortfolioConfig(
            num_long=15,
            num_short=5,
            target_leverage=Decimal("2.5"),
            rank_power=Decimal("0.8"),
            stop_loss=stop_loss,
            rebalancing=rebalancing,
        )

        execution = ExecutionConfig(
            slippage_tolerance=Decimal("0.01"),
            limit_price_offset=Decimal("0.002"),
            min_trade_value=Decimal("25.0"),
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.GTC,
        )

        config = TradingConfig(
            active_profile="mainnet",
            profiles={"mainnet": profile},
            data_source=data_source,
            portfolio=portfolio,
            execution=execution,
        )

        # Verify all nested configs
        assert config.active_profile == "mainnet"
        assert config.current_profile.name == "mainnet"
        assert config.owner_address == "0x1234567890abcdef"
        assert config.exchange_name == "hyperliquid"
        assert config.data_source.source == "crowdcent"
        assert config.portfolio.num_long == 15
        assert config.portfolio.stop_loss.sides == "both"
        assert config.portfolio.rebalancing.every_n_days == 7
        assert config.execution.order_type == OrderType.LIMIT

        # Verify serialization works
        data = config.model_dump()
        assert isinstance(data, dict)
        assert data["portfolio"]["stop_loss"]["sides"] == "both"
        assert data["portfolio"]["rebalancing"]["every_n_days"] == 7
