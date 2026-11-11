// Service worker: guarda so a "casca" da tela (HTML, CSS, JS, fontes) para abrir mesmo com
// Wi-Fi ruim. NUNCA guarda /api/*: os dados da cadeia sempre vem do gateway, sem copia velha.
"use strict";
const CACHE = "cc-shell-v3";
const SHELL = ["/", "/static/style.css", "/static/app.js", "/static/vendor/chart.umd.min.js",
  "/static/vendor/chartjs-plugin-annotation.min.js", "/static/vendor/qrcode.js",
  "/static/icons/icon-192.png", "/manifest.webmanifest",
  "/verificador", "/static/verificador.js", "/static/verifier-core.js", "/static/metrics.js"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => Promise.all(SHELL.map((u) => c.add(u).catch(() => {})))));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname === "/healthz" || url.pathname === "/sw.js") return;
  // rede primeiro (sempre a versao nova); se cair, usa a copia guardada
  e.respondWith(
    fetch(req).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req).then((hit) => hit || Response.error()))
  );
});
