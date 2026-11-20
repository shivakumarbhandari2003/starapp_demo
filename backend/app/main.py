"""
Main FastAPI Application Entrypoint for StarApp.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse

from backend.app.core.config import DEBUG, BASE_DIR
from backend.app.core.exceptions import StarAppException, starapp_exception_handler
from backend.app.database.migrations import apply_migrations
from backend.app.database.connection import check_database_integrity

# Import feature routers
from backend.app.features.auth.router import router as auth_router
from backend.app.features.users.router import router as users_router
from backend.app.features.bands.router import router as bands_router
from backend.app.features.badges.router import router as badges_router
from backend.app.features.reviews.router import router as reviews_router
from backend.app.features.allotments.router import router as allotments_router
from backend.app.features.submissions.router import router as submissions_router
from backend.app.features.evaluations.router import router as evaluations_router
from backend.app.features.audit.router import router as audit_router
from backend.app.integrations.gemini.router import router as gemini_router
from pydantic import BaseModel
from typing import Any, Optional
import json
from starapp.app import controller


class ActionDispatchRequest(BaseModel):
    action: str
    payload: Optional[Any] = "{}"
    session_id: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Apply database migrations and verify integrity
    apply_migrations()
    integrity = check_database_integrity()
    print(f"[StarApp Backend] Initialized. Database Status: {integrity}")
    yield
    print("[StarApp Backend] Shutting down.")


app = FastAPI(
    title="StarApp Full-Stack Architecture",
    description="Full-stack FastAPI backend for StarApp with persistent SQLite3 storage and RBAC.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register custom exception handlers
app.add_exception_handler(StarAppException, starapp_exception_handler)

# Register API v1 Routers
api_v1_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(users_router, prefix=api_v1_prefix)
app.include_router(bands_router, prefix=api_v1_prefix)
app.include_router(badges_router, prefix=api_v1_prefix)
app.include_router(reviews_router, prefix=api_v1_prefix)
app.include_router(allotments_router, prefix=api_v1_prefix)
app.include_router(submissions_router, prefix=api_v1_prefix)
app.include_router(evaluations_router, prefix=api_v1_prefix)
app.include_router(audit_router, prefix=api_v1_prefix)
app.include_router(gemini_router, prefix=api_v1_prefix)


@app.post("/api/v1/dispatch")
async def dispatch_action(req: ActionDispatchRequest):
    """
    Full-stack action dispatcher: Executes UI actions server-side on the FastAPI backend,
    persists changes to authoritative SQLite3 (data/starapp.db), and returns incremental regions.
    """
    action = req.action
    payload_str = req.payload if isinstance(req.payload, str) else json.dumps(req.payload)

    if action not in ("boot", "get_ui", "initial_render"):
        controller.handle_event(action, payload_str)

    full_html = controller.render()
    regions = getattr(controller, "last_rendered_regions", None)

    return {
        "success": True,
        "action": action,
        "full_html": full_html,
        "regions": regions,
        "current_view": getattr(controller, "current_view", "login"),
        "user": {
            "id": controller.current_user.id,
            "name": controller.current_user.name,
            "role": controller.current_user.role,
        } if controller.current_user else None,
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    integrity = check_database_integrity()
    return {
        "status": "healthy" if integrity["status"] == "healthy" else "degraded",
        "database": integrity,
        "version": "2.0.0",
    }


# Static files and root route serving existing frontend
css_dir = BASE_DIR / "css"
js_dir = BASE_DIR / "js"
if css_dir.exists():
    app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
if js_dir.exists():
    app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")


@app.get("/")
async def root():
    index_file = BASE_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "StarApp Full-Stack Backend Active"}
