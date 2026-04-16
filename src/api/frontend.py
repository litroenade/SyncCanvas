
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
FRONTEND_INDEX_PATH = FRONTEND_DIST_DIR / "index.html"
EXCLUDED_FRONTEND_PREFIXES = (
    "/api",
    "/ws",
    "/metrics",
    "/internal",
    "/docs",
    "/redoc",
    "/openapi.json",
)


def frontend_bundle_available() -> bool:
    return FRONTEND_INDEX_PATH.is_file()


def _frontend_instructions() -> str:
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SyncCanvas Frontend Not Built</title>
    <style>
      body { font-family: sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
      main { max-width: 720px; margin: 8rem auto; padding: 0 1.5rem; }
      code { background: rgba(148, 163, 184, 0.15); padding: 0.15rem 0.35rem; border-radius: 0.35rem; }
      pre { background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(148, 163, 184, 0.2); padding: 1rem; border-radius: 0.75rem; overflow-x: auto; }
    </style>
  </head>
  <body>
    <main>
      <h1>Frontend bundle is not available.</h1>
      <p>Build the frontend with <code>pnpm build</code> in <code>frontend/</code>, or run the Vite dev server with <code>pnpm dev</code>.</p>
      <pre>cd frontend
pnpm build

# or during development
pnpm dev</pre>
    </main>
  </body>
</html>
"""


def _resolve_frontend_file(request_path: str) -> Path | None:
    if not request_path:
        return FRONTEND_INDEX_PATH if frontend_bundle_available() else None

    candidate = (FRONTEND_DIST_DIR / request_path.lstrip("/")).resolve()
    dist_root = FRONTEND_DIST_DIR.resolve()
    if candidate == dist_root or dist_root not in candidate.parents:
        return None
    if candidate.is_file():
        return candidate
    return None


def _serve_frontend_path(request_path: str) -> Response:
    if not frontend_bundle_available():
        return HTMLResponse(_frontend_instructions(), status_code=503)

    static_file = _resolve_frontend_file(request_path)
    if static_file is not None:
        return FileResponse(static_file)
    return FileResponse(FRONTEND_INDEX_PATH)


def register_frontend_routes(app: FastAPI) -> None:
    @app.get("/", include_in_schema=False)
    async def frontend_index() -> Response:
        return _serve_frontend_path("")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def frontend_spa(full_path: str) -> Response:
        normalized_path = f"/{full_path.lstrip('/')}"
        if normalized_path.startswith(EXCLUDED_FRONTEND_PREFIXES):
            return PlainTextResponse("Not Found", status_code=404)
        return _serve_frontend_path(full_path)
