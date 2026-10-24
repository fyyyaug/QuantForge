import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from conftest import approved_run

from backend.canonical import canonical
from backend.errors import ResearchError
from backend.store import Store


def test_complete_workflow_and_three_run_reproducibility(service):
    identities = [approved_run(service, key=f"replay-{i}") for i in range(3)]
    artifacts = [service.store.artifact("alice", identity) for identity in identities]
    assert len({a["scientific_hash"] for a in artifacts}) == 1
    assert len({canonical(a) for a in artifacts}) == 1
    assert artifacts[0]["admissibility"] == "ADMISSIBLE_WITHIN_CHECKED_SCOPE"
    assert artifacts[0]["result"]["metrics"]["trade_count"] > 0
    assert artifacts[0]["findings"][-1]["status"] == "UNVERIFIED"
    events = service.store.events("alice", identities[0])
    assert [e["state"] for e in events] == ["QUEUED", "VALIDATING", "RUNNING", "AUDITING", "REPORTING", "COMPLETED"]
    assert service.store.events("alice", identities[0], events[-1]["sequence"]) == []


@pytest.mark.parametrize("dataset", ["missing_open", "duplicate_sessions", "invalid_ohlc"])
def test_integrity_failure_completes_with_blocked_audit_and_no_metrics(service, dataset):
    identity = approved_run(service, dataset=dataset)
    artifact = service.store.artifact("alice", identity)
    assert service.view("alice", identity)["state"] == "COMPLETED"
    assert artifact["admissibility"] == "BLOCKED"
    assert artifact["result"] is None
    assert artifact["findings"][0]["status"] == "FAIL"
    assert "No performance metrics are claimed" in artifact["report"]


def test_diagnostic_and_approved_correction_preserve_parent(service):
    spec = service.template("leaky_next_close")
    parent = service.store.queue_diagnostic("alice", spec, "diagnostic")
    service.execute("alice", parent)
    original = service.store.artifact("alice", parent)
    assert original["admissibility"] == "BLOCKED"
    assert original["result"] is not None
    assert next(f for f in original["findings"] if f["check_id"] == "A01_LOOKAHEAD")["status"] == "FAIL"
    assert "INTENTIONALLY FLAWED" in original["report"]
    proposal = service.propose("alice", parent, "timing")
    assert proposal["child_id"] is None
    child = service.store.approve_rerun("alice", proposal["id"], proposal["hash"], "approved")
    service.execute("alice", child)
    corrected = service.store.artifact("alice", child)
    assert corrected["mode"] == "RESEARCH"
    assert corrected["admissibility"] == "ADMISSIBLE_WITHIN_CHECKED_SCOPE"
    assert service.view("alice", child)["parent_run_id"] == parent
    assert service.store.artifact("alice", parent) == original
    assert service.compare("alice", parent, child)["classification"] == "METHODOLOGY_CORRECTION"
    again = service.store.approve_rerun("alice", proposal["id"], proposal["hash"], "approved")
    different_key = service.store.approve_rerun("alice", proposal["id"], proposal["hash"], "another-key")
    assert again == different_key == child


def test_cost_sensitivity_recomputes_same_gross_trades(service):
    parent = approved_run(service, overrides={"fee_bps_each_side": "0", "slippage_bps_each_side": "0"})
    original = service.store.artifact("alice", parent)
    proposal = service.propose("alice", parent, "costs")
    child = service.store.approve_rerun("alice", proposal["id"], proposal["hash"], "costs")
    service.execute("alice", child)
    paid = service.store.artifact("alice", child)
    assert len(original["result"]["trades"]) == len(paid["result"]["trades"])
    assert [t["gross_return"] for t in original["result"]["trades"]] == [
        t["gross_return"] for t in paid["result"]["trades"]
    ]
    assert Decimal(paid["result"]["metrics"]["ending_nav"]) < Decimal(original["result"]["metrics"]["ending_nav"])
    assert service.compare("alice", parent, child)["classification"] == "CONTROLLED_ASSUMPTION_CHANGE"


def test_approval_invalidation_and_idempotency_conflict(service):
    spec = service.template()
    plan = service.store.create_plan("alice", spec)
    with pytest.raises(ResearchError) as error:
        service.store.queue_plan("alice", plan["id"], 1, plan["hash"], "before-approval")
    assert error.value.code == "STALE_APPROVAL"
    service.store.approve("alice", plan["id"], 1, plan["hash"])
    first = service.store.queue_plan("alice", plan["id"], 1, plan["hash"], "key")
    assert service.store.queue_plan("alice", plan["id"], 1, plan["hash"], "key") == first
    new = spec.model_copy(update={"threshold_pct": Decimal(3)})
    revised = service.store.revise("alice", plan["id"], 1, new)
    assert revised["revision"] == 2 and not revised["approved"]
    with pytest.raises(ResearchError):
        service.store.queue_plan("alice", plan["id"], 2, revised["hash"], "new-key")
    service.store.approve("alice", plan["id"], 2, revised["hash"])
    with pytest.raises(ResearchError) as error:
        service.store.queue_plan("alice", plan["id"], 2, revised["hash"], "key")
    assert error.value.code == "IDEMPOTENCY_CONFLICT"
    assert json.loads(service.store.get("runs", first, "alice")["spec"])["threshold_pct"] == "2"


def test_concurrent_retries_queue_exactly_one_run(service):
    plan = service.store.create_plan("alice", service.template())
    service.store.approve("alice", plan["id"], 1, plan["hash"])

    def queue(_):
        return service.store.queue_plan("alice", plan["id"], 1, plan["hash"], "same")

    with ThreadPoolExecutor(max_workers=8) as pool:
        identities = list(pool.map(queue, range(16)))
    assert len(set(identities)) == 1
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda identity: service.execute("alice", identity), identities[:4]))
    assert all(r["state"] == "COMPLETED" for r in results)
    assert len(service.store.events("alice", identities[0])) == 6


def test_unknown_workspace_cannot_read_or_correct(service):
    identity = approved_run(service)
    actions = [
        lambda: service.store.artifact("bob", identity),
        lambda: service.store.events("bob", identity),
        lambda: service.propose("bob", identity, "costs"),
        lambda: service.compare("bob", identity, identity),
    ]
    for action in actions:
        with pytest.raises(ResearchError) as error:
            action()
        assert error.value.code == "NOT_FOUND"


def test_storage_survives_restart_and_integrity_tampering_is_detected(service, tmp_path, catalog):
    identity = approved_run(service)
    expected = service.store.artifact("alice", identity)
    reopened = Store(tmp_path / "research.sqlite3")
    assert reopened.artifact("alice", identity) == expected
    run = reopened.get("runs", identity, "alice")
    with reopened.transaction() as db:
        db.execute("UPDATE artifacts SET content=? WHERE hash=?", ('{"tampered":true}', run["artifact_hash"]))
    with pytest.raises(ResearchError) as error:
        reopened.artifact("alice", identity)
    assert error.value.code == "ARTIFACT_WRITE_FAILED"
    reopened.close()


def test_invalid_transition_and_interruption_recovery(service):
    spec = service.template()
    identity = service.store.queue_diagnostic("alice", spec, "recovery")
    with pytest.raises(ResearchError):
        service.store.transition("alice", identity, "COMPLETED", artifact={"fake": True})
    assert service.store.get("runs", identity, "alice")["state"] == "QUEUED"
    assert service.store.recover_interrupted() == 1
    assert service.view("alice", identity)["error"] == "WORKER_INTERRUPTED"
    assert service.store.recover_interrupted() == 0


def test_failed_corrected_run_does_not_overwrite_parent(service, monkeypatch):
    parent = approved_run(service, overrides={"fee_bps_each_side": "0", "slippage_bps_each_side": "0"})
    original = service.store.artifact("alice", parent)
    correction = service.propose("alice", parent, "costs")
    child = service.store.approve_rerun("alice", correction["id"], correction["hash"], "child")

    def unavailable(_):
        raise ResearchError("DATASET_UNAVAILABLE", "unavailable", 503)

    monkeypatch.setattr(service.catalog, "load", unavailable)
    assert service.execute("alice", child)["state"] == "FAILED"
    assert service.view("alice", child)["error"] == "DATASET_UNAVAILABLE"
    assert service.store.artifact("alice", parent) == original
    with pytest.raises(ResearchError):
        service.store.artifact("alice", child)


def test_transaction_rolls_back_on_artifact_write_failure(service, monkeypatch):
    original = service.store.transition

    def fail_completion(workspace, identity, target, **kwargs):
        if target == "COMPLETED":
            raise ResearchError("ARTIFACT_WRITE_FAILED", "injected failure", 503)
        return original(workspace, identity, target, **kwargs)

    monkeypatch.setattr(service.store, "transition", fail_completion)
    identity = approved_run(service)
    assert service.view("alice", identity)["state"] == "FAILED"
    assert service.view("alice", identity)["artifact_hash"] is None
