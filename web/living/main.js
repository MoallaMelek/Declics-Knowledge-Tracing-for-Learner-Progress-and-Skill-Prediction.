'use strict';
// Wiring: one store, one client, four synchronised views.
(function (L) {
  const A = L.adapters, $ = id => document.getElementById(id);
  const store = L.store.createStore(L.store.initial());
  const client = L.api.createClient();
  const status = (text) => { $('status').textContent = text; };

  const constellation = L.constellation.create({store});
  const timeline = L.timeline.create({store, goTo});
  const fingerprint = L.fingerprint.create({store, api: client, constellation});
  const observatory = L.observatory.create({store, client, onReveal: reveal, onInspect: inspect});
  L.app = {store, client, goTo};   // exposed for the Node harness and debugging; holds no hidden outcome

  // One render per frame; the timer fallback keeps background tabs (where frames pause) consistent.
  let scheduled = false;
  store.subscribe(() => {
    if (scheduled) return; scheduled = true;
    const run = () => { if (!scheduled) return; scheduled = false; renderAll(); };
    requestAnimationFrame(run); setTimeout(run, 150);
  });
  function renderAll() {
    const st = store.get(); if (!st.snapshot) return;
    timeline.render(st); constellation.render(st); fingerprint.render(st); observatory.render(st);
  }

  function want() { const st = store.get(); return {source: st.source, learner: st.learner}; }

  async function goTo(cutoff) {
    const st = store.get(); if (!st.stepsTotal) return;
    const c = Math.max(1, Math.min(st.stepsTotal, Math.round(cutoff)));
    const request = {...want(), cutoff: c};
    store.set({cutoff: c});
    if (!client.cached(request.source, request.learner, c)) status(`Chargement du pas ${c}…`);
    try {
      const snap = await client.state(request.source, request.learner, c);
      const now = store.get();
      // Stale-response guard: a slower answer for an older cutoff or learner never reaches the views.
      if (!A.sameRequest(snap, {source: now.source, learner: now.learner, cutoff: now.cutoff})) return;
      A.assertCausal(snap);
      const keep = now.selected !== null && snap.skill_states.states.some(x => x.concept === now.selected);
      store.set({snapshot: snap, selected: keep ? now.selected : null, error: null});
      const unit = A.stepName(snap.source);
      status(`${now.learners.find(l => l.token === snap.learner)?.label || 'Parcours'} · ${unit} ${snap.cutoff} sur ${snap.steps_total}. `
        + (snap.target ? `Le résultat du pas ${snap.cutoff + 1} et des suivants n’a pas été transmis à cette page.` : 'Tout le parcours enregistré est observé.'));
      syncUrl();
    } catch (e) {
      if (e.name === 'AbortError') return;
      if (store.get().cutoff === c) { status(e.message); store.set({error: e.message, playing: false}); }
    }
  }

  let inspecting = null;
  function inspect() {
    const st = store.get(), snap = st.snapshot; if (!snap) return;
    const key = `${snap.source}|${snap.learner}`, tag = `${key}|${snap.cutoff}`;
    if ((st.inspection && st.inspection.key === key && st.inspection.cutoff === snap.cutoff) || inspecting === tag) return;
    inspecting = tag;
    client.inspect(snap.source, snap.learner, snap.cutoff)
      .then(payload => ({...payload, key}))
      .catch(e => ({key, cutoff: snap.cutoff, error: e.message}))
      .then(value => {
        if (inspecting === tag) inspecting = null;
        const now = store.get().snapshot;
        if (now && `${now.source}|${now.learner}` === key && now.cutoff === snap.cutoff) store.set({inspection: value});
      });
  }

  async function reveal() {
    const snap = store.get().snapshot; if (!snap || !snap.reveal_receipt) return;
    status('Demande du résultat réel au serveur, avec le reçu de la prévision…');
    try {
      let rv;
      try { rv = await client.reveal(snap.reveal_receipt); }
      catch (e) {
        if (e.status !== 409) throw e;
        // Receipt expired while the cutoff sat in the cache: fetch the same cutoff again and retry once.
        const fresh = A.assertCausal(await client.state(snap.source, snap.learner, snap.cutoff, {fresh: true}));
        if (!fresh.reveal_receipt || JSON.stringify(fresh.forecast.predictions) !== JSON.stringify(snap.forecast.predictions)) throw e;
        rv = await client.reveal(fresh.reveal_receipt);
      }
      const now = store.get().snapshot;
      if (!now || A.revealKey(now) !== A.revealKey(snap)) return;
      if (!A.acceptReveal(snap, rv)) throw new Error('Révélation incohérente avec la prévision affichée ; elle est ignorée.');
      store.set({reveals: {...store.get().reveals, [A.revealKey(snap)]: rv}});
      status(`Résultat du pas ${snap.cutoff + 1} révélé après la prévision. Les erreurs restent visibles.`);
    } catch (e) { status(e.message); store.set({}); }
  }

  function syncUrl() {
    const st = store.get();
    try { window.history.replaceState(null, '', `?source=${st.source}&learner=${st.learner}&cutoff=${st.cutoff}${location.hash}`); } catch (e) { /* file:// or sandbox */ }
  }

  async function load(source, learner, cutoff) {
    timeline.stop();
    store.set({source, learner: learner || '01', snapshot: null, selected: null, compareCutoff: null, compareSnapshot: null,
               inspection: null, stepsTotal: 0, playing: false, error: null});
    constellation.reset();
    status('Chargement des parcours de test…');
    try {
      const data = await client.learners(source);
      if (store.get().source !== source) return;
      const tokens = data.learners.map(l => l.token);
      const token = tokens.includes(learner) ? learner : tokens[0];
      const unit = A.stepName(source);
      $('learner').replaceChildren(...data.learners.map(l => L.dom.h('option', {value: l.token, text: `${l.label} · ${l.steps} ${unit}s`})));
      $('learner').value = token;
      $('selection-note').textContent = `${data.selection} ${data.counts.shown} affichés sur ${data.counts.eligible} éligibles (${data.counts.test_learners} au test). ${data.replay}`;
      const total = data.learners.find(l => l.token === token).steps;
      store.set({learners: data.learners, learner: token, stepsTotal: total, provenance: data.provenance, counts: data.counts, selection: data.selection});
      constellation.legend(source);
      for (const id of ['stage', 'fingerprint', 'observatory', 'dock']) $(id).hidden = false;
      document.body.classList.add('has-dock');
      $('sky-sub').textContent = source === 'singpad'
        ? `${data.provenance.K} concepts source du vocabulaire SingPAD ; seules les étoiles observées avant le pas choisi s’allument.`
        : 'Un seul indicateur Yousician : le score agrégé de chaque jour actif.';
      await goTo(cutoff || Math.min(3, total));
      applyDeepLink();
    } catch (e) {
      status(e.status === 503 ? `${e.message} Les poids publics sont présents, mais les parcours individuels de test restent privés : voir docs/PHASE7_REPRODUCTION.md.` : e.message);
      for (const id of ['stage', 'fingerprint', 'observatory', 'dock']) $(id).hidden = true;
    }
  }

  $('source').addEventListener('change', () => load($('source').value, '01'));
  $('learner').addEventListener('change', () => {
    const st = store.get(), l = st.learners.find(x => x.token === $('learner').value); if (!l) return;
    timeline.stop(); constellation.reset();
    store.set({learner: l.token, stepsTotal: l.steps, snapshot: null, selected: null, compareCutoff: null, compareSnapshot: null, inspection: null});
    goTo(Math.min(3, l.steps));
  });
  $('research-mode').addEventListener('change', e => store.set({research: e.target.checked}));

  document.addEventListener('keydown', e => {
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
    const t = e.target, tag = t.tagName;
    if (['INPUT', 'SELECT', 'TEXTAREA', 'BUTTON', 'SUMMARY'].includes(tag) || t.isContentEditable || t.closest('#sky')) return;
    const st = store.get(); if (!st.snapshot) return;
    if (e.key === 'ArrowRight') { timeline.stop(); goTo(st.cutoff + 1); e.preventDefault(); }
    else if (e.key === 'ArrowLeft') { timeline.stop(); goTo(st.cutoff - 1); e.preventDefault(); }
    else if (e.key === 'Home') { timeline.stop(); goTo(1); e.preventDefault(); }
    else if (e.key === 'End') { timeline.stop(); goTo(st.stepsTotal); e.preventDefault(); }
    else if (e.key === ' ') { timeline.toggle(); e.preventDefault(); }
  });

  // Demo links (?stage=gru&concept=3&research=1#observatory) open a prepared view once. A reveal is never automatic.
  let deepLinkDone = false;
  const initial = new URLSearchParams(location.search);   // read before syncUrl() rewrites the address
  function applyDeepLink() {
    if (deepLinkDone) return; deepLinkDone = true;
    const p = initial, st = store.get();
    if (L.observatory.STAGES.some(x => x.id === p.get('stage'))) store.set({stage: p.get('stage')});
    if (p.get('research') === '1') { $('research-mode').checked = true; store.set({research: true}); }
    const k = Number(p.get('concept'));
    if (p.has('concept') && Number.isInteger(k) && st.snapshot && st.snapshot.skill_states.states.some(x => x.concept === k)) constellation.select(k);
    const target = location.hash && document.getElementById(location.hash.slice(1));
    if (target) requestAnimationFrame(() => requestAnimationFrame(() => target.scrollIntoView()));
  }

  const params = new URLSearchParams(location.search);
  const source = params.get('source') === 'yousician' ? 'yousician' : 'singpad';
  $('source').value = source;
  const cutoff = Number(params.get('cutoff'));
  load(source, params.get('learner') || '01', Number.isInteger(cutoff) && cutoff > 0 ? cutoff : null);
})(window.Living);
