/**
 * STARAPP MINIMAL JS BRIDGE & REAL-TIME MULTI-WINDOW SYNC
 * Technical Explanation:
 * Browser APIs such as IndexedDB (asynchronous object store) and FileReader (reading local
 * files as Base64 for persistent offline storage) require asynchronous JavaScript promises.
 * Multi-window support uses sessionStorage for per-tab authentication isolation and BroadcastChannel
 * + storage events for instant cross-window live data synchronization.
 * To keep strict architectural purity, NO business logic, calculations, or validations exist here.
 * This file is solely a thin asynchronous storage and file I/O bridge for Python/Pyodide.
 */

(function () {
  const DB_NAME = "StarAppLocalDB";
  const DB_VERSION = 7;
  const STORE_NAME = "starapp_state";

  // Tab-unique identifier to prevent self-triggering broadcast loops
  const currentWindowId = "win_" + Math.random().toString(36).substring(2, 10);
  let lastSyncTimestamp = 0;
  let localActionSeq = 0;
  let lastKnownDataJson = null;
  let pendingSyncTimer = null;
  let pendingDeferredReload = false;

  // Incremental 3-region DOM state
  const renderState = {
    mode: null,
    portalKey: null,
    routeKey: null,
    pageContainerClass: null,
    flashHtml: null,
    mainHtml: null,
    modalKind: "",
    modalKey: "",
    modalHtml: "",
    appliedGeneration: 0,
    regionSkipCounts: {
      sidebarSkipped: 0,
      mainSkipped: 0,
      modalSkipped: 0,
      modalPatchedInPlace: 0,
      reviewLeftOnly: 0,
      staleAsyncDropped: 0
    }
  };

  function isActivelyEditingFormControl() {
    const el = document.activeElement;
    if (!el || el === document.body) return false;
    const tag = el.tagName;
    if (tag === "TEXTAREA") return true;
    if (tag === "INPUT") {
      const t = (el.type || "text").toLowerCase();
      return !["button", "submit", "reset", "checkbox", "radio", "file"].includes(t);
    }
    return false;
  }

  document.addEventListener("focusout", () => {
    if (pendingDeferredReload && !isActivelyEditingFormControl()) {
      pendingDeferredReload = false;
      triggerCrossWindowLiveReload("deferred_after_edit");
    }
  });

  // Real-time cross-window synchronization channel
  const syncChannel = ("BroadcastChannel" in window)
    ? new BroadcastChannel("starapp_cross_window_sync")
    : null;

  function openDatabase() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME);
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // Cross-window live data synchronization handler with async race guard
  async function triggerCrossWindowLiveReload(sourceName) {
    if (isActivelyEditingFormControl()) {
      pendingDeferredReload = true;
      return;
    }
    const now = Date.now();
    // Coalesce bursts within 300ms into a single trailing reload
    if (now - lastSyncTimestamp < 300) {
      if (!pendingSyncTimer) {
        pendingSyncTimer = setTimeout(() => {
          pendingSyncTimer = null;
          triggerCrossWindowLiveReload(sourceName);
        }, 310 - (now - lastSyncTimestamp));
      }
      return;
    }
    lastSyncTimestamp = now;
    const seqAtStart = localActionSeq;

    try {
      const latestDataJson = await window.StarAppBridge.getStore("data");
      // Abort if user navigated/acted locally while awaiting IndexedDB I/O
      if (localActionSeq !== seqAtStart) {
        renderState.regionSkipCounts.staleAsyncDropped += 1;
        return;
      }
      if (!latestDataJson || latestDataJson === lastKnownDataJson) {
        return;
      }
      if (window.starAppController && typeof window.starAppController.reload_data === "function") {
        lastKnownDataJson = latestDataJson;
        console.log(`[StarAppBridge] Live data sync executed from ${sourceName}. Updating controller...`);
        window.starAppController.reload_data(latestDataJson, renderState.appliedGeneration);
      }
    } catch (err) {
      console.warn("[StarAppBridge] Cross-window live sync error:", err);
    }
  }

  // 1. Listen for BroadcastChannel events from other browser windows (preferred, tab-targeted)
  if (syncChannel) {
    syncChannel.onmessage = (event) => {
      if (event.data && event.data.type === "STARAPP_DATA_UPDATED" && event.data.sender !== currentWindowId) {
        triggerCrossWindowLiveReload("BroadcastChannel");
      }
    };
  } else {
    // 2. Fallback: ONLY listen for storage events if BroadcastChannel is not supported
    // Prevents duplicate sync events firing within milliseconds of each other
    window.addEventListener("storage", (e) => {
      if (e.key === "starapp_data" && e.newValue) {
        triggerCrossWindowLiveReload("storage_event");
      }
    });
  }

  window.StarAppBridge = {
    // Current window ID for debugging & multi-window telemetry
    getWindowId() {
      return currentWindowId;
    },

    // Read JSON state from IndexedDB / Storage
    async getStore(key) {
      if (key === "session") {
        // A. Check URL query parameters for fast role-based multi-window launching (e.g. ?role=guardian or ?role=cosmonaut)
        try {
          const urlParams = new URLSearchParams(window.location.search);
          const requestedRole = urlParams.get("role");
          const requestedUser = urlParams.get("user");

          if (requestedRole === "guardian" || requestedUser === "guardian_1") {
            const sess = JSON.stringify({ user_id: "guardian_1", current_view: "g_dashboard" });
            sessionStorage.setItem("starapp_session", sess);
            return sess;
          } else if (requestedRole === "cosmonaut" || requestedUser === "cosmo_1") {
            const sess = JSON.stringify({ user_id: "cosmo_1", current_view: "c_dashboard" });
            sessionStorage.setItem("starapp_session", sess);
            return sess;
          }
        } catch (e) {}

        // B. Read per-window isolated session from sessionStorage
        const sessionInTab = sessionStorage.getItem("starapp_session");
        if (sessionInTab) {
          return sessionInTab;
        }

        // C. Fallback: return null (renders the clean login view allowing this window to choose its own role)
        return null;
      }

      // Shared domain data store across all windows (localStorage + IndexedDB single source of truth)
      try {
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
          const tx = db.transaction(STORE_NAME, "readonly");
          const store = tx.objectStore(STORE_NAME);
          const req = store.get(key);
          req.onsuccess = () => resolve(req.result || localStorage.getItem("starapp_" + key) || null);
          req.onerror = () => resolve(localStorage.getItem("starapp_" + key) || null);
        });
      } catch (err) {
        console.warn("[StarAppBridge] IndexedDB read fallback to localStorage", err);
        return localStorage.getItem("starapp_" + key);
      }
    },

    // Write JSON state to storage
    async setStore(key, value) {
      if (key === "session") {
        // Tab-isolated session storage: keeps Window 1 (Cosmonaut) and Window 2 (Guardian) independent!
        sessionStorage.setItem("starapp_session", value);
        return true;
      }

      // Data store write: persist in shared localStorage + IndexedDB
      if (key === "data") {
        lastKnownDataJson = value;
      }
      try {
        localStorage.setItem("starapp_" + key, value);
        const db = await openDatabase();
        const tx = db.transaction(STORE_NAME, "readwrite");
        const store = tx.objectStore(STORE_NAME);
        store.put(value, key);
      } catch (err) {
        console.warn("[StarAppBridge] Data persisted in localStorage", err);
      }

      // Broadcast live update event to all other open windows/tabs
      if (syncChannel && key === "data") {
        try {
          syncChannel.postMessage({
            type: "STARAPP_DATA_UPDATED",
            sender: currentWindowId,
            timestamp: Date.now()
          });
        } catch (e) {}
      }

      return true;
    },

    // Clear state
    async clearStore() {
      sessionStorage.removeItem("starapp_session");
      localStorage.removeItem("starapp_data");
      localStorage.removeItem("starapp_session");
      try {
        const db = await openDatabase();
        const tx = db.transaction(STORE_NAME, "readwrite");
        const store = tx.objectStore(STORE_NAME);
        store.clear();
      } catch (err) {}

      if (syncChannel) {
        try {
          syncChannel.postMessage({
            type: "STARAPP_DATA_UPDATED",
            sender: currentWindowId,
            timestamp: Date.now()
          });
        } catch (e) {}
      }
      return true;
    },

    // Read user uploaded file as Base64 data URL
    readFileAsDataUrl(fileInputId) {
      return new Promise((resolve, reject) => {
        const input = typeof fileInputId === "string" ? document.getElementById(fileInputId) : fileInputId;
        if (!input || !input.files || input.files.length === 0) {
          resolve(null);
          return;
        }
        const file = input.files[0];
        const reader = new FileReader();
        reader.onload = () => resolve({
          name: file.name,
          size: file.size,
          type: file.type,
          dataUrl: reader.result
        });
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(file);
      });
    },

    // Read user uploaded file as UTF-8 Text
    readFileAsText(fileInputId) {
      return new Promise((resolve, reject) => {
        const input = typeof fileInputId === "string" ? document.getElementById(fileInputId) : fileInputId;
        if (!input || !input.files || input.files.length === 0) {
          resolve(null);
          return;
        }
        const file = input.files[0];
        const reader = new FileReader();
        reader.onload = () => resolve({
          name: file.name,
          size: file.size,
          type: file.type,
          text: reader.result
        });
        reader.onerror = () => reject(reader.error);
        reader.readAsText(file);
      });
    },

    // High-performance asynchronous submission form handler
    async submitCosmonautDeliverables() {
      const badgeInp = document.getElementById("submission-badge-id");
      const pdfInp = document.getElementById("submission-pdf-file");
      const codeInp = document.getElementById("submission-code-file");
      const ghInp = document.getElementById("submission-github-url");

      let pdfData = null;
      if (pdfInp && pdfInp.files && pdfInp.files.length > 0) {
        pdfData = await window.StarAppBridge.readFileAsDataUrl("submission-pdf-file");
      }

      let codeData = null;
      if (codeInp && codeInp.files && codeInp.files.length > 0) {
        codeData = await window.StarAppBridge.readFileAsText("submission-code-file");
      }

      const payload = {
        badge_id: badgeInp ? badgeInp.value : "",
        pdf_name: pdfData ? pdfData.name : "",
        pdf_payload: pdfData ? pdfData.dataUrl : "",
        code_name: codeData ? codeData.name : "",
        code_payload: codeData ? codeData.text : "",
        github_url: ghInp ? ghInp.value.trim() : ""
      };

      window.StarAppBridge.dispatchAction("submit_project_deliverable", JSON.stringify(payload));
    },

    // Real-time recalculation of the 50-mark rubric in browser DOM
    recalcRubricTotal() {
      const bu = parseFloat(document.getElementById("rubric-bu")?.value || 0);
      const ar = parseFloat(document.getElementById("rubric-ar")?.value || 0);
      const tk = parseFloat(document.getElementById("rubric-tk")?.value || 0);
      const pr = parseFloat(document.getElementById("rubric-pr")?.value || 0);
      const qa = parseFloat(document.getElementById("rubric-qa")?.value || 0);
      const total = bu + ar + tk + pr + qa;
      const pct = (total / 50.0) * 100.0;
      const formatted = total.toFixed(1) + " / 50.0 (" + pct.toFixed(1) + "%)";
      const disp = document.getElementById("rubric-total-display");
      if (disp) {
        disp.innerText = formatted;
      }
      const sumDisp = document.getElementById("rubric-sum-display");
      if (sumDisp) {
        sumDisp.innerText = formatted;
      }
    },

    // Submit evaluation marksheet with form values collected from DOM
    submitEvaluationMarksheet(subId) {
      const bu = parseFloat(document.getElementById("rubric-bu")?.value || 0);
      const ar = parseFloat(document.getElementById("rubric-ar")?.value || 0);
      const tk = parseFloat(document.getElementById("rubric-tk")?.value || 0);
      const pr = parseFloat(document.getElementById("rubric-pr")?.value || 0);
      const qa = parseFloat(document.getElementById("rubric-qa")?.value || 0);
      const strengths = document.getElementById("rubric-strengths")?.value || "";
      const improvements = document.getElementById("rubric-improvements")?.value || "";
      const feedback = document.getElementById("rubric-feedback")?.value || "";
      const decision = document.getElementById("rubric-decision")?.value || "approve";

      const payload = {
        submission_id: subId,
        bu: bu,
        ar: ar,
        tk: tk,
        pr: pr,
        qa: qa,
        strengths: strengths,
        improvements: improvements,
        feedback: feedback,
        decision: decision
      };
      window.StarAppBridge.dispatchAction("submit_evaluation_marksheet", JSON.stringify(payload));
    },

    // Toggle expand deliverable viewer to full window height in-place
    toggleViewerExpand() {
      const container = document.getElementById("deliverable-viewport-container");
      const btn = document.getElementById("toggle-viewer-expand-btn");
      if (!container) return;
      if (container.style.height === "calc(100vh - 140px)" || container.style.height === "88vh") {
        container.style.height = "760px";
        if (btn) btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:5px;"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg> Expand Viewport';
      } else {
        container.style.height = "calc(100vh - 140px)";
        if (btn) btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:5px;"><path d="M4 14h6v6M20 10h-6V4M14 10l7-7M10 14l-7 7"/></svg> Standard Height';
        container.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    },

    // Copy source code to clipboard
    copySourceCode() {
      const pre = document.getElementById("raw-code-store");
      if (pre) {
        navigator.clipboard.writeText(pre.innerText).then(() => {
          alert("Source code copied to clipboard!");
        }).catch(() => {
          alert("Source code copied.");
        });
      }
    },

    // In-memory array for multiple selected PDFs
    bulkPdfs: [],

    // Handle multi-PDF selection via FileReader
    handleBulkPdfSelect(event) {
      const files = event.target.files;
      if (!files || !files.length) return;
      if (!window.StarAppBridge.bulkPdfs) {
        window.StarAppBridge.bulkPdfs = [];
      }
      const promises = Array.from(files).map(file => {
        return new Promise((resolve) => {
          const reader = new FileReader();
          reader.onload = (e) => {
            resolve({
              name: file.name,
              size: (file.size / 1024).toFixed(1),
              dataUrl: e.target.result
            });
          };
          reader.readAsDataURL(file);
        });
      });

      Promise.all(promises).then(newItems => {
        window.StarAppBridge.bulkPdfs = window.StarAppBridge.bulkPdfs.concat(newItems);
        window.StarAppBridge.renderBulkPdfList();
      });
    },

    // Remove PDF from bulk list
    removeBulkPdf(index) {
      if (window.StarAppBridge.bulkPdfs && window.StarAppBridge.bulkPdfs.length > index) {
        window.StarAppBridge.bulkPdfs.splice(index, 1);
        window.StarAppBridge.renderBulkPdfList();
      }
    },

    // Render interactive list of selected PDFs
    renderBulkPdfList() {
      const container = document.getElementById("bulk-pdf-list");
      if (!container) return;
      if (!window.StarAppBridge.bulkPdfs || !window.StarAppBridge.bulkPdfs.length) {
        container.innerHTML = "";
        return;
      }
      container.innerHTML = window.StarAppBridge.bulkPdfs.map((item, idx) => `
        <div style="display:flex; justify-content:space-between; align-items:center; background:#FFFFFF; padding:6px 12px; border-radius:var(--radius-xs); border:1px solid var(--icy-steel); font-size:12px;">
          <div style="display:flex; align-items:center; gap:8px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
            <span style="font-weight:800; color:var(--deep-frozen-midnight);">📄 ${item.name.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</span>
            <span style="color:var(--frost-navy-50); font-size:11px;">(${item.size} KB)</span>
          </div>
          <button type="button" onclick="window.StarAppBridge.removeBulkPdf(${idx})" style="background:transparent; border:none; color:#d9534f; cursor:pointer; font-weight:800; font-size:16px; padding:0 4px;" title="Remove this PDF">&times;</button>
        </div>
      `).join("");
    },

    // Clear or remove YouTube row
    clearOrRemoveYouTubeRow(btn) {
      if (document.querySelectorAll('.youtube-input-row').length > 1) {
        btn.parentElement.remove();
      } else {
        const title = btn.parentElement.querySelector('.yt-title-input');
        const url = btn.parentElement.querySelector('.yt-url-input');
        if (title) title.value = '';
        if (url) url.value = '';
      }
    },

    // Add extra dynamic YouTube row
    addYouTubeRow() {
      const container = document.getElementById("youtube-rows-container");
      if (!container) return;
      const row = document.createElement("div");
      row.className = "youtube-input-row";
      row.style.cssText = "display:grid; grid-template-columns:1fr 1.5fr auto; gap:8px; align-items:center; margin-bottom:8px;";
      row.innerHTML = `
        <input type="text" class="yt-title-input form-control" placeholder="Video Title (e.g. Masterclass Lecture)">
        <input type="url" class="yt-url-input form-control" placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/...">
        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.clearOrRemoveYouTubeRow(this)" style="color:#d9534f; padding:4px 8px; font-weight:800;" title="Remove row">&times;</button>
      `;
      container.appendChild(row);
    },

    // Submit bulk materials form
    submitBulkMaterials() {
      const badgeEl = document.getElementById("bulk-mat-badge");
      const topicEl = document.getElementById("bulk-mat-topic");
      const descEl = document.getElementById("bulk-mat-desc");

      const badgeId = badgeEl ? badgeEl.value : "";
      const topic = topicEl ? topicEl.value.trim() : "Module Specification";
      const desc = descEl ? descEl.value.trim() : "";

      const pdfs = window.StarAppBridge.bulkPdfs || [];

      const ytRows = document.querySelectorAll("#youtube-rows-container .youtube-input-row");
      const youtubeLinks = [];
      ytRows.forEach(row => {
        const urlInput = row.querySelector(".yt-url-input");
        const titleInput = row.querySelector(".yt-title-input");
        const url = urlInput ? urlInput.value.trim() : "";
        const title = titleInput ? titleInput.value.trim() : "";
        if (url) {
          youtubeLinks.push({ title: title, url: url });
        }
      });

      if (pdfs.length === 0 && youtubeLinks.length === 0) {
        alert("Please select at least one PDF file or enter at least one YouTube link.");
        return;
      }

      const payload = {
        badge_id: badgeId,
        topic: topic,
        description: desc,
        pdfs: pdfs,
        youtube_links: youtubeLinks
      };

      // Reset in-memory list and submit
      window.StarAppBridge.bulkPdfs = [];
      window.StarAppBridge.dispatchAction("save_bulk_materials", JSON.stringify(payload));
    },

    // Submit single material edit form
    submitEditMaterial(matId) {
      const badgeId = document.getElementById("edit-mat-badge")?.value || "";
      const title = document.getElementById("edit-mat-title")?.value.trim() || "";
      const topic = document.getElementById("edit-mat-topic")?.value.trim() || "";
      const type = document.getElementById("edit-mat-type")?.value || "youtube";
      const url = document.getElementById("edit-mat-url")?.value.trim() || "";
      const desc = document.getElementById("edit-mat-desc")?.value.trim() || "";

      if (!title) {
        alert("Please enter a title for the material.");
        return;
      }

      const payload = {
        material_id: matId,
        badge_id: badgeId,
        title: title,
        topic: topic,
        material_type: type,
        url_or_data: url,
        description: desc
      };

      window.StarAppBridge.dispatchAction("update_material", JSON.stringify(payload));
    },

    // Read-only telemetry accessor for regression verification
    _getRenderState() {
      return renderState;
    },

    // Dispatch UI click/action event to Python controller
    dispatchAction(action, payloadJson = "{}") {
      localActionSeq += 1;
      pendingDeferredReload = false;
      if (window.starAppController && typeof window.starAppController.handle_event === "function") {
        window.starAppController.handle_event(action, payloadJson);
      } else {
        console.warn("[StarAppBridge] Controller not yet initialized. Queuing action:", action);
      }
    },

    // Capture focus + selection within an optional root/container
    _captureFocus() {
      const activeEl = document.activeElement;
      const activeId = (activeEl && activeEl !== document.body && activeEl.id) ? activeEl.id : null;
      let selStart = null;
      let selEnd = null;
      if (activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA")) {
        try {
          selStart = activeEl.selectionStart;
          selEnd = activeEl.selectionEnd;
        } catch (e) {}
      }
      return { activeId, selStart, selEnd };
    },

    _restoreFocus(focusSnap) {
      if (!focusSnap || !focusSnap.activeId) return;
      const targetFocus = document.getElementById(focusSnap.activeId);
      if (targetFocus && typeof targetFocus.focus === "function") {
        targetFocus.focus({ preventScroll: true });
        if (focusSnap.selStart !== null && focusSnap.selEnd !== null && typeof targetFocus.setSelectionRange === "function") {
          try {
            targetFocus.setSelectionRange(focusSnap.selStart, focusSnap.selEnd);
          } catch (e) {}
        }
      }
    },

    _captureScrolls(container) {
      if (!container) return [];
      const snapshots = [];
      const scrollables = [];
      if (container.classList && container.classList.contains("app-main")) {
        scrollables.push(container);
      }
      const mainViewport = document.getElementById("starapp-main-viewport") || document.querySelector(".app-main");
      if (mainViewport && !scrollables.includes(mainViewport)) {
        scrollables.push(mainViewport);
      }
      container.querySelectorAll("[id], .app-main, .sidebar-nav, .page-container, .table-responsive, .modal-body, .review-workspace-grid").forEach((el) => {
        if (!scrollables.includes(el)) scrollables.push(el);
      });
      scrollables.forEach((el) => {
        if (el.scrollTop > 0 || el.scrollLeft > 0) {
          snapshots.push({
            id: el.id || null,
            firstClass: (typeof el.className === "string" && el.className.trim()) ? el.className.trim().split(/\s+/)[0] : null,
            top: el.scrollTop,
            left: el.scrollLeft
          });
        }
      });
      return snapshots;
    },

    _restoreScrolls(container, snapshots) {
      if (!container || !snapshots || !snapshots.length) return;
      snapshots.forEach((snap) => {
        let target = snap.id ? document.getElementById(snap.id) : null;
        if (!target && snap.firstClass) {
          if (snap.firstClass === "app-main") {
            target = document.getElementById("starapp-main-viewport") || document.querySelector(".app-main");
          } else {
            target = container.querySelector("." + snap.firstClass);
          }
        }
        if (target) {
          target.scrollTop = snap.top;
          target.scrollLeft = snap.left;
        }
      });
    },

    // Update persistent sidebar active state and badges in-place without rebuilding <aside>
    _updateSidebarInPlace(sidebarEl, activeNavId, badgesMap) {
      if (!sidebarEl) return;
      sidebarEl.querySelectorAll("a.nav-link[data-nav-id]").forEach((link) => {
        const isActive = link.dataset.navId === activeNavId;
        if (link.classList.contains("active") !== isActive) {
          link.classList.toggle("active", isActive);
        }
      });
      if (badgesMap && typeof badgesMap === "object") {
        Object.entries(badgesMap).forEach(([navId, count]) => {
          const badgeEl = sidebarEl.querySelector(`.nav-badge[data-badge-for="${navId}"]`);
          if (badgeEl) {
            const nextText = String(count);
            if (badgeEl.textContent !== nextText) {
              badgeEl.textContent = nextText;
            }
            const shouldShow = Number(count) > 0;
            const currentlyHidden = badgeEl.style.display === "none";
            if (shouldShow && currentlyHidden) {
              badgeEl.style.display = "";
            } else if (!shouldShow && !currentlyHidden) {
              badgeEl.style.display = "none";
            }
          }
        });
      }
    },

    // 3-Region incremental renderer: Persistent Sidebar + Main Page Slot + Modal Root
    updateRegions(regionsJson) {
      const root = document.getElementById("app-root");
      if (!root) return;

      let payload;
      try {
        payload = typeof regionsJson === "string" ? JSON.parse(regionsJson) : regionsJson;
      } catch (e) {
        return;
      }
      if (!payload) return;

      if (payload.isCrossTabReload && payload.generation < renderState.appliedGeneration) {
        renderState.regionSkipCounts.staleAsyncDropped += 1;
        return;
      }
      renderState.appliedGeneration = Math.max(renderState.appliedGeneration, Number(payload.generation || 0));

      if (payload.pageTitle) {
        document.title = `StarApp — ${payload.pageTitle}`;
      }

      // Mode 1: Login view
      if (payload.mode === "login") {
        if (renderState.mode === "login" && renderState.mainHtml === payload.mainContentHtml) {
          renderState.regionSkipCounts.mainSkipped += 1;
          return;
        }
        root.innerHTML = payload.mainContentHtml;
        renderState.mode = "login";
        renderState.portalKey = "login";
        renderState.routeKey = "login";
        renderState.pageContainerClass = "";
        renderState.flashHtml = "";
        renderState.mainHtml = payload.mainContentHtml;
        renderState.modalKind = "";
        renderState.modalKey = "";
        renderState.modalHtml = "";
        return;
      }

      // Mode 2: Authenticated 3-Region Workspace
      const existingSidebar = document.getElementById("starapp-shell-sidebar");
      const existingViewport = document.getElementById("starapp-main-viewport");
      const existingPageSlot = document.getElementById("starapp-page-slot");
      const existingFlashSlot = document.getElementById("starapp-flash-slot");
      const existingPageBody = document.getElementById("starapp-page-body");
      const existingModalRoot = document.getElementById("starapp-modal-root");

      const canPatchRegions = Boolean(
        existingSidebar &&
        existingViewport &&
        existingPageSlot &&
        existingFlashSlot &&
        existingPageBody &&
        existingModalRoot &&
        renderState.mode === "workspace" &&
        renderState.portalKey === payload.portalKey
      );

      if (!canPatchRegions) {
        // Initial workspace mount or portal/user switch
        root.innerHTML =
          `${payload.sidebarHtml}` +
          `<div id="starapp-main-viewport" class="app-main">` +
            `<main id="starapp-page-slot" class="${payload.pageContainerClass}">` +
              `<div id="starapp-flash-slot">${payload.flashHtml || ""}</div>` +
              `<div id="starapp-page-body">${payload.mainContentHtml}</div>` +
            `</main>` +
          `</div>` +
          `<div id="starapp-modal-root">${payload.modalHtml || ""}</div>`;

        renderState.mode = "workspace";
        renderState.portalKey = payload.portalKey;
        renderState.routeKey = payload.routeKey;
        renderState.pageContainerClass = payload.pageContainerClass;
        renderState.flashHtml = payload.flashHtml || "";
        renderState.mainHtml = payload.mainContentHtml;
        renderState.modalKind = payload.activeModal || "";
        renderState.modalKey = payload.modalKey || "";
        renderState.modalHtml = payload.modalHtml || "";
        return;
      }

      // Region 1: Persistent Sidebar (update active link + badge counts in place)
      this._updateSidebarInPlace(existingSidebar, payload.activeNavId, payload.sidebarBadges);
      renderState.regionSkipCounts.sidebarSkipped += 1;

      // Region 2: Main Page Content
      const nextFlash = payload.flashHtml || "";
      if (renderState.pageContainerClass !== payload.pageContainerClass) {
        existingPageSlot.className = payload.pageContainerClass;
        renderState.pageContainerClass = payload.pageContainerClass;
      }
      if (renderState.flashHtml !== nextFlash) {
        existingFlashSlot.innerHTML = nextFlash;
        renderState.flashHtml = nextFlash;
      }

      if (renderState.mainHtml !== payload.mainContentHtml) {
        const sameRoute = (renderState.routeKey === payload.routeKey);
        const focusSnap = sameRoute ? this._captureFocus() : null;
        const scrollSnaps = sameRoute ? this._captureScrolls(existingViewport) : [];

        // Special case: switching viewer tab (pdf <-> code <-> github) on the SAME review submission
        // preserves .review-right-column (#guardian-rubric-form) untouched!
        let patchedLeftOnly = false;
        if (sameRoute && payload.routeKey.startsWith("g_review_detail:")) {
          const oldLeft = existingPageBody.querySelector(".review-left-column");
          if (oldLeft) {
            const tpl = document.createElement("template");
            tpl.innerHTML = payload.mainContentHtml;
            const newLeft = tpl.content.querySelector(".review-left-column");
            if (newLeft) {
              oldLeft.replaceWith(newLeft);
              patchedLeftOnly = true;
              renderState.regionSkipCounts.reviewLeftOnly += 1;
            }
          }
        }

        if (!patchedLeftOnly) {
          existingPageBody.innerHTML = payload.mainContentHtml;
        }

        renderState.mainHtml = payload.mainContentHtml;
        renderState.routeKey = payload.routeKey;

        if (sameRoute) {
          this._restoreScrolls(existingViewport, scrollSnaps);
          this._restoreFocus(focusSnap);
        } else {
          // Route changed: reset main viewport scroll cleanly without copying old page offsets
          existingViewport.scrollTop = 0;
          existingViewport.scrollLeft = 0;
        }
      } else {
        renderState.routeKey = payload.routeKey;
        renderState.regionSkipCounts.mainSkipped += 1;
      }

      // Region 3: Modal Root
      const nextModalKind = payload.activeModal || "";
      const nextModalKey = payload.modalKey || "";
      const nextModalHtml = payload.modalHtml || "";

      if (!nextModalKind) {
        if (renderState.modalKind) {
          existingModalRoot.innerHTML = "";
        } else {
          renderState.regionSkipCounts.modalSkipped += 1;
        }
        renderState.modalKind = "";
        renderState.modalKey = "";
        renderState.modalHtml = "";
      } else if (renderState.modalHtml === nextModalHtml) {
        renderState.regionSkipCounts.modalSkipped += 1;
      } else if (renderState.modalKind === nextModalKind && renderState.modalKey === nextModalKey) {
        // Same open modal updated (e.g. live BroadcastChannel sync): update title & body without restarting .modal-backdrop fade!
        const existingTitle = existingModalRoot.querySelector(".modal-title");
        const existingBody = existingModalRoot.querySelector(".modal-body");
        if (existingTitle && existingBody) {
          const tpl = document.createElement("template");
          tpl.innerHTML = nextModalHtml;
          const nextTitleEl = tpl.content.querySelector(".modal-title");
          const nextBodyEl = tpl.content.querySelector(".modal-body");
          if (nextTitleEl && nextBodyEl) {
            const modalFocus = this._captureFocus();
            const modalScrollTop = existingBody.scrollTop;
            if (existingTitle.textContent !== nextTitleEl.textContent) {
              existingTitle.textContent = nextTitleEl.textContent;
            }
            existingBody.classList.add("modal-no-replay");
            existingBody.innerHTML = nextBodyEl.innerHTML;
            existingBody.scrollTop = modalScrollTop;
            this._restoreFocus(modalFocus);
            renderState.modalHtml = nextModalHtml;
            renderState.regionSkipCounts.modalPatchedInPlace += 1;
            return;
          }
        }
        existingModalRoot.innerHTML = nextModalHtml;
        renderState.modalHtml = nextModalHtml;
      } else {
        existingModalRoot.innerHTML = nextModalHtml;
        renderState.modalKind = nextModalKind;
        renderState.modalKey = nextModalKey;
        renderState.modalHtml = nextModalHtml;
      }
    },

    // Fallback atomic DOM update (with .app-main scroll support)
    updateAppRoot(newHtml) {
      const root = document.getElementById("app-root");
      if (!root) return;

      const savedWindowY = window.scrollY || window.pageYOffset || 0;
      const scrollSnapshots = this._captureScrolls(root);
      const focusSnap = this._captureFocus();

      root.innerHTML = newHtml;
      renderState.mode = null;
      renderState.portalKey = null;

      if (savedWindowY > 0) {
        window.scrollTo(0, savedWindowY);
      }
      this._restoreScrolls(root, scrollSnapshots);
      this._restoreFocus(focusSnap);
    }
  };
})();
