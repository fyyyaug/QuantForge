"""Local, single-process API. Shared-secret workspace tokens are not production auth."""

import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field, ValidationError

from .canonical import plain
from .config import DemoPolicy, enabled
from .data import DatasetCatalog
from .demo import DemoAccess
from .errors import ResearchError
from .evaluation import evaluate_audits
from .models import Contract, Cost, StrategySpec
from .planner import PARAMETERS, ClaudePlanner
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
    fixture_id: Literal["timing_trap", "leaky_next_close"] = "timing_trap"


class EmptyRequest(Contract):
    pass


class HypothesisRequest(Contract):
    dataset_id: str = Field(default="clean_momentum", max_length=80)
    hypothesis: str = Field(min_length=10, max_length=1200)


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
        "planning_mode": plan["planning"]["source"],
        "planning": plan["planning"],
    }


def correction_view(row):
    return {
        "correction_id": row["id"],
        "proposal_hash": row["hash"],
        "proposal": json.loads(row["proposal"]),
        "child_run_id": row["child_id"],
    }


def create_app(
    data_dir: Path | None = None,
    tokens: dict[str, str] | None = None,
    fixtures: Path = DEFAULT_FIXTURES,
    demo_policy: DemoPolicy | None = None,
    planner_provider: ClaudePlanner | None = None,
):
    planner_provider = planner_provider or ClaudePlanner.from_environment()
    if demo_policy is None and enabled("QUANTFORGE_PUBLIC_DEMO"):
        demo_policy = DemoPolicy()
    secure_cookie = enabled("QUANTFORGE_COOKIE_SECURE")
    cookie_name = "__Host-quantforge_demo" if secure_cookie else "quantforge_demo"
    if tokens is None:
        token = os.environ.get("QUANTFORGE_API_TOKEN", "")
        if token and len(token) < 32:
            raise ValueError("Configure workspace tokens with at least 32 characters")
        tokens = {token: "local"} if len(token) >= 32 else {}
    if (not tokens and demo_policy is None) or any(
        len(token) < 32 or not workspace or workspace.startswith("demo:") for token, workspace in tokens.items()
    ):
        raise ValueError("Configure workspace tokens with at least 32 characters; no insecure default is provided")
    tokens = dict(tokens)
    root = data_dir or Path(os.environ.get("QUANTFORGE_DATA_DIR", ".quantforge"))

    @asynccontextmanager
    async def lifespan(app):
        store = Store(root / "research.sqlite3", demo_policy)
        store.recover_interrupted()
        app.state.service = ResearchService(store, DatasetCatalog(fixtures))
        app.state.evaluation = evaluate_audits()
        app.state.demo = DemoAccess(store, demo_policy) if demo_policy else None
        if app.state.demo:
            app.state.demo.cleanup()
        try:
            yield
        finally:
            store.close()

    app = FastAPI(title="QuantForge Foundation API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    def same_origin(request):
        # A custom header cannot be sent by a cross-origin HTML form. No CORS
        # permission is granted for cross-origin JavaScript to add it.
        if request.headers.get("x-quantforge-request") != "workspace":
            raise ResearchError("ORIGIN_REJECTED", "Use the same-origin research workspace for demo actions.", 403)
        origin = request.headers.get("origin")
        if origin:
            scheme = "https" if secure_cookie else request.url.scheme
            if origin != f"{scheme}://{request.headers.get('host')}":
                raise ResearchError("ORIGIN_REJECTED", "Demo actions must originate from this workspace.", 403)

    def workspace(request: Request, authorization: Annotated[str | None, Header()] = None):
        bearer = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
        for token, owner in tokens.items():
            if hmac.compare_digest(bearer.encode("utf-8"), token.encode("utf-8")):
                return owner
        # An explicitly supplied bad credential must not fall back to a cookie.
        if not authorization and demo_policy is not None:
            cookie = request.cookies.get(cookie_name, "")
            if cookie:
                if request.method not in {"GET", "HEAD", "OPTIONS"}:
                    same_origin(request)
                return app.state.demo.resolve(cookie)
        raise ResearchError("UNAUTHORIZED", "Valid workspace bearer token required", 401)

    def key(idempotency_key: Annotated[str, Header(min_length=1, max_length=128)]):
        return idempotency_key

    W = Annotated[str, Depends(workspace)]
    K = Annotated[str, Depends(key)]

    def service():
        return app.state.service

    def safe_error(code, message, status, fields=None):
        return JSONResponse(
            {"error": {"code": code, "message": message, "fields": fields or [], "correlation_id": uuid4().hex}},
            status_code=status,
        )

    def validation_fields(exc):
        allowed = (
            set(StrategySpec.model_fields) | set(PARAMETERS) | {"hypothesis", "revision", "spec_hash", "proposal_hash"}
        )
        return sorted({str(part) for error in exc.errors() for part in error["loc"] if part in allowed})

    @app.exception_handler(ResearchError)
    async def domain_error(request, exc):
        return safe_error(exc.code, exc.message, exc.status)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Do not echo raw input or token-bearing request fields.
        return safe_error(
            "INVALID_REQUEST", "Check the required fields, formats and allowed ranges", 422, validation_fields(exc)
        )

    @app.exception_handler(ValidationError)
    async def invalid_spec(request, exc):
        return safe_error(
            "INVALID_SPEC", "Check strategy field ranges, precision and sample ordering", 422, validation_fields(exc)
        )

    @app.exception_handler(Exception)
    async def internal_error(request, exc):
        logger.exception("Unhandled API error", exc_info=exc)
        return safe_error("INTERNAL_ERROR", "Request could not be completed", 500)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.1.0", "execution": "synchronous_single_process"}

    @app.get("/api/workspace")
    def workspace_options(request: Request):
        session = app.state.demo.peek(request.cookies.get(cookie_name)) if demo_policy else None
        return {
            "planning_mode": "DETERMINISTIC_TEMPLATE",
            "planner": planner_provider.public(),
            "demo": {
                "enabled": demo_policy is not None,
                "session_active": session is not None,
                "expires_at": session["expires_at"] if session else None,
                "limits": demo_policy.public() if demo_policy else None,
            },
        }

    @app.post("/api/demo/session")
    def start_demo(body: EmptyRequest, request: Request, response: Response):
        if demo_policy is None:
            raise ResearchError("NOT_FOUND", "Public demo is not enabled", 404)
        same_origin(request)
        existing = app.state.demo.peek(request.cookies.get(cookie_name))
        if existing:
            return {"expires_at": existing["expires_at"], "limits": demo_policy.public()}
        token, session = app.state.demo.issue()
        response.set_cookie(
            cookie_name,
            token,
            max_age=demo_policy.ttl_seconds,
            httponly=True,
            secure=secure_cookie,
            samesite="strict",
            path="/",
        )
        return {"expires_at": session["expires_at"], "limits": demo_policy.public()}

    @app.post("/api/demo/session/logout")
    def end_demo(body: EmptyRequest, request: Request, response: Response):
        if demo_policy is None:
            raise ResearchError("NOT_FOUND", "Public demo is not enabled", 404)
        same_origin(request)
        app.state.demo.revoke(request.cookies.get(cookie_name, ""))
        response.delete_cookie(cookie_name, path="/", secure=secure_cookie, httponly=True, samesite="strict")
        return {"ended": True}

    @app.get("/api/datasets")
    def datasets(owner: W):
        return plain(service().catalog.list())

    @app.get("/api/evaluation")
    def audit_evaluation(owner: W):
        return app.state.evaluation

    @app.get("/api/runs")
    def history(owner: W, limit: int = Query(50, ge=1, le=100)):
        return service().history(owner, limit)

    @app.post("/api/research/plans", status_code=201)
    def create_plan(body: PlanRequest, owner: W):
        spec = service().template(body.dataset_id, body.overrides)
        return plan_view(service().store.create_plan(owner, spec))

    @app.post("/api/research/hypotheses")
    def draft_hypothesis(body: HypothesisRequest, owner: W):
        # Resolve data locally before any external call. No data rows, tokens,
        # private reports or filesystem context are sent to the provider.
        service().template(body.dataset_id)
        answer, provenance = planner_provider.draft(service().store, owner, body.hypothesis)
        if answer.status != "PLAN":
            return {
                "status": answer.status,
                "reason": answer.reason,
                "question": answer.question,
                "message": "Clarify the requested strategy before creating a plan."
                if answer.status == "CLARIFY"
                else "This request is outside the supported strategy. Use the template or revise the hypothesis.",
            }
        try:
            spec = service().template(body.dataset_id, answer.parameters.model_dump(exclude_none=True))
        except (ValidationError, ResearchError):
            raise ResearchError(
                "PLANNER_INVALID_OUTPUT",
                "AI proposed unsupported parameters. No plan was created; use the template.",
                422,
            ) from None
        plan = service().store.create_plan(owner, spec, provenance)
        return {"status": "PLAN", "plan": plan_view(plan)}

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

    @app.get("/api/runs/{run_id}/comparison/report", response_class=PlainTextResponse)
    def comparison_report(run_id: str, other_run_id: str, owner: W):
        return service().comparison_report(owner, run_id, other_run_id)

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
