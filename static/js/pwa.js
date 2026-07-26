/**
 * Enregistrement du service worker (scope racine).
 */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/service-worker.js', { scope: '/' })
      .catch((err) => console.warn('[PWA] Service worker:', err));
  });
}
