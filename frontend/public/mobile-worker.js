const CACHE_PREFIX = "tremplin-mobile-shell-";
const CACHE = CACHE_PREFIX + "1";
const SHELL = "/mobile";
const STATIC = ["/mobile.webmanifest", "/mobile-icon-192.png", "/mobile-icon-512.png"];

function asset(path) {
  return path.startsWith("/assets/") && !path.includes("?");
}

async function install() {
  const cache = await caches.open(CACHE);
  const response = await fetch(SHELL, { credentials: "omit" });
  if (!response.ok) throw new Error("Mobile shell unavailable");
  const html = await response.clone().text();
  const embedded = [...html.matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g)]
    .map((match) => match[1]).filter(asset);
  await cache.addAll([...new Set([...STATIC, ...embedded])]);
  await cache.put(SHELL, response);
  await self.skipWaiting();
}

self.addEventListener("install", (event) => event.waitUntil(install()));

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter((name) => name.startsWith(CACHE_PREFIX) && name !== CACHE)
      .map((name) => caches.delete(name)));
    await self.clients.claim();
  })());
});

async function serve(request, key, navigation) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(key);
  if (cached && !navigation) return cached;
  try {
    const response = await fetch(request);
    if (response.ok && response.type === "basic" && !response.redirected) {
      await cache.put(key, response.clone());
    }
    return response;
  } catch {
    return cached ?? new Response("", { status: 503 });
  }
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (request.mode === "navigate" && url.pathname === SHELL) {
    event.respondWith(serve(request, SHELL, true));
  } else if (asset(url.pathname) || STATIC.includes(url.pathname)) {
    event.respondWith(serve(request, url.pathname, false));
  }
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: "window" });
    const mobile = windows.find((item) => new URL(item.url).pathname === SHELL);
    if (mobile) await mobile.focus();
    else await self.clients.openWindow(SHELL);
  })());
});
