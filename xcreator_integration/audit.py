"""Small audit log abstraction used by assistant and OCR flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .redaction import redact


@dataclass(frozen=True)
class AuditEvent:
    kind: str
    payload: dict[str, Any]
    created_at: datetime


class InMemoryAuditLog:
    """Test and local-fixture audit log that always stores redacted payloads."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        created_at: datetime | None = None,
    ) -> None:
        self.events.append(
            AuditEvent(
                kind=kind,
                payload=redact(payload),
                created_at=created_at or datetime.now(timezone.utc),
            )
        )

    def purge_older_than(self, max_age: timedelta, *, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        before = len(self.events)
        self.events = [event for event in self.events if now - event.created_at <= max_age]
        return before - len(self.events)

