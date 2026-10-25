import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from urllib.error import HTTPError

import pytest
from conftest import FIXTURES, TOKEN_A, TOKEN_B
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.planner import PARAMETERS, ClaudePlanner, NoRedirects, PlannerSettings

HYPOTHESIS = "If the five-session trailing return exceeds 2%, enter at next open and exit at close."
KEY = "fake-provider-secret-used-only-in-tests"


def answer(status="PLAN", reason="SUPPORTED", question="", **parameters):
    return {
        "status": status,
        "reason": reason,
        "question": question,
        "parameters": {name: parameters.get(name) for name in PARAMETERS},
    }


def wire(body):
    return json.dumps({"stop_reason": "end_turn", "content": [{"type": "text", "text": json.dumps(body)}]}).encode()


def provider_with_response(monkeypatch, raw, settings=None):
    provider = ClaudePlanner(settings or PlannerSettings(KEY, "claude-test"))

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, size):
            return raw[:size]

    class Opener:
        def open(self, request, timeout):
            provider.last_request = request
            provider.last_timeout = timeout
            return Response()

    monkeypatch.setattr("backend.planner.build_opener", lambda *args: Opener())
    return provider


def app_client(tmp_path, provider):
    return TestClient(
        create_app(tmp_path, {TOKEN_A: "alice", TOKEN_B: "bob"}, FIXTURES, planner_provider=provider),
        headers={"Authorization": f"Bearer {TOKEN_A}"},
    )


def test_disabled_planner_preserves_template_path(client):
    assert not client.get("/api/workspace").json()["planner"]["available"]
    response = client.post("/api/research/hypotheses", json={"hypothesis": HYPOTHESIS})
    assert response.status_code == 503
    assert client.post("/api/research/plans", json={}).status_code == 201


def test_valid_draft_is_saved_unapproved_and_provenance_reaches_report(tmp_path, monkeypatch):
    provider = provider_with_response(monkeypatch, wire(answer(lookback_sessions=5, threshold_pct="2")))
    with app_client(tmp_path, provider) as client:
        response = client.post("/api/research/hypotheses", json={"hypothesis": HYPOTHESIS})
        assert response.status_code == 200, response.text
        plan = response.json()["plan"]
        assert plan["planning_mode"] == "CLAUDE_STRUCTURED"
        assert plan["planning"]["proposed_fields"] == ["lookback_sessions", "threshold_pct"]
        assert "fee_bps_each_side" in plan["planning"]["defaulted_fields"]
        identity = plan["plan_id"]
        saved = client.get(f"/api/research/plans/{identity}").json()
        assert saved["planning"] == plan["planning"]
        approval = {"revision": plan["revision"], "spec_hash": plan["spec_hash"]}
        payload = {"plan_id": identity, **approval}
        assert client.post("/api/research/runs", json=payload, headers={"Idempotency-Key": "before"}).status_code == 409
        assert client.post(f"/api/research/plans/{identity}/approve", json=approval).status_code == 200
        run = client.post("/api/research/runs", json=payload, headers={"Idempotency-Key": "after"}).json()
        report = client.get(f"/api/runs/{run['run_id']}/report").text
        assert "CLAUDE_STRUCTURED" in report and KEY not in report and HYPOTHESIS not in report
        assert client.get(f"/api/runs/{run['run_id']}/artifact").json()["planning"] == plan["planning"]
        request = provider.last_request
        assert request.full_url == "https://api.anthropic.com/v1/messages"
        assert request.get_header("Authorization") == f"Bearer {KEY}"
        body = json.loads(request.data)
        assert body["max_tokens"] == 768 and "tools" not in body
        assert body["messages"] == [{"role": "user", "content": HYPOTHESIS}]
        assert KEY not in json.dumps(body) and "dataset_hash" not in json.dumps(body)
        assert provider.last_timeout == 8


@pytest.mark.parametrize(
    "status,reason,question",
    [
        ("CLARIFY", "MISSING_DETAILS", "Which trailing lookback should define the signal?"),
        ("UNSUPPORTED", "UNSUPPORTED_TIMING", ""),
        ("UNSUPPORTED", "UNSUPPORTED_STRATEGY", ""),
        ("UNSUPPORTED", "UNSUPPORTED_ASSET", ""),
        ("UNSUPPORTED", "UNSAFE_REQUEST", ""),
    ],
)
def test_nonplan_answers_never_create_or_execute_plans(tmp_path, monkeypatch, status, reason, question):
    provider = provider_with_response(monkeypatch, wire(answer(status, reason, question)))
    with app_client(tmp_path, provider) as client:
        response = client.post("/api/research/hypotheses", json={"hypothesis": HYPOTHESIS})
        assert response.status_code == 200 and response.json()["status"] == status
        store = client.app.state.service.store
        assert store.db.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == 0
        assert store.db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0


@pytest.mark.parametrize(
    "parameters",
    [{"lookback_sessions": 0}, {"threshold_pct": "NaN"}, {"allocation_fraction": "2"}, {"sample_start": "bad-date"}],
)
def test_out_of_scope_model_parameters_do_not_become_valid_plans(tmp_path, monkeypatch, parameters):
    provider = provider_with_response(monkeypatch, wire(answer(**parameters)))
    with app_client(tmp_path, provider) as client:
        response = client.post("/api/research/hypotheses", json={"hypothesis": HYPOTHESIS})
        assert response.status_code == 422 and response.json()["error"]["code"] == "PLANNER_INVALID_OUTPUT"
        assert client.app.state.service.store.db.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == 0


@pytest.mark.parametrize(
    "raw",
    [
        b"not json",
        b"x" * 32769,
        b'{"stop_reason":"max_tokens","content":[]}',
        b'{"stop_reason":"end_turn","content":[{"type":"tool_use"}]}',
        b'{"stop_reason":"end_turn","content":["unexpected"]}',
        wire({**answer(), "source_code": "import os"}),
        wire({**answer(), "parameters": {}}),
        wire(answer("PLAN", "UNSUPPORTED_TIMING")),
        wire(answer("CLARIFY", "MISSING_DETAILS", "")),
        wire(answer("UNSUPPORTED", "SUPPORTED")),
        wire(answer("UNSUPPORTED", "UNSAFE_REQUEST", lookback_sessions=5)),
    ],
)
def test_invalid_provider_output_fails_safely_without_breaking_template(tmp_path, monkeypatch, raw):
    provider = provider_with_response(monkeypatch, raw)
    with app_client(tmp_path, provider) as client:
        response = client.post("/api/research/hypotheses", json={"hypothesis": HYPOTHESIS})
        assert response.status_code == 503 and KEY not in response.text and "Traceback" not in response.text
        assert client.post("/api/research/plans", json={}).status_code == 201


def test_timeout_counts_against_persistent_quota_and_never_leaks_error(tmp_path, monkeypatch):
    provider = ClaudePlanner(replace(PlannerSettings(KEY, "claude-test"), calls_per_workspace_hour=1))

    def timeout(payload):
        raise TimeoutError(f"private provider detail {KEY}")

    monkeypatch.setattr(provider, "send", timeout)
    with app_client(tmp_path, provider) as client:
        first = client.post("/api/research/hypotheses", json={"hypothesis": HYPOTHESIS})
        assert first.status_code == 503 and KEY not in first.text
    with app_client(tmp_path, provider) as client:
        assert client.post("/api/research/hypotheses", json={"hypothesis": HYPOTHESIS}).status_code == 429
        assert client.post("/api/research/plans", json={}).status_code == 201


def test_service_wide_budget_applies_across_workspaces(tmp_path, monkeypatch):
    settings = replace(PlannerSettings(KEY, "claude-test"), calls_per_service_hour=1)
    provider = provider_with_response(monkeypatch, wire(answer()), settings)
    with app_client(tmp_path, provider) as client:
        assert client.post("/api/research/hypotheses", json={"hypothesis": HYPOTHESIS}).status_code == 200
        client.headers["Authorization"] = f"Bearer {TOKEN_B}"
        assert client.post("/api/research/hypotheses", json={"hypothesis": HYPOTHESIS}).status_code == 429


def test_provider_http_error_is_controlled(tmp_path, monkeypatch):
    provider = ClaudePlanner(PlannerSettings(KEY, "claude-test"))
    monkeypatch.setattr(
        provider, "send", lambda body: (_ for _ in ()).throw(HTTPError("https://api.anthropic.com", 401, KEY, {}, None))
    )
    with app_client(tmp_path, provider) as client:
        response = client.post("/api/research/hypotheses", json={"hypothesis": HYPOTHESIS})
        assert response.status_code == 503 and KEY not in response.text


def test_environment_configuration_is_explicit_and_never_exposes_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    monkeypatch.setenv("QUANTFORGE_PLANNER_MODEL", "claude-test")
    monkeypatch.delenv("QUANTFORGE_ENABLE_PLANNER", raising=False)
    assert not ClaudePlanner.from_environment().public()["available"]
    monkeypatch.setenv("QUANTFORGE_ENABLE_PLANNER", "true")
    configured = ClaudePlanner.from_environment()
    assert configured.public()["available"]
    assert KEY not in repr(configured.settings) and KEY not in json.dumps(configured.public())
    monkeypatch.setenv("QUANTFORGE_PLANNER_MODEL", "invalid-model")
    assert not ClaudePlanner.from_environment().public()["available"]
    assert NoRedirects().redirect_request(None, None, 302, "redirect", {}, "https://other.test") is None


def test_live_evaluation_requires_an_explicit_flag_before_any_provider_call():
    result = subprocess.run(
        [sys.executable, "scripts/evaluate_planner.py"],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2 and "--live" in result.stderr
