const CACHE_NAME = "astrasync-v1";
const ASSETS = [
  "/frontend/pages/index.html",
  "/frontend/pages/login.html",
  "/frontend/pages/profile.html",
  "/frontend/pages/add_data.html",
  "/frontend/pages/upload.html",
  "/frontend/pages/history.html",
  "/frontend/pages/report.html",

  "/frontend/css/style.css",
  "/frontend/js/app.js",
  "/frontend/js/api.js",
  "/frontend/js/charts.js",

  "/frontend/public/manifest.json",
  "/frontend/public/assets/icon-192.png",
  "/frontend/public/assets/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.map(k => (k !== CACHE_NAME ? caches.delete(k) : null)))
    )
  );
});

self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
