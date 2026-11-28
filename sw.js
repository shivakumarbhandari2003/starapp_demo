/**
 * STARAPP SERVICE WORKER & ASSET CACHING ENGINE
 * Provides instant secondary load times and offline execution for:
 * 1. Pyodide WebAssembly binaries & Python standard library (jsDelivr CDN)
 * 2. StarApp static CSS design tokens, components, and layout files
 * 3. StarApp JavaScript bridge and Python bundle
 */

const CACHE_NAME = "starapp-runtime-cache-v78";
const PYODIDE_CACHE_NAME = "starapp-pyodide-v0.26.2";

// Static core assets to pre-cache on service worker install
const CORE_STATIC_ASSETS = [
  "./",
  "./index.html",
  "./css/design_tokens.css?v=121",
  "./css/liquid_glass.css?v=121",
  "./css/layout.css?v=121",
  "./css/components.css?v=121",
  "./css/responsive.css?v=121",
  "./js/api.js?v=121",
  "./js/bridge.js?v=121",
  "./js/starapp_bundle.js?v=121"
];

// Install: Cache local static assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(CORE_STATIC_ASSETS).catch((err) => {
        console.warn("[SW] Some initial assets could not be pre-cached:", err);
      });
    }).then(() => self.skipWaiting())
  );
});

// Activate: Clean up old cache versions
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME && key !== PYODIDE_CACHE_NAME) {
            console.log("[SW] Removing legacy cache:", key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: Strategy depending on request type
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // 1. Pyodide CDN assets: Cache-First strategy (immutable v0.26.2 release assets)
  if (url.origin === "https://cdn.jsdelivr.net" && url.pathname.includes("pyodide")) {
    event.respondWith(
      caches.open(PYODIDE_CACHE_NAME).then(async (cache) => {
        const cachedResponse = await cache.match(event.request);
        if (cachedResponse) {
          return cachedResponse;
        }
        try {
          const networkResponse = await fetch(event.request);
          if (networkResponse && networkResponse.status === 200) {
            cache.put(event.request, networkResponse.clone());
          }
          return networkResponse;
        } catch (fetchErr) {
          // If offline and not in cache, fallback
          return cachedResponse || Promise.reject(fetchErr);
        }
      })
    );
    return;
  }

  // 2. Local StarApp assets: Network-First with cache:"no-store" so F5 always pulls latest live edits
  if (url.origin === self.location.origin) {
    if (event.request.method !== "GET" || url.pathname.startsWith("/api/")) return;

    event.respondWith(
      fetch(event.request, { cache: "no-store" }).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const resClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, resClone));
        }
        return networkResponse;
      }).catch(async () => {
        const cache = await caches.open(CACHE_NAME);
        return cache.match(event.request);
      })
    );
  }
});

