/**
 * Ambiance particules — qualité adaptative + budget 60 fps.
 */
(function () {
  const canvas = document.getElementById('ambient-canvas');
  if (!canvas) return;

  const tier = () => window.kerGetWowTier?.() || document.documentElement.dataset.wow || 'medium';
  if (tier() === 'low') {
    canvas.style.display = 'none';
    window.kerBurst = function () {
      document.documentElement.classList.add('ker-burst-css');
      setTimeout(() => document.documentElement.classList.remove('ker-burst-css'), 900);
    };
    return;
  }

  const ctx = canvas.getContext('2d', { alpha: true, desynchronized: true });
  let w, h, dpr, running = true;
  let targetCount = tier() === 'high' ? 26 : 16;
  let particles = [];
  let frameTimes = [];
  let frameSkip = 0;

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, tier() === 'high' ? 1.75 : 1.25);
    w = window.innerWidth;
    h = window.innerHeight;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function spawn(x, y, burst) {
    return {
      x: x ?? Math.random() * w,
      y: y ?? Math.random() * h,
      r: burst ? Math.random() * 2 + 1.2 : Math.random() * 1.8 + 0.8,
      vx: (Math.random() - 0.5) * (burst ? 4 : 0.35),
      vy: (Math.random() - 0.5) * (burst ? 4 : 0.35) - (burst ? 0 : 0.06),
      a: burst ? 0.75 : Math.random() * 0.22 + 0.1,
      hue: Math.random() > 0.5 ? 330 : 278,
      life: burst ? 45 + (Math.random() * 15 | 0) : 0,
    };
  }

  function seed() {
    particles = Array.from({ length: targetCount }, () => spawn());
  }

  function drawConnections() {
    if (tier() !== 'high') return;
    const ambient = particles.filter((p) => !p.life);
    const len = Math.min(ambient.length, 22);
    for (let i = 0; i < len; i++) {
      for (let j = i + 1; j < Math.min(i + 4, len); j++) {
        const a = ambient[i];
        const b = ambient[j];
        const dist = Math.hypot(a.x - b.x, a.y - b.y);
        if (dist < 85) {
          ctx.strokeStyle = `rgba(255, 140, 190, ${0.06 * (1 - dist / 85)})`;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }
  }

  function tick(now) {
    if (!running) return;

    if (frameSkip > 0) {
      frameSkip--;
      requestAnimationFrame(tick);
      return;
    }

    const t0 = performance.now();
    ctx.clearRect(0, 0, w, h);

    if (tier() === 'high' && (now | 0) % 2 === 0) {
      drawConnections();
    }

    let ambientCount = 0;
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.x += p.vx;
      p.y += p.vy;

      if (p.life > 0) {
        p.life--;
        p.a *= 0.91;
        p.vx *= 0.96;
        p.vy *= 0.96;
        if (p.life <= 0 || p.a < 0.02) {
          particles.splice(i, 1);
          continue;
        }
      } else {
        ambientCount++;
        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;
      }

      ctx.beginPath();
      ctx.fillStyle = `hsla(${p.hue}, 88%, 72%, ${p.a})`;
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }

    while (ambientCount < targetCount) {
      particles.push(spawn());
      ambientCount++;
    }

    const elapsed = performance.now() - t0;
    frameTimes.push(elapsed);
    if (frameTimes.length > 45) frameTimes.shift();
    if (frameTimes.length === 45) {
      const avg = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
      if (avg > 14 && targetCount > 12) {
        targetCount = Math.max(12, targetCount - 4);
        window.kerDowngradeWow?.();
        frameTimes = [];
      }
    }

    if (elapsed > 12) frameSkip = 1;

    requestAnimationFrame(tick);
  }

  window.kerBurst = function (x, y) {
    const cx = x ?? w / 2;
    const cy = y ?? h / 2;
    const n = tier() === 'high' ? 22 : 12;
    for (let i = 0; i < n; i++) {
      const angle = (Math.PI * 2 * i) / n;
      particles.push(spawn(cx, cy, true));
      const p = particles[particles.length - 1];
      p.vx = Math.cos(angle) * (2.5 + Math.random() * 3);
      p.vy = Math.sin(angle) * (2.5 + Math.random() * 3);
    }
    document.documentElement.classList.add('ker-burst-css');
    setTimeout(() => document.documentElement.classList.remove('ker-burst-css'), 900);
  };

  document.addEventListener('visibilitychange', () => {
    running = document.visibilityState === 'visible';
    if (running) requestAnimationFrame(tick);
  });

  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      resize();
      seed();
    }, 150);
  });

  resize();
  seed();
  requestAnimationFrame(tick);
})();
