"""Strategy factory for creating composed strategies from configuration."""

from typing import TYPE_CHECKING
from .composed import (
    ComposedStrategy,
    create_full_mode_strategy,
    create_rolling_mode_strategy,
    create_take_profit_auto_strategy,
    create_take_profit_with_stop_loss_strategy,
    create_rolling_with_take_profit_strategy,
)

if TYPE_CHECKING:
    from ..config import Config


class StrategyFactory:
    """Factory for creating strategy instances from configuration.

    Maps strategy names to factory functions that create
    composed strategies with the right components.
    """

    # Registry of built-in strategies
    _STRATEGIES = {
        "full_mode": create_full_mode_strategy,
        "rolling_mode": create_rolling_mode_strategy,
        "take_profit_auto": create_take_profit_auto_strategy,
        "take_profit_with_stop_loss": create_take_profit_with_stop_loss_strategy,
        "rolling_with_take_profit": create_rolling_with_take_profit_strategy,
    }

    @classmethod
    def create(cls, config: "Config") -> ComposedStrategy:
        """Create strategy from configuration.

        Args:
            config: Configuration object

        Returns:
            Composed strategy instance

        Raises:
            ValueError: If strategy name not found
        """
        strategy_name = config.portfolio.strategy.get("name", "rolling_mode")
        params = config.portfolio.strategy.get("params", {})

        # Get shared parameters
        num_long = config.portfolio.strategy.get("num_long", 10)
        num_short = config.portfolio.strategy.get("num_short", 10)
        target_leverage = config.portfolio.strategy.get("target_leverage", 1.0)
        rank_power = config.portfolio.strategy.get("rank_power", 0.0)

        # Find factory function
        if strategy_name not in cls._STRATEGIES:
            available = ", ".join(cls._STRATEGIES.keys())
            raise ValueError(
                f"Unknown strategy: {strategy_name}. "
                f"Available strategies: {available}"
            )

        factory_func = cls._STRATEGIES[strategy_name]

        # Call factory with appropriate parameters
        if strategy_name == "full_mode":
            return factory_func(
                num_long=num_long,
                num_short=num_short,
                rank_power=rank_power,
            )

        elif strategy_name == "rolling_mode":
            rolling_days = params.get("rolling_days", 30)
            seed_full = params.get("seed_full", False)
            return factory_func(
                num_long=num_long,
                num_short=num_short,
                rolling_days=rolling_days,
                seed_full=seed_full,
                rank_power=rank_power,
            )

        elif strategy_name == "take_profit_auto":
            pnl_threshold = params.get("pnl_threshold_pct", 0.15)
            return factory_func(
                num_long=num_long,
                num_short=num_short,
                pnl_threshold_pct=pnl_threshold,
                rank_power=rank_power,
            )

        elif strategy_name == "take_profit_with_stop_loss":
            take_profit = params.get("take_profit_pct", 0.15)
            stop_loss = params.get("stop_loss_pct", 0.10)
            return factory_func(
                num_long=num_long,
                num_short=num_short,
                take_profit_pct=take_profit,
                stop_loss_pct=stop_loss,
                rank_power=rank_power,
            )

        elif strategy_name == "rolling_with_take_profit":
            rolling_days = params.get("rolling_days", 30)
            pnl_threshold = params.get("pnl_threshold_pct", 0.15)
            seed_full = params.get("seed_full", False)
            return factory_func(
                num_long=num_long,
                num_short=num_short,
                rolling_days=rolling_days,
                pnl_threshold_pct=pnl_threshold,
                seed_full=seed_full,
                rank_power=rank_power,
            )

        # Should never reach here
        raise ValueError(f"Factory not implemented for {strategy_name}")

    @classmethod
    def register_strategy(cls, name: str, factory_func):
        """Register a custom strategy factory.

        Allows users to add their own strategies without modifying core code.

        Args:
            name: Strategy name (used in config)
            factory_func: Function that returns ComposedStrategy

        Example:
            def my_strategy_factory(**kwargs):
                return ComposedStrategy(...)

            StrategyFactory.register_strategy("my_strategy", my_strategy_factory)
        """
        cls._STRATEGIES[name] = factory_func

    @classmethod
    def list_strategies(cls) -> list[str]:
        """List all registered strategy names."""
        return list(cls._STRATEGIES.keys())
