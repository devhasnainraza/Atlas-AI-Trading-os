"""Trading account and position metrics (Spec 03 US3, T069).

Tracks:
- Sync age per connection (gauge in seconds, FR-019)
- Stale-view gauge (count of connections with stale account views)
- External-position discovery counter (positions discovered from outside Atlas, FR-017)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class AccountSyncMetrics:
    """Telemetry collector for account and position synchronization."""

    sync_ages_seconds: dict[str, float] = field(default_factory=dict)
    stale_connections: set[str] = field(default_factory=set)
    external_positions_discovered: int = 0

    def record_sync_age(self, connection_id: str, age_seconds: float) -> None:
        self.sync_ages_seconds[connection_id] = age_seconds

    def set_connection_stale(self, connection_id: str, is_stale: bool) -> None:
        if is_stale:
            self.stale_connections.add(connection_id)
        else:
            self.stale_connections.discard(connection_id)

    def record_external_position(self) -> None:
        self.external_positions_discovered += 1

    @property
    def stale_view_count(self) -> int:
        return len(self.stale_connections)

    def snapshot(self) -> dict[str, float | int]:
        max_age = max(self.sync_ages_seconds.values()) if self.sync_ages_seconds else 0.0
        return {
            "max_sync_age_seconds": max_age,
            "stale_view_count": self.stale_view_count,
            "external_positions_count": self.external_positions_discovered,
        }


# Global singleton instance
account_metrics = AccountSyncMetrics()

__all__ = ["AccountSyncMetrics", "account_metrics"]
