"""Event-driven runtime – processa intenções e orquestra fluxo."""
from dataclasses import dataclass
from typing import Callable, Dict, Any
import hashlib
import time

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

    def register(self, event_type: str, handler: Callable):
        self.handlers[event_type] = handler

    def emit(self, event_type: str, payload: Any) -> Any:
        event = Event(
            id=hashlib.md5(f"{event_type}{time.time()}".encode()).hexdigest()[:8],
            type=event_type,
            payload=payload,
            timestamp=time.time()
        )
        self.history.append(event)
        if event_type in self.handlers:
            return self.handlers[event_type](event)
        return None
