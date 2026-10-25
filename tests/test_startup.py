import pytest

from backend.__main__ import main


def test_startup_explains_missing_token_before_starting_server(monkeypatch, capsys):
    monkeypatch.delenv("QUANTFORGE_API_TOKEN", raising=False)
    with pytest.raises(SystemExit, match="same PowerShell window"):
        main()
    assert "initializing" in capsys.readouterr().out


def test_startup_shows_address_without_echoing_secret(monkeypatch, capsys):
    import uvicorn

    secret = "startup-test-only-token-with-32-characters"
    monkeypatch.setenv("QUANTFORGE_API_TOKEN", secret)
    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    main()
    output = capsys.readouterr().out
    assert "http://127.0.0.1:8000/" in output
    assert secret not in output
    assert calls[0][1] == {"factory": True, "host": "127.0.0.1", "port": 8000, "workers": 1}


def test_cloud_port_and_demo_startup_require_no_shared_browser_secret(monkeypatch, capsys):
    import uvicorn

    monkeypatch.delenv("QUANTFORGE_API_TOKEN", raising=False)
    monkeypatch.setenv("QUANTFORGE_PUBLIC_DEMO", "true")
    monkeypatch.setenv("PORT", "10000")
    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: calls.append(kwargs))
    main()
    assert calls == [{"factory": True, "host": "0.0.0.0", "port": 10000, "workers": 1}]
    assert "0.0.0.0:10000" in capsys.readouterr().out


@pytest.mark.parametrize("port", ["0", "65536", "nonsense"])
def test_invalid_cloud_port_is_rejected(monkeypatch, port):
    from backend.config import server_address

    monkeypatch.setenv("PORT", port)
    with pytest.raises(ValueError, match="PORT"):
        server_address()
