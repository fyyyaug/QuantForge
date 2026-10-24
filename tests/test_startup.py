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
