"""Memória causal – ledger em memória com hash chain."""
import hashlib
import json
from typing import List, Dict, Any
import time

class MemoryGate:
    def __init__(self):
        self.chain: List[Dict] = []
        self.last_hash = "0" * 64

    def append(self, data: Dict) -> str:
        entry = {
            "data": data,
            "prev_hash": self.last_hash,
            "timestamp": time.time()
        }
        blob = json.dumps(entry, sort_keys=True).encode()
        entry_hash = hashlib.sha256(blob).hexdigest()
        entry["hash"] = entry_hash
        self.chain.append(entry)
        self.last_hash = entry_hash
        return entry_hash

    def verify(self) -> bool:
        prev = "0" * 64
        for e in self.chain:
            if e["prev_hash"] != prev:
                return False
            blob = json.dumps({k:v for k,v in e.items() if k!="hash"}, sort_keys=True).encode()
            if hashlib.sha256(blob).hexdigest() != e["hash"]:
                return False
            prev = e["hash"]
        return True
