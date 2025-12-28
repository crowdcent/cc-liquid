"""Example usage of ConfigLoader.

This script demonstrates how to use the ConfigLoader to load configuration
from YAML and .env files, and apply CLI overrides.

Run with: uv run python cc_flow/config/example_usage.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path (cc_flow is at project root level)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cc_flow.config.loader import ConfigLoader


def main():
    """Demonstrate ConfigLoader usage."""
    print("=" * 80)
    print("ConfigLoader Example Usage")
    print("=" * 80)

    # Example 1: Load configuration with default paths
    print("\n1. Loading configuration from test fixtures:")
    print("-" * 80)

    test_fixtures = Path(__file__).parent.parent.parent / "tests" / "fixtures"
    config_path = test_fixtures / "test_config.yaml"
    env_path = test_fixtures / "test.env"

    loader = ConfigLoader(
        config_path=str(config_path),
        env_path=str(env_path)
    )

    config = loader.load_config()

    print(f"Active Profile: {config.active_profile}")
    print(f"Owner Address: {config.owner_address}")
    print(f"Exchange: {config.exchange_name}")
    print(f"Portfolio: {config.portfolio.num_long} long / {config.portfolio.num_short} short")
    print(f"Target Leverage: {config.portfolio.target_leverage}")
    print(f"Data Source: {config.data_source.source}")

    # Example 2: Apply CLI overrides
    print("\n2. Applying CLI overrides:")
    print("-" * 80)

    overrides = {
        "portfolio.num_long": "20",
        "portfolio.num_short": "5",
        "portfolio.target_leverage": "2.0",
        "execution.min_trade_value": "25.0",
        "data_source.source": "numerai"
    }

    print("Original values:")
    print(f"  num_long: {config.portfolio.num_long}")
    print(f"  num_short: {config.portfolio.num_short}")
    print(f"  target_leverage: {config.portfolio.target_leverage}")
    print(f"  min_trade_value: {config.execution.min_trade_value}")
    print(f"  data_source: {config.data_source.source}")

    updated_config = loader.apply_overrides(config, overrides)

    print("\nUpdated values:")
    print(f"  num_long: {updated_config.portfolio.num_long}")
    print(f"  num_short: {updated_config.portfolio.num_short}")
    print(f"  target_leverage: {updated_config.portfolio.target_leverage}")
    print(f"  min_trade_value: {updated_config.execution.min_trade_value}")
    print(f"  data_source: {updated_config.data_source.source}")

    # Example 3: Nested overrides
    print("\n3. Applying nested overrides:")
    print("-" * 80)

    nested_overrides = {
        "portfolio.stop_loss.pct": "0.25",
        "portfolio.rebalancing.every_n_days": "7",
        "portfolio.rebalancing.at_time": "12:00"
    }

    print("Original nested values:")
    print(f"  stop_loss.pct: {config.portfolio.stop_loss.pct}")
    print(f"  rebalancing.every_n_days: {config.portfolio.rebalancing.every_n_days}")
    print(f"  rebalancing.at_time: {config.portfolio.rebalancing.at_time}")

    updated_config2 = loader.apply_overrides(config, nested_overrides)

    print("\nUpdated nested values:")
    print(f"  stop_loss.pct: {updated_config2.portfolio.stop_loss.pct}")
    print(f"  rebalancing.every_n_days: {updated_config2.portfolio.rebalancing.every_n_days}")
    print(f"  rebalancing.at_time: {updated_config2.portfolio.rebalancing.at_time}")

    # Example 4: Error handling
    print("\n4. Error handling:")
    print("-" * 80)

    try:
        invalid_overrides = {"invalid.path": "value"}
        loader.apply_overrides(config, invalid_overrides)
    except ValueError as e:
        print(f"✓ Caught expected error for invalid path: {e}")

    try:
        invalid_overrides = {"portfolio.nonexistent": "value"}
        loader.apply_overrides(config, invalid_overrides)
    except ValueError as e:
        print(f"✓ Caught expected error for invalid nested field: {e}")

    print("\n" + "=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
