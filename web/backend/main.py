"""HexaVeil CMS Backend — FastAPI Application.

Pattern: remnawave's main.py (simplified for CMS).
CORS, middleware, health endpoint, router registration.
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from web.backend.core.auto_sync import auto_sync_loop
from web.backend.core.config import get_cms_settings
from web.backend.core.database import check_connection, close_engine
from web.backend.core.errors import E
from web.backend.core.logging_config import setup_logging
from web.backend.schemas.common import HealthResponse

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — on startup check DB, on shutdown cleanup."""
    settings = get_cms_settings()
    logger.info("🚀 CMS API starting on %s:%s", settings.host, settings.port)

    # Check DB connection
    db_ok = await check_connection()
    if db_ok:
        logger.info("Database connected: %s@%s:%s/%s",
                     settings.db_user, settings.db_host, settings.db_port, settings.db_name)
    else:
        logger.warning("Database connection failed — API will run with limited functionality")

    # Start the in-app auto-sync loop (acts only when a provider has
    # `*_auto_sync` enabled in fin_settings).
    auto_sync_task = asyncio.create_task(auto_sync_loop())

    yield

    # Shutdown
    auto_sync_task.cancel()
    try:
        await auto_sync_task
    except asyncio.CancelledError:
        pass
    await close_engine()
    logger.info("👋 CMS API stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_cms_settings()

    app = FastAPI(
        title="HexaVeil CMS API",
        description="REST API for HexaVeil CMS — migrating from PHP to FastAPI",
        version="0.1.0",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        openapi_url="/api/openapi.json" if settings.debug else None,
        lifespan=lifespan,
        redirect_slashes=False,
    )

    # ── Exception handlers ──────────────────────────────────────
    from fastapi import HTTPException
    from fastapi.exception_handlers import http_exception_handler
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(HTTPException)
    async def cms_http_exception_handler(request: Request, exc: HTTPException):
        """Unwrap dict details into top-level PHP-compatible error body.

        Dependencies raise HTTPException(detail={"success": False, "error": ..., "code": ...}).
        FastAPI would nest that under "detail"; we return it flat instead.
        """
        if isinstance(exc.detail, dict):
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,
                headers=getattr(exc, "headers", None),
            )
        return await http_exception_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        fields = []
        for err in errors:
            loc = " → ".join(str(x) for x in err.get("loc", []) if x != "body")
            fields.append(f"{loc}: {err.get('msg', 'invalid')}")
        detail = "; ".join(fields) if fields else "Validation error"
        return JSONResponse(
            status_code=422,
            content={"success": False, "error": detail, "code": E.VALIDATION_ERROR.value},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Internal server error", "code": E.INTERNAL_ERROR.value},
        )

    # ── CORS ────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # ── Request body size limit ─────────────────────────────────
    @app.middleware("http")
    async def limit_request_body(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_upload_size:
            return JSONResponse(
                {"success": False, "error": "Request body too large", "code": E.FILE_TOO_LARGE.value},
                status_code=413,
            )
        return await call_next(request)

    # ── Security headers ────────────────────────────────────────
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    # ── Request logging (mirrors Remnawave's api_call log line) ──
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        import time
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "api_call %s %s -> %s (%sms)",
            request.method, request.url.path, response.status_code, duration_ms,
        )
        return response

    # ── Include routers ─────────────────────────────────────────
    from web.backend.api.v1 import auth as auth_api
    from web.backend.api.v1 import dashboard as dashboard_api
    from web.backend.api.v1 import posts as posts_api
    from web.backend.api.v1 import categories as categories_api
    from web.backend.api.v1 import pages as pages_api
    from web.backend.api.v1 import users as users_api
    from web.backend.api.v1 import logs as logs_api
    from web.backend.api.v1 import widgets as widgets_api
    from web.backend.api.v1 import menus as menus_api
    from web.backend.api.v1 import themes as themes_api
    from web.backend.api.v1 import settings as settings_api
    from web.backend.api.v1 import notifications as notifications_api
    from web.backend.api.v1 import media as media_api
    from web.backend.api.v1 import public as public_api
    from web.backend.api.v1 import preferences as preferences_api
    from web.backend.api.v1 import diagnostics as diagnostics_api
    from web.backend.api.v1 import finance as finance_api
    from web.backend.api.v1 import finance_payments as finance_payments_api
    from web.backend.api.v1.bedolaga import router as bedolaga_router

    app.include_router(auth_api.router, prefix="/api", tags=["auth"])
    app.include_router(dashboard_api.router, prefix="/api", tags=["dashboard"])
    app.include_router(posts_api.router, prefix="/api", tags=["posts"])
    app.include_router(categories_api.router, prefix="/api", tags=["categories"])
    app.include_router(pages_api.router, prefix="/api", tags=["pages"])
    app.include_router(users_api.router, prefix="/api", tags=["users"])
    app.include_router(logs_api.router, prefix="/api", tags=["logs"])
    app.include_router(widgets_api.router, prefix="/api", tags=["widgets"])
    app.include_router(menus_api.router, prefix="/api", tags=["menus"])
    app.include_router(themes_api.router, prefix="/api", tags=["themes"])
    app.include_router(settings_api.router, prefix="/api", tags=["settings"])
    app.include_router(notifications_api.router, prefix="/api", tags=["notifications"])
    app.include_router(media_api.router, prefix="/api", tags=["media"])

    # Unauthenticated branding (login page + admin shell)
    app.include_router(public_api.router, prefix="/api", tags=["public"])

    # Migrated PHP-bridge endpoints (React keeps calling the same /admin/* paths)
    app.include_router(preferences_api.router, prefix="/admin/settings", tags=["preferences"])
    app.include_router(diagnostics_api.router, prefix="/admin/diagnostics/api", tags=["diagnostics"])
    app.include_router(finance_api.router, prefix="/admin/finance/api", tags=["finance"])
    app.include_router(finance_payments_api.router, prefix="/admin/finance/api", tags=["finance-payments"])

    # Bedolaga Bot API proxy
    app.include_router(bedolaga_router, prefix="/api/bedolaga", tags=["bedolaga"])

    # ── Health check ────────────────────────────────────────────
    @app.get("/api/health", tags=["health"])
    async def health_check():
        """Health check endpoint — used by nginx and monitoring."""
        db_ok = await check_connection()
        return HealthResponse(
            status="ok",
            database="connected" if db_ok else "disconnected",
        )

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "hexaveil-cms-api",
            "version": "0.1.0",
            "docs": "/api/docs" if settings.debug else None,
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_cms_settings()
    uvicorn.run(
        "web.backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )