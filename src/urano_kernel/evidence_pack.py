"""Pacote de evidências – coleta e selagem de provas."""
import hashlib
import json
from typing import List, Dict, Any
import time

class EvidencePack:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.evidence: List[Dict] = []

    def add(self, source: str, data: Any):
        self.evidence.append({
            "source": source,
            "data": data,
            "timestamp": time.time()
        })

    def seal(self) -> str:
        pack = {
            "session_id": self.session_id,
            "evidence": self.evidence,
            "sealed_at": time.time()
        }
        blob = json.dumps(pack, sort_keys=True).encode()
        return hashlib.sha3_256(blob).hexdigest()
