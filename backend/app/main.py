"""
Main FastAPI Application Entrypoint for StarApp.
"""
from contextlib import asynccontextmanager
from pathlib import Path
import importlib
import os
import re
import sys
import threading
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, Response, HTMLResponse

from backend.app.core.config import DEBUG, BASE_DIR, SECRET_KEY, SESSION_EXPIRE_HOURS, DEMO_MODE, MAX_SESSIONS, HOT_RELOAD
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
from backend.app.features.cycles.router import router as cycles_router
from backend.app.integrations.gemini.router import router as gemini_router
from pydantic import BaseModel
from typing import Any, Optional, Dict, Union
import json
import collections
import hashlib
import hmac
import time
from starapp.app import StarAppController, controller
from starapp.storage import store


class ActionDispatchRequest(BaseModel):
    action: str
    payload: Optional[Any] = "{}"
    session_id: Optional[str] = None


# Tab-isolated session controller registry. It is an LRU: at most MAX_SESSIONS controllers stay in
# memory; the least recently used one is evicted (its user is restored from the signed snapshot the
# browser sends on its next request), so memory stays bounded however many users visit.
_session_controllers: "collections.OrderedDict[str, StarAppController]" = collections.OrderedDict()
_session_controllers["default"] = controller
_reload_lock = threading.RLock()
# All StarApp actions share ONE in-memory store, so state-changing work is serialised with this lock.
# The lock is taken inside a worker thread (see dispatch_action) so the event loop never blocks.
_dispatch_lock = threading.RLock()
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{8,96}$")
_SIGNING_KEY = SECRET_KEY.encode("utf-8")
_SNAPSHOT_MAX_AGE_SECONDS = max(1, SESSION_EXPIRE_HOURS) * 3600


def _sign_session_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Adds an issued-at timestamp and an HMAC-SHA256 signature so the browser cannot forge who it is."""
    payload = {k: v for k, v in state.items() if k not in ("_sig", "_iat")}
    payload["_iat"] = int(time.time())
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    payload["_sig"] = hmac.new(_SIGNING_KEY, raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return payload


def _verify_session_state(state: Any) -> bool:
    """True only for a snapshot WE signed, that has not expired."""
    if not isinstance(state, dict):
        return False
    sig = state.get("_sig")
    iat = state.get("_iat")
    if not isinstance(sig, str) or not isinstance(iat, int):
        return False
    if time.time() - iat > _SNAPSHOT_MAX_AGE_SECONDS or iat > time.time() + 300:
        return False
    payload = {k: v for k, v in state.items() if k != "_sig"}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    expected = hmac.new(_SIGNING_KEY, raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)

_CORE_MODEL_FILES = ("models.py", "database.py", "sqlite_store.py", "storage.py", "seed_data.py", "previous_cycle_seed.py")
_UI_RELOAD_ORDER = (
    "starapp.validation",
    "starapp.assessment",
    "starapp.analytics",
    "starapp.badge_generator",
    "starapp.cycles",
    "starapp.roadmap",
    "starapp.mapping_data",
    "starapp.dashboard_demo",
    "starapp.views_common",
    "starapp.views_cosmonaut",
    "starapp.views_guardian",
    "starapp.app",
)
_CORE_RELOAD_ORDER = (
    "starapp.models",
    "starapp.database",
    "starapp.sqlite_store",
    "starapp.storage",
    "starapp.seed_data",
    "starapp.previous_cycle_seed",
)


def _compute_starapp_versions() -> tuple[int, int]:
    starapp_dir = BASE_DIR / "starapp"
    core_max = 0
    ui_max = 0
    if starapp_dir.exists():
        for pyf in starapp_dir.glob("*.py"):
            mtime = int(pyf.stat().st_mtime_ns)
            if pyf.name in _CORE_MODEL_FILES:
                core_max = max(core_max, mtime)
            else:
                ui_max = max(ui_max, mtime)
    return core_max, ui_max


def _compute_asset_version() -> str:
    latest = 0
    for folder, pattern in (("css", "*.css"), ("js", "*.js")):
        d = BASE_DIR / folder
        if d.exists():
            for f in d.glob(pattern):
                latest = max(latest, int(f.stat().st_mtime))
    idx = BASE_DIR / "index.html"
    if idx.exists():
        latest = max(latest, int(idx.stat().st_mtime))
    return str(latest or 14)


_LOADED_CORE_VER, _LOADED_UI_VER = _compute_starapp_versions()

_SESSION_ATTRS = (
    "current_view",
    "selected_cycle_id",
    "create_badge_band",
    "create_badge_power",
    "create_badge_capability",
    "create_badge_skill",
    "create_badge_reviewer_id",
    "create_badge_outcome_sentence",
    "create_badge_skill_search",
    "created_badge_data",
    "is_editing_badge",
    "badge_approval_filter",
    "badge_approval_search",
    "badge_approval_band_filter",
    "cycle_band_filter",
    "cycle_role_filter",
    "selected_guardian_cosmo_id",
    "guardian_review_filter",
    "assessment_power_filter",
    "assessment_capability_filter",
    "assessment_selected_badge_id",
    "assessment_selected_cosmonaut_id",
    "selected_review_sub_id",
    "selected_reviewer_sub_id",
    "reviewer_selected_submission_id",
    "selected_viewer_tab",
    "cosmo_selected_badge_id",
    "cosmo_requests_tab",
    "cosmo_requests_search",
    "reviewer_assessments_filter",
    "materials_badge_filter",
    "materials_type_filter",
    "mapping_selected_band",
    "mapping_selected_roles",
    "mapping_selected_badge",
    "mapping_selected_badge_id",
    "mapping_selected_cosmonauts",
    "mapping_selected_reviewer_bands",
    "mapping_selected_reviewer_band",
    "mapping_selected_reviewers",
    "mapping_review_anchor",
    "mapping_review_direction",
    "mapping_review_days_count",
    "mapping_review_mode",
    "mapping_range_start",
    "mapping_review_dates",
    "mapping_staged_previews",
    "mapping_expanded_badge_key",
    "mapping_detail_badge_key",
    "mapping_show_final_stage",
    "active_modal",
    "modal_payload",
    "view_history",
)


def _extract_controller_state(ctrl: StarAppController) -> Dict[str, Any]:
    u = getattr(ctrl, "current_user", None)
    state: Dict[str, Any] = {"user_id": u.id if u else None}
    for attr in _SESSION_ATTRS:
        if hasattr(ctrl, attr):
            val = getattr(ctrl, attr)
            try:
                json.dumps(val)
                state[attr] = val
            except Exception:
                pass
    return state


def _restore_controller_state(ctrl: StarAppController, state: Dict[str, Any], force_user: bool = True) -> None:
    if not isinstance(state, dict):
        return
    uid = state.get("user_id")
    if uid and (force_user or not getattr(ctrl, "current_user", None)):
        u = store.get_user_by_id(uid)
        if u:
            ctrl.current_user = u
    elif force_user and uid is None:
        ctrl.current_user = None
    for attr in _SESSION_ATTRS:
        if attr in state:
            setattr(ctrl, attr, state[attr])


def _reload_starapp_if_changed() -> None:
    """Hot-reload changed starapp modules in-process so a browser refresh reflects edits immediately."""
    global _LOADED_CORE_VER, _LOADED_UI_VER, StarAppController, controller, store
    if not HOT_RELOAD:
        return
    with _reload_lock:
        core_ver, ui_ver = _compute_starapp_versions()
        if core_ver <= _LOADED_CORE_VER and ui_ver <= _LOADED_UI_VER:
            return

        snapshots = {sid: _extract_controller_state(c) for sid, c in _session_controllers.items()}

        if core_ver > _LOADED_CORE_VER:
            for mod_name in _CORE_RELOAD_ORDER:
                mod = sys.modules.get(mod_name)
                if mod is not None:
                    importlib.reload(mod)
            cycles_router_mod = sys.modules.get("backend.app.features.cycles.router")
            if cycles_router_mod is not None:
                importlib.reload(cycles_router_mod)

        for mod_name in _UI_RELOAD_ORDER:
            mod = sys.modules.get(mod_name)
            if mod is not None:
                importlib.reload(mod)

        import starapp.storage as storage_mod
        import starapp.app as app_mod
        store = storage_mod.store
        StarAppController = app_mod.StarAppController
        controller = app_mod.controller

        rebuilt: Dict[str, StarAppController] = {}
        for sid, snap in snapshots.items():
            new_ctrl = controller if sid == "default" else StarAppController()
            if sid != "default":
                new_ctrl.initialize()
            _restore_controller_state(new_ctrl, snap, force_user=True)
            rebuilt[sid] = new_ctrl
        _session_controllers.clear()
        _session_controllers.update(rebuilt)
        if "default" not in _session_controllers:
            _session_controllers["default"] = controller

        _LOADED_CORE_VER = core_ver
        _LOADED_UI_VER = ui_ver


def get_session_controller(session_id: Optional[str] = None, role_hint: Optional[str] = None) -> StarAppController:
    """
    Returns an isolated StarAppController for each browser window/tab session,
    allowing concurrent multi-user use (e.g. Guardian in Window 1, Cosmonaut in Window 2)
    while sharing the authoritative persistent SQLite3 database.

    SECURITY: a session starts logged OUT. The previous behaviour auto-logged-in as the admin or a
    cosmonaut whenever the (client chosen) session id merely CONTAINED "guard" / "cosmo". Passwordless
    role shortcuts now exist only when STARAPP_DEMO_MODE is on AND the caller asks for them explicitly.
    """
    sid = session_id or "default"
    if sid in _session_controllers:
        _session_controllers.move_to_end(sid)
        return _session_controllers[sid]

    ctrl = StarAppController()
    ctrl.initialize()
    if DEMO_MODE and role_hint == "cosmonaut":
        user = store.get_user_by_id("cosmo_1")
        if user:
            ctrl.current_user = user
            ctrl.current_view = "c_dashboard"
    elif DEMO_MODE and role_hint == "guardian":
        user = store.get_user_by_id("admin") or store.get_user_by_id("guardian_1")
        if user:
            ctrl.current_user = user
            ctrl.current_view = "g_dashboard"
    _session_controllers[sid] = ctrl
    _evict_idle_sessions()
    return ctrl


def _evict_idle_sessions() -> None:
    """Drops least-recently-used controllers beyond MAX_SESSIONS (never the shared default one)."""
    while len(_session_controllers) > max(2, MAX_SESSIONS):
        for victim in _session_controllers:
            if victim != "default":
                _session_controllers.pop(victim, None)
                break
        else:
            break


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

# Compress HTML / JSON / JS / CSS responses (dispatch payloads are mostly repetitive markup).
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)

# CORS: wildcard origin + credentials is both invalid per the CORS spec and unsafe. Local development
# origins are allowed by default; set STARAPP_CORS_ORIGINS="https://a.example,https://b.example" in prod.
_cors_origins = [o.strip() for o in os.getenv("STARAPP_CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def disable_stale_browser_cache(request: Request, call_next):
    """Cache versioned static CSS/JS assets across tabs while keeping HTML & API responses fresh."""
    response = await call_next(request)
    if request.url.path.startswith(("/css/", "/js/")) and "v" in request.query_params:
        response.headers["Cache-Control"] = "public, max-age=86400"
    else:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


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
app.include_router(cycles_router, prefix=api_v1_prefix)
app.include_router(gemini_router, prefix=api_v1_prefix)


def _run_dispatch(req: "ActionDispatchRequest", header_sid: Optional[str]) -> Dict[str, Any]:
    """Synchronous body of the dispatcher; executed in a worker thread under `_dispatch_lock`."""
    _reload_starapp_if_changed()

    action = req.action
    payload_str = req.payload if isinstance(req.payload, str) else json.dumps(req.payload)
    sid = req.session_id or header_sid or ""

    role_hint = None
    restore_session = None
    if isinstance(req.payload, dict):
        role_hint = req.payload.get("role")
        restore_session = req.payload.get("restore_session")
    elif isinstance(req.payload, str) and req.payload.startswith("{"):
        try:
            p = json.loads(req.payload)
            if isinstance(p, dict):
                role_hint = p.get("role")
                restore_session = p.get("restore_session")
        except Exception:
            pass

    had_existing_session = sid in _session_controllers
    ctrl = get_session_controller(sid, role_hint=role_hint)

    if action == "boot":
        # Recover exact page & role across server restarts / LRU eviction -- ONLY from a snapshot this
        # server signed (the browser can no longer claim to be an arbitrary user_id).
        if (not had_existing_session or not getattr(ctrl, "current_user", None)) and _verify_session_state(restore_session):
            _restore_controller_state(ctrl, restore_session, force_user=True)
        elif DEMO_MODE and role_hint:
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

    # handle_event() already renders at the end of every action; render again only when it did not
    # (boot / get_ui / actions that return early). This removes the duplicate render per click.
    gen_before = getattr(ctrl, "render_generation", 0)
    if action not in ("boot", "get_ui", "initial_render"):
        ctrl.handle_event(action, payload_str)
    if action in ("boot", "get_ui", "initial_render") or getattr(ctrl, "render_generation", 0) == gen_before \
            or getattr(ctrl, "last_rendered_html", None) is None:
        full_html = ctrl.render()
    else:
        full_html = ctrl.last_rendered_html
    regions = getattr(ctrl, "last_rendered_regions", None)

    state = _extract_controller_state(ctrl)
    return {
        "success": True,
        "action": action,
        # `regions` carries every HTML fragment already; shipping the full page twice doubled the payload.
        "full_html": None if regions else full_html,
        "regions": regions,
        "session_id": sid,
        "current_view": getattr(ctrl, "current_view", "login"),
        "session_state": _sign_session_state(state) if state.get("user_id") else state,
        "user": {
            "id": ctrl.current_user.id,
            "name": ctrl.current_user.name,
            "role": ctrl.current_user.role,
        } if ctrl.current_user else None,
    }


@app.post("/api/v1/dispatch")
async def dispatch_action(req: ActionDispatchRequest, request: Request):
    """
    Full-stack action dispatcher: Executes UI actions server-side on the FastAPI backend,
    persists changes to authoritative SQLite3 (data/starapp.db), and returns incremental regions.
    Supports tab-isolated sessions via session_id or X-Session-Id header, plus live module reload.

    The (CPU heavy) work runs in a worker thread so the event loop keeps serving static files, health
    checks and REST calls; actions themselves are serialised because they share one in-memory store.
    """
    header_sid = request.headers.get("X-Session-Id")
    sid = req.session_id or header_sid or ""
    if sid != "default" and not _SESSION_ID_RE.match(sid):
        return JSONResponse(status_code=400, content={"success": False, "error": {"code": "BAD_SESSION", "message": "A valid X-Session-Id is required."}})

    def _locked() -> Dict[str, Any]:
        with _dispatch_lock:
            return _run_dispatch(req, header_sid)

    return await run_in_threadpool(_locked)


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


@app.get("/js/starapp_bundle.js")
async def offline_runtime_bundle():
    """
    The offline (Pyodide) bundle embeds a BASE64 COPY OF THE WHOLE DATABASE, passwords included. It is a
    demo-only convenience: with STARAPP_DEMO_MODE=false it is never served. (Registered before the /js
    static mount so it takes precedence.)
    """
    bundle = js_dir / "starapp_bundle.js"
    if not DEMO_MODE or not bundle.exists():
        return JSONResponse(status_code=404, content={"message": "Not found"})
    return FileResponse(str(bundle), media_type="application/javascript")


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
    return Response(status_code=204)


def _build_index_response() -> Any:
    index_file = BASE_DIR / "index.html"
    if index_file.exists():
        _reload_starapp_if_changed()
        html = index_file.read_text(encoding="utf-8")
        asset_ver = _compute_asset_version()
        html = re.sub(r'(\.(?:css|js)\?v=)\d+', rf'\g<1>{asset_ver}', html)
        ssr_ctrl = StarAppController()
        login_html = ssr_ctrl.render_login_view()
        html = html.replace(
            "/* STARAPP_SERVER_FLAGS */",
            "window.__STARAPP_CONFIG__.FASTAPI_ACTIVE = true;\n"
            "    window.__STARAPP_CONFIG__.SSR_LOGIN = true;",
        )
        html = re.sub(
            r"<!-- STARAPP_INITIAL_ROOT_START -->.*?<!-- STARAPP_INITIAL_ROOT_END -->",
            lambda _m: login_html,
            html,
            flags=re.DOTALL,
        )
        return HTMLResponse(
            content=html,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return {"message": "StarApp Full-Stack Backend Active"}


@app.get("/")
@app.get("/index.html")
async def root():
    return _build_index_response()
