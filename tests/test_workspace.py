from conftest import TOKEN_B
from test_api import make_run


def test_workspace_served_without_disclosing_credentials(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "QuantForge" in page.text
    assert "script-src" in page.headers["content-security-policy"]
    assert "'unsafe-inline'" not in page.headers["content-security-policy"]
    assert page.headers["cache-control"] == "no-store"
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/assets/style.css").status_code == 200
    assert client.get("/assets/icon.svg").status_code == 200
    assert client.get("/assets/../backend/store.py").status_code == 404
    assert client.get("/assets/package.json").status_code == 404
    assert client.get("/assets/node_modules/prettier/package.json").status_code == 404


def test_workspace_history_is_bounded_and_scoped(client):
    first, _ = make_run(client, key="history-one")
    second, _ = make_run(client, key="history-two")
    rows = client.get("/api/runs").json()
    assert len(rows) == 2
    assert rows[0]["run_id"] == second["run_id"]
    assert {r["run_id"] for r in rows} == {first["run_id"], second["run_id"]}
    assert all("spec" not in r and "workspace" not in r for r in rows)
    assert len(client.get("/api/runs?limit=1").json()) == 1
    assert client.get("/api/runs?limit=101").status_code == 422
    client.headers["Authorization"] = f"Bearer {TOKEN_B}"
    assert client.get("/api/runs").json() == []


def test_history_requires_authentication(client):
    client.headers.pop("Authorization")
    assert client.get("/api/runs").status_code == 401
    assert client.get("/").status_code == 200
