'use strict';
// Feature 1 · Constellation vivante. Fixed vocabulary sky; each lit star is a concept observed before the cutoff.
(function (L) {
  const {h, s, table, tween, reducedMotion} = L.dom, A = L.adapters;
  const GOLD = '#e3c178';

  function arcPath(r, fraction) {
    const f = Math.max(0, Math.min(0.9999, fraction)), a = -Math.PI / 2 + 2 * Math.PI * f;
    return `M 0 ${-r} A ${r} ${r} 0 ${f > 0.5 ? 1 : 0} 1 ${r * Math.cos(a)} ${r * Math.sin(a)}`;
  }

  function create({store}) {
    const host = document.getElementById('sky'), inspector = document.getElementById('inspector');
    const tip = h('div', {class: 'sky-tip', role: 'presentation', hidden: true});
    const svg = s('svg', {viewBox: '-520 -520 1040 1040', class: 'sky-svg', role: 'img'});
    const world = s('g', {class: 'world'});
    const layers = {guides: s('g', {class: 'guides'}), dust: s('g', {class: 'dust'}), edges: s('g', {class: 'edges'}),
                    orbit: s('g', {class: 'orbit'}), nodes: s('g', {class: 'nodes'}), labels: s('g', {class: 'labels'})};
    svg.append(world);
    world.append(...Object.values(layers));
    host.replaceChildren(svg, tip);
    for (const r of [150, 300, 450]) layers.guides.append(s('circle', {r, class: 'guide'}));

    const nodes = new Map();
    // autoFrame: the camera follows the evidence (bounding box of the current, past-only nodes) until the user takes over.
    let view = {x: 0, y: 0, k: 1}, cancelCamera = () => {}, dustKey = null, model = null, hover = null, autoFrame = true;

    function frame(ms = 700) {
      if (!model || !model.nodes.length) return;
      const box = svg.getBoundingClientRect(); if (!box.width || !box.height) return;
      const unit = Math.min(box.width, box.height) / 1040, vw = box.width / unit, vh = box.height / unit;
      let x0, x1, y0, y1;
      if (model.K === 1) { x0 = y0 = -300; x1 = y1 = 300; }
      else {
        x0 = Math.min(...model.nodes.map(n => n.x - n.r)); x1 = Math.max(...model.nodes.map(n => n.x + n.r));
        y0 = Math.min(...model.nodes.map(n => n.y - n.r)); y1 = Math.max(...model.nodes.map(n => n.y + n.r));
      }
      const margin = 70, k = Math.max(0.85, Math.min(2.4, Math.min(vw / (x1 - x0 + 2 * margin), vh / (y1 - y0 + 2 * margin))));
      const target = {x: (x0 + x1) / 2, y: (y0 + y1) / 2, k};
      const moved = Math.abs(target.k - view.k) / view.k > 0.06 || Math.hypot(target.x - view.x, target.y - view.y) > 30 / view.k;
      if (moved) camera(target, ms);
    }
    const manual = () => { autoFrame = false; };

    function applyView() {
      world.setAttribute('transform', `scale(${view.k}) translate(${-view.x} ${-view.y})`);
      svg.style.setProperty('--k', view.k.toFixed(3)); svg.classList.toggle('zoomed', view.k >= 2.2);
    }
    function camera(target, ms = 650) {
      cancelCamera(); const from = {...view};
      cancelCamera = tween(reducedMotion() ? 0 : ms, t => {
        view = {x: from.x + (target.x - from.x) * t, y: from.y + (target.y - from.y) * t, k: from.k + (target.k - from.k) * t};
        applyView();
      });
    }
    const clampK = k => Math.max(0.8, Math.min(5, k));

    function dust(K) {
      if (dustKey === K) return; dustKey = K; layers.dust.replaceChildren();
      if (K === 1) return;
      for (let k = 0; k < K; k++) { const p = A.slot(k, K); layers.dust.append(s('circle', {cx: p.x.toFixed(1), cy: p.y.toFixed(1), r: 1.9, class: 'dust-dot'})); }
    }

    function nodeView(n) {
      const g = s('g', {class: 'node', 'data-k': n.k});
      const glow = s('circle', {r: 0, class: 'node-glow'});
      const halo = s('circle', {r: 0, class: 'node-halo'});
      const ring = s('circle', {r: 0, class: 'node-target'});
      const arc = s('path', {class: 'node-pred'});
      const obs = s('path', {class: 'node-obs'});
      const core = s('circle', {r: 0, class: 'node-core'});
      const sel = s('circle', {r: 0, class: 'node-sel'});
      const title = s('title', {});
      g.append(glow, halo, ring, arc, obs, core, sel, title);
      g.setAttribute('transform', `translate(${n.x.toFixed(1)} ${n.y.toFixed(1)})`);
      layers.nodes.append(g);
      const label = s('text', {x: n.x.toFixed(1), y: (n.y - 14).toFixed(1), class: 'node-label', 'text-anchor': 'middle'});
      layers.labels.append(label);
      return {g, glow, halo, ring, arc, obs, core, sel, title, label, r: 0, cancel: () => {}};
    }

    function render(st) {
      const snap = st.snapshot; if (!snap) return;
      model = A.constellation(snap); dust(model.K);
      const reveal = st.reveals[A.revealKey(snap)] || null;
      const observedBy = reveal ? Object.fromEntries(reveal.comparison.map(c => [c.concept, c.observed])) : {};
      const selected = st.selected;
      svg.setAttribute('aria-label', `Constellation au ${A.stepName(snap.source)} ${snap.cutoff} : ${model.nodes.filter(n => n.observed).length} concept(s) observé(s), ${snap.target ? snap.target.concepts.length : 0} évalué(s) au prochain pas. Tableau équivalent disponible sous la figure.`);

      // Edges: co-evaluation in the same past step. Repeated pairs (2+ steps) by default, every pair of the selected concept.
      layers.edges.replaceChildren();
      const pos = new Map(model.nodes.map(n => [n.k, n]));
      const linked = new Set();
      for (const e of model.edges) {
        const a = pos.get(e.a), b = pos.get(e.b); if (!a || !b) continue;
        const on = selected !== null && (e.a === selected || e.b === selected);
        if (on) { linked.add(e.a); linked.add(e.b); }
        if (!on && e.n < 2) continue;
        layers.edges.append(s('line', {x1: a.x.toFixed(1), y1: a.y.toFixed(1), x2: b.x.toFixed(1), y2: b.y.toFixed(1),
          class: on ? 'edge on' : 'edge', style: `stroke-opacity:${on ? Math.min(0.85, 0.25 + 0.1 * e.n) : Math.min(0.22, 0.03 + 0.025 * e.n)}`}));
      }
      svg.classList.toggle('focusing', selected !== null);

      // Yousician: one source indicator, with its day orbit (one dot per observed day).
      layers.orbit.replaceChildren();
      if (model.K === 1) {
        const n = snap.steps_total;
        for (let i = 0; i < n; i++) {
          const a = -Math.PI / 2 + 2 * Math.PI * i / n, x = 250 * Math.cos(a), y = 250 * Math.sin(a);
          if (i < snap.cutoff) layers.orbit.append(s('circle', {cx: x, cy: y, r: 11, class: 'day', style: `fill:${L.dom.ramp(snap.past[i].score)}`}, s('title', {text: `Jour actif ${i + 1} : ${A.score(snap.source, snap.past[i].score)}`})));
          else if (i === snap.cutoff) layers.orbit.append(s('circle', {cx: x, cy: y, r: 13, class: 'day next'}));
          else layers.orbit.append(s('circle', {cx: x, cy: y, r: 3, class: 'day future'}));
        }
        layers.orbit.prepend(s('circle', {r: 250, class: 'guide orbit-line'}));
      }

      const seen = new Set();
      for (const n of model.nodes) {
        seen.add(n.k);
        let v = nodes.get(n.k); const created = !v;
        if (!v) { v = nodeView(n); nodes.set(n.k, v); }
        const color = n.meta.color, hollow = !!n.meta.hollow;
        v.core.setAttribute('class', `node-core${hollow ? ' hollow' : ''}`);
        // Insufficient evidence stays visible but faint (translucent, dashed); never-observed target concepts stay empty.
        const faint = n.state === 'insufficient_evidence';
        v.core.style.fill = hollow && !faint ? 'transparent' : color; v.core.style.fillOpacity = faint ? 0.38 : 1; v.core.style.stroke = color;
        v.glow.style.fill = color; v.glow.style.opacity = faint || hollow ? 0 : 0.16;
        v.g.classList.toggle('dim', selected !== null && selected !== n.k && !linked.has(n.k));
        v.g.classList.toggle('is-selected', selected === n.k);
        const from = v.r, to = n.r; v.cancel();
        v.cancel = tween(created ? 700 : 450, t => {
          const r = from + (to - from) * t; v.r = r;
          v.core.setAttribute('r', r.toFixed(2)); v.glow.setAttribute('r', (r * 1.9 + 4).toFixed(2));
          v.halo.setAttribute('r', (r + 7).toFixed(2)); v.ring.setAttribute('r', (r + 5).toFixed(2));
          v.sel.setAttribute('r', (r + 11).toFixed(2));
          v.arc.setAttribute('d', n.prediction !== null ? arcPath(r + 5, n.prediction) : '');
          v.obs.setAttribute('d', observedBy[n.k] !== undefined ? arcPath(r + 9, observedBy[n.k]) : '');
        });
        v.halo.classList.toggle('fresh', n.fresh); if (n.fresh) v.halo.style.stroke = color;
        v.ring.classList.toggle('on', n.target);
        v.arc.style.display = n.prediction !== null ? '' : 'none';
        v.obs.style.display = observedBy[n.k] !== undefined ? '' : 'none';
        v.label.textContent = model.K === 1 ? 'Score global du jour' : `C${n.k}`;
        v.label.classList.toggle('show', selected === n.k || hover === n.k || model.K === 1);
        v.label.setAttribute('y', String(model.K === 1 ? n.y + n.r + 34 : n.y - n.r - 12));
        v.title.textContent = `${A.conceptName(snap.source, n.k)} · ${n.meta.label}${n.observed ? ` · ${n.groups} ${A.stepName(snap.source)}(s)` : ''}`;
      }
      for (const [k, v] of nodes) if (!seen.has(k)) { v.cancel(); v.g.remove(); v.label.remove(); nodes.delete(k); }
      renderTable(snap); renderInspector(st);
      if (autoFrame && selected === null) frame();
    }

    function select(k, opts = {}) {
      const st = store.get();
      if (k === null) { store.set({selected: null}); if (opts.reset !== false) { autoFrame = true; frame(); } return; }
      store.set({selected: k});
      const n = model && model.nodes.find(x => x.k === k);
      if (n && opts.camera !== false && model.K > 1) camera({x: n.x, y: n.y, k: Math.min(3, Math.max(view.k * 1.15, 1.6))});
      const announce = document.getElementById('sr-announce');
      if (n) announce.textContent = `${A.conceptName(st.snapshot.source, k)} : ${n.meta.label}.`;
    }

    // Pointer: click selects, drag pans, ctrl/cmd + wheel zooms (plain wheel keeps scrolling the page).
    let drag = null;
    svg.addEventListener('pointerdown', e => {
      // Pointer capture retargets pointerup to the SVG, so the star under the press is remembered here.
      const node = e.target.closest && e.target.closest('.node');
      drag = {x: e.clientX, y: e.clientY, vx: view.x, vy: view.y, moved: false, k: node ? Number(node.dataset.k) : null};
      svg.setPointerCapture(e.pointerId);
    });
    svg.addEventListener('pointermove', e => {
      if (drag) {
        const box = svg.getBoundingClientRect(), scale = 1040 / Math.min(box.width, box.height) / view.k;
        const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
        if (drag.moved) { manual(); cancelCamera(); view.x = drag.vx - dx * scale; view.y = drag.vy - dy * scale; applyView(); }
        return;
      }
      const g = e.target.closest && e.target.closest('.node');
      const k = g ? Number(g.dataset.k) : null;
      if (k !== hover) setHover(k);
      if (k !== null) showTip(k, e); else tip.hidden = true;
    });
    svg.addEventListener('pointerleave', () => { tip.hidden = true; setHover(null); });
    function setHover(k) {
      const sel = store.get().selected;
      for (const key of [hover, k]) { const v = nodes.get(key); if (v && model && model.K > 1) v.label.classList.toggle('show', key === k || key === sel); }
      hover = k;
    }
    svg.addEventListener('pointerup', e => {
      if (drag && !drag.moved) {
        if (drag.k !== null) select(drag.k); else if (store.get().selected !== null) select(null, {reset: false});
      }
      drag = null;
    });
    svg.addEventListener('dblclick', e => { e.preventDefault(); manual(); camera({...view, k: clampK(view.k * 1.6)}, 300); });
    svg.addEventListener('wheel', e => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault(); manual(); cancelCamera(); view.k = clampK(view.k * (e.deltaY < 0 ? 1.15 : 1 / 1.15)); applyView();
    }, {passive: false});
    document.getElementById('zoom-in').addEventListener('click', () => { manual(); camera({...view, k: clampK(view.k * 1.4)}, 300); });
    document.getElementById('zoom-out').addEventListener('click', () => { manual(); camera({...view, k: clampK(view.k / 1.4)}, 300); });
    document.getElementById('zoom-reset').addEventListener('click', () => { autoFrame = true; frame(500); });

    function showTip(k, e) {
      const n = model.nodes.find(x => x.k === k); if (!n) return;
      const snap = store.get().snapshot, box = host.getBoundingClientRect();
      L.dom.put(tip, h('strong', {text: A.conceptName(snap.source, k)}), h('span', {text: n.meta.label}),
        h('span', {text: n.observed ? `${n.groups} ${A.stepName(snap.source)}(s) · ${snap.source === 'singpad' ? `${A.num(n.notes)} notes · ` : ''}récent ${A.score(snap.source, n.recent)}` : 'Aucune observation avant ce pas'}),
        n.prediction !== null ? h('span', {class: 'gold', text: `Prévision du réseau : ${A.forecast(snap.source, n.prediction)}`}) : null);
      tip.hidden = false;
      const x = Math.min(box.width - 220, e.clientX - box.left + 14), y = Math.max(8, e.clientY - box.top - 10);
      tip.style.transform = `translate(${x}px, ${y}px)`;
    }

    host.addEventListener('keydown', e => {
      if (!model) return;
      const st = store.get(), list = model.nodes;
      if (e.key === 'Escape') { select(null); e.preventDefault(); return; }
      if (e.key === '+' || e.key === '=') { manual(); camera({...view, k: clampK(view.k * 1.4)}, 250); e.preventDefault(); return; }
      if (e.key === '-') { manual(); camera({...view, k: clampK(view.k / 1.4)}, 250); e.preventDefault(); return; }
      if (e.key === '0') { autoFrame = true; frame(400); e.preventDefault(); return; }
      if (e.key === 'Enter' || e.key === ' ') {
        if (st.selected === null && list.length) select(list[0].k);
        else inspector.focus();
        e.preventDefault(); return;
      }
      const dirs = {ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]};
      if (!dirs[e.key]) return;
      e.preventDefault(); e.stopPropagation();
      const cur = list.find(n => n.k === st.selected) || {x: 0, y: 0, k: null};
      const [dx, dy] = dirs[e.key];
      let best = null, bestScore = Infinity;
      for (const n of list) {
        if (n.k === cur.k) continue;
        const vx = n.x - cur.x, vy = n.y - cur.y, along = vx * dx + vy * dy;
        if (along <= 0) continue;
        const across = Math.abs(vx * dy - vy * dx), score = along + 2 * across;
        if (score < bestScore) { bestScore = score; best = n; }
      }
      if (best) select(best.k);
    });

    function renderTable(snap) {
      const rows = model.nodes.map(n => [A.conceptName(snap.source, n.k), n.meta.label, n.groups, snap.source === 'singpad' ? A.num(n.notes) : '—',
        A.score(snap.source, n.historical), A.score(snap.source, n.recent), n.target ? 'oui' : 'non', n.prediction !== null ? A.forecast(snap.source, n.prediction) : '—']);
      document.getElementById('sky-table').replaceChildren(table(['Concept', 'État descriptif', 'Pas évalués', 'Notes', 'Réussite passée', 'Récente', 'Évalué au prochain pas', 'Prévision du réseau'], rows));
    }

    function sparkline(snap, k) {
      const series = A.conceptSeries(snap, k), n = Math.max(2, snap.cutoff + 1), W = 300, H = 92, x = i => 10 + i / (n - 1) * (W - 20), y = v => 12 + (1 - v) * (H - 30);
      const g = s('svg', {viewBox: `0 0 ${W} ${H}`, class: 'spark', role: 'img',
        'aria-label': `${series.observed.length} résultat(s) observé(s) pour ce concept ; ${series.forecasts.length} prévision(s) antérieure(s) évaluée(s).`});
      for (const v of [0, 0.65, 1]) g.append(s('line', {x1: 10, x2: W - 10, y1: y(v), y2: y(v), class: v === 0.65 ? 'spark-th' : 'spark-grid'}));
      g.append(s('text', {x: 12, y: y(0.65) + 11, class: 'spark-txt', text: 'seuil descriptif 65 %'}));
      if (series.observed.length > 1) g.append(s('polyline', {points: series.observed.map(o => `${x(o.index)},${y(o.value)}`).join(' '), class: 'spark-line'}));
      for (const o of series.observed) g.append(s('circle', {cx: x(o.index), cy: y(o.value), r: 3.4, class: 'spark-dot', style: `fill:${L.dom.ramp(o.value)}`}));
      for (const f of series.forecasts) g.append(s('rect', {x: x(f.index) - 3, y: y(f.value) - 3, width: 6, height: 6, class: 'spark-pred', transform: `rotate(45 ${x(f.index)} ${y(f.value)})`}));
      if (series.next) g.append(s('circle', {cx: x(series.next.index), cy: y(series.next.value), r: 4.5, class: 'spark-next'}));
      g.append(s('line', {x1: x(snap.cutoff - 1), x2: x(snap.cutoff - 1), y1: 6, y2: H - 16, class: 'spark-now'}));
      g.append(s('text', {x: 10, y: H - 3, class: 'spark-txt', text: 'pas 1'}), s('text', {x: x(snap.cutoff - 1), y: H - 3, 'text-anchor': 'middle', class: 'spark-txt', text: `pas ${snap.cutoff}`}));
      return g;
    }

    function stat(label, value) { return h('div', {class: 'stat'}, h('span', {text: label}), h('strong', {text: value})); }

    function renderInspector(st) {
      const snap = st.snapshot, k = st.selected;
      if (k === null || !model.nodes.some(n => n.k === k)) { L.dom.put(inspector, ...overview(st)); return; }
      const n = model.nodes.find(x => x.k === k), state = A.stateIndex(snap)[k], o = state.observation, singpad = snap.source === 'singpad';
      const reveal = st.reveals[A.revealKey(snap)], revealed = reveal && reveal.comparison.find(c => c.concept === k);
      const recs = snap.recommendation.suggestions.filter(r => r.concepts.includes(k));
      const nb = A.neighbours(snap, k).slice(0, 8);
      L.dom.put(inspector,
        h('div', {class: 'insp-head'},
          h('button', {type: 'button', class: 'btn btn-quiet back', text: 'Revenir à la vue d’ensemble', onclick: () => select(null)}),
          h('h2', {id: 'inspector-title', text: A.conceptName(snap.source, k)}),
          h('p', {class: 'chip', style: `--c:${n.meta.color}`, text: n.meta.label})),
        h('p', {class: 'insp-text', text: state.interpretation}),
        !n.sufficient && n.observed ? h('p', {class: 'warn', text: `Preuves insuffisantes : ${o.groups_evaluated} ${A.stepName(snap.source)}(s)${singpad ? `, ${A.num(o.evaluated_weight)} notes` : ''}. Il faut au moins 3 pas${singpad ? ' et 10 notes' : ''} avant de qualifier une régularité.`}) : null,
        !n.observed ? h('p', {class: 'warn', text: 'Ce concept n’a encore aucun résultat avant ce pas : il apparaît seulement parce qu’il sera évalué au prochain pas.'}) : null,
        h('div', {class: 'stats'},
          stat(`${A.stepName(snap.source)}s évalués`, A.num(o.groups_evaluated)),
          singpad ? stat('Notes observées', A.num(o.evaluated_weight || 0)) : null,
          stat(singpad ? 'Réussite passée' : 'Score moyen passé', A.score(snap.source, o.historical_score)),
          stat('3 dernières séances', A.score(snap.source, o.recent_score)),
          stat('Évolution', o.recent_minus_prior === null || o.recent_minus_prior === undefined ? 'insuffisant' : A.points(o.recent_minus_prior)),
          stat('Pas sans mesure', A.num(o.groups_without_concept))),
        n.observed ? h('figure', {class: 'spark-fig'}, sparkline(snap, k),
          h('figcaption', {class: 'fine', text: 'Points : résultats observés · losanges dorés : prévisions faites plus tôt, déjà évaluées · cercle doré : prévision pour le prochain pas.'})) : null,
        n.target ? h('div', {class: 'insp-pred'},
          h('h3', {text: 'Au prochain pas'}),
          n.prediction !== null
            ? h('p', {}, 'Le réseau prévoit ', h('strong', {class: 'gold', text: A.forecast(snap.source, n.prediction)}), singpad ? ' de réussite pour une note de ce concept.' : ' comme score du prochain jour actif.')
            : h('p', {text: snap.forecast ? A.reason(snap.forecast.reason) : 'Aucune prévision.'}),
          revealed ? h('p', {}, 'Observé après révélation : ', h('strong', {text: A.score(snap.source, revealed.observed)}), `${singpad ? ` sur ${A.num(revealed.notes)} note(s)` : ''} · écart ${singpad ? A.points(revealed.prediction - revealed.observed) : `${A.num(100 * Math.abs(revealed.prediction - revealed.observed), 1)} points sur 100`}`) : null,
          h('p', {class: 'fine', text: singpad ? 'Probabilité de réussite d’une note, pas une confiance du modèle ; incertitude individuelle non validée.' : 'Score continu sur 100, pas une probabilité ; incertitude individuelle non validée.'})) : null,
        nb.length ? h('div', {class: 'insp-nb'}, h('h3', {text: 'Évalués dans les mêmes pas'}),
          h('p', {class: 'fine', text: 'Lien observé : les deux concepts apparaissent dans un même enregistrement passé. Ce n’est pas une relation pédagogique.'}),
          h('div', {class: 'nb-list'}, nb.map(x => h('button', {type: 'button', class: 'nb', onclick: () => select(x.k), text: `C${x.k} · ${x.n}×`})))) : null,
        recs.length ? h('div', {class: 'insp-rec'}, h('h3', {text: 'Piste de pratique'}),
          recs.map(r => h('p', {}, `Reprendre l’exercice source ${r.exercise} (${r.exercise_evidence_groups} pas observé(s)). `, h('span', {class: 'fine', text: r.caveat})))) : null);
    }

    function overview(st) {
      const snap = st.snapshot, counts = {};
      for (const n of model.nodes) if (n.observed) counts[n.state] = (counts[n.state] || 0) + 1;
      const f = snap.forecast, preds = f && f.predictions ? Object.values(f.predictions) : null;
      const rec = snap.recommendation;
      return [
        h('h2', {id: 'inspector-title', text: 'Lire un concept'}),
        h('p', {class: 'insp-text', text: snap.source === 'singpad'
          ? `${model.nodes.filter(n => n.observed).length} concepts ont été évalués dans les ${snap.cutoff} groupe(s) observé(s). Choisissez un point sur la carte pour lire son histoire : ses résultats séance par séance, et la prévision s’il est évalué au prochain groupe.`
          : `Un seul indicateur existe pour Yousician : le score agrégé du jour actif. ${snap.cutoff} jour(s) observé(s).`}),
        h('ul', {class: 'counts'}, Object.entries(A.STATES).filter(([key]) => counts[key]).map(([key, m]) =>
          h('li', {}, h('span', {class: 'dot' + (m.hollow ? ' hollow' : ''), style: `--c:${m.color}`}), h('span', {text: m.label}), h('strong', {text: counts[key]})))),
        h('div', {class: 'insp-pred'}, h('h3', {text: 'Prochain pas'}),
          !snap.target ? h('p', {text: 'Fin du parcours enregistré : aucun résultat futur n’existe dans les données.'})
            : preds ? h('p', {}, `${snap.source === 'singpad' ? `Exercice source ${snap.target.exercise} · ${snap.target.concepts.length} concepts évalués. ` : ''}${snap.source === 'singpad' ? 'Le réseau prévoit en moyenne ' : 'Le réseau prévoit '}`,
                h('strong', {class: 'gold', text: A.forecast(snap.source, A.mean(preds))}), snap.source === 'singpad' ? ' de réussite par note (moyenne simple des concepts).' : ' pour le prochain jour actif.')
            : h('p', {text: A.reason(f && f.reason)}),
          snap.target ? h('p', {class: 'fine', text: snap.target.definition}) : null,
          h('button', {type: 'button', class: 'btn btn-quiet', text: 'Lire le prochain essai', onclick: () => document.getElementById('ahead').scrollIntoView({behavior: reducedMotion() ? 'auto' : 'smooth'})})),
        h('div', {class: 'insp-rec'}, h('h3', {text: 'Piste de pratique'}),
          rec.status === 'abstained' ? h('p', {class: 'fine', text: rec.reason})
            : rec.suggestions.map(r => h('p', {}, `Reprendre l’exercice source ${r.exercise} : concepts ${r.concepts.map(c => 'C' + c).join(', ')}. `, h('span', {class: 'fine', text: r.caveat}))))
      ];
    }

    function legend(source) {
      const items = Object.entries(A.STATES).filter(([k]) => source === 'singpad' || k !== 'not_evaluated');
      L.dom.put(document.getElementById('legend'),
        h('ul', {class: 'legend-states'}, items.map(([, m]) => h('li', {}, h('span', {class: 'dot' + (m.hollow ? ' hollow' : ''), style: `--c:${m.color}`}), m.label))),
        h('ul', {class: 'legend-glyphs'},
          h('li', {}, h('span', {class: 'g-size'}), source === 'singpad' ? 'Plus grand : plus de notes observées' : 'Plus grand : plus de jours observés'),
          h('li', {}, h('span', {class: 'g-gold'}), 'Anneau ocre pointillé : évalué à la prochaine séance ; l’arc plein donne la prévision'),
          h('li', {}, h('span', {class: 'g-fresh'}), 'Halo : observé à la dernière séance'),
          source === 'singpad' ? h('li', {}, h('span', {class: 'g-edge'}), 'Trait : évalués ensemble dans au moins deux séances (tous les liens du concept choisi)') : null,
          source === 'singpad' ? h('li', {}, h('span', {class: 'g-dust'}), 'Petit point gris : concept du vocabulaire pas encore observé') : null),
        h('p', {class: 'fine', text: source === 'singpad'
          ? 'La position d’un point dépend seulement de son numéro dans SingPAD et ne bouge jamais : elle n’a pas de sens musical, et la distance entre deux points ne veut rien dire. Les couleurs décrivent des résultats observés (règle source-skill-state-v1), pas une maîtrise.'
          : 'Yousician ne fournit qu’un score agrégé par jour actif : pas de concepts séparés, donc pas de liens. L’orbite montre chaque jour observé.'}));
      host.setAttribute('aria-label', source === 'singpad' ? 'Constellation des concepts source SingPAD' : 'Indicateur Yousician et ses jours actifs');
    }

    applyView();
    return {render, legend, select, reset: () => { for (const v of nodes.values()) { v.cancel(); v.g.remove(); v.label.remove(); } nodes.clear(); dustKey = null; autoFrame = true; camera({x: 0, y: 0, k: 1}, 0); }};
  }
  L.constellation = {create};
})(window.Living);
