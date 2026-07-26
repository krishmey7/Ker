/**
 * Profil appareil + réseau — fluidité prioritaire sur tous les téléphones.
 * <html data-wow="low|medium|high" data-network="slow|ok">
 */
(function () {
  const root = document.documentElement;

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    root.dataset.wow = 'low';
    root.dataset.network = 'slow';
    return;
  }

  const conn = navigator.connection;
  const saveData = !!conn?.saveData;
  const effectiveType = conn?.effectiveType || '4g';
  const slowNetwork =
    saveData || effectiveType === 'slow-2g' || effectiveType === '2g' || effectiveType === '3g';

  root.dataset.network = slowNetwork ? 'slow' : 'ok';

  const isTouchPhone =
    window.matchMedia('(pointer: coarse)').matches &&
    window.matchMedia('(max-width: 900px)').matches;
  const cores = navigator.hardwareConcurrency || 4;
  const memory = navigator.deviceMemory || 4;

  /* Mobile-first : low par défaut, medium seulement sur téléphones récents + bon réseau */
  let tier = 'low';
  if (!isTouchPhone && !slowNetwork) {
    if (cores >= 8 && memory >= 8) tier = 'high';
    else if (cores >= 6 && memory >= 4) tier = 'medium';
  } else if (isTouchPhone && !slowNetwork && cores >= 6 && memory >= 4) {
    tier = 'medium';
  }

  if (slowNetwork) tier = 'low';

  root.dataset.wow = tier;

  window.kerDowngradeWow = function () {
    const current = root.dataset.wow;
    if (current === 'high') root.dataset.wow = 'medium';
    else if (current === 'medium') root.dataset.wow = 'low';
  };

  window.kerGetWowTier = function () {
    return root.dataset.wow || 'low';
  };

  window.kerIsSlowNetwork = function () {
    return root.dataset.network === 'slow';
  };

  conn?.addEventListener?.('change', () => {
    const slow =
      conn.saveData || conn.effectiveType === 'slow-2g' || conn.effectiveType === '2g';
    root.dataset.network = slow ? 'slow' : 'ok';
    if (slow) root.dataset.wow = 'low';
  });
})();
