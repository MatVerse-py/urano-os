"""URANO OS Kernel — HTTP bridge (dev-only).

Exposes a single running UranoKernel instance over a minimal local HTTP
API and serves the repo root as static files, so `urano/URANO OSX.html`
can perform one real, traceable traversal — intent -> event -> memory
hash-chain entry -> evidence -> receipt returned to the browser — instead
of only simulating one client-side.

This file is new and additive. It does not modify kernel.py,
event_runtime.py, cassandra_gate.py, memory_gate.py, or evidence_pack.py:
those remain exactly as they were (see urano/PROVENANCE.md).

There is no Ω-Gate / authority layer here — this bridge exposes the
`perception` and `action` event paths as they exist in the kernel today,
nothing more. propose -> gate -> authorize -> execute -> receipt is not
implemented; this is the perceive/act -> receipt slice only.

Run from the repo root:
    python3 -m src.urano_kernel.bridge [port]

Then open:
    http://localhost:8765/urano/URANO%20OSX.html
"""
from __future__ import annotations

import json
import sys
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from .kernel import UranoKernel

REPO_ROOT = Path(__file__).resolve().parents[2]

_kernel_lock = threading.Lock()
_kernel: UranoKernel | None = None


def get_kernel() -> UranoKernel:
    global _kernel
    if _kernel is None:
        _kernel = UranoKernel()
        _kernel.boot()
    return _kernel


def _state_snapshot(kernel: UranoKernel) -> dict:
    return {
        "session_id": kernel.session_id,
        "chain_length": len(kernel.memory.chain),
        "last_hash": kernel.memory.last_hash,
        "chain_verified": kernel.memory.verify(),
        "voice_active": kernel.cassandra.voice_active,
        "evidence_count": len(kernel.evidence.evidence),
    }


class BridgeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("[bridge] " + (fmt % args) + "\n")

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_OPTIONS(self):  # CORS preflight for cross-origin dev setups
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/state":
            with _kernel_lock:
                kernel = get_kernel()
                self._send_json(200, {"ok": True, "state": _state_snapshot(kernel)})
            return
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/perceive", "/api/act"):
            self._send_json(404, {"ok": False, "error": "no such route"})
            return

        body = self._read_json_body()
        payload = body.get("payload")
        if not payload or not isinstance(payload, str):
            self._send_json(400, {"ok": False, "error": "payload (string) required"})
            return

        event_type = "perception" if path == "/api/perceive" else "action"
        with _kernel_lock:
            kernel = get_kernel()
            chain_before = len(kernel.memory.chain)
            result = kernel.runtime.emit(event_type, payload)
            appended = len(kernel.memory.chain) > chain_before
            state = _state_snapshot(kernel)

        self._send_json(200, {
            "ok": True,
            "event_type": event_type,
            "result": result,
            "memory_appended": appended,
            "receipt_hash": state["last_hash"] if appended else None,
            "state": state,
        })


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    get_kernel()  # boot once up front so /api/state is meaningful immediately
    server = ThreadingHTTPServer(("127.0.0.1", port), BridgeHandler)
    print(f"[bridge] URANO kernel bridge on http://localhost:{port}")
    print(f"[bridge] OSX Surface: http://localhost:{port}/urano/URANO%20OSX.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
