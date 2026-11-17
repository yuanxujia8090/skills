#!/usr/bin/env python3
"""Offline smoke test: no real image API call, no cost, no network egress.

Starts a local mock server that answers /images/generations (b64) and
/images/edits (url download), then runs the real script against it.

  python3 scripts/test_smoke.py
"""
from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT = Path(__file__).with_name("generate_image.py")
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep test output clean
        pass

    def _json(self, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/file.png":
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(PNG)))
            self.end_headers()
            self.wfile.write(PNG)
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        assert self.headers.get("Authorization", "").startswith("Bearer "), "missing bearer token"
        if self.path.endswith("/images/generations"):
            payload = json.loads(body)
            assert payload["model"] and payload["prompt"], "prompt/model missing"
            self._json({"data": [{"b64_json": base64.b64encode(PNG).decode()}]})
        elif self.path.endswith("/images/edits"):
            assert b"image" in body, "reference image not uploaded"
            self._json({"data": [{"url": f"http://127.0.0.1:{self.server.server_port}/file.png"}]})
        else:
            self.send_error(404)


def run(args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=120
    )


def main() -> int:
    port = free_port()
    server = HTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        env = dict(os.environ)
        env.update({
            "OPENIMAGE_API_KEY": "test-key",
            "OPENIMAGE_BASE_URL": f"http://127.0.0.1:{port}/v1",
            "OPENIMAGE_MODEL": "mock-model",
            "OPENIMAGE_TIMEOUT_MS": "20000",
            "YXJ_IMAGEGEN_CONFIG": str(tmpdir / "missing.json"),
        })

        # 1. config resolution, no API call
        shown = run(["--show-config"], env)
        if shown.returncode != 0:
            print(f"FAIL show-config exit={shown.returncode}\n{shown.stderr}")
            failures += 1
        else:
            cfg = json.loads(shown.stdout)
            print(f"ok   show-config baseUrl={cfg['baseUrl']} model={cfg['model']} keyFromEnv={cfg['keyFromEnv']}")
            if cfg["model"] != "mock-model" or not cfg["baseUrl"].endswith(f":{port}/v1"):
                print("FAIL env overrides not applied")
                failures += 1

        # 2. text-to-image, b64 response
        out1 = tmpdir / "out" / "01-gen.png"
        res = run(["--prompt", "a small paper funnel on a desk", "--size", "1024x1024", "--out", str(out1)], env)
        if res.returncode != 0:
            print(f"FAIL generate exit={res.returncode}\n{res.stderr}")
            failures += 1
        elif not out1.exists() or out1.read_bytes() != PNG:
            print("FAIL generate wrote unexpected bytes")
            failures += 1
        else:
            print(f"ok   generate {json.loads(res.stdout)['path']} ({out1.stat().st_size} bytes)")

        # 3. edit with reference image, url response
        ref = tmpdir / "ref.jpg"
        ref.write_bytes(b"\xff\xd8\xff\xe0reference")
        out2 = tmpdir / "out" / "02-edit.png"
        res = run(["--prompt", "keep identity, change the scene", "--image", str(ref), "--out", str(out2)], env)
        if res.returncode != 0:
            print(f"FAIL edit exit={res.returncode}\n{res.stderr}")
            failures += 1
        elif not out2.exists() or out2.read_bytes() != PNG:
            print("FAIL edit did not save downloaded url bytes")
            failures += 1
        else:
            print(f"ok   edit {json.loads(res.stdout)['mode']} -> {out2.name}")

        # 4. missing prompt is a usage error, not a crash
        if run(["--out", str(tmpdir / "x.png")], env).returncode == 0:
            print("FAIL missing --prompt should fail")
            failures += 1
        else:
            print("ok   missing --prompt rejected")

    server.shutdown()
    print("SMOKE " + ("PASS" if failures == 0 else f"FAIL ({failures})"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
