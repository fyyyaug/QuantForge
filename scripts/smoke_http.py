"""Exercise a real loopback HTTP server without saving or printing credentials."""

import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

ROOT = Path(__file__).resolve().parent.parent


def main():
    token = secrets.token_urlsafe(40)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="quantforge-http-") as directory:
        env = dict(
            os.environ,
            QUANTFORGE_API_TOKEN=token,
            QUANTFORGE_DATA_DIR=directory,
            QUANTFORGE_PUBLIC_DEMO="true",
            QUANTFORGE_COOKIE_SECURE="false",
            QUANTFORGE_ENABLE_PLANNER="false",
        )
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
            assert request("/api/evaluation")["summary"] == {"total": 26, "passed": 26}
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
            assert comparison["decision_changes"]["changed_signals"] > 0
            assert comparison["left"]["metrics"]["total_return"] != comparison["right"]["metrics"]["total_return"]
            exported = request(f"/api/runs/{parent}/comparison/report?other_run_id={child['run_id']}")
            assert "Original experiment" in exported and "New experiment" in exported
            assert "lookback_sessions" in exported and "available_at" in exported

            demo = build_opener(HTTPCookieProcessor(CookieJar()))

            def demo_request(path, body=None, key=None):
                headers = {"X-QuantForge-Request": "workspace"}
                if body is not None:
                    headers["Content-Type"] = "application/json"
                if key:
                    headers["Idempotency-Key"] = key
                data = json.dumps(body).encode() if body is not None else None
                with demo.open(
                    Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers), timeout=10
                ) as response:
                    return json.loads(response.read())

            demo_request("/api/demo/session", {})
            assert demo_request("/api/workspace")["demo"]["session_active"]
            assert demo_request("/api/runs") == []
            demo_run = demo_request("/api/demo/diagnostic-runs", {}, "anonymous-demo")
            demo_parent = demo_run["run_id"]
            demo_fix = demo_request(f"/api/runs/{demo_parent}/corrections", {"kind": "timing"})
            demo_child = demo_request(
                f"/api/corrections/{demo_fix['correction_id']}/approve-and-rerun",
                {"proposal_hash": demo_fix["proposal_hash"]},
                "anonymous-child",
            )
            assert demo_child["state"] == "COMPLETED"
            assert len(demo_request("/api/runs")) == 2
            assert len(request("/api/runs")) == 3
            assert demo_request("/api/demo/session/logout", {})["ended"]
            print(
                json.dumps(
                    {
                        "http_smoke": "passed",
                        "normal_run": run["state"],
                        "comparison": comparison["classification"],
                        "parent_preserved": True,
                        "anonymous_demo": "passed",
                        "changed_signals": comparison["decision_changes"]["changed_signals"],
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
