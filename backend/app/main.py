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
from typing import Any, Optional, Dict, Union
import json
from starapp.app import StarAppController, controller
from starapp.storage import store


class ActionDispatchRequest(BaseModel):
    action: str
    payload: Optional[Any] = "{}"
    session_id: Optional[str] = None


# Tab-isolated session controller registry for concurrent multi-window testing
_session_controllers: Dict[str, StarAppController] = {"default": controller}


def get_session_controller(session_id: Optional[str] = None, role_hint: Optional[str] = None) -> StarAppController:
    """
    Returns an isolated StarAppController for each browser window/tab session,
    allowing concurrent multi-user testing (e.g. Guardian in Window 1, Cosmonaut in Window 2)
    while sharing the authoritative persistent SQLite3 database.
    """
    sid = session_id or "default"
    if sid not in _session_controllers:
        ctrl = StarAppController()
        ctrl.initialize()
        if role_hint == "cosmonaut" or "cosmo" in sid.lower():
            user = store.get_user_by_id("cosmo_1")
            if user:
                ctrl.current_user = user
                ctrl.current_view = "c_dashboard"
        elif role_hint == "guardian" or "guard" in sid.lower():
            user = store.get_user_by_id("admin") or store.get_user_by_id("guardian_1")
            if user:
                ctrl.current_user = user
                ctrl.current_view = "g_dashboard"
        _session_controllers[sid] = ctrl
    return _session_controllers[sid]


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
async def dispatch_action(req: ActionDispatchRequest, request: Request):
    """
    Full-stack action dispatcher: Executes UI actions server-side on the FastAPI backend,
    persists changes to authoritative SQLite3 (data/starapp.db), and returns incremental regions.
    Supports tab-isolated sessions via session_id or X-Session-Id header.
    """
    action = req.action
    payload_str = req.payload if isinstance(req.payload, str) else json.dumps(req.payload)
    sid = req.session_id or request.headers.get("X-Session-Id") or "default"

    role_hint = None
    if isinstance(req.payload, dict):
        role_hint = req.payload.get("role")
    elif isinstance(req.payload, str) and req.payload.startswith("{"):
        try:
            p = json.loads(req.payload)
            if isinstance(p, dict):
                role_hint = p.get("role")
        except Exception:
            pass

    ctrl = get_session_controller(sid, role_hint=role_hint)

    # Fast role initialization if requested via ?role= on boot
    if action == "boot" and role_hint:
        if role_hint == "cosmonaut" and (not ctrl.current_user or ctrl.current_user.id != "cosmo_1"):
            user = store.get_user_by_id("cosmo_1")
            if user:
                ctrl.current_user = user
                ctrl.current_view = "c_dashboard"
        elif role_hint == "guardian" and (not ctrl.current_user or ctrl.current_user.role != "guardian"):
            user = store.get_user_by_id("admin") or store.get_user_by_id("guardian_1")
            if user:
                ctrl.current_user = user
                ctrl.current_view = "g_dashboard"

    if action not in ("boot", "get_ui", "initial_render"):
        ctrl.handle_event(action, payload_str)

    full_html = ctrl.render()
    regions = getattr(ctrl, "last_rendered_regions", None)

    return {
        "success": True,
        "action": action,
        "full_html": full_html,
        "regions": regions,
        "session_id": sid,
        "current_view": getattr(ctrl, "current_view", "login"),
        "user": {
            "id": ctrl.current_user.id,
            "name": ctrl.current_user.name,
            "role": ctrl.current_user.role,
        } if ctrl.current_user else None,
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


@app.get("/sw.js")
async def service_worker():
    sw_file = BASE_DIR / "sw.js"
    if sw_file.exists():
        return FileResponse(str(sw_file), media_type="application/javascript")
    return JSONResponse(status_code=404, content={"message": "Service worker not found"})


@app.get("/favicon.ico")
async def favicon():
    fav_file = BASE_DIR / "favicon.ico"
    if fav_file.exists():
        return FileResponse(str(fav_file))
    return JSONResponse(status_code=204, content={})


@app.get("/")
async def root():
    index_file = BASE_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "StarApp Full-Stack Backend Active"}
