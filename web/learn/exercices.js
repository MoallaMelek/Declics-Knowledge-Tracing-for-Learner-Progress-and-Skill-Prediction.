'use strict';
// Bibliothèque : chaque exercice avec sa fiche en 10 champs, ses niveaux et ses références.
(function (L) {
  const {h, api} = L;
  const app = document.getElementById('app');
  const PURPOSE = {'développer': 'Entraîne', 'mesurer': 'Mesure', 'développer et mesurer': 'Entraîne et mesure'};
  const RESPONSE = {choice: 'boutons', staff: 'portée + boutons', keyboard: 'clavier virtuel', tap: 'barre d’espace'};
  let catalog, filter = 'all';

  async function boot() {
    try { catalog = await api.catalog(); render(); }
    catch (e) { L.problem(app, e, boot); }
  }

  function render() {
    const skills = Object.fromEntries(catalog.skills.map(s => [s.id, s]));
    const filters = h('div', {class: 'filters', role: 'group', 'aria-label': 'Filtrer par compétence'},
      [['all', 'Toutes']].concat(catalog.skills.map(s => [s.id, s.label])).map(([id, label]) =>
        h('button', {type: 'button', class: 'btn btn-secondary', 'aria-pressed': String(filter === id), text: label, onclick: () => { filter = id; render(); }})));
    const shown = catalog.exercises.filter(e => filter === 'all' || e.skill === filter);
    const prereqOf = id => (catalog.prerequisites[id] || []).map(p => `${catalog.exercises.find(e => e.id === p.exercise)?.title || p.exercise}, niveau ${p.level}`);
    const cards = shown.map(e => {
      const dd = (term, ...content) => [h('dt', {text: term}), h('dd', {}, ...content)];
      const levels = h('table', {}, h('thead', {}, h('tr', {}, ['Niveau', 'Ce qui change', 'Hasard', 'Maîtrise', ''].map(t => h('th', {text: t})))),
        h('tbody', {}, e.difficulty.levels.map(lv => h('tr', {}, h('td', {text: `${lv.level} · ${lv.label}`}), h('td', {text: lv.criteria}),
          h('td', {text: lv.chance == null ? '—' : `${Math.round(lv.chance * 100)} %`}),
          h('td', {text: lv.mastery_min ? `${lv.mastery_min} / ${e.mastery_window}` : '—'}),
          h('td', {}, h('a', {class: 'btn btn-quiet', href: `/web/seance.html?exercise=${encodeURIComponent(e.id)}&level=${lv.level}`, text: 'S’entraîner'}))))));
      return h('article', {class: 'card', id: e.id, 'aria-labelledby': `t-${e.id}`},
        h('header', {}, h('h2', {id: `t-${e.id}`, text: e.title}),
          h('span', {}, h('span', {class: 'tag', text: skills[e.skill].label}), ' ', h('span', {class: 'tag tag-good', text: PURPOSE[e.purpose]}), ' ', h('span', {class: 'tag', text: `réponse : ${RESPONSE[e.response]}`}))),
        h('dl', {},
          dd('1 · Objectif', e.objective),
          dd('2 · Compétence évaluée', e.skills_assessed.map(s => skills[s].label).join(', ')),
          dd('3 · Difficulté', h('p', {text: e.difficulty.basis}), h('div', {class: 'table-scroll'}, levels)),
          dd('4 · Prérequis', prereqOf(e.id).length ? prereqOf(e.id).join(' ; ') : 'Aucun'),
          dd('5 · Consignes', h('ol', {}, e.instructions.map(i => h('li', {text: i})))),
          dd('6 · Entrées', e.inputs),
          dd('7 · Résultat attendu', e.expected),
          dd('8 · Correction', e.correction, e.mastery_window ? h('p', {class: 'fine', text: `Maîtrise d’un niveau : au moins 80 % de justes sur les ${e.mastery_window} dernières réponses ET un score très improbable au hasard (test binomial, p < 0,05) ; le minimum exact figure dans la colonne « Maîtrise ».`}) : h('p', {class: 'fine', text: 'Exercice de mesure : pas de maîtrise, un résultat chiffré.'})),
          dd('9 · Métriques', h('ul', {}, e.metrics.map(m => h('li', {text: m})))),
          dd('10 · Références', h('ul', {}, e.references.map(r => h('li', {}, r.url ? h('a', {href: r.url, rel: 'noopener', target: '_blank', text: r.citation}) : r.citation))))));
    });
    const refs = Object.values(catalog.references).sort((a, b) => a.citation.localeCompare(b.citation, 'fr'));
    app.replaceChildren(
      h('header', {class: 'page-head'},
        h('h1', {text: 'Bibliothèque d’exercices'}),
        h('p', {class: 'lede', text: `${catalog.exercises.length} exercices, ${catalog.exercises.reduce((n, e) => n + e.difficulty.levels.length, 0)} niveaux, tous faisables sans instrument. Chaque niveau dit précisément ce qui le rend plus difficile, et chaque exercice dit s’il entraîne une compétence, la mesure, ou les deux.`}),
        h('details', {}, h('summary', {text: 'Entraîner ou mesurer : quelle différence ?'}),
          h('p', {text: 'Un exercice qui entraîne donne une correction après chaque réponse et permet de réécouter. Une mesure suit un protocole fixe, sans correction pendant l’essai (par exemple l’escalier adaptatif du seuil de hauteur), pour obtenir un chiffre comparable d’une fois sur l’autre. Les exercices « entraîne et mesure » servent aux deux : chaque réponse est notée et alimente votre parcours.'}),
          h('p', {class: 'fine', text: 'Aucun exercice n’a encore été validé par un enseignant. Les seuils marqués « provisoires » sont des choix de DÉCLIC, pas des normes publiées.'}))),
      filters, h('div', {class: 'cards'}, cards),
      h('section', {class: 'section', 'aria-labelledby': 'ref-title'},
        h('h2', {id: 'ref-title', text: 'Références'}),
        h('p', {class: 'sub', text: 'Chaque référence est citée pour ce qu’elle établit, résumé à côté. Les liens mènent à la publication (DOI) ou à une page qui la décrit.'}),
        h('ol', {class: 'refs sheet pad'}, refs.map(r => h('li', {}, r.url ? h('a', {href: r.url, rel: 'noopener', target: '_blank', text: r.citation}) : h('span', {text: r.citation}), h('p', {text: r.supports}))))));
  }

  L.booted();
  boot();
})(window.Learn);
