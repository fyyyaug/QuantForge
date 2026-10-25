from conftest import TOKEN_A, TOKEN_B


def make_run(client, overrides=None, dataset="clean_momentum", key="first"):
    response = client.post("/api/research/plans", json={"dataset_id": dataset, "overrides": overrides or {}})
    assert response.status_code == 201, response.text
    plan = response.json()
    approval = {"revision": plan["revision"], "spec_hash": plan["spec_hash"]}
    assert client.post(f"/api/research/plans/{plan['plan_id']}/approve", json=approval).status_code == 200
    payload = {"plan_id": plan["plan_id"], **approval}
    response = client.post("/api/research/runs", json=payload, headers={"Idempotency-Key": key})
    assert response.status_code == 201, response.text
    return response.json(), payload


def test_api_full_flow_and_contract(client):
    assert client.get("/health").json()["status"] == "ok"
    assert len(client.get("/api/datasets").json()) == 6
    run, payload = make_run(client)
    assert run["state"] == "COMPLETED"
    identity = run["run_id"]
    artifact = client.get(f"/api/runs/{identity}/artifact").json()
    assert artifact["admissibility"] == "ADMISSIBLE_WITHIN_CHECKED_SCOPE"
    assert client.get(f"/api/runs/{identity}/result").json()["metrics"]["trade_count"] > 0
    assert len(client.get(f"/api/runs/{identity}/audit").json()["findings"]) == 6
    assert "SYNTHETIC" in client.get(f"/api/runs/{identity}/report").text
    repeated = client.post("/api/research/runs", json=payload, headers={"Idempotency-Key": "first"})
    assert repeated.json()["run_id"] == identity
    assert client.get(f"/api/runs/{identity}/events", params={"after": 6}).json() == []


def test_api_diagnostic_correction_and_comparison(client):
    original = client.post("/api/demo/diagnostic-runs", json={}, headers={"Idempotency-Key": "diag"})
    assert original.status_code == 201, original.text
    parent = original.json()["run_id"]
    response = client.post(f"/api/runs/{parent}/corrections", json={"kind": "timing"})
    assert response.status_code == 201, response.text
    proposal = response.json()
    child = client.post(
        f"/api/corrections/{proposal['correction_id']}/approve-and-rerun",
        json={"proposal_hash": proposal["proposal_hash"]},
        headers={"Idempotency-Key": "child"},
    )
    assert child.status_code == 201, child.text
    identity = child.json()["run_id"]
    comparison = client.get(f"/api/runs/{parent}/comparison", params={"other_run_id": identity})
    assert comparison.json()["classification"] == "METHODOLOGY_CORRECTION"
    assert comparison.json()["left"]["admissibility"] == "BLOCKED"
    assert comparison.json()["right"]["admissibility"] == "ADMISSIBLE_WITHIN_CHECKED_SCOPE"


def test_api_cost_correction(client):
    run, _ = make_run(client, {"fee_bps_each_side": "0", "slippage_bps_each_side": "0"})
    response = client.post(f"/api/runs/{run['run_id']}/corrections", json={"kind": "costs"})
    assert response.status_code == 201, response.text
    assert response.json()["proposal"]["spec"]["fee_bps_each_side"] == "5"


def test_unauthorized_and_cross_workspace_access(client):
    run, _ = make_run(client)
    identity = run["run_id"]
    client.headers["Authorization"] = "Bearer wrong"
    assert client.get("/api/datasets").status_code == 401
    client.headers["Authorization"] = f"Bearer {TOKEN_B}"
    for path in ("", "/artifact", "/audit", "/result", "/report", "/events"):
        assert client.get(f"/api/runs/{identity}{path}").status_code == 404
    assert client.post(f"/api/runs/{identity}/corrections", json={"kind": "costs"}).status_code == 404


def test_bad_inputs_return_safe_errors(client):
    responses = [
        client.post("/api/research/plans", json={"overrides": {"lookback_sessions": 0}}),
        client.post("/api/research/plans", json={"overrides": {"threshold_pct": "NaN"}}),
        client.post("/api/research/plans", json={"overrides": {"execution_mode": "DIAGNOSTIC_INVALID"}}),
        client.post("/api/research/plans", json={"overrides": {"source_code": "import os"}}),
        client.post("/api/research/plans", content="{bad json", headers={"Content-Type": "application/json"}),
        client.post(
            "/api/demo/diagnostic-runs", json={"fixture_id": "user-upload"}, headers={"Idempotency-Key": "bad"}
        ),
    ]
    for response in responses:
        assert response.status_code == 422, response.text
        assert "error" in response.json()
        assert "Traceback" not in response.text and TOKEN_A not in response.text


def test_large_body_and_missing_key_are_controlled(client):
    assert client.post("/api/research/plans", content="x" * 65537).status_code == 413
    assert client.post("/api/demo/diagnostic-runs", json={}).status_code == 422


def test_blocked_dataset_has_no_result_and_completed_cancel_conflicts(client):
    run, _ = make_run(client, dataset="missing_open")
    assert client.get(f"/api/runs/{run['run_id']}/result").json() is None
    assert client.get(f"/api/runs/{run['run_id']}/audit").json()["admissibility"] == "BLOCKED"
    assert client.post(f"/api/runs/{run['run_id']}/cancel").status_code == 409


def test_invalid_correction_approval_does_not_execute(client):
    run, _ = make_run(client, {"fee_bps_each_side": "0", "slippage_bps_each_side": "0"})
    proposal = client.post(f"/api/runs/{run['run_id']}/corrections", json={"kind": "costs"}).json()
    response = client.post(
        f"/api/corrections/{proposal['correction_id']}/approve-and-rerun",
        json={"proposal_hash": "0" * 64},
        headers={"Idempotency-Key": "wrong"},
    )
    assert response.status_code == 409


def test_openapi_is_generated(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/research/runs" in response.json()["paths"]
