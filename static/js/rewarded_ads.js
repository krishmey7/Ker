/**
 * Publicités récompensées — simulation locale (dev) et hook prod (Monetag / GAM).
 * Le déblocage est toujours validé par le backend.
 */
const KerRewardedAds = {
  config: {
    debug: true,
    simulationSeconds: 30,
    completeUrl: '/payments/api/rewarded-ad/complete/',
  },

  init(userConfig = {}) {
    this.config = { ...this.config, ...userConfig };
  },

  getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  },

  /**
   * Point d'entrée unique — choisit simulateur ou régie réelle.
   */
  async showRewardedAd(onProgress) {
    if (this.config.debug) {
      return this.simulateRewardedAd(onProgress);
    }
    return this.showRealRewardedAd(onProgress);
  },

  /**
   * Simulation locale 30s — pour développement sans régie.
   */
  simulateRewardedAd(onProgress) {
    const total = this.config.simulationSeconds || 30;
    let remaining = total;

    return new Promise((resolve, reject) => {
      if (typeof onProgress === 'function') {
        onProgress({ phase: 'playing', remaining, total });
      }

      const timer = setInterval(() => {
        remaining -= 1;
        if (typeof onProgress === 'function') {
          onProgress({ phase: 'playing', remaining: Math.max(0, remaining), total });
        }
        if (remaining <= 0) {
          clearInterval(timer);
          if (typeof onProgress === 'function') {
            onProgress({ phase: 'done', remaining: 0, total });
          }
          resolve({ simulated: true, ad_network: 'simulated' });
        }
      }, 1000);
    });
  },

  /**
   * Intégration régie réelle — à brancher sur Monetag ou Google Ad Manager.
   */
  showRealRewardedAd(onProgress) {
    return new Promise((resolve, reject) => {
      if (typeof window.showMonetagRewardedAd === 'function') {
        window.showMonetagRewardedAd({
          onComplete: () => resolve({ simulated: false, ad_network: 'monetag' }),
          onError: (err) => reject(err || new Error('Pub interrompue')),
          onProgress,
        });
        return;
      }
      reject(
        new Error(
          'Régie publicitaire non configurée. Activez DEBUG pour la simulation locale.'
        )
      );
    });
  },

  /**
   * Valide la pub côté backend — seule source de vérité pour les crédits.
   */
  async completeReward(adNetwork = 'simulated') {
    const response = await fetch(this.config.completeUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCsrfToken(),
      },
      credentials: 'same-origin',
      body: JSON.stringify({ ad_network: adNetwork }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Validation impossible');
    }
    return data;
  },

  /**
   * Lance la pub puis valide — flux complet pour le bouton UI.
   */
  async watchAndValidate(onProgress) {
    const adResult = await this.showRewardedAd(onProgress);
    return this.completeReward(adResult.ad_network || 'simulated');
  },
};

window.KerRewardedAds = KerRewardedAds;
