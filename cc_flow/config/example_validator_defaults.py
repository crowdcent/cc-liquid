"""Example usage of ConfigValidator and default configurations.

This example demonstrates how to:
1. Create default configurations
2. Validate configurations
3. Handle validation warnings and errors
"""

from decimal import Decimal

from cc_flow.config.defaults import (
    get_default_config,
    get_mainnet_config,
    get_testnet_config,
)
from cc_flow.config.validator import ConfigValidator


def example_basic_usage():
    """Basic usage of defaults and validator."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)

    # Create a default config
    config = get_default_config()
    print(f"Created default config with profile: {config.active_profile}")
    print(f"Is testnet: {config.profiles['default'].is_testnet}")
    print(f"Leverage: {config.portfolio.target_leverage}x")
    print(f"Positions: {config.portfolio.num_long} long, {config.portfolio.num_short} short")

    # Validate it
    validator = ConfigValidator()
    warnings = validator.validate(config)

    if warnings:
        print("\nWarnings found:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("\nConfiguration is valid with no warnings!")


def example_testnet_vs_mainnet():
    """Compare testnet and mainnet configurations."""
    print("\n" + "=" * 60)
    print("Example 2: Testnet vs Mainnet")
    print("=" * 60)

    testnet = get_testnet_config()
    mainnet = get_mainnet_config()

    print(f"Testnet is_testnet: {testnet.profiles['default'].is_testnet}")
    print(f"Mainnet is_testnet: {mainnet.profiles['default'].is_testnet}")

    validator = ConfigValidator()

    print("\nValidating testnet config...")
    testnet_warnings = validator.validate(testnet)
    print(f"Warnings: {len(testnet_warnings)}")

    print("\nValidating mainnet config...")
    mainnet_warnings = validator.validate(mainnet)
    print(f"Warnings: {len(mainnet_warnings)}")


def example_validation_warnings():
    """Demonstrate validation warnings."""
    print("\n" + "=" * 60)
    print("Example 3: Validation Warnings")
    print("=" * 60)

    config = get_default_config()
    validator = ConfigValidator()

    # Set high leverage (will warn)
    print("\nSetting leverage to 15x (high)...")
    config.portfolio.target_leverage = Decimal("15.0")

    warnings = validator.validate(config)
    print(f"Warnings: {len(warnings)}")
    for warning in warnings:
        print(f"  - {warning}")

    # Set high min trade value with many positions
    print("\nSetting high min trade value with 100 positions...")
    config.portfolio.target_leverage = Decimal("1.0")  # Reset leverage
    config.portfolio.num_long = 50
    config.portfolio.num_short = 50
    config.execution.min_trade_value = Decimal("200.0")

    warnings = validator.validate(config)
    print(f"Warnings: {len(warnings)}")
    for warning in warnings:
        print(f"  - {warning}")


def example_validation_errors():
    """Demonstrate validation errors."""
    print("\n" + "=" * 60)
    print("Example 4: Validation Errors")
    print("=" * 60)

    config = get_default_config()
    validator = ConfigValidator()

    # Try invalid profile
    print("\nTrying invalid profile...")
    config.active_profile = "nonexistent"
    try:
        validator.validate(config)
        print("No error raised (unexpected!)")
    except ValueError as e:
        print(f"Error raised (expected): {e}")

    # Reset and try zero leverage
    config = get_default_config()
    print("\nTrying zero leverage...")
    config.portfolio.target_leverage = Decimal("0")
    try:
        validator.validate(config)
        print("No error raised (unexpected!)")
    except ValueError as e:
        print(f"Error raised (expected): {e}")

    # Reset and try zero positions
    config = get_default_config()
    print("\nTrying zero positions...")
    config.portfolio.num_long = 0
    config.portfolio.num_short = 0
    try:
        validator.validate(config)
        print("No error raised (unexpected!)")
    except ValueError as e:
        print(f"Error raised (expected): {e}")

    # Reset and try invalid time format
    config = get_default_config()
    print("\nTrying invalid time format...")
    config.portfolio.rebalancing.at_time = "9:15"  # Should be 09:15
    try:
        validator.validate(config)
        print("No error raised (unexpected!)")
    except ValueError as e:
        print(f"Error raised (expected): {e}")


def example_customization():
    """Demonstrate customizing default configs."""
    print("\n" + "=" * 60)
    print("Example 5: Customizing Default Configs")
    print("=" * 60)

    # Start with default
    config = get_default_config()
    print("Starting with default config...")
    print(f"  Leverage: {config.portfolio.target_leverage}x")
    print(f"  Long positions: {config.portfolio.num_long}")
    print(f"  Short positions: {config.portfolio.num_short}")

    # Customize for more aggressive strategy
    print("\nCustomizing for aggressive strategy...")
    config.portfolio.target_leverage = Decimal("3.0")
    config.portfolio.num_long = 20
    config.portfolio.num_short = 20
    config.portfolio.rank_power = Decimal("1.5")

    print(f"  Leverage: {config.portfolio.target_leverage}x")
    print(f"  Long positions: {config.portfolio.num_long}")
    print(f"  Short positions: {config.portfolio.num_short}")
    print(f"  Rank power: {config.portfolio.rank_power}")

    # Validate
    validator = ConfigValidator()
    warnings = validator.validate(config)

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("\nConfiguration is valid!")


if __name__ == "__main__":
    example_basic_usage()
    example_testnet_vs_mainnet()
    example_validation_warnings()
    example_validation_errors()
    example_customization()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
