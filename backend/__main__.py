"""Start a local single-process server with explicit authentication."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("backend.api:create_app", factory=True, host="127.0.0.1", port=8000, workers=1)
