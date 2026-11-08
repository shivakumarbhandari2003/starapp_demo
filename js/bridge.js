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
        const input = document.getElementById(fileInputId);
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
