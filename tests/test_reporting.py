from copy import deepcopy

from conftest import TOKEN_B, approved_run

from backend.reporting import research_report


def test_report_contains_exact_spec_units_evidence_and_fingerprints(service):
    identity = service.store.queue_diagnostic("alice", service.template("timing_trap"), "report")
    service.execute("alice", identity)
    artifact = service.store.artifact("alice", identity)
    report = artifact["report"]
    for key in artifact["spec"]:
        assert f'"{key}"' in report
    for value in (
        "83.7684%",
        "USD 18376.84",
        "bps per side",
        "available_at",
        "decision_at",
        "entry_at",
        "row_number",
        "source_hash",
        "dependency_lock_hash",
        "INTENTIONALLY FLAWED",
        "UNVERIFIED",
    ):
        assert value in report
    assert artifact["scientific_hash"] in report
    assert "0.01 means 1%" in report


def test_comparison_report_has_both_saved_results_and_ownership(client):
    parent = client.post("/api/demo/diagnostic-runs", json={}, headers={"Idempotency-Key": "report"}).json()["run_id"]
    proposal = client.post(f"/api/runs/{parent}/corrections", json={"kind": "timing"}).json()
    child = client.post(
        f"/api/corrections/{proposal['correction_id']}/approve-and-rerun",
        json={"proposal_hash": proposal["proposal_hash"]},
        headers={"Idempotency-Key": "child"},
    ).json()["run_id"]
    endpoint = f"/api/runs/{parent}/comparison/report?other_run_id={child}"
    report = client.get(endpoint)
    assert report.status_code == 200
    for value in (
        parent,
        child,
        "Original experiment",
        "New experiment",
        "INTENTIONALLY FLAWED",
        "-50.8060%",
        '"changed_signals": 14',
        '"feature_source"',
        "APPROVED_CORRECTION",
    ):
        assert value in report.text
    client.headers["Authorization"] = f"Bearer {TOKEN_B}"
    assert client.get(endpoint).status_code == 404


def test_report_handles_empty_results_escapes_markup_and_discloses_limits(service):
    identity = approved_run(service)
    artifact = deepcopy(service.store.artifact("alice", identity))
    artifact["dataset"]["source"] = "<script>bad()</script>```"
    artifact["result"]["trades"] *= 10
    artifact["findings"][0]["evidence"] = [{"row_number": 2}] * 101
    report = research_report(artifact)
    assert "<script>" not in report and "\\u003cscript>" in report
    assert "Showing 100 of" in report
    artifact["result"] = None
    assert "No performance metrics are claimed" in research_report(artifact)


def test_zero_trade_report_is_explicit_and_does_not_invent_statistics(service):
    identity = approved_run(service, overrides={"threshold_pct": "10000"})
    report = service.store.artifact("alice", identity)["report"]
    assert "No trades. The flat NAV is a computed outcome." in report
    assert "| sharpe | N/A | N/A |" in report
