const CACHE = "financas-offline-v1";
const ARQUIVOS_OFFLINE = ["/offline.html", "/css/tokens.css", "/css/offline.css", "/img/pwa/icone.svg"];

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(ARQUIVOS_OFFLINE))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches
      .keys()
      .then((nomes) => Promise.all(nomes.filter((nome) => nome !== CACHE).map((nome) => caches.delete(nome))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (evento) => {
  const pedido = evento.request;
  if (pedido.method !== "GET") return;

  const url = new URL(pedido.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  if (pedido.mode === "navigate") {
    evento.respondWith(fetch(pedido).catch(() => caches.match("/offline.html")));
    return;
  }

  if (ARQUIVOS_OFFLINE.includes(url.pathname)) {
    evento.respondWith(fetch(pedido).catch(() => caches.match(url.pathname)));
  }
});
