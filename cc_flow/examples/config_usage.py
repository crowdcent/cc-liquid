"""
Example usage of configuration domain models.

This script demonstrates how to create and use configuration models
for the cc-flow trading system.
"""

from decimal import Decimal

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


def example_simple_config():
    """Create a simple trading configuration with default settings."""
    print("\n=== Simple Configuration ===")

    # Create exchange profile
    profile = ExchangeProfile(
        name="mainnet",
        exchange="hyperliquid",
        owner_address="0x1234567890abcdef1234567890abcdef12345678",
        is_testnet=False,
    )

    # Create trading config with defaults
    config = TradingConfig(
        active_profile="mainnet",
        profiles={"mainnet": profile},
    )

    print(f"Active Profile: {config.active_profile}")
    print(f"Owner Address: {config.owner_address}")
    print(f"Exchange: {config.exchange_name}")
    print(f"Data Source: {config.data_source.source}")
    print(f"Portfolio Leverage: {config.portfolio.target_leverage}")
    print(f"Number of Longs: {config.portfolio.num_long}")
    print(f"Number of Shorts: {config.portfolio.num_short}")


def example_custom_portfolio():
    """Create a configuration with custom portfolio settings."""
    print("\n=== Custom Portfolio Configuration ===")

    # Configure stop loss
    stop_loss = StopLossConfig(
        sides="both",  # Apply to both long and short positions
        pct=Decimal("0.20"),  # 20% stop loss
        slippage=Decimal("0.05"),  # 5% slippage tolerance
    )

    # Configure rebalancing schedule
    rebalancing = RebalancingConfig(
        every_n_days=7,  # Weekly rebalancing
        at_time="12:00",  # At noon UTC
    )

    # Configure portfolio
    portfolio = PortfolioConfig(
        num_long=15,  # Hold 15 long positions
        num_short=5,  # Hold 5 short positions
        target_leverage=Decimal("2.0"),  # 2x leverage
        rank_power=Decimal("0.5"),  # Use rank-weighted scheme
        stop_loss=stop_loss,
        rebalancing=rebalancing,
    )

    # Create profile
    profile = ExchangeProfile(
        name="aggressive",
        exchange="hyperliquid",
        owner_address="0xabcdef1234567890abcdef1234567890abcdef12",
    )

    # Create config
    config = TradingConfig(
        active_profile="aggressive",
        profiles={"aggressive": profile},
        portfolio=portfolio,
    )

    print(f"Portfolio Leverage: {config.portfolio.target_leverage}")
    print(f"Longs/Shorts: {config.portfolio.num_long}/{config.portfolio.num_short}")
    print(f"Stop Loss: {config.portfolio.stop_loss.sides} @ {config.portfolio.stop_loss.pct}%")
    print(f"Rebalance: Every {config.portfolio.rebalancing.every_n_days} days @ {config.portfolio.rebalancing.at_time}")


def example_multi_profile():
    """Create a configuration with multiple exchange profiles."""
    print("\n=== Multi-Profile Configuration ===")

    # Create mainnet profile
    mainnet = ExchangeProfile(
        name="mainnet",
        exchange="hyperliquid",
        owner_address="0x1111111111111111111111111111111111111111",
        signer_env="MAINNET_PRIVATE_KEY",
        is_testnet=False,
    )

    # Create testnet profile
    testnet = ExchangeProfile(
        name="testnet",
        exchange="hyperliquid",
        owner_address="0x2222222222222222222222222222222222222222",
        signer_env="TESTNET_PRIVATE_KEY",
        is_testnet=True,
    )

    # Create vault profile
    vault = ExchangeProfile(
        name="vault",
        exchange="hyperliquid",
        owner_address="0x3333333333333333333333333333333333333333",
        vault_address="0x4444444444444444444444444444444444444444",
        signer_env="VAULT_PRIVATE_KEY",
        is_testnet=False,
    )

    # Create config with all profiles
    config = TradingConfig(
        active_profile="mainnet",
        profiles={
            "mainnet": mainnet,
            "testnet": testnet,
            "vault": vault,
        },
    )

    print(f"Active Profile: {config.active_profile}")
    print(f"Current Owner: {config.owner_address}")

    # Switch to testnet
    config.active_profile = "testnet"
    print(f"\nSwitched to: {config.active_profile}")
    print(f"New Owner: {config.owner_address}")
    print(f"Is Testnet: {config.current_profile.is_testnet}")

    # Switch to vault
    config.active_profile = "vault"
    print(f"\nSwitched to: {config.active_profile}")
    print(f"Vault Address: {config.current_profile.vault_address}")


def example_custom_execution():
    """Create a configuration with custom execution settings."""
    print("\n=== Custom Execution Configuration ===")

    # Configure execution with limit orders
    execution = ExecutionConfig(
        slippage_tolerance=Decimal("0.01"),  # 1% slippage tolerance
        limit_price_offset=Decimal("0.002"),  # 0.2% price offset
        min_trade_value=Decimal("25.0"),  # $25 minimum trade
        order_type=OrderType.LIMIT,  # Use limit orders
        time_in_force=TimeInForce.GTC,  # Good til canceled
    )

    profile = ExchangeProfile(
        name="default",
        exchange="hyperliquid",
        owner_address="0x5555555555555555555555555555555555555555",
    )

    config = TradingConfig(
        active_profile="default",
        profiles={"default": profile},
        execution=execution,
    )

    print(f"Order Type: {config.execution.order_type.value}")
    print(f"Time in Force: {config.execution.time_in_force.value}")
    print(f"Slippage Tolerance: {config.execution.slippage_tolerance}")
    print(f"Min Trade Value: ${config.execution.min_trade_value}")


def example_data_source():
    """Create a configuration with custom data source."""
    print("\n=== Custom Data Source Configuration ===")

    # Configure CrowdCent data source
    crowdcent = DataSourceConfig(
        source="crowdcent",
        crowdcent_challenge="hyperliquid-ranking",
        date_column="release_date",
        asset_id_column="id",
        prediction_column="pred_10d",
    )

    # Configure local data source
    local = DataSourceConfig(
        source="local",
        path="/path/to/predictions.parquet",
        date_column="trade_date",
        asset_id_column="ticker",
        prediction_column="signal",
    )

    profile = ExchangeProfile(
        name="default",
        exchange="hyperliquid",
        owner_address="0x6666666666666666666666666666666666666666",
    )

    # Create config with CrowdCent
    config = TradingConfig(
        active_profile="default",
        profiles={"default": profile},
        data_source=crowdcent,
    )

    print(f"Data Source: {config.data_source.source}")
    print(f"Challenge: {config.data_source.crowdcent_challenge}")
    print(f"Columns: {config.data_source.date_column}, {config.data_source.asset_id_column}, {config.data_source.prediction_column}")

    # Switch to local source
    config.data_source = local
    print(f"\nSwitched to: {config.data_source.source}")
    print(f"Path: {config.data_source.path}")


def example_serialization():
    """Demonstrate configuration serialization."""
    print("\n=== Configuration Serialization ===")

    profile = ExchangeProfile(
        name="demo",
        exchange="hyperliquid",
        owner_address="0x7777777777777777777777777777777777777777",
    )

    config = TradingConfig(
        active_profile="demo",
        profiles={"demo": profile},
    )

    # Serialize to dict
    config_dict = config.model_dump()
    print(f"Dict keys: {list(config_dict.keys())}")

    # Serialize to JSON-compatible dict
    json_dict = config.model_dump(mode="json")
    print(f"JSON-compatible: {type(json_dict['portfolio']['target_leverage'])}")

    # Serialize to JSON string
    json_str = config.model_dump_json()
    print(f"JSON string length: {len(json_str)} chars")
    print(f"JSON preview: {json_str[:100]}...")


def example_complete_config():
    """Create a complete production-ready configuration."""
    print("\n=== Complete Production Configuration ===")

    # Data source
    data_source = DataSourceConfig(
        source="crowdcent",
        crowdcent_challenge="hyperliquid-ranking",
    )

    # Stop loss
    stop_loss = StopLossConfig(
        sides="both",
        pct=Decimal("0.17"),
        slippage=Decimal("0.05"),
    )

    # Rebalancing
    rebalancing = RebalancingConfig(
        every_n_days=10,
        at_time="18:15",
    )

    # Portfolio
    portfolio = PortfolioConfig(
        num_long=10,
        num_short=10,
        target_leverage=Decimal("1.5"),
        rank_power=Decimal("0.3"),
        stop_loss=stop_loss,
        rebalancing=rebalancing,
    )

    # Execution
    execution = ExecutionConfig(
        slippage_tolerance=Decimal("0.005"),
        limit_price_offset=Decimal("0.0"),
        min_trade_value=Decimal("10.0"),
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.IOC,
    )

    # Exchange profile
    profile = ExchangeProfile(
        name="production",
        exchange="hyperliquid",
        owner_address="0x8888888888888888888888888888888888888888",
        vault_address="0x9999999999999999999999999999999999999999",
        signer_env="PRODUCTION_PRIVATE_KEY",
        is_testnet=False,
    )

    # Complete config
    config = TradingConfig(
        active_profile="production",
        profiles={"production": profile},
        data_source=data_source,
        portfolio=portfolio,
        execution=execution,
    )

    print("Complete configuration created successfully!")
    print(f"Profile: {config.active_profile}")
    print(f"Exchange: {config.exchange_name}")
    print(f"Data: {config.data_source.source}")
    print(f"Portfolio: {config.portfolio.num_long}L/{config.portfolio.num_short}S @ {config.portfolio.target_leverage}x")
    print(f"Execution: {config.execution.order_type.value} orders")
    print(f"Rebalance: Every {config.portfolio.rebalancing.every_n_days}d @ {config.portfolio.rebalancing.at_time} UTC")


if __name__ == "__main__":
    example_simple_config()
    example_custom_portfolio()
    example_multi_profile()
    example_custom_execution()
    example_data_source()
    example_serialization()
    example_complete_config()
    print("\n=== All examples completed successfully! ===\n")
