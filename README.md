# StarApp — Autonomous Training & Gamified Badge Management Platform

StarApp is a functional, locally persistent training and badge management application featuring two interconnected, role-based portals:
1. **Guardian Portal** — for mentors/trainers who manage Cosmonauts, allot and publish badges, schedule milestone timelines, conduct project reviews using the standard 50-mark rubric, publish learning materials, manage deadline extensions, and broadcast announcements.
2. **Cosmonaut Portal** — for learners who progress through a Candy Crush-inspired gamified learning roadmap, study embedded documentation and videos, submit project deliverables (PDF, GitHub, or Code), review comprehensive rubric marksheets across multiple attempts, manage profile skills and certifications, and track real-time batch leaderboard rankings.

The entire application runs **without a conventional backend or database service** (no Flask, Django, FastAPI, Node.js, Firebase, or Supabase). The application logic is written in modular Python and executes client-side in the browser via Pyodide WebAssembly, storing all persistent data in browser-local storage (IndexedDB and localStorage).

---

## 1. Project Directory & File Structure

```
starapp_demo/
├── index.html                  # HTML entry point, SVG displacement filter definitions, Pyodide bootstrapper
├── serve.py                    # Static launcher using Python's built-in http.server (no backend framework)
├── push_to_github.py           # Zero-dependency GitHub REST API synchronizer
├── code.txt                    # Original reference component (React/JSX liquid glass and metal buttons)
├── css/
│   ├── design_tokens.css       # Strict 5-colour palette, typography scale, radii, and transitions
│   ├── liquid_glass.css        # Pure HTML/CSS conversion of code.txt (SVG filter, container, liquid & metal buttons)
│   ├── layout.css              # Sidebars, top navigation bar, modals, and main workspace layout
│   ├── components.css          # KPI cards, data tables, 50-mark rubric grid, Candy Crush roadmap, timelines
│   └── responsive.css          # Responsive breakpoints (Desktop, Laptop, Tablet, Mobile)
├── js/
│   ├── bridge.js               # Minimal JS bridge (<90 lines) for IndexedDB promises and FileReader
│   └── starapp_bundle.js       # Bundled starapp Python modules for instant virtual FS mounting
├── starapp/                    # Core Modular Python Application Logic (runs in Pyodide & Python CLI)
│   ├── __init__.py
│   ├── models.py               # Shared data models: User, CosmonautProfile, Badge, Timeline, Submission, etc.
│   ├── storage.py              # Centralized data-access layer with IndexedDB & localStorage synchronization
│   ├── seed_data.py            # Initial synthetic dataset (Dr. Elena Vance + Astraea Nova + 5 Badges)
│   ├── assessment.py           # Standard 50-mark rubric engine, calculations, leaderboard ranking, analytics
│   ├── roadmap.py              # Gamified roadmap graph engine, prerequisite validation, milestone states
│   ├── validation.py           # Form and domain validation rules
│   ├── views_common.py         # Shared UI templates (modals, marksheets, timelines, topbar)
│   ├── views_guardian.py       # Guardian views (aggregate dashboard, review queue, allotment, materials, etc.)
│   ├── views_cosmonaut.py      # Cosmonaut views (personal dashboard, profile, roadmap, submit, materials, etc.)
│   └── app.py                  # Main application controller, routing, event dispatch, and UI rendering
├── tests/                      # Automated Python unit & workflow test suite
│   ├── test_all.py             # Unit tests for models, validation, rubric scoring, and prerequisites
│   ├── test_scenarios_a_to_h.py# Verification of all 8 mandatory end-to-end workflows
│   └── run_tests.py            # Central test discovery and execution script
└── scripts/
    └── pack_py.py              # Helper utility to pack starapp/*.py into js/starapp_bundle.js
```

---

## 2. Reusable Liquid-Glass Container Implementation

StarApp directly converts the React/JSX liquid-glass container from `code.txt` into standard, reusable HTML and CSS classes without external framework dependencies:

### SVG Displacement Filter
Defined globally in `index.html`:
```html
<svg class="glass-svg-defs" aria-hidden="true">
  <defs>
    <filter id="container-glass" x="0%" y="0%" width="100%" height="100%" color-interpolation-filters="sRGB">
      <feTurbulence type="fractalNoise" baseFrequency="0.05 0.05" numOctaves="1" seed="1" result="turbulence" />
      <feGaussianBlur in="turbulence" stdDeviation="2" result="blurredNoise" />
      <feDisplacementMap in="SourceGraphic" in2="blurredNoise" scale="70" xChannelSelector="R" yChannelSelector="B" result="displaced" />
      <feGaussianBlur in="displaced" stdDeviation="4" result="finalBlur" />
      <feComposite in="finalBlur" in2="finalBlur" operator="over" />
    </filter>
  </defs>
</svg>
```

### CSS Styling & Multi-Layer Specular Highlights (`css/liquid_glass.css`)
```css
.liquid-glass-card,
.liquid-glass-panel,
.liquid-glass-modal {
  position: relative;
  border-radius: var(--radius-lg);
  isolation: isolate;
  overflow: hidden;
  border: 1px solid var(--icy-steel-50);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.72) 0%, rgba(234, 244, 255, 0.45) 100%);
  -webkit-backdrop-filter: blur(18px) saturate(180%);
  backdrop-filter: url("#container-glass") blur(18px) saturate(180%);
  box-shadow:
    0 4px 24px -2px rgba(7, 22, 41, 0.08),
    0 1px 4px rgba(7, 22, 41, 0.04),
    inset 3px 3px 0.5px -3.5px rgba(255, 255, 255, 0.8),
    inset -3px -3px 0.5px -3.5px rgba(157, 183, 213, 0.35),
    inset 1px 1px 1px -0.5px rgba(255, 255, 255, 0.9),
    inset -1px -1px 1px -0.5px rgba(157, 183, 213, 0.5),
    inset 0 0 6px 6px rgba(234, 244, 255, 0.25),
    inset 0 0 2px 2px rgba(255, 255, 255, 0.4);
}
```

### Button Variants from `code.txt`
- `.btn-liquid`: Floating specular pill button with dynamic scaling and liquid highlight.
- `.btn-metal`: 3D tactile button with bevel rim layering, gradient illumination, and active press depress states.

---

## 3. Strict 5-Colour Design Palette

All interface elements, backgrounds, typography, charts, and status indicators strictly adhere to the five approved colours and their alpha/gradient tints:

| Colour Name | Hex Code | Purpose in StarApp |
|---|---|---|
| **Frost Navy** | `#071629` | Main dark background, sidebar background, high-contrast headings |
| **Deep Frozen Midnight** | `#17345C` | Primary buttons, active navigation, marksheet headers, dark glass panels |
| **Icy Steel** | `#9DB7D5` | Secondary accents, borders, dividers, subtle highlights, locked milestones |
| **Frost Mist** | `#EAF4FF` | Main application content background, soft surfaces, badge fills |
| **Snow White** | `#FFFFFF` | Cards, modal content surfaces, light text on dark backgrounds |

---

## 4. Shared Data Model & Local Persistence Architecture

Both Guardian and Cosmonaut portals interact with a single, centralized data store (`starapp/storage.py`) containing the normalized models:
- **Users**: Guardian and 6 Cosmonauts.
- **Cosmonaut Profiles**: Cohort information, mentor credentials, dynamically updated skills and certifications.
- **Badges**: 10 enterprise badges with descriptions, learning outcomes, covered topics, project requirements, prerequisites, and publication status.
- **Timelines**: 9-point milestone lifecycle (Assignment, Publication, Learning Start/End, Project Start/End, Submission Deadline, Review Date, Award Date).
- **Project Submissions**: Deliverables (PDF base64, GitHub repo URL, or Code file) tracked across sequential attempt numbers.
- **Assessment Marksheets**: The universal 50-mark rubric evaluated by Guardian (5 criteria x 10 marks max) with qualitative strengths, improvement areas, overall feedback, and decision (`approve`, `reject`, `resubmission_requested`).
- **Learning Materials**: Course handbooks (PDF) and embedded YouTube lectures with fallback handling.
- **Deadline Extensions**: Request records with current vs proposed deadline, reason, and Guardian decision/notes.
- **Announcements**: Broadcast notices targeted to all or specific Cosmonauts with read receipts.
- **Activity Feed**: Batch-wide and personal chronological audit trails.
- **Notifications**: Cross-portal event alerts.

### Storage Synchronization
- **IndexedDB**: Structured snapshot of all objects and file attachments.
- **localStorage**: Session preferences and active user identity.
- **Demo Reset**: A single click on "Demo Reset" in the top bar instantly restores the clean initial seed data without data corruption.

---

## 5. Demo Login Credentials

The application provides a one-click demo login selector on the sign-in screen, or you can log in using these credentials:

| Role | Name | Username / Email | Password | Key Context |
|---|---|---|---|---|
| **Guardian** | Dr. Elena Vance | `guardian` / `guardian@starapp.dev` | `guardian123` | Training Mentor & Lead Evaluator |
| **Cosmonaut** | Astraea Nova | `astraea` / `astraea@starapp.dev` | `cosmo123` | Rank #1 (GOV-101: 48/50, CUR-102: 47/50) |
| **Cosmonaut** | Orion Drake | `orion` / `orion@starapp.dev` | `cosmo123` | GOV-101 completed; CUR-102 pending review |
| **Cosmonaut** | Lyra Solaris | `lyra` / `lyra@starapp.dev` | `cosmo123` | ING-104 Attempt 2 resubmitted after feedback |
| **Cosmonaut** | Cassian Ray | `cassian` / `cassian@starapp.dev` | `cosmo123` | Cloud Foundations extension request pending |
| **Cosmonaut** | Kaelen Vesper | `kaelen` / `kaelen@starapp.dev` | `cosmo123` | Software Foundations completed (44/50) |
| **Cosmonaut** | Seraphina Moon | `seraphina` / `seraphina@starapp.dev` | `cosmo123` | Early stage cadet working on GOV-101 |

---

## 6. How to Launch & Run StarApp

### Method 1: Using the Static Python Launcher (Recommended)
Open a terminal in the project directory and run:
```powershell
python serve.py
```
This starts Python's built-in static HTTP server on port 8000 and automatically opens `http://localhost:8000/index.html` in your default browser.

### Method 2: Direct Browser Launch
You can also open `index.html` directly in any modern browser (Chrome, Edge, Firefox). The bundled script `js/starapp_bundle.js` mounts the Python modules into Pyodide's virtual filesystem with zero CORS issues.

### Running Automated Tests
Run the complete test suite directly with Python:
```powershell
python tests/run_tests.py
```
This executes all 17 automated unit and workflow tests across Scenarios A through H.

---

## 7. Implemented Features Summary

1. **Dual Interconnected Portals**: Guardian and Cosmonaut interfaces operating on shared local application state.
2. **Candy Crush-Inspired Learning Roadmap**: Continuous SVG cubic bezier curved track connecting all milestone stone centers with multi-layered glow and dashed stepping paths. Enforces a 5-badge initial state cohort-wide (3 completed, 1 active with pulsing halo, 1 locked), with dynamic cohort-wide unlocking whenever the Guardian creates new badges.
3. **Standard 50-Mark Rubric**: Strict 5 criteria (Business Understanding, Architecture/Report, Technical Knowledge, Presentation, Q&A) scored 0-10 each, with automatic total (/50) and percentage calculations.
4. **Multi-Attempt History Retention**: When a resubmission is requested, all previous attempts retain their original marksheets and scores; subsequent attempts do not overwrite earlier records.
5. **Batch Leaderboard**: Fair ranking of all 6 Cosmonauts calculated on average score across approved badges, preventing unfair advantages from badge quantity.
6. **Project Submission Hub**: Supports PDF document upload, GitHub repository link, and raw script/code upload.
7. **In-App Material Viewer**: PDF previewer and embedded YouTube player with owner-disabled fallback links.
8. **Interactive Profile**: Cosmonauts can dynamically add/edit/remove skills and certifications, which immediately reflect in the dashboard.
9. **Deadline Extension Management**: Cosmonauts submit extension requests with reasons; Guardian approval automatically updates the badge deadline application-wide.
10. **Targeted Announcements & Read Receipts**: Broadcast notices to all or selected Cosmonauts, with real-time read receipt tracking.
11. **Automatic Audit Trail**: All assignments, submissions, evaluations, extensions, and publications generate chronological activity feed items.

---

## 8. Verification of End-to-End Workflows (Scenarios A through H)

All mandatory scenarios from Section 13 have been verified via automated integration tests (`tests/test_scenarios_a_to_h.py`):

- **Scenario A (Badge Publication)**: Guardian creates `TEST-500` and assigns it only to Astraea and Orion. Astraea sees the badge on her roadmap; unselected Cosmonaut Seraphina does not.
- **Scenario B (Submission & 50-Mark Assessment)**: Astraea submits a project; Guardian opens the deliverable, enters all 5 criteria scores, inputs strengths/improvements/feedback, and approves. Astraea's marksheet reflects 48.0/50 (96.0%) and the leaderboard updates in real-time.
- **Scenario C (Resubmission & History Retention)**: Lyra Solaris's Attempt 1 for Ingestion Foundations retains its 31.0/50 marksheet with resubmission requested; Attempt 2 is evaluated with 45.0/50 and both attempt marksheets remain fully accessible in history.
- **Scenario D (Deadline Extension)**: Orion requests an extension on SQL-201; Guardian approves; the new deadline propagates to Orion's timeline and Guardian views. Rejection flow preserves original deadline.
- **Scenario E (Announcements & Read Receipts)**: Guardian broadcasts batch-wide and targeted notices; targeted recipients receive them; marking as read updates the Guardian's read receipt count.
- **Scenario F (Materials)**: Guardian publishes YouTube and PDF resources; Cosmonauts access them inside StarApp with responsive embedding.
- **Scenario G (Persistence)**: Full state serialization to JSON snapshot and reload verified without data loss.
- **Scenario H (Privacy & Permissions)**: Cosmonauts can view the batch leaderboard but cannot access other Cosmonauts' private dashboards or dossiers. Guardian retains full batch oversight.

---

## 9. Known Limitations of the Local-Only Prototype

1. **Multi-Tab Concurrency**: Storage updates synchronize via IndexedDB and localStorage; cross-tab synchronization triggers on next action or page refresh.
2. **Offline External Links**: While PDFs and code files are stored locally in base64, external GitHub repository links require an internet connection to browse external source trees on github.com.
3. **Client-Side Demo Authentication**: Demo authentication is designed for prototype demonstration. In production, authentication tokens and RBAC authorization must be verified by a secure backend server.

---

## 10. Future Migration Recommendations for a Real Backend

When transitioning StarApp to an enterprise production environment:
1. **API Layer**: Replace `starapp/storage.py` with RESTful or GraphQL endpoints (e.g. FastAPI or Django REST Framework). The modular Python data models in `starapp/models.py` map cleanly to Pydantic schemas or ORM models (SQLAlchemy / PostgreSQL).
2. **Object Storage**: Store large project deliverables and PDF documents in cloud object storage (Amazon S3, Google Cloud Storage) with signed temporary URLs, storing only metadata in the database.
3. **Real-Time Push**: Integrate WebSockets or Server-Sent Events (SSE) for instantaneous notification delivery across separate devices when a Guardian publishes an assessment or announcement.
4. **Production RBAC**: Enforce strict JSON Web Token (JWT) verification and role-based access control at the API gateway level to guarantee data isolation between Cosmonauts.

---

## 11. GitHub Synchronization

To synchronize local changes with the GitHub repository at any time:

```powershell
python push_to_github.py "Your commit message"
```

The script reads the personal access token and target repository directly from `.env` and pushes all project files to `main` via the GitHub REST API without requiring external binaries.


