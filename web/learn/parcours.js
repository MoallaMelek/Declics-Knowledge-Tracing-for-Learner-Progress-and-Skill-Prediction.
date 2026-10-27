'use strict';
// Mon parcours : où j'en suis, forces et faiblesses, erreurs récurrentes, historique, et O08 sur mes propres données.
(function (L) {
  const {h, api, profile, fmt} = L;
  const app = document.getElementById('app');
  const SVG = 'http://www.w3.org/2000/svg';
  const s = (tag, attrs, ...kids) => { const n = document.createElementNS(SVG, tag); for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v); n.append(...kids.filter(Boolean)); return n; };
  const txt = (x, y, t, attrs = {}) => { const n = s('text', {x, y, ...attrs}); n.textContent = t; return n; };
  const LABEL = {maitrise: 'maîtrisé', en_cours: 'en cours', non_commence: 'à venir', mesure: 'mesure'};

  async function boot() {
    try {
      const {id, list} = await profile.resolve();
      if (!id) {
        return app.replaceChildren(h('header', {class: 'page-head'}, h('h1', {text: 'Mon parcours'}),
          h('p', {class: 'lede', text: list.length ? 'Plusieurs profils existent sur cet ordinateur : choisissez le vôtre depuis la page Séance.' : 'Vous n’avez pas encore de profil. Créez-le en deux secondes, puis faites l’évaluation initiale : votre parcours se construira à partir de vos réponses.'}),
          h('div', {class: 'actions'}, h('a', {class: 'btn btn-primary', href: '/web/seance.html', text: list.length ? 'Choisir mon profil' : 'Créer mon profil'}))));
      }
      render(await api.progress(id));
    } catch (e) { L.problem(app, e, boot); }
  }

  function render(p) {
    const mastered = p.mastery.filter(m => m.status === 'maitrise').length;
    const total = p.mastery.filter(m => m.status !== 'mesure').length;
    const cta = p.active_session
      ? h('a', {class: 'btn btn-primary', href: '/web/seance.html', text: `Reprendre ma séance (${p.active_session.answered} / ${p.active_session.total})`})
      : h('a', {class: 'btn btn-primary', href: '/web/seance.html', text: 'Commencer une séance'});
    app.replaceChildren(...[
      h('header', {class: 'page-head'},
        h('p', {class: 'kicker', text: `Profil : ${p.learner.name} · créé le ${fmt.date(p.learner.created_at)} · dernière activité ${fmt.ago(p.last_activity)}`}),
        h('h1', {text: 'Mon parcours'}),
        h('p', {class: 'lede', text: p.totals.answers
          ? 'Chaque réponse corrigée met à jour vos niveaux. Le parcours propose l’étape suivante ; il ne bloque rien : tout reste accessible dans la bibliothèque.'
          : 'Votre parcours est vide pour l’instant. Commencez par l’évaluation initiale : elle situe votre point de départ.'}),
        h('div', {class: 'actions'}, cta, h('a', {class: 'btn btn-secondary', href: '/web/exercices.html', text: 'Bibliothèque d’exercices'})),
        h('div', {class: 'stat-row'},
          stat(p.totals.answers, 'réponses corrigées'),
          stat(p.totals.answers ? fmt.pct(p.totals.correct / p.totals.answers) : '—', 'de réponses justes'),
          stat(p.totals.sessions_finished, 'séances terminées'),
          stat(`${mastered} / ${total}`, 'niveaux maîtrisés'))),
      concepts(),
      mapSection(p),
      skillsSection(p),
      errorsSection(p),
      evolutionSection(p),
      historySection(p),
      o08Section(p)].filter(Boolean));
    if (location.hash) { const t = document.getElementById(location.hash.slice(1)); if (t) t.scrollIntoView(); }
  }
  const num = v => v.toLocaleString('fr-FR', {minimumFractionDigits: 3, maximumFractionDigits: 3});
  const stat = (v, label) => h('div', {class: 'stat'}, h('b', {text: String(v)}), h('span', {text: label}));

  function concepts() {
    const item = (t, d) => h('div', {}, h('dt', {text: t}), h('dd', {text: d}));
    return h('section', {class: 'section', 'aria-labelledby': 'c-title'},
      h('h2', {id: 'c-title', text: 'Cinq mots, cinq choses différentes'}),
      h('dl', {class: 'concepts'},
        item('Compétence', 'Ce que vous apprenez : 9 compétences, de la hauteur aux fonctions tonales.'),
        item('Exercice', 'Une activité qui entraîne ou mesure une compétence, avec des niveaux ordonnés par des critères vérifiables.'),
        item('Évaluation', 'La correction d’une réponse par le serveur. Et, au début, l’évaluation initiale qui situe votre point de départ.'),
        item('Séance', 'Environ 10 minutes de questions choisies d’après vos résultats. Elle se reprend si elle est interrompue.'),
        item('Parcours', 'Cette page : tous les niveaux de tous les exercices, ce qui est maîtrisé et l’étape suivante.')));
  }

  function mapSection(p) {
    const bySkill = {};
    for (const m of p.mastery) (bySkill[m.exercise] = bySkill[m.exercise] || []).push(m);
    const rows = Object.entries(bySkill).map(([ex, levels]) => {
      const f = p.frontier[ex];
      if (!f) {
        const t = p.pitch_threshold;
        return h('div', {class: 'map-row'}, h('div', {}, h('h3', {text: levels[0].title}), h('span', {class: 'fine', text: 'Mesure, sans niveaux'})),
          h('p', {text: t ? (t.threshold_cents ? `Dernière estimation de votre seuil : ${t.threshold_cents} cents (${t.reversals} changements de sens).` : `Seuil non estimé : ${t.reliability}.`) : 'Pas encore mesuré (fait partie de l’évaluation initiale).'}));
      }
      const chips = levels.map(m => {
        const next = f.level === m.level;
        const locked = next && !f.available;
        const placed = f.placed_by_threshold && m.level < f.placed_by_threshold && m.status !== 'maitrise';
        const state = placed ? 'validé par la mesure' : m.status === 'en_cours' ? `${m.recent.successes}/${m.recent.count}` : LABEL[m.status];
        return h('li', {}, h('a', {class: `lvl lvl-${placed ? 'placed' : m.status}${next ? ' lvl-next' : ''}${locked ? ' lvl-locked' : ''}`, href: `/web/seance.html?exercise=${encodeURIComponent(ex)}&level=${m.level}`,
          title: `${m.label} · ${m.attempts} réponse(s)`, 'aria-label': `Niveau ${m.level}, ${m.label} : ${state}${next ? ', prochaine étape' : ''}${locked ? ' (prérequis non atteints)' : ''}. S’entraîner.`},
          m.status === 'maitrise' ? '✓ ' : '', `N${m.level}`, h('span', {class: 'fine', text: ` ${state}`})));
      });
      const prereq = f.prerequisites.filter(x => !x.met);
      return h('div', {class: 'map-row'},
        h('div', {}, h('h3', {text: levels[0].title}),
          h('span', {class: 'fine', text: f.level == null ? 'Tous les niveaux sont maîtrisés' : prereq.length ? `Prérequis à atteindre : ${prereq.map(x => `${x.title}, niveau ${x.level}`).join(', ')}` :
            f.placed_by_threshold ? `Niveau de départ fixé par votre seuil mesuré : ${f.placed_by_threshold}` : `Prochaine étape : niveau ${f.level}`})),
        h('ul', {class: 'levels'}, chips));
    });
    return h('section', {class: 'section', 'aria-labelledby': 'map-title'},
      h('h2', {id: 'map-title', text: 'Où j’en suis'}),
      h('p', {class: 'sub', text: 'Un niveau est maîtrisé quand au moins 80 % de vos 10 dernières réponses à ce niveau sont justes (6 pour le clavier et le tapotement) et que ce score est très improbable au hasard. La prochaine étape est entourée. Cliquez un niveau pour vous y entraîner.'}),
      h('div', {class: 'legend-row'}, h('span', {class: 'lvl lvl-maitrise', text: '✓ maîtrisé'}), h('span', {class: 'lvl lvl-en_cours', text: 'en cours : réussites / réponses récentes'}),
        h('span', {class: 'lvl lvl-next', text: 'prochaine étape'}), h('span', {class: 'lvl lvl-locked', text: 'prérequis non atteints'})),
      h('div', {class: 'map'}, rows));
  }

  function skillsSection(p) {
    const rows = p.skills.map(sk => {
      if (!sk.attempts) return h('div', {class: 'skill-row'}, h('strong', {text: sk.label}), h('div', {class: 'meter'}), h('span', {class: 'tag', text: 'pas encore travaillé'}));
      const tag = p.strengths.includes(sk.id) ? h('span', {class: 'tag tag-good', text: 'point fort'}) : p.weaknesses.includes(sk.id) ? h('span', {class: 'tag tag-work', text: 'à travailler'}) :
        sk.status === 'evalue' ? h('span', {class: 'tag', text: 'intermédiaire'}) : h('span', {class: 'tag', text: `${sk.attempts} réponse(s) : trop peu`});
      const meter = h('div', {class: 'meter', role: 'img', 'aria-label': `${fmt.pct(sk.recent_rate)} de réponses justes récemment, hasard ${fmt.pct(sk.chance)}`},
        h('i', {style: `width:${(sk.recent_rate * 100).toFixed(0)}%`}), h('b', {style: `left:${(sk.chance * 100).toFixed(0)}%`, title: 'niveau du hasard'}));
      const trend = sk.trend ? ` · début ${fmt.pct(sk.trend.first_rate)} (niveau moyen ${sk.trend.first_mean_level}) → récemment ${fmt.pct(sk.trend.second_rate)} (niveau ${sk.trend.second_mean_level})` : '';
      return h('div', {class: 'skill-row'}, h('div', {}, h('strong', {text: sk.label}), h('span', {class: 'fine', text: ` ${fmt.pct(sk.recent_rate)} sur ${sk.recent_count}${trend}`})), meter, tag);
    });
    return h('section', {class: 'section', 'aria-labelledby': 'sk-title'},
      h('h2', {id: 'sk-title', text: 'Forces et points à travailler'}),
      h('p', {class: 'sub', text: 'Réussite sur vos 20 dernières réponses dans chaque compétence ; le trait marque le niveau du hasard. Une compétence n’est classée qu’à partir de 6 réponses. Comparer deux périodes n’a de sens qu’à niveau comparable : le niveau moyen est affiché à côté.'}),
      h('div', {class: 'skills'}, rows));
  }

  function errorsSection(p) {
    return h('section', {class: 'section', 'aria-labelledby': 'err-title'},
      h('h2', {id: 'err-title', text: 'Erreurs récurrentes'}),
      h('p', {class: 'sub', text: 'Les confusions revenues au moins deux fois dans vos 40 dernières réponses.'}),
      p.recurring_errors.length ? h('ul', {class: 'sheet pad'}, p.recurring_errors.map(e => h('li', {}, h('strong', {text: `${e.title} : `}), `${e.error} — ${e.count} fois, dernière ${fmt.ago(e.last)}`)))
        : h('p', {class: 'status-line', text: 'Aucune erreur répétée pour l’instant.'}));
  }

  function evolutionSection(p) {
    const days = p.days;
    if (!days.length) return null;
    const W = 720, H = 220, pad = 36, bw = Math.min(40, (W - 2 * pad) / days.length * 0.6);
    const x = i => pad + (days.length === 1 ? (W - 2 * pad) / 2 : i * (W - 2 * pad) / (days.length - 1));
    const maxN = Math.max(...days.map(d => d.answers));
    const chart = s('svg', {viewBox: `0 0 ${W} ${H}`, class: 'chart', role: 'img', 'aria-label': 'Réponses et réussite par jour'});
    for (const v of [0, 0.5, 1]) { const y = H - pad - v * (H - 2 * pad); chart.append(s('line', {x1: pad, x2: W - pad, y1: y, y2: y, class: 'grid'}), txt(4, y + 4, `${v * 100} %`)); }
    days.forEach((d, i) => {
      const hgt = d.answers / maxN * (H - 2 * pad) * 0.5;
      chart.append(s('rect', {x: x(i) - bw / 2, y: H - pad - hgt, width: bw, height: hgt, fill: 'var(--cover)'}));
      chart.append(txt(x(i), H - 12, d.date.slice(5).split('-').reverse().join('/'), {'text-anchor': 'middle'}));
    });
    const path = days.map((d, i) => `${i ? 'L' : 'M'}${x(i)} ${H - pad - d.correct / d.answers * (H - 2 * pad)}`).join(' ');
    chart.append(s('path', {d: path, class: 's-obs'}));
    days.forEach((d, i) => chart.append(s('circle', {cx: x(i), cy: H - pad - d.correct / d.answers * (H - 2 * pad), r: 4, fill: 'var(--cover-deep)'})));
    const table = h('table', {}, h('thead', {}, h('tr', {}, ['Jour', 'Réponses', 'Justes'].map(t => h('th', {text: t})))),
      h('tbody', {}, days.map(d => h('tr', {}, h('td', {text: fmt.date(d.date)}), h('td', {text: d.answers}), h('td', {text: fmt.pct(d.correct / d.answers)})))));
    return h('section', {class: 'section', 'aria-labelledby': 'ev-title'},
      h('h2', {id: 'ev-title', text: 'Évolution jour après jour'}),
      h('p', {class: 'sub', text: 'Barres : nombre de réponses ce jour-là. Ligne : part de réponses justes. Attention, quand vous passez à un niveau plus difficile, la réussite baisse normalement : regardez aussi la carte des niveaux.'}),
      chart, h('details', {}, h('summary', {text: 'Lire sous forme de tableau'}), h('div', {class: 'table-scroll'}, table)));
  }

  function historySection(p) {
    if (!p.sessions.length) return null;
    return h('section', {class: 'section', 'aria-labelledby': 'hist-title'},
      h('h2', {id: 'hist-title', text: 'Historique des séances'}),
      h('div', {class: 'table-scroll sheet pad'}, h('table', {},
        h('thead', {}, h('tr', {}, ['Date', 'Type', 'État', 'Réponses', 'Justes', ''].map(t => h('th', {text: t})))),
        h('tbody', {}, p.sessions.slice().reverse().map(x => h('tr', {},
          h('td', {text: fmt.dateTime(x.created_at)}), h('td', {text: fmt.KIND[x.kind]}), h('td', {text: fmt.STATUS[x.status]}),
          h('td', {text: `${x.answered} / ${x.total}`}), h('td', {text: x.answered ? fmt.pct(x.correct / x.answered) : '—'}),
          h('td', {}, x.status === 'active' ? h('a', {href: '/web/seance.html', text: 'Reprendre'}) : h('a', {href: `/web/seance.html?bilan=${encodeURIComponent(x.id)}`, text: 'Bilan'}))))))));
  }

  function o08Section(p) {
    const o = p.o08, q = o.quality;
    const explain = h('div', {class: 'sheet pad'},
      h('h3', {text: 'Quel modèle prévoit, et pourquoi pas les réseaux O08 entraînés ?'}),
      h('p', {}, 'Avant chaque question, DÉCLIC enregistre une prévision de réussite calculée uniquement à partir de vos réponses précédentes. Elle vient du ',
        h('strong', {text: 'modèle de référence O08'}), ` (${o.reference_model.id}) : ${o.reference_model.formula}, où c est le hasard de la question et d la difficulté fixée par le niveau. Ce n’est pas un réseau de neurones : il est transparent et fonctionne avec un seul apprenant.`),
      h('p', {text: `Il s’abstient tant qu’une compétence a moins de ${o.reference_model.min_skill_history} réponses. Une prévision n’est jamais modifiée après coup : elle est horodatée avant votre réponse et comparée ensuite au résultat.`}),
      h('p', {text: 'Les réseaux O08 entraînés (EnhancedGRU) ne reçoivent pas vos réponses. Ils ont été entraînés sur d’autres tâches et leur contrat d’entrée refuse tout autre domaine ; leur faire lire vos données serait un réétiquetage, pas une prévision. Ils restent testables sur leurs propres données réelles dans le Laboratoire.'}),
      h('div', {class: 'table-scroll'}, h('table', {}, h('thead', {}, h('tr', {}, ['Réseau servi', 'Base · instrument', 'Sur vos données'].map(t => h('th', {text: t})))),
        h('tbody', {}, o.neural_models.map(m => h('tr', {}, h('td', {class: 'mono', text: m.model_id}), h('td', {text: `${m.source} · ${m.instrument}`}), h('td', {text: `S’abstient. ${m.reason}`}))))))
    );
    let quality;
    if (!q.scored) {
      quality = h('p', {class: 'status-line', text: `Aucune prévision évaluée pour l’instant : ${o.abstained} question(s) sans prévision faute de données. Les prévisions commencent après 5 réponses dans une compétence.`});
    } else {
      const better = q.skill_vs_baseline != null && q.skill_vs_baseline > 0;
      quality = h('div', {class: 'sheet pad'},
        h('div', {class: 'stat-row'}, stat(q.scored, 'prévisions évaluées'), stat(fmt.pct(q.mean_predicted), 'réussite prévue en moyenne'), stat(fmt.pct(q.observed_rate), 'réussite observée'),
          stat(num(q.brier_model), `score de Brier du modèle, plus bas = meilleur (taux simple : ${num(q.brier_baseline)})`)),
        h('p', {class: 'verdict-text', text: q.skill_vs_baseline == null ? '' : better
          ? `Sur vos données, le modèle de référence prévoit mieux que le simple taux de réussite (gain de ${Math.round(q.skill_vs_baseline * 100)} % sur le score de Brier).`
          : `Sur vos données, le modèle de référence ne prévoit pas mieux que le simple taux de réussite (son score de Brier est ${Math.abs(Math.round(q.skill_vs_baseline * 100))} % moins bon). C’est un résultat, pas une erreur d’affichage : avec peu de données, un modèle simple peut perdre contre une moyenne.`}),
        q.rolling.length ? rollingChart(q) : h('p', {class: 'fine', text: `L’évolution de la qualité s’affiche par tranches de ${q.window} prévisions évaluées (vous en avez ${q.scored}).`}),
        q.calibration ? calibrationTable(q) : h('p', {class: 'fine', text: `La calibration (prévu contre observé par tranche) s’affiche à partir de ${q.calibration_min} prévisions évaluées.`}));
    }
    const recent = o.predictions.slice(-15).reverse();
    const table = recent.length ? h('div', {class: 'table-scroll'}, h('table', {},
      h('caption', {text: 'Les 15 dernières prévisions évaluées (enregistrées avant la réponse)'}),
      h('thead', {}, h('tr', {}, ['Date', 'Exercice', 'Prévu', 'Taux simple', 'Résultat'].map(t => h('th', {text: t})))),
      h('tbody', {}, recent.map(r => h('tr', {}, h('td', {text: fmt.dateTime(r.at)}), h('td', {text: `${r.title} · N${r.level}`}),
        h('td', {class: 'cat-forecast', text: fmt.pct(r.p)}), h('td', {text: fmt.pct(r.baseline)}), h('td', {text: r.y ? 'réussi' : 'manqué'})))))) : null;
    const upcoming = h('div', {class: 'table-scroll'}, h('table', {},
      h('caption', {text: 'Prochaines étapes : probabilité de réussite prévue maintenant'}),
      h('thead', {}, h('tr', {}, ['Exercice', 'Niveau', 'Prévision'].map(t => h('th', {text: t})))),
      h('tbody', {}, o.upcoming.map(u => h('tr', {}, h('td', {text: u.title}), h('td', {text: `N${u.level}${u.available ? '' : ' (prérequis)'}`}),
        h('td', {class: u.status === 'ok' ? 'cat-forecast' : 'fine', text: u.status === 'ok' ? fmt.pct(u.p) : `pas de prévision : ${u.n_skill}/${u.needed} réponses`}))))));
    return h('section', {class: 'section', id: 'o08', 'aria-labelledby': 'o08-title'},
      h('h2', {id: 'o08-title', text: 'O08 sur mes données'}),
      h('p', {class: 'sub', text: 'Prévoir la réussite à la prochaine question à partir de la suite de vos tentatives, puis vérifier. Avec un seul apprenant, cela teste le modèle sur vous, pas sa validité pour les autres.'}),
      explain, h('h3', {class: 'h3', style: 'margin-top:24px', text: 'Prévisions contre résultats réels'}), quality, table,
      h('h3', {class: 'h3', style: 'margin-top:24px', text: 'Mes prochains exercices'}), upcoming,
      h('div', {class: 'actions', style: 'margin-top:16px'}, h('a', {class: 'btn btn-secondary', href: api.exportUrl(p.learner.id), download: `declic-${p.learner.name}.json`, text: 'Exporter mes tentatives (format O08)'}),
        h('span', {class: 'fine', text: 'Un fichier JSON : vos réponses horodatées, les prévisions enregistrées et les groupes au format de l’encodeur O08.'})));
  }

  function rollingChart(q) {
    const W = 720, H = 200, pad = 40, n = q.rolling.length;
    const maxB = Math.max(0.3, ...q.rolling.flatMap(r => [r.brier_model, r.brier_baseline]));
    const x = i => pad + (n === 1 ? (W - 2 * pad) / 2 : i * (W - 2 * pad) / (n - 1));
    const y = v => H - pad - v / maxB * (H - 2 * pad);
    const svg = s('svg', {viewBox: `0 0 ${W} ${H}`, class: 'chart', role: 'img', 'aria-label': 'Score de Brier par tranche de prévisions : plus bas est meilleur'});
    for (const v of [0, maxB / 2, maxB]) svg.append(s('line', {x1: pad, x2: W - pad, y1: y(v), y2: y(v), class: 'grid'}), txt(2, y(v) + 4, v.toLocaleString('fr-FR', {maximumFractionDigits: 2})));
    const line = key => q.rolling.map((r, i) => `${i ? 'L' : 'M'}${x(i)} ${y(r[key])}`).join(' ');
    svg.append(s('path', {d: line('brier_baseline'), class: 's-base'}), s('path', {d: line('brier_model'), class: 's-model'}));
    q.rolling.forEach((r, i) => svg.append(txt(x(i), H - 12, `${r.from}–${r.to}`, {'text-anchor': 'middle'})));
    svg.append(txt(W - pad, 16, 'pointillé : modèle de référence · trait plein : taux simple · plus bas = meilleur', {'text-anchor': 'end'}));
    return h('figure', {}, svg, h('figcaption', {class: 'fine', text: `Qualité des prévisions par tranches de ${q.window} : si le modèle apprend utilement de vos données, son score de Brier baisse et passe sous celui du taux simple.`}));
  }

  function calibrationTable(q) {
    return h('div', {class: 'table-scroll'}, h('table', {},
      h('caption', {text: 'Calibration : quand le modèle prévoit X %, réussissez-vous environ X % du temps ?'}),
      h('thead', {}, h('tr', {}, ['Tranche prévue', 'Prévisions', 'Moyenne prévue', 'Réussite observée'].map(t => h('th', {text: t})))),
      h('tbody', {}, q.calibration.map(b => h('tr', {}, h('td', {text: `${Math.round(b.from * 100)}–${Math.round(b.to * 100)} %`}), h('td', {text: b.count}),
        h('td', {text: fmt.pct(b.mean_predicted)}), h('td', {text: fmt.pct(b.observed)}))))));
  }

  L.booted();
  boot();
})(window.Learn);
