#!/usr/bin/env python3
"""Demonstration of portfolio domain models.

This example shows how to use TargetPosition, RebalancePlan, and ExecutionResult
models for tracking portfolio rebalancing workflows.

Run with: uv run python examples/portfolio_models_demo.py
"""

import sys
from decimal import Decimal
from pathlib import Path

# Add parent directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from domain.orders import OrderSide, Trade
from domain.portfolio import ExecutionResult, RebalancePlan, TargetPosition


def main() -> None:
    """Demonstrate portfolio model usage."""

    print("=" * 80)
    print("Portfolio Domain Models Demo")
    print("=" * 80)
    print()

    # =========================================================================
    # 1. Create Target Positions
    # =========================================================================
    print("1. Creating Target Positions")
    print("-" * 80)

    # Long position in BTC
    btc_position = TargetPosition(
        coin="BTC", target_value=Decimal("5000.00"), weight=Decimal("0.5")
    )
    print(f"BTC Position: {btc_position.coin}")
    print(f"  Target Value: ${btc_position.target_value:,.2f}")
    print(f"  Weight: {btc_position.weight:.1%}")
    print(f"  Side: {btc_position.side}")
    print()

    # Short position in ETH
    eth_position = TargetPosition(
        coin="ETH", target_value=Decimal("-3000.00"), weight=Decimal("-0.3")
    )
    print(f"ETH Position: {eth_position.coin}")
    print(f"  Target Value: ${eth_position.target_value:,.2f}")
    print(f"  Weight: {eth_position.weight:.1%}")
    print(f"  Side: {eth_position.side}")
    print()

    # Zero position (closing SOL)
    sol_position = TargetPosition(coin="SOL", target_value=Decimal("0"), weight=Decimal("0"))
    print(f"SOL Position: {sol_position.coin}")
    print(f"  Target Value: ${sol_position.target_value:,.2f}")
    print(f"  Weight: {sol_position.weight:.1%}")
    print(f"  Side: {sol_position.side} (closing position)")
    print()

    # =========================================================================
    # 2. Create Trades
    # =========================================================================
    print("2. Creating Trades")
    print("-" * 80)

    # Trade to open BTC position
    btc_trade = Trade(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("0.1"),
        reference_price=Decimal("50000.00"),
        current_value=Decimal("0"),
        target_value=Decimal("5000.00"),
        delta_value=Decimal("5000.00"),
        trade_type="open",
        estimated_fee=Decimal("2.50"),
    )
    print(f"BTC Trade: {btc_trade.trade_type.upper()} - {btc_trade.side.value.upper()}")
    print(f"  Size: {btc_trade.size} BTC")
    print(f"  Reference Price: ${btc_trade.reference_price:,.2f}")
    print(f"  Delta Value: ${btc_trade.delta_value:,.2f}")
    print(f"  Estimated Fee: ${btc_trade.estimated_fee:.2f}")
    print()

    # Trade to open ETH short
    eth_trade = Trade(
        coin="ETH",
        side=OrderSide.SELL,
        size=Decimal("1.0"),
        reference_price=Decimal("3000.00"),
        current_value=Decimal("0"),
        target_value=Decimal("-3000.00"),
        delta_value=Decimal("-3000.00"),
        trade_type="open",
        estimated_fee=Decimal("1.50"),
    )
    print(f"ETH Trade: {eth_trade.trade_type.upper()} - {eth_trade.side.value.upper()}")
    print(f"  Size: {eth_trade.size} ETH")
    print(f"  Reference Price: ${eth_trade.reference_price:,.2f}")
    print(f"  Delta Value: ${eth_trade.delta_value:,.2f}")
    print(f"  Estimated Fee: ${eth_trade.estimated_fee:.2f}")
    print()

    # Small trade below min notional (will be skipped)
    sol_trade = Trade(
        coin="SOL",
        side=OrderSide.BUY,
        size=Decimal("0.05"),
        reference_price=Decimal("100.00"),
        current_value=Decimal("0"),
        target_value=Decimal("5.00"),
        delta_value=Decimal("5.00"),
        trade_type="open",
        estimated_fee=Decimal("0.003"),
    )
    print(f"SOL Trade: {sol_trade.trade_type.upper()} - {sol_trade.side.value.upper()}")
    print(f"  Size: {sol_trade.size} SOL")
    print(f"  Delta Value: ${sol_trade.delta_value:,.2f} (below min notional, will skip)")
    print()

    # =========================================================================
    # 3. Create Rebalance Plan
    # =========================================================================
    print("3. Creating Rebalance Plan")
    print("-" * 80)

    plan = RebalancePlan(
        account_value=Decimal("10000.00"),
        current_leverage=Decimal("0.0"),
        target_leverage=Decimal("0.8"),
        target_positions=[btc_position, eth_position, sol_position],
        executable_trades=[btc_trade, eth_trade],
        skipped_trades=[sol_trade],
    )

    print(f"Account Value: ${plan.account_value:,.2f}")
    print(f"Current Leverage: {plan.current_leverage:.1f}x")
    print(f"Target Leverage: {plan.target_leverage:.1f}x")
    print()
    print(f"Target Positions: {len(plan.target_positions)}")
    print(f"Executable Trades: {len(plan.executable_trades)}")
    print(f"Skipped Trades: {len(plan.skipped_trades)}")
    print(f"Total Trades: {plan.total_trades}")
    print(f"Total Trade Value: ${plan.total_trade_value:,.2f}")
    print()

    # Show target positions
    print("Target Positions:")
    for pos in plan.target_positions:
        print(
            f"  {pos.coin:>5}: ${pos.target_value:>10,.2f} "
            f"({pos.weight:>6.1%}) - {pos.side}"
        )
    print()

    # =========================================================================
    # 4. Execute Plan and Create Result
    # =========================================================================
    print("4. Execution Result")
    print("-" * 80)

    # Simulate execution - BTC succeeds, ETH fails
    result = ExecutionResult(
        plan=plan,
        successful_trades=[btc_trade],
        failed_trades=[eth_trade],
        stop_losses_applied=1,
        stop_losses_failed=0,
    )

    print(f"Successful Trades: {len(result.successful_trades)}")
    print(f"Failed Trades: {len(result.failed_trades)}")
    print(f"Success Rate: {result.success_rate:.1%}")
    print(f"Stop Losses Applied: {result.stop_losses_applied}")
    print(f"Stop Losses Failed: {result.stop_losses_failed}")
    print()

    print("Successful Trades:")
    for trade in result.successful_trades:
        print(
            f"  {trade.coin:>5}: {trade.side.value.upper():>4} "
            f"{trade.size:>8.4f} @ ${trade.reference_price:>10,.2f}"
        )
    print()

    print("Failed Trades:")
    for trade in result.failed_trades:
        print(
            f"  {trade.coin:>5}: {trade.side.value.upper():>4} "
            f"{trade.size:>8.4f} @ ${trade.reference_price:>10,.2f}"
        )
    print()

    # =========================================================================
    # 5. Serialization Demo
    # =========================================================================
    print("5. Serialization")
    print("-" * 80)

    # Serialize plan to dict
    plan_dict = plan.model_dump()
    print(f"Plan serialized to dict with {len(plan_dict)} keys:")
    print(f"  Keys: {', '.join(plan_dict.keys())}")
    print()

    # Serialize result to JSON-compatible dict
    result_dict = result.model_dump(mode="json")
    print(f"Result serialized to JSON mode with {len(result_dict)} keys:")
    print(f"  Success rate: {result_dict['successful_trades']}")
    print()

    # =========================================================================
    # 6. Computed Properties Demo
    # =========================================================================
    print("6. Computed Properties")
    print("-" * 80)

    # Create a plan with all successful trades
    perfect_plan = RebalancePlan(
        account_value=Decimal("10000.00"),
        current_leverage=Decimal("0.5"),
        target_leverage=Decimal("1.0"),
        target_positions=[btc_position],
        executable_trades=[btc_trade],
    )

    perfect_result = ExecutionResult(plan=perfect_plan, successful_trades=[btc_trade])

    print("Perfect Execution:")
    print(f"  Total Trades: {perfect_plan.total_trades}")
    print(f"  Total Trade Value: ${perfect_plan.total_trade_value:,.2f}")
    print(f"  Success Rate: {perfect_result.success_rate:.0%}")
    print()

    # Create a plan with all failed trades
    failed_plan = RebalancePlan(
        account_value=Decimal("10000.00"),
        current_leverage=Decimal("0.5"),
        target_leverage=Decimal("1.0"),
        target_positions=[eth_position],
        executable_trades=[eth_trade],
    )

    failed_result = ExecutionResult(plan=failed_plan, successful_trades=[], failed_trades=[eth_trade])

    print("Failed Execution:")
    print(f"  Total Trades: {failed_plan.total_trades}")
    print(f"  Total Trade Value: ${failed_plan.total_trade_value:,.2f}")
    print(f"  Success Rate: {failed_result.success_rate:.0%}")
    print()

    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
