import asyncio

import pytest
from conftest import approved_run

from backend.api import BodyLimitMiddleware, create_app
from backend.canonical import canonical, digest
from backend.data import Snapshot, validate_data
from backend.errors import ResearchError


def test_api_refuses_missing_or_short_secret(tmp_path, monkeypatch):
    monkeypatch.delenv("QUANTFORGE_API_TOKEN", raising=False)
    with pytest.raises(ValueError, match="at least 32"):
        create_app(tmp_path)
    with pytest.raises(ValueError):
        create_app(tmp_path, {"short": "workspace"})


def test_model_error_is_controlled_and_does_not_claim_success(service, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("private internal sentinel")

    monkeypatch.setattr("backend.service.simulate", fail)
    identity = approved_run(service)
    view = service.view("alice", identity)
    assert view["state"] == "FAILED"
    assert view["error"] == "INTERNAL_EXECUTION_ERROR"
    assert "sentinel" not in canonical(view)


def test_correction_ownership_and_stale_hash(service):
    parent = approved_run(service)
    correction = service.propose("alice", parent, "costs", fee="10")
    with pytest.raises(ResearchError) as error:
        service.store.approve_rerun("bob", correction["id"], correction["hash"], "steal")
    assert error.value.code == "NOT_FOUND"
    with pytest.raises(ResearchError) as error:
        service.store.approve_rerun("alice", correction["id"], "0" * 64, "stale")
    assert error.value.code == "STALE_APPROVAL"


def test_normal_research_on_leaky_named_file_does_not_enable_future_feature(service):
    identity = approved_run(service, dataset="leaky_next_close")
    artifact = service.store.artifact("alice", identity)
    assert artifact["mode"] == "RESEARCH"
    assert next(f for f in artifact["findings"] if f["check_id"] == "A01_LOOKAHEAD")["status"] == "PASS"


def test_dataset_difference_disallows_direct_comparison(service):
    first = approved_run(service, key="one")
    other = approved_run(service, dataset="missing_open", key="two")
    assert service.compare("alice", first, other)["classification"] == "NOT_DIRECTLY_COMPARABLE"


@pytest.mark.parametrize("content", [b"\xffinvalid", b"date,symbol,open,high,low,close,volume\n", b"date,date\n1,1\n"])
def test_malformed_csv_shapes(service, catalog, content):
    snapshot = Snapshot(catalog.load("clean_momentum").manifest, content)
    _, issues = validate_data(snapshot, service.template())
    assert issues


def test_missing_lineage_stays_blocked_in_normal_pipeline(service, monkeypatch):
    from backend.engine import build_decisions

    def invalid(bars, spec, **kwargs):
        decisions, skips = build_decisions(bars, spec)
        return tuple(d.model_copy(update={"dependencies": ()}) for d in decisions), skips

    monkeypatch.setattr("backend.service.build_decisions", invalid)
    identity = approved_run(service)
    artifact = service.store.artifact("alice", identity)
    assert artifact["admissibility"] == "BLOCKED"
    assert artifact["result"] is None


def test_approvals_are_recorded_transactionally(service):
    approved_run(service)
    with service.store.lock:
        rows = list(service.store.db.execute("SELECT * FROM approvals"))
    assert len(rows) == 1
    assert rows[0]["workspace"] == "alice"
    assert rows[0]["timestamp"]


def test_completed_state_is_terminal(service):
    identity = approved_run(service)
    for state in ("RUNNING", "FAILED", "COMPLETED"):
        with pytest.raises(ResearchError):
            service.store.transition("alice", identity, state)


def test_chunked_body_limit_without_content_length():
    sent = []
    called = []

    async def inner(scope, receive, send):
        called.append(True)

    chunks = iter(
        [
            {"type": "http.request", "body": b"1234", "more_body": True},
            {"type": "http.request", "body": b"5678", "more_body": False},
        ]
    )

    async def receive():
        return next(chunks)

    async def send(message):
        sent.append(message)

    asyncio.run(BodyLimitMiddleware(inner, limit=6)({"type": "http"}, receive, send))
    assert not called
    assert sent[0]["status"] == 413


def test_canonical_hash_ignores_decimal_spelling():
    from decimal import Decimal

    assert digest({"x": Decimal("2.000")}) == digest({"x": Decimal(2)})
    assert canonical({"x": Decimal("-0.00")}) == '{"x":"0"}'


def test_insufficient_warmup_is_not_a_false_timing_pass(service):
    identity = approved_run(service, overrides={"sample_end": "2026-01-05"})
    artifact = service.store.artifact("alice", identity)
    finding = next(f for f in artifact["findings"] if f["check_id"] == "A01_LOOKAHEAD")
    assert finding["status"] == "NOT_APPLICABLE"
    assert artifact["result"]["metrics"]["trade_count"] == 0


def test_normal_request_cannot_enable_diagnostic_mode(client):
    response = client.post(
        "/api/demo/diagnostic-runs", json={"execution_mode": "RESEARCH"}, headers={"Idempotency-Key": "no-override"}
    )
    assert response.status_code == 422


def test_missing_database_artifact_is_controlled(service):
    identity = approved_run(service)
    run = service.store.get("runs", identity, "alice")
    with service.store.transaction() as db:
        db.execute("DELETE FROM artifacts WHERE hash=?", (run["artifact_hash"],))
    with pytest.raises(ResearchError) as error:
        service.store.artifact("alice", identity)
    assert error.value.code == "ARTIFACT_WRITE_FAILED"
