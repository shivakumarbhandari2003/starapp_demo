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
  const DB_NAME = "StarAppLocalDB_v9";
  const DB_VERSION = 9;
  const STORE_NAME = "starapp_state";

  // Purge legacy synthetic database and old cached data
  try {
    const rawData = localStorage.getItem("starapp_data") || "";
    const rawDb = localStorage.getItem("starapp_sqlite_db") || "";
    if (rawData.includes("Elena Vance") || rawData.includes("badge_gov_101") || rawData.includes("Ada Lovelace") || rawData.includes("AGT-304") || rawDb.length > 0) {
      console.log("[StarAppBridge] Purging legacy synthetic state from localStorage & IndexedDB");
      localStorage.removeItem("starapp_data");
      localStorage.removeItem("starapp_sqlite_db");
      try { indexedDB.deleteDatabase("StarAppLocalDB"); } catch (e) {}
    }
  } catch (e) {}

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
    sidebarHtml: null,
    topbarHtml: null,
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
            const sess = JSON.stringify({ user_id: "guardian_1", current_view: "g_cycles" });
            sessionStorage.setItem("starapp_session", sess);
            return sess;
          } else if (requestedRole === "cosmonaut" || requestedUser === "cosmo_1") {
            const sess = JSON.stringify({ user_id: "cosmo_1", current_view: "c_choose_cycle" });
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

    // Publish badge from Guardian Approved Badge tray
    publishBadge(badgeId) {
      if (!badgeId) return;
      if (confirm("Publish this approved badge to the Academy curriculum and enable mapping to cadets?")) {
        window.StarAppBridge.dispatchAction("publish_badge", badgeId);
      }
    },

    // Submit technical assessment by assigned higher-band reviewer
    submitReviewerAssessment(subId) {
      const bu = parseFloat(document.getElementById("rubric-bu")?.value || 0);
      const ar = parseFloat(document.getElementById("rubric-ar")?.value || 0);
      const tk = parseFloat(document.getElementById("rubric-tk")?.value || 0);
      const pr = parseFloat(document.getElementById("rubric-pr")?.value || 0);
      const qa = parseFloat(document.getElementById("rubric-qa")?.value || 0);
      const strengths = document.getElementById("rubric-strengths")?.value || "";
      const improvements = document.getElementById("rubric-improvements")?.value || "";
      const feedback = document.getElementById("rubric-feedback")?.value || "";

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
        decision: (bu + ar + tk + pr + qa) >= 35.0 ? "approve" : "changes_requested"
      };
      window.StarAppBridge.dispatchAction("submit_reviewer_assessment", JSON.stringify(payload));
    },

    // Send a reviewer project (heading + content) to the selected mapped cosmonauts
    submitReviewerProject(badgeId, reviewerId) {
      const title = document.getElementById("rev_proj_title")?.value?.trim() || "";
      const content = document.getElementById("rev_proj_content")?.value?.trim() || "";
      const cosmonautIds = Array.from(document.querySelectorAll(".rev-proj-recipient:checked")).map((el) => el.value);
      if (!title) { alert("Please give the project a heading."); return; }
      if (!content) { alert("Please write the project content."); return; }
      if (!cosmonautIds.length) { alert("Select at least one mapped cosmonaut to send the project to."); return; }
      window.StarAppBridge.dispatchAction("send_reviewer_project", JSON.stringify({
        badge_id: badgeId,
        reviewer_id: reviewerId,
        title: title,
        content: content,
        cosmonaut_ids: cosmonautIds,
        status: "released"
      }));
    },

    // Submit Guardian final assessment marksheet & badge award determination
    submitGuardianFinalAssessment(subId) {
      const bu = parseFloat(document.getElementById("rubric-bu")?.value || 0);
      const ar = parseFloat(document.getElementById("rubric-ar")?.value || 0);
      const tk = parseFloat(document.getElementById("rubric-tk")?.value || 0);
      const pr = parseFloat(document.getElementById("rubric-pr")?.value || 0);
      const qa = parseFloat(document.getElementById("rubric-qa")?.value || 0);
      const strengths = document.getElementById("rubric-strengths")?.value || "";
      const improvements = document.getElementById("rubric-improvements")?.value || "";
      const feedback = document.getElementById("rubric-feedback")?.value || "";
      const decision = document.getElementById("rubric-decision")?.value || ((bu + ar + tk + pr + qa) >= 35.0 ? "approve" : "changes_requested");

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
      window.StarAppBridge.dispatchAction("submit_guardian_final_assessment", JSON.stringify(payload));
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

    // Instant client-side DOM filter for Mapping Badge dropdown list (optimized, zero-reflow)
    filterBadgeList(query) {
      const q = (query || "").trim().toLowerCase();
      const container = document.getElementById("mapping-badges-scroll");
      if (!container) return;
      window.requestAnimationFrame(() => {
        const items = container.querySelectorAll(".mapping-badge-item");
        for (let i = 0; i < items.length; i++) {
          const item = items[i];
          const badgeName = item.getAttribute("data-badge-name") || (item.textContent || "").toLowerCase();
          const matches = !q || badgeName.includes(q);
          const targetDisplay = matches ? "flex" : "none";
          if (item.style.display !== targetDisplay) {
            item.style.display = targetDisplay;
          }
        }
      });
    },

    // Instant client-side DOM filter for Mapping Cosmonauts dropdown list (optimized, zero-reflow)
    filterCosmoList(query) {
      const q = (query || "").trim().toLowerCase();
      const container = document.getElementById("mapping-cosmo-scroll");
      if (!container) return;
      window.requestAnimationFrame(() => {
        const items = container.querySelectorAll(".mapping-member-item");
        for (let i = 0; i < items.length; i++) {
          const item = items[i];
          const name = item.getAttribute("data-member-name") || "";
          const role = item.getAttribute("data-member-role") || "";
          const matches = !q || name.includes(q) || role.includes(q);
          const targetDisplay = matches ? "flex" : "none";
          if (item.style.display !== targetDisplay) {
            item.style.display = targetDisplay;
          }
        }
      });
    },

    // Instant client-side DOM filter for Mapping Reviewers dropdown list (optimized, zero-reflow)
    filterReviewerList(query) {
      const q = (query || "").trim().toLowerCase();
      const container = document.getElementById("mapping-reviewer-scroll");
      if (!container) return;
      window.requestAnimationFrame(() => {
        const items = container.querySelectorAll(".mapping-member-item");
        for (let i = 0; i < items.length; i++) {
          const item = items[i];
          const name = item.getAttribute("data-member-name") || "";
          const role = item.getAttribute("data-member-role") || "";
          const matches = !q || name.includes(q) || role.includes(q);
          const targetDisplay = matches ? "flex" : "none";
          if (item.style.display !== targetDisplay) {
            item.style.display = targetDisplay;
          }
        }
      });
    },

    // Toggle sidebar pinned-expanded / collapsed state with local persistence
    toggleSidebar() {
      const sb = document.getElementById("starapp-shell-sidebar");
      if (!sb) return;
      const isPinned = sb.classList.toggle("pinned-expanded");
      sb.classList.toggle("collapsed", !isPinned);
      try {
        localStorage.setItem("starapp_sidebar_collapsed", isPinned ? "0" : "1");
      } catch (e) {}
    },

    // Apply persisted sidebar state
    applyPersistedSidebarState() {
      try {
        const sb = document.getElementById("starapp-shell-sidebar");
        if (!sb) return;
        const isCollapsed = localStorage.getItem("starapp_sidebar_collapsed") === "1";
        if (isCollapsed) {
          sb.classList.remove("pinned-expanded");
          sb.classList.add("collapsed");
        } else if (localStorage.getItem("starapp_sidebar_collapsed") === "0") {
          sb.classList.add("pinned-expanded");
          sb.classList.remove("collapsed");
        }
      } catch (e) {}
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

    // Add custom capability
    addCustomCapability() {
      const input = document.getElementById("custom-capability-input");
      if (!input || !input.value.trim()) return;
      window.StarAppBridge.dispatchAction("add_custom_capability", input.value.trim());
      input.value = "";
    },

    // Liquid-Glass quick-add dialog for adding custom capability or skill inside dropdown
    openTaxonomyQuickAdd(kind) {
      const existing = document.getElementById("lg-taxonomy-modal");
      if (existing) existing.remove();

      const isSkill = kind === "skill";
      const capEl = document.getElementById("badge-capability-select");
      const currentCap = capEl?.value || capEl?.dataset?.currentCap || "Data & Machine";
      const titleText = isSkill ? "Add New Skill" : "Add New Capability";
      const subtitleText = isSkill
        ? `Create a persistent Skill under "${currentCap}".`
        : "Create a persistent Capability across the taxonomy catalog.";
      const placeholderText = isSkill
        ? "e.g., Vector Search, Agent Orchestration"
        : "e.g., Autonomous Systems, Spatial Computing";

      const overlay = document.createElement("div");
      overlay.id = "lg-taxonomy-modal";
      overlay.setAttribute("role", "dialog");
      overlay.setAttribute("aria-modal", "true");
      overlay.setAttribute("aria-labelledby", "lg-taxonomy-modal-title");
      overlay.style.cssText = [
        "position:fixed", "inset:0", "z-index:9999",
        "background:rgba(7,22,41,0.42)",
        "backdrop-filter:blur(8px)", "-webkit-backdrop-filter:blur(8px)",
        "display:flex", "align-items:center", "justify-content:center",
        "padding:20px"
      ].join(";");

      const card = document.createElement("div");
      card.className = "liquid-glass-card";
      card.style.cssText = [
        "width:100%", "max-width:460px", "padding:24px",
        "border-radius:20px",
        "background:rgba(255,255,255,0.95)",
        "border:1.5px solid var(--icy-steel)",
        "box-shadow:0 24px 60px rgba(7,22,41,0.22)"
      ].join(";");

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:14px;">
          <div>
            <h3 id="lg-taxonomy-modal-title" style="margin:0 0 4px 0; font-size:1.2rem; font-weight:800; color:var(--frost-navy);">${titleText}</h3>
            <p id="lg-taxonomy-modal-sub" style="margin:0; font-size:13.5px; font-weight:500; color:var(--frost-navy); line-height:1.45;"></p>
          </div>
          <button type="button" id="lg-taxonomy-close-btn" class="btn-secondary btn-sm" aria-label="Close" style="padding:6px 10px; display:inline-flex; align-items:center; justify-content:center;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <form id="lg-taxonomy-form">
          <label for="lg-taxonomy-name-input" style="display:block; font-size:12.5px; font-weight:800; color:var(--frost-navy); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:7px;">
            ${isSkill ? "Skill Name" : "Capability Name"}
          </label>
          <input type="text" id="lg-taxonomy-name-input" class="liquid-glass-control" autocomplete="off"
                 style="width:100%; height:44px; padding:0 14px; font-size:14.5px; font-weight:600; color:var(--frost-navy); box-sizing:border-box;" />
          <div id="lg-taxonomy-error" style="display:none; margin-top:8px; font-size:12.5px; font-weight:700; color:#DC2626;"></div>
          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:18px;">
            <button type="button" id="lg-taxonomy-cancel-btn" class="btn-secondary" style="font-size:13.5px; font-weight:700; padding:9px 18px;">Cancel</button>
            <button type="submit" class="btn-metal" style="font-size:13.5px; font-weight:800; padding:9px 20px;">Save ${isSkill ? "Skill" : "Capability"}</button>
          </div>
        </form>
      `;

      overlay.appendChild(card);
      document.body.appendChild(overlay);

      const subEl = document.getElementById("lg-taxonomy-modal-sub");
      if (subEl) subEl.textContent = subtitleText;
      const inputEl = document.getElementById("lg-taxonomy-name-input");
      if (inputEl) {
        inputEl.placeholder = placeholderText;
        inputEl.focus();
      }

      const closeModal = () => {
        overlay.remove();
        document.removeEventListener("keydown", onEsc);
      };
      const onEsc = (e) => {
        if (e.key === "Escape") closeModal();
      };
      document.addEventListener("keydown", onEsc);

      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) closeModal();
      });
      document.getElementById("lg-taxonomy-close-btn")?.addEventListener("click", closeModal);
      document.getElementById("lg-taxonomy-cancel-btn")?.addEventListener("click", closeModal);

      document.getElementById("lg-taxonomy-form")?.addEventListener("submit", (e) => {
        e.preventDefault();
        const trimmed = (inputEl?.value || "").trim();
        const errEl = document.getElementById("lg-taxonomy-error");
        if (!trimmed) {
          if (errEl) {
            errEl.textContent = `Please enter a valid ${isSkill ? "skill" : "capability"} name.`;
            errEl.style.display = "block";
          }
          inputEl?.focus();
          return;
        }
        closeModal();
        if (isSkill) {
          window.StarAppBridge.dispatchAction("add_custom_skill", JSON.stringify({ name: trimmed, capability: currentCap }));
        } else {
          window.StarAppBridge.dispatchAction("add_custom_capability", JSON.stringify({ name: trimmed }));
        }
      });
    },

    // Prompt user to add a new custom capability
    promptAddCapability() {
      this.openTaxonomyQuickAdd("capability");
    },

    // Add custom skill
    addCustomSkill() {
      const input = document.getElementById("custom-skill-input");
      if (!input || !input.value.trim()) return;
      window.StarAppBridge.dispatchAction("add_custom_skill", input.value.trim());
      input.value = "";
    },

    // Prompt user to add a new custom skill under currently selected capability
    promptAddSkill() {
      this.openTaxonomyQuickAdd("skill");
    },

    // Debounced JSON prompt change handler
    onPromptChange(val) {
      if (this._promptTimer) clearTimeout(this._promptTimer);
      this._promptTimer = setTimeout(() => {
        window.StarAppBridge.dispatchAction("update_badge_prompt", val);
      }, 350);
    },

    // Format badge prompt editor JSON
    formatBadgePrompt() {
      const editor = document.getElementById("badge-prompt-editor");
      if (!editor) return;
      try {
        const parsed = JSON.parse(editor.value);
        editor.value = JSON.stringify(parsed, null, 2);
        window.StarAppBridge.dispatchAction("update_badge_prompt", editor.value);
      } catch (err) {
        window.StarAppBridge.dispatchAction("format_badge_prompt", "{}");
      }
    },

    // Collect all inputs and preview new badge
    collectAndPreviewBadge() {
      const payload = {
        code: document.getElementById("badge-code")?.value || "",
        title: document.getElementById("badge-title")?.value || "",
        category: document.getElementById("badge-category")?.value || "",
        description: document.getElementById("badge-desc")?.value || "",
        learning_outcomes: document.getElementById("badge-outcomes")?.value || "",
        learning_topics: document.getElementById("badge-topics")?.value || "",
        project_requirements: document.getElementById("badge-reqs")?.value || "",
        prompt_json: document.getElementById("badge-prompt-editor")?.value || ""
      };
      window.StarAppBridge.dispatchAction("preview_new_badge", JSON.stringify(payload));
    },

    // Format prompt in reviewer edit modal
    formatReviewedBadgePrompt() {
      const editor = document.getElementById("edit-badge-prompt");
      if (!editor) return;
      try {
        const parsed = JSON.parse(editor.value);
        editor.value = JSON.stringify(parsed, null, 2);
      } catch (err) {
        alert("Cannot format: Invalid JSON syntax (" + err.message + ")");
      }
    },

    // Submit reviewer badge edits
    submitReviewedBadgeEdit(badgeId) {
      const title = document.getElementById("edit-badge-title")?.value || "";
      const power = document.getElementById("edit-badge-power")?.value || "Tech";
      const capability = document.getElementById("edit-badge-cap")?.value || "Data & Machine";
      const skill = document.getElementById("edit-badge-skill")?.value || "Hardware";
      const description = document.getElementById("edit-badge-desc")?.value || "";
      const outcomesText = document.getElementById("edit-badge-outcomes")?.value || "";
      const practicePrompt = document.getElementById("edit-practice-prompt")?.value || "";
      const resourcesPrompt = document.getElementById("edit-resources-prompt")?.value || "";
      const notes = document.getElementById("edit-reviewer-notes")?.value || "";

      const outcomes = outcomesText.split("\n").map(s => s.trim()).filter(s => s.length > 0);
      const topics = [];
      for (let i = 0; i < 6; i++) {
        const tTitle = document.getElementById(`edit-topic-title-${i}`)?.value || `Module ${i+1}`;
        const tDesc = document.getElementById(`edit-topic-desc-${i}`)?.value || "";
        topics.push({ title: tTitle, description: tDesc, completed: false });
      }

      const promptObj = {
        title: title,
        description: description,
        power: power,
        capability: capability,
        skill: skill,
        outcomes: outcomes,
        learning_outcomes: outcomes,
        practice_project: {
          intro: "Want some hands-on practice? Use this prompt to generate a practice project.",
          prompt: practicePrompt,
          footnote: "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge."
        },
        practice_prompt: practicePrompt,
        learning_topics: topics,
        learning_resources: {
          intro: "Not sure where to start learning? Use this prompt to find free resources tailored to this badge.",
          prompt: resourcesPrompt,
          footnote: "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources."
        },
        resources_prompt: resourcesPrompt,
        notes: notes
      };

      const payload = {
        badge_id: badgeId,
        title: title,
        power: power,
        capability: capability,
        skill: skill,
        description: description,
        learning_outcomes: outcomes,
        learning_topics: topics,
        project_requirements: practicePrompt,
        practice_prompt: practicePrompt,
        resources_prompt: resourcesPrompt,
        notes: notes,
        prompt_json: JSON.stringify(promptObj),
        and_approve: false
      };
      window.StarAppBridge.dispatchAction("save_reviewed_badge", JSON.stringify(payload));
    },

    submitAndApproveBadge(badgeId) {
      const title = document.getElementById("edit-badge-title")?.value || "";
      const power = document.getElementById("edit-badge-power")?.value || "Tech";
      const capability = document.getElementById("edit-badge-cap")?.value || "Data & Machine";
      const skill = document.getElementById("edit-badge-skill")?.value || "Hardware";
      const description = document.getElementById("edit-badge-desc")?.value || "";
      const outcomesText = document.getElementById("edit-badge-outcomes")?.value || "";
      const practicePrompt = document.getElementById("edit-practice-prompt")?.value || "";
      const resourcesPrompt = document.getElementById("edit-resources-prompt")?.value || "";
      const notes = document.getElementById("edit-reviewer-notes")?.value || "";

      const outcomes = outcomesText.split("\n").map(s => s.trim()).filter(s => s.length > 0);
      const topics = [];
      for (let i = 0; i < 6; i++) {
        const tTitle = document.getElementById(`edit-topic-title-${i}`)?.value || `Module ${i+1}`;
        const tDesc = document.getElementById(`edit-topic-desc-${i}`)?.value || "";
        topics.push({ title: tTitle, description: tDesc, completed: false });
      }

      const promptObj = {
        title: title,
        description: description,
        power: power,
        capability: capability,
        skill: skill,
        outcomes: outcomes,
        learning_outcomes: outcomes,
        practice_project: {
          intro: "Want some hands-on practice? Use this prompt to generate a practice project.",
          prompt: practicePrompt,
          footnote: "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge."
        },
        practice_prompt: practicePrompt,
        learning_topics: topics,
        learning_resources: {
          intro: "Not sure where to start learning? Use this prompt to find free resources tailored to this badge.",
          prompt: resourcesPrompt,
          footnote: "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources."
        },
        resources_prompt: resourcesPrompt,
        notes: notes
      };

      const payload = {
        badge_id: badgeId,
        title: title,
        power: power,
        capability: capability,
        skill: skill,
        description: description,
        learning_outcomes: outcomes,
        learning_topics: topics,
        project_requirements: practicePrompt,
        practice_prompt: practicePrompt,
        resources_prompt: resourcesPrompt,
        notes: notes,
        prompt_json: JSON.stringify(promptObj),
        and_approve: true
      };
      window.StarAppBridge.dispatchAction("save_reviewed_badge", JSON.stringify(payload));
    },

    // ------------------------------------------------------------------------
    // CASCADING DROPDOWNS & GEMINI BADGE GENERATOR
    // ------------------------------------------------------------------------
    getCapabilitySkillsMap() {
      return {
        "Data & Machine": [
          "Hardware", "Software", "Network", "Cloud", "AI-OS",
          "Data Model", "Architecture", "Ingestion", "Curation", "Governance"
        ],
        "Reasoning": [
          "Descriptive", "Diagnostic", "Predictive", "Prescriptive"
        ],
        "Action": [
          "Agents", "Controls", "Signals", "Feedback"
        ],
        "Outcome": [
          "Intelligent Apps", "HITL", "HOTL"
        ],
        "Trust": [
          "Security", "Drift", "Audit", "Reliability"
        ]
      };
    },

    onPowerSelect(power) {
      const crumbPower = document.getElementById("cb-crumb-power");
      if (crumbPower) crumbPower.textContent = power;
      window.StarAppBridge.dispatchAction("change_badge_power", power);
    },

    onCapabilitySelect(capability) {
      const capSelect = document.getElementById("badge-capability-select");
      if (capability === "__add_custom_capability__") {
        if (capSelect) {
          capSelect.value = capSelect.dataset.currentCap || "Data & Machine";
        }
        this.openTaxonomyQuickAdd("capability");
        return;
      }
      if (capSelect) {
        capSelect.dataset.currentCap = capability;
      }
      const crumbCap = document.getElementById("cb-crumb-cap");
      if (crumbCap) crumbCap.textContent = capability;

      const skillsMap = this.getCapabilitySkillsMap();
      const mappedSkills = skillsMap[capability];
      const skillSelect = document.getElementById("badge-skill-select");
      if (skillSelect && Array.isArray(mappedSkills) && mappedSkills.length > 0) {
        skillSelect.innerHTML = "";
        mappedSkills.forEach((s) => {
          const opt = document.createElement("option");
          opt.value = s;
          opt.textContent = s;
          skillSelect.appendChild(opt);
        });
        const addOpt = document.createElement("option");
        addOpt.value = "__add_custom_skill__";
        addOpt.textContent = "+ Add New Skill...";
        skillSelect.appendChild(addOpt);
        skillSelect.dataset.currentSkill = mappedSkills[0];
        const crumbSkill = document.getElementById("cb-crumb-skill");
        if (crumbSkill) crumbSkill.textContent = mappedSkills[0];
      }
      window.StarAppBridge.dispatchAction("change_badge_capability", capability);
      if (Array.isArray(mappedSkills) && mappedSkills.length > 0) {
        window.StarAppBridge.dispatchAction("change_badge_skill", mappedSkills[0]);
      }
    },

    onSkillSelect(skill) {
      const skillSelect = document.getElementById("badge-skill-select");
      if (skill === "__add_custom_skill__") {
        if (skillSelect) {
          skillSelect.value = skillSelect.dataset.currentSkill || "";
        }
        this.openTaxonomyQuickAdd("skill");
        return;
      }
      if (skillSelect) {
        skillSelect.dataset.currentSkill = skill;
      }
      const crumbSkill = document.getElementById("cb-crumb-skill");
      if (crumbSkill) crumbSkill.textContent = skill;
      window.StarAppBridge.dispatchAction("change_badge_skill", skill);
    },

    async triggerCreateBadgeGemini() {
      const powerEl = document.getElementById("badge-power-select");
      const capEl = document.getElementById("badge-capability-select");
      const skillEl = document.getElementById("badge-skill-select");
      const outcomeEl = document.getElementById("badge-outcome-sentence-input");
      const btn = document.getElementById("create-badge-gemini-btn");
      const spinner = document.getElementById("gemini-loading-indicator");

      const power = powerEl?.value || "Tech";
      const capability = capEl?.value || "Data & Machine";
      const skill = skillEl?.value || "Hardware";
      const outcomeSentence = outcomeEl?.value?.trim() || "";

      const bandEl = document.getElementById("current-badge-band");
      let band = (bandEl && bandEl.value) ? bandEl.value.trim() : "";
      if (!band) {
        band = sessionStorage.getItem("starapp_active_band") || "";
      }
      if (!band && window.starAppController && window.starAppController.create_badge_band) {
        band = window.starAppController.create_badge_band;
      }
      if (!band) band = "B1";

      if (btn) {
        btn.disabled = true;
        btn.style.opacity = "0.6";
        btn.style.cursor = "not-allowed";
      }
      if (spinner) spinner.style.display = "flex";

      // Animated progress steps
      const loadingSteps = [
        `✦ Analysing ${skill} under ${capability}…`,
        `✦ Crafting learning outcomes…`,
        `✦ Building practice project prompt…`,
        `✦ Generating learning topics…`,
        `✦ Writing learning resources prompt…`,
        `✦ Finalising badge structure…`
      ];
      let stepIdx = 0;
      const loadingTextEl = document.getElementById("gemini-loading-text");
      const stepInterval = setInterval(() => {
        if (loadingTextEl && stepIdx < loadingSteps.length) {
          loadingTextEl.textContent = loadingSteps[stepIdx++];
        }
      }, 900);

      const apiKey = (window.__STARAPP_CONFIG__ && window.__STARAPP_CONFIG__.GEMINI_API_KEY)
        || localStorage.getItem("starapp_gemini_api_key")
        || localStorage.getItem("GEMINI_API_KEY")
        || (window.atob ? window.atob("QVEuQWI4Uk42TFJMWVJpcm9JSjRPRm5DdGd3UjZySzNNVlo3V2JZekdZU0l5S0Vqci10VVE=") : "");

      const promptInstruction = `You are an expert curriculum architect for engineering badges.
Create a detailed, high-quality badge for:
- Band: ${band}
- Power: ${power}
- Capability: ${capability}
- Skill: ${skill}
- Outcome Sentence: "${outcomeSentence}"

Return ONLY valid JSON matching this exact schema:
{
  "title": "${skill} Foundations",
  "description": "Foundational badge covering core ${skill.toLowerCase()} concepts...",
  "outcomes": [
    "Can identify ...",
    "Can analyze ...",
    "Can design ...",
    "Can implement ..."
  ],
  "learning_topics": [
    {"title": "Topic 1", "description": "..."},
    {"title": "Topic 2", "description": "..."},
    {"title": "Topic 3", "description": "..."},
    {"title": "Topic 4", "description": "..."},
    {"title": "Topic 5", "description": "..."},
    {"title": "Topic 6", "description": "..."}
  ],
  "practice_prompt": "I'm working toward the \\"${skill} Foundations\\" badge (${skill} / ${capability} / ${power})...",
  "resources_prompt": "I'm working toward the \\"${skill} Foundations\\" badge (${skill} / ${capability} / ${power})..."
}`;

      let parsedBadge = null;

      // Prefer secure Backend Gemini Proxy
      if (window.StarAppAPI && window.StarAppAPI.gemini) {
        try {
          const apiRes = await window.StarAppAPI.gemini.generateBadge(band, power, capability, skill, outcomeSentence);
          if (apiRes && apiRes.badge) {
            const rawObj = apiRes.badge;
            const locationStr = `${rawObj.title} -> ${skill} -> ${capability} -> ${power} -> Band ${band}`;
            const formattedOutcomes = (rawObj.outcomes || []).map(o => {
              let s = String(o).trim();
              if (!s.startsWith("Can ")) {
                s = "Can " + s.charAt(0).toLowerCase() + s.slice(1);
              }
              if (!s.endsWith(".")) s += ".";
              return s;
            });

            const outcomesList = formattedOutcomes.length > 0 ? formattedOutcomes : [outcomeSentence];

            const topics = (rawObj.learning_topics || []).map((t, idx) => ({
              title: t.title || `Topic ${idx + 1}`,
              description: t.description || "",
              status: t.status || "In Progress",
              completed: !!t.completed
            }));

            const topicsBullets = topics.map(t => `- ${t.title}: ${t.description}`).join("\n");
            const outcomesSemicolon = outcomesList.join("; ");

            const defaultPracticePrompt = `I'm working toward the "${rawObj.title}" badge (${skill} / ${capability} / ${power}) in Band ${band}.\nI want to practice the following topics for this badge:\n${topicsBullets}\n\nBy the end I need to be able to: ${outcomesSemicolon}\n\nDesign one small, hands-on practice project that lets me demonstrate all of the topics and outcomes above together. Include a clear task description, any starting constraints or inputs I should assume, and what a finished/successful result looks like.`;

            const defaultResourcesPrompt = `I'm working toward the "${rawObj.title}" badge (${skill} / ${capability} / ${power}) in Band ${band}.\nI need free, current, high-quality learning resources (official docs, free courses, tutorials, videos) that help me learn:\n${topicsBullets}\n\nBy the end I need to be able to: ${outcomesSemicolon}\n\nPlease suggest specific free resources for each topic above (prefer official docs, free interactive tutorials, and reputable free video/blog content over paid courses), and suggest one small hands-on project that lets me demonstrate all of the topics together.`;

            const practicePrompt = (rawObj.practice_project && rawObj.practice_project.prompt)
              || rawObj.practice_prompt
              || defaultPracticePrompt;

            const resourcesPrompt = (rawObj.learning_resources && rawObj.learning_resources.prompt)
              || rawObj.resources_prompt
              || defaultResourcesPrompt;

            parsedBadge = {
              id: `badge_${band.toLowerCase()}_${skill.toLowerCase().replace(/[^a-z0-9]/g, "_")}`,
              code: `${band}-${skill.substring(0,3).toUpperCase()}-01`,
              title: rawObj.title,
              description: rawObj.description || `Foundational badge covering core ${skill.toLowerCase()} concepts.`,
              target_band: band,
              power: power,
              capability: capability,
              skill: skill,
              location: locationStr,
              outcomes: outcomesList,
              learning_topics: topics,
              practice_prompt: practicePrompt,
              resources_prompt: resourcesPrompt,
              practice_project: {
                intro: (rawObj.practice_project && rawObj.practice_project.intro) || "Want some hands-on practice? Use this prompt to generate a practice project.",
                prompt: practicePrompt,
                footnote: (rawObj.practice_project && rawObj.practice_project.footnote) || "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge."
              },
              learning_resources: {
                intro: (rawObj.learning_resources && rawObj.learning_resources.intro) || "Not sure where to start learning? Use this prompt to find free resources tailored to this badge.",
                prompt: resourcesPrompt,
                footnote: (rawObj.learning_resources && rawObj.learning_resources.footnote) || "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources."
              },
              earn_badge_status: "Pending Review",
              earn_badge_text: "Great job submitting your project — your guardian is reviewing it now.",
              related: {
                skill: skill,
                capability: capability,
                power: power
              }
            };
          }
        } catch (e) {
          console.warn("[StarApp] Backend Gemini API call failed, falling back to deterministic generation:", e);
        }
      }

      // Fallback if not generated
      if (!parsedBadge) {
        parsedBadge = this.generateDeterministicBadgeData(band, power, capability, skill, outcomeSentence);
      }

      clearInterval(stepInterval);
      if (btn) {
        btn.disabled = false;
        btn.style.opacity = "";
        btn.style.cursor = "";
      }
      if (spinner) spinner.style.display = "none";
      if (loadingTextEl) loadingTextEl.textContent = "Generating badge with Gemini AI...";

      if (parsedBadge) {
        window.StarAppBridge._lastGeneratedBadge = parsedBadge;
        try {
          sessionStorage.setItem("starapp_last_generated_badge", JSON.stringify(parsedBadge));
        } catch (e) {}
      }

      window.StarAppBridge.dispatchAction("on_badge_generated", JSON.stringify({
        band,
        power,
        capability,
        skill,
        outcome_sentence: outcomeSentence,
        badge_data: parsedBadge
      }));
    },

    generateDeterministicBadgeData(band, power, capability, skill, outcomeSentence) {
      const suffix = (band === "B1" || band === "B2") ? "Foundations" : ((band === "B3" || band === "B4") ? "Architecture" : "Mastery");
      const title = `${skill} ${suffix}`;
      const location = `${title} -> ${skill} -> ${capability} -> ${power} -> Band ${band}`;
      let outcome = outcomeSentence?.trim() || `Identify core ${skill.toLowerCase()} components and evaluate their primary system roles`;
      if (!outcome.startsWith("Can ")) {
        outcome = "Can " + outcome.charAt(0).toLowerCase() + outcome.slice(1);
      }
      if (!outcome.endsWith(".")) outcome += ".";

      const outcomes = [
        outcome,
        `Can explain how ${skill.toLowerCase()} architectures impact performance, throughput, and operational resilience.`,
        `Can analyze and select appropriate ${skill.toLowerCase()} specifications for diverse engineering workloads in Band ${band}.`,
        `Can implement automated telemetry and quality verification for ${skill.toLowerCase()} components.`
      ];

      const topics = [
        { title: `${skill} architecture & fundamentals`, status: "In Progress", completed: false, description: `Understanding core ${skill.toLowerCase()} primitives, execution layers, and operational boundaries.` },
        { title: `${skill} interface contracts & modeling`, status: "In Progress", completed: false, description: `Designing robust ${skill.toLowerCase()} interfaces, data formats, and error handling protocols.` },
        { title: `${skill} subsystem integration`, status: "In Progress", completed: false, description: `Integrating ${skill.toLowerCase()} components across distributed cloud and on-premise infrastructure.` },
        { title: `${skill} telemetry & health monitoring`, status: "In Progress", completed: false, description: `Monitoring latency, throughput benchmarks, and resource utilization for ${skill.toLowerCase()}.` },
        { title: `${skill} optimization & failure modes`, status: "In Progress", completed: false, description: `Identifying performance bottlenecks, thermal/memory limits, and recovery strategies for ${skill.toLowerCase()}.` },
        { title: `${skill} governance & best practices`, status: "In Progress", completed: false, description: `Enforcing operational governance, security controls, and verification standards for ${skill.toLowerCase()}.` }
      ];

      const topicsBullets = topics.map(t => `- ${t.title}: ${t.description}`).join("\n");
      const outcomesSemicolon = outcomes.join("; ");

      const practicePrompt = `I'm working toward the "${title}" badge (${skill} / ${capability} / ${power}) in Band ${band}.\nI want to practice the following topics for this badge:\n${topicsBullets}\n\nBy the end I need to be able to: ${outcomesSemicolon}\n\nDesign one small, hands-on practice project that lets me demonstrate all of the topics and outcomes above together. Include a clear task description, any starting constraints or inputs I should assume, and what a finished/successful result looks like.`;

      const resourcesPrompt = `I'm working toward the "${title}" badge (${skill} / ${capability} / ${power}) in Band ${band}.\nI need free, current, high-quality learning resources (official docs, free courses, tutorials, videos) that help me learn:\n${topicsBullets}\n\nBy the end I need to be able to: ${outcomesSemicolon}\n\nPlease suggest specific free resources for each topic above (prefer official docs, free interactive tutorials, and reputable free video/blog content over paid courses), and suggest one small hands-on project that lets me demonstrate all of the topics together.`;

      return {
        id: `badge_${band.toLowerCase()}_${skill.toLowerCase().replace(/[^a-z0-9]/g, "_")}`,
        code: `${band}-${skill.substring(0,3).toUpperCase()}-01`,
        title: title,
        description: `${band} badge specializing in ${skill} under the ${capability} capability (${power} domain). ${outcomeSentence || ""}`.trim(),
        target_band: band,
        power: power,
        capability: capability,
        skill: skill,
        location: location,
        outcomes: outcomes,
        earn_badge_status: "Pending Review",
        earn_badge_text: "Great job submitting your project — your guardian is reviewing it now.",
        practice_prompt: practicePrompt,
        resources_prompt: resourcesPrompt,
        practice_project: {
          intro: "Want some hands-on practice? Use this prompt to generate a practice project.",
          prompt: practicePrompt,
          footnote: "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge."
        },
        learning_topics: topics,
        learning_resources: {
          intro: "Not sure where to start learning? Use this prompt to find free resources tailored to this badge.",
          prompt: resourcesPrompt,
          footnote: "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources."
        },
        related: {
          skill: skill,
          capability: capability,
          power: power
        }
      };
    },

    promptSetApiKey() {
      const current = localStorage.getItem("starapp_gemini_api_key") || "";
      const masked = current ? current.substring(0, 6) + "..." + current.substring(current.length - 4) : "(none)";
      const input = window.prompt(`Enter your Gemini API key (current: ${masked}). Leave blank to use instant offline generator:`, current);
      if (input !== null) {
        if (input.trim()) {
          localStorage.setItem("starapp_gemini_api_key", input.trim());
          alert("Gemini API key saved in browser storage.");
        } else {
          localStorage.removeItem("starapp_gemini_api_key");
          alert("Gemini API key cleared. StarApp will use instant offline template generator.");
        }
      }
    },

    _setSectionChevronState(chevron, isOpen) {
      if (!chevron) return;
      const svg = chevron.querySelector("svg");
      if (svg) {
        svg.style.transform = isOpen ? "rotate(0deg)" : "rotate(180deg)";
        chevron.dataset.open = isOpen ? "1" : "0";
      } else {
        chevron.textContent = isOpen ? "Open" : "Closed";
      }
    },

    toggleBadgeSection(sectionId) {
      const content = document.getElementById(`content-${sectionId}`);
      const chevron = document.getElementById(`chevron-${sectionId}`);
      if (!content) return;
      const isClosed = content.style.display === "none";
      content.style.display = isClosed ? "block" : "none";
      this._setSectionChevronState(chevron, isClosed);
      if (isClosed) {
        requestAnimationFrame(() => this.autoResizeTextareas(content));
      }
    },

    toggleAllBadgeSections() {
      const sections = ["outcomes", "allocated-project", "practice", "topics", "resources", "related"];
      let anyOpen = false;
      for (const s of sections) {
        const c = document.getElementById(`content-${s}`);
        if (c && c.style.display !== "none") {
          anyOpen = true;
          break;
        }
      }
      const nextOpen = !anyOpen;
      for (const s of sections) {
        const c = document.getElementById(`content-${s}`);
        const ch = document.getElementById(`chevron-${s}`);
        if (c) {
          c.style.display = nextOpen ? "block" : "none";
        }
        this._setSectionChevronState(ch, nextOpen);
      }
      if (nextOpen) {
        requestAnimationFrame(() => this.autoResizeTextareas(document));
      }
    },

    toggleCosmonautBadgeCard(badgeId) {
      this.dispatchAction("toggle_cosmonaut_badge_card", badgeId);
    },

    async copyTextFromElement(elementId, btnElement) {
      const el = document.getElementById(elementId);
      if (!el) return;
      const textToCopy = (el.innerText || el.textContent || "").trim();
      const copiedHtml = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Copied';
      try {
        await navigator.clipboard.writeText(textToCopy);
        const originalHtml = btnElement.innerHTML;
        btnElement.innerHTML = copiedHtml;
        btnElement.style.background = "#059669";
        btnElement.style.color = "#FFFFFF";
        setTimeout(() => {
          btnElement.innerHTML = originalHtml;
          btnElement.style.background = "";
          btnElement.style.color = "";
        }, 2000);
      } catch (err) {
        const ta = document.createElement("textarea");
        ta.value = textToCopy;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        const originalHtml = btnElement.innerHTML;
        btnElement.innerHTML = copiedHtml;
        setTimeout(() => { btnElement.innerHTML = originalHtml; }, 2000);
      }
    },

    toggleEditBadge() {
      const isEditingNow = !!document.getElementById("edit-badge-title-input")
        || !!(window.starAppController && window.starAppController.is_editing_badge);
      if (isEditingNow) {
        this.saveBadgeEdits();
      } else {
        window.StarAppBridge.dispatchAction("toggle_edit_badge");
      }
    },

    saveBadgeEdits() {
      const title = document.getElementById("edit-badge-title-input")?.value;
      const desc = document.getElementById("edit-badge-desc-input")?.value;
      const outcomes = document.getElementById("edit-badge-outcomes-input")?.value;
      const practicePrompt = document.getElementById("edit-practice-prompt-input")?.value;
      const resourcesPrompt = document.getElementById("edit-resources-prompt-input")?.value;

      const topics = [];
      for (let i = 0; i < 20; i++) {
        const titleEl = document.getElementById(`edit-topic-title-${i}`);
        const descEl = document.getElementById(`edit-topic-desc-${i}`);
        if (!titleEl && !descEl) break;
        const existingTopic = window.starAppController?.created_badge_data?.learning_topics?.[i];
        const dsCompleted = titleEl?.dataset?.completed;
        const dsStatus = titleEl?.dataset?.status;
        const completed = dsCompleted !== undefined
          ? dsCompleted === "1"
          : (existingTopic ? (existingTopic.completed ?? (existingTopic.status === "Completed")) : false);
        const status = dsStatus || (completed ? "Completed" : (existingTopic?.status || "In Progress"));
        topics.push({
          title: titleEl?.value?.trim() || `Topic ${i+1}`,
          description: descEl?.value?.trim() || "",
          status: status,
          completed: completed
        });
      }

      const payload = {
        title: title || "",
        description: desc || "",
        outcomes: outcomes ? outcomes.split("\n").filter(o => o.trim()) : [],
        practice_prompt: practicePrompt || "",
        resources_prompt: resourcesPrompt || "",
        topics: topics.length > 0 ? topics : undefined
      };
      window.StarAppBridge.dispatchAction("save_badge_edits", JSON.stringify(payload));
    },

    toggleTopicCompletion(idx) {
      const cardEl = document.getElementById(`topic-card-${idx}`);
      const btnEl = document.getElementById(`topic-toggle-btn-${idx}`);
      const tagEl = document.getElementById(`topic-status-tag-${idx}`);
      if (!btnEl) return;

      const isCompleted = btnEl.classList.contains("is-completed");
      const nextCompleted = !isCompleted;

      if (nextCompleted) {
        btnEl.classList.add("is-completed");
        btnEl.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Completed`;
        btnEl.style.background = "#10B981";
        btnEl.style.color = "white";
        btnEl.style.borderColor = "#059669";
        btnEl.style.boxShadow = "0 2px 10px rgba(16,185,129,0.35)";

        if (tagEl) {
          tagEl.textContent = "Completed";
          tagEl.style.background = "rgba(16,185,129,0.15)";
          tagEl.style.color = "#10B981";
          tagEl.style.borderColor = "rgba(16,185,129,0.3)";
        }
        if (cardEl) {
          cardEl.style.borderColor = "#10B981";
          cardEl.style.background = "linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(236,253,245,0.7) 100%)";
          cardEl.classList.remove("animate-green-pulse");
          void cardEl.offsetWidth; // trigger reflow for animation restart
          cardEl.classList.add("animate-green-pulse");
        }
      } else {
        btnEl.classList.remove("is-completed");
        btnEl.innerHTML = `Mark Complete`;
        btnEl.style.background = "rgba(255,255,255,0.9)";
        btnEl.style.color = "var(--frost-navy-75)";
        btnEl.style.borderColor = "var(--icy-steel)";
        btnEl.style.boxShadow = "none";

        if (tagEl) {
          tagEl.textContent = "In Progress";
          tagEl.style.background = "rgba(157,183,213,0.18)";
          tagEl.style.color = "var(--frost-navy-50)";
          tagEl.style.borderColor = "rgba(157,183,213,0.3)";
        }
        if (cardEl) {
          cardEl.style.borderColor = "rgba(6,182,212,0.3)";
          cardEl.style.background = "linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(234,244,255,0.85) 100%)";
          cardEl.classList.remove("animate-green-pulse");
        }
      }

      // Sync state to window.starAppController.created_badge_data if present
      if (window.starAppController && window.starAppController.created_badge_data) {
        const topics = window.starAppController.created_badge_data.learning_topics;
        if (topics && topics[idx]) {
          topics[idx].completed = nextCompleted;
          topics[idx].status = nextCompleted ? "Completed" : "In Progress";
        }
      }

      // Update progress bar & percentage text & summary pill
      const allBtns = document.querySelectorAll('[id^="topic-toggle-btn-"]');
      const total = allBtns.length;
      const completedCount = document.querySelectorAll('[id^="topic-toggle-btn-"].is-completed').length;
      const pct = total > 0 ? Math.round((completedCount / total) * 100) : 0;

      const bar = document.getElementById("topics-progress-bar");
      if (bar) bar.style.width = pct + "%";

      const txt = document.getElementById("topics-progress-text");
      if (txt) txt.textContent = pct + "%";

      const pill = document.getElementById("topics-summary-pill");
      if (pill) {
        pill.textContent = completedCount === total ? "Completed" : `${completedCount}/${total} Completed`;
        if (completedCount === total) {
          pill.style.background = "rgba(16,185,129,0.2)";
          pill.style.color = "#10B981";
          pill.style.borderColor = "rgba(16,185,129,0.35)";
        } else if (completedCount > 0) {
          pill.style.background = "rgba(6,182,212,0.15)";
          pill.style.color = "#0891B2";
          pill.style.borderColor = "rgba(6,182,212,0.3)";
        } else {
          pill.style.background = "rgba(157,183,213,0.18)";
          pill.style.color = "var(--frost-navy-50)";
          pill.style.borderColor = "rgba(157,183,213,0.3)";
        }
      }

      // Also notify Python controller in background for full state parity
      window.StarAppBridge.dispatchAction("toggle_topic_completion", JSON.stringify({ index: idx, completed: nextCompleted }));
    },

    saveGeneratedBadge() {
      const titleInput = document.getElementById("edit-badge-title-input");
      const descInput = document.getElementById("edit-badge-desc-input");
      const outcomesInput = document.getElementById("edit-badge-outcomes-input");
      const practicePromptInput = document.getElementById("edit-practice-prompt-input");
      const resourcesPromptInput = document.getElementById("edit-resources-prompt-input");

      const bandEl = document.getElementById("current-badge-band");
      const bandRaw = bandEl ? (bandEl.value || bandEl.textContent || "") : "";
      const activeBand = (bandRaw.replace(/[^0-9A-Za-z]/g, "")) || sessionStorage.getItem("starapp_active_band") || "B1";

      const payload = { band: activeBand };

      if (titleInput || descInput) {
        const topics = [];
        for (let i = 0; i < 20; i++) {
          const titleEl = document.getElementById(`edit-topic-title-${i}`);
          const descEl = document.getElementById(`edit-topic-desc-${i}`);
          if (!titleEl && !descEl) break;
          topics.push({
            title: titleEl?.value?.trim() || `Topic ${i+1}`,
            description: descEl?.value?.trim() || "",
            status: "In Progress",
            completed: false
          });
        }
        payload.title = titleInput ? titleInput.value.trim() : "";
        payload.description = descInput ? descInput.value.trim() : "";
        payload.outcomes = outcomesInput ? outcomesInput.value.split("\n").filter(o => o.trim()) : [];
        payload.practice_prompt = practicePromptInput ? practicePromptInput.value.trim() : "";
        payload.resources_prompt = resourcesPromptInput ? resourcesPromptInput.value.trim() : "";
        if (topics.length > 0) payload.topics = topics;
      }

      if (window.StarAppBridge._lastGeneratedBadge) {
        payload.badge_data = window.StarAppBridge._lastGeneratedBadge;
      } else {
        try {
          const cached = sessionStorage.getItem("starapp_last_generated_badge");
          if (cached) payload.badge_data = JSON.parse(cached);
        } catch (e) {}
      }

      window.StarAppBridge.dispatchAction("save_generated_badge", JSON.stringify(payload));
    },

    // Read-only telemetry accessor for regression verification
    _getRenderState() {
      return renderState;
    },

    getWindowSessionId() {
      let sid = sessionStorage.getItem("starapp_window_session_id");
      if (!sid) {
        const urlParams = new URLSearchParams(window.location.search);
        const role = urlParams.get("role") || "";
        sid = (role ? role + "_" : "win_") + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
        sessionStorage.setItem("starapp_window_session_id", sid);
      }
      return sid;
    },

    // Go back to previous view in history stack
    goBack() {
      this.dispatchAction("go_back", "{}");
    },

    // Dispatch UI click/action event to Python controller (Native FastAPI Backend or in-browser Pyodide)
    dispatchAction(action, payloadJson = "{}") {
      localActionSeq += 1;
      pendingDeferredReload = false;

      // Track active band in tab session storage
      if (action === "select_create_badge_band") {
        const b = typeof payloadJson === "string" ? payloadJson.replace(/[{"}:]/g, "") : (payloadJson?.band || "");
        if (b) sessionStorage.setItem("starapp_active_band", b.trim());
      } else if (action === "go_back") {
        const bandEl = document.getElementById("current-badge-band");
        if (bandEl) sessionStorage.removeItem("starapp_active_band");
      }

      if (window.starAppController && typeof window.starAppController.handle_event === "function") {
        window.starAppController.handle_event(action, payloadJson);
      } else {
        // Native FastAPI Full-Stack Backend dispatch with tab-isolated session ID
        const sid = this.getWindowSessionId();
        const payloadStr = typeof payloadJson === "string" ? payloadJson : JSON.stringify(payloadJson);
        fetch("/api/v1/dispatch", {
          method: "POST",
          cache: "no-store",
          headers: {
            "Content-Type": "application/json",
            "X-Session-Id": sid
          },
          body: JSON.stringify({ action: action, payload: payloadStr, session_id: sid })
        })
        .then(res => res.json())
        .then(data => {
          if (data && data.session_state) {
            try {
              if (action === "logout" || !data.session_state.user_id) {
                sessionStorage.removeItem("starapp_fastapi_session");
              } else {
                sessionStorage.setItem("starapp_fastapi_session", JSON.stringify(data.session_state));
              }
            } catch (e) {}
          }
          if (data && data.regions) {
            window.StarAppBridge.updateRegions(JSON.stringify(data.regions));
          } else if (data && data.full_html) {
            window.StarAppBridge.updateAppRoot(data.full_html);
          }
        })
        .catch(err => {
          console.error("[StarAppBridge] FastAPI backend dispatch error:", err);
        });
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

    // Structural signature of the sidebar markup that IGNORES which link is active. The server renders the
    // "active" class into the HTML, so comparing raw strings made every navigation look like a sidebar
    // change and the whole <aside> was rebuilt (hover/scroll state lost, visible flicker) even though
    // _updateSidebarInPlace already knows how to move the highlight. Now only a REAL structural change
    // (different links, badge counts, user, cycle pill) replaces the element.
    _sidebarSignature(html) {
      return String(html || "").replace(/class="nav-link active"/g, 'class="nav-link"');
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
        renderState.sidebarHtml = "";
        renderState.topbarHtml = "";
        renderState.pageContainerClass = "";
        renderState.flashHtml = "";
        renderState.mainHtml = payload.mainContentHtml;
        renderState.modalKind = "";
        renderState.modalKey = "";
        renderState.modalHtml = "";
        return;
      }

      // Mode 2: Authenticated Workspace with persistent top-right Back strip
      const existingSidebar = document.getElementById("starapp-shell-sidebar");
      const existingViewport = document.getElementById("starapp-main-viewport");
      const existingTopbarSlot = document.getElementById("starapp-topbar-slot");
      const existingPageSlot = document.getElementById("starapp-page-slot");
      const existingFlashSlot = document.getElementById("starapp-flash-slot");
      const existingPageBody = document.getElementById("starapp-page-body");
      const existingModalRoot = document.getElementById("starapp-modal-root");

      const canPatchRegions = Boolean(
        existingSidebar &&
        existingViewport &&
        existingTopbarSlot &&
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
            `<div id="starapp-topbar-slot">${payload.topbarHtml || ""}</div>` +
            `<main id="starapp-page-slot" class="${payload.pageContainerClass}">` +
              `<div id="starapp-flash-slot">${payload.flashHtml || ""}</div>` +
              `<div id="starapp-page-body">${payload.mainContentHtml}</div>` +
            `</main>` +
          `</div>` +
          `<div id="starapp-modal-root">${payload.modalHtml || ""}</div>`;

        renderState.mode = "workspace";
        renderState.portalKey = payload.portalKey;
        renderState.routeKey = payload.routeKey;
        renderState.sidebarHtml = this._sidebarSignature(payload.sidebarHtml);
        renderState.topbarHtml = payload.topbarHtml || "";
        renderState.pageContainerClass = payload.pageContainerClass;
        renderState.flashHtml = payload.flashHtml || "";
        renderState.mainHtml = payload.mainContentHtml;
        renderState.modalKind = payload.activeModal || "";
        renderState.modalKey = payload.modalKey || "";
        renderState.modalHtml = payload.modalHtml || "";
        this.applyPersistedSidebarState();
        this.initCycleWidgets();
        return;
      }

      // Region 1: Persistent Sidebar (update active link + badge counts in place, or replace when sidebarHtml changes)
      const nextSidebarSig = this._sidebarSignature(payload.sidebarHtml);
      if (payload.sidebarHtml && renderState.sidebarHtml !== nextSidebarSig) {
        existingSidebar.outerHTML = payload.sidebarHtml;
        renderState.sidebarHtml = nextSidebarSig;
        const newSidebar = document.getElementById("starapp-shell-sidebar");
        this._updateSidebarInPlace(newSidebar, payload.activeNavId, payload.sidebarBadges);
        this.applyPersistedSidebarState();
      } else {
        this._updateSidebarInPlace(existingSidebar, payload.activeNavId, payload.sidebarBadges);
        this.applyPersistedSidebarState();
        renderState.regionSkipCounts.sidebarSkipped += 1;
      }

      // Region 1b: Universal top-right Back strip
      const nextTopbar = payload.topbarHtml || "";
      if (renderState.topbarHtml !== nextTopbar) {
        existingTopbarSlot.innerHTML = nextTopbar;
        renderState.topbarHtml = nextTopbar;
      }

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
            this.initCycleWidgets();
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
      this.initCycleWidgets();
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
      this.initCycleWidgets();
    },

    // =========================================================================
    // PERFORMANCE CYCLE SWITCHER & LIQUID-GLASS DATE RANGE CALENDAR
    // =========================================================================
    _cycleCalState: {
      target: "start",
      viewYear: 2026,
      viewMonth: 0,
      startIso: "",
      endIso: ""
    },

    filterCycleCards(statusFilter, btnEl) {
      const grid = document.getElementById("cycle-switcher-grid");
      if (!grid) return;
      grid.querySelectorAll(".cycle-item[data-cycle-status]").forEach((card) => {
        const st = (card.getAttribute("data-cycle-status") || "").toLowerCase();
        const show =
          statusFilter === "all" ||
          (statusFilter === "active" && (st === "active" || st === "evaluating")) ||
          (statusFilter === "closed" && st === "closed");
        card.style.display = show ? "" : "none";
      });
      if (btnEl && btnEl.parentElement) {
        btnEl.parentElement.querySelectorAll(".cycle-tab-btn").forEach((b) => {
          b.classList.toggle("is-active", b === btnEl);
        });
      }
    },

    _parseIsoDate(iso) {
      if (!iso || typeof iso !== "string") return null;
      const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.trim().slice(0, 10));
      if (!m) return null;
      const y = Number(m[1]), mo = Number(m[2]) - 1, d = Number(m[3]);
      const dt = new Date(y, mo, d);
      if (dt.getFullYear() !== y || dt.getMonth() !== mo || dt.getDate() !== d) return null;
      return dt;
    },

    _formatIsoDate(dt) {
      const y = dt.getFullYear();
      const m = String(dt.getMonth() + 1).padStart(2, "0");
      const d = String(dt.getDate()).padStart(2, "0");
      return `${y}-${m}-${d}`;
    },

    _formatPrettyDate(iso) {
      const dt = this._parseIsoDate(iso);
      if (!dt) return iso || "Select date";
      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const dd = String(dt.getDate()).padStart(2, "0");
      return `${months[dt.getMonth()]} ${dd}, ${dt.getFullYear()}`;
    },

    _addSixMonthsMinusOne(iso) {
      const dt = this._parseIsoDate(iso);
      if (!dt) return iso;
      const targetMonth = dt.getMonth() + 6;
      const targetYear = dt.getFullYear() + Math.floor(targetMonth / 12);
      const normalizedMonth = targetMonth % 12;
      const daysInTargetMonth = new Date(targetYear, normalizedMonth + 1, 0).getDate();
      const clampedDay = Math.min(dt.getDate(), daysInTargetMonth);
      const next = new Date(targetYear, normalizedMonth, clampedDay);
      next.setDate(next.getDate() - 1);
      return this._formatIsoDate(next);
    },

    autoResizeTextarea(el) {
      if (!el || el.tagName !== "TEXTAREA") return;
      el.style.resize = "none";
      el.style.overflow = "hidden";
      el.style.height = "auto";
      const minH = parseFloat(el.dataset.minHeight || el.style.minHeight || "0") || 0;
      if (el.scrollHeight > 0) {
        el.style.height = Math.max(minH, el.scrollHeight + 2) + "px";
      } else {
        const rows = parseInt(el.getAttribute("rows") || "2", 10) || 2;
        el.style.height = Math.max(minH, rows * 24 + 20) + "px";
      }
    },

    autoResizeTextareas(root = document) {
      if (!root || typeof root.querySelectorAll !== "function") return;
      root.querySelectorAll("textarea").forEach((ta) => {
        this.autoResizeTextarea(ta);
      });
    },

    initAutoGrowTextareas() {
      if (typeof document !== "undefined" && document.documentElement && !document.documentElement.dataset.autoGrowBound) {
        document.documentElement.dataset.autoGrowBound = "1";
        document.addEventListener("input", (e) => {
          if (e.target && e.target.tagName === "TEXTAREA") {
            this.autoResizeTextarea(e.target);
          }
        });
        if (typeof window !== "undefined") {
          window.addEventListener("resize", () => this.autoResizeTextareas(document));
        }
      }
      this.autoResizeTextareas(document);
      if (typeof requestAnimationFrame === "function") {
        requestAnimationFrame(() => this.autoResizeTextareas(document));
      }
    },

    initCycleWidgets() {
      this.initAutoGrowTextareas();
      const mount = document.getElementById("lg-cycle-calendar-mount");
      if (!mount) return;
      const startInput = document.getElementById("new-cycle-start");
      const endInput = document.getElementById("new-cycle-end");
      const startVal = startInput ? startInput.value : "";
      const endVal = endInput ? endInput.value : "";
      if (!mount.dataset.calBound || this._cycleCalState.startIso !== startVal || this._cycleCalState.endIso !== endVal) {
        const refDt = this._parseIsoDate(startVal) || new Date();
        if (!mount.dataset.calBound) {
          this._cycleCalState.target = "start";
          this._cycleCalState.viewYear = refDt.getFullYear();
          this._cycleCalState.viewMonth = refDt.getMonth();
          mount.dataset.calBound = "1";
          mount.addEventListener("click", (e) => {
            const btn = e.target.closest("[data-cal-nav], [data-cal-date], [data-cal-preset]");
            if (!btn) return;
            e.preventDefault();
            if (btn.dataset.calNav === "prev") {
              this.cycleCalShiftMonth(-1);
            } else if (btn.dataset.calNav === "next") {
              this.cycleCalShiftMonth(1);
            } else if (btn.dataset.calPreset === "6m") {
              this.cycleCalApplySixMonth();
            } else if (btn.dataset.calDate) {
              this.cycleCalPickDate(btn.dataset.calDate);
            }
          });
        }
        this._cycleCalState.startIso = startVal;
        this._cycleCalState.endIso = endVal;
        this.cycleCalRender();
      }
    },

    cycleCalSetTarget(target) {
      this._cycleCalState.target = target === "end" ? "end" : "start";
      const targetIso = target === "end" ? this._cycleCalState.endIso : this._cycleCalState.startIso;
      const dt = this._parseIsoDate(targetIso);
      if (dt) {
        this._cycleCalState.viewYear = dt.getFullYear();
        this._cycleCalState.viewMonth = dt.getMonth();
      }
      this.cycleCalRender();
    },

    cycleCalShiftMonth(delta) {
      const dt = new Date(this._cycleCalState.viewYear, this._cycleCalState.viewMonth + delta, 1);
      this._cycleCalState.viewYear = dt.getFullYear();
      this._cycleCalState.viewMonth = dt.getMonth();
      this.cycleCalRender();
    },

    cycleCalSetYear(yearVal) {
      const yr = Number(yearVal);
      if (!Number.isFinite(yr) || yr < 2000 || yr > 2100) return;
      this._cycleCalState.viewYear = yr;
      this.cycleCalRender();
    },

    cycleCalApplySixMonth() {
      if (!this._cycleCalState.startIso) return;
      this._cycleCalState.endIso = this._addSixMonthsMinusOne(this._cycleCalState.startIso);
      this._cycleCalState.target = "end";
      this._syncCycleDateInputs();
      this.cycleCalRender();
    },

    cycleCalPickDate(iso) {
      const st = this._cycleCalState;
      if (st.target === "start") {
        st.startIso = iso;
        if (!st.endIso || st.endIso < iso) {
          st.endIso = this._addSixMonthsMinusOne(iso);
        }
        st.target = "end";
      } else {
        if (st.startIso && iso < st.startIso) {
          st.startIso = iso;
          st.target = "end";
        } else {
          st.endIso = iso;
          st.target = "start";
        }
      }
      const picked = this._parseIsoDate(iso);
      if (picked) {
        st.viewYear = picked.getFullYear();
        st.viewMonth = picked.getMonth();
      }
      this._syncCycleDateInputs();
      this.cycleCalRender();
    },

    _syncCycleDateInputs() {
      const startEl = document.getElementById("new-cycle-start");
      const endEl = document.getElementById("new-cycle-end");
      if (startEl) startEl.value = this._cycleCalState.startIso;
      if (endEl) endEl.value = this._cycleCalState.endIso;
      const startLabel = document.getElementById("cycle-start-display");
      const endLabel = document.getElementById("cycle-end-display");
      if (startLabel) startLabel.textContent = this._formatPrettyDate(this._cycleCalState.startIso);
      if (endLabel) endLabel.textContent = this._formatPrettyDate(this._cycleCalState.endIso);
    },

    cycleCalRender() {
      const mount = document.getElementById("lg-cycle-calendar-mount");
      if (!mount) return;
      const st = this._cycleCalState;
      const startBtn = document.getElementById("cycle-trigger-start");
      const endBtn = document.getElementById("cycle-trigger-end");
      if (startBtn) startBtn.classList.toggle("is-editing", st.target === "start");
      if (endBtn) endBtn.classList.toggle("is-editing", st.target === "end");
      this._syncCycleDateInputs();

      const monthNames = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
      ];
      const todayIso = this._formatIsoDate(new Date());
      const firstOfMonth = new Date(st.viewYear, st.viewMonth, 1);
      const startWeekday = firstOfMonth.getDay();
      const gridStart = new Date(st.viewYear, st.viewMonth, 1 - startWeekday);

      let yearOpts = "";
      for (let y = st.viewYear - 2; y <= st.viewYear + 4; y += 1) {
        yearOpts += `<option value="${y}"${y === st.viewYear ? " selected" : ""}>${y}</option>`;
      }

      let cellsHtml = "";
      for (let i = 0; i < 42; i += 1) {
        const cellDt = new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i);
        const cellIso = this._formatIsoDate(cellDt);
        const isOutside = cellDt.getMonth() !== st.viewMonth;
        const isStart = st.startIso && cellIso === st.startIso;
        const isEnd = st.endIso && cellIso === st.endIso;
        const inRange = st.startIso && st.endIso && cellIso > st.startIso && cellIso < st.endIso;
        const isToday = cellIso === todayIso;
        const cls = [
          "lg-cal-day",
          isOutside ? "is-outside" : "",
          inRange ? "is-in-range" : "",
          isStart ? "is-range-start" : "",
          isEnd ? "is-range-end" : "",
          isToday ? "is-today" : ""
        ].filter(Boolean).join(" ");
        cellsHtml += `<button type="button" class="${cls}" data-cal-date="${cellIso}" aria-label="${cellIso}">${cellDt.getDate()}</button>`;
      }

      let durationText = "Select dates";
      const sDt = this._parseIsoDate(st.startIso);
      const eDt = this._parseIsoDate(st.endIso);
      if (sDt && eDt && eDt >= sDt) {
        const days = Math.round((eDt - sDt) / 86400000) + 1;
        durationText = `${days} days selected`;
      }

      const modeHint = st.target === "start" ? "Picking From date" : "Picking To date";
      mount.innerHTML = `
        <div class="lg-cal-shell">
          <div class="lg-cal-header">
            <button type="button" class="lg-cal-nav" data-cal-nav="prev" title="Previous Month" aria-label="Previous Month">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
            </button>
            <div style="display:flex; align-items:center; gap:6px;">
              <span class="lg-cal-month-label">${monthNames[st.viewMonth]}</span>
              <select class="liquid-glass-control liquid-glass-select" style="width:auto; height:30px; padding:0 28px 0 10px; font-size:12.5px;"
                      onchange="window.StarAppBridge.cycleCalSetYear(this.value)" aria-label="Calendar Year">
                ${yearOpts}
              </select>
            </div>
            <button type="button" class="lg-cal-nav" data-cal-nav="next" title="Next Month" aria-label="Next Month">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
          </div>
          <div class="lg-cal-weekdays">
            <span>Su</span><span>Mo</span><span>Tu</span><span>We</span><span>Th</span><span>Fr</span><span>Sa</span>
          </div>
          <div class="lg-cal-grid">${cellsHtml}</div>
          <div class="lg-cal-footer">
            <span style="font-weight:700; color:var(--deep-frozen-midnight);">${modeHint}</span>
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-variant-numeric:tabular-nums; color:var(--frost-navy-50);">${durationText}</span>
              <button type="button" class="cycle-tab-btn is-active" data-cal-preset="6m" style="border:1px solid var(--icy-steel-50);">+6M Window</button>
            </div>
          </div>
        </div>
      `;
    }
  };
})();
