/**
 * Client WebSocket — résilient (reconnexion, file d'attente, réseau lent).
 */
function coupleRoom(roomCode, userId, initialCompatibility = 50, initialLevel = 1) {
  return {
    roomCode,
    userId: Number(userId),
    coupleCompatibility: Number(initialCompatibility) || 50,
    coupleLevel: Number(initialLevel) || 1,
    socket: null,
    phase: 'lobby',
    question: {},
    reveal: { answers: [] },
    answerText: '',
    hasAnswered: false,
    partnerHasAnswered: false,
    category: '',
    activeReaction: null,
    partnerReaction: null,
    waitingReveal: false,
    autoNextSeconds: 10,
    autoNextCountdown: 0,
    autoNextTimer: null,
    autoNextCountdownTimer: null,
    errorMessage: '',
    usage: {
      remaining: 7,
      limit: 7,
      used: 0,
      extra_questions: 0,
      mode: 'free',
      unlimited: false,
      badge: '',
      show_paywall: false,
      all_categories: false,
    },
    adReward: {
      can_watch_ad: true,
      user_completed: false,
      partner_completed: false,
      waiting_for_partner: false,
    },
    adPlaying: false,
    adCountdown: 0,
    adMessage: '',
    connectionStatus: 'connecting',
    pendingMessages: [],
    reconnectDelay: 800,
    maxReconnectDelay: 12000,
    reconnectTimer: null,
    reactions: [
      { id: 'love', emoji: '❤️', label: 'Amour' },
      { id: 'laugh', emoji: '😂', label: 'Rire' },
      { id: 'blush', emoji: '😳', label: 'Touché' },
      { id: 'warm', emoji: '🥰', label: 'Tendre' },
      { id: 'adore', emoji: '😍', label: 'Adore' },
      { id: 'fire', emoji: '🔥', label: 'Intense' },
      { id: 'sad', emoji: '😢', label: 'Triste' },
      { id: 'hurt', emoji: '💔', label: 'Peiné' },
    ],

    init() {
      if (window.KerRewardedAds && window.KER_AD_CONFIG) {
        window.KerRewardedAds.init(window.KER_AD_CONFIG);
      }
      window.addEventListener('online', () => this.connect());
      window.addEventListener('offline', () => this.setOffline());
    },

    syncAdRewardFromPayload(payload) {
      const rewards = payload.ad_rewards || {};
      const mine = rewards[String(this.userId)];
      if (mine) {
        this.adReward = { ...this.adReward, ...mine };
      }
    },

    applyPaywallPayload(payload) {
      this.phase = 'paywall';
      if (payload.usage) this.usage = payload.usage;
      this.syncAdRewardFromPayload(payload);
      this.adMessage = '';
    },

    async watchRewardedAd() {
      if (!window.KerRewardedAds || this.adPlaying || !this.adReward.can_watch_ad) return;

      this.adPlaying = true;
      this.adMessage = '';
      this.errorMessage = '';

      try {
        const result = await window.KerRewardedAds.watchAndValidate((progress) => {
          if (progress.phase === 'playing') {
            this.adCountdown = progress.remaining;
          }
        });

        this.adPlaying = false;
        this.adCountdown = 0;

        if (result.usage) this.usage = result.usage;
        if (result.ad_reward) this.adReward = { ...this.adReward, ...result.ad_reward };

        if (result.unlocked) {
          this.adMessage = result.message || '❤️ Vous avez débloqué 5 questions';
          this.phase = 'transition';
          return;
        }

        if (result.ad_reward?.waiting_for_partner) {
          this.adMessage = 'Pub terminée ❤️ — En attente du partenaire';
        } else {
          this.adMessage = result.message || 'Pub terminée ❤️';
        }
      } catch (err) {
        this.adPlaying = false;
        this.adCountdown = 0;
        this.errorMessage = err.message || 'Impossible de valider la publicité.';
      }
    },

    connectionLabel() {
      const map = {
        connecting: 'Connexion…',
        live: 'En direct',
        reconnecting: 'Reconnexion…',
        offline: 'Hors ligne',
      };
      return map[this.connectionStatus] || '';
    },

    setOffline() {
      this.connectionStatus = 'offline';
      this.errorMessage = 'Pas de réseau — vos réponses reprendront à la reconnexion.';
      if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
      if (this.socket) {
        this.socket.onclose = null;
        this.socket.onerror = null;
        try {
          this.socket.close();
        } catch {
          /* fermeture silencieuse */
        }
        this.socket = null;
      }
    },

    scheduleReconnect() {
      if (!navigator.onLine) {
        this.setOffline();
        return;
      }
      this.connectionStatus = 'reconnecting';
      if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
      this.reconnectTimer = setTimeout(() => this.connect(), this.reconnectDelay);
      this.reconnectDelay = Math.min(this.reconnectDelay * 1.4, this.maxReconnectDelay);
    },

    connect() {
      if (!navigator.onLine) {
        this.setOffline();
        return;
      }

      if (this.socket?.readyState === WebSocket.OPEN) return;

      this.connectionStatus = 'connecting';
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const url = `${proto}://${location.host}/ws/couple/${this.roomCode}/`;

      try {
        this.socket = new WebSocket(url);
      } catch {
        this.scheduleReconnect();
        return;
      }

      this.socket.onopen = () => {
        this.connectionStatus = 'live';
        this.reconnectDelay = 800;
        this.errorMessage = '';
        this.flushPending();
      };

      this.socket.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          this.handleMessage(msg);
        } catch {
          /* message invalide ignoré */
        }
      };

      this.socket.onerror = () => {
        this.connectionStatus = 'reconnecting';
      };

      this.socket.onclose = () => {
        this.scheduleReconnect();
      };
    },

    flushPending() {
      while (this.pendingMessages.length && this.socket?.readyState === WebSocket.OPEN) {
        const { type, payload } = this.pendingMessages.shift();
        this.socket.send(JSON.stringify({ type, payload }));
      }
    },

    send(type, payload = {}) {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type, payload }));
        return true;
      }
      this.pendingMessages.push({ type, payload });
      if (this.pendingMessages.length > 20) {
        this.pendingMessages.shift();
      }
      if (navigator.onLine) {
        this.connectionStatus = 'reconnecting';
        this.connect();
      }
      return false;
    },

    triggerRevealBurst() {
      if (typeof window.kerBurst === 'function') {
        window.kerBurst(window.innerWidth / 2, window.innerHeight * 0.35);
      }
    },

    syncAnswerPhase() {
      if (this.hasAnswered && this.partnerHasAnswered && this.phase !== 'reveal') {
        this.phase = 'waiting';
        this.waitingReveal = true;
      } else if (this.hasAnswered && !this.partnerHasAnswered) {
        this.phase = 'waiting';
        this.waitingReveal = false;
      } else if (!this.hasAnswered) {
        this.phase = 'question';
        this.waitingReveal = false;
      }
    },

    handleMessage(msg) {
      const type = msg.type;
      const payload = msg.payload ?? {};

      if (type === 'session_state') {
        this.applyState(payload);
        return;
      }
      if (type === 'question') {
        const q = msg.question || payload.question || payload;
        if (!this.hasValidQuestion(q)) {
          this.errorMessage = 'Question indisponible — réessayez dans un instant.';
          this.phase = 'lobby';
          return;
        }
        this.clearAutoNextTimers();
        this.phase = 'question';
        this.question = q;
        if (payload.usage) this.usage = payload.usage;
        this.answerText = '';
        this.hasAnswered = false;
        this.partnerHasAnswered = false;
        this.activeReaction = null;
        this.reveal = { answers: [] };
        return;
      }
      if (type === 'answer_submitted') {
        const submitterId = Number(payload.user_id);
        if (submitterId === this.userId) {
          this.hasAnswered = true;
        } else {
          this.partnerHasAnswered = true;
        }
        this.syncAnswerPhase();
        return;
      }
      if (type === 'reveal') {
        if (!payload.answers || payload.answers.length < 2) return;
        this.phase = 'reveal';
        this.reveal = payload;
        this.hasAnswered = true;
        this.partnerHasAnswered = true;
        this.waitingReveal = false;
        if (payload.couple_compatibility_score != null) {
          this.coupleCompatibility = Number(payload.couple_compatibility_score);
        }
        if (payload.couple_level != null) {
          this.coupleLevel = Number(payload.couple_level);
        }
        this.startAutoNextCountdown(payload.auto_next_seconds || this.autoNextSeconds);
        if (!window.kerIsSlowNetwork?.()) {
          setTimeout(() => this.triggerRevealBurst(), 80);
        } else {
          document.documentElement.classList.add('ker-burst-css');
          setTimeout(() => document.documentElement.classList.remove('ker-burst-css'), 900);
        }
        return;
      }
      if (type === 'error') {
        this.errorMessage = payload.message || 'Une erreur est survenue.';
        return;
      }
      if (type === 'reaction') {
        if (Number(payload.user_id) !== this.userId) {
          this.partnerReaction = payload.emoji;
        }
        return;
      }
      if (type === 'paywall') {
        this.applyPaywallPayload(payload);
        return;
      }
      if (type === 'ad_reward_progress') {
        if (payload.usage) this.usage = payload.usage;
        this.syncAdRewardFromPayload(payload);
        const mine = (payload.ad_rewards || {})[String(this.userId)];
        if (mine?.waiting_for_partner) {
          this.adMessage = 'Pub terminée ❤️ — En attente du partenaire';
        } else if (mine?.partner_completed && !mine?.user_completed) {
          this.adMessage = 'Votre moitié a regardé sa pub — à vous ❤️';
        }
        if (this.phase !== 'paywall') this.phase = 'paywall';
        return;
      }
      if (type === 'reward_unlocked') {
        if (payload.usage) this.usage = { ...this.usage, ...payload.usage };
        this.adMessage = payload.message || '❤️ Vous avez débloqué 5 questions';
        this.adReward.can_watch_ad = false;
        this.phase = 'transition';
        return;
      }
      if (type === 'premium_active' || type === 'weekend_mode_active' || type === 'subscription_activated') {
        if (payload.usage) this.usage = { ...this.usage, ...payload.usage };
        if (payload.access) this.usage = { ...this.usage, ...payload.access, badge: payload.access.badge || payload.message };
        this.adMessage = payload.message || this.usage.badge || '';
        this.phase = 'lobby';
        this.errorMessage = '';
        return;
      }
      if (type === 'session_finished') {
        this.phase = 'lobby';
      }
    },

    hasValidQuestion(q) {
      return !!(q && q.id && q.text);
    },

    applyState(state) {
      if (state.status === 'no_session') {
        this.phase = 'lobby';
        return;
      }

      if (state.status === 'paywall') {
        this.applyPaywallPayload(state);
        return;
      }

      if (state.usage) this.usage = state.usage;
      this.syncAdRewardFromPayload(state);

      this.hasAnswered = !!state.has_answered;
      this.partnerHasAnswered = !!state.partner_has_answered;

      if (state.status === 'reveal' && state.reveal?.answers?.length >= 2) {
        this.phase = 'reveal';
        this.reveal = state.reveal;
        return;
      }

      if (this.hasValidQuestion(state.question)) {
        this.question = state.question;
        this.phase = this.hasAnswered && !this.partnerHasAnswered ? 'waiting' : 'question';
        return;
      }

      this.phase = 'lobby';
    },

    startSession() {
      this.send('start_session', { category: this.category });
    },

    submitAnswer() {
      const text = this.answerText.trim();
      if (!text || this.hasAnswered) return;

      if (!navigator.onLine) {
        this.errorMessage = 'Hors ligne — reconnectez-vous au réseau.';
        return;
      }

      const sent = this.send('answer_submitted', { text });
      if (!sent) {
        this.errorMessage = 'Envoi en attente — reconnexion…';
        this.hasAnswered = true;
        this.syncAnswerPhase();
        return;
      }

      this.errorMessage = '';
      if (this.partnerHasAnswered) {
        this.hasAnswered = true;
        this.waitingReveal = true;
        this.phase = 'waiting';
      }
    },

    sendReaction(emoji) {
      this.activeReaction = emoji;
      this.send('reaction', { emoji });
    },

    clearAutoNextTimers() {
      if (this.autoNextTimer) {
        clearTimeout(this.autoNextTimer);
        this.autoNextTimer = null;
      }
      if (this.autoNextCountdownTimer) {
        clearInterval(this.autoNextCountdownTimer);
        this.autoNextCountdownTimer = null;
      }
      this.autoNextCountdown = 0;
    },

    startAutoNextCountdown(seconds) {
      this.clearAutoNextTimers();
      const delay = Math.max(2, Number(seconds) || 10);
      this.autoNextSeconds = delay;
      this.autoNextCountdown = delay;
      this.autoNextCountdownTimer = setInterval(() => {
        if (this.autoNextCountdown > 0) this.autoNextCountdown -= 1;
      }, 1000);
      // La question suivante est poussée par le serveur (timer Celery / auto_advance).
      // Évite un double next_question depuis les deux téléphones (verrou SQLite).
      this.autoNextTimer = null;
    },

    nextQuestion() {
      this.clearAutoNextTimers();
      this.phase = 'transition';
      this.send('next_question');
    },

    categoryLabel(cat) {
      const labels = {
        romantic: 'Romantique',
        funny: 'Drôle',
        spicy: 'Spicy',
        deep: 'Profond',
        know_partner: 'Partenaire',
        future: 'Futur',
        habits: 'Habitudes',
      };
      return labels[cat] || cat || 'Couple';
    },

    myAnswer() {
      return (this.reveal.answers || []).find((a) => Number(a.user_id) === this.userId);
    },

    partnerAnswer() {
      return (this.reveal.answers || []).find((a) => Number(a.user_id) !== this.userId);
    },
  };
}
