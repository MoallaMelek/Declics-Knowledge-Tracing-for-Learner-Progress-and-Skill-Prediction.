'use strict';
// Vue simple du parcours : « En bref » (observé + lecture) et « Le prochain essai » (prévision + révélation).
// Aucun calcul nouveau : tout vient des adaptateurs digest() / nextStep() et de la révélation servie.
(function (L) {
  const {h, s, put, reducedMotion} = L.dom, A = L.adapters;

  function create({store, constellation, onReveal, onResearch}) {
    const summary = document.getElementById('summary'), ahead = document.getElementById('ahead');
    let lastRevealKey = null;

    const tag = (kind, text) => h('span', {class: `cat cat-${kind}`, text});
    const moment = snap => `${A.stepName(snap.source) === 'groupe' ? 'Groupe' : 'Jour actif'} ${snap.cutoff} sur ${snap.steps_total}`;
    const unitPlural = (snap, n) => snap.source === 'singpad' ? `groupe${n > 1 ? 's' : ''} d’enregistrements` : `jour${n > 1 ? 's' : ''} actif${n > 1 ? 's' : ''}`;
    const name = (snap, k) => snap.source === 'singpad' ? `Concept C${k}` : 'Score global du jour';

    function focusConcept(k) {
      constellation.select(k);
      document.getElementById('stage').scrollIntoView({behavior: reducedMotion() ? 'auto' : 'smooth', block: 'start'});
    }

    function conceptList(snap, items, empty) {
      if (!items.length) return h('p', {class: 'empty-line', text: empty});
      return h('ul', {class: 'concepts'}, items.slice(0, 6).map(it => h('li', {},
        h('button', {type: 'button', class: 'concept', style: `--c:${it.meta.color}`, onclick: () => focusConcept(it.k),
          'aria-label': `${name(snap, it.k)} : ${it.meta.label}. Voir sur la carte.`},
          h('span', {class: 'concept-dot', 'aria-hidden': 'true'}),
          h('span', {class: 'concept-name', text: name(snap, it.k)}),
          h('span', {class: 'concept-state', text: it.meta.label}),
          h('span', {class: 'concept-proof', text: `${it.groups} ${unitPlural(snap, it.groups)}${snap.source === 'singpad' ? ` · ${A.num(it.notes)} notes` : ''} · récent ${A.pct(it.recent, 0)}`})))),
        items.length > 6 ? h('li', {class: 'more', text: `et ${items.length - 6} autre(s), visibles sur la carte`}) : null);
    }

    function renderSummary(st) {
      const snap = st.snapshot, d = A.digest(snap), singpad = snap.source === 'singpad';
      const lead = singpad
        ? [`Sur les ${d.steps} ${unitPlural(snap, d.steps)} observés, `, h('strong', {text: d.historical.display}), ' des notes évaluées ont été réussies',
           d.recent.sufficient ? [', et ', h('strong', {text: d.recent.display}), ' sur les trois derniers.'] : '.']
        : [`Sur les ${d.steps} ${unitPlural(snap, d.steps)} observés, le score quotidien moyen est de `, h('strong', {text: d.historical.display}),
           d.recent.sufficient ? [', et de ', h('strong', {text: d.recent.display}), ' sur les trois derniers jours.'] : '.'];
      const change = d.change.sufficient
        ? `Les trois dernières séances se situent ${A.points(Math.abs(d.change.value)).replace('+', '')} ${d.change.value >= 0 ? 'au-dessus' : 'en dessous'} des précédentes.`
        : 'Trop tôt pour parler d’une évolution : il faut au moins trois séances avant les trois dernières.';
      const rec = d.recommendation;
      put(summary,
        h('div', {class: 'chapter-head'}, h('div', {},
          h('h2', {id: 'summary-title', text: 'En bref'}),
          h('p', {class: 'moment', text: `${moment(snap)} · ce que montrent les séances déjà observées`}))),
        h('div', {class: 'brief'},
          h('div', {class: 'brief-main'},
            tag('observed', 'Observé'),
            h('p', {class: 'brief-lead'}, lead),
            h('p', {class: 'brief-change', text: change}),
            h('dl', {class: 'facts'},
              h('div', {}, h('dt', {text: 'Séances observées'}), h('dd', {text: `${d.steps} sur ${d.total}`})),
              singpad ? h('div', {}, h('dt', {text: 'Concepts évalués'}), h('dd', {text: `${d.concepts} sur ${d.K}`})) : null,
              h('div', {}, h('dt', {text: 'Assez observés pour être qualifiés'}), h('dd', {text: d.sufficiency.display})))),
          h('div', {class: 'brief-reading'},
            tag('reading', 'Lecture des observations'),
            h('h3', {text: 'À surveiller'}),
            conceptList(snap, d.attention, d.thin === d.concepts
              ? 'Rien à signaler pour l’instant : aucun concept n’a encore assez d’observations pour être qualifié.'
              : 'Aucun concept suffisamment observé ne montre de résultats faibles, en baisse ou variables.'),
            h('h3', {text: 'Résultats réguliers ou en hausse'}),
            conceptList(snap, d.steady, 'Aucun pour l’instant.'),
            d.thin ? h('p', {class: 'fine', text: `${d.thin} concept(s) observé(s) trop peu de fois pour être qualifié(s) : il faut au moins 3 séances${singpad ? ' et 10 notes' : ''}. Ce n’est pas un échec, c’est un manque de recul.`}) : null,
            h('div', {class: 'practice'},
              h('h3', {text: 'Piste de pratique'}),
              rec.status === 'abstained'
                ? h('p', {class: 'fine', text: `${rec.reason} DÉCLIC s’abstient plutôt que d’inventer un exercice.`})
                : rec.suggestions.map(r => h('p', {}, `Reprendre l’exercice source ${r.exercise}, qui contient ${r.concepts.map(c => singpad ? 'C' + c : 'ce score').join(', ')}. `, h('span', {class: 'fine', text: r.caveat})))))),
        h('p', {class: 'fine source-note', text: singpad
          ? 'SingPAD identifie ses concepts par un numéro et note automatiquement chaque note chantée (réussie ou non). DÉCLIC ne donne pas de nom musical à ces numéros : ce serait inventer une taxonomie.'
          : 'Yousician fournit un seul score agrégé par jour actif (ukulélé) : il n’y a pas de concepts séparés à surveiller.'}));
    }

    // Échelle 0–100 : prévision en pointillé ocre, résultat révélé en vert, l'écart entre les deux reste visible.
    function measure(snap, n, rv) {
      const W = 640, H = 92, x = v => 20 + v * (W - 40);
      const svg = s('svg', {viewBox: `0 0 ${W} ${H}`, class: 'measure', role: 'img',
        'aria-label': rv ? `Prévu ${A.forecast(snap.source, n.value)}, observé ${A.pct(rv.observed_mean)}.` : `Prévu ${A.forecast(snap.source, n.value)}. Résultat réel encore caché.`});
      svg.append(s('rect', {x: 20, y: 40, width: W - 40, height: 6, rx: 3, class: 'ms-track'}));
      for (const v of [0, .25, .5, .75, 1]) svg.append(s('line', {x1: x(v), x2: x(v), y1: 36, y2: 50, class: 'ms-tick'}), s('text', {x: x(v), y: 70, 'text-anchor': 'middle', class: 'ms-txt', text: `${100 * v}`}));
      const fx = x(n.value);
      svg.append(s('g', {class: 'ms-forecast'}, s('line', {x1: fx, x2: fx, y1: 14, y2: 54}), s('circle', {cx: fx, cy: 43, r: 9}),
        s('text', {x: fx, y: 10, 'text-anchor': 'middle', text: 'prévu'})));
      if (rv) {
        const ox = x(rv.observed_mean), fresh = lastRevealKey === A.revealKey(snap);
        svg.append(s('line', {x1: Math.min(fx, ox), x2: Math.max(fx, ox), y1: 84, y2: 84, class: 'ms-gap'}));
        svg.append(s('g', {class: 'ms-revealed' + (fresh ? ' arriving' : ''), style: `--from:${(fx - ox).toFixed(1)}px`},
          s('line', {x1: ox, x2: ox, y1: 26, y2: 60}), s('circle', {cx: ox, cy: 43, r: 9}),
          s('text', {x: ox, y: 82 - 2, 'text-anchor': 'middle', dy: '-.2em', text: 'révélé'})));
      } else svg.append(s('g', {class: 'ms-hidden'}, s('rect', {x: W - 140, y: 26, width: 120, height: 34, rx: 4}),
        s('text', {x: W - 80, y: 48, 'text-anchor': 'middle', text: 'résultat caché'})));
      return svg;
    }

    function renderAhead(st) {
      const snap = st.snapshot, n = A.nextStep(snap), singpad = snap.source === 'singpad';
      const head = h('div', {class: 'chapter-head'}, h('div', {},
        h('h2', {id: 'ahead-title', text: 'Le prochain essai'}),
        h('p', {class: 'moment', text: n.status === 'end' ? `${moment(snap)} · fin du parcours enregistré` : `Ce que le réseau estime pour la séance ${snap.cutoff + 1}, sans connaître son résultat`})));
      if (n.status === 'end') {
        put(ahead, head, h('div', {class: 'forecast-card is-empty'},
          h('p', {class: 'big', text: 'Il n’y a plus de séance à prévoir.'}),
          h('p', {text: 'C’est la dernière séance enregistrée de ce parcours : aucun résultat futur n’existe dans les données. Reculez dans le temps avec la frise en bas de l’écran pour voir une prévision et la comparer au résultat réel.'})));
        return;
      }
      if (n.status === 'abstained') {
        put(ahead, head, h('div', {class: 'forecast-card is-empty'},
          tag('forecast', 'Prévision'),
          h('p', {class: 'big', text: 'Pas de prévision à ce moment.'}),
          h('p', {text: `${n.reason} Avancez d’une séance pour lui donner plus d’historique.`})));
        return;
      }
      const rv = st.reveals[A.revealKey(snap)] || null;
      const value = A.forecast(snap.source, n.value);
      const sentence = singpad
        ? ['Pour le groupe ', String(n.index + 1), `, le réseau estime en moyenne `, h('strong', {class: 'fc', text: value}), ' de chances de réussir une note.']
        : ['Pour le jour actif ', String(n.index + 1), ', le réseau prévoit un score de ', h('strong', {class: 'fc', text: value}), '.'];
      const gap = rv ? rv.predicted_mean - rv.observed_mean : null;
      put(ahead, head,
        h('div', {class: 'forecast-card' + (rv ? ' is-revealed' : '')},
          h('div', {class: 'fc-main'},
            tag('forecast', 'Prévision du réseau'),
            h('p', {class: 'big'}, sentence),
            measure(snap, n, rv),
            rv ? h('div', {class: 'fc-result', role: 'status'},
              tag('revealed', 'Résultat révélé'),
              h('p', {}, singpad ? 'Réellement : ' : 'Score réel : ', h('strong', {class: 'rv', text: singpad ? `${A.pct(rv.observed_mean)} des notes réussies` : `${A.num(100 * rv.observed_mean, 1)} / 100`}),
                singpad ? ` (moyenne des ${rv.comparison.length} concepts).` : '.'),
              h('p', {class: 'fine', text: Math.abs(gap) < 0.005 ? 'La prévision tombe presque exactement sur le résultat. Une seule séance ne permet pourtant aucune conclusion.'
                : `Écart de ${A.points(Math.abs(gap)).replace('+', '')} : le réseau a ${gap > 0 ? 'surestimé' : 'sous-estimé'} ce résultat. Une seule séance ne permet aucune conclusion ; la vue chercheur compare à des références simples.`}))
              : h('div', {class: 'actions'},
                  h('button', {type: 'button', class: 'btn btn-forecast', text: 'Révéler le résultat réel', onclick: e => { e.currentTarget.disabled = true; lastRevealKey = A.revealKey(snap); onReveal(); }}),
                  h('span', {class: 'fine', text: 'Le serveur ne le transmet qu’après la prévision, avec un reçu qui les lie.'}))),
          h('div', {class: 'fc-notes'},
            h('h3', {text: 'Ce que c’est'}),
            h('p', {text: singpad
              ? `La probabilité qu’une note chantée soit juste, pour chacun des ${n.concepts.length} concepts évalués à ce groupe (exercice source ${n.exercise || 'non précisé'}), puis leur moyenne simple.`
              : 'Un score continu entre 0 et 100 pour le prochain jour de pratique, prévu sans connaître ce jour ni ses exercices.'}),
            h('p', {text: `Il ne s’appuie que sur les séances 1 à ${snap.cutoff}. Le réseau entraîné (un GRU) n’a jamais vu ce parcours pendant son apprentissage.`}),
            h('h3', {text: 'Ce que ce n’est pas'}),
            h('p', {text: singpad
              ? 'Ni une certitude, ni une note de niveau. Une probabilité de réussite n’est pas la confiance du modèle, et aucune incertitude individuelle n’a été validée.'
              : 'Ni une probabilité, ni une certitude. Aucune incertitude individuelle n’a été validée.'}),
            singpad && n.concepts.length > 1 ? h('details', {class: 'alt'}, h('summary', {text: `Détail par concept (${n.concepts.length})`}),
              h('ul', {class: 'per-concept'}, n.concepts.map(c => {
                const r = rv && rv.comparison.find(x => x.concept === c.k);
                return h('li', {}, h('span', {text: `C${c.k}`}), h('span', {class: 'fc', text: `prévu ${A.pct(c.value)}`}), r ? h('span', {class: 'rv', text: `réel ${A.pct(r.observed)} sur ${A.num(r.notes)} note(s)`}) : null);
              }))) : null,
            h('button', {type: 'button', class: 'btn btn-quiet', text: 'Voir comment le réseau calcule cette valeur', onclick: onResearch}))));
    }

    function render(st) {
      if (!st.snapshot) return;
      renderSummary(st); renderAhead(st);
      if (lastRevealKey && st.reveals[lastRevealKey]) requestAnimationFrame(() => { lastRevealKey = null; });
    }
    return {render};
  }
  L.summary = {create};
})(window.Living);
