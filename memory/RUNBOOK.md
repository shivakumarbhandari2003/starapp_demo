# Runbook — set up, run, test, troubleshoot (new machine)

## 1. Prerequisites

* Python **3.12 or 3.13**, `pip`, Git. (Windows, macOS, Linux all fine.)
* Optional: Google Chrome + `playwright` for UI audits (**not** part of `requirements.txt`; install only if you need screenshots).
* Optional: a Gemini API key for AI-assisted badge drafting (`GEMINI_API_KEY`); the app works without it (fallback generator).

## 2. First-time setup

```bash
git clone <repo-url> starapp_demo && cd starapp_demo
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env   (then edit; .env is gitignored)
python tests/run_tests.py       # expect: Ran 239 tests ... OK   (~18 s)
python serve.py                 # http://127.0.0.1:8000   (docs: /docs, health: /api/health)
```

`requirements.txt`: fastapi, uvicorn[standard], pydantic, python-multipart, bcrypt, python-dotenv, httpx.

Alternative launch: `uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload`.

## 3. Sign in (demo)

Open `http://127.0.0.1:8000`. With `STARAPP_DEMO_MODE=true` (default) the login page offers quick-login pills. Otherwise sign in with email + password `123456789`:

| Who | Email | Notes |
|:---|:---|:---|
| Guardian | `arjun.mehta@starapp.io` (`guardian_1`) / `admin@starapp.io` (`admin`) | full Guardian portal |
| Cadet B1 | `aarav.sharma@starapp.io` (`m_b1_1`) | Cosmonaut portal |
| Reviewer (B2) | `rohan.deshmukh@starapp.io` (`m_b2_1`) | reviewer pages + cadet pages (dual role) |
| B6 | `devika.narayanan@starapp.io` (`m_b6_1`) | top band (cannot have peer reviewers) |

## 4. Environment variables (`.env`)

| Variable | Default | Meaning |
|:---|:---|:---|
| `HOST`, `PORT` | `127.0.0.1`, `8000` | bind address |
| `DEBUG` | `True` | dev mode; also default for `STARAPP_HOT_RELOAD` |
| `SECRET_KEY` | dev key | **change for real use**; signs session snapshots |
| `SESSION_EXPIRE_HOURS` | `24` | REST session lifetime |
| `DATABASE_URL` | `data/starapp.db` | path relative to the repo root (tests set an absolute temp path) |
| `GEMINI_API_KEY` | – | server-side only; never commit |
| `STARAPP_DEMO_MODE` | `true` | demo shortcuts. **false for real users** |
| `STARAPP_MAX_SESSIONS` | `1500` | LRU cap for in-memory UI sessions |
| `STARAPP_HOT_RELOAD` | = `DEBUG` | reload python modules per request (dev only) |
| `STARAPP_CORS_ORIGINS` | localhost | comma-separated origins |
| `STARAPP_COOKIE_SECURE` | `false` | set `true` behind HTTPS |
| `STARAPP_DB_PATH` | derived | set automatically from `DATABASE_URL` (tests override) |
| `STARAPP_TEST_USE_REAL_DB` | unset | **dangerous**: lets the test runner use the real DB |

## 5. Testing

```bash
python tests/run_tests.py                      # full suite (239 tests, isolated DB copy)  ← the only supported entry point
python tests/test_backend_fullstack.py         # fast backend smoke (only on a throw-away DB copy!)
```

* Single module on an isolated DB: copy `data/starapp.db` to a temp dir, set `STARAPP_DB_PATH` and `DATABASE_URL` to it, then run that module.
* Regression home for Stage 1/2: `tests/test_scale_and_security_regressions.py` (41 tests: cascade safety, indexes/memo, lazy payloads, pagination, dispatch security, REST RBAC, workflow rules, UI polish).
* After the run: `git status data/` must be empty (`pack_py.py` and the runner can dirty it: restore with `git checkout data/starapp.db`).
* The two `scripts/e2e_guardian_*.py` scripts copy the DB to a temp folder themselves; the browser one starts uvicorn on port 8133 and Chrome on 9371.

## 6. After changing code

1. `python tests/run_tests.py`
2. `python scripts/pack_py.py` (if you touched `starapp/`) → regenerates `js/starapp_bundle.js`
3. If you touched `css/` or `js/`: bump `?v=N` in `index.html` + `sw.js` (+ asserts in `tests/test_backend_fullstack.py`, `tests/test_ui_remediation.py`, `Report.md`) — otherwise browsers keep the old files for up to 24 h
4. UI / workflow change: `python scripts/e2e_guardian_logic.py` and `python scripts/e2e_guardian_browser.py` (Chrome needed; `CHROME_PATH` if not in the default location) → expect `0 failed`
5. Update `memory/` docs + change log (README §3)
6. `git status` — make sure `data/starapp.db` is not modified unintentionally (`git checkout data/starapp.db` after tests/pack runs)

## 7. Useful scripts (`scripts/`)

| Script | Use |
|:---|:---|
| `pack_py.py` | rebuild the offline Pyodide bundle |
| `seed_previous_cycle.py` | (re)seed the closed previous cycle |
| `clear_badges.py`, `clear_data.py` | destructive cleanup helpers — **never on the shared DB** |
| `verify_e2e_workflow.py` | end-to-end lifecycle check |

## 8. Troubleshooting

| Symptom | Cause / fix |
|:---|:---|
| `database is locked` | two writers on the same DB (another server/test/DB browser). Stop them; WAL + `busy_timeout=5000` handle brief contention. |
| Test run changed `data/starapp.db` | you ran tests without the runner. `git checkout data/starapp.db` (only if you have no intentional DB changes). |
| UI shows old behaviour | browser cached JS/bundle; hard refresh; rebuild bundle (`pack_py.py`). |
| Windows console `UnicodeEncodeError` (cp1252) | set `PYTHONUTF8=1`. |
| Login says role not permitted | the selected role isn't in `user_role_assignments` for that user. |
| `DENIED guardian-only action` in the log | a non-guardian called a Guardian action — expected; check the action list in `_GUARDIAN_ONLY_ACTIONS`. |
| Health shows different `table_count` | internal `sqlite_%` tables are excluded; real count is 38. |
| Session lost after server restart | by design: sessions restore from the browser's signed snapshot; if `SECRET_KEY` changed, snapshots are rejected → log in again. |
| Port in use | change `PORT` or stop the other process. |

## 9. Security checklist before exposing the app to real users

`STARAPP_DEMO_MODE=false` · unique `SECRET_KEY` · `DEBUG=False` · HTTPS + `STARAPP_COOKIE_SECURE=true` · tight `STARAPP_CORS_ORIGINS` · replace seeded plaintext passwords · back up `data/starapp.db` (WAL: copy the db *and* `-wal`/`-shm`, or use `sqlite3 .backup`).
