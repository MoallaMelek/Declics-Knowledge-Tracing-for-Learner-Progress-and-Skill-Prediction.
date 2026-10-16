'use strict';
// Feature 2 · Machine à remonter le parcours. Controls the cutoff for every view.
(function (L) {
  const {s} = L.dom, A = L.adapters;
  const W = 1000, H = 56, PAD = 14;

  function create({store, goTo}) {
    const range = document.getElementById('cutoff'), track = document.getElementById('track');
    const play = document.getElementById('play'), playIcon = document.getElementById('play-icon');
    const speed = document.getElementById('speed');
    let timer = null, dragTimer = null;

    const x = (i, n) => PAD + (n <= 1 ? 0 : i / (n - 1)) * (W - 2 * PAD);

    function render(st) {
      const snap = st.snapshot; if (!snap) return;
      const n = snap.steps_total, slots = A.timeline(snap), bw = Math.max(2, Math.min(26, (W - 2 * PAD) / Math.max(1, n - 1) * 0.55));
      range.max = String(n); range.min = '1'; range.value = String(snap.cutoff);
      const unit = A.stepName(snap.source);
      range.setAttribute('aria-valuetext', `${snap.cutoff} ${unit}(s) observé(s) sur ${n}`);
      const g = s('svg', {viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: 'none', class: 'track-svg'});
      g.append(s('line', {x1: PAD, x2: W - PAD, y1: H - 8, y2: H - 8, class: 'tl-base'}));
      for (const slot of slots) {
        const cx = x(slot.index, n);
        if (slot.kind === 'past') {
          const h = 6 + (H - 20) * slot.score;
          g.append(s('rect', {x: cx - bw / 2, y: H - 8 - h, width: bw, height: h, rx: 1.5, class: 'tl-bar', style: `fill:${L.dom.ramp(slot.score)}`}));
          if (slot.predicted !== null) g.append(s('line', {x1: cx - bw / 2 - 2, x2: cx + bw / 2 + 2, y1: H - 8 - (6 + (H - 20) * slot.predicted), y2: H - 8 - (6 + (H - 20) * slot.predicted), class: 'tl-pred'}));
        } else if (slot.kind === 'next') {
          g.append(s('rect', {x: cx - bw / 2, y: 6, width: bw, height: H - 14, rx: 1.5, class: 'tl-next'}));
          if (slot.predicted !== null) g.append(s('line', {x1: cx - bw / 2 - 2, x2: cx + bw / 2 + 2, y1: H - 8 - (6 + (H - 20) * slot.predicted), y2: H - 8 - (6 + (H - 20) * slot.predicted), class: 'tl-pred'}));
        } else g.append(s('line', {x1: cx, x2: cx, y1: H - 12, y2: H - 4, class: 'tl-future'}));
      }
      if (st.compareCutoff) g.append(s('line', {x1: x(st.compareCutoff - 1, n), x2: x(st.compareCutoff - 1, n), y1: 2, y2: H - 2, class: 'tl-compare'}));
      g.append(s('line', {x1: x(snap.cutoff - 1, n), x2: x(snap.cutoff - 1, n), y1: 0, y2: H, class: 'tl-now'}));
      track.replaceChildren(g);
      const last = snap.past[snap.past.length - 1];
      document.getElementById('cutoff-label').textContent = `${unit === 'groupe' ? 'Groupe' : 'Jour actif'} ${snap.cutoff} sur ${n}`;
      const when = snap.source === 'singpad' ? `J+${A.num(last.day, 1)} depuis le premier enregistrement` : `jour ${last.day} depuis l’inscription`;
      document.getElementById('cutoff-detail').textContent = snap.target
        ? `${when} · résultat du pas ${snap.cutoff + 1} masqué · frise : moyenne par concept`
        : `${when} · fin du parcours enregistré, rien à prévoir`;
      document.getElementById('prev').disabled = snap.cutoff <= 1;
      document.getElementById('next').disabled = snap.cutoff >= n;
      playIcon.setAttribute('href', st.playing ? '#i-pause' : '#i-play');
      play.setAttribute('aria-label', st.playing ? 'Pause' : 'Lecture');
      play.setAttribute('aria-pressed', String(st.playing));
    }

    function stop() { if (timer) clearTimeout(timer); timer = null; if (store.get().playing) store.set({playing: false}); }
    async function tick() {
      const st = store.get();
      if (!st.playing) return;
      if (!st.snapshot || st.snapshot.cutoff >= st.snapshot.steps_total) { stop(); return; }
      await goTo(st.snapshot.cutoff + 1);
      // The next step is scheduled only after the state has arrived: playback never skips evidence.
      if (store.get().playing) timer = setTimeout(tick, 1500 / Number(store.get().speed || 1));
    }
    function toggle() {
      const st = store.get();
      if (st.playing) { stop(); return; }
      if (st.snapshot && st.snapshot.cutoff >= st.snapshot.steps_total) goTo(1);
      store.set({playing: true}); timer = setTimeout(tick, 350);
    }

    range.addEventListener('input', () => {
      stop(); clearTimeout(dragTimer);
      const value = Number(range.value);
      dragTimer = setTimeout(() => goTo(value), 70);
    });
    document.getElementById('prev').addEventListener('click', () => { stop(); goTo(store.get().cutoff - 1); });
    document.getElementById('next').addEventListener('click', () => { stop(); goTo(store.get().cutoff + 1); });
    play.addEventListener('click', toggle);
    speed.addEventListener('change', () => store.set({speed: Number(speed.value)}));
    track.addEventListener('click', e => {
      const box = track.getBoundingClientRect(), n = store.get().stepsTotal;
      const f = (e.clientX - box.left) / box.width * W;
      stop(); goTo(Math.max(1, Math.min(n, Math.round((f - PAD) / (W - 2 * PAD) * (n - 1)) + 1)));
    });
    return {render, stop, toggle};
  }
  L.timeline = {create};
})(window.Living);
