'use strict';
// Laboratoire : trois lectures indépendantes de l'API. Chacune a son chargement, son erreur et sa reprise ;
// une panne n'efface jamais les autres blocs. Aucune valeur n'est calculée hors des moyennes déjà publiées.
(function () {
  const $ = id => document.getElementById(id);
  const nf = d => new Intl.NumberFormat('fr-FR', {minimumFractionDigits: d, maximumFractionDigits: d});
  const num = (v, d = 4) => v === null || v === undefined || !isFinite(v) ? '—' : nf(d).format(v);
  const SOURCES = {
    singpad: {name: 'Chant · SingPAD', target: 'Réussite des notes du prochain groupe d’enregistrements, par concept source'},
    yousician: {name: 'Ukulélé · Yousician', target: 'Score agrégé du prochain jour actif (continu, pas une probabilité)'},
    amme: {name: 'Clavier · AMME', target: 'Score de similarité mélodique du prochain bloc (pas un pourcentage de notes justes)'}
  };
  const METRIC = {log_loss: 'perte logarithmique', mae: 'erreur absolue moyenne'};
  const MODE = {synthetic_fixture: 'Données synthétiques d’intégration (vérifient la mécanique, pas l’apprentissage)', private_research_data: 'Parcours réels du jeu de test (données privées)'};

  function h(tag, attrs, ...children) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') n.className = v; else if (k === 'text') n.textContent = v;
      else if (k.startsWith('on')) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v);
    }
    for (const c of children.flat(Infinity)) if (c !== null && c !== undefined && c !== false) n.append(c instanceof Node ? c : document.createTextNode(String(c)));
    return n;
  }
  const table = (head, rows, caption) => h('div', {class: 'table-scroll'}, h('table', {}, caption ? h('caption', {text: caption}) : null,
    h('thead', {}, h('tr', {}, head.map(x => h('th', {scope: 'col', text: x})))),
    h('tbody', {}, rows.map(r => h('tr', {}, r.map(v => h('td', {}, v === null || v === undefined ? '—' : v)))))));

  async function get(url) {
    const guard = new AbortController(), timer = setTimeout(() => guard.abort(), 15000);
    try {
      const r = await fetch(url, {signal: guard.signal, cache: 'no-store'});
      const body = await r.json().catch(() => null);
      return {ok: r.ok, status: r.status, body};
    } finally { clearTimeout(timer); }
  }
  function failure(target, what, retry, detail) {
    target.replaceChildren(h('div', {class: 'problem'},
      h('h3', {text: `${what} indisponible`}),
      h('p', {text: detail || 'Le serveur DÉCLIC ne répond pas. Vérifiez qu’il est lancé (Launch.ps1), puis réessayez.'}),
      h('div', {class: 'actions'}, h('button', {type: 'button', class: 'btn btn-primary', text: 'Réessayer', onclick: retry}))));
  }
  // replaceChildren() prints "null" for optional parts; they are dropped instead.
  const put = (target, ...parts) => target.replaceChildren(...parts.flat(Infinity).filter(x => x !== null && x !== undefined && x !== false));
  const loading = (target, text) => target.replaceChildren(h('p', {class: 'loading', text}));

  async function system() {
    const out = $('system'); loading(out, 'Lecture de l’état du serveur…');
    let r; try { r = await get('/api/readiness'); } catch (e) { return failure(out, 'L’état du système', system); }
    const d = r.body;
    if (!d || !d.sources) return failure(out, 'L’état du système', system, 'Le serveur a répondu sans l’état attendu : vérifiez qu’il s’agit bien du serveur DÉCLIC Phase 8 ou ultérieure.');
    put(out,
      h('p', {class: 'verdict ' + (d.ready ? 'is-ok' : 'is-warn'), text: d.ready ? 'Démonstration prête : modèles valides, données préparées et inférence vérifiées.' : 'Démonstration partielle : au moins une base n’est pas prête. Le Parcours affichera un diagnostic pour celle-ci.'}),
      h('dl', {class: 'kv'},
        h('div', {}, h('dt', {text: 'Données'}), h('dd', {text: MODE[d.data_mode] || d.data_mode || '—'})),
        h('div', {}, h('dt', {text: 'Version'}), h('dd', {text: `${d.application || '—'} ${d.version || ''}`})),
        h('div', {}, h('dt', {text: 'Révision du code'}), h('dd', {}, h('code', {text: d.revision ? d.revision.slice(0, 12) : '—'}), d.branch ? ` · ${d.branch}` : ''))),
      table(['Base', 'Prête', 'Modèle servi', 'Architecture', 'Parcours', 'Génération'], Object.entries(d.sources).map(([k, s]) => [
        (SOURCES[k] || {name: k}).name, s.ready ? 'oui' : `non (${s.reason || 'raison inconnue'})`, h('code', {text: s.model_id || '—'}),
        s.architecture || '—', s.learners === undefined ? '—' : String(s.learners), h('code', {text: s.generation ? s.generation.slice(0, 12) + '…' : '—'})])),
      d.ready ? null : h('p', {class: 'fine', text: d.recovery || ''}));
  }

  async function bench() {
    const out = $('bench'), limits = $('limits'); loading(out, 'Chargement des résultats publiés…');
    let r; try { r = await get('/api/v6/o08/demo/research'); } catch (e) { failure(limits, 'Les limites publiées', bench); return failure(out, 'Les bancs d’essai', bench); }
    const d = r.body;
    if (!r.ok || !d || !Array.isArray(d.comparisons)) { failure(limits, 'Les limites publiées', bench); return failure(out, 'Les bancs d’essai', bench, 'Les résultats Phase 7 ne sont pas lisibles sur ce serveur (artefacts manquants ?).'); }
    const metricOf = src => (d.comparisons.find(c => c.source === src) || {}).metric;
    const rows = Object.entries(d.means || {}).map(([src, m]) => {
      const metric = metricOf(src), lower = m.neural < m.control ? 'réseau' : m.neural > m.control ? 'contrôle' : 'égalité';
      return h('li', {class: 'bench-row'},
        h('div', {class: 'bench-name'}, h('h3', {text: (SOURCES[src] || {name: src}).name}), h('p', {class: 'fine', text: `${METRIC[metric] || metric}, moyenne sur ${d.comparisons.filter(c => c.source === src).length} découpages`})),
        h('div', {class: 'bench-bars'}, bars(m)),
        h('p', {class: 'bench-read', text: lower === 'réseau' ? 'Le réseau obtient la valeur moyenne la plus basse.' : lower === 'contrôle' ? 'Le contrôle obtient la valeur moyenne la plus basse.' : 'Valeurs identiques.'}));
    });
    put(out,
      h('ul', {class: 'bench'}, rows),
      h('p', {class: 'fine', text: `${d.scope} ${d.completed_neural_runs} entraînements neuronaux terminés (${d.completed_core_neural_runs} principaux) ; ${d.interrupted_dense_attention_runs_excluded} exécution interrompue exclue. Promotion dans le registre actif (texte du serveur) : ${d.promotion}.`}),
      h('details', {class: 'alt'}, h('summary', {text: 'Détail par découpage'}),
        table(['Base', 'Graine', 'Mesure', 'Réseau choisi', 'Test réseau', 'Contrôle choisi', 'Test contrôle', 'Contrôle appris', 'Test contrôle appris'],
          d.comparisons.map(c => [(SOURCES[c.source] || {name: c.source}).name, String(c.seed), METRIC[c.metric] || c.metric, c.selected, num(c.neural_test, 5),
            c.selected_control || '—', num(c.control_test, 5), c.selected_learned_control || '—', num(c.learned_control_test, 5)]),
          'Sélection sur validation avant lecture du test. Les contrôles servent à la comparaison scientifique ; aucune prévision de l’application ne passe par eux.')));
    put(limits,
      h('ul', {class: 'limit-list'}, (d.limitations || []).map(t => h('li', {text: t}))),
      d.work_status ? h('div', {class: 'status-list'}, h('h3', {text: 'État des travaux'}),
        h('dl', {class: 'kv'}, Object.entries(d.work_status).map(([k, v]) => h('div', {}, h('dt', {text: ({experiments: 'Expériences', skill_states: 'États descriptifs', prospective: 'Collecte prospective', taxonomy: 'Taxonomie', piano: 'Piano'})[k] || k}), h('dd', {text: v}))))) : null);
  }

  // Deux barres sur la même échelle : réseau (encre) et contrôle (bleu d'édition). L'écart-type du réseau est indiqué.
  function bars(m) {
    const max = Math.max(m.neural + (m.neural_sd || 0), m.control) * 1.08 || 1;
    const bar = (label, v, cls, extra) => h('div', {class: 'bar ' + cls},
      h('span', {class: 'bar-label', text: label}),
      h('span', {class: 'bar-track'}, h('span', {class: 'bar-fill', style: `width:${(100 * v / max).toFixed(2)}%`})),
      h('span', {class: 'bar-value', text: num(v) + (extra || '')}));
    return [bar('Réseau', m.neural, 'is-neural', m.neural_sd ? ` ± ${num(m.neural_sd, 4)}` : ''), bar('Contrôle', m.control, 'is-control')];
  }

  async function models() {
    const out = $('models'); loading(out, 'Chargement du registre…');
    let r; try { r = await get('/api/v5/musical/models'); } catch (e) { return failure(out, 'Le registre des modèles', models); }
    const d = r.body;
    if (!r.ok || !d || !Array.isArray(d.models)) return failure(out, 'Le registre des modèles', models, 'Le registre n’a pas pu être lu sur ce serveur.');
    if (!d.models.length) { out.replaceChildren(h('p', {class: 'empty-state', text: 'Aucun modèle dans le registre de ce serveur.'})); return; }
    put(out, h('ul', {class: 'model-list'}, d.models.map(m => {
      const t = m.test || {}, metric = t.log_loss !== undefined ? ['perte logarithmique', t.log_loss] : ['erreur absolue moyenne', t.mae];
      return h('li', {class: 'model'},
        h('div', {}, h('h3', {text: (SOURCES[m.source] || {name: m.source}).name}), h('p', {class: 'fine'}, h('code', {text: m.id}), ` · ${m.model}`)),
        h('p', {text: (SOURCES[m.source] || {}).target || m.target}),
        h('p', {class: 'model-metric'}, `Test : ${metric[0]} `, h('strong', {text: num(metric[1])}), t.observed_targets ? ` sur ${new Intl.NumberFormat('fr-FR').format(t.observed_targets)} cibles` : ''),
        m.citation ? h('p', {class: 'fine', text: m.citation}) : null,
        m.limitations && m.limitations.length ? h('details', {class: 'alt'}, h('summary', {text: 'Limites déclarées (en anglais dans le registre)'}), h('ul', {}, m.limitations.map(x => h('li', {text: x})))) : null);
    })), d.message ? h('p', {class: 'fine', text: d.message}) : null);
  }

  system(); bench(); models();
})();
