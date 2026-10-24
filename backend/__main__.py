"""Start a local single-process server with visible startup diagnostics."""

import os


def main():
    # Emit this before importing the web stack, so slow initialization is visible.
    print("QuantForge: initializing the local research workspace...", flush=True)
    if len(os.environ.get("QUANTFORGE_API_TOKEN", "")) < 32:
        raise SystemExit(
            "QUANTFORGE_API_TOKEN is missing or too short. Set a private token of at least "
            "32 characters in this same PowerShell window, then run this command again."
        )

    import uvicorn

    print("QuantForge: starting HTTP on http://127.0.0.1:8000/", flush=True)
    print("Keep this terminal open. Wait for 'Application startup complete' before opening the page.", flush=True)
    uvicorn.run("backend.api:create_app", factory=True, host="127.0.0.1", port=8000, workers=1)


if __name__ == "__main__":
    main()
