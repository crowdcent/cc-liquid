"""Portfolio domain models for rebalancing and execution tracking.

This module defines models for target positions, rebalancing plans, and
execution results used throughout the trading workflow.

Models:
    TargetPosition: Target position specification with coin, value, and weight
    RebalancePlan: Complete rebalancing plan with trades and portfolio state
    ExecutionResult: Result of executing a rebalance plan with success metrics
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .orders import Trade


class TargetPosition(BaseModel):
    """Target position specification.

    Represents the desired position for a specific coin, including the
    target notional value (signed for long/short) and leverage-adjusted weight.

    Attributes:
        coin: Trading pair symbol (e.g., "BTC", "ETH")
        target_value: Signed notional value (positive for LONG, negative for SHORT)
        weight: Leverage-adjusted weight in the portfolio

    Properties:
        side: Position side ("LONG" if target_value > 0, else "SHORT")

    Example:
        >>> position = TargetPosition(
        ...     coin="BTC",
        ...     target_value=Decimal("5000.00"),
        ...     weight=Decimal("0.5")
        ... )
        >>> assert position.side == "LONG"
    """

    model_config = ConfigDict(frozen=True)

    coin: str
    target_value: Decimal  # Signed notional value
    weight: Decimal  # Leverage-adjusted weight

    @property
    def side(self) -> str:
        """Determine position side based on target value.

        Returns:
            "LONG" if target_value > 0, else "SHORT"
        """
        return "LONG" if self.target_value > 0 else "SHORT"


class RebalancePlan(BaseModel):
    """Complete rebalancing plan.

    Represents a comprehensive rebalancing plan including current portfolio state,
    target positions, trades to execute, and skipped trades.

    Attributes:
        timestamp: Plan creation timestamp (auto-generated)
        account_value: Total account value in USD
        current_leverage: Current portfolio leverage
        target_leverage: Desired target leverage
        target_positions: List of target positions
        executable_trades: Trades that will be executed
        skipped_trades: Trades that were skipped (e.g., below min notional)
        open_orders: List of existing open orders

    Properties:
        total_trades: Total number of trades (executable + skipped)
        total_trade_value: Sum of absolute delta values for executable trades

    Example:
        >>> plan = RebalancePlan(
        ...     account_value=Decimal("10000.00"),
        ...     current_leverage=Decimal("0.5"),
        ...     target_leverage=Decimal("1.0"),
        ...     target_positions=[position],
        ...     executable_trades=[trade]
        ... )
        >>> assert plan.total_trades == 1
    """

    model_config = ConfigDict(frozen=False)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

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
        """Calculate total number of trades.

        Returns:
            Sum of executable and skipped trades
        """
        return len(self.executable_trades) + len(self.skipped_trades)

    @property
    def total_trade_value(self) -> Decimal:
        """Calculate total trade value (absolute sum).

        Returns:
            Sum of absolute delta values for all executable trades
        """
        return sum(abs(t.delta_value) for t in self.executable_trades)


class ExecutionResult(BaseModel):
    """Result of executing a rebalance plan.

    Tracks the execution outcome including successful/failed trades and
    stop loss application.

    Attributes:
        plan: The rebalance plan that was executed
        executed_at: Execution timestamp (auto-generated)
        successful_trades: List of successfully executed trades
        failed_trades: List of failed trades
        stop_losses_applied: Number of stop losses successfully applied
        stop_losses_failed: Number of stop loss applications that failed

    Properties:
        success_rate: Ratio of successful trades to total trades (0.0 to 1.0)

    Example:
        >>> result = ExecutionResult(
        ...     plan=plan,
        ...     successful_trades=[trade1, trade2],
        ...     failed_trades=[trade3]
        ... )
        >>> assert result.success_rate == 0.666...
    """

    model_config = ConfigDict(frozen=False)

    plan: RebalancePlan
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    successful_trades: list[Trade]
    failed_trades: list[Trade] = Field(default_factory=list)

    # Stop loss info
    stop_losses_applied: int = 0
    stop_losses_failed: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate trade execution success rate.

        Returns:
            Ratio of successful trades to total trades (0.0 if no trades)
        """
        total = len(self.successful_trades) + len(self.failed_trades)
        return len(self.successful_trades) / total if total > 0 else 0.0
