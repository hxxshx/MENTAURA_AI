"""
Session manager — in-memory store of per-victim pulse history.
Used for escalation detection across multiple turns.
"""

from collections import defaultdict
from datetime import datetime
from typing import Optional

from schemas.distress import DistressResult


class SessionManager:
    """
    In-memory per-victim state. Stores recent distress results so
    escalation detection has history to work with.

    In production this would be Redis or a DB. For hackathon, in-memory
    is fine — it's fast and demonstrates the concept.
    """

    def __init__(self, max_history: int = 10):
        self._history: dict[str, list[DistressResult]] = defaultdict(list)
        self._max_history = max_history

    def add_distress_result(
        self, victim_id: str, result: DistressResult
    ) -> None:
        """Append a distress result to the victim's history."""
        self._history[victim_id].append(result)
        # Trim to max
        if len(self._history[victim_id]) > self._max_history:
            self._history[victim_id] = self._history[victim_id][-self._max_history:]

    def get_history(self, victim_id: str) -> list[DistressResult]:
        """Return recent distress results (oldest → newest)."""
        return list(self._history.get(victim_id, []))

    def clear(self, victim_id: str) -> None:
        """Clear history for a victim (e.g., case closed)."""
        self._history.pop(victim_id, None)

    def clear_all(self) -> None:
        """Reset everything (used in tests)."""
        self._history.clear()

    def victim_count(self) -> int:
        """How many victims are being tracked."""
        return len(self._history)


# Singleton
_manager_instance: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SessionManager()
    return _manager_instance