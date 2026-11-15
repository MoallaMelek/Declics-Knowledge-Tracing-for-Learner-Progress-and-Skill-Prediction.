'use strict';
// Feature 3 · Empreinte musicale. A polar record: one groove per observed step, one arc per evaluated concept.
(function (L) {
  const {h, s, table, ramp} = L.dom, A = L.adapters;
  const R0 = 46, R1 = 284;

  function arc(r, a0, a1) {
    if (a1 - a0 >= 2 * Math.PI - 1e-6) return `M ${r} 0 A ${r} ${r} 0 1 1 ${-r} 0 A ${r} ${r} 0 1 1 ${r} 0`;
    const large = a1 - a0 > Math.PI ? 1 : 0;
    return `M ${(r * Math.cos(a0)).toFixed(2)} ${(r * Math.sin(a0)).toFixed(2)} A ${r} ${r} 0 ${large} 1 ${(r * Math.cos(a1)).toFixed(2)} ${(r * Math.sin(a1)).toFixed(2)}`;
  }

  function draw(snap, {selected, onSelect, small, lastIndex}) {
    const fp = A.fingerprint(snap), band = (R1 - R0) / Math.max(1, fp.total), unit = A.stepName(snap.source);
    const svg = s('svg', {viewBox: '-312 -312 624 624', class: 'fp-svg' + (small ? ' small' : ''), role: 'img',
      'aria-label': `Empreinte au ${unit} ${snap.cutoff} : ${fp.rings.length} sillon(s) observé(s), ${fp.rings.reduce((a, r) => a + r.arcs.length, 0)} mesure(s) de concept.`});
    svg.append(s('circle', {r: R1 + 8, class: 'fp-disc'}));
    for (let i = 0; i < fp.total; i++) svg.append(s('circle', {r: R0 + band * (i + 0.5), class: i < snap.cutoff ? 'fp-groove' : 'fp-groove future'}));
    if (fp.K > 1) {
      // Outer rim: one tick per vocabulary concept; lit once the concept has been evaluated before the cutoff (coverage).
      const seen = new Set(fp.rings.flatMap(r => r.arcs.map(a => a.k))), rim = s('g', {class: 'fp-rim'});
      for (let k = 0; k < fp.K; k++) {
        const a = A.slot(k, fp.K).angle, r0 = R1 + 12, r1 = R1 + (seen.has(k) ? 22 : 16);
        rim.append(s('line', {x1: (r0 * Math.cos(a)).toFixed(1), y1: (r0 * Math.sin(a)).toFixed(1), x2: (r1 * Math.cos(a)).toFixed(1), y2: (r1 * Math.sin(a)).toFixed(1), class: seen.has(k) ? 'lit' : ''}));
      }
      svg.append(rim);
    }
    for (const ring of fp.rings) {
      const r = R0 + band * (ring.index + 0.5), g = s('g', {class: 'fp-ring' + (ring.index === lastIndex ? ' enter' : '')});
      for (const a of ring.arcs) {
        g.append(s('path', {d: arc(r, a.a0, a.a1), class: 'fp-arc', 'data-k': a.k, style: `stroke:${ramp(a.value)};stroke-width:${Math.max(1.2, band * 0.8).toFixed(2)}`},
          s('title', {text: `${A.conceptName(snap.source, a.k)} · ${unit} ${ring.index + 1} : ${A.score(snap.source, a.value)}${snap.source === 'singpad' ? ` sur ${A.num(a.notes)} note(s)` : ''}`})));
      }
      svg.append(g);
    }
    if (fp.target) {
      const r = R0 + band * (fp.target.index + 0.5), g = s('g', {class: 'fp-target'});
      for (const a of fp.target.arcs) g.append(s('path', {d: arc(r, a.a0, a.a1), class: 'fp-next', style: `stroke-width:${Math.max(1.2, band * 0.8).toFixed(2)}`}));
      svg.append(g);
    }
    if (selected !== null && selected !== undefined && fp.K > 1) {
      const a = A.slot(selected, fp.K).angle;
      svg.append(s('line', {x1: (R0 - 6) * Math.cos(a), y1: (R0 - 6) * Math.sin(a), x2: (R1 + 12) * Math.cos(a), y2: (R1 + 12) * Math.sin(a), class: 'fp-spoke'}));
    }
    svg.append(s('text', {x: 0, y: -4, 'text-anchor': 'middle', class: 'fp-center', text: String(snap.cutoff)}),
               s('text', {x: 0, y: 14, 'text-anchor': 'middle', class: 'fp-center-sub', text: `sur ${fp.total}`}));
    if (onSelect) svg.addEventListener('click', e => { const p = e.target.closest && e.target.closest('.fp-arc'); if (p) onSelect(Number(p.dataset.k)); });
    return svg;
  }

  function bar(ind) {
    const W = 120, Hh = 6, v = ind.value;
    const g = s('svg', {viewBox: `0 0 ${W} ${Hh}`, class: 'ind-bar', 'aria-hidden': 'true'});
    g.append(s('rect', {x: 0, y: 0, width: W, height: Hh, rx: 3, class: 'ind-track'}));
    if (v === null || !ind.sufficient) return g;
    if (ind.unit === 'delta') {
      const x = Math.max(-0.5, Math.min(0.5, v)) / 0.5 * W / 2;
      g.append(s('line', {x1: W / 2, x2: W / 2, y1: -1, y2: Hh + 1, class: 'ind-mid'}),
               s('rect', {x: Math.min(W / 2, W / 2 + x), y: 0, width: Math.abs(x), height: Hh, rx: 3, class: v >= 0 ? 'ind-fill up' : 'ind-fill down'}));
    } else g.append(s('rect', {x: 0, y: 0, width: W * Math.max(0, Math.min(1, v / ind.scale)), height: Hh, rx: 3, class: 'ind-fill'}));
    return g;
  }

  function create({store, api, constellation}) {
    const main = document.getElementById('fp-main'), cmpFig = document.getElementById('fp-compare-figure');
    const cmp = document.getElementById('fp-compare'), list = document.getElementById('fp-indicators');
    const button = document.getElementById('compare');
    let lastCutoff = null;

    button.addEventListener('click', () => {
      const st = store.get();
      if (st.compareCutoff) store.set({compareCutoff: null, compareSnapshot: null, comparisonEpoch: st.comparisonEpoch + 1});
      else store.set({compareCutoff: st.snapshot.cutoff, compareSnapshot: st.snapshot, comparisonEpoch: st.comparisonEpoch + 1});
    });

    function render(st) {
      const snap = st.snapshot; if (!snap) return;
      const grew = lastCutoff !== null && snap.cutoff === lastCutoff + 1; lastCutoff = snap.cutoff;
      const onSelect = k => constellation.select(k);
      main.replaceChildren(draw(snap, {selected: st.selected, onSelect, lastIndex: grew ? snap.cutoff - 1 : null}));
      const unit = A.stepName(snap.source);
      document.getElementById('fp-caption').textContent = `Moment ${st.compareCutoff ? 'B' : 'actuel'} : ${unit} ${snap.cutoff} sur ${snap.steps_total}. `
        + (snap.target ? 'Le sillon doré en pointillé marque les concepts évalués au prochain pas ; leurs résultats restent cachés.' : 'Parcours enregistré complet.');
      const a = st.compareSnapshot && A.sameRequest(st.compareSnapshot, {source: snap.source, learner: snap.learner, cutoff: st.compareCutoff}) ? st.compareSnapshot : null;
      button.setAttribute('aria-pressed', String(!!st.compareCutoff));
      button.textContent = st.compareCutoff ? `Arrêter la comparaison (A = pas ${st.compareCutoff})` : 'Comparer deux moments';
      cmpFig.hidden = !a;
      if (a) {
        cmp.replaceChildren(draw(a, {selected: st.selected, onSelect, small: true}));
        const later = a.cutoff > snap.cutoff;
        document.getElementById('fp-compare-caption').textContent = later
          ? `Moment A épinglé : ${unit} ${a.cutoff}, après le moment observé. Il montre des résultats déjà vus plus loin que le reste de la page garde cachés.`
          : `Moment A épinglé : ${unit} ${a.cutoff}. Déplacez la machine pour choisir le moment B.`;
        cmpFig.classList.toggle('is-later', later);
      }
      const inds = A.indicators(snap);
      const head = h('div', {class: 'ind-head'}, h('h3', {text: a ? `Indicateurs : A (pas ${a.cutoff}) et B (pas ${snap.cutoff})` : `Indicateurs au pas ${snap.cutoff}`}),
        h('p', {class: 'fine', text: 'Chaque indicateur a sa propre échelle et sa définition ; ils ne sont pas additionnés en un score de niveau.'}));
      if (a) {
        const rows = A.compareIndicators(a, snap).map(r => [r.label, r.a, r.b, r.delta === null ? 'non comparable (preuves insuffisantes)'
          : r.unit === 'fraction' || r.unit === 'delta' || r.unit === 'spread' ? A.points(r.delta) : `${r.delta > 0 ? '+' : r.delta < 0 ? '−' : ''}${A.num(Math.abs(r.delta))}`]);
        list.replaceChildren(head, table(['Indicateur', `A · pas ${a.cutoff}`, `B · pas ${snap.cutoff}`, 'Écart B − A'], rows));
        return;
      }
      list.replaceChildren(head, h('ul', {class: 'ind-list'}, inds.map(ind => h('li', {class: 'ind' + (ind.sufficient ? '' : ' insufficient')},
        h('div', {class: 'ind-top'}, h('span', {class: 'ind-label', text: ind.label}), h('strong', {class: 'ind-value', text: ind.display})),
        bar(ind),
        h('details', {}, h('summary', {text: ind.sufficient ? `Mesure · ${ind.support}` : `Insuffisant · ${ind.support}`}),
          h('p', {text: ind.definition}), h('p', {class: 'mono', text: ind.formula}),
          ind.concepts && ind.concepts.length ? h('div', {class: 'nb-list'}, ind.concepts.map(k => h('button', {type: 'button', class: 'nb', text: `C${k}`, onclick: () => constellation.select(k)}))) : null)))));
    }
    return {render};
  }
  L.fingerprint = {create, draw};
})(window.Living);
