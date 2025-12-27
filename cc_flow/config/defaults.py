"""Default configuration factory functions.

This module provides factory functions for creating pre-configured
TradingConfig instances with sensible defaults for common scenarios.

The defaults prioritize safety:
- Conservative 1x leverage
- Testnet by default
- Stop losses disabled
- Equal weighting
- 10 long + 10 short positions

Users should customize these defaults based on their risk tolerance
and trading strategy.

Example:
    >>> from cc_flow.config.defaults import get_default_config
    >>> config = get_default_config()
    >>> config.portfolio.target_leverage
    Decimal('1.0')
    >>> config.profiles["default"].is_testnet
    True
"""

from __future__ import annotations

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


def get_default_config() -> TradingConfig:
    """Get default trading configuration.

    Creates a safe, conservative configuration suitable for getting started.
    Uses testnet, 1x leverage, and equal weighting.

    Returns:
        TradingConfig with sensible defaults

    Example:
        >>> config = get_default_config()
        >>> assert config.profiles["default"].is_testnet is True
        >>> assert config.portfolio.target_leverage == Decimal("1.0")
    """
    return TradingConfig(
        active_profile="default",
        profiles={
            "default": ExchangeProfile(
                name="default",
                exchange="hyperliquid",
                owner_address="0x0000000000000000000000000000000000000000",
                vault_address=None,
                signer_env="HYPERLIQUID_PRIVATE_KEY",
                is_testnet=True,
            )
        },
        data_source=DataSourceConfig(
            source="local",
            path="predictions.parquet",
            date_column="date",
            asset_id_column="asset_id",
            prediction_column="prediction",
        ),
        portfolio=PortfolioConfig(
            num_long=10,
            num_short=10,
            target_leverage=Decimal("1.0"),
            rank_power=Decimal("0.0"),
            stop_loss=StopLossConfig(
                sides="none",
                pct=Decimal("0.17"),
                slippage=Decimal("0.05"),
            ),
            rebalancing=RebalancingConfig(
                every_n_days=10,
                at_time="18:15",
            ),
        ),
        execution=ExecutionConfig(
            slippage_tolerance=Decimal("0.005"),
            limit_price_offset=Decimal("0.0"),
            min_trade_value=Decimal("10.0"),
        ),
    )


def get_testnet_config() -> TradingConfig:
    """Get testnet configuration.

    Returns a configuration explicitly set for testnet.
    Identical to default config (which is already testnet).

    Returns:
        TradingConfig configured for testnet

    Example:
        >>> config = get_testnet_config()
        >>> assert config.profiles["default"].is_testnet is True
    """
    config = get_default_config()
    config.profiles["default"].is_testnet = True
    return config


def get_mainnet_config() -> TradingConfig:
    """Get mainnet configuration template.

    Returns a configuration for mainnet with testnet flag disabled.
    User must still update the owner_address with their actual address.

    WARNING: This configuration will trade with real money.
    Always verify addresses and settings before using.

    Returns:
        TradingConfig configured for mainnet

    Example:
        >>> config = get_mainnet_config()
        >>> assert config.profiles["default"].is_testnet is False
        >>> # User must update address:
        >>> config.profiles["default"].owner_address = "0x..."
    """
    config = get_default_config()
    config.profiles["default"].is_testnet = False
    return config
