# TECHNICAL DEBT AUDIT & REMEDIATION PLAN

---

## 1. Major Technical Debt Categories

### TD-1: HTML in Python String Templates
- **Impact:** 7,744 lines of raw HTML strings inside Python files (`views_guardian.py`, `views_cosmonaut.py`, `views_common.py`).
- **Issues:**
  - Lack of syntax highlighting and IDE linting.
  - Mandatory escaping of `{` and `}` for CSS/JS interpolation.
  - Extreme error risk when editing styling or attributes.
- **Remediation:** Extract and modularize UI templates into clean static HTML/CSS/JS components or templates served by FastAPI.

### TD-2: The 3,476-Line God Controller (`app.py`)
- **Impact:** A single class `StarApp` handles 114 actions, mixing routing, business rules, DB transactions, and rendering.
- **Issues:**
  - High cognitive load for developers and AI agents.
  - Merge conflicts and coupling between unrelated features.
- **Remediation:** Decompose into modular feature routers, services, and repositories under `backend/app/features/`.

### TD-3: Pyodide WebAssembly VFS Dependency
- **Impact:** Requires bundling all Python files into `js/starapp_bundle.js` (1.17 MB) using `pack_py.py`.
- **Issues:**
  - Slow compilation step required after every Python change.
  - Heavy browser memory usage and 5–8 second initial load time.
- **Remediation:** Run Python natively on the local FastAPI server; deliver lightweight static frontend to the browser.

### TD-4: Tri-State Synchronization
- **Impact:** State simultaneously in Python dataclasses, in-VFS SQLite, and base64 localStorage snapshots.
- **Issues:**
  - Desynchronization risk.
  - Loss of changes on browser cache clear.
- **Remediation:** Eliminate dual stores; SQLite on disk is the authoritative state.
