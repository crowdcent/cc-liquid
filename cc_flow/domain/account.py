"""
Account domain models for cc-flow.

This module defines Pydantic v2 models for account-level data including
account information, positions, and portfolio snapshots from cryptocurrency
exchanges.

Models:
    - AccountInfo: Account-level information (balance, margin, leverage)
    - Position: Individual trading position information
    - PortfolioSnapshot: Complete portfolio state at a point in time

Design Principles:
    - All models use Pydantic v2 for validation and type safety
    - Decimal type for precise financial calculations
    - Computed properties for derived metrics
    - Frozen configuration for immutable snapshots where appropriate
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AccountInfo(BaseModel):
    """
    Account-level information.

    Represents the overall state of a trading account including balance,
    margin usage, and leverage metrics.

    Attributes:
        account_value: Total account value in USD
        total_position_value: Sum of absolute position values
        margin_used: Margin currently in use
        free_collateral: Available margin
        cash_balance: Cash balance
        withdrawable: Amount available for withdrawal
        current_leverage: Current leverage ratio
        cross_leverage: Optional cross-margin leverage
        cross_margin_used: Optional cross-margin used
        cross_maintenance_margin: Optional cross-margin maintenance requirement
        raw_data: Optional raw API response for debugging

    Example:
        >>> account = AccountInfo(
        ...     account_value=Decimal("10000.00"),
        ...     total_position_value=Decimal("5000.00"),
        ...     margin_used=Decimal("2500.00"),
        ...     free_collateral=Decimal("7500.00"),
        ...     cash_balance=Decimal("5000.00"),
        ...     withdrawable=Decimal("5000.00"),
        ...     current_leverage=Decimal("0.5"),
        ... )
        >>> account.leverage_percentage
        50.0
    """

    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)

    account_value: Decimal = Field(..., description="Total account value in USD")
    total_position_value: Decimal = Field(..., description="Sum of absolute position values")
    margin_used: Decimal = Field(..., description="Margin currently in use")
    free_collateral: Decimal = Field(..., description="Available margin")
    cash_balance: Decimal = Field(..., description="Cash balance")
    withdrawable: Decimal = Field(..., description="Amount available for withdrawal")
    current_leverage: Decimal = Field(..., description="Current leverage ratio")

    # Optional cross-margin info
    cross_leverage: Decimal | None = None
    cross_margin_used: Decimal | None = None
    cross_maintenance_margin: Decimal | None = None

    # Raw data for debugging
    raw_data: dict | None = None

    @property
    def leverage_percentage(self) -> float:
        """
        Current leverage as percentage.

        Returns:
            Leverage as a percentage (e.g., 0.5 leverage returns 50.0)

        Example:
            >>> account = AccountInfo(
            ...     account_value=Decimal("10000.00"),
            ...     total_position_value=Decimal("5000.00"),
            ...     margin_used=Decimal("2500.00"),
            ...     free_collateral=Decimal("7500.00"),
            ...     cash_balance=Decimal("5000.00"),
            ...     withdrawable=Decimal("5000.00"),
            ...     current_leverage=Decimal("2.5"),
            ... )
            >>> account.leverage_percentage
            250.0
        """
        return float(self.current_leverage * 100)


class Position(BaseModel):
    """
    Individual position information.

    Represents a single trading position in the portfolio, either long or short.

    Attributes:
        coin: Asset symbol (e.g., "BTC", "ETH")
        side: Position side ("LONG" or "SHORT")
        size: Position size (always positive)
        entry_price: Average entry price
        mark_price: Current mark price
        value: Position notional value
        unrealized_pnl: Unrealized profit/loss
        return_pct: Return percentage
        liquidation_price: Optional liquidation price
        margin_used: Optional margin used for this position

    Example:
        >>> position = Position(
        ...     coin="BTC",
        ...     side="LONG",
        ...     size=Decimal("1.5"),
        ...     entry_price=Decimal("50000.00"),
        ...     mark_price=Decimal("52000.00"),
        ...     value=Decimal("78000.00"),
        ...     unrealized_pnl=Decimal("3000.00"),
        ...     return_pct=Decimal("0.04"),
        ... )
        >>> position.signed_size
        Decimal('1.5')
    """

    model_config = ConfigDict(frozen=False)

    coin: str = Field(..., description="Asset symbol")
    side: str = Field(..., description="LONG or SHORT")
    size: Decimal = Field(..., description="Position size (always positive)")
    entry_price: Decimal = Field(..., description="Average entry price")
    mark_price: Decimal = Field(..., description="Current mark price")
    value: Decimal = Field(..., description="Position notional value")
    unrealized_pnl: Decimal = Field(..., description="Unrealized profit/loss")
    return_pct: Decimal = Field(..., description="Return percentage")

    liquidation_price: Decimal | None = None
    margin_used: Decimal | None = None

    @property
    def signed_size(self) -> Decimal:
        """
        Size with sign (+ for long, - for short).

        Returns:
            Positive size for LONG positions, negative for SHORT positions

        Example:
            >>> long_pos = Position(
            ...     coin="BTC", side="LONG", size=Decimal("1.5"),
            ...     entry_price=Decimal("50000"), mark_price=Decimal("52000"),
            ...     value=Decimal("78000"), unrealized_pnl=Decimal("3000"),
            ...     return_pct=Decimal("0.04")
            ... )
            >>> long_pos.signed_size
            Decimal('1.5')
            >>> short_pos = Position(
            ...     coin="ETH", side="SHORT", size=Decimal("10.0"),
            ...     entry_price=Decimal("3000"), mark_price=Decimal("2900"),
            ...     value=Decimal("29000"), unrealized_pnl=Decimal("1000"),
            ...     return_pct=Decimal("0.0333")
            ... )
            >>> short_pos.signed_size
            Decimal('-10.0')
        """
        return self.size if self.side == "LONG" else -self.size


class PortfolioSnapshot(BaseModel):
    """
    Complete portfolio state at a point in time.

    Represents the entire portfolio including account information and all
    positions at a specific timestamp. Provides computed properties for
    portfolio-level metrics.

    Attributes:
        timestamp: Time of snapshot (auto-generated if not provided)
        account: Account information
        positions: List of positions (defaults to empty list)

    Computed Properties:
        total_long_value: Sum of all long position values
        total_short_value: Sum of all short position values
        net_exposure: Long value minus short value
        total_unrealized_pnl: Sum of all unrealized P&L

    Example:
        >>> account = AccountInfo(
        ...     account_value=Decimal("10000.00"),
        ...     total_position_value=Decimal("10000.00"),
        ...     margin_used=Decimal("5000.00"),
        ...     free_collateral=Decimal("5000.00"),
        ...     cash_balance=Decimal("5000.00"),
        ...     withdrawable=Decimal("5000.00"),
        ...     current_leverage=Decimal("1.0"),
        ... )
        >>> positions = [
        ...     Position(
        ...         coin="BTC", side="LONG", size=Decimal("1.0"),
        ...         entry_price=Decimal("50000"), mark_price=Decimal("52000"),
        ...         value=Decimal("52000"), unrealized_pnl=Decimal("2000"),
        ...         return_pct=Decimal("0.04")
        ...     ),
        ... ]
        >>> snapshot = PortfolioSnapshot(account=account, positions=positions)
        >>> snapshot.total_long_value
        Decimal('52000')
        >>> snapshot.net_exposure
        Decimal('52000')
    """

    model_config = ConfigDict(frozen=False)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    account: AccountInfo
    positions: list[Position] = Field(default_factory=list)

    @property
    def total_long_value(self) -> Decimal:
        """
        Sum of all long position values.

        Returns:
            Total value of all LONG positions

        Example:
            >>> # With two long positions
            >>> snapshot.total_long_value
            Decimal('83000.00')
        """
        return sum((p.value for p in self.positions if p.side == "LONG"), Decimal("0"))

    @property
    def total_short_value(self) -> Decimal:
        """
        Sum of all short position values.

        Returns:
            Total value of all SHORT positions

        Example:
            >>> # With two short positions
            >>> snapshot.total_short_value
            Decimal('38500.00')
        """
        return sum((p.value for p in self.positions if p.side == "SHORT"), Decimal("0"))

    @property
    def net_exposure(self) -> Decimal:
        """
        Net exposure (long value - short value).

        Returns:
            Net directional exposure of the portfolio

        Example:
            >>> # With $52000 long and $14500 short
            >>> snapshot.net_exposure
            Decimal('37500.00')
        """
        return self.total_long_value - self.total_short_value

    @property
    def total_unrealized_pnl(self) -> Decimal:
        """
        Sum of all unrealized P&L.

        Returns:
            Total unrealized profit/loss across all positions

        Example:
            >>> # With mixed P&L positions
            >>> snapshot.total_unrealized_pnl
            Decimal('2000.00')
        """
        return sum((p.unrealized_pnl for p in self.positions), Decimal("0"))
