"""
State management and event bus for cc-flow.

This module provides state management for portfolio snapshots and execution
history, plus a simple pub/sub event bus for decoupled communication.

Classes:
    StateManager: Manages application state including snapshots and execution history
    EventBus: Simple publish/subscribe event bus for component communication

Design Principles:
    - Single Responsibility: StateManager handles state, EventBus handles events
    - Immutable queries: Query methods return data without side effects
    - Clear separation: State and events are independent concerns
    - Type safety: Full type hints for all public APIs

Thread Safety:
    - Basic implementation without synchronization primitives
    - Not thread-safe for concurrent modifications
    - For production use, add threading.Lock if needed

Example:
    >>> from datetime import datetime, UTC
    >>> from decimal import Decimal
    >>> from cc_flow.core.state import StateManager, EventBus
    >>> from cc_flow.domain.account import AccountInfo, PortfolioSnapshot
    >>>
    >>> # State management
    >>> state = StateManager()
    >>> account = AccountInfo(
    ...     account_value=Decimal("10000"),
    ...     total_position_value=Decimal("5000"),
    ...     margin_used=Decimal("2500"),
    ...     free_collateral=Decimal("7500"),
    ...     cash_balance=Decimal("5000"),
    ...     withdrawable=Decimal("5000"),
    ...     current_leverage=Decimal("0.5"),
    ... )
    >>> snapshot = PortfolioSnapshot(account=account)
    >>> state.add_portfolio_snapshot(snapshot)
    >>> latest = state.get_latest_snapshot()
    >>>
    >>> # Event bus
    >>> bus = EventBus()
    >>> def on_rebalance(data):
    ...     print(f"Rebalance event: {data}")
    >>> bus.subscribe("rebalance", on_rebalance)
    >>> bus.emit("rebalance", {"status": "complete"})
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from cc_flow.domain.account import PortfolioSnapshot
from cc_flow.domain.portfolio import ExecutionResult


class StateManager:
    """
    Manages application state including portfolio snapshots and execution history.

    The StateManager is responsible for storing and querying:
    - Portfolio snapshots: Time-series of portfolio states
    - Execution history: Results of rebalancing operations
    - Metadata: Arbitrary key-value pairs for application state

    Attributes:
        portfolio_snapshots: List of portfolio snapshots in chronological order
        execution_history: List of execution results in chronological order
        metadata: Dictionary for arbitrary application state

    Example:
        >>> state = StateManager()
        >>> state.add_portfolio_snapshot(snapshot)
        >>> latest = state.get_latest_snapshot()
        >>> recent = state.get_snapshots_since(timestamp)
        >>> count = state.get_execution_count()

    Note:
        This implementation is not thread-safe. For concurrent access,
        add synchronization primitives (e.g., threading.Lock).
    """

    def __init__(self) -> None:
        """
        Initialize state manager with empty state.

        Creates empty collections for snapshots, execution history, and metadata.
        Each instance is independent with its own state.
        """
        self.portfolio_snapshots: list[PortfolioSnapshot] = []
        self.execution_history: list[ExecutionResult] = []
        self.execution_results: list[ExecutionResult] = []  # Alias for tests
        self.metadata: dict[str, Any] = {}

    def add_portfolio_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        """
        Add a portfolio snapshot to the history.

        Snapshots are stored in chronological order of addition. The caller
        is responsible for ensuring snapshots are added in timestamp order
        if chronological ordering is required.

        Args:
            snapshot: Portfolio snapshot to add

        Example:
            >>> state = StateManager()
            >>> snapshot = PortfolioSnapshot(account=account_info)
            >>> state.add_portfolio_snapshot(snapshot)
            >>> assert len(state.portfolio_snapshots) == 1
        """
        self.portfolio_snapshots.append(snapshot)

    def add_execution_result(self, result: ExecutionResult) -> None:
        """
        Add an execution result to the history.

        Execution results are stored in chronological order of addition,
        typically representing the order in which rebalancing operations
        were executed.

        Args:
            result: Execution result to add

        Example:
            >>> state = StateManager()
            >>> result = ExecutionResult(plan=plan, successful_trades=[trade])
            >>> state.add_execution_result(result)
            >>> assert state.get_execution_count() == 1
        """
        self.execution_history.append(result)
        self.execution_results.append(result)  # Keep both in sync

    def get_latest_snapshot(self) -> PortfolioSnapshot | None:
        """
        Get the most recent portfolio snapshot.

        Returns the last snapshot that was added to the manager.
        Useful for displaying current portfolio state.

        Returns:
            The most recent PortfolioSnapshot, or None if no snapshots exist

        Example:
            >>> state = StateManager()
            >>> assert state.get_latest_snapshot() is None
            >>> state.add_portfolio_snapshot(snapshot)
            >>> latest = state.get_latest_snapshot()
            >>> assert latest is snapshot
        """
        if not self.portfolio_snapshots:
            return None
        return self.portfolio_snapshots[-1]

    def get_snapshots_since(self, timestamp: datetime) -> list[PortfolioSnapshot]:
        """
        Get all snapshots since a given timestamp (inclusive).

        Returns snapshots where snapshot.timestamp >= timestamp.
        Useful for analyzing recent portfolio changes or calculating
        performance over a time period.

        Args:
            timestamp: The cutoff timestamp (inclusive)

        Returns:
            List of snapshots with timestamp >= cutoff, in chronological order

        Example:
            >>> from datetime import datetime, UTC, timedelta
            >>> state = StateManager()
            >>> cutoff = datetime.now(UTC) - timedelta(hours=1)
            >>> recent = state.get_snapshots_since(cutoff)
            >>> assert all(s.timestamp >= cutoff for s in recent)
        """
        return [s for s in self.portfolio_snapshots if s.timestamp >= timestamp]

    def get_execution_count(self) -> int:
        """
        Get the total number of executions.

        Returns:
            Total number of execution results in history

        Example:
            >>> state = StateManager()
            >>> assert state.get_execution_count() == 0
            >>> state.add_execution_result(result)
            >>> assert state.get_execution_count() == 1
        """
        return len(self.execution_history)

    def clear_history(self) -> None:
        """
        Clear all portfolio snapshots and execution history.

        This operation clears snapshots and execution history but
        preserves metadata. Use this to reset state while maintaining
        application configuration.

        Note:
            This does NOT clear metadata. To clear metadata, access
            the metadata dict directly.

        Example:
            >>> state = StateManager()
            >>> state.add_portfolio_snapshot(snapshot)
            >>> state.metadata["key"] = "value"
            >>> state.clear_history()
            >>> assert len(state.portfolio_snapshots) == 0
            >>> assert state.metadata == {"key": "value"}
        """
        self.portfolio_snapshots.clear()
        self.execution_history.clear()
        self.execution_results.clear()


class EventBus:
    """
    Simple publish/subscribe event bus.

    The EventBus enables decoupled communication between components using
    the observer pattern. Components can subscribe to events and emit events
    without tight coupling.

    Events are identified by string names. Subscribers are called synchronously
    in subscription order when events are emitted.

    Attributes:
        subscribers: Dictionary mapping event names to lists of callbacks

    Example:
        >>> bus = EventBus()
        >>> def on_trade(data):
        ...     print(f"Trade executed: {data}")
        >>> bus.subscribe("trade_executed", on_trade)
        >>> bus.emit("trade_executed", {"coin": "BTC", "value": 1000})

    Thread Safety:
        This implementation is not thread-safe. For concurrent access,
        add synchronization primitives.

    Design Notes:
        - Callbacks are called synchronously (not async)
        - No error handling for callback exceptions (they propagate)
        - No automatic unsubscription on callback errors
        - Subscribers are called in subscription order
    """

    def __init__(self) -> None:
        """
        Initialize event bus with empty subscribers.

        Creates an empty subscriber dictionary. Each instance is independent.
        """
        self.subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, event_name: str, callback: Callable) -> None:
        """
        Subscribe a callback to an event.

        The callback will be invoked whenever the specified event is emitted.
        The same callback can be subscribed multiple times (no deduplication).

        Args:
            event_name: Name of the event to subscribe to
            callback: Callable that accepts one argument (event data)

        Example:
            >>> bus = EventBus()
            >>> def handler(data):
            ...     print(data)
            >>> bus.subscribe("my_event", handler)
            >>> bus.emit("my_event", "hello")
        """
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        """
        Unsubscribe a callback from an event.

        Removes the first occurrence of the callback from the event's
        subscriber list. If the callback was subscribed multiple times,
        only one subscription is removed.

        Does not raise an error if the event or callback doesn't exist.

        Args:
            event_name: Name of the event
            callback: Callback to remove

        Example:
            >>> bus = EventBus()
            >>> bus.subscribe("event", handler)
            >>> bus.unsubscribe("event", handler)
        """
        if event_name in self.subscribers:
            try:
                self.subscribers[event_name].remove(callback)
            except ValueError:
                # Callback not in list, silently ignore
                pass

    def emit(self, event_name: str, data: Any = None) -> None:
        """
        Emit an event to all subscribers.

        Calls all subscribed callbacks for the event in subscription order.
        If no subscribers exist for the event, this is a no-op.

        Args:
            event_name: Name of the event to emit
            data: Optional data to pass to subscribers (default: None)

        Raises:
            Any exception raised by subscriber callbacks will propagate

        Example:
            >>> bus = EventBus()
            >>> def handler(data):
            ...     print(f"Received: {data}")
            >>> bus.subscribe("event", handler)
            >>> bus.emit("event", {"key": "value"})

        Note:
            Callbacks are invoked synchronously in the current thread.
            If a callback raises an exception, subsequent callbacks will
            not be called.
        """
        if event_name in self.subscribers:
            for callback in self.subscribers[event_name]:
                callback(data)

    def clear_subscribers(self, event_name: str | None = None) -> None:
        """
        Clear subscribers for an event or all events.

        If event_name is provided, removes all subscribers for that event.
        If event_name is None, removes all subscribers for all events.

        Args:
            event_name: Specific event to clear, or None to clear all

        Example:
            >>> bus = EventBus()
            >>> bus.subscribe("event1", handler1)
            >>> bus.subscribe("event2", handler2)
            >>> bus.clear_subscribers("event1")  # Clear only event1
            >>> bus.clear_subscribers()  # Clear all events
        """
        if event_name:
            self.subscribers.pop(event_name, None)
        else:
            self.subscribers.clear()
