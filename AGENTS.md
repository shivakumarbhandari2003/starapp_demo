# STARAPP — AI CODING AGENT INSTRUCTIONS & ARCHITECTURE GUIDE

> **Critical Notice for AI Coding Agents:**  
> Read this file **first** before making any modifications to the StarApp repository.  
> Following this guide ensures fast, single-pass feature implementation without triggering regressions or scanning the entire codebase.

---

## 1. Project Architecture Overview

StarApp is structured as a **clean, modular Full-Stack Python application**:

```text
USER / BROWSER
      │
      ▼
EXISTING FRONTEND (HTML5 + Liquid Glass CSS + Vanilla JS)
      │
      │ HTTP REST / JSON (js/api.js)
      ▼
FASTAPI BACKEND (Python 3.12 / 3.13)
      ├── Core: Security, RBAC Permissions, Dependencies, Exceptions
      ├── Feature Modules: Auth, Users, Bands, Badges, Reviews, Allotments, Submissions, Evaluations, Audit
      ├── Repository Layer: Raw parameterized SQLite3 queries
      └── External Integrations: Google Gemini API proxy (server-side key)
      │
      ▼
PERSISTENT SQLITE3 DATABASE (data/starapp.db — WAL mode, PRAGMA foreign_keys = ON)
```

---

## 2. Directory & Responsibility Map

| Directory / File | Architectural Layer | Responsibility |
|:---|:---|:---|
| `backend/app/main.py` | FastAPI Application | Main entry point, router aggregation, CORS, static file mounting |
| `backend/app/core/` | Core Utilities | `config.py` (env), `security.py` (bcrypt), `permissions.py` (RBAC), `dependencies.py` |
| `backend/app/database/` | Database Layer | `connection.py` (connection pool & PRAGMAs), `migrations.py` (versioned DDL) |
| `backend/app/features/` | Feature Modules | Modular features: `auth`, `users`, `bands`, `badges`, `reviews`, `allotments`, `submissions`, `evaluations`, `audit` |
| `backend/app/integrations/` | External Services | `gemini/` (server-side Gemini API client & fallback generator) |
| `data/starapp.db` | Persistent Storage | Single authoritative SQLite database (33 tables + 1 view) |
| `js/api.js` | Frontend API Client | Reusable client exposing `window.StarAppAPI` |
| `js/bridge.js` | UI Bridge | Bridges UI DOM events to the API layer |
| `css/` | Presentation | Design tokens, liquid-glass frosted cards, responsive grid |
| `tests/` | QA & Verification | `run_tests.py` (89 tests including 79 baseline + 10 full-stack backend) |

---

## 3. Feature Ownership Matrix

When tasked with modifying a specific feature, **edit only the files in its row**:

| Feature | Frontend Trigger | Backend Router | Feature Service | Repository Layer | SQLite Tables | Test Suite |
|:---|:---|:---|:---|:---|:---|:---|
| **Authentication & Sessions** | `js/api.js` (`StarAppAPI.auth`) | `backend/app/features/auth/router.py` | `auth/service.py` | `auth/repository.py` | `users`, `user_sessions` | `tests/test_backend_fullstack.py` |
| **Employees & Hierarchy** | `js/api.js` (`StarAppAPI.users`) | `backend/app/features/users/router.py` | `users/service.py` | `users/repository.py` | `users`, `employees` | `tests/test_sqlite_persistence.py` |
| **Bands & Taxonomy** | `js/api.js` (`StarAppAPI.bands`) | `backend/app/features/bands/router.py` | `bands/service.py` | `bands/repository.py` | `bands`, `custom_capabilities`, `custom_skills` | `tests/test_badge_creation_and_approval.py` |
| **Badge Authoring** | `js/api.js` (`StarAppAPI.badges`) | `backend/app/features/badges/router.py` | `badges/service.py` | `badges/repository.py` | `badges`, `badge_powers`, `badge_capabilities` | `tests/test_badge_creation_and_approval.py` |
| **Badge Reviews & Approval** | `js/api.js` (`StarAppAPI.reviews`) | `backend/app/features/reviews/router.py` | `reviews/service.py` | `reviews/repository.py` | `badge_reviewer_assignments`, `badge_review_events` | `tests/test_badge_review_workflow.py` |
| **Allotments & Roadmap** | `js/api.js` (`StarAppAPI.allotments`) | `backend/app/features/allotments/router.py` | `allotments/service.py` | `allotments/repository.py` | `badge_timelines`, `deadline_extensions` | `tests/test_extension_flow.py` |
| **Project Submissions** | `js/api.js` (`StarAppAPI.submissions`) | `backend/app/features/submissions/router.py` | `submissions/service.py` | `submissions/repository.py` | `project_submissions` | `tests/test_scenarios_a_to_h.py` |
| **50-Mark Evaluations** | `js/api.js` (`StarAppAPI.evaluations`) | `backend/app/features/evaluations/router.py` | `evaluations/service.py` | `evaluations/repository.py` | `assessment_marksheets` | `tests/test_scenarios_a_to_h.py` |
| **Gemini AI Integration** | `js/api.js` (`StarAppAPI.gemini`) | `backend/app/integrations/gemini/router.py` | In router | N/A | None (uses server `.env`) | `tests/test_badge_creation_and_approval.py` |

---

## 4. Non-Negotiable Business Rules

1. **Reviewer Eligibility Rule:**
   $$\text{Reviewer\_Band} > \text{Badge\_Band}$$
   - Reviewer must strictly be in a higher band than the badge target band.
   - Enforced in `backend/app/core/permissions.py` and `backend/app/features/reviews/service.py`.
   - Never allow peer review in Band 1 or Band 6.

2. **50-Mark Rubric Structure:**
   - 5 Criteria: Business Understanding (10), Architecture/Report (10), Technical Knowledge (10), Presentation (10), Q&A (10).
   - Total Marks: 0 to 50.
   - Pass Threshold: $\ge 35/50$ (70%).
   - Enforced in `validate_50_mark_rubric()` in `backend/app/core/permissions.py`.

3. **Multi-Attempt History Retention:**
   - Submissions must never overwrite previous attempts.
   - Increment `attempt_number` and insert new row into `project_submissions`.

---

## 5. Development & Testing Commands

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the full test suite (89 tests)
python tests/run_tests.py

# 3. Run only full-stack backend tests (fast, ~1.8s)
python tests/test_backend_fullstack.py

# 4. Launch local production server
python serve.py
# Or directly with uvicorn:
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
