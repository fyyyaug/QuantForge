from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.data import DatasetCatalog
from backend.service import ResearchService
from backend.store import Store

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
TOKEN_A = "a" * 32
TOKEN_B = "b" * 32


@pytest.fixture
def catalog():
    return DatasetCatalog(FIXTURES)


@pytest.fixture
def service(tmp_path, catalog):
    store = Store(tmp_path / "research.sqlite3")
    yield ResearchService(store, catalog)
    store.close()


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path, {TOKEN_A: "alice", TOKEN_B: "bob"}, FIXTURES)
    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {TOKEN_A}"
        yield client


def approved_run(service, *, workspace="alice", dataset="clean_momentum", overrides=None, key="run"):
    spec = service.template(dataset, overrides)
    plan = service.store.create_plan(workspace, spec)
    service.store.approve(workspace, plan["id"], plan["revision"], plan["hash"])
    identity = service.store.queue_plan(workspace, plan["id"], plan["revision"], plan["hash"], key)
    service.execute(workspace, identity)
    return identity
