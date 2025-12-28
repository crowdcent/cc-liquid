"""Unit tests for portfolio domain models.

This module tests the portfolio domain models including target positions,
rebalancing plans, and execution results.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from cc_flow.domain.orders import OrderSide, Trade
from cc_flow.domain.portfolio import ExecutionResult, RebalancePlan, TargetPosition


class TestTargetPosition:
    """Test suite for TargetPosition model."""

    def test_long_position_has_long_side(self) -> None:
        """Test that positive target_value results in LONG side."""
        position = TargetPosition(
            coin="BTC",
            target_value=Decimal("5000.00"),
            weight=Decimal("0.5")
        )

        assert position.coin == "BTC"
        assert position.target_value == Decimal("5000.00")
        assert position.weight == Decimal("0.5")
        assert position.side == "LONG"

    def test_short_position_has_short_side(self) -> None:
        """Test that negative target_value results in SHORT side."""
        position = TargetPosition(
            coin="ETH",
            target_value=Decimal("-3000.00"),
            weight=Decimal("-0.3")
        )

        assert position.coin == "ETH"
        assert position.target_value == Decimal("-3000.00")
        assert position.weight == Decimal("-0.3")
        assert position.side == "SHORT"

    def test_zero_position_has_short_side(self) -> None:
        """Test that zero target_value results in SHORT side (per spec)."""
        position = TargetPosition(
            coin="SOL",
            target_value=Decimal("0"),
            weight=Decimal("0")
        )

        assert position.target_value == Decimal("0")
        assert position.side == "SHORT"

    def test_target_position_is_frozen(self) -> None:
        """Test that TargetPosition is immutable (frozen=True)."""
        position = TargetPosition(
            coin="BTC",
            target_value=Decimal("1000.00"),
            weight=Decimal("0.1")
        )

        with pytest.raises(ValidationError, match="Instance is frozen"):
            position.coin = "ETH"  # type: ignore

    def test_target_position_serialization(self) -> None:
        """Test that TargetPosition can be serialized and deserialized."""
        position = TargetPosition(
            coin="AVAX",
            target_value=Decimal("2500.50"),
            weight=Decimal("0.25")
        )

        # Serialize to dict
        data = position.model_dump()
        assert data["coin"] == "AVAX"
        assert data["target_value"] == Decimal("2500.50")
        assert data["weight"] == Decimal("0.25")

        # Deserialize from dict
        restored = TargetPosition(**data)
        assert restored.coin == position.coin
        assert restored.target_value == position.target_value
        assert restored.weight == position.weight

    def test_target_position_with_very_small_value(self) -> None:
        """Test TargetPosition handles very small values."""
        position = TargetPosition(
            coin="BTC",
            target_value=Decimal("0.0001"),
            weight=Decimal("0.00001")
        )

        assert position.target_value == Decimal("0.0001")
        assert position.side == "LONG"

    def test_target_position_with_very_large_value(self) -> None:
        """Test TargetPosition handles very large values."""
        position = TargetPosition(
            coin="BTC",
            target_value=Decimal("1000000.00"),
            weight=Decimal("10.0")
        )

        assert position.target_value == Decimal("1000000.00")
        assert position.side == "LONG"

    def test_target_position_requires_all_fields(self) -> None:
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            TargetPosition(coin="BTC")  # type: ignore


class TestRebalancePlan:
    """Test suite for RebalancePlan model."""

    @pytest.fixture
    def sample_trade(self) -> Trade:
        """Create a sample trade for testing."""
        return Trade(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            reference_price=Decimal("50000.00"),
            current_value=Decimal("0"),
            target_value=Decimal("5000.00"),
            delta_value=Decimal("5000.00"),
            trade_type="open",
            estimated_fee=Decimal("2.50")
        )

    @pytest.fixture
    def sample_target_position(self) -> TargetPosition:
        """Create a sample target position for testing."""
        return TargetPosition(
            coin="BTC",
            target_value=Decimal("5000.00"),
            weight=Decimal("0.5")
        )

    def test_rebalance_plan_with_empty_trades(
        self,
        sample_target_position: TargetPosition
    ) -> None:
        """Test RebalancePlan with no trades."""
        plan = RebalancePlan(
            account_value=Decimal("10000.00"),
            current_leverage=Decimal("0.5"),
            target_leverage=Decimal("1.0"),
            target_positions=[sample_target_position],
            executable_trades=[]
        )

        assert plan.account_value == Decimal("10000.00")
        assert plan.current_leverage == Decimal("0.5")
        assert plan.target_leverage == Decimal("1.0")
        assert len(plan.target_positions) == 1
        assert plan.total_trades == 0
        assert plan.total_trade_value == Decimal("0")
        assert len(plan.skipped_trades) == 0
        assert len(plan.open_orders) == 0

    def test_rebalance_plan_with_only_executable_trades(
        self,
        sample_trade: Trade,
        sample_target_position: TargetPosition
    ) -> None:
        """Test RebalancePlan with only executable trades."""
        trade2 = Trade(
            coin="ETH",
            side=OrderSide.BUY,
            size=Decimal("1.0"),
            reference_price=Decimal("3000.00"),
            current_value=Decimal("0"),
            target_value=Decimal("3000.00"),
            delta_value=Decimal("3000.00"),
            trade_type="open",
            estimated_fee=Decimal("1.50")
        )

        plan = RebalancePlan(
            account_value=Decimal("10000.00"),
            current_leverage=Decimal("0.0"),
            target_leverage=Decimal("0.8"),
            target_positions=[sample_target_position],
            executable_trades=[sample_trade, trade2]
        )

        assert plan.total_trades == 2
        assert plan.total_trade_value == Decimal("8000.00")  # 5000 + 3000
        assert len(plan.executable_trades) == 2
        assert len(plan.skipped_trades) == 0

    def test_rebalance_plan_with_only_skipped_trades(
        self,
        sample_trade: Trade,
        sample_target_position: TargetPosition
    ) -> None:
        """Test RebalancePlan with only skipped trades."""
        plan = RebalancePlan(
            account_value=Decimal("10000.00"),
            current_leverage=Decimal("1.0"),
            target_leverage=Decimal("1.0"),
            target_positions=[sample_target_position],
            executable_trades=[],
            skipped_trades=[sample_trade]
        )

        assert plan.total_trades == 1
        assert plan.total_trade_value == Decimal("0")  # No executable trades
        assert len(plan.executable_trades) == 0
        assert len(plan.skipped_trades) == 1

    def test_rebalance_plan_with_both_executable_and_skipped_trades(
        self,
        sample_target_position: TargetPosition
    ) -> None:
        """Test RebalancePlan with both executable and skipped trades."""
        executable = Trade(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            reference_price=Decimal("50000.00"),
            current_value=Decimal("0"),
            target_value=Decimal("5000.00"),
            delta_value=Decimal("5000.00"),
            trade_type="open",
            estimated_fee=Decimal("2.50")
        )

        skipped = Trade(
            coin="SOL",
            side=OrderSide.BUY,
            size=Decimal("1.0"),
            reference_price=Decimal("100.00"),
            current_value=Decimal("0"),
            target_value=Decimal("100.00"),
            delta_value=Decimal("100.00"),
            trade_type="open",
            estimated_fee=Decimal("0.05")
        )

        plan = RebalancePlan(
            account_value=Decimal("10000.00"),
            current_leverage=Decimal("0.5"),
            target_leverage=Decimal("1.0"),
            target_positions=[sample_target_position],
            executable_trades=[executable],
            skipped_trades=[skipped]
        )

        assert plan.total_trades == 2
        assert plan.total_trade_value == Decimal("5000.00")  # Only executable
        assert len(plan.executable_trades) == 1
        assert len(plan.skipped_trades) == 1

    def test_rebalance_plan_total_trade_value_uses_absolute_values(
        self,
        sample_target_position: TargetPosition
    ) -> None:
        """Test that total_trade_value uses absolute values (no negative)."""
        long_trade = Trade(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            reference_price=Decimal("50000.00"),
            current_value=Decimal("0"),
            target_value=Decimal("5000.00"),
            delta_value=Decimal("5000.00"),
            trade_type="open",
            estimated_fee=Decimal("2.50")
        )

        short_trade = Trade(
            coin="ETH",
            side=OrderSide.SELL,
            size=Decimal("1.0"),
            reference_price=Decimal("3000.00"),
            current_value=Decimal("0"),
            target_value=Decimal("-3000.00"),
            delta_value=Decimal("-3000.00"),
            trade_type="open",
            estimated_fee=Decimal("1.50")
        )

        plan = RebalancePlan(
            account_value=Decimal("10000.00"),
            current_leverage=Decimal("0.0"),
            target_leverage=Decimal("0.8"),
            target_positions=[sample_target_position],
            executable_trades=[long_trade, short_trade]
        )

        # Should be |5000| + |-3000| = 8000
        assert plan.total_trade_value == Decimal("8000.00")

    def test_rebalance_plan_with_open_orders(
        self,
        sample_target_position: TargetPosition
    ) -> None:
        """Test RebalancePlan with existing open orders."""
        open_orders = [
            {"coin": "BTC", "side": "buy", "size": "0.05"},
            {"coin": "ETH", "side": "sell", "size": "0.5"}
        ]

        plan = RebalancePlan(
            account_value=Decimal("10000.00"),
            current_leverage=Decimal("0.5"),
            target_leverage=Decimal("1.0"),
            target_positions=[sample_target_position],
            executable_trades=[],
            open_orders=open_orders
        )

        assert len(plan.open_orders) == 2
        assert plan.open_orders[0]["coin"] == "BTC"
        assert plan.open_orders[1]["coin"] == "ETH"

    def test_rebalance_plan_timestamp_auto_generation(
        self,
        sample_target_position: TargetPosition
    ) -> None:
        """Test that timestamp is auto-generated if not provided."""
        plan = RebalancePlan(
            account_value=Decimal("10000.00"),
            current_leverage=Decimal("0.5"),
            target_leverage=Decimal("1.0"),
            target_positions=[sample_target_position],
            executable_trades=[]
        )

        assert plan.timestamp is not None
        assert isinstance(plan.timestamp, datetime)
        # Should be recent (within last minute)
        now = datetime.now(UTC)
        assert (now - plan.timestamp).total_seconds() < 60

    def test_rebalance_plan_serialization_with_nested_trades(
        self,
        sample_trade: Trade,
        sample_target_position: TargetPosition
    ) -> None:
        """Test that RebalancePlan can serialize nested Trade objects."""
        plan = RebalancePlan(
            account_value=Decimal("10000.00"),
            current_leverage=Decimal("0.5"),
            target_leverage=Decimal("1.0"),
            target_positions=[sample_target_position],
            executable_trades=[sample_trade]
        )

        # Serialize to dict
        data = plan.model_dump()
        assert data["account_value"] == Decimal("10000.00")
        assert len(data["executable_trades"]) == 1
        assert data["executable_trades"][0]["coin"] == "BTC"

        # Deserialize from dict
        restored = RebalancePlan(**data)
        assert restored.account_value == plan.account_value
        assert len(restored.executable_trades) == 1
        assert restored.executable_trades[0].coin == "BTC"

    def test_rebalance_plan_leverage_change(
        self,
        sample_target_position: TargetPosition
    ) -> None:
        """Test RebalancePlan captures leverage changes."""
        plan = RebalancePlan(
            account_value=Decimal("10000.00"),
            current_leverage=Decimal("0.5"),
            target_leverage=Decimal("2.0"),
            target_positions=[sample_target_position],
            executable_trades=[]
        )

        assert plan.current_leverage == Decimal("0.5")
        assert plan.target_leverage == Decimal("2.0")
        # Leverage is increasing
        assert plan.target_leverage > plan.current_leverage

    def test_rebalance_plan_is_mutable(
        self,
        sample_target_position: TargetPosition
    ) -> None:
        """Test that RebalancePlan is mutable (frozen=False)."""
        plan = RebalancePlan(
            account_value=Decimal("10000.00"),
            current_leverage=Decimal("0.5"),
            target_leverage=Decimal("1.0"),
            target_positions=[sample_target_position],
            executable_trades=[]
        )

        # Should be able to modify
        plan.account_value = Decimal("20000.00")
        assert plan.account_value == Decimal("20000.00")

    def test_rebalance_plan_with_zero_account_value(
        self,
        sample_target_position: TargetPosition
    ) -> None:
        """Test RebalancePlan handles zero account value edge case."""
        plan = RebalancePlan(
            account_value=Decimal("0"),
            current_leverage=Decimal("0"),
            target_leverage=Decimal("0"),
            target_positions=[sample_target_position],
            executable_trades=[]
        )

        assert plan.account_value == Decimal("0")
        assert plan.total_trade_value == Decimal("0")

    def test_rebalance_plan_with_many_trades(
        self,
        sample_target_position: TargetPosition
    ) -> None:
        """Test RebalancePlan with large number of trades."""
        # Create 100 trades
        trades = [
            Trade(
                coin=f"COIN{i}",
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                size=Decimal("1.0"),
                reference_price=Decimal("100.00"),
                current_value=Decimal("0"),
                target_value=Decimal("100.00") if i % 2 == 0 else Decimal("-100.00"),
                delta_value=Decimal("100.00") if i % 2 == 0 else Decimal("-100.00"),
                trade_type="open",
                estimated_fee=Decimal("0.05")
            )
            for i in range(100)
        ]

        plan = RebalancePlan(
            account_value=Decimal("100000.00"),
            current_leverage=Decimal("0.0"),
            target_leverage=Decimal("1.0"),
            target_positions=[sample_target_position],
            executable_trades=trades
        )

        assert plan.total_trades == 100
        # Each trade has abs(delta_value) = 100
        assert plan.total_trade_value == Decimal("10000.00")


class TestExecutionResult:
    """Test suite for ExecutionResult model."""

    @pytest.fixture
    def sample_trade(self) -> Trade:
        """Create a sample trade for testing."""
        return Trade(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            reference_price=Decimal("50000.00"),
            current_value=Decimal("0"),
            target_value=Decimal("5000.00"),
            delta_value=Decimal("5000.00"),
            trade_type="open",
            estimated_fee=Decimal("2.50")
        )

    @pytest.fixture
    def sample_plan(self, sample_trade: Trade) -> RebalancePlan:
        """Create a sample rebalance plan for testing."""
        target_position = TargetPosition(
            coin="BTC",
            target_value=Decimal("5000.00"),
            weight=Decimal("0.5")
        )

        return RebalancePlan(
            account_value=Decimal("10000.00"),
            current_leverage=Decimal("0.0"),
            target_leverage=Decimal("0.5"),
            target_positions=[target_position],
            executable_trades=[sample_trade]
        )

    def test_execution_result_with_all_successful_trades(
        self,
        sample_plan: RebalancePlan,
        sample_trade: Trade
    ) -> None:
        """Test ExecutionResult with 100% success rate."""
        result = ExecutionResult(
            plan=sample_plan,
            successful_trades=[sample_trade]
        )

        assert result.success_rate == 1.0
        assert len(result.successful_trades) == 1
        assert len(result.failed_trades) == 0
        assert result.stop_losses_applied == 0
        assert result.stop_losses_failed == 0

    def test_execution_result_with_all_failed_trades(
        self,
        sample_plan: RebalancePlan,
        sample_trade: Trade
    ) -> None:
        """Test ExecutionResult with 0% success rate."""
        result = ExecutionResult(
            plan=sample_plan,
            successful_trades=[],
            failed_trades=[sample_trade]
        )

        assert result.success_rate == 0.0
        assert len(result.successful_trades) == 0
        assert len(result.failed_trades) == 1

    def test_execution_result_with_mixed_success_failure(
        self,
        sample_plan: RebalancePlan
    ) -> None:
        """Test ExecutionResult with 50% success rate."""
        trade1 = Trade(
            coin="BTC",
            side=OrderSide.BUY,
            size=Decimal("0.1"),
            reference_price=Decimal("50000.00"),
            current_value=Decimal("0"),
            target_value=Decimal("5000.00"),
            delta_value=Decimal("5000.00"),
            trade_type="open",
            estimated_fee=Decimal("2.50")
        )

        trade2 = Trade(
            coin="ETH",
            side=OrderSide.BUY,
            size=Decimal("1.0"),
            reference_price=Decimal("3000.00"),
            current_value=Decimal("0"),
            target_value=Decimal("3000.00"),
            delta_value=Decimal("3000.00"),
            trade_type="open",
            estimated_fee=Decimal("1.50")
        )

        result = ExecutionResult(
            plan=sample_plan,
            successful_trades=[trade1],
            failed_trades=[trade2]
        )

        assert result.success_rate == 0.5
        assert len(result.successful_trades) == 1
        assert len(result.failed_trades) == 1

    def test_execution_result_with_no_trades(
        self,
        sample_plan: RebalancePlan
    ) -> None:
        """Test ExecutionResult with no trades returns 0.0 success rate."""
        result = ExecutionResult(
            plan=sample_plan,
            successful_trades=[]
        )

        assert result.success_rate == 0.0
        assert len(result.successful_trades) == 0
        assert len(result.failed_trades) == 0

    def test_execution_result_with_75_percent_success(
        self,
        sample_plan: RebalancePlan
    ) -> None:
        """Test ExecutionResult with 75% success rate (3/4)."""
        trades = [
            Trade(
                coin=f"COIN{i}",
                side=OrderSide.BUY,
                size=Decimal("1.0"),
                reference_price=Decimal("100.00"),
                current_value=Decimal("0"),
                target_value=Decimal("100.00"),
                delta_value=Decimal("100.00"),
                trade_type="open",
                estimated_fee=Decimal("0.05")
            )
            for i in range(4)
        ]

        result = ExecutionResult(
            plan=sample_plan,
            successful_trades=trades[:3],
            failed_trades=[trades[3]]
        )

        assert result.success_rate == 0.75
        assert len(result.successful_trades) == 3
        assert len(result.failed_trades) == 1

    def test_execution_result_with_stop_losses_applied(
        self,
        sample_plan: RebalancePlan,
        sample_trade: Trade
    ) -> None:
        """Test ExecutionResult tracks stop losses applied."""
        result = ExecutionResult(
            plan=sample_plan,
            successful_trades=[sample_trade],
            stop_losses_applied=5
        )

        assert result.stop_losses_applied == 5
        assert result.stop_losses_failed == 0

    def test_execution_result_with_stop_losses_failed(
        self,
        sample_plan: RebalancePlan,
        sample_trade: Trade
    ) -> None:
        """Test ExecutionResult tracks stop losses that failed."""
        result = ExecutionResult(
            plan=sample_plan,
            successful_trades=[sample_trade],
            stop_losses_applied=3,
            stop_losses_failed=2
        )

        assert result.stop_losses_applied == 3
        assert result.stop_losses_failed == 2

    def test_execution_result_executed_at_auto_generation(
        self,
        sample_plan: RebalancePlan,
        sample_trade: Trade
    ) -> None:
        """Test that executed_at is auto-generated if not provided."""
        result = ExecutionResult(
            plan=sample_plan,
            successful_trades=[sample_trade]
        )

        assert result.executed_at is not None
        assert isinstance(result.executed_at, datetime)
        # Should be recent (within last minute)
        now = datetime.now(UTC)
        assert (now - result.executed_at).total_seconds() < 60

    def test_execution_result_serialization_with_nested_plan(
        self,
        sample_plan: RebalancePlan,
        sample_trade: Trade
    ) -> None:
        """Test that ExecutionResult can serialize nested RebalancePlan."""
        result = ExecutionResult(
            plan=sample_plan,
            successful_trades=[sample_trade]
        )

        # Serialize to dict
        data = result.model_dump()
        assert "plan" in data
        assert data["plan"]["account_value"] == Decimal("10000.00")
        assert len(data["successful_trades"]) == 1

        # Deserialize from dict
        restored = ExecutionResult(**data)
        assert restored.plan.account_value == sample_plan.account_value
        assert len(restored.successful_trades) == 1
        assert restored.successful_trades[0].coin == "BTC"

    def test_execution_result_is_mutable(
        self,
        sample_plan: RebalancePlan,
        sample_trade: Trade
    ) -> None:
        """Test that ExecutionResult is mutable (frozen=False)."""
        result = ExecutionResult(
            plan=sample_plan,
            successful_trades=[sample_trade]
        )

        # Should be able to modify
        result.stop_losses_applied = 10
        assert result.stop_losses_applied == 10

    def test_execution_result_success_rate_with_only_successful(
        self,
        sample_plan: RebalancePlan
    ) -> None:
        """Test success_rate calculation with only successful trades."""
        trades = [
            Trade(
                coin=f"COIN{i}",
                side=OrderSide.BUY,
                size=Decimal("1.0"),
                reference_price=Decimal("100.00"),
                current_value=Decimal("0"),
                target_value=Decimal("100.00"),
                delta_value=Decimal("100.00"),
                trade_type="open",
                estimated_fee=Decimal("0.05")
            )
            for i in range(10)
        ]

        result = ExecutionResult(
            plan=sample_plan,
            successful_trades=trades
        )

        assert result.success_rate == 1.0

    def test_execution_result_success_rate_with_only_failed(
        self,
        sample_plan: RebalancePlan
    ) -> None:
        """Test success_rate calculation with only failed trades."""
        trades = [
            Trade(
                coin=f"COIN{i}",
                side=OrderSide.BUY,
                size=Decimal("1.0"),
                reference_price=Decimal("100.00"),
                current_value=Decimal("0"),
                target_value=Decimal("100.00"),
                delta_value=Decimal("100.00"),
                trade_type="open",
                estimated_fee=Decimal("0.05")
            )
            for i in range(10)
        ]

        result = ExecutionResult(
            plan=sample_plan,
            successful_trades=[],
            failed_trades=trades
        )

        assert result.success_rate == 0.0

    def test_execution_result_with_decimal_precision(
        self,
        sample_plan: RebalancePlan
    ) -> None:
        """Test success_rate maintains decimal precision."""
        trades = [
            Trade(
                coin=f"COIN{i}",
                side=OrderSide.BUY,
                size=Decimal("1.0"),
                reference_price=Decimal("100.00"),
                current_value=Decimal("0"),
                target_value=Decimal("100.00"),
                delta_value=Decimal("100.00"),
                trade_type="open",
                estimated_fee=Decimal("0.05")
            )
            for i in range(3)
        ]

        # 2 successful, 1 failed = 2/3 = 0.666...
        result = ExecutionResult(
            plan=sample_plan,
            successful_trades=trades[:2],
            failed_trades=[trades[2]]
        )

        assert abs(result.success_rate - 0.6666666666666666) < 1e-10
