/* Keeps the app available offline. When online, the app's own files are always fetched fresh
   (skipping the browser's 10-minute cache), so a new version shows on the next open. */
const CACHE = "tbs-preview-v13";
const FILES = ["./", "index.html", "manifest.webmanifest", "apple-touch-icon.png", "icon-192.png", "icon-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES.map(f => new Request(f, { cache: "reload" })))).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  // Only the app's own files. Calls to the sync server are left alone and never stored.
  if (new URL(req.url).origin !== self.location.origin) return;
  e.respondWith(fetch(req, { cache: "no-store" }).then(r => { if (r.ok) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(req, copy)); } return r; })
    .catch(() => caches.match(req).then(m => m || caches.match("index.html"))));
});
