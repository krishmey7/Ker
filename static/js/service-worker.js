/**
 * Service Worker K'er — cache UI (cache-first) + API (network-first).
 */
const STATIC_CACHE = 'ker-static-v5';
const PAGES_CACHE = 'ker-pages-v5';

const PRECACHE_STATIC = [
  '/static/css/app.css',
  '/static/js/perf.js',
  '/static/js/ambient.js',
  '/static/js/pwa.js',
  '/static/js/install-prompt.js',
  '/static/js/offline-handler.js',
  '/static/js/room.js',
  '/static/images/icons/icon-192.png',
  '/static/images/icons/icon-512.png',
  '/static/images/logo.png',
  '/static/images/favicon.ico',
  '/offline/',
];

const PRECACHE_PAGES = ['/offline/'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    Promise.all([
      caches.open(STATIC_CACHE).then((cache) =>
        cache.addAll(PRECACHE_STATIC).catch((err) => {
          console.warn('[SW] precache static partial', err);
        })
      ),
      caches.open(PAGES_CACHE).then((cache) =>
        cache.addAll(PRECACHE_PAGES).catch(() => {})
      ),
    ])
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== STATIC_CACHE && key !== PAGES_CACHE)
          .map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

function isStaticAsset(url) {
  return url.pathname.startsWith('/static/');
}

function isApiRequest(url) {
  return (
    url.pathname.startsWith('/payments/api/') ||
    url.pathname.startsWith('/admin/') ||
    url.pathname.startsWith('/ws/') ||
    url.pathname.includes('/api/')
  );
}

function isNavigation(request) {
  return request.mode === 'navigate';
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return caches.match(request);
  }
}

async function networkFirstPage(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(PAGES_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return caches.match('/offline/');
  }
}

async function networkFirstApi(request) {
  return fetch(request);
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (isApiRequest(url)) {
    event.respondWith(networkFirstApi(request));
    return;
  }

  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  if (isNavigation(request)) {
    event.respondWith(networkFirstPage(request));
    return;
  }

  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});
