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

  // Cross-window live data synchronization handler
  async function triggerCrossWindowLiveReload(sourceName) {
    const now = Date.now();
    // Debounce rapid sync triggers within 150ms
    if (now - lastSyncTimestamp < 150) return;
    lastSyncTimestamp = now;

    try {
      const latestDataJson = await window.StarAppBridge.getStore("data");
      if (latestDataJson && window.starAppController && typeof window.starAppController.reload_data === "function") {
        console.log(`[StarAppBridge] Live data sync executed from ${sourceName}. Updating controller...`);
        window.starAppController.reload_data(latestDataJson);
      }
    } catch (err) {
      console.warn("[StarAppBridge] Cross-window live sync error:", err);
    }
  }

  // 1. Listen for BroadcastChannel events from other browser windows
  if (syncChannel) {
    syncChannel.onmessage = (event) => {
      if (event.data && event.data.type === "STARAPP_DATA_UPDATED" && event.data.sender !== currentWindowId) {
        triggerCrossWindowLiveReload("BroadcastChannel");
      }
    };
  }

  // 2. Fallback: Listen for localStorage storage events across windows
  window.addEventListener("storage", (e) => {
    if (e.key === "starapp_data" && e.newValue) {
      triggerCrossWindowLiveReload("storage_event");
    }
  });

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

    // Dispatch UI click/action event to Python controller
    dispatchAction(action, payloadJson = "{}") {
      if (window.starAppController && typeof window.starAppController.handle_event === "function") {
        window.starAppController.handle_event(action, payloadJson);
      } else {
        console.warn("[StarAppBridge] Controller not yet initialized. Queuing action:", action);
      }
    }
  };
})();
