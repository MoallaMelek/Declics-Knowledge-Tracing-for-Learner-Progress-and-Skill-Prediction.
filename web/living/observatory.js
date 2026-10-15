'use strict';
// Feature 4 · Observatoire de la décision. Real inputs, recorded activations, served output, server-mediated reveal.
(function (L) {
  const {h, s, table, ramp, activation} = L.dom, A = L.adapters;
  const STAGES = [
    {id: 'history', n: '01', label: 'Historique', hint: 'Pas antérieurs fournis'},
    {id: 'encoding', n: '02', label: 'Encodage', hint: 'Tenseurs réellement construits'},
    {id: 'gru', n: '03', label: 'Mémoire GRU', hint: 'Activations enregistrées'},
    {id: 'head', n: '04', label: 'Tête de sortie', hint: 'Logits → probabilités'},
    {id: 'forecast', n: '05', label: 'Prévision', hint: 'Valeur servie et provenance'},
    {id: 'evaluation', n: '06', label: 'Évaluation', hint: 'Révélation à la demande'}
  ];
  const NEEDS_INSPECTION = new Set(['encoding', 'gru', 'head']);

  function shape(ins, name) { const l = ins.layers.find(x => x.name === name); return l ? l.shape : null; }

  function create({store, client, onReveal, onInspect}) {
    const pipeline = document.getElementById('pipeline'), detail = document.getElementById('stage-detail');
    const research = document.getElementById('research');
    let researchData = null, researchError = null, researchLoading = false;

    pipeline.replaceChildren(...STAGES.map(st => h('li', {}, h('button', {type: 'button', class: 'stage-btn', 'data-stage': st.id,
      onclick: () => { store.set({stage: st.id}); detail.focus({preventScroll: true}); }},
      h('span', {class: 'stage-n', text: st.n}), h('span', {class: 'stage-label', text: st.label}), h('span', {class: 'stage-hint', text: st.hint})))));

    function render(st) {
      const snap = st.snapshot; if (!snap) return;
      for (const b of pipeline.querySelectorAll('.stage-btn')) {
        const on = b.dataset.stage === st.stage;
        b.classList.toggle('on', on); if (on) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current');
      }
      const forecastReady = !!(snap.forecast && snap.forecast.predictions);
      pipeline.classList.toggle('abstained', !forecastReady);
      if (NEEDS_INSPECTION.has(st.stage) && forecastReady) onInspect();
      const body = ({history, encoding, gru, head: headStage, forecast, evaluation})[st.stage](st);
      L.dom.put(detail, ...[].concat(body));
      renderResearch(st);
    }

    function needsForecast(snap) {
      if (!snap.target) return h('p', {class: 'empty', text: 'Fin du parcours enregistré : il n’existe aucun résultat futur à prévoir. Reculez la machine pour inspecter une prévision.'});
      if (!snap.forecast || !snap.forecast.predictions) return h('p', {class: 'empty', text: A.reason(snap.forecast && snap.forecast.reason)});
      return null;
    }
    function inspectionOr(st) {
      const ins = st.inspection;
      if (!ins || ins.cutoff !== st.snapshot.cutoff || ins.key !== `${st.snapshot.source}|${st.snapshot.learner}`) return h('p', {class: 'empty', text: 'Lecture des tenseurs réellement fournis au réseau…'});
      if (ins.error) return h('p', {class: 'empty', text: ins.error});
      if (!ins.available) return h('p', {class: 'empty', text: A.reason(ins.reason)});
      return null;
    }

    function history(st) {
      const snap = st.snapshot, singpad = snap.source === 'singpad', unit = A.stepName(snap.source);
      const concepts = snap.target ? snap.target.concepts : [];
      const others = new Set(); for (const p of snap.past) for (const k of Object.keys(p.concepts)) if (!concepts.includes(Number(k))) others.add(k);
      const rows = singpad ? concepts : [0];
      const cw = Math.max(8, Math.min(22, 560 / Math.max(1, snap.cutoff))), rh = singpad ? 12 : 26, left = 64;
      const W = left + cw * snap.cutoff + 8, H = 18 + rh * rows.length;
      const svg = s('svg', {viewBox: `0 0 ${W} ${H}`, class: 'matrix', role: 'img', style: `max-width:${W}px`,
        'aria-label': `Résultats des ${snap.cutoff} ${unit}(s) passés pour les concepts évalués au prochain pas. Tableau équivalent ci-dessous.`});
      snap.past.forEach((p, i) => { if (i % Math.ceil(snap.cutoff / 14) === 0 || i === snap.cutoff - 1) svg.append(s('text', {x: left + cw * (i + 0.5), y: 11, 'text-anchor': 'middle', class: 'mx-txt', text: String(i + 1)})); });
      rows.forEach((k, r) => {
        svg.append(s('text', {x: left - 6, y: 18 + rh * r + rh * 0.75, 'text-anchor': 'end', class: 'mx-txt', text: singpad ? `C${k}` : 'score'}));
        snap.past.forEach((p, i) => {
          const v = p.concepts[String(k)];
          svg.append(v ? s('rect', {x: left + cw * i + 1, y: 18 + rh * r + 1, width: cw - 2, height: rh - 2, rx: 1.5, style: `fill:${ramp(v[0] / v[1])}`}, s('title', {text: `${A.conceptName(snap.source, k)} · ${unit} ${i + 1} : ${A.pct(v[0] / v[1])}${singpad ? ` (${A.num(v[1])} notes)` : ''}`}))
                       : s('rect', {x: left + cw * i + cw / 2 - 1, y: 18 + rh * r + rh / 2 - 1, width: 2, height: 2, class: 'mx-gap'}));
        });
      });
      const lastFull = snap.past.slice(-6);
      return [
        h('h3', {text: `${snap.cutoff} ${unit}(s) antérieurs, dans l’ordre`}),
        h('p', {text: singpad
          ? `Le réseau lit chaque groupe passé : quels concepts ont été chantés et quelle part des notes a réussi. Le prochain groupe (exercice ${snap.target ? snap.target.exercise : '—'}) n’apporte que sa définition. ${others.size} autre(s) concept(s) observé(s) entrent aussi dans les cumuls.`
          : 'Le réseau lit le score agrégé de chaque jour actif passé. Les jours sans pratique ne sont pas des échecs : ils n’existent pas dans la séquence.'}),
        rows.length ? h('figure', {class: 'mx-fig'}, svg, h('figcaption', {class: 'fine', text: 'Case colorée : part des notes réussies · point : concept non mesuré à ce pas (absence ≠ échec).'})) : h('p', {class: 'empty', text: 'Aucune cible : fin du parcours.'}),
        h('details', {class: 'alt'}, h('summary', {text: 'Valeurs des derniers pas'}),
          table([A.stepName(snap.source), 'Jour relatif', 'Exercice', 'Réussite agrégée', singpad ? 'Notes' : 'Mesures'], lastFull.map(p => [p.index + 1, A.num(p.day, singpad ? 1 : 0), p.exercise || '—', A.pct(p.score), A.num(p.weight)])))
      ];
    }

    function encoding(st) {
      const snap = st.snapshot, blocked = needsForecast(snap) || inspectionOr(st); if (blocked) return blocked;
      const ins = st.inspection, concepts = Object.keys(ins.steps[0].features), T = ins.steps.length;
      const cols = concepts.length * 4, cw = Math.max(4, Math.min(14, 640 / cols)), rh = Math.max(7, Math.min(16, 300 / T)), left = 46, top = 22;
      const max = [0, 1, 2, 3].map(f => Math.max(1e-9, ...ins.steps.flatMap(r => concepts.map(k => r.features[k][f]))));
      const W = left + cw * cols + 70, H = top + rh * T + 8;
      const svg = s('svg', {viewBox: `0 0 ${W} ${H}`, class: 'matrix', role: 'img', style: `max-width:${W}px`,
        'aria-label': `Entrée x réellement construite : ${T} pas × ${concepts.length} concepts ciblés × 4 caractéristiques.`});
      concepts.forEach((k, j) => { if (concepts.length <= 12 || j % 2 === 0) svg.append(s('text', {x: left + cw * (4 * j + 2), y: 12, 'text-anchor': 'middle', class: 'mx-txt', text: `C${k}`})); });
      svg.append(s('text', {x: left + cw * cols + 6, y: 12, class: 'mx-txt', text: 'autres ≠ 0'}));
      ins.steps.forEach((r, i) => {
        const y = top + rh * i;
        svg.append(s('text', {x: left - 6, y: y + rh * 0.78, 'text-anchor': 'end', class: 'mx-txt' + (r.is_query ? ' gold' : ''), text: r.is_query ? 'requête' : `pas ${r.step + 1}`}));
        concepts.forEach((k, j) => r.features[k].forEach((v, f) => {
          const t = v / max[f], c = f % 2 === 0 ? [124, 196, 160] : [226, 104, 91];
          svg.append(s('rect', {x: left + cw * (4 * j + f) + 0.5, y: y + 0.5, width: cw - 1, height: rh - 1,
            style: `fill:rgb(${c.map(x => Math.round(22 + (x - 22) * Math.sqrt(t))).join(',')})`}, s('title', {text: `${ins.feature_order[f]} · C${k} · ${A.num(v, 4)}`})));
        }));
        svg.append(s('text', {x: left + cw * cols + 6, y: y + rh * 0.78, class: 'mx-txt', text: String(r.other_nonzero_features)}));
      });
      const t = ins.tensors;
      return [
        h('h3', {text: 'Ce que le réseau reçoit réellement'}),
        h('div', {class: 'tensors'},
          h('span', {class: 'tensor', text: `x · [${t.x.join(' × ')}]`}), h('span', {class: 'tensor', text: `exercice précédent · [${t.previous_item.join(' × ')}]`}),
          h('span', {class: 'tensor', text: `exercice demandé · [${t.current_item.join(' × ')}]`}), h('span', {class: 'tensor', text: `difficulté · [${t.difficulty.join(' × ')}] (nulle)`})),
        h('p', {text: `La ligne « requête » est le pas à prévoir : elle ne contient que des valeurs issues des pas antérieurs et l’identifiant de l’exercice demandé. Fenêtre : ${ins.window.steps_in_window} ligne(s) sur un contexte de ${ins.window.context} ; les cumuls couvrent tout le passé.`}),
        h('figure', {class: 'mx-fig'}, svg, h('figcaption', {class: 'fine', text: `Par concept, 4 colonnes : ${ins.feature_order.join(' · ')}. Vert : réussites, corail : échecs ; intensité normalisée par type de caractéristique. Dernière colonne : caractéristiques non nulles des autres concepts (aussi reçues).`})),
        h('details', {class: 'alt'}, h('summary', {text: 'Exercices encodés (identifiants du vocabulaire)'}),
          table(['Ligne', 'Exercice précédent', 'Exercice demandé'], ins.steps.map(r => [r.is_query ? 'requête' : `pas ${r.step + 1}`, r.previous_exercise ? `${r.previous_exercise} (#${r.previous_item})` : 'aucun (#0)', r.current_exercise ? `${r.current_exercise} (#${r.current_item})` : 'inconnu ou absent (#0)'])))
      ];
    }

    function architecture(ins, K) {
      const emb = shape(ins, 'item.weight'), out0 = shape(ins, 'output.0.weight'), out2 = shape(ins, 'output.2.weight');
      const boxes = [
        {x: 10, y: 30, w: 150, label: 'x_t', sub: `${4 * K} valeurs`},
        {x: 10, y: 92, w: 150, label: 'exercice précédent', sub: emb ? `embedding ${emb[1]}` : 'embedding'},
        {x: 200, y: 58, w: 120, label: 'GRU', sub: `entrée ${ins.tensors.gru_input_width} → ${ins.tensors.hidden_size}`, accent: true},
        {x: 360, y: 30, w: 160, label: 'h_t + exercice demandé', sub: out0 ? `+ cumuls → ${out0[1]}` : ''},
        {x: 560, y: 58, w: 110, label: 'MLP', sub: out0 && out2 ? `${out0[1]}→${out0[0]}→${out2[0]}` : ''},
        {x: 700, y: 58, w: 90, label: 'sigmoïde', sub: `${K} sortie(s)`, gold: true}
      ];
      const svg = s('svg', {viewBox: '0 0 800 150', class: 'arch', role: 'img', 'aria-label': 'Schéma de l’architecture EnhancedGRU servie, avec les dimensions réelles des couches.'});
      const arrow = (x1, y1, x2, y2) => svg.append(s('path', {d: `M${x1} ${y1} C ${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}`, class: 'arch-link'}));
      arrow(160, 50, 200, 78); arrow(160, 112, 200, 88); arrow(320, 78, 360, 50); arrow(520, 50, 560, 78); arrow(670, 78, 700, 78);
      svg.append(s('path', {d: 'M260 98 C 260 135, 300 135, 300 108', class: 'arch-link loop'}), s('text', {x: 262, y: 146, class: 'arch-sub', text: 'mémoire h_t-1'}));
      for (const b of boxes) svg.append(s('g', {class: 'arch-box' + (b.accent ? ' accent' : '') + (b.gold ? ' gold' : '')},
        s('rect', {x: b.x, y: b.y, width: b.w, height: 40, rx: 6}),
        s('text', {x: b.x + b.w / 2, y: b.y + 17, 'text-anchor': 'middle', class: 'arch-label', text: b.label}),
        s('text', {x: b.x + b.w / 2, y: b.y + 32, 'text-anchor': 'middle', class: 'arch-sub', text: b.sub})));
      return svg;
    }

    function gru(st) {
      const snap = st.snapshot, blocked = needsForecast(snap) || inspectionOr(st); if (blocked) return blocked;
      const ins = st.inspection, hs = ins.hidden_states;
      const parts = [h('h3', {text: 'La mémoire du réseau, pas après pas'}),
        h('figure', {class: 'arch-fig'}, architecture(ins, snap.K), h('figcaption', {class: 'fine', text: `Schéma explicatif, pas le dessin de chaque opération. Dimensions lues dans les ${A.num(ins.parameters)} paramètres du modèle servi. Les poids ne changent pas pendant le rejeu.`})),
        h('p', {class: 'note', text: ins.attention_note})];
      if (!hs) return parts.concat(h('p', {class: 'empty', text: 'Activations indisponibles pour cette architecture.'}));
      const T = hs.length, Hn = hs[0].length, cw = Math.max(5, Math.min(13, 620 / Hn)), rh = Math.max(7, Math.min(15, 300 / T)), left = 60;
      const svg = s('svg', {viewBox: `0 0 ${left + cw * Hn + 6} ${rh * T + 22}`, class: 'matrix', role: 'img', style: `max-width:${left + cw * Hn + 6}px`,
        'aria-label': `États cachés enregistrés : ${T} pas × ${Hn} unités.`});
      svg.append(s('text', {x: left, y: 11, class: 'mx-txt', text: `unités 1…${Hn}`}));
      hs.forEach((row, i) => {
        const step = ins.steps[i];
        svg.append(s('text', {x: left - 6, y: 18 + rh * i + rh * 0.78, 'text-anchor': 'end', class: 'mx-txt' + (step.is_query ? ' gold' : ''), text: step.is_query ? 'requête' : `pas ${step.step + 1}`}));
        row.forEach((v, j) => svg.append(s('rect', {x: left + cw * j + 0.5, y: 18 + rh * i + 0.5, width: cw - 1, height: rh - 1, style: `fill:${activation(v)}`})));
      });
      const last = hs[T - 1], prev = T > 1 ? hs[T - 2] : null;
      const change = prev ? Math.sqrt(last.reduce((a, v, j) => a + (v - prev[j]) ** 2, 0)) : null;
      return parts.concat(
        h('figure', {class: 'mx-fig'}, svg, h('figcaption', {class: 'fine', text: `${ins.activation_note} Orange : valeur positive, bleu : négative, entre −1 et 1.`})),
        h('p', {class: 'fine', text: change === null ? '' : `Variation de l’état caché entre les deux dernières lignes : ${A.num(change, 3)} (norme euclidienne). Une grande variation ne dit pas pourquoi la prévision change.`}));
    }

    function headStage(st) {
      const snap = st.snapshot, blocked = needsForecast(snap) || inspectionOr(st); if (blocked) return blocked;
      const ins = st.inspection, entries = Object.entries(ins.head.logits);
      return [h('h3', {text: 'De l’état caché à une probabilité'}),
        h('p', {text: `La tête combine : ${ins.head.inputs.join(', ')}. Elle produit un logit par concept ; la sigmoïde le transforme en probabilité.`}),
        h('ul', {class: 'logits'}, entries.map(([k, z]) => {
          const p = ins.head.probabilities[k];
          return h('li', {}, h('span', {class: 'lg-name', text: snap.source === 'singpad' ? `C${k}` : 'score'}),
            h('span', {class: 'lg-z', text: `logit ${z >= 0 ? '+' : '−'}${A.num(Math.abs(z), 3)}`}),
            h('span', {class: 'lg-bar'}, h('span', {style: `width:${(100 * p).toFixed(1)}%`})),
            h('strong', {class: 'gold', text: A.forecast(snap.source, p)}));
        })),
        h('p', {class: ins.matches_served_forecast ? 'ok' : 'warn', text: ins.matches_served_forecast
          ? `Contrôle : ces probabilités recalculées sur une copie isolée du modèle sont identiques à la prévision servie (écart maximal ${A.num(ins.max_abs_difference, 7)}).`
          : 'Attention : la recomposition ne correspond pas à la prévision servie ; elle n’est pas utilisée.'})];
    }

    function forecast(st) {
      const snap = st.snapshot, blocked = needsForecast(snap); if (blocked) return blocked;
      const p = snap.forecast.predictions, prov = st.provenance || {}, singpad = snap.source === 'singpad';
      const values = Object.values(p), m = A.mean(values), bin = singpad ? A.calibrationBin(prov.calibration_bins, m) : null;
      const test = prov.test || {}, ref = prov.train_mean_test || {};
      return [h('h3', {text: singpad ? `Probabilité de réussite d’une note, pour ${values.length} concepts du prochain groupe` : 'Score prévu pour le prochain jour actif'}),
        h('ul', {class: 'logits probs'}, Object.entries(p).map(([k, v]) => h('li', {}, h('span', {class: 'lg-name', text: singpad ? `C${k}` : 'score'}),
          h('span', {class: 'lg-bar'}, h('span', {style: `width:${(100 * v).toFixed(1)}%`})), h('strong', {class: 'gold', text: A.forecast(snap.source, v)})))),
        h('p', {}, singpad ? 'Moyenne simple des concepts : ' : 'Valeur : ', h('strong', {class: 'gold', text: A.forecast(snap.source, m)}), singpad ? ' (une probabilité n’est pas la confiance du modèle).' : ' (score continu, pas une probabilité).'),
        bin ? h('p', {class: 'note', text: `Repère de population, pas une incertitude individuelle : sur le test, quand le modèle prévoyait entre ${A.pct(bin.lower, 0)} et ${A.pct(bin.lower + 0.1, 0)}, la fréquence observée était ${A.pct(bin.observed)} (${A.num(bin.weight)} notes).`}) : null,
        table(['Provenance', 'Valeur'], [
          ['Moteur', prov.engine], ['Modèle', prov.model_id], ['Architecture', prov.architecture], ['Empreinte des poids (SHA-256)', prov.model_sha256 ? `${prov.model_sha256.slice(0, 16)}…` : '—'],
          ['Base d’entraînement', `${prov.dataset} · ${prov.citation}`], ['Instrument et cible', `${prov.instrument} · ${prov.target}`],
          ['Apprenants (train / validation / test)', prov.splits ? `${prov.splits.train.count} / ${prov.splits.validation.count} / ${prov.splits.test.count}, disjoints` : '—'],
          ['Point de coupure', `${snap.cutoff} ${A.stepName(snap.source)}(s) observé(s)`], ['Horizon', singpad ? 'prochain groupe d’enregistrements' : 'prochain jour actif'],
          ['Mesure sur le test', singpad ? `log-loss ${A.num(test.log_loss, 4)} (moyenne d’entraînement : ${A.num(ref.log_loss, 4)}) · ROC-AUC ${A.num(test.roc_auc, 3)}` : `erreur absolue ${A.num(test.mae, 4)} (moyenne d’entraînement : ${A.num(ref.mae, 4)})`],
          ['Domaine', 'Base source uniquement ; aucune validation au piano ni pour un autre instrument'], ['Incertitude individuelle', 'non validée']])];
    }

    function trailChart(snap) {
      const pts = snap.trail.filter(t => t.predicted_mean !== undefined);
      if (!pts.length) return null;
      const n = Math.max(2, snap.cutoff), W = 600, H = 120, x = i => 24 + i / (n - 1) * (W - 40), y = v => 10 + (1 - v) * (H - 30);
      const svg = s('svg', {viewBox: `0 0 ${W} ${H}`, class: 'trail', role: 'img', 'aria-label': `${pts.length} prévisions antérieures et leurs résultats observés.`});
      for (const v of [0, 0.5, 1]) svg.append(s('line', {x1: 24, x2: W - 16, y1: y(v), y2: y(v), class: 'spark-grid'}), s('text', {x: 2, y: y(v) + 4, class: 'spark-txt', text: `${100 * v}`}));
      for (const t of pts) {
        svg.append(s('line', {x1: x(t.index), x2: x(t.index), y1: y(t.predicted_mean), y2: y(t.observed_mean), class: 'trail-err'}),
          s('circle', {cx: x(t.index), cy: y(t.observed_mean), r: 3.6, class: 'trail-obs'}, s('title', {text: `Pas ${t.index + 1} · observé ${A.pct(t.observed_mean)}`})),
          s('rect', {x: x(t.index) - 3.2, y: y(t.predicted_mean) - 3.2, width: 6.4, height: 6.4, transform: `rotate(45 ${x(t.index)} ${y(t.predicted_mean)})`, class: 'spark-pred'}, s('title', {text: `Pas ${t.index + 1} · prévu ${A.pct(t.predicted_mean)} · ${t.metric} ${A.num(t.error, 3)}`})));
      }
      const meanErr = A.mean(pts.map(t => t.error));
      return h('figure', {class: 'trail-fig'}, svg, h('figcaption', {class: 'fine', text: `Toutes les prévisions déjà évaluées de ce parcours, sans sélection : losange doré = prévu, point = observé (moyennes simples des concepts). ${pts[0].metric} moyenne : ${A.num(meanErr, 3)} sur ${pts.length} pas.`}));
    }

    function evaluation(st) {
      const snap = st.snapshot, blocked = needsForecast(snap);
      const chart = trailChart(snap);
      if (blocked) return [blocked, chart].filter(Boolean);
      const rv = st.reveals[A.revealKey(snap)], singpad = snap.source === 'singpad';
      if (!rv) return [h('h3', {text: 'Le résultat réel reste caché'}),
        h('p', {text: 'La prévision a été calculée sans lui. Il n’a pas été transmis à cette page : le serveur ne le renvoie qu’avec le reçu signé de cette prévision.'}),
        h('button', {type: 'button', class: 'primary', text: `Révéler le résultat du pas ${snap.cutoff + 1}`, onclick: e => { e.currentTarget.disabled = true; onReveal(); }}),
        chart].filter(Boolean);
      const refs = rv.references, lch = refs.learner_concept_history;
      return [h('h3', {text: `Résultat observé au pas ${snap.cutoff + 1}`}),
        dumbbell(rv, singpad),
        h('details', {class: 'alt'}, h('summary', {text: 'Valeurs par concept'}),
          table([singpad ? 'Concept' : 'Cible', 'Prévu', 'Observé', singpad ? 'Notes' : 'Mesure', 'Écart', singpad ? 'Log-loss par note' : 'Erreur absolue'],
            rv.comparison.map(c => [singpad ? `C${c.concept}` : 'Score global', A.pct(c.prediction), A.pct(c.observed), A.num(c.notes), A.points(c.prediction - c.observed), singpad ? A.num(c.log_loss, 3) : A.num(c.absolute_error, 3)]))),
        h('p', {}, `${rv.metric} de ce pas : `, h('strong', {text: A.num(rv.error, 4)}), ` · moyenne prévue ${A.pct(rv.predicted_mean)}, observée ${A.pct(rv.observed_mean)}.`),
        h('h3', {text: 'Références simples sur exactement les mêmes notes'}),
        table(['Méthode', rv.metric, 'Cibles'], [
          ['Réseau EnhancedGRU (servi)', A.num(rv.error, 4), String(rv.comparison.length)],
          ['Moyenne d’entraînement constante', A.num(refs.train_mean.error, 4), String(refs.train_mean.targets)],
          ['Réseau, sur les concepts déjà vus', lch.model_error_same_targets === null ? '—' : A.num(lch.model_error_same_targets, 4), String(lch.targets)],
          ['Fréquence passée du concept chez l’apprenant', lch.error === null ? '—' : A.num(lch.error, 4), `${lch.targets} (${lch.excluded} sans passé exclus)`]]),
        h('p', {class: 'fine', text: `${refs.scope} Un seul pas ne permet aucune conclusion ; ${rv.interpretation}`}),
        chart].filter(Boolean);
    }

    // Predicted (gold diamond) vs observed (ivory dot) per target; the bar is the error. Every target is drawn.
    function dumbbell(rv, singpad) {
      const rows = rv.comparison, rh = 20, left = 62, W = 640, H = 26 + rh * rows.length, x = v => left + v * (W - left - 70);
      const svg = s('svg', {viewBox: `0 0 ${W} ${H}`, class: 'dumbbell', role: 'img', style: `max-width:${W}px`,
        'aria-label': `Prévu et observé pour ${rows.length} cible(s). Valeurs détaillées dans le tableau ci-dessous.`});
      for (const v of [0, 0.5, 1]) svg.append(s('line', {x1: x(v), x2: x(v), y1: 14, y2: H - 6, class: 'spark-grid'}), s('text', {x: x(v), y: 10, 'text-anchor': 'middle', class: 'mx-txt', text: `${100 * v} %`}));
      rows.forEach((c, i) => {
        const y = 24 + rh * i;
        svg.append(s('text', {x: left - 8, y: y + 4, 'text-anchor': 'end', class: 'mx-txt', text: singpad ? `C${c.concept}` : 'score'}),
          s('line', {x1: x(c.prediction), x2: x(c.observed), y1: y, y2: y, class: 'db-err' + (c.prediction > c.observed ? ' over' : ' under')}),
          s('circle', {cx: x(c.observed), cy: y, r: 4.2, class: 'trail-obs'}, s('title', {text: `Observé ${A.pct(c.observed)}${singpad ? ` sur ${A.num(c.notes)} note(s)` : ''}`})),
          s('rect', {x: x(c.prediction) - 3.6, y: y - 3.6, width: 7.2, height: 7.2, transform: `rotate(45 ${x(c.prediction)} ${y})`, class: 'spark-pred'}, s('title', {text: `Prévu ${A.pct(c.prediction)}`})),
          s('text', {x: W - 6, y: y + 4, 'text-anchor': 'end', class: 'mx-txt', text: singpad ? `${A.num(c.notes)} n.` : ''}));
      });
      return h('figure', {class: 'mx-fig'}, svg, h('figcaption', {class: 'fine', text: 'Losange doré : prévision faite avant la révélation · point : résultat observé · trait : écart (corail si le réseau surestime, bleu s’il sous-estime). Toutes les cibles sont montrées.'}));
    }

    function renderResearch(st) {
      research.hidden = !st.research;
      if (!st.research) return;
      if (!researchData && !researchError && !researchLoading) {
        researchLoading = true;
        client.research().then(d => { researchData = d; }).catch(e => { researchError = e.message; }).finally(() => { researchLoading = false; render(store.get()); });
      }
      const prov = st.provenance || {}, snap = st.snapshot;
      const parts = [h('h3', {text: 'Mode recherche · bancs d’essai Phase 7'}),
        h('p', {class: 'note', text: 'Les contrôles classiques (régression logistique, PFA, Ridge, arbres boostés) servent uniquement à la comparaison scientifique. Aucune prévision de cette page ne passe par eux.'})];
      if (researchError) parts.push(h('p', {class: 'empty', text: researchError}));
      else if (!researchData) parts.push(h('p', {class: 'empty', text: 'Chargement des résultats publiés…'}));
      else {
        parts.push(table(['Base', 'Graine', 'Réseau choisi', 'Test réseau', 'Contrôle choisi', 'Test contrôle', 'Contrôle appris choisi', 'Test contrôle appris'],
          researchData.comparisons.map(r => [r.source, r.seed, r.selected, A.num(r.neural_test, 5), r.selected_control || '—', A.num(r.control_test, 5), r.selected_learned_control || '—', A.num(r.learned_control_test, 5)]),
          'Plus bas = meilleur (log-loss SingPAD, erreur absolue AMME et Yousician). Sélection sur validation avant lecture du test.'));
        parts.push(h('p', {class: 'fine', text: researchData.scope}));
      }
      if (snap.source === 'singpad' && prov.calibration_bins) parts.push(reliability(prov.calibration_bins));
      L.dom.put(research, ...parts);
    }

    function reliability(bins) {
      const W = 260, P = 30, x = v => P + v * (W - 2 * P), y = v => W - P - v * (W - 2 * P);
      const total = bins.reduce((a, b) => a + b.weight, 0);
      const svg = s('svg', {viewBox: `0 0 ${W} ${W}`, class: 'reliability', role: 'img', 'aria-label': 'Diagramme de fiabilité du modèle actif sur le test SingPAD.'},
        s('line', {x1: x(0), y1: y(0), x2: x(1), y2: y(1), class: 'spark-th'}),
        s('line', {x1: x(0), y1: y(0), x2: x(1), y2: y(0), class: 'spark-grid'}), s('line', {x1: x(0), y1: y(0), x2: x(0), y2: y(1), class: 'spark-grid'}),
        s('text', {x: W / 2, y: W - 6, 'text-anchor': 'middle', class: 'spark-txt', text: 'prévision moyenne'}),
        s('text', {x: 10, y: W / 2, transform: `rotate(-90 10 ${W / 2})`, 'text-anchor': 'middle', class: 'spark-txt', text: 'fréquence observée'}));
      for (const b of bins) svg.append(s('circle', {cx: x(b.prediction), cy: y(b.observed), r: 2.5 + 9 * Math.sqrt(b.weight / total), class: 'rel-dot'},
        s('title', {text: `Prévu ${A.pct(b.prediction)} · observé ${A.pct(b.observed)} · ${A.num(b.weight)} notes`})));
      return h('figure', {class: 'rel-fig'}, svg, h('figcaption', {class: 'fine', text: 'Calibration de population sur le test du modèle servi (aire ∝ nombre de notes). Proche de la diagonale ne veut pas dire fiable pour un individu.'}));
    }

    return {render};
  }
  L.observatory = {create, STAGES};
})(window.Living);
