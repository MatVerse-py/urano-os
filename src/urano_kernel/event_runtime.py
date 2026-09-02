"""Event-driven runtime with explicit payload-retention policy."""

from dataclasses import dataclass
from typing import Callable, Dict, Any
import hashlib
import json
import time
import uuid


@dataclass
class Event:
    id: str
    type: str
    payload: Any
    timestamp: float


class EventRuntime:
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.history: list[Event] = []
        self._retain_payload: Dict[str, bool] = {}

    @staticmethod
    def _payload_digest(payload: Any) -> str:
        blob = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def register(self, event_type: str, handler: Callable, *, retain_payload: bool = True):
        self.handlers[event_type] = handler
        self._retain_payload[event_type] = retain_payload

    def emit(self, event_type: str, payload: Any) -> Any:
        timestamp = time.time()
        event_id = uuid.uuid4().hex[:16]
        handler_event = Event(
            id=event_id,
            type=event_type,
            payload=payload,
            timestamp=timestamp,
        )

        retain_payload = self._retain_payload.get(event_type, True)
        history_payload = payload
        if not retain_payload:
            history_payload = {
                "redacted": True,
                "payload_sha256": self._payload_digest(payload),
            }

        self.history.append(
            Event(
                id=event_id,
                type=event_type,
                payload=history_payload,
                timestamp=timestamp,
            )
        )
        if event_type in self.handlers:
            return self.handlers[event_type](handler_event)
        return None
