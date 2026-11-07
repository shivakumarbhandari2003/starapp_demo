/**
 * STARAPP MINIMAL JS BRIDGE
 * Technical Explanation:
 * Browser APIs such as IndexedDB (asynchronous object store) and FileReader (reading local
 * files as Base64 for persistent offline storage) require asynchronous JavaScript promises.
 * To keep strict architectural purity, NO business logic, calculations, or validations exist here.
 * This file is solely a thin asynchronous storage and file I/O bridge for Python/Pyodide.
 */

(function () {
  const DB_NAME = "StarAppLocalDB";
  const DB_VERSION = 5;
  const STORE_NAME = "starapp_state";

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

  window.StarAppBridge = {
    // Read JSON state from IndexedDB
    async getStore(key) {
      try {
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
          const tx = db.transaction(STORE_NAME, "readonly");
          const store = tx.objectStore(STORE_NAME);
          const req = store.get(key);
          req.onsuccess = () => resolve(req.result || null);
          req.onerror = () => reject(req.error);
        });
      } catch (err) {
        console.warn("[StarAppBridge] IndexedDB read failed, falling back to localStorage", err);
        return localStorage.getItem("starapp_" + key);
      }
    },

    // Write JSON state to IndexedDB with localStorage fallback
    async setStore(key, value) {
      try {
        localStorage.setItem("starapp_" + key, value);
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
          const tx = db.transaction(STORE_NAME, "readwrite");
          const store = tx.objectStore(STORE_NAME);
          const req = store.put(value, key);
          req.onsuccess = () => resolve(true);
          req.onerror = () => reject(req.error);
        });
      } catch (err) {
        console.warn("[StarAppBridge] IndexedDB write failed, persisted in localStorage", err);
        return true;
      }
    },

    // Clear state
    async clearStore() {
      try {
        localStorage.removeItem("starapp_data");
        localStorage.removeItem("starapp_session");
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
          const tx = db.transaction(STORE_NAME, "readwrite");
          const store = tx.objectStore(STORE_NAME);
          const req = store.clear();
          req.onsuccess = () => resolve(true);
          req.onerror = () => reject(req.error);
        });
      } catch (err) {
        return true;
      }
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

