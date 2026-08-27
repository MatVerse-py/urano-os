"""URANO OS Kernel — local HTTP bridge.

The bridge exposes the existing kernel traversal, a DOI-first publication
resolver, and a user-mediated browser capture inbox. Browser authentication
stays inside Chrome: cookies, passwords, OAuth tokens and profile data are
never requested or copied into URANO.

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

from .browser_capture import BrowserCaptureStore
from .kernel import UranoKernel
from .publication_resolver import resolve_publication

REPO_ROOT = Path(__file__).resolve().parents[2]

_kernel_lock = threading.Lock()
_kernel: UranoKernel | None = None
_browser_captures = BrowserCaptureStore()


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
        "browser_capture_count": len(_browser_captures.list()),
    }


class BridgeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("[bridge] " + (fmt % args) + "\n")

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        if length > 2_000_000:
            return {}
        raw = self.rfile.read(length)
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return decoded if isinstance(decoded, dict) else {}

    def do_OPTIONS(self):
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

        if path == "/api/browser/captures":
            self._send_json(200, {"ok": True, "captures": _browser_captures.list()})
            return

        prefix = "/api/browser/capture/"
        if path.startswith(prefix):
            capture_id = path[len(prefix):]
            capture = _browser_captures.get(capture_id)
            if capture is None:
                self._send_json(404, {"ok": False, "error": "capture not found"})
            else:
                self._send_json(200, {"ok": True, "capture": capture})
            return

        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/publication/resolve":
            body = self._read_json_body()
            value = body.get("value")
            if not isinstance(value, str) or not value.strip():
                self._send_json(400, {"ok": False, "error": "value (DOI or URL containing DOI) required"})
                return
            result = resolve_publication(value.strip())
            self._send_json(200 if result.get("ok") else 422, result)
            return

        if path == "/api/browser/capture":
            body = self._read_json_body()
            capture_payload = body.get("capture")
            if not isinstance(capture_payload, dict):
                self._send_json(400, {"ok": False, "error": "capture (object) required"})
                return
            try:
                capture = _browser_captures.add(capture_payload)
            except ValueError as exc:
                self._send_json(400, {"ok": False, "error": str(exc)})
                return

            publication = None
            resolver_error = None
            if capture.doi:
                try:
                    publication = resolve_publication(capture.doi)
                except Exception as exc:  # network/API failure must not reject the capture itself
                    resolver_error = f"{type(exc).__name__}: {exc}"

            self._send_json(201, {
                "ok": True,
                "capture": capture.summary(),
                "publication": publication,
                "resolver_error": resolver_error,
                "policy": {
                    "browser_session": "remains_in_browser",
                    "credentials_received": False,
                    "cookies_received": False,
                    "capture_requires_user_action": True,
                },
            })
            return

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
    get_kernel()
    server = ThreadingHTTPServer(("127.0.0.1", port), BridgeHandler)
    print(f"[bridge] URANO kernel bridge on http://localhost:{port}")
    print(f"[bridge] OSX Surface: http://localhost:{port}/urano/URANO%20OSX.html")
    print("[bridge] Publication resolver: POST /api/publication/resolve")
    print("[bridge] Chrome capture inbox: POST /api/browser/capture")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
