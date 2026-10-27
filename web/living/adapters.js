'use strict';
// Pure presentation adapters for the Living Learner page. No DOM, no network: testable in Node.
// They only reshape /api/v7/o08/living payloads; every number traces back to a server field.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else (root.Living = root.Living || {}).adapters = api;
})(typeof self !== 'undefined' ? self : this, function () {

  // Descriptive states from policy source-skill-state-v1 (axis7/skill_states.py). Order = legend order.
  const STATES = {
    consistently_strong_observed_performance: {label: 'Résultats régulièrement élevés', short: 'Élevés', color: '#1E7A50'},
    improving_observed_performance: {label: 'Amélioration observée', short: 'En hausse', color: '#237F86'},
    observed_without_clear_pattern: {label: 'Pas de motif net', short: 'Sans motif', color: '#7C879A'},
    inconsistent_observed_performance: {label: 'Résultats variables', short: 'Variables', color: '#6A55AE'},
    declining_observed_performance: {label: 'Baisse observée', short: 'En baisse', color: '#B45A12'},
    repeatedly_weak_observed_performance: {label: 'Résultats faibles répétés', short: 'Faibles répétés', color: '#A3304E'},
    insufficient_evidence: {label: 'Observations insuffisantes', short: 'Insuffisant', color: '#6F7B8E', hollow: true},
    not_evaluated: {label: 'Pas encore observé', short: 'Non observé', color: '#808A9A', hollow: true}
  };
  const SUFFICIENT = s => s && s !== 'insufficient_evidence' && s !== 'not_evaluated';
  const FLAGGED = new Set(['repeatedly_weak_observed_performance', 'declining_observed_performance']);

  const nf = (digits) => new Intl.NumberFormat('fr-FR', {minimumFractionDigits: digits, maximumFractionDigits: digits});
  const pct = (v, d = 1) => v === null || v === undefined || !isFinite(v) ? '—' : `${nf(d).format(100 * v)} %`;
  const num = (v, d = 0) => v === null || v === undefined || !isFinite(v) ? '—' : nf(d).format(v);
  const points = (v, d = 1) => v === null || v === undefined || !isFinite(v) ? '—' : `${v > 0 ? '+' : v < 0 ? '−' : ''}${nf(d).format(Math.abs(100 * v))} pts`;

  // Observed values on the scale of their source: SingPAD a share of notes (%), Yousician a continuous score (/ 100).
  const score = (source, v, d = 1) => v === null || v === undefined || !isFinite(v) ? '—' : source === 'singpad' ? pct(v, d) : `${nf(d).format(100 * v)} / 100`;
  const forecast = (source, v) => v === null || v === undefined || !isFinite(v) ? '—' : source === 'singpad' ? pct(v) : `${nf(1).format(100 * v)} / 100`;
  function conceptName(source, k) { return source === 'singpad' ? `Concept source ${k}` : 'Score global du jour'; }
  function stepName(source) { return source === 'singpad' ? 'groupe' : 'jour actif'; }

  // Deterministic vocabulary-only layout: depends on (k, K), never on a learner, so it cannot encode the future.
  function hash01(k) {
    let h = (k + 1) * 2654435761 >>> 0;
    h ^= h >>> 15; h = Math.imul(h, 2246822519) >>> 0; h ^= h >>> 13;
    return (h >>> 0) / 4294967296;
  }
  function slot(k, K) {
    if (K === 1) return {x: 0, y: 0, angle: -Math.PI / 2};
    const angle = 2 * Math.PI * k / K - Math.PI / 2;
    const r = 150 + 300 * (0.15 + 0.85 * hash01(k));
    return {x: r * Math.cos(angle), y: r * Math.sin(angle), angle};
  }

  // Refuse payloads that would contain information from the selected cutoff onwards.
  function assertCausal(s) {
    if (!s || !identityKey(s) || s.identity.source !== s.source || s.identity.learner !== s.learner
        || s.identity.cutoff !== s.cutoff || s.identity.target_index !== (s.target ? s.cutoff : null)
        || s.identity.model_id !== s.provenance?.model_id || s.identity.model_sha256 !== s.provenance?.model_sha256)
      throw new Error('Identité de prévision incompatible avec la vue reçue');
    if (!s || !Array.isArray(s.past) || s.past.length !== s.cutoff) throw new Error('Réponse incohérente avec le point de coupure');
    s.past.forEach((p, i) => { if (p.index !== i || i >= s.cutoff) throw new Error('Observation postérieure au point de coupure'); });
    (s.trail || []).forEach(t => { if (t.index >= s.cutoff) throw new Error('Prévision évaluée postérieure au point de coupure'); });
    if (s.target && s.target.index !== s.cutoff) throw new Error('Cible incohérente');
    if (s.future_outcome_included !== false) throw new Error('Résultat futur inattendu');
    return s;
  }
  function sameRequest(s, want) { return !!s && s.source === want.source && s.learner === want.learner && s.cutoff === want.cutoff; }
  const identityKey = s => {
    const fields = ['generation', 'request_id', 'model_id', 'model_sha256', 'source', 'learner', 'cutoff', 'target_index'];
    if (!s || !s.identity || fields.some(k => s.identity[k] === undefined)) return '';
    return fields.map(k => String(s.identity[k])).join('|');
  };
  const sameIdentity = (a, b) => !!identityKey(a) && identityKey(a) === identityKey(b);
  const revealKey = s => `${s.source}|${s.learner}|${s.cutoff}|${identityKey(s)}`;
  // A reveal is accepted only for the forecast it was requested for, and only if it has the predictions we showed.
  function acceptReveal(s, rv) {
    if (!rv || !sameIdentity(s, rv) || rv.model_id !== s.provenance.model_id || rv.model_sha256 !== s.provenance.model_sha256 || rv.cutoff !== s.cutoff || rv.learner !== s.learner || !s.forecast || !s.forecast.predictions) return false;
    const p = s.forecast.predictions;
    return Array.isArray(rv.comparison) && new Set(rv.comparison.map(c => String(c.concept))).size === Object.keys(p).length
      && rv.comparison.length === Object.keys(p).length && rv.comparison.every(c => Object.hasOwn(p, String(c.concept)) && Math.abs(p[String(c.concept)] - c.prediction) < 1e-9);
  }

  function stateIndex(s) { const out = {}; for (const st of s.skill_states.states) out[st.concept] = st; return out; }

  function constellation(s) {
    const states = stateIndex(s), K = s.K, last = s.past[s.past.length - 1];
    const fresh = new Set(last ? Object.keys(last.concepts).map(Number) : []);
    const target = new Set(s.target ? s.target.concepts : []);
    const predictions = (s.forecast && s.forecast.predictions) || {};
    const nodes = [];
    for (const key of Object.keys(states)) {
      const k = Number(key), st = states[k], o = st.observation, p = slot(k, K);
      const notes = o.evaluated_weight || 0;
      nodes.push({
        k, x: p.x, y: p.y, angle: p.angle, state: st.estimated_state, meta: STATES[st.estimated_state] || STATES.not_evaluated,
        sufficient: SUFFICIENT(st.estimated_state), observed: o.groups_evaluated > 0, groups: o.groups_evaluated,
        notes, historical: o.historical_score ?? null, recent: o.recent_score ?? null, trend: o.recent_minus_prior ?? null,
        fresh: fresh.has(k), target: target.has(k), prediction: predictions[String(k)] ?? null,
        r: K === 1 ? 30 + 7 * Math.sqrt(o.groups_evaluated) : (o.groups_evaluated ? 6 + 2.2 * Math.sqrt(notes) : 5)
      });
    }
    nodes.sort((a, b) => a.k - b.k);
    const edges = s.edges.map(([a, b, n]) => ({a, b, n}));
    return {K, nodes, edges, dust: K > 1 ? Array.from({length: K}, (_, k) => ({k, ...slot(k, K)})) : []};
  }

  function neighbours(s, k) {
    return s.edges.filter(([a, b]) => a === k || b === k).map(([a, b, n]) => ({k: a === k ? b : a, n}))
      .sort((x, y) => y.n - x.n || x.k - y.k);
  }

  // Per-step series for one concept, past only, plus forecasts that were made earlier for it.
  function conceptSeries(s, k) {
    const key = String(k);
    const observed = s.past.filter(p => p.concepts[key]).map(p => ({index: p.index, value: p.concepts[key][0] / p.concepts[key][1], notes: p.concepts[key][1]}));
    const forecasts = s.trail.filter(t => t.concepts && t.concepts[key]).map(t => ({index: t.index, value: t.concepts[key][0]}));
    const next = s.forecast && s.forecast.predictions && s.forecast.predictions[key] !== undefined ? {index: s.cutoff, value: s.forecast.predictions[key]} : null;
    return {observed, forecasts, next};
  }

  // Polar record: rings = observed steps; arc angle = the same slot angle as the constellation.
  function fingerprint(s) {
    const K = s.K, width = K === 1 ? 2 * Math.PI : Math.max(2 * Math.PI / K * 0.94, 0.012);
    const rings = s.past.map(p => ({index: p.index, day: p.day, arcs: Object.entries(p.concepts).map(([key, [succ, n]]) => {
      const a = slot(Number(key), K).angle;
      return {k: Number(key), a0: K === 1 ? 0 : a - width / 2, a1: K === 1 ? 2 * Math.PI : a + width / 2, value: succ / n, notes: n};
    })}));
    const target = s.target ? {index: s.target.index, arcs: s.target.concepts.map(k => {
      const a = slot(k, K).angle; return {k, a0: K === 1 ? 0 : a - width / 2, a1: K === 1 ? 2 * Math.PI : a + width / 2};
    })} : null;
    return {total: s.steps_total, rings, target, K};
  }

  function weighted(steps) {
    let succ = 0, n = 0;
    for (const p of steps) for (const [a, b] of Object.values(p.concepts)) { succ += a; n += b; }
    return n ? succ / n : null;
  }

  function indicators(s) {
    const singpad = s.source === 'singpad', past = s.past, unit = stepName(s.source);
    const states = s.skill_states.states.filter(st => st.observation.groups_evaluated > 0);
    const sufficient = states.filter(st => SUFFICIENT(st.estimated_state));
    const scores = past.map(p => p.score);
    const recent = past.slice(-3), earlier = past.slice(0, -3);
    const mean = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null;
    const sd = scores.length >= 3 ? Math.sqrt(scores.reduce((a, b) => a + (b - mean) ** 2, 0) / (scores.length - 1)) : null;
    const hist = singpad ? weighted(past) : mean;
    const rec = past.length >= 3 ? (singpad ? weighted(recent) : recent.reduce((a, p) => a + p.score, 0) / 3) : null;
    const before = earlier.length >= 3 ? (singpad ? weighted(earlier) : earlier.reduce((a, p) => a + p.score, 0) / earlier.length) : null;
    const flagged = sufficient.filter(st => FLAGGED.has(st.estimated_state));
    const notes = past.reduce((a, p) => a + p.weight, 0);
    return [
      {id: 'coverage', label: singpad ? 'Concepts observés' : 'Jours actifs observés', value: singpad ? states.length : past.length,
       display: singpad ? num(states.length) : num(past.length), unit: 'count', scale: singpad ? s.K : s.steps_total,
       definition: singpad ? `Nombre de concepts source ayant au moins une note évaluée, sur les ${s.K} du vocabulaire du modèle.` : 'Nombre de jours actifs déjà observés.',
       formula: singpad ? 'distinct(concepts des pas 1…T)' : 'T', support: `${past.length} ${unit}(s)`, sufficient: true},
      {id: 'historical', label: 'Réussite sur tout le passé', value: hist, display: score(s.source, hist), unit: 'fraction', scale: 1,
       definition: singpad ? 'Part des notes réussies, toutes notes évaluées confondues.' : 'Moyenne des scores quotidiens observés.',
       formula: singpad ? 'Σ réussites / Σ notes' : 'moyenne(scores)', support: singpad ? `${num(notes)} notes` : `${past.length} jours`, sufficient: past.length >= 1},
      {id: 'recent', label: 'Réussite récente', value: rec, display: score(s.source, rec), unit: 'fraction', scale: 1,
       definition: `Même calcul sur les trois derniers ${unit}s observés.`, formula: singpad ? 'Σ réussites / Σ notes (3 derniers)' : 'moyenne(3 derniers scores)',
       support: `${Math.min(3, past.length)} ${unit}(s)`, sufficient: past.length >= 3},
      {id: 'change', label: 'Évolution récente', value: rec !== null && before !== null ? rec - before : null,
       display: rec !== null && before !== null ? points(rec - before) : 'insuffisant', unit: 'delta', scale: 1,
       definition: 'Réussite récente moins réussite antérieure ; demande au moins trois pas antérieurs, comme la règle des états.',
       formula: 'récente − antérieure', support: `${earlier.length} ${unit}(s) antérieurs`, sufficient: earlier.length >= 3},
      {id: 'variability', label: 'Variabilité entre pas', value: sd, display: sd === null ? 'insuffisant' : `${nf(1).format(100 * sd)} pts`, unit: 'spread', scale: 0.5,
       definition: `Écart-type des résultats agrégés d’un ${unit} à l’autre.`, formula: 'écart-type(score des pas)', support: `${past.length} ${unit}(s)`, sufficient: past.length >= 3},
      {id: 'weakness', label: 'Fragilités récurrentes', value: flagged.length, display: num(flagged.length), unit: 'count', scale: Math.max(1, sufficient.length),
       definition: 'Concepts dont l’état est « faibles répétés » ou « en baisse », parmi ceux qui ont assez d’observations.',
       formula: 'compte(états signalés)', support: `${sufficient.length} concept(s) suffisamment observé(s)`, sufficient: sufficient.length > 0,
       concepts: flagged.map(st => st.concept)},
      {id: 'sufficiency', label: 'Preuves suffisantes', value: states.length ? sufficient.length / states.length : null,
       display: states.length ? `${sufficient.length} / ${states.length}` : '—', unit: 'fraction', scale: 1,
       definition: singpad ? 'Concepts avec au moins 3 groupes et 10 notes, parmi les concepts observés.' : 'Le score global dispose-t-il d’au moins 3 jours ?',
       formula: 'suffisants / observés', support: `${states.length} observé(s)`, sufficient: true}
    ];
  }

  // The served reveal receipt is base64url(JSON) + '.' + HMAC. Decoding it only displays what the server signed;
  // the signature itself cannot be checked in the browser (the key stays on the server).
  function receipt(s) {
    if (!s || typeof s.reveal_receipt !== 'string') return null;
    const [encoded, signature] = s.reveal_receipt.split('.');
    try {
      const b64 = encoded.replace(/-/g, '+').replace(/_/g, '/');
      const text = typeof atob === 'function' ? decodeURIComponent(escape(atob(b64))) : Buffer.from(b64, 'base64').toString('utf8');
      return {payload: JSON.parse(text), signature: signature || ''};
    } catch (e) { return null; }
  }

  // Plain-language reading of one cutoff, for the learner view. Every number comes from indicators() or the
  // served skill states; the lists only regroup descriptive states (policy source-skill-state-v1), never rank learners.
  const ATTENTION = ['repeatedly_weak_observed_performance', 'declining_observed_performance', 'inconsistent_observed_performance'];
  const STEADY = ['consistently_strong_observed_performance', 'improving_observed_performance'];
  function digest(s) {
    const byId = Object.fromEntries(indicators(s).map(i => [i.id, i]));
    const observed = s.skill_states.states.filter(st => st.observation.groups_evaluated > 0);
    const item = st => ({k: st.concept, state: st.estimated_state, meta: STATES[st.estimated_state] || STATES.not_evaluated,
      groups: st.observation.groups_evaluated, notes: st.observation.evaluated_weight || 0,
      recent: st.observation.recent_score ?? null, historical: st.observation.historical_score ?? null});
    const order = list => (a, b) => list.indexOf(a.state) - list.indexOf(b.state) || b.groups - a.groups || a.k - b.k;
    const attention = observed.filter(st => ATTENTION.includes(st.estimated_state)).map(item).sort(order(ATTENTION));
    const steady = observed.filter(st => STEADY.includes(st.estimated_state)).map(item).sort(order(STEADY));
    const flat = observed.filter(st => st.estimated_state === 'observed_without_clear_pattern').map(item);
    const thin = observed.filter(st => !SUFFICIENT(st.estimated_state)).length;
    return {source: s.source, unit: stepName(s.source), steps: s.cutoff, total: s.steps_total, K: s.K,
      concepts: observed.length, historical: byId.historical, recent: byId.recent, change: byId.change,
      sufficiency: byId.sufficiency, attention, steady, flat, thin, recommendation: s.recommendation};
  }

  // The next-step forecast as one sentence's worth of data. 'end' and 'abstained' never carry a number.
  function nextStep(s) {
    if (!s.target) return {status: 'end'};
    const f = s.forecast;
    if (!f || !f.predictions) return {status: 'abstained', reason: reason(f && f.reason), index: s.cutoff};
    const entries = Object.entries(f.predictions).map(([k, v]) => ({k: Number(k), value: v})).sort((a, b) => a.k - b.k);
    return {status: 'ready', index: s.cutoff, exercise: s.target.exercise, definition: s.target.definition,
      value: mean(entries.map(e => e.value)), concepts: entries, continuous: s.source !== 'singpad'};
  }

  function compareIndicators(a, b) {
    const ia = indicators(a), ib = indicators(b);
    return ia.map((x, i) => {
      // Same learner, same source, same definition: only the cutoff differs, so the units match.
      const y = ib[i];
      const delta = x.value !== null && y.value !== null && x.sufficient && y.sufficient ? y.value - x.value : null;
      return {id: x.id, label: x.label, a: x.display, b: y.display, delta, unit: x.unit};
    });
  }

  function timeline(s) {
    const slots = [];
    for (let i = 0; i < s.steps_total; i++) {
      if (i < s.cutoff) {
        const t = s.trail.find(e => e.index === i);
        // Both series give every concept equal weight; scientific note-weighted loss is unchanged.
        const observed = t && t.observed_mean !== undefined ? t.observed_mean : mean(Object.values(s.past[i].concepts).map(([a, n]) => a / n));
        slots.push({index: i, kind: 'past', score: observed, predicted: t && t.predicted_mean !== undefined ? t.predicted_mean : null});
      } else if (i === s.cutoff) slots.push({index: i, kind: 'next', predicted: s.forecast && s.forecast.predictions ? mean(Object.values(s.forecast.predictions)) : null});
      else slots.push({index: i, kind: 'future'});
    }
    return slots;
  }
  function mean(xs) { return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null; }

  function logLoss(p, successes, notes) {
    const q = Math.min(Math.max(p, 1e-7), 1 - 1e-7);
    return -(successes * Math.log(q) + (notes - successes) * Math.log(1 - q));
  }

  function calibrationBin(bins, p) {
    if (!bins || p === null || p === undefined) return null;
    const lower = Math.floor(p * 10) / 10;
    return bins.find(b => Math.abs(b.lower - lower) < 1e-9) || null;
  }

  const REASONS = {
    insufficient_atomic_history: 'Le réseau s’abstient : il faut au moins deux pas observés avant de prévoir.',
    unseen_exercise: 'Le réseau s’abstient : cet exercice n’existe pas dans le vocabulaire d’entraînement.',
    inactive_model: 'Le réseau s’abstient : ce modèle n’est pas le modèle actif.',
    incompatible_domain: 'Le réseau s’abstient : domaine incompatible avec le modèle.',
    query_exercise_required: 'Le réseau s’abstient : l’exercice demandé est inconnu.'
  };
  const reason = r => REASONS[r] || 'Le réseau s’abstient ; aucune valeur n’est inventée.';

  return {STATES, SUFFICIENT, pct, num, score, forecast, points, nf, conceptName, stepName, slot, hash01, assertCausal, sameRequest, identityKey, sameIdentity, revealKey, acceptReveal,
          stateIndex, constellation, neighbours, conceptSeries, fingerprint, indicators, compareIndicators, timeline,
          logLoss, calibrationBin, reason, mean, digest, nextStep, receipt, ATTENTION, STEADY};
});
