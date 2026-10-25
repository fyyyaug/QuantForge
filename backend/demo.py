"""Isolated anonymous sessions, hashed cookies, and persistent demo quotas."""

import hashlib
import secrets
import time
from uuid import uuid4

from .config import DemoPolicy
from .errors import ResearchError


class DemoAccess:
    def __init__(self, store, policy: DemoPolicy, clock=time.time):
        self.store, self.policy, self.clock = store, policy, clock

    @staticmethod
    def token_hash(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def consume(db, scope, window, limit, message):
        row = db.execute("SELECT count FROM demo_counters WHERE scope=? AND window=?", (scope, window)).fetchone()
        if row and row[0] >= limit:
            raise ResearchError("DEMO_RATE_LIMIT", message, 429)
        db.execute(
            "INSERT INTO demo_counters VALUES(?,?,1) ON CONFLICT(scope,window) DO UPDATE SET count=count+1",
            (scope, window),
        )

    def cleanup(self):
        """Remove only expired demo workspaces, preserving private runs and shared artifacts."""
        with self.store.transaction() as db:
            expired = [
                r[0]
                for r in db.execute(
                    "SELECT workspace FROM demo_sessions WHERE expires_at<=? AND NOT EXISTS "
                    "(SELECT 1 FROM runs WHERE runs.workspace=demo_sessions.workspace "
                    "AND state NOT IN ('COMPLETED','FAILED','CANCELLED'))",
                    (self.clock(),),
                )
            ]
            for workspace in expired:
                db.execute("DELETE FROM approvals WHERE workspace=?", (workspace,))
                db.execute("DELETE FROM requests WHERE workspace=?", (workspace,))
                db.execute("DELETE FROM events WHERE run_id IN (SELECT id FROM runs WHERE workspace=?)", (workspace,))
                db.execute("DELETE FROM corrections WHERE workspace=?", (workspace,))
                db.execute("DELETE FROM runs WHERE workspace=?", (workspace,))
                db.execute("DELETE FROM plans WHERE workspace=?", (workspace,))
                db.execute("DELETE FROM demo_sessions WHERE workspace=?", (workspace,))
                db.execute("DELETE FROM demo_counters WHERE scope=?", (workspace,))
            if expired:
                db.execute(
                    "DELETE FROM artifacts WHERE hash NOT IN (SELECT artifact_hash FROM runs WHERE artifact_hash IS NOT NULL)"
                )
            db.execute(
                "DELETE FROM demo_counters WHERE scope='issuance' AND window<?", (int(self.clock()) // 3600 - 1,)
            )

    def issue(self):
        self.cleanup()
        now = int(self.clock())
        token = secrets.token_urlsafe(40)
        workspace = f"demo:{uuid4().hex}"
        expires = now + self.policy.ttl_seconds
        with self.store.transaction() as db:
            self.consume(
                db,
                "issuance",
                now // 3600,
                self.policy.sessions_per_hour,
                "Public demo session capacity is reached for this hour. Please try again later.",
            )
            db.execute(
                "INSERT INTO demo_sessions(token_hash,workspace,expires_at) VALUES(?,?,?)",
                (self.token_hash(token), workspace, expires),
            )
        return token, {"workspace": workspace, "expires_at": expires}

    def peek(self, token):
        if not token or len(token) > 128:
            return None
        with self.store.lock:
            row = self.store.db.execute(
                "SELECT * FROM demo_sessions WHERE token_hash=? AND expires_at>? AND revoked=0",
                (self.token_hash(token), self.clock()),
            ).fetchone()
            return dict(row) if row else None

    def resolve(self, token):
        with self.store.transaction() as db:
            row = db.execute(
                "SELECT * FROM demo_sessions WHERE token_hash=? AND expires_at>? AND revoked=0",
                (self.token_hash(token[:129]), self.clock()),
            ).fetchone()
            if not row:
                raise ResearchError("SESSION_EXPIRED", "This demo session ended. Open a new demo to continue.", 401)
            if row["requests"] >= self.policy.requests_per_session:
                raise ResearchError("DEMO_QUOTA_REACHED", "This demo session has reached its request allowance.", 429)
            window = int(self.clock()) // 60
            self.consume(
                db,
                row["workspace"],
                window,
                self.policy.requests_per_minute,
                "This demo session is receiving too many requests. Please wait a minute.",
            )
            db.execute("DELETE FROM demo_counters WHERE scope=? AND window<?", (row["workspace"], window - 1))
            db.execute("UPDATE demo_sessions SET requests=requests+1 WHERE workspace=?", (row["workspace"],))
            return row["workspace"]

    def revoke(self, token):
        with self.store.transaction() as db:
            db.execute("UPDATE demo_sessions SET revoked=1 WHERE token_hash=?", (self.token_hash(token[:129]),))
