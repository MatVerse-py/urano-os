"""Gate de visão/voz – valida entrada e gera alertas."""
from typing import Dict, Any, Tuple

class CassandraGate:
    def __init__(self):
        self.voice_active = False

    def perceive(self, payload: Any) -> Tuple[bool, str]:
        # Regras simples de saneamento
        if isinstance(payload, str) and "CORRUPTED" in payload:
            return False, "QUARANTINE"
        if payload is None:
            return False, "NULL_INPUT"
        return True, "PASS"

    def speak(self, message: str):
        print(f"[CASSANDRA] {message}")
        self.voice_active = True
