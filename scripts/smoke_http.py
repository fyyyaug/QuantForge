"""Exercise a real loopback HTTP server without saving or printing credentials."""

import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent


def main():
    token = secrets.token_urlsafe(40)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="quantforge-http-") as directory:
        env = dict(os.environ, QUANTFORGE_API_TOKEN=token, QUANTFORGE_DATA_DIR=directory)
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.api:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--workers",
                "1",
                "--log-level",
                "warning",
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        def request(path, body=None, key=None):
            headers = {"Authorization": f"Bearer {token}"}
            if body is not None:
                headers["Content-Type"] = "application/json"
            if key:
                headers["Idempotency-Key"] = key
            data = json.dumps(body).encode() if body is not None else None
            with urlopen(Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers), timeout=10) as response:
                payload = response.read().decode()
                return json.loads(payload) if response.headers.get_content_type() == "application/json" else payload

        try:
            deadline = time.monotonic() + 15
            while True:
                try:
                    health = request("/health")
                    break
                except (URLError, TimeoutError):
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError("HTTP server did not start")
                    time.sleep(0.1)
            assert health["status"] == "ok"
            assert "Research workspace" in request("/")
            assert "Research dataset" in request("/assets/app.js")
            plan = request("/api/research/plans", {})
            approval = {"revision": plan["revision"], "spec_hash": plan["spec_hash"]}
            request(f"/api/research/plans/{plan['plan_id']}/approve", approval)
            run = request("/api/research/runs", {"plan_id": plan["plan_id"], **approval}, "normal")
            assert run["state"] == "COMPLETED"
            assert any(item["run_id"] == run["run_id"] for item in request("/api/runs"))
            diagnostic = request("/api/demo/diagnostic-runs", {}, "diagnostic")
            parent = diagnostic["run_id"]
            correction = request(f"/api/runs/{parent}/corrections", {"kind": "timing"})
            child = request(
                f"/api/corrections/{correction['correction_id']}/approve-and-rerun",
                {"proposal_hash": correction["proposal_hash"]},
                "rerun",
            )
            comparison = request(f"/api/runs/{parent}/comparison?other_run_id={child['run_id']}")
            assert comparison["left"]["admissibility"] == "BLOCKED"
            assert comparison["right"]["admissibility"] == "ADMISSIBLE_WITHIN_CHECKED_SCOPE"
            assert "SYNTHETIC" in request(f"/api/runs/{child['run_id']}/report")
            print(
                json.dumps(
                    {
                        "http_smoke": "passed",
                        "normal_run": run["state"],
                        "comparison": comparison["classification"],
                        "parent_preserved": True,
                    }
                )
            )
        finally:
            process.terminate()
            try:
                process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()


if __name__ == "__main__":
    main()
