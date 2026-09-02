"""URANO OS Kernel v0.5 - Operational Core."""
from .event_runtime import EventRuntime
from .cassandra_gate import CassandraGate
from .memory_gate import MemoryGate
from .evidence_pack import EvidencePack
from .evidence_gate import EvidenceClass
import uuid

class UranoKernel:
    def __init__(self):
        self.runtime = EventRuntime()
        self.cassandra = CassandraGate()
        self.memory = MemoryGate()
        self.session_id = str(uuid.uuid4())
        self.evidence = EvidencePack(self.session_id)
        
        # Registro de handlers básicos
        self.runtime.register("perception", self._handle_perception)
        self.runtime.register("action", self._handle_action)

    def _handle_perception(self, event):
        ok, status = self.cassandra.perceive(event.payload)
        # status é resultado de um cálculo do gate, não texto observado bruto.
        self.evidence.add("cassandra_gate", {"input": event.payload, "status": status}, EvidenceClass.COMPUTED)
        if ok:
            self.memory.append({"event": "perception", "payload": event.payload})
            return f"PERCEPTION_OK: {status}"
        return f"PERCEPTION_FAILED: {status}"

    def _handle_action(self, event):
        self.cassandra.speak(f"Executing action: {event.payload}")
        self.memory.append({"event": "action", "payload": event.payload})
        # payload é o texto de entrada tal como recebido no evento.
        self.evidence.add("action_log", event.payload, EvidenceClass.OBSERVED_TEXT)
        return "ACTION_EXECUTED"

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
    print(f"Evidence Seal: {kernel.evidence.seal(require_publishable=True)}")
