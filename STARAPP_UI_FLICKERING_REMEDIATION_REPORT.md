# STARAPP — UI FLICKERING, LIQUID GLASS & RENDERING REMEDIATION REPORT

## 1. Executive Summary

A controlled, multi-phase remediation was executed against StarApp to eliminate global UI flickering, navigation tearing, Liquid Glass compositor instability, duplicate click dispatches, async cross-tab overwrite hazards, and scrollbar-induced viewport shifts—while preserving 100% of StarApp's Liquid Glass design language, domain business logic, offline storage, multi-window synchronization, and workflows across both Guardian and Cosmonaut portals.

Verification in real headless Chromium 157 (`cdp_harness.py`) and the expanded Python unit/regression test suite (`python tests/run_tests.py`: **35/35 passing**) confirms:
- **Zero full-app reconstruction across workspace navigation & modals:** `sidebarReplaced: false` and `mainReplaced: false` across every post-login navigation, tab switch, and modal open/close event (`regionSkipCounts`: `sidebarSkipped: 22`, `mainSkipped: 7`, `modalSkipped: 15`).
- **In-place sub-region patching:** Switching viewer tabs in `g_review_detail` (`pdf` -> `code`) preserved `.review-right-column` (`#guardian-rubric-form`) and unsaved draft text identically (`sameRight: true`, `reviewLeftOnly: 1`), and opening/closing the Material Reader modal preserved inline `.media-video-box iframe` DOM nodes (`ytIframePreserved: true`).
- **Cross-tab modal preservation:** Simulated cross-tab data updates while a badge modal was open updated `.modal-body` in place with `.modal-no-replay` without recreating `.modal-backdrop` (`backdropPreserved: true`, `modalPatchedInPlace: 1`).
- **Locked layout geometry:** `appMainClientWidth` remained fixed at `1165px` across all desktop routes (eliminating the baseline `1165px -> 1180px` jump on `g_review_detail`, `g_materials`, and `c_submission`).
- **Zero console errors, zero long tasks, zero horizontal overflow:** Verified across all 9 viewports from `1920x1080` down to `320x640`.

---

## 2. Confirmed Root Causes Addressed

| Category | Root Cause Resolved | Remediation Applied |
|---|---|---|
| **DOM & Navigation** | Monolithic `root.innerHTML = newHtml` rebuilt `<aside class="app-sidebar">`, `<main>`, flash messages, active forms, iframes, and modals on every interaction | Replaced browser update path with a keyed **3-region architecture** (`#starapp-shell-sidebar`, `#starapp-main-viewport` -> `#starapp-page-slot` -> `#starapp-flash-slot` + `#starapp-page-body`, and `#starapp-modal-root`) via `StarAppBridge.updateRegions()` while retaining `controller.render()` string output for compatibility/tests |
| **Session Restore Gap** | `"g_allotment"` was missing from `StarAppController._GUARDIAN_VIEWS`, breaking session restoration on reload | Added `"g_allotment"` to `_GUARDIAN_VIEWS` in `starapp/app.py` |
| **Scroll & Layout Shift** | `.app-main` scrollbar appearing/disappearing toggled viewport width (`1165px <-> 1180px`); `_captureScrolls()` missed `.app-main` and leaked offsets across unrelated routes | Added `scrollbar-gutter: stable` to `.app-main`; scoped scroll & focus restoration strictly to same-route updates and reset `existingViewport.scrollTop = 0` on route change |
| **Review Workspace Reloads** | Switching between PDF, Source Code, and GitHub Repo tabs tore down the entire rubric form and wrapped `#pdf-document-frame` in `isolation:isolate; transform:translateZ(0);` | Added `g_review_detail:{sub.id}` route key; `updateRegions` swaps `.review-left-column` alone when `routeKey` stays on the same submission; removed `isolation:isolate; transform:translateZ(0)` on `#pdf-document-frame`; aligned workspace height (`calc(100vh - 16px)`) with `css/responsive.css` |
| **Duplicate Click Dispatches** | `.media-pdf-box` stacked 3 bubbling `onclick="...view_material_preview..."` handlers on parent and child overlay elements | Consolidated to a single `onclick` dispatcher on `.media-pdf-box` in `starapp/views_common.py` |
| **Focus Loss on Filter** | Materials badge `<select>` lacked a deterministic `id` and `for=` label | Added `id="materials-badge-filter-select"` and matching `label[for="materials-badge-filter-select"]` |
| **Async Race & Cross-Tab Churn** | `BroadcastChannel` bursts and async IndexedDB reads could overwrite newer local navigations, fire mid-typing, or skip deduplication | Added `render_generation` on `StarAppController` with `expected_generation` guard in `reload_data()`, monotonic `localActionSeq`, `lastKnownDataJson` deduplication, 300ms burst coalescing (`pendingSyncTimer`), and active form-control deferral (`isActivelyEditingFormControl` + `focusout` flush) in `js/bridge.js` |
| **Liquid Glass & Layer Thrashing** | `.liquid-glass-card` / `.liquid-glass-panel` / `.liquid-glass-modal` combined `backdrop-filter`, `isolation: isolate`, `backface-visibility: hidden`, and `transform: translateZ(0)`, plus nested control blurs, mobile `blur(12px) saturate(150%)` modal overrides, sticky table cell blurs, permanent `will-change: transform`, and `transition: all` | Removed forced layer-promotion hacks (`isolation: isolate`, `backface-visibility: hidden`, `transform: translateZ(0)`), flattened nested control/table/modal blur overrides, removed permanent `will-change: transform`, added `:hover/:focus-within/:has(.metric-info-trigger.is-active)` elevation (`z-index: 60`), and replaced every `transition: all` across CSS and Python with explicit property lists |
| **Invalid Interactive Markup & Inline Hover JS** | `.glass-tooltip-popover` `<div>` was nested inside `<button class="metric-info-trigger">`; roadmap nodes mutated inline `style.transform` via `onmouseover`/`onmouseout` | Moved `.glass-tooltip-popover` out as a sibling inside `.has-glass-tooltip` with sibling CSS selectors (`+ .glass-tooltip-popover`); replaced inline JS hover handlers with `.milestone-container-node:hover` CSS rule |
| **Modal Replay & Responsive Wrapping** | Cross-tab updates re-triggered `.modal-backdrop` fade and timeline animations; 3 duplicate `@media (max-width: 768px)` blocks existed; narrow modal pills clipped at `390px` | Added `modal-no-replay` guard when updating an already-open modal body; consolidated `@media (max-width: 768px)` blocks; wrapped `.node-connector-strip` and inner rows under `@media (max-width: 540px)` |
| **Unused SVG Defs & Stale SW Cache** | Unused `<svg class="glass-svg-defs">` (`#container-glass` `feTurbulence` / `feDisplacementMap`) sat in `index.html`; CSS/JS/SW cache keys were outdated | Removed `<svg class="glass-svg-defs">` from `index.html`, versioned CSS/JS links to `?v=9`, and bumped `CACHE_NAME` to `"starapp-runtime-cache-v2"` in `sw.js` |

---

## 3. Modified Files

### Remediated in This Pass
- [`starapp/app.py`](file:///c:/Users/USER/Desktop/starapp_demo/starapp/app.py): Added `"g_allotment"` to `_GUARDIAN_VIEWS`, `render_generation` tracking, `expected_generation` stale-async guard in `reload_data()`, and `_dispatch_browser_render()` building structured 3-region JSON payloads alongside full HTML assembly (`#starapp-shell-sidebar`, `#starapp-main-viewport`, `#starapp-page-slot`, `#starapp-flash-slot`, `#starapp-page-body`, `#starapp-modal-root`).
- [`starapp/views_guardian.py`](file:///c:/Users/USER/Desktop/starapp_demo/starapp/views_guardian.py): Added persistent sidebar `id`/`data-portal-role`/`data-user-id`/`data-nav-id`/`data-badge-for` attributes; moved `.glass-tooltip-popover` out of `<button class="metric-info-trigger">` as a sibling; replaced inline `transition: all` and inline KPI hover transitions with `.interactive` / explicit properties; removed `isolation:isolate; transform:translateZ(0)` on `#pdf-document-frame` and unified review detail height to `calc(100vh - 16px)`.
- [`starapp/views_cosmonaut.py`](file:///c:/Users/USER/Desktop/starapp_demo/starapp/views_cosmonaut.py): Added persistent sidebar `id`/`data-*` attributes; moved `.glass-tooltip-popover` out of `<button class="metric-info-trigger">`; replaced chart bar `transition: all` with explicit properties; removed `onmouseover`/`onmouseout` and inline transition on `.milestone-container-node`.
- [`starapp/views_common.py`](file:///c:/Users/USER/Desktop/starapp_demo/starapp/views_common.py): Removed redundant nested `onclick` attributes inside `.media-pdf-box` overlay children; added `id="materials-badge-filter-select"` and matching `<label for=...>`.
- [`js/bridge.js`](file:///c:/Users/USER/Desktop/starapp_demo/js/bridge.js): Added `updateRegions()`, persistent sidebar active/badge in-place updates (`_updateSidebarInPlace`), `.review-left-column`-only replacement for `g_review_detail` tab switches, in-place `.modal-body.modal-no-replay` patching, route-scoped `_captureScrolls`/`_restoreScrolls`/`_captureFocus`/`_restoreFocus`, `localActionSeq`, `lastKnownDataJson`, 300ms burst coalescing (`pendingSyncTimer`), active-control edit deferral (`isActivelyEditingFormControl`), and `_getRenderState()`.
- [`js/starapp_bundle.js`](file:///c:/Users/USER/Desktop/starapp_demo/js/starapp_bundle.js): Regenerated cleanly via `python scripts/pack_py.py` (all 13 `starapp/*.py` modules).
- [`css/liquid_glass.css`](file:///c:/Users/USER/Desktop/starapp_demo/css/liquid_glass.css): Removed `isolation: isolate`, `backface-visibility: hidden`, `transform: translateZ(0)`, permanent `will-change: transform`, nested input/button `backdrop-filter` stacking, `.liquid-glass-modal` `backdrop-filter` override, and all `transition: all` rules; added `:has(.metric-info-trigger.is-active)` card stacking elevation and `+ .glass-tooltip-popover` sibling visibility selectors.
- [`css/layout.css`](file:///c:/Users/USER/Desktop/starapp_demo/css/layout.css): Added `scrollbar-gutter: stable` to `.app-main`, removed `transform: translateZ(0)` on `.app-topbar`, replaced `transition: all` on `.nav-link` and `.notif-btn`, cleaned redundant `!important` flags on `.modal-dialog`.
- [`css/components.css`](file:///c:/Users/USER/Desktop/starapp_demo/css/components.css): Replaced `transition: all` on `.form-control` and `.milestone-stone`, added `.modal-body.modal-no-replay` animation suppression rules, and added `.milestone-container-node` CSS `:hover` transition.
- [`css/responsive.css`](file:///c:/Users/USER/Desktop/starapp_demo/css/responsive.css): Consolidated 3 duplicate `@media (max-width: 768px)` blocks into one unified block, removed mobile modal `.liquid-glass-modal` blur/saturate override and `.cadet-risk-table` sticky-cell blurs, and added `@media (max-width: 540px)` `.node-connector-strip` wrapping.
- [`index.html`](file:///c:/Users/USER/Desktop/starapp_demo/index.html) & [`sw.js`](file:///c:/Users/USER/Desktop/starapp_demo/sw.js): Removed unused `<svg class="glass-svg-defs">` block, updated CSS/JS asset URLs to `?v=9`, and updated `CACHE_NAME` to `"starapp-runtime-cache-v2"`.
- [`tests/test_ui_remediation.py`](file:///c:/Users/USER/Desktop/starapp_demo/tests/test_ui_remediation.py): Added 8 Phase-9 automated unit and regression tests.

*(Note: `serve.py` and `starapp/roadmap.py` also show uncommitted modifications in `git status --short` from earlier fixes prior to this remediation pass.)*

---

## 4. Technical Measurement Comparison (Headless Chromium 157 CDP)

Measurements were collected using an automated Chrome DevTools Protocol WebSocket harness (`cdp_harness.py`) driving `http://127.0.0.1:8000/index.html` with Pyodide `0.26.2` before and after remediation.

### 4.1 DOM Stability & Functional Verification

| Scenario | Before Remediation | After Remediation |
|---|---|---|
| **Guardian Navigation (Dash -> Allotment -> Reviews -> Detail -> Materials -> Roadmap)** | `sidebarReplaced: true` and `mainReplaced: true` on every hop (`appRootUpdates` recreated full tree) | `sidebarReplaced: false` and `mainReplaced: false` on every hop (`sidebarSkipped: 22`, `mainSkipped: 7`) |
| **Desktop Scrollbar Width Stability (`appMainClientWidth`)** | Jumped `1165px` -> `1180px` on `g_review_detail`, `g_materials`, and `c_submission` | Locked at **`1165px`** across every desktop route |
| **Repeated 5-Hop Cosmonaut Loop (`10_repeated_navigation_5_hops`)** | `added: 25`, `removed: 25`, 5 full `#app-root` rebuilds | `added: 15` (`-40%`), `removed: 15` (`-40%`), `sidebarReplaced: false` x5, `mainReplaced: false` x5 |
| **Review Viewer Tab Switch (`pdf` -> `code` on `g_review_detail`)** | Destroyed rubric form on tab change *(not isolated in baseline)* | `switched: true`, **`sameRight: true`**, `#rubric-feedback` draft preserved (`"PERSISTED_RUBRIC_DRAFT"`), `reviewLeftOnly: 1` |
| **Materials PDF Overlay Click (`4b_materials_pdf_overlay_click`)** | Seed started empty (`no-box`); source contained 3 bubbling `onclick` handlers | Seeded PDF + YouTube card: **single** `view_material_preview` dispatch, `hasPreviewModal: true`, inline `.media-video-box iframe` preserved across modal open & close (`ytIframePreserved: true`) |
| **Mobile Modal `backdrop-filter` (`390x844`)** | `"blur(12px) saturate(1.5)"` | **`"none"`** |
| **Cross-Tab `reload_data` While Badge Modal Open** | Full DOM teardown & modal animation replay *(baseline behavior)* | **`backdropPreserved: true`**, **`hasNoReplayClass: true`**, `modalPatchedInPlace: 1` |
| **Console Errors & Long Tasks (`>50ms`)** | `console_errors: []`, `longTasks: []` | `console_errors: []`, `longTasks: []` |

### 4.2 DevTools Performance Counters & Trace Summary

Per-step CDP `Performance.getMetrics()` deltas observed:
- `1_guardian_dash_to_allotment`: `layoutCountDelta: 1`, `layoutDurationDeltaMs: 13.815ms` (before: `17.706ms`), `recalcDurationDeltaMs: 5.469ms`, `scriptDurationDeltaMs: 11.835ms`, `wallMs: 332.3ms`.
- `2_allotment_to_reviews`: `layoutCountDelta: 1`, `layoutDurationDeltaMs: 12.163ms`, `recalcDurationDeltaMs: 6.867ms`, `scriptDurationDeltaMs: 3.614ms`, `wallMs: 318.7ms`.
- `4b_materials_pdf_overlay_click`: `layoutCountDelta: 8`, `layoutDurationDeltaMs: 8.714ms`, `recalcDurationDeltaMs: 3.66ms`, `scriptDurationDeltaMs: 5.117ms`.
- `9_close_modal`: `layoutCountDelta: 1`, `layoutDurationDeltaMs: 0.219ms`, `recalcDurationDeltaMs: 0.02ms`, `scriptDurationDeltaMs: 4.684ms`.
- `11_cross_tab_reload_modal_open`: `layoutDurationDeltaMs: 6.437ms`, `recalcDurationDeltaMs: 2.947ms`, `scriptDurationDeltaMs: 0.055ms`.
- **Full-suite Chrome Trace Event Counts:** Before baseline (`7` core navigation/modal scenarios + 9 viewports) recorded `Layout: 116`, `Paint: 709`, `UpdateLayoutTree: 98`. After remediation (which executed all baseline steps **plus** `save_bulk_materials` seeding, `3b_review_tab_switch_preserves_rubric`, real PDF overlay click & modal reader mount, and `11_cross_tab_reload_modal_open`) recorded `Layout: 193`, `Paint: 854`, `UpdateLayoutTree: 289` across the expanded workflow.

*(Artifacts saved in conversation artifacts folder: `screenshots_before/before_metrics.json` and `screenshots_after/after_metrics.json`.)*

---

## 5. Responsive Verification Across Desktop, Tablet & Mobile

Tested via CDP `Emulation.setDeviceMetricsOverride` on the remediated Cosmonaut Dashboard (`after_metrics.json`) with **0px horizontal overflow across every viewport**:

| Viewport | Device Profile | `docScrollWidth` | `innerWidth` | `horizontalOverflowPx` | `sidebarHeight` |
|---|---|---|---|---|---|
| `1920x1080` | Large Desktop | `1920` | `1920` | **`0`** | `1080px` |
| `1440x900` | Standard Desktop | `1440` | `1440` | **`0`** | `900px` |
| `1280x800` | Compact Desktop / Laptop | `1280` | `1280` | **`0`** | `800px` |
| `1024x768` | Small Laptop / Tablet Landscape | `1024` | `1024` | **`0`** | `768px` |
| `900x700` | Tablet Landscape Boundary | `900` | `900` | **`0`** | `700px` |
| `768x1024` | Tablet Portrait (`<=768px` breakpoint) | `768` | `768` | **`0`** | `338.25px` |
| `480x800` | Large Phone | `480` | `480` | **`0`** | `418.25px` |
| `390x844` | Mobile Portrait | `390` | `390` | **`0`** | `578.25px` |
| `320x640` | Small Mobile | `320` | `320` | **`0`** | `578.25px` |

---

## 6. Before & After Screenshot Artifacts

Verified visually in headless Chromium 157 (`screenshots_before/` and `screenshots_after/` inside the conversation artifact directory):
- **Guardian Dashboard (`1440x900`):** [before_01](file:///C:/Users/USER/.gemini/antigravity/brain/320c4c3d-f84e-4b61-8bcb-419514dbf783/screenshots_before/before_01_guardian_dashboard.png) | [after_01](file:///C:/Users/USER/.gemini/antigravity/brain/320c4c3d-f84e-4b61-8bcb-419514dbf783/screenshots_after/after_01_guardian_dashboard.png) — Liquid Glass cards, KPI tooltips, cohort chart, and sidebar styling preserved identically.
- **Guardian Review Detail (`1440x900`):** [before_04](file:///C:/Users/USER/.gemini/antigravity/brain/320c4c3d-f84e-4b61-8bcb-419514dbf783/screenshots_before/before_04_guardian_review_detail.png) | [after_04](file:///C:/Users/USER/.gemini/antigravity/brain/320c4c3d-f84e-4b61-8bcb-419514dbf783/screenshots_after/after_04_guardian_review_detail.png) — PDF deliverable viewer + sticky right-hand 50-mark rubric form at locked `1165px` container width.
- **Guardian PDF Theater Modal (`1440x900`):** [after_06_guardian_pdf_modal.png](file:///C:/Users/USER/.gemini/antigravity/brain/320c4c3d-f84e-4b61-8bcb-419514dbf783/screenshots_after/after_06_guardian_pdf_modal.png) — Verified single-click overlay launch into full large-reader modal while background YouTube iframe remained mounted.
- **Mobile Timeline Modal (`390x844`):** [before_07](file:///C:/Users/USER/.gemini/antigravity/brain/320c4c3d-f84e-4b61-8bcb-419514dbf783/screenshots_before/before_07_mobile_390_modal.png) | [after_07](file:///C:/Users/USER/.gemini/antigravity/brain/320c4c3d-f84e-4b61-8bcb-419514dbf783/screenshots_after/after_07_mobile_390_modal.png) — Before: horizontal right-edge clipping on `.node-connector-strip` status pills (`Completed`); After: clean vertical flex wrapping inside cards with mobile `backdrop-filter: none` on `.liquid-glass-modal`.
- **Cosmonaut Dashboard & Roadmap (`1440x900`):** [after_08](file:///C:/Users/USER/.gemini/antigravity/brain/320c4c3d-f84e-4b61-8bcb-419514dbf783/screenshots_after/after_08_cosmonaut_dashboard.png) | [after_09](file:///C:/Users/USER/.gemini/antigravity/brain/320c4c3d-f84e-4b61-8bcb-419514dbf783/screenshots_after/after_09_cosmonaut_roadmap.png)
- **Mobile Breakpoints (`390x844` & `320x640`):** [after_resp_390x844.png](file:///C:/Users/USER/.gemini/antigravity/brain/320c4c3d-f84e-4b61-8bcb-419514dbf783/screenshots_after/after_resp_390x844.png) | [after_resp_320x640.png](file:///C:/Users/USER/.gemini/antigravity/brain/320c4c3d-f84e-4b61-8bcb-419514dbf783/screenshots_after/after_resp_320x640.png)

---

## 7. Automated Test Suite Results

Command run after final edits:
```powershell
python tests/run_tests.py
```
Result: **`Ran 35 tests in 0.045s` — `OK` (0 failures, 0 errors, 0 skipped)** across:
- `test_all.py` (11 tests)
- `test_dashboard_enhancements.py` (5 tests)
- `test_extension_flow.py` (1 test)
- `test_materials_flow.py` (1 test)
- `test_review_flow.py` (1 test)
- `test_scenarios_a_to_h.py` (8 tests: Scenarios A–H)
- `test_ui_remediation.py` (8 Phase-9 regression tests)

---

## 8. Remaining Tradeoffs & Notes

1. **Page-Body Granularity Between Distinct Routes:** While sidebar, flash banner, and modal regions remain completely untouched when unchanged (and same-route updates in `g_review_detail` only swap `.review-left-column`), navigating between two completely different views still replaces `#starapp-page-body` in a single atomic write so unrelated page trees never mismatch or leak state.
2. **Real-World Browser PDF/YouTube Network Latency:** In headless verification, the seeded PDF payload was an inline base64 stub and offline YouTube embeds depend on external network availability; however, DOM preservation of the embed node itself (`ytIframePreserved: true`) was directly confirmed.
3. **Previous Session File Changes in Working Tree:** `serve.py` and `starapp/roadmap.py` were modified before this remediation pass and left intact.

---

## 9. Recovery & Runtime Instructions

1. **Start the application locally:**
   ```powershell
   python serve.py
   ```
   *(Or `python -m http.server 8000 --bind 127.0.0.1`, then open `http://127.0.0.1:8000/index.html`.)*
2. **If editing any `starapp/*.py` module:** Always re-pack the browser Python bundle before reloading:
   ```powershell
   python scripts/pack_py.py
   ```
3. **Run the verification suite:**
   ```powershell
   python tests/run_tests.py
   ```
4. **Hard-refresh cached browser tabs if needed:** Static assets and the Service Worker use cache version `?v=9` / `"starapp-runtime-cache-v2"`. Triggering a hard reload or clearing site data ensures older service worker registrations update immediately.

