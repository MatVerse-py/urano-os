"""URANO OS Kernel v0.5 - Operational Core."""

from hashlib import sha256
import uuid

from .event_runtime import EventRuntime
from .cassandra_gate import CassandraGate
from .memory_gate import MemoryGate
from .evidence_pack import EvidencePack
from .argus_argos import (
    ArgusPipeline,
    BridgeProtocolError,
    ClaimCandidate,
    EvidenceRetriever,
    SourceDocument,
)


class UranoKernel:
    def __init__(self, *, argus_retriever: EvidenceRetriever | None = None):
        self.runtime = EventRuntime()
        self.cassandra = CassandraGate()
        self.memory = MemoryGate()
        self.session_id = str(uuid.uuid4())
        self.evidence = EvidencePack(self.session_id)
        self.argus_pipeline = ArgusPipeline(retriever=argus_retriever)

        # Existing handlers preserve legacy behavior. ARGUS payloads are marked
        # non-retained because they may contain sensitive documents/media.
        self.runtime.register("perception", self._handle_perception)
        self.runtime.register("action", self._handle_action)
        self.runtime.register("argus_case", self._handle_argus_case, retain_payload=False)
        self.runtime.register("argus_document", self._handle_argus_document, retain_payload=False)

    def _handle_perception(self, event):
        ok, status = self.cassandra.perceive(event.payload)
        self.evidence.add("cassandra_gate", {"input": event.payload, "status": status})
        if ok:
            self.memory.append({"event": "perception", "payload": event.payload})
            return f"PERCEPTION_OK: {status}"
        return f"PERCEPTION_FAILED: {status}"

    def _handle_action(self, event):
        self.cassandra.speak(f"Executing action: {event.payload}")
        self.memory.append({"event": "action", "payload": event.payload})
        self.evidence.add("action_log", event.payload)
        return "ACTION_EXECUTED"

    @staticmethod
    def _source_from_payload(item: dict) -> SourceDocument:
        if not isinstance(item, dict):
            raise ValueError("evidence entries must be objects")
        return SourceDocument(
            locator=str(item.get("locator") or ""),
            representation=str(item.get("representation") or ""),
            content=item.get("content", ""),
            metadata=dict(item.get("metadata") or {}),
            expected_sha256=item.get("expected_sha256"),
            evidence_root_id=item.get("evidence_root_id"),
        )

    @staticmethod
    def _decision_summary(result) -> dict:
        return {
            "claim_ref": result.claim.claim_ref,
            "claim_sha256": result.finding.content_hash,
            "finding_id": result.finding.finding_id,
            "finding_type": result.finding.finding_type.value,
            "governance_state": result.governance.state.value,
            "governance_reasons": tuple(result.governance.reasons),
            "authority": result.finding.authority.as_dict(),
            "evidence_root_count": result.evidence_root_count,
            "independent_root_count": result.independent_root_count,
            "support_root_count": result.support_root_count,
            "contradiction_root_count": result.contradiction_root_count,
            "evidence_root_ids": result.evidence_root_ids,
        }

    def _record_argus_summary(self, summary: dict) -> None:
        # Intentionally records only hashes/decisions/root ids, never raw claim or
        # evidence content. This keeps operational replay material without
        # duplicating sensitive source material inside URANO memory.
        self.evidence.add("argus_argos_decision", summary)
        self.memory.append({"event": "argus_argos_decision", "summary": summary})

    def _blocked_argus_result(self, reason: str) -> dict:
        summary = {
            "governance_state": "BLOCK",
            "governance_reasons": (reason,),
        }
        self._record_argus_summary(summary)
        return summary

    def _held_argus_result(self, reason: str) -> dict:
        summary = {
            "governance_state": "HOLD",
            "governance_reasons": (reason,),
        }
        self._record_argus_summary(summary)
        return summary

    def _handle_argus_case(self, event):
        payload = event.payload
        if not isinstance(payload, dict):
            return self._blocked_argus_result("MALFORMED_ARGUS_CASE")

        claim_text = str(payload.get("claim") or "").strip()
        if not claim_text:
            return self._blocked_argus_result("MISSING_CLAIM")

        try:
            evidence = tuple(
                self._source_from_payload(item)
                for item in tuple(payload.get("evidence") or ())
            )
        except (TypeError, ValueError):
            return self._blocked_argus_result("MALFORMED_EVIDENCE")

        claim_ref = str(payload.get("claim_ref") or "").strip()
        if not claim_ref:
            digest = sha256(claim_text.encode("utf-8")).hexdigest()[:24]
            claim_ref = f"claim://runtime-{digest}"

        source_ref = str(payload.get("source_ref") or "runtime://argus-case")
        claim = ClaimCandidate(
            claim_ref=claim_ref,
            text=claim_text,
            source_ref=source_ref,
            ordinal=1,
        )
        try:
            result = self.argus_pipeline.analyze_claim(claim=claim, evidence=evidence)
        except BridgeProtocolError:
            return self._held_argus_result("BRIDGE_RETRIEVAL_UNAVAILABLE")
        summary = self._decision_summary(result)
        self._record_argus_summary(summary)
        return summary

    def _handle_argus_document(self, event):
        payload = event.payload
        if not isinstance(payload, dict):
            return self._blocked_argus_result("MALFORMED_ARGUS_DOCUMENT")
        document_data = payload.get("document")
        if not isinstance(document_data, dict):
            return self._blocked_argus_result("MISSING_DOCUMENT")

        try:
            document = self._source_from_payload(document_data)
            evidence = tuple(
                self._source_from_payload(item)
                for item in tuple(payload.get("evidence") or ())
            )
            results = self.argus_pipeline.analyze_document(document, evidence=evidence)
        except BridgeProtocolError:
            return self._held_argus_result("BRIDGE_RETRIEVAL_UNAVAILABLE")
        except (TypeError, ValueError):
            return self._blocked_argus_result("MALFORMED_DOCUMENT_OR_EVIDENCE")

        summaries = tuple(self._decision_summary(result) for result in results)
        for summary in summaries:
            self._record_argus_summary(summary)
        return {
            "document_sha256": sha256(
                document.content if isinstance(document.content, bytes) else document.content.encode("utf-8")
            ).hexdigest(),
            "claim_count": len(summaries),
            "results": summaries,
        }

    def boot(self):
        self.cassandra.speak("URANO OS Kernel v0.5 Booting...")
        self.memory.append({"event": "system_boot", "status": "online"})
        self.cassandra.speak(f"Session ID: {self.session_id}")
        return True


if __name__ == "__main__":
    kernel = UranoKernel()
    kernel.boot()
    kernel.runtime.emit("perception", "Observing digital life cycle")
    kernel.runtime.emit("action", "Initializing primary ledger link")
    print(f"Evidence Seal: {kernel.evidence.seal()}")
