"""Start a local single-process server with visible startup diagnostics."""

import os

from .config import enabled, server_address


def main():
    # Emit this before importing the web stack, so slow initialization is visible.
    print("QuantForge: initializing the local research workspace...", flush=True)
    if len(os.environ.get("QUANTFORGE_API_TOKEN", "")) < 32 and not enabled("QUANTFORGE_PUBLIC_DEMO"):
        raise SystemExit(
            "QUANTFORGE_API_TOKEN is missing or too short. Set a private token of at least "
            "32 characters in this same PowerShell window (or shell), then run this command again. "
            "For anonymous synthetic demos, explicitly set QUANTFORGE_PUBLIC_DEMO=true."
        )

    import uvicorn

    host, port = server_address()
    print(f"QuantForge: starting HTTP on http://{host}:{port}/", flush=True)
    print("Keep this terminal open. Wait for 'Application startup complete' before opening the page.", flush=True)
    uvicorn.run("backend.api:create_app", factory=True, host=host, port=port, workers=1)


if __name__ == "__main__":
    main()
