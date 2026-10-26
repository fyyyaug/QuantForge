"""Explicit local/cloud settings and small, bounded public-demo allowances."""

import os
from dataclasses import dataclass


def enabled(name: str) -> bool:
    value = os.environ.get(name, "false").lower()
    if value not in {"true", "false", "1", "0"}:
        raise ValueError(f"{name} must be true or false")
    return value in {"true", "1"}


@dataclass(frozen=True)
class DemoPolicy:
    ttl_seconds: int = 7200
    sessions_per_hour: int = 30
    requests_per_minute: int = 120
    requests_per_session: int = 600
    max_runs: int = 12
    max_plans: int = 24
    max_corrections: int = 24

    def public(self):
        return {
            "session_minutes": self.ttl_seconds // 60,
            "max_runs": self.max_runs,
            "max_plans": self.max_plans,
            "max_corrections": self.max_corrections,
            "requests_per_minute": self.requests_per_minute,
            "requests_per_session": self.requests_per_session,
        }


def server_address():
    host = os.environ.get("QUANTFORGE_HOST", "0.0.0.0" if "PORT" in os.environ else "127.0.0.1")
    try:
        port = int(os.environ.get("PORT", "8000"))
    except ValueError as exc:
        raise ValueError("PORT must be an integer from 1 to 65535") from exc
    if not host or not 1 <= port <= 65535:
        raise ValueError("Set QUANTFORGE_HOST and a PORT from 1 to 65535")
    return host, port
