"""State management components."""

from typing import Protocol, Any
import json
from pathlib import Path


class StateManager(Protocol):
    """Interface for managing strategy state across rebalances.

    State managers handle persistence of strategy-specific data:
    - Vintages (for rolling mode)
    - Entry times (for time-based exits)
    - Peak prices (for trailing stops)
    - Custom strategy metadata
    """

    def get_state(self) -> dict[str, Any]:
        """Retrieve current state.

        Returns:
            State dictionary
        """
        ...

    def update_state(self, updates: dict[str, Any]) -> None:
        """Update state with new data.

        Args:
            updates: Dict of state updates to merge
        """
        ...

    def clear_state(self) -> None:
        """Clear all state (useful for reset/testing)."""
        ...


class NoOpState:
    """No-op state manager for stateless strategies.

    Used by FULL MODE - no state needed between rebalances.
    """

    def get_state(self) -> dict[str, Any]:
        """Return empty state."""
        return {}

    def update_state(self, updates: dict[str, Any]) -> None:
        """Ignore state updates."""
        pass

    def clear_state(self) -> None:
        """Nothing to clear."""
        pass


class VintageState:
    """State manager for vintage-based strategies.

    Used by ROLLING MODE - persists vintages to disk.
    Stores vintage creation dates and positions in JSON.
    """

    def __init__(self, state_file: str = ".cc-liquid-state.json"):
        """
        Args:
            state_file: Path to state file (relative to config directory)
        """
        self.state_file = Path(state_file)
        self._state: dict[str, Any] = {}
        self._load_from_file()

    def get_state(self) -> dict[str, Any]:
        """Load and return current state."""
        return self._state.copy()

    def update_state(self, updates: dict[str, Any]) -> None:
        """Update state and persist to disk."""
        self._state.update(updates)
        self._save_to_file()

    def clear_state(self) -> None:
        """Clear state and delete file."""
        self._state = {}
        if self.state_file.exists():
            self.state_file.unlink()

    def _load_from_file(self) -> None:
        """Load state from JSON file."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    self._state = json.load(f)
            except Exception as e:
                # If file is corrupted, start fresh
                self._state = {}

    def _save_to_file(self) -> None:
        """Persist state to JSON file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            # Log but don't fail on save errors
            pass


class InMemoryState:
    """In-memory state manager for testing.

    Doesn't persist to disk - useful for unit tests and backtesting.
    """

    def __init__(self):
        self._state: dict[str, Any] = {}

    def get_state(self) -> dict[str, Any]:
        """Return current state."""
        return self._state.copy()

    def update_state(self, updates: dict[str, Any]) -> None:
        """Update state in memory."""
        self._state.update(updates)

    def clear_state(self) -> None:
        """Clear state."""
        self._state = {}


class DatabaseState:
    """Database-backed state manager for production systems.

    Example of how you could persist to a database instead of JSON.
    Useful for multi-instance deployments or cloud environments.
    """

    def __init__(self, db_url: str, table_name: str = "strategy_state"):
        """
        Args:
            db_url: Database connection string
            table_name: Table to store state
        """
        self.db_url = db_url
        self.table_name = table_name
        # In practice, initialize DB connection here

    def get_state(self) -> dict[str, Any]:
        """Fetch state from database."""
        # Pseudo-code:
        # conn = connect(self.db_url)
        # result = conn.execute(f"SELECT state FROM {self.table_name}")
        # return json.loads(result['state'])
        return {}

    def update_state(self, updates: dict[str, Any]) -> None:
        """Persist state to database."""
        # Pseudo-code:
        # current = self.get_state()
        # current.update(updates)
        # conn = connect(self.db_url)
        # conn.execute(
        #     f"UPDATE {self.table_name} SET state = ?",
        #     json.dumps(current)
        # )
        pass

    def clear_state(self) -> None:
        """Clear database state."""
        # conn.execute(f"DELETE FROM {self.table_name}")
        pass
