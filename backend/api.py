"""Local, single-process API. Shared-secret workspace tokens are not production auth."""

import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field, ValidationError

from .canonical import plain
from .data import DatasetCatalog
from .errors import ResearchError
from .models import Contract, Cost, StrategySpec
from .service import ResearchService
from .store import Store

DEFAULT_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
DEFAULT_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        async def secured(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"cache-control", b"no-store"),
                        (b"x-frame-options", b"DENY"),
                    ]
                )
                # Swagger's separate documentation page needs its own CDN assets.
                # The research workspace uses only same-origin external JS/CSS.
                if not scope.get("path", "").startswith(("/docs", "/redoc")):
                    headers.append(
                        (
                            b"content-security-policy",
                            b"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
                        )
                    )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, secured)


class BodyLimitMiddleware:
    """Bound and replay the ASGI body without depending on Request internals."""

    def __init__(self, app, limit=65536):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        messages, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.limit:
                response = JSONResponse(
                    {"error": {"code": "RESOURCE_LIMIT", "message": "Request body exceeds 64 KiB"}}, status_code=413
                )
                return await response(scope, receive, send)
            messages.append(message)
            if not message.get("more_body", False):
                break
        iterator = iter(messages)

        async def replay():
            try:
                return next(iterator)
            except StopIteration:
                # Streaming/static responses listen for disconnects. Replaying
                # endless empty request messages would starve their event loop.
                return await receive()

        await self.app(scope, replay, send)


class PlanRequest(Contract):
    dataset_id: str = "clean_momentum"
    overrides: dict = Field(default_factory=dict)


class Approval(Contract):
    revision: int = Field(ge=1, strict=True)
    spec_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class EditPlan(Contract):
    revision: int = Field(ge=1, strict=True)
    spec: StrategySpec


class RunRequest(Approval):
    plan_id: str


class DiagnosticRequest(Contract):
    fixture_id: Literal["leaky_next_close"] = "leaky_next_close"


class CorrectionRequest(Contract):
    kind: Literal["timing", "costs"]
    fee_bps_each_side: Cost = 5
    slippage_bps_each_side: Cost = 5


class CorrectionApproval(Contract):
    proposal_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


def plan_view(plan):
    spec = json.loads(plan["spec"])
    return {
        "plan_id": plan["id"],
        "revision": plan["revision"],
        "spec_hash": plan["hash"],
        "approved": bool(plan["approved"]),
        "spec": spec,
        "assumptions": "Template defaults are explicit in spec; review all fields before approval.",
        "planning_mode": "DETERMINISTIC_TEMPLATE",
    }


def correction_view(row):
    return {
        "correction_id": row["id"],
        "proposal_hash": row["hash"],
        "proposal": json.loads(row["proposal"]),
        "child_run_id": row["child_id"],
    }


def create_app(data_dir: Path | None = None, tokens: dict[str, str] | None = None, fixtures: Path = DEFAULT_FIXTURES):
    if tokens is None:
        token = os.environ.get("QUANTFORGE_API_TOKEN", "")
        tokens = {token: "local"} if len(token) >= 32 else {}
    if not tokens or any(len(token) < 32 or not workspace for token, workspace in tokens.items()):
        raise ValueError("Configure workspace tokens with at least 32 characters; no insecure default is provided")
    tokens = dict(tokens)
    root = data_dir or Path(os.environ.get("QUANTFORGE_DATA_DIR", ".quantforge"))

    @asynccontextmanager
    async def lifespan(app):
        store = Store(root / "research.sqlite3")
        store.recover_interrupted()
        app.state.service = ResearchService(store, DatasetCatalog(fixtures))
        try:
            yield
        finally:
            store.close()

    app = FastAPI(title="QuantForge Foundation API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    def workspace(authorization: Annotated[str | None, Header()] = None):
        bearer = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
        for token, owner in tokens.items():
            if hmac.compare_digest(bearer.encode("utf-8"), token.encode("utf-8")):
                return owner
        raise ResearchError("UNAUTHORIZED", "Valid workspace bearer token required", 401)

    def key(idempotency_key: Annotated[str, Header(min_length=1, max_length=128)]):
        return idempotency_key

    W = Annotated[str, Depends(workspace)]
    K = Annotated[str, Depends(key)]

    def service():
        return app.state.service

    def safe_error(code, message, status):
        return JSONResponse(
            {"error": {"code": code, "message": message, "correlation_id": uuid4().hex}}, status_code=status
        )

    @app.exception_handler(ResearchError)
    async def domain_error(request, exc):
        return safe_error(exc.code, exc.message, exc.status)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Do not echo raw input or token-bearing request fields.
        return safe_error("INVALID_REQUEST", "Request does not match the supported contract", 422)

    @app.exception_handler(ValidationError)
    async def invalid_spec(request, exc):
        return safe_error("INVALID_SPEC", "Strategy fields violate the supported model", 422)

    @app.exception_handler(Exception)
    async def internal_error(request, exc):
        logger.exception("Unhandled API error", exc_info=exc)
        return safe_error("INTERNAL_ERROR", "Request could not be completed", 500)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.1.0", "execution": "synchronous_single_process"}

    @app.get("/api/datasets")
    def datasets(owner: W):
        return plain(service().catalog.list())

    @app.get("/api/runs")
    def history(owner: W, limit: int = Query(50, ge=1, le=100)):
        return service().history(owner, limit)

    @app.post("/api/research/plans", status_code=201)
    def create_plan(body: PlanRequest, owner: W):
        spec = service().template(body.dataset_id, body.overrides)
        return plan_view(service().store.create_plan(owner, spec))

    @app.get("/api/research/plans/{plan_id}")
    def get_plan(plan_id: str, owner: W):
        return plan_view(service().store.get("plans", plan_id, owner))

    @app.patch("/api/research/plans/{plan_id}")
    def edit_plan(plan_id: str, body: EditPlan, owner: W):
        return plan_view(service().store.revise(owner, plan_id, body.revision, body.spec))

    @app.post("/api/research/plans/{plan_id}/approve")
    def approve(plan_id: str, body: Approval, owner: W):
        return plan_view(service().store.approve(owner, plan_id, body.revision, body.spec_hash))

    @app.post("/api/research/runs", status_code=201)
    def run(body: RunRequest, owner: W, request_key: K):
        identity = service().store.queue_plan(owner, body.plan_id, body.revision, body.spec_hash, request_key)
        return service().execute(owner, identity)

    @app.post("/api/demo/diagnostic-runs", status_code=201)
    def diagnostic(body: DiagnosticRequest, owner: W, request_key: K):
        spec = service().template(body.fixture_id)
        identity = service().store.queue_diagnostic(owner, spec, request_key)
        return service().execute(owner, identity)

    @app.get("/api/runs/{run_id}")
    def view_run(run_id: str, owner: W):
        return service().view(owner, run_id)

    @app.get("/api/runs/{run_id}/events")
    def events(run_id: str, owner: W, after: int = Query(0, ge=0)):
        return service().store.events(owner, run_id, after)

    @app.get("/api/runs/{run_id}/artifact")
    def artifact(run_id: str, owner: W):
        return service().store.artifact(owner, run_id)

    @app.get("/api/runs/{run_id}/result")
    def result(run_id: str, owner: W):
        return service().store.artifact(owner, run_id)["result"]

    @app.get("/api/runs/{run_id}/audit")
    def findings(run_id: str, owner: W):
        artifact = service().store.artifact(owner, run_id)
        return {"admissibility": artifact["admissibility"], "findings": artifact["findings"]}

    @app.get("/api/runs/{run_id}/report", response_class=PlainTextResponse)
    def report(run_id: str, owner: W):
        return service().store.artifact(owner, run_id)["report"]

    @app.post("/api/runs/{run_id}/corrections", status_code=201)
    def correction(run_id: str, body: CorrectionRequest, owner: W):
        return correction_view(
            service().propose(owner, run_id, body.kind, body.fee_bps_each_side, body.slippage_bps_each_side)
        )

    @app.post("/api/corrections/{correction_id}/approve-and-rerun", status_code=201)
    def rerun(correction_id: str, body: CorrectionApproval, owner: W, request_key: K):
        identity = service().store.approve_rerun(owner, correction_id, body.proposal_hash, request_key)
        return service().execute(owner, identity)

    @app.get("/api/runs/{run_id}/comparison")
    def comparison(run_id: str, other_run_id: str, owner: W):
        return service().compare(owner, run_id, other_run_id)

    @app.post("/api/runs/{run_id}/cancel")
    def cancel(run_id: str, owner: W):
        # In-flight synchronous work is not cancellable; no false success.
        run = service().view(owner, run_id)
        if run["state"] == "QUEUED":
            service().store.transition(owner, run_id, "CANCELLED")
            return service().view(owner, run_id)
        raise ResearchError("STATE_CONFLICT", "Only queued runs can be cancelled in this foundation", 409)

    if DEFAULT_FRONTEND.is_dir():
        app.mount("/assets", StaticFiles(directory=DEFAULT_FRONTEND / "assets"), name="workspace-assets")

        @app.get("/", include_in_schema=False)
        def workspace_page():
            return FileResponse(DEFAULT_FRONTEND / "index.html")

    return app
