"""
Example usage of StateManager and EventBus.

This example demonstrates how to use the StateManager for tracking portfolio
state and execution history, and the EventBus for decoupled event communication.

Run with: uv run python -m cc_flow.examples.state_manager_example
(from the parent directory of cc_flow)
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import cc_flow
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from cc_flow.core.state import EventBus, StateManager
from cc_flow.domain.account import AccountInfo, PortfolioSnapshot, Position
from cc_flow.domain.orders import OrderSide, Trade
from cc_flow.domain.portfolio import ExecutionResult, RebalancePlan, TargetPosition


def example_state_manager():
    """Demonstrate StateManager usage."""
    print("=" * 60)
    print("StateManager Example")
    print("=" * 60)

    # Create a state manager
    state = StateManager()
    print("\nCreated StateManager instance")

    # Add some metadata
    state.metadata["strategy"] = "momentum"
    state.metadata["rebalance_frequency"] = "daily"
    print(f"Metadata: {state.metadata}")

    # Create some portfolio snapshots
    print("\n" + "-" * 60)
    print("Adding portfolio snapshots...")

    for i in range(3):
        account = AccountInfo(
            account_value=Decimal("10000") + Decimal(i * 100),
            total_position_value=Decimal("5000") + Decimal(i * 50),
            margin_used=Decimal("2500"),
            free_collateral=Decimal("7500"),
            cash_balance=Decimal("5000"),
            withdrawable=Decimal("5000"),
            current_leverage=Decimal("0.5"),
        )

        position = Position(
            coin="BTC",
            side="LONG",
            size=Decimal("1.0"),
            entry_price=Decimal("50000"),
            mark_price=Decimal("50000") + Decimal(i * 1000),
            value=Decimal("50000") + Decimal(i * 1000),
            unrealized_pnl=Decimal(i * 1000),
            return_pct=Decimal("0.02") * i,
        )

        snapshot = PortfolioSnapshot(
            timestamp=datetime.now(UTC) - timedelta(hours=3 - i),
            account=account,
            positions=[position],
        )

        state.add_portfolio_snapshot(snapshot)
        print(f"  Snapshot {i + 1}: Account value = ${account.account_value}, "
              f"Unrealized P&L = ${position.unrealized_pnl}")

    print(f"\nTotal snapshots: {len(state.portfolio_snapshots)}")

    # Query latest snapshot
    print("\n" + "-" * 60)
    print("Getting latest snapshot...")
    latest = state.get_latest_snapshot()
    if latest:
        print(f"  Account value: ${latest.account.account_value}")
        print(f"  Timestamp: {latest.timestamp}")
        print(f"  Total unrealized P&L: ${latest.total_unrealized_pnl}")

    # Query snapshots since a time
    print("\n" + "-" * 60)
    print("Getting snapshots from last 2 hours...")
    cutoff = datetime.now(UTC) - timedelta(hours=2)
    recent = state.get_snapshots_since(cutoff)
    print(f"  Found {len(recent)} snapshots since {cutoff}")

    # Add execution result
    print("\n" + "-" * 60)
    print("Adding execution result...")

    target = TargetPosition(
        coin="BTC",
        target_value=Decimal("5000"),
        weight=Decimal("0.5"),
    )

    trade = Trade(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("0.1"),
        reference_price=Decimal("50000"),
        current_value=Decimal("0"),
        target_value=Decimal("5000"),
        delta_value=Decimal("5000"),
        trade_type="open",
        estimated_fee=Decimal("2.50"),
    )

    plan = RebalancePlan(
        account_value=Decimal("10000"),
        current_leverage=Decimal("0.0"),
        target_leverage=Decimal("0.5"),
        target_positions=[target],
        executable_trades=[trade],
    )

    result = ExecutionResult(
        plan=plan,
        successful_trades=[trade],
    )

    state.add_execution_result(result)
    print(f"  Execution count: {state.get_execution_count()}")
    print(f"  Success rate: {result.success_rate:.1%}")

    # Clear history
    print("\n" + "-" * 60)
    print("Clearing history...")
    state.clear_history()
    print(f"  Snapshots: {len(state.portfolio_snapshots)}")
    print(f"  Executions: {len(state.execution_history)}")
    print(f"  Metadata preserved: {state.metadata}")


def example_event_bus():
    """Demonstrate EventBus usage."""
    print("\n" + "=" * 60)
    print("EventBus Example")
    print("=" * 60)

    # Create event bus
    bus = EventBus()
    print("\nCreated EventBus instance")

    # Subscribe to events
    print("\n" + "-" * 60)
    print("Subscribing to events...")

    received_events = []

    def on_trade_executed(data):
        received_events.append(("trade", data))
        print(f"  [TRADE HANDLER] Trade executed: {data['coin']} - ${data['value']}")

    def on_rebalance_started(data):
        received_events.append(("rebalance_start", data))
        print(f"  [REBALANCE HANDLER] Starting rebalance with {data['num_trades']} trades")

    def on_rebalance_completed(data):
        received_events.append(("rebalance_complete", data))
        print(f"  [REBALANCE HANDLER] Rebalance complete - Success rate: {data['success_rate']:.1%}")

    bus.subscribe("trade_executed", on_trade_executed)
    bus.subscribe("rebalance_started", on_rebalance_started)
    bus.subscribe("rebalance_completed", on_rebalance_completed)

    print(f"  Subscribed to {len(bus.subscribers)} event types")

    # Emit events
    print("\n" + "-" * 60)
    print("Emitting events...")

    bus.emit("rebalance_started", {"num_trades": 5})

    for coin in ["BTC", "ETH", "SOL"]:
        bus.emit("trade_executed", {"coin": coin, "value": 1000 * (ord(coin[0]) - 64)})

    bus.emit("rebalance_completed", {"success_rate": 1.0})

    print(f"\n  Total events received: {len(received_events)}")

    # Multiple subscribers to same event
    print("\n" + "-" * 60)
    print("Testing multiple subscribers...")

    def logger1(data):
        print(f"  [LOGGER 1] {data}")

    def logger2(data):
        print(f"  [LOGGER 2] {data}")

    def logger3(data):
        print(f"  [LOGGER 3] {data}")

    bus.subscribe("log_event", logger1)
    bus.subscribe("log_event", logger2)
    bus.subscribe("log_event", logger3)

    print(f"  Subscribed {len(bus.subscribers['log_event'])} handlers to 'log_event'")
    print("  Emitting event...")
    bus.emit("log_event", "Test message")

    # Unsubscribe
    print("\n" + "-" * 60)
    print("Testing unsubscribe...")

    bus.unsubscribe("log_event", logger2)
    print(f"  Remaining subscribers: {len(bus.subscribers['log_event'])}")
    print("  Emitting event again...")
    bus.emit("log_event", "Test after unsubscribe")

    # Clear subscribers
    print("\n" + "-" * 60)
    print("Clearing subscribers...")

    bus.clear_subscribers("log_event")
    print(f"  Subscribers for 'log_event': {len(bus.subscribers.get('log_event', []))}")

    bus.clear_subscribers()
    print(f"  Total event types: {len(bus.subscribers)}")


def example_combined_usage():
    """Demonstrate using StateManager and EventBus together."""
    print("\n" + "=" * 60)
    print("Combined Usage Example")
    print("=" * 60)

    # Create both components
    state = StateManager()
    bus = EventBus()
    print("\nCreated StateManager and EventBus instances")

    # Subscribe to events that update state
    def on_snapshot_received(data):
        snapshot = data["snapshot"]
        state.add_portfolio_snapshot(snapshot)
        print(f"  [STATE] Added snapshot - Total: {len(state.portfolio_snapshots)}")

    def on_execution_completed(data):
        result = data["result"]
        state.add_execution_result(result)
        print(f"  [STATE] Added execution - Total: {state.get_execution_count()}")
        print(f"  [STATE] Success rate: {result.success_rate:.1%}")

    bus.subscribe("snapshot_received", on_snapshot_received)
    bus.subscribe("execution_completed", on_execution_completed)

    # Simulate workflow
    print("\n" + "-" * 60)
    print("Simulating trading workflow...")

    # Get portfolio snapshot
    account = AccountInfo(
        account_value=Decimal("10000"),
        total_position_value=Decimal("0"),
        margin_used=Decimal("0"),
        free_collateral=Decimal("10000"),
        cash_balance=Decimal("10000"),
        withdrawable=Decimal("10000"),
        current_leverage=Decimal("0"),
    )
    snapshot = PortfolioSnapshot(account=account)

    print("\n1. Portfolio snapshot received")
    bus.emit("snapshot_received", {"snapshot": snapshot})

    # Execute rebalance
    target = TargetPosition(
        coin="BTC",
        target_value=Decimal("5000"),
        weight=Decimal("0.5"),
    )

    trade = Trade(
        coin="BTC",
        side=OrderSide.BUY,
        size=Decimal("0.1"),
        reference_price=Decimal("50000"),
        current_value=Decimal("0"),
        target_value=Decimal("5000"),
        delta_value=Decimal("5000"),
        trade_type="open",
        estimated_fee=Decimal("2.50"),
    )

    plan = RebalancePlan(
        account_value=Decimal("10000"),
        current_leverage=Decimal("0.0"),
        target_leverage=Decimal("0.5"),
        target_positions=[target],
        executable_trades=[trade],
    )

    result = ExecutionResult(
        plan=plan,
        successful_trades=[trade],
    )

    print("\n2. Execution completed")
    bus.emit("execution_completed", {"result": result})

    # Query state
    print("\n" + "-" * 60)
    print("Querying state...")
    print(f"  Total snapshots: {len(state.portfolio_snapshots)}")
    print(f"  Total executions: {state.get_execution_count()}")
    print(f"  Latest account value: ${state.get_latest_snapshot().account.account_value}")


if __name__ == "__main__":
    example_state_manager()
    example_event_bus()
    example_combined_usage()

    print("\n" + "=" * 60)
    print("Examples completed successfully!")
    print("=" * 60)
