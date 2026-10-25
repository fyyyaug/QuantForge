from dataclasses import replace

import pytest
from conftest import FIXTURES, TOKEN_A
from fastapi.testclient import TestClient
from test_api import make_run

from backend.api import create_app
from backend.config import DemoPolicy

HEADERS = {"X-QuantForge-Request": "workspace"}


@pytest.fixture
def demo_client(tmp_path):
    app = create_app(tmp_path, {TOKEN_A: "private"}, FIXTURES, DemoPolicy())
    with TestClient(app, headers=HEADERS) as client:
        yield client


def start(client):
    response = client.post("/api/demo/session", json={})
    assert response.status_code == 200, response.text
    return response


def test_public_demo_is_opt_in_and_does_not_change_private_auth(client):
    assert client.get("/api/workspace").json()["demo"]["enabled"] is False
    assert client.post("/api/demo/session", json={}, headers=HEADERS).status_code == 404


def test_cookie_is_http_only_scoped_hashed_and_resumable(demo_client):
    assert demo_client.get("/api/workspace").json()["demo"]["session_active"] is False
    response = start(demo_client)
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/" in cookie
    token = demo_client.cookies.get("quantforge_demo")
    assert token and token not in response.text and TOKEN_A not in response.text
    with demo_client.app.state.service.store.lock:
        stored = demo_client.app.state.service.store.db.execute("SELECT * FROM demo_sessions").fetchone()
        assert stored["token_hash"] != token and token not in str(dict(stored))
    assert demo_client.get("/api/workspace").json()["demo"]["session_active"] is True
    assert "set-cookie" not in start(demo_client).headers
    assert len(demo_client.get("/api/datasets").json()) == 6


def test_demo_workspaces_cannot_access_each_others_runs_or_private_runs(demo_client):
    start(demo_client)
    first, _ = make_run(demo_client)
    other = TestClient(demo_client.app, headers=HEADERS)
    try:
        start(other)
        assert other.get("/api/runs").json() == []
        identity = first["run_id"]
        for suffix in ("", "/artifact", "/result", "/report", "/events", "/audit"):
            assert other.get(f"/api/runs/{identity}{suffix}").status_code == 404
        assert other.post(f"/api/runs/{identity}/corrections", json={"kind": "costs"}).status_code == 404
        assert other.get(f"/api/runs/{identity}/comparison", params={"other_run_id": identity}).status_code == 404
        other.headers["Authorization"] = f"Bearer {TOKEN_A}"
        private, _ = make_run(other, key="private-run")
        assert demo_client.get(f"/api/runs/{private['run_id']}/artifact").status_code == 404
        assert len(demo_client.get("/api/runs").json()) == 1
    finally:
        other.close()


def test_demo_mutations_require_same_origin_header_and_reject_cross_origin(demo_client):
    assert demo_client.post("/api/demo/session", json={}, headers={"X-QuantForge-Request": ""}).status_code == 403
    assert (
        demo_client.post("/api/demo/session", json={}, headers={"Origin": "https://attacker.test"}).status_code == 403
    )
    start(demo_client)
    assert demo_client.post("/api/research/plans", json={}, headers={"X-QuantForge-Request": ""}).status_code == 403
    assert (
        demo_client.post("/api/research/plans", json={}, headers={"Origin": "https://attacker.test"}).status_code == 403
    )
    assert demo_client.post("/api/research/plans", json={}, headers={"Origin": "http://testserver"}).status_code == 201
    preflight = demo_client.options(
        "/api/demo/session",
        headers={"Origin": "https://attacker.test", "Access-Control-Request-Headers": "X-QuantForge-Request"},
    )
    assert "access-control-allow-origin" not in preflight.headers


def test_bad_bearer_does_not_fall_back_to_demo_cookie(demo_client):
    start(demo_client)
    assert demo_client.get("/api/runs", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_run_quota_is_atomic_but_idempotent_retries_still_work(tmp_path):
    policy = replace(DemoPolicy(), max_runs=1)
    with TestClient(create_app(tmp_path, {}, FIXTURES, policy), headers=HEADERS) as client:
        start(client)
        first, payload = make_run(client)
        retry = client.post("/api/research/runs", json=payload, headers={"Idempotency-Key": "first"})
        assert retry.status_code == 201 and retry.json()["run_id"] == first["run_id"]
        exhausted = client.post("/api/research/runs", json=payload, headers={"Idempotency-Key": "second"})
        assert exhausted.status_code == 429 and exhausted.json()["error"]["code"] == "DEMO_QUOTA_REACHED"
        assert len(client.get("/api/runs").json()) == 1
        proposal = client.post(
            f"/api/runs/{first['run_id']}/corrections", json={"kind": "costs", "fee_bps_each_side": "10"}
        ).json()
        child = client.post(
            f"/api/corrections/{proposal['correction_id']}/approve-and-rerun",
            json={"proposal_hash": proposal["proposal_hash"]},
            headers={"Idempotency-Key": "child"},
        )
        assert child.status_code == 429
        assert client.get(f"/api/runs/{first['run_id']}/artifact").status_code == 200


def test_plans_and_correction_proposals_have_separate_limits(tmp_path):
    policy = replace(DemoPolicy(), max_plans=1, max_corrections=1)
    with TestClient(create_app(tmp_path, {}, FIXTURES, policy), headers=HEADERS) as client:
        start(client)
        run, _ = make_run(client)
        assert client.post("/api/research/plans", json={}).status_code == 429
        endpoint = f"/api/runs/{run['run_id']}/corrections"
        assert client.post(endpoint, json={"kind": "costs", "fee_bps_each_side": "10"}).status_code == 201
        assert client.post(endpoint, json={"kind": "costs", "fee_bps_each_side": "10"}).status_code == 429


def test_rate_limit_window_resets_without_resetting_session_quota(tmp_path):
    policy = replace(DemoPolicy(), requests_per_minute=2, requests_per_session=3)
    with TestClient(create_app(tmp_path, {}, FIXTURES, policy), headers=HEADERS) as client:
        access = client.app.state.demo
        now = [100000]
        access.clock = lambda: now[0]
        start(client)
        assert client.get("/api/runs").status_code == 200
        assert client.get("/api/runs").status_code == 200
        assert client.get("/api/runs").status_code == 429
        now[0] += 61
        assert client.get("/api/runs").status_code == 200
        assert client.get("/api/runs").status_code == 429
        assert client.post("/api/demo/session/logout", json={}).status_code == 200


def test_issuance_is_bounded_and_persists_across_restarts(tmp_path):
    policy = replace(DemoPolicy(), sessions_per_hour=1)
    with TestClient(create_app(tmp_path, {}, FIXTURES, policy), headers=HEADERS) as client:
        start(client)
        cookies = dict(client.cookies)
        run, _ = make_run(client)
    with TestClient(create_app(tmp_path, {}, FIXTURES, policy), headers=HEADERS) as restarted:
        restarted.cookies.update(cookies)
        assert restarted.get("/api/workspace").json()["demo"]["session_active"] is True
        assert restarted.get(f"/api/runs/{run['run_id']}/artifact").status_code == 200
        restarted.cookies.clear()
        assert restarted.post("/api/demo/session", json={}).status_code == 429


def test_request_allowance_cannot_be_reset_by_restarting(tmp_path):
    policy = replace(DemoPolicy(), requests_per_session=1)
    with TestClient(create_app(tmp_path, {}, FIXTURES, policy), headers=HEADERS) as client:
        start(client)
        cookies = dict(client.cookies)
        assert client.get("/api/runs").status_code == 200
    with TestClient(create_app(tmp_path, {}, FIXTURES, policy), headers=HEADERS) as restarted:
        restarted.cookies.update(cookies)
        assert restarted.get("/api/runs").status_code == 429


def test_expiry_cleans_parent_child_artifacts_but_preserves_private_history(demo_client):
    access = demo_client.app.state.demo
    now = [int(access.clock())]
    access.clock = lambda: now[0]
    start(demo_client)
    parent = demo_client.post("/api/demo/diagnostic-runs", json={}, headers={"Idempotency-Key": "parent"}).json()
    correction = demo_client.post(f"/api/runs/{parent['run_id']}/corrections", json={"kind": "timing"}).json()
    child = demo_client.post(
        f"/api/corrections/{correction['correction_id']}/approve-and-rerun",
        json={"proposal_hash": correction["proposal_hash"]},
        headers={"Idempotency-Key": "child"},
    )
    assert child.status_code == 201
    shared, _ = make_run(demo_client, key="shared-scientific-artifact")
    demo_client.headers["Authorization"] = f"Bearer {TOKEN_A}"
    private, _ = make_run(demo_client, key="private")
    assert shared["artifact_hash"] == private["artifact_hash"]
    demo_client.headers.pop("Authorization")
    now[0] += access.policy.ttl_seconds + 1
    expired = demo_client.get("/api/runs")
    assert expired.status_code == 401 and expired.json()["error"]["code"] == "SESSION_EXPIRED"
    start(demo_client)
    assert demo_client.get("/api/runs").json() == []
    store = demo_client.app.state.service.store
    with store.lock:
        assert store.db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1
        assert store.db.execute("SELECT COUNT(*) FROM corrections").fetchone()[0] == 0
        assert store.db.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 1
    demo_client.headers["Authorization"] = f"Bearer {TOKEN_A}"
    assert demo_client.get(f"/api/runs/{private['run_id']}/artifact").status_code == 200


def test_logout_revokes_copied_cookie(demo_client):
    start(demo_client)
    copied = dict(demo_client.cookies)
    assert demo_client.post("/api/demo/session/logout", json={}).status_code == 200
    demo_client.cookies.update(copied)
    assert demo_client.get("/api/workspace").json()["demo"]["session_active"] is False
    assert demo_client.get("/api/runs").status_code == 401


def test_cleanup_preserves_inflight_work_until_terminal(demo_client):
    access = demo_client.app.state.demo
    now = [int(access.clock())]
    access.clock = lambda: now[0]
    start(demo_client)
    session = access.peek(demo_client.cookies.get("quantforge_demo"))
    service = demo_client.app.state.service
    identity = service.store.queue_diagnostic(session["workspace"], service.template("timing_trap"), "inflight")
    service.store.transition(session["workspace"], identity, "VALIDATING")
    now[0] += access.policy.ttl_seconds + 1
    access.cleanup()
    assert service.store.get("runs", identity, session["workspace"])["state"] == "VALIDATING"
    service.store.transition(session["workspace"], identity, "FAILED", error="TEST_INTERRUPTION")
    access.cleanup()
    with service.store.lock:
        assert service.store.db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0


def test_secure_host_cookie_and_no_credentials_in_session_json(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANTFORGE_COOKIE_SECURE", "true")
    with TestClient(
        create_app(tmp_path, {}, FIXTURES, DemoPolicy()), base_url="https://testserver", headers=HEADERS
    ) as client:
        response = start(client)
        assert response.headers["set-cookie"].startswith("__Host-quantforge_demo=")
        assert "Secure" in response.headers["set-cookie"]
        assert set(response.json()) == {"expires_at", "limits"}
        assert client.get("/api/runs").status_code == 200
        assert client.post("/api/research/plans", json={}, headers={"Origin": "http://testserver"}).status_code == 403


def test_demo_mode_rejects_misconfigured_private_secret_and_reserved_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANTFORGE_PUBLIC_DEMO", "true")
    monkeypatch.setenv("QUANTFORGE_API_TOKEN", "too-short")
    with pytest.raises(ValueError, match="at least 32"):
        create_app(tmp_path)
    with pytest.raises(ValueError):
        create_app(tmp_path, {TOKEN_A: "demo:reserved"})
