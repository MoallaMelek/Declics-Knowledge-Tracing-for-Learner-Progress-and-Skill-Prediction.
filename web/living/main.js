'use strict';
// Wiring: one store, one client, four synchronised views.
(function (L) {
  const A = L.adapters, $ = id => document.getElementById(id);
  const store = L.store.createStore(L.store.initial());
  const client = L.api.createClient();
  const status = (text) => { $('status').textContent = text; };
  let loadEpoch = 0, viewEpoch = 0;
  function showError(e) {
    status(e.message);
    $('recovery').hidden = false;
    $('diagnostic').textContent = e.diagnostic || 'Réponse incohérente ; vérifier la version du serveur.';
    store.set({error: e.message, playing: false});
  }
  function clearError() { $('recovery').hidden = true; }

  const constellation = L.constellation.create({store});
  const timeline = L.timeline.create({store, goTo});
  const fingerprint = L.fingerprint.create({store, api: client, constellation});
  const observatory = L.observatory.create({store, client, onReveal: reveal, onInspect: inspect});
  const summary = L.summary.create({store, constellation, onReveal: reveal, onResearch: openResearch});
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
    timeline.render(st); constellation.render(st); fingerprint.render(st); summary.render(st); observatory.render(st);
    showResearch(st.research);
    syncUrl();
  }

  function want() { const st = store.get(); return {source: st.source, learner: st.learner}; }

  async function goTo(cutoff) {
    const st = store.get(); if (!st.stepsTotal) return;
    const c = Math.max(1, Math.min(st.stepsTotal, Math.round(cutoff)));
    const request = {...want(), cutoff: c};
    const cohortEpoch = loadEpoch, requestEpoch = ++viewEpoch;
    clearError();
    store.set({cutoff: c, error: null});
    if (!client.cached(request.source, request.learner, c)) status(`Chargement du pas ${c}…`);
    try {
      const snap = await client.state(request.source, request.learner, c);
      const now = store.get();
      if (cohortEpoch !== loadEpoch || requestEpoch !== viewEpoch) return;
      // Stale-response guard: a slower answer for an older cutoff or learner never reaches the views.
      if (!A.sameRequest(snap, {source: now.source, learner: now.learner, cutoff: now.cutoff})) return;
      A.assertCausal(snap);
      if (snap.identity.generation !== now.provenance.generation) throw new Error('Le modèle ou les données ont changé. Rechargez ce parcours.');
      const keep = now.selected !== null && snap.skill_states.states.some(x => x.concept === now.selected);
      store.set({snapshot: snap, selected: keep ? now.selected : null, error: null, inspection: null});
      clearError();
      const unit = A.stepName(snap.source);
      status(`${now.learners.find(l => l.token === snap.learner)?.label || 'Parcours'} · ${unit} ${snap.cutoff} sur ${snap.steps_total}. `
        + (snap.target ? `Le résultat de la séance ${snap.cutoff + 1} reste caché dans cette vue, même si vous l’avez déjà vu plus loin dans le rejeu.` : 'Tout le parcours enregistré est observé.'));
      syncUrl();
    } catch (e) {
      if (e.name === 'AbortError') return;
      if (cohortEpoch === loadEpoch && requestEpoch === viewEpoch) showError(e);
    }
  }

  let inspecting = null;
  function inspect() {
    const st = store.get(), snap = st.snapshot; if (!snap) return;
    const key = `${snap.source}|${snap.learner}`, epoch = viewEpoch, cohortEpoch = loadEpoch;
    const tag = `${A.identityKey(snap)}|${cohortEpoch}|${epoch}`;
    if ((st.inspection && st.inspection.key === key && st.inspection.cutoff === snap.cutoff) || inspecting === tag) return;
    inspecting = tag;
    client.inspect(snap.source, snap.learner, snap.cutoff)
      .then(payload => ({...payload, key}))
      .catch(e => ({key, cutoff: snap.cutoff, error: e.message, diagnostic: e.diagnostic, identity: snap.identity}))
      .then(value => {
        if (inspecting === tag) inspecting = null;
        const now = store.get().snapshot;
        if (cohortEpoch === loadEpoch && epoch === viewEpoch && A.sameIdentity(now, snap)
            && (value.available === false || A.sameIdentity(snap, value))) {
          store.set({inspection: value});
          if (value.error) showError({message: value.error, diagnostic: value.diagnostic});
        }
      });
  }

  async function reveal() {
    const snap = store.get().snapshot; if (!snap || !snap.reveal_receipt) return;
    const epoch = viewEpoch, cohortEpoch = loadEpoch;
    clearError();
    status('Demande du résultat réel au serveur, avec le reçu de la prévision…');
    try {
      let rv;
      try { rv = await client.reveal(snap.reveal_receipt); }
      catch (e) {
        if (e.status !== 409) throw e;
        // Receipt expired while the cutoff sat in the cache: fetch the same cutoff again and retry once.
        const fresh = A.assertCausal(await client.state(snap.source, snap.learner, snap.cutoff, {fresh: true}));
        if (!fresh.reveal_receipt || !A.sameIdentity(fresh, snap) || JSON.stringify(fresh.forecast.predictions) !== JSON.stringify(snap.forecast.predictions)) throw e;
        if (epoch !== viewEpoch || cohortEpoch !== loadEpoch) return;
        rv = await client.reveal(fresh.reveal_receipt);
      }
      const now = store.get().snapshot;
      if (epoch !== viewEpoch || cohortEpoch !== loadEpoch || !A.sameIdentity(now, snap)) return;
      if (!A.acceptReveal(snap, rv)) throw new Error('Révélation incohérente avec la prévision affichée ; elle est ignorée.');
      store.set({reveals: {...store.get().reveals, [A.revealKey(snap)]: rv}, error: null});
      clearError();
      status(`Résultat du pas ${snap.cutoff + 1} révélé après la prévision. Les erreurs restent visibles.`);
    } catch (e) { if (epoch === viewEpoch && cohortEpoch === loadEpoch) showError(e); }
  }

  function syncUrl() {
    const st = store.get();
    if (!deepLinkDone || !st.snapshot) return;
    // A failed/in-flight destination is intent, not the snapshot being displayed.
    const p = new URLSearchParams({source: st.snapshot.source, learner: st.snapshot.learner, cutoff: st.snapshot.cutoff, stage: st.stage});
    if (st.research) p.set('research', '1');
    if (st.selected !== null) p.set('concept', st.selected);
    if (st.compareCutoff) p.set('compare', st.compareCutoff);
    try { window.history.replaceState(null, '', `?${p}${location.hash}`); } catch (e) { /* file:// or sandbox */ }
  }

  async function load(source, learner, cutoff) {
    const epoch = ++loadEpoch; ++viewEpoch;
    client.forget(); inspecting = null; clearError();
    timeline.stop();
    store.set({source, learner: learner || '01', cutoff: cutoff || 3, snapshot: null, selected: null, compareCutoff: null, compareSnapshot: null,
               inspection: null, reveals: {}, stepsTotal: 0, playing: false, error: null});
    showViews(false);
    constellation.reset();
    status('Chargement des parcours de test…');
    try {
      const data = await client.learners(source);
      if (epoch !== loadEpoch) return;
      if (!data.learners.length) throw new Error('Aucun parcours compatible disponible ; consultez le diagnostic de démarrage.');
      const tokens = data.learners.map(l => l.token);
      const token = tokens.includes(learner) ? learner : tokens[0];
      const unit = A.stepName(source);
      $('learner').replaceChildren(...data.learners.map(l => L.dom.h('option', {value: l.token, text: `${l.label} · ${l.steps} ${unit}s`})));
      $('learner').value = token;
      $('selection-note').textContent = `${data.provenance.data_mode === 'synthetic_fixture' ? 'TEST SYNTHÉTIQUE D’INTÉGRATION — aucune validation sur apprenants réels. ' : ''}${data.selection} ${data.counts.shown} affichés sur ${data.counts.eligible} éligibles (${data.counts.test_learners} au test). ${data.replay}`;
      const total = data.learners.find(l => l.token === token).steps;
      store.set({learners: data.learners, learner: token, stepsTotal: total, provenance: data.provenance, counts: data.counts, selection: data.selection});
      constellation.legend(source);
      showViews(true);
      document.body.classList.add('has-dock');
      $('sky-sub').textContent = source === 'singpad'
        ? `Chaque point est un concept SingPAD déjà évalué avant la séance choisie (sur les ${data.provenance.K} du vocabulaire du modèle). Sa couleur décrit ses résultats, sa taille le nombre de notes observées. Les points s’allument au fil des séances.`
        : 'Yousician ne mesure qu’un score global par jour actif : la carte le montre au centre, entouré de chaque jour observé.';
      await goTo(cutoff || Math.min(3, total));
      if (epoch === loadEpoch) await applyDeepLink();
    } catch (e) {
      if (epoch !== loadEpoch) return;
      showError(e);
      showViews(false);
    }
  }

  $('source').addEventListener('change', () => load($('source').value, '01'));
  $('learner').addEventListener('change', () => {
    const st = store.get(), l = st.learners.find(x => x.token === $('learner').value); if (!l) return;
    ++loadEpoch; ++viewEpoch; timeline.stop(); constellation.reset();
    store.set({learner: l.token, stepsTotal: l.steps, snapshot: null, selected: null, compareCutoff: null, compareSnapshot: null, inspection: null});
    goTo(Math.min(3, l.steps));
  });
  $('retry').addEventListener('click', () => { const st = store.get(); load(st.source, st.learner, st.cutoff); });
  $('research-mode').addEventListener('change', e => store.set({research: e.target.checked}));

  // Simple view by default; the researcher view adds the computation chapter. Neither changes any data.
  const VIEWS = ['summary', 'ahead', 'chapters', 'stage', 'fingerprint', 'dock'];
  function showViews(on) {
    for (const id of VIEWS) $(id).hidden = !on;
    showResearch(on && store.get().research);
  }
  function showResearch(on) {
    const visible = !!on && !!store.get().snapshot && !$('stage').hidden;
    $('observatory').hidden = !visible;
    document.body.classList.toggle('is-research', !!on);
  }
  function openResearch() {
    $('research-mode').checked = true; store.set({research: true});
    requestAnimationFrame(() => { showResearch(true); $('observatory').scrollIntoView({behavior: L.dom.reducedMotion() ? 'auto' : 'smooth', block: 'start'}); });
  }

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
  async function applyDeepLink() {
    if (deepLinkDone) return; deepLinkDone = true;
    const p = initial, st = store.get();
    if (L.observatory.STAGES.some(x => x.id === p.get('stage'))) store.set({stage: p.get('stage')});
    if (p.get('research') === '1') { $('research-mode').checked = true; store.set({research: true}); }
    const k = Number(p.get('concept'));
    if (p.has('concept') && Number.isInteger(k) && st.snapshot && st.snapshot.skill_states.states.some(x => x.concept === k)) constellation.select(k);
    const compare = Number(p.get('compare')), epoch = loadEpoch, compareEpoch = st.comparisonEpoch;
    if (p.has('compare') && Number.isInteger(compare) && compare >= 1 && compare <= st.stepsTotal) {
      try {
        const other = A.assertCausal(await client.state(st.source, st.learner, compare));
        if (epoch === loadEpoch && compareEpoch === store.get().comparisonEpoch && other.identity.generation === store.get().snapshot?.identity.generation)
          store.set({compareCutoff: compare, compareSnapshot: other});
      } catch (e) { if (epoch === loadEpoch && e.name !== 'AbortError') showError(e); }
    }
    const target = location.hash && document.getElementById(location.hash.slice(1));
    if (target) requestAnimationFrame(() => requestAnimationFrame(() => target.scrollIntoView()));
  }

  const params = new URLSearchParams(location.search);
  const source = params.get('source') === 'yousician' ? 'yousician' : 'singpad';
  $('source').value = source;
  const cutoff = Number(params.get('cutoff'));
  load(source, params.get('learner') || '01', Number.isInteger(cutoff) && cutoff > 0 ? cutoff : null);
})(window.Living);
