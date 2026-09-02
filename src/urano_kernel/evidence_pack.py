"""Pacote de evidências – coleta e selagem de provas."""
import hashlib
import json
from typing import List, Dict, Any
import time

from .evidence_gate import EvidenceClass, PUBLISHABLE


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
        """CanPublish: toda entrada deve possuir classe mecanicamente verificável."""
        for entry in self.evidence:
            try:
                evidence_class = EvidenceClass(entry["evidence_class"])
            except (KeyError, ValueError, TypeError):
                return False
            if evidence_class not in PUBLISHABLE:
                return False
        return True

    def seal(self, require_publishable: bool = False) -> str:
        if require_publishable and not self.can_publish():
            blocked = [
                e.get("source", "")
                for e in self.evidence
                if e.get("evidence_class") not in {c.value for c in PUBLISHABLE}
            ]
            raise ValueError(f"CanPublish falhou: evidência não-publicável em {blocked}")
        pack = {
            "session_id": self.session_id,
            "evidence": self.evidence,
            "sealed_at": time.time()
        }
        blob = json.dumps(pack, sort_keys=True).encode()
        return hashlib.sha3_256(blob).hexdigest()
