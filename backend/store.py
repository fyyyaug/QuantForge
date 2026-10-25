"""Transactional SQLite persistence with immutable, hash-checked artifacts.

The foundation executes synchronously. Interrupted runs are failed on explicit
single-process recovery, never silently resumed or presented as complete.
"""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .canonical import canonical, digest
from .errors import ResearchError

TRANSITIONS = {
    "QUEUED": {"VALIDATING", "CANCELLED", "FAILED"},
    "VALIDATING": {"RUNNING", "AUDITING", "FAILED"},
    "RUNNING": {"AUDITING", "FAILED"},
    "AUDITING": {"REPORTING", "FAILED"},
    "REPORTING": {"COMPLETED", "FAILED"},
    "COMPLETED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}


def now():
    return datetime.now(UTC).isoformat()


def uid():
    return uuid4().hex


class Store:
    def __init__(self, path: Path, demo_policy=None):
        self.demo_policy = demo_policy
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY, workspace TEXT NOT NULL, revision INTEGER NOT NULL,
                spec TEXT NOT NULL, hash TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY, workspace TEXT NOT NULL, spec TEXT NOT NULL,
                spec_hash TEXT NOT NULL, mode TEXT NOT NULL, parent_id TEXT REFERENCES runs(id),
                state TEXT NOT NULL, error TEXT, artifact_hash TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                run_id TEXT REFERENCES runs(id), sequence INTEGER, state TEXT, timestamp TEXT,
                PRIMARY KEY (run_id, sequence)
            );
            CREATE TABLE IF NOT EXISTS artifacts (hash TEXT PRIMARY KEY, content TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS requests (
                workspace TEXT, action TEXT, key TEXT, hash TEXT NOT NULL, run_id TEXT REFERENCES runs(id),
                PRIMARY KEY(workspace, action, key)
            );
            CREATE TABLE IF NOT EXISTS corrections (
                id TEXT PRIMARY KEY, workspace TEXT NOT NULL, parent_id TEXT REFERENCES runs(id),
                proposal TEXT NOT NULL, hash TEXT NOT NULL, child_id TEXT REFERENCES runs(id)
            );
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY, entity TEXT NOT NULL, entity_id TEXT NOT NULL,
                workspace TEXT NOT NULL, revision_hash TEXT NOT NULL, timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS demo_sessions (
                token_hash TEXT PRIMARY KEY, workspace TEXT UNIQUE NOT NULL, expires_at INTEGER NOT NULL,
                requests INTEGER NOT NULL DEFAULT 0, revoked INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS demo_counters (
                scope TEXT, window INTEGER, count INTEGER NOT NULL, PRIMARY KEY(scope,window)
            );
        """)
        self.db.commit()

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield self.db
                self.db.commit()
            except BaseException:
                self.db.rollback()
                raise

    @staticmethod
    def owned(db, table, identity, workspace):
        if table not in {"plans", "runs", "corrections"}:
            raise ValueError("Invalid internal table")
        row = db.execute(f"SELECT * FROM {table} WHERE id=? AND workspace=?", (identity, workspace)).fetchone()
        if row is None:
            raise ResearchError("NOT_FOUND", "Resource not found", 404)
        return dict(row)

    def get(self, table, identity, workspace):
        with self.lock:
            return self.owned(self.db, table, identity, workspace)

    def list_runs(self, workspace, limit=50):
        with self.lock:
            return [
                dict(row)
                for row in self.db.execute(
                    "SELECT * FROM runs WHERE workspace=? ORDER BY created_at DESC,id DESC LIMIT ?",
                    (workspace, limit),
                )
            ]

    def create_plan(self, workspace, spec):
        with self.transaction() as db:
            self.check_demo_capacity(db, workspace, "plans")
            identity = uid()
            db.execute(
                "INSERT INTO plans VALUES(?,?,?,?,?,0)",
                (
                    identity,
                    workspace,
                    1,
                    canonical(spec),
                    digest(spec),
                ),
            )
        return self.get("plans", identity, workspace)

    def revise(self, workspace, identity, revision, spec):
        with self.transaction() as db:
            plan = self.owned(db, "plans", identity, workspace)
            if plan["revision"] != revision:
                raise ResearchError("STALE_APPROVAL", "Plan revision changed", 409)
            db.execute(
                "UPDATE plans SET revision=revision+1,spec=?,hash=?,approved=0 WHERE id=?",
                (canonical(spec), digest(spec), identity),
            )
        return self.get("plans", identity, workspace)

    def approve(self, workspace, identity, revision, spec_hash):
        with self.transaction() as db:
            plan = self.owned(db, "plans", identity, workspace)
            if plan["revision"] != revision or plan["hash"] != spec_hash:
                raise ResearchError("STALE_APPROVAL", "Approval does not match current plan", 409)
            db.execute("UPDATE plans SET approved=1 WHERE id=?", (identity,))
            db.execute(
                "INSERT INTO approvals VALUES(?,?,?,?,?,?)", (uid(), "plan", identity, workspace, spec_hash, now())
            )
        return self.get("plans", identity, workspace)

    def insert_run(self, db, workspace, spec, mode, parent=None):
        self.check_demo_capacity(db, workspace, "runs")
        identity, timestamp = uid(), now()
        db.execute(
            "INSERT INTO runs VALUES(?,?,?,?,?,?,?,NULL,NULL,?,?)",
            (identity, workspace, canonical(spec), digest(spec), mode, parent, "QUEUED", timestamp, timestamp),
        )
        db.execute("INSERT INTO events VALUES(?,?,?,?)", (identity, 1, "QUEUED", timestamp))
        return identity

    @staticmethod
    def request(db, workspace, action, key, request_hash):
        row = db.execute(
            "SELECT * FROM requests WHERE workspace=? AND action=? AND key=?", (workspace, action, key)
        ).fetchone()
        if row:
            if row["hash"] != request_hash:
                raise ResearchError("IDEMPOTENCY_CONFLICT", "Key already used with different request", 409)
            return row["run_id"]
        return None

    def queue_plan(self, workspace, plan_id, revision, spec_hash, key):
        request_hash = digest([plan_id, revision, spec_hash])
        with self.transaction() as db:
            existing = self.request(db, workspace, "run", key, request_hash)
            if existing:
                return existing
            plan = self.owned(db, "plans", plan_id, workspace)
            if not plan["approved"] or plan["revision"] != revision or plan["hash"] != spec_hash:
                raise ResearchError("STALE_APPROVAL", "Approve the exact current plan before execution", 409)
            identity = self.insert_run(db, workspace, json.loads(plan["spec"]), "RESEARCH")
            db.execute("INSERT INTO requests VALUES(?,?,?,?,?)", (workspace, "run", key, request_hash, identity))
        return identity

    def queue_diagnostic(self, workspace, spec, key):
        request_hash = digest(spec)
        with self.transaction() as db:
            identity = self.request(db, workspace, "diagnostic", key, request_hash)
            if not identity:
                identity = self.insert_run(db, workspace, spec, "DIAGNOSTIC_INVALID")
                db.execute(
                    "INSERT INTO requests VALUES(?,?,?,?,?)", (workspace, "diagnostic", key, request_hash, identity)
                )
        return identity

    def transition(self, workspace, identity, target, *, error=None, artifact=None):
        with self.transaction() as db:
            run = self.owned(db, "runs", identity, workspace)
            if target not in TRANSITIONS[run["state"]]:
                raise ResearchError("STATE_CONFLICT", "Run state no longer permits this action", 409)
            artifact_hash = run["artifact_hash"]
            if artifact is not None:
                artifact_hash = digest(artifact)
                db.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?)", (artifact_hash, canonical(artifact)))
            if target == "COMPLETED" and not artifact_hash:
                raise ResearchError("ARTIFACT_WRITE_FAILED", "Completed run requires a stored artifact", 503)
            timestamp = now()
            db.execute(
                "UPDATE runs SET state=?,error=?,artifact_hash=?,updated_at=? WHERE id=?",
                (target, error, artifact_hash, timestamp, identity),
            )
            sequence = db.execute(
                "SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE run_id=?", (identity,)
            ).fetchone()[0]
            db.execute("INSERT INTO events VALUES(?,?,?,?)", (identity, sequence, target, timestamp))

    def artifact(self, workspace, identity):
        with self.lock:
            run = self.owned(self.db, "runs", identity, workspace)
            if run["state"] != "COMPLETED":
                raise ResearchError("RUN_NOT_READY", "Run has no completed artifact", 409)
            row = self.db.execute("SELECT content FROM artifacts WHERE hash=?", (run["artifact_hash"],)).fetchone()
            if row is None or digest(json.loads(row[0])) != run["artifact_hash"]:
                raise ResearchError("ARTIFACT_WRITE_FAILED", "Stored artifact integrity check failed", 503)
            return json.loads(row[0])

    def events(self, workspace, identity, after=0):
        with self.lock:
            self.owned(self.db, "runs", identity, workspace)
            return [
                dict(row)
                for row in self.db.execute(
                    "SELECT * FROM events WHERE run_id=? AND sequence>? ORDER BY sequence", (identity, after)
                )
            ]

    def correction(self, workspace, parent_id, proposal):
        with self.transaction() as db:
            self.owned(db, "runs", parent_id, workspace)
            self.check_demo_capacity(db, workspace, "corrections")
            identity = uid()
            db.execute(
                "INSERT INTO corrections VALUES(?,?,?,?,?,NULL)",
                (identity, workspace, parent_id, canonical(proposal), digest(proposal)),
            )
        return self.get("corrections", identity, workspace)

    def approve_rerun(self, workspace, identity, proposal_hash, key):
        request_hash = digest([identity, proposal_hash])
        with self.transaction() as db:
            existing = self.request(db, workspace, "rerun", key, request_hash)
            if existing:
                return existing
            correction = self.owned(db, "corrections", identity, workspace)
            if correction["hash"] != proposal_hash:
                raise ResearchError("STALE_APPROVAL", "Correction proposal changed", 409)
            if correction["child_id"]:
                identity_run = correction["child_id"]
            else:
                proposal = json.loads(correction["proposal"])
                identity_run = self.insert_run(db, workspace, proposal["spec"], "RESEARCH", correction["parent_id"])
                db.execute("UPDATE corrections SET child_id=? WHERE id=?", (identity_run, identity))
                db.execute(
                    "INSERT INTO approvals VALUES(?,?,?,?,?,?)",
                    (uid(), "correction", identity, workspace, proposal_hash, now()),
                )
            db.execute("INSERT INTO requests VALUES(?,?,?,?,?)", (workspace, "rerun", key, request_hash, identity_run))
        return identity_run

    def check_demo_capacity(self, db, workspace, table):
        if self.demo_policy is None or not workspace.startswith("demo:"):
            return
        limits = {
            "runs": self.demo_policy.max_runs,
            "plans": self.demo_policy.max_plans,
            "corrections": self.demo_policy.max_corrections,
        }
        if table not in limits:
            raise ValueError("Unsupported demo quota")
        count = db.execute(f"SELECT COUNT(*) FROM {table} WHERE workspace=?", (workspace,)).fetchone()[0]
        if count >= limits[table]:
            raise ResearchError("DEMO_QUOTA_REACHED", f"Demo limit reached: {limits[table]} {table} per session.", 429)

    def recover_interrupted(self):
        """Call only during startup of the documented single-process deployment."""
        with self.lock:
            rows = list(
                self.db.execute("SELECT id,workspace FROM runs WHERE state NOT IN ('COMPLETED','FAILED','CANCELLED')")
            )
        for row in rows:
            self.transition(row["workspace"], row["id"], "FAILED", error="WORKER_INTERRUPTED")
        return len(rows)

    def close(self):
        with self.lock:
            self.db.close()
