
import asyncio
from contextlib import asynccontextmanager
from time import monotonic
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.cors import CORSMiddleware

from src.api.frontend import register_frontend_routes
from src.api.routers import (
    ai_router,
    admin_router,
    auth_router,
    config_router,
    rooms_router,
    upload_router,
    version_control_router,
)
from src.infra.config import config
from src.infra.metrics import inc_counter, observe_ms, prom_text
from src.infra.singleton_canvas import bootstrap_singleton_canvas
from src.infra.startup import (
    ensure_bind_available,
    resolve_server_host,
    resolve_server_port,
    resolve_server_reload,
)
from src.infra.logging import get_logger, setup_logging
from src.middleware.rate_limit import RateLimitMiddleware
from src.api.policy import PolicyErrorCode, normalize_http_exception
from src.persistence.db.engine import init_db
from src.realtime.yjs.server import asgi_server, background_compaction_task, websocket_server
from starlette.applications import Starlette

app_logger = get_logger(__name__)


def _normalize_error_code(status_code: int, detail: Any) -> str:
    if isinstance(detail, str):
        if detail in {
            "authentication_required",
            "invalid_token",
            PolicyErrorCode.AUTHZ_DENIED,
        }:
            return PolicyErrorCode.AUTHZ_DENIED
        if detail == PolicyErrorCode.RATE_LIMIT_EXCEEDED:
            return PolicyErrorCode.RATE_LIMIT_EXCEEDED
        if detail in {"room_not_found", "ROOM_NOT_FOUND", "run_not_found"}:
            return PolicyErrorCode.ROOM_NOT_FOUND
        if detail in {"room_membership_required", "room_owner_required", "room_not_accessible"}:
            return PolicyErrorCode.ROOM_MEMBERSHIP_REQUIRED
        if detail == PolicyErrorCode.AI_CIRCUIT_OPEN:
            return PolicyErrorCode.AI_CIRCUIT_OPEN
        if detail == PolicyErrorCode.TXN_ROLLBACK:
            return PolicyErrorCode.TXN_ROLLBACK

    if status_code == 401 or status_code == 403:
        return PolicyErrorCode.AUTHZ_DENIED
    if status_code == 404:
        return PolicyErrorCode.ROOM_NOT_FOUND
    return "INTERNAL_ERROR"


@asynccontextmanager
async def lifespan(_app):
    websocket_task: asyncio.Task[None] | None = None
    bg_task: asyncio.Task[None] | None = None

    setup_logging()
    init_db()
    bootstrap_singleton_canvas()
    websocket_task = asyncio.create_task(websocket_server.start())
    started_wait = asyncio.create_task(websocket_server.started.wait())
    done, _ = await asyncio.wait(
        {websocket_task, started_wait},
        return_when=asyncio.FIRST_COMPLETED,
    )
    if websocket_task in done:
        await websocket_task
        raise RuntimeError("Websocket server exited before startup completed")
    await started_wait
    app_logger.info("Starting SyncCanvas service")

    bg_task = asyncio.create_task(background_compaction_task())
    try:
        yield
    finally:
        if bg_task is not None:
            bg_task.cancel()
            try:
                await bg_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        if websocket_task is not None and not websocket_task.done():
            try:
                await websocket_server.stop()
            except RuntimeError:
                websocket_task.cancel()
        if websocket_task is not None:
            try:
                await websocket_task
            except asyncio.CancelledError:
                pass
        app_logger.info("Shutdown SyncCanvas service")


app = FastAPI(title="SyncCanvas", version=config.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(ai_router, prefix="/api")
# Single-instance mode keeps auth helpers in codebase, but disables the login entrypoint.
# app.include_router(auth_router, prefix="/api")
# The current UI still depends on room-scoped HTTP APIs for history and managed diagram rebuilds.
app.include_router(rooms_router, prefix="/api")
app.include_router(version_control_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(upload_router)
app.include_router(admin_router)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    request.state.request_id = request_id
    started_at = monotonic()

    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (monotonic() - started_at) * 1000
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        inc_counter(
            "http_requests_total",
            labels={
                "method": request.method,
                "path": path,
                "status": "500",
                "outcome": "exception",
            },
        )
        observe_ms(
            "http_request_duration_ms",
            elapsed_ms,
            {"method": request.method, "path": path, "status": "500"},
        )
        app_logger.exception(
            "Unhandled request error",
            extra={
                "trace_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "latency_ms": round(elapsed_ms, 2),
            },
        )
        raise

    elapsed_ms = (monotonic() - started_at) * 1000
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    inc_counter(
        "http_requests_total",
        labels={
            "method": request.method,
            "path": path,
            "status": str(response.status_code),
            "outcome": "success",
        },
    )
    observe_ms(
        "http_request_duration_ms",
        elapsed_ms,
        {"method": request.method, "path": path, "status": str(response.status_code)},
    )
    response.headers["X-Request-ID"] = request_id
    for header_name, header_value in getattr(request.state, "rate_limit_headers", {}).items():
        response.headers[header_name] = header_value
    return response


@app.exception_handler(HTTPException)
async def policy_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = request.state.request_id if hasattr(request.state, "request_id") else None
    normalized = normalize_http_exception(exc, use_legacy_detail=False)
    detail = normalized.detail
    if isinstance(detail, dict):
        payload = dict(detail)
        payload.setdefault("request_id", str(request_id))
        payload.setdefault("trace_id", str(request_id))
        payload.setdefault("path", request.url.path)
        payload.setdefault("status_code", str(normalized.status_code))
        if request_id is None:
            payload.setdefault("request_id", str(request_id))
        return JSONResponse(status_code=normalized.status_code, content=payload)

    if not isinstance(detail, str):
        detail = str(detail)

    code = _normalize_error_code(normalized.status_code, detail)
    if code in {
        PolicyErrorCode.AUTHZ_DENIED,
        PolicyErrorCode.RATE_LIMIT_EXCEEDED,
        PolicyErrorCode.ROOM_NOT_FOUND,
        PolicyErrorCode.ROOM_MEMBERSHIP_REQUIRED,
        PolicyErrorCode.AI_CIRCUIT_OPEN,
        PolicyErrorCode.TXN_ROLLBACK,
    }:
        payload = {
            "code": code,
            "message": detail,
            "request_id": request_id,
            "trace_id": request_id,
            "path": request.url.path,
            "status_code": normalized.status_code,
        }
        return JSONResponse(status_code=normalized.status_code, content=payload)

    return JSONResponse(
        status_code=normalized.status_code,
        content={"detail": detail, "request_id": request_id, "trace_id": request_id},
    )


@app.get("/internal/healthz")
def internal_healthz():
    """Process-level health probe."""

    return {"status": "ok", "version": config.version}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics_endpoint() -> str:
    """Prometheus compatible metrics payload."""

    return prom_text()


if callable(asgi_server):
    ws_app = asgi_server
else:
    ws_app = Starlette(routes=[])
app.mount("/ws", ws_app)  # type: ignore
register_frontend_routes(app)


if __name__ == "__main__":
    import uvicorn

    host = resolve_server_host()
    port = resolve_server_port()
    reload_enabled = resolve_server_reload()
    ensure_bind_available(host, port)
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload_enabled,
    )
