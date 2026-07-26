/**
 * Gestion globale online/offline — évite actions réseau inutiles.
 */
(function () {
  function notify(status) {
    document.documentElement.dataset.network = status;
    window.dispatchEvent(new CustomEvent('ker:network', { detail: { status } }));
  }

  window.addEventListener('online', () => notify('online'));
  window.addEventListener('offline', () => notify('offline'));

  if (!navigator.onLine) {
    notify('offline');
  } else {
    notify('online');
  }
})();
