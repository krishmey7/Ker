/**
 * Prompt d'installation PWA — Android / iOS / bureau.
 * beforeinstallprompt n'existe pas sur Safari iOS et est rare sur HTTP (hors localhost) : instructions manuelles.
 */
(function () {
  const STORAGE_KEY = 'ker_install_dismissed_at';
  const SESSION_HIDE_KEY = 'ker_install_session_hidden';
  const COOLDOWN_DAYS = 7;
  const COOLDOWN_MS = COOLDOWN_DAYS * 24 * 60 * 60 * 1000;

  const NATIVE_FALLBACK_MS = 4500;

  let deferredPrompt = null;
  let fallbackTimer = null;

  const el = {
    banner: () => document.getElementById('ker-install-banner'),
    title: () => document.getElementById('ker-install-title'),
    accept: () => document.getElementById('ker-install-accept'),
    hintNative: () => document.getElementById('ker-install-hint-native'),
    hintAndroid: () => document.getElementById('ker-install-hint-android'),
    hintIos: () => document.getElementById('ker-install-hint-ios'),
    hintDesktop: () => document.getElementById('ker-install-hint-desktop'),
  };

  function isStandalone() {
    return (
      window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true
    );
  }

  function isIOS() {
    const ua = window.navigator.userAgent;
    return (
      /iPad|iPhone|iPod/.test(ua) ||
      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
    );
  }

  function isAndroid() {
    return /Android/i.test(navigator.userAgent);
  }

  function isSessionHidden() {
    try {
      return sessionStorage.getItem(SESSION_HIDE_KEY) === '1';
    } catch {
      return false;
    }
  }

  function setSessionHidden() {
    try {
      sessionStorage.setItem(SESSION_HIDE_KEY, '1');
    } catch {
      /* navigation privée : ignorer */
    }
  }

  function isDismissed() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    const ts = parseInt(raw, 10);
    if (Number.isNaN(ts)) return false;
    return Date.now() - ts < COOLDOWN_MS;
  }

  function dismissWithCooldown() {
    localStorage.setItem(STORAGE_KEY, String(Date.now()));
    hideBanner();
  }

  function hideBannerOnly() {
    el.banner()?.classList.add('hidden');
  }

  function hideBanner() {
    hideBannerOnly();
    clearFallbackTimer();
  }

  function clearFallbackTimer() {
    if (fallbackTimer) {
      clearTimeout(fallbackTimer);
      fallbackTimer = null;
    }
  }

  function setHintsVisible(mode) {
    const m = {
      native: el.hintNative(),
      android: el.hintAndroid(),
      ios: el.hintIos(),
      desktop: el.hintDesktop(),
    };
    Object.keys(m).forEach((k) => {
      const node = m[k];
      if (!node) return;
      node.classList.toggle('hidden', k !== mode);
    });
  }

  /**
   * mode: native | android_manual | ios | desktop_manual
   */
  function applyMode(mode) {
    const title = el.title();
    const accept = el.accept();
    if (!title || !accept) return;

    if (mode === 'native') {
      title.textContent = "Installer l'application ❤️";
      accept.textContent = 'Installer';
      setHintsVisible('native');
    } else if (mode === 'android_manual') {
      title.textContent = "Ajouter K'er à l'accueil";
      accept.textContent = 'OK, compris';
      setHintsVisible('android');
    } else if (mode === 'ios') {
      title.textContent = "Ajouter à l'écran d'accueil";
      accept.textContent = 'Compris';
      setHintsVisible('ios');
    } else if (mode === 'desktop_manual') {
      title.textContent = 'Installer comme application';
      accept.textContent = 'OK';
      setHintsVisible('desktop');
    }
  }

  function showBanner(mode) {
    if (isStandalone() || isDismissed() || isSessionHidden()) return;
    const b = el.banner();
    if (!b) return;
    if (!b.classList.contains('hidden') && b.dataset.mode === mode) return;

    b.classList.remove('hidden');
    b.dataset.mode = mode;
    applyMode(mode);
  }

  async function triggerNativeInstall() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    deferredPrompt = null;
    hideBanner();
    if (outcome === 'dismissed') {
      dismissWithCooldown();
    }
  }

  function scheduleNativeFallback() {
    clearFallbackTimer();
    fallbackTimer = window.setTimeout(() => {
      fallbackTimer = null;
      if (deferredPrompt || isStandalone() || isDismissed() || isSessionHidden()) return;
      const b = el.banner();
      if (b && !b.classList.contains('hidden')) return;

      if (isIOS()) {
        showBanner('ios');
      } else if (isAndroid()) {
        showBanner('android_manual');
      } else {
        showBanner('desktop_manual');
      }
    }, NATIVE_FALLBACK_MS);
  }

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    clearFallbackTimer();
    showBanner('native');
  });

  window.addEventListener('appinstalled', () => {
    deferredPrompt = null;
    hideBanner();
  });

  document.addEventListener('DOMContentLoaded', () => {
    if (isStandalone() || isDismissed() || isSessionHidden()) return;

    el.accept()?.addEventListener('click', () => {
      const mode = el.banner()?.dataset.mode;
      if (mode === 'native' && deferredPrompt) {
        triggerNativeInstall();
        return;
      }
      if (mode === 'ios' || mode === 'android_manual' || mode === 'desktop_manual') {
        setSessionHidden();
      }
      hideBannerOnly();
      clearFallbackTimer();
    });

    el.banner()
      ?.querySelector('#ker-install-dismiss')
      ?.addEventListener('click', dismissWithCooldown);

    if (isIOS()) {
      window.setTimeout(() => showBanner('ios'), 2000);
      return;
    }

    scheduleNativeFallback();
  });
})();
