"""Pacote de evidências – coleta e selagem de provas."""
import hashlib
import json
from typing import List, Dict, Any
import time

from .evidence_gate import EvidenceClass

class EvidencePack:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.evidence: List[Dict] = []

    def add(self, source: str, data: Any, evidence_class: EvidenceClass = EvidenceClass.UNVERIFIED):
        self.evidence.append({
            "source": source,
            "data": data,
            "evidence_class": evidence_class.value,
            "timestamp": time.time()
        })

    def can_publish(self) -> bool:
        """CanPublish: nenhuma entrada UNVERIFIED pode sair como prova selada."""
        return all(e["evidence_class"] != EvidenceClass.UNVERIFIED.value for e in self.evidence)

    def seal(self, require_publishable: bool = False) -> str:
        if require_publishable and not self.can_publish():
            unverified = [e["source"] for e in self.evidence if e["evidence_class"] == EvidenceClass.UNVERIFIED.value]
            raise ValueError(f"CanPublish falhou: evidência UNVERIFIED em {unverified}")
        pack = {
            "session_id": self.session_id,
            "evidence": self.evidence,
            "sealed_at": time.time()
        }
        blob = json.dumps(pack, sort_keys=True).encode()
        return hashlib.sha3_256(blob).hexdigest()
