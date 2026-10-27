'use strict';
// Séance : profil → « Commencer une séance » → questions corrigées par le serveur → bilan.
(function (L) {
  const {h, api, profile, fmt} = L;
  const app = document.getElementById('app');
  const params = new URLSearchParams(location.search);
  const SKILL = {hauteur: 'Hauteur', intervalles: 'Intervalles', accords: 'Accords', memoire: 'Mémoire mélodique', reproduction: 'Reproduction au clavier',
                 pulsation: 'Pulsation', rythme: 'Rythme', lecture: 'Lecture de notes', tonalite: 'Fonctions tonales'};
  let learner = null, session = null, cleanup = [];

  function screen(...children) {
    cleanup.forEach(f => { try { f(); } catch (e) { /* ignore */ } }); cleanup = [];
    L.audio.stop();
    app.replaceChildren(...children.filter(c => c != null && c !== false));
    const focus = app.querySelector('[data-autofocus]') || app.querySelector('h1, h2');
    if (focus) { if (!focus.hasAttribute('tabindex') && !/^(BUTTON|INPUT|A)$/.test(focus.tagName)) focus.setAttribute('tabindex', '-1'); focus.focus({preventScroll: false}); }
  }
  function fail(error, retry) { L.problem(app, error, retry); }

  // ---------------------------------------------------------------- profile
  async function boot() {
    try {
      const {id, list} = await profile.resolve();
      if (!id) return profileScreen(list);
      learner = await api.learner(id);
      if (params.get('bilan')) return summaryScreen(params.get('bilan'));
      startScreen();
    } catch (e) { fail(e, boot); }
  }

  function profileScreen(list) {
    const input = h('input', {type: 'text', id: 'name', maxlength: '40', autocomplete: 'nickname', required: true, 'data-autofocus': true});
    const error = h('p', {class: 'form-error', role: 'alert'});
    const form = h('form', {class: 'sheet pad profile-form', onsubmit: async e => {
      e.preventDefault();
      const name = input.value.trim();
      if (!name) { error.textContent = 'Indiquez un prénom ou un pseudonyme.'; input.focus(); return; }
      try { const created = await api.createLearner(name); profile.set(created.id); learner = await api.learner(created.id); startScreen(); }
      catch (err) { error.textContent = err.message; }
    }},
      h('div', {class: 'field'}, h('label', {for: 'name', text: 'Votre prénom ou un pseudonyme'}), input),
      h('p', {class: 'fine', text: 'Pas besoin d’instrument ni de compte : le profil reste sur cet ordinateur, dans la base locale de DÉCLIC. Vous pourrez revenir demain et retrouver votre historique.'}),
      error,
      h('div', {class: 'actions'}, h('button', {type: 'submit', class: 'btn btn-primary', text: 'Créer mon profil'})));
    const others = list.length ? h('section', {class: 'pick'}, h('h2', {class: 'h3', text: 'Ou reprendre un profil existant'}),
      h('ul', {class: 'pick-list'}, list.map(l => h('li', {},
        h('button', {type: 'button', class: 'btn btn-secondary', onclick: async () => { profile.set(l.id); learner = await api.learner(l.id); startScreen(); }},
          `${l.name}`), h('span', {class: 'fine', text: ` · ${l.answers} réponse(s) · dernière activité ${fmt.ago(l.last_activity)}`}))))) : null;
    screen(h('header', {class: 'page-head'}, h('h1', {text: 'Créer mon profil'}),
      h('p', {class: 'lede', text: 'Votre profil garde vos réponses, vos niveaux et vos séances pour mesurer votre progression d’un jour à l’autre.'})), form, others);
  }

  // ---------------------------------------------------------------- start
  function startScreen() {
    const focusEx = params.get('exercise'), focusLevel = Number(params.get('level'));
    const active = learner.active_session;
    const first = !learner.initial_assessment_done;
    let primary, primaryLabel, intro;
    if (focusEx && focusLevel) {
      primaryLabel = 'Commencer cet exercice';
      intro = h('p', {class: 'lede', text: `Séance ciblée choisie dans la bibliothèque : ${focusEx}, niveau ${focusLevel}. Elle compte dans votre parcours comme les autres.`});
      primary = () => begin({kind: 'ciblee', exercise: focusEx, level: focusLevel});
    } else if (active) {
      primaryLabel = `Reprendre ma séance (${active.progress.answered} / ${active.progress.total})`;
      intro = h('p', {class: 'lede', text: `Vous aviez commencé une ${fmt.KIND[active.kind].toLowerCase()} ${fmt.ago(active.created_at)}. Vous reprendrez à la question où vous vous étiez arrêté ; vos réponses déjà données sont conservées.`});
      primary = () => begin({kind: 'auto'});
    } else if (first) {
      primaryLabel = 'Commencer une séance';
      intro = h('p', {class: 'lede', text: 'Votre première séance est une évaluation initiale d’environ 10 minutes : 30 questions courtes pour situer votre oreille, votre sens du rythme et votre lecture. Il n’y a rien à réussir : elle sert à choisir vos premiers exercices.'});
      primary = () => begin({kind: 'auto'});
    } else {
      primaryLabel = 'Commencer une séance';
      intro = h('p', {class: 'lede', text: 'Une séance d’environ 10 minutes, composée à partir de vos derniers résultats : ce qui vous résiste, ce qui est nouveau, et une révision espacée.'});
      primary = () => begin({kind: 'auto'});
    }
    const needs = h('ul', {class: 'needs'},
      h('li', {}, h('strong', {text: 'Du son'}), ' : haut-parleurs ou casque, volume moyen.'),
      h('li', {}, h('strong', {text: 'Aucun instrument'}), ' : vous répondez avec la souris, le clavier de l’ordinateur et la barre d’espace.'),
      h('li', {}, h('strong', {text: 'Pas de micro'}), ' : rien n’est enregistré à part vos réponses.'));
    screen(
      h('header', {class: 'page-head'},
        h('p', {class: 'kicker', text: `Profil : ${learner.name}`}),
        h('h1', {text: active ? 'Votre séance vous attend' : first ? 'Bienvenue' : 'Prêt pour une séance ?'}), intro,
        h('div', {class: 'actions'},
          h('button', {type: 'button', class: 'btn btn-primary btn-big', id: 'start', 'data-autofocus': true, text: primaryLabel, onclick: primary}),
          active && !focusEx ? h('button', {type: 'button', class: 'btn btn-secondary', text: 'Commencer une nouvelle séance', onclick: () => begin({kind: learner.initial_assessment_done ? 'seance' : 'evaluation'})}) : null,
          h('a', {class: 'btn btn-quiet', href: '/web/parcours.html', text: 'Voir mon parcours'}))),
      h('section', {class: 'sheet pad'}, h('h2', {class: 'h3', text: 'Ce qu’il vous faut'}), needs),
      h('p', {class: 'fine switch'}, `Ce n’est pas vous ? `, h('button', {type: 'button', class: 'btn btn-quiet', text: 'Changer de profil', onclick: async () => { profile.clear(); profileScreen((await api.learners()).learners); }})));
    if (!L.audio.available()) app.prepend(h('div', {class: 'problem'}, h('h2', {text: 'Son indisponible'}), h('p', {text: 'Ce navigateur ne peut pas produire de son. Utilisez Edge, Chrome ou Firefox récents.'})));
  }

  async function begin(body) {
    try { L.audio.context(); } catch (e) { /* the item screen explains */ }
    try {
      const r = await api.startSession(learner.id, body);
      session = r.session;
      if (params.has('exercise')) history.replaceState(null, '', location.pathname);
      nextItem();
    } catch (e) { fail(e, () => begin(body)); }
  }

  // ---------------------------------------------------------------- items
  async function nextItem() {
    try {
      const r = await api.next(session.id);
      if (r.status === 'complete') return summaryScreen(session.id);
      itemScreen(r.item, r.progress);
    } catch (e) { fail(e, nextItem); }
  }

  function bar(progress, corrected) {
    const ratio = progress.total ? progress.answered / progress.total : 0;
    const label = corrected ? `question ${progress.answered} sur ${progress.total} · corrigée` : `question ${Math.min(progress.answered + 1, progress.total)} sur ${progress.total}`;
    return h('div', {class: 'progress'},
      h('div', {class: 'progress-text'}, h('span', {text: `${fmt.KIND[session.kind]} · ${label}`}),
        h('button', {type: 'button', class: 'btn btn-quiet', text: 'Terminer maintenant', onclick: finishNow})),
      h('div', {class: 'progress-track', role: 'progressbar', 'aria-valuemin': 0, 'aria-valuemax': progress.total, 'aria-valuenow': progress.answered, 'aria-label': 'Avancement de la séance'},
        h('span', {style: `width:${(ratio * 100).toFixed(1)}%`})));
  }

  async function finishNow() {
    if (!confirmInline()) return;
    try { await api.finish(session.id); summaryScreen(session.id); } catch (e) { fail(e, finishNow); }
  }
  let confirmArmed = false;
  function confirmInline() {
    if (confirmArmed) return true;
    confirmArmed = true;
    const note = h('p', {class: 'notice-inline', role: 'status', text: 'Cliquez à nouveau sur « Terminer maintenant » pour arrêter. Les questions non répondues ne compteront pas comme des erreurs.'});
    app.querySelector('.progress')?.after(note);
    setTimeout(() => { confirmArmed = false; note.remove(); }, 5000);
    return false;
  }

  function itemScreen(item, progress) {
    const s = item.served, ex = item.exercise;
    const started = performance.now();
    let stimulusEnd = null, replays = 0, busy = false;
    const message = h('p', {class: 'form-error', role: 'alert'});
    const body = h('div', {class: 'item-body'});
    const head = h('div', {class: 'item-head'},
      h('p', {class: 'kicker', text: `${SKILL[item.skill]} · ${item.title} · niveau ${item.level}`}),
      h('h1', {class: 'item-prompt', text: s.prompt}),
      h('details', {class: 'why'}, h('summary', {text: 'Pourquoi cet exercice ?'}), h('p', {text: s.block_reason})));
    screen(bar(progress), h('article', {class: 'sheet item', 'aria-labelledby': 'q'}, head, body, message));
    head.querySelector('h1').id = 'q';

    async function listen(auto) {
      if (!s.audio.length) return;
      if (!auto) { if (replays >= s.replays) return; replays++; }
      const playBtn = body.querySelector('.listen');
      if (playBtn) playBtn.disabled = true;
      try { const p = L.audio.play(s.audio); await p.done; } catch (e) { message.textContent = e.message; }
      stimulusEnd = performance.now();
      if (playBtn) { playBtn.disabled = replays >= s.replays; playBtn.textContent = replays >= s.replays ? 'Plus de réécoute' : `Réécouter (${s.replays - replays})`; }
    }
    function listenButton() {
      return h('button', {type: 'button', class: 'btn btn-secondary listen', text: s.replays ? `Réécouter (${s.replays})` : 'Écouter', onclick: () => listen(false)});
    }

    async function submit(response) {
      if (busy) return; busy = true; message.textContent = '';
      const response_ms = Math.round(performance.now() - (stimulusEnd || started));
      try {
        const r = await api.answer(item.id, {response, response_ms, replays});
        feedbackScreen(item, r);
      } catch (e) {
        busy = false;
        if (e.status === 422) { message.textContent = e.message; if (onInvalid) onInvalid(); }
        else fail(e, () => submit(response));
      }
    }
    let onInvalid = null;

    if (item.response_type === 'choice') {
      const options = h('div', {class: 'options', role: 'group', 'aria-label': 'Réponses possibles'},
        s.options.map((o, i) => h('button', {type: 'button', class: 'btn btn-option', 'data-value': o.value, onclick: () => submit({choice: o.value})},
          h('kbd', {text: String(i + 1)}), h('span', {text: o.label}))));
      body.append(h('div', {class: 'actions'}, listenButton()), options);
      const onKey = e => { const n = Number(e.key); if (n >= 1 && n <= s.options.length && !e.repeat) submit({choice: s.options[n - 1].value}); };
      document.addEventListener('keydown', onKey); cleanup.push(() => document.removeEventListener('keydown', onKey));
      listen(true);
    } else if (item.response_type === 'staff') {
      const box = h('div', {class: 'staff'}); L.widgets.staff(box, s.staff);
      let accidental = 'natural';
      const accs = s.accidentals ? h('div', {class: 'acc-row', role: 'radiogroup', 'aria-label': 'Altération'},
        [['flat', '♭ bémol'], ['natural', 'aucune'], ['sharp', '♯ dièse']].map(([v, label]) => h('button', {type: 'button', class: 'btn btn-secondary acc', role: 'radio',
          'aria-checked': String(v === 'natural'), 'data-acc': v, text: label, onclick: e => { accidental = v; accs.querySelectorAll('.acc').forEach(b => b.setAttribute('aria-checked', String(b.dataset.acc === v))); }}))) : null;
      const options = h('div', {class: 'options options-notes', role: 'group', 'aria-label': 'Nom de la note'},
        s.options.map((o, i) => h('button', {type: 'button', class: 'btn btn-option', onclick: () => submit({choice: o.value, accidental})}, h('kbd', {text: String(i + 1)}), h('span', {text: o.label}))));
      body.append(...[box, accs, options].filter(Boolean));
      const onKey = e => { const n = Number(e.key); if (n >= 1 && n <= s.options.length && !e.repeat) submit({choice: s.options[n - 1].value, accidental}); };
      document.addEventListener('keydown', onKey); cleanup.push(() => document.removeEventListener('keydown', onKey));
    } else if (item.response_type === 'keyboard') {
      const box = h('div', {class: 'kb-box'});
      const validate = h('button', {type: 'button', class: 'btn btn-primary', text: 'Valider ma réponse', disabled: true});
      const kb = L.widgets.keyboard(box, {low: s.keyboard.low, high: s.keyboard.high, start: s.keyboard.start, max: 16,
        onChange: notes => { validate.disabled = !notes.length; }});
      cleanup.push(kb.destroy);
      validate.addEventListener('click', () => submit({notes: kb.notes()}));
      body.append(h('div', {class: 'actions'}, listenButton(), h('span', {class: 'fine', text: `${s.keyboard.length} notes · la première est entourée sur le clavier`})), box, h('div', {class: 'actions'}, validate));
      listen(true);
    } else if (item.response_type === 'tap' && ex === 'pulsation') {
      const pad = h('div', {class: 'tap-box'});
      const tp = L.widgets.tapper(pad, {label: 'Espace'}); cleanup.push(tp.destroy);
      const go = h('button', {type: 'button', class: 'btn btn-primary', text: 'Démarrer', 'data-autofocus': true});
      const state = h('p', {class: 'tap-state', 'aria-live': 'polite', text: `${s.tap.sync} clics, puis continuez seul ${s.tap.cont} fois jusqu’au son aigu de fin.`});
      async function run() {
        go.disabled = true; message.textContent = '';
        const endTone = {t: s.tap.end_signal, d: 0.35, midi: 88, v: 0.6};
        const played = L.audio.play(s.audio, {extra: [endTone]});
        tp.start(played.startPerf);
        state.textContent = 'Tapez avec les clics…';
        setTimeout(() => { state.textContent = 'Continuez seul, au même tempo…'; }, s.tap.sync * s.tap.ioi * 1000 + 150);
        await played.done;
        tp.stop(); stimulusEnd = performance.now();
        state.textContent = 'Fin. Correction…';
        submit({taps: tp.taps()});
      }
      onInvalid = () => { go.disabled = false; go.textContent = 'Recommencer'; state.textContent = 'Recommencez quand vous êtes prêt.'; };
      go.addEventListener('click', run);
      body.append(state, pad, h('div', {class: 'actions'}, go));
    } else if (item.response_type === 'tap') {
      const pad = h('div', {class: 'tap-box'});
      const tp = L.widgets.tapper(pad, {label: 'Espace'}); cleanup.push(tp.destroy);
      const mine = h('button', {type: 'button', class: 'btn btn-primary', text: 'À moi de taper', disabled: true});
      const validate = h('button', {type: 'button', class: 'btn btn-primary', text: 'Valider mon rythme', disabled: true});
      const state = h('p', {class: 'tap-state', 'aria-live': 'polite', text: `Écoutez le décompte (4 clics) puis le rythme (${s.tap.expected} sons).`});
      mine.addEventListener('click', () => {
        tp.start(performance.now()); mine.disabled = true; validate.disabled = false;
        state.textContent = 'Tapez le rythme avec la barre d’espace, puis validez (Entrée).';
      });
      validate.addEventListener('click', () => { tp.stop(); submit({taps: tp.taps()}); });
      const onEnter = e => { if (e.key === 'Enter' && !validate.disabled) { e.preventDefault(); validate.click(); } };
      document.addEventListener('keydown', onEnter); cleanup.push(() => document.removeEventListener('keydown', onEnter));
      onInvalid = () => { tp.stop(); mine.disabled = false; validate.disabled = true; state.textContent = 'Réécoutez si besoin, puis recommencez.'; };
      const first = listen(true).then(() => { mine.disabled = false; });
      body.append(state, h('div', {class: 'actions'}, listenButton(), mine), pad, h('div', {class: 'actions'}, validate));
      void first;
    }
  }

  function predictionNote(p, outcome, skill) {
    if (!p) return null;
    if (p.status === 'ok') {
      return h('div', {class: 'forecast-note'},
        h('p', {class: 'cat cat-forecast', text: 'Prévision enregistrée avant votre réponse'}),
        h('p', {}, `Modèle de référence O08 : ${fmt.pct(p.p)} de chances de réussite (taux de réussite simple : ${fmt.pct(p.baseline)}). `,
          h('strong', {text: outcome ? 'Résultat : réussi.' : 'Résultat : manqué.'})));
    }
    if (p.status === 'abstained') {
      return h('div', {class: 'forecast-note is-abstained'},
        h('p', {class: 'cat cat-forecast', text: 'Pas de prévision pour cette question'}),
        h('p', {text: `Données insuffisantes : ${p.n_skill} réponse(s) en ${SKILL[skill]}, ${p.needed} nécessaires avant que le modèle de référence prévoie quoi que ce soit.`}));
    }
    return h('div', {class: 'forecast-note is-abstained'}, h('p', {text: 'Prévision indisponible (erreur du modèle de référence). Votre réponse est enregistrée normalement.'}));
  }

  function feedbackScreen(item, r) {
    const res = r.result, ok = res.correct;
    const extra = [];
    if (item.response_type === 'keyboard') {
      extra.push(h('button', {type: 'button', class: 'btn btn-secondary', text: 'Écouter la bonne mélodie', onclick: () => L.audio.play(res.details.expected.map((m, i) => ({t: i * 0.55, d: 0.5, midi: m})))}));
      extra.push(h('button', {type: 'button', class: 'btn btn-secondary', text: 'Écouter ma réponse', onclick: () => L.audio.play(res.details.given.map((m, i) => ({t: i * 0.55, d: 0.5, midi: m})))}));
    } else if (item.response_type === 'staff') {
      L.audio.note(res.details.reveal_midi, 0.7);
      extra.push(h('button', {type: 'button', class: 'btn btn-secondary', text: 'Réentendre la note', onclick: () => L.audio.note(res.details.reveal_midi, 0.7)}));
    } else if (item.served.audio.length) {
      extra.push(h('button', {type: 'button', class: 'btn btn-secondary', text: 'Réentendre l’exercice', onclick: () => L.audio.play(item.served.audio)}));
    }
    const done = r.progress.answered >= r.progress.total;
    const next = h('button', {type: 'button', class: 'btn btn-primary', 'data-autofocus': true, text: done ? 'Voir le bilan de la séance' : 'Question suivante',
      onclick: () => done ? summaryScreen(session.id) : nextItem()});
    const metrics = [];
    if (res.details.cents != null) metrics.push(`écart joué : ${res.details.cents} cents`);
    if (res.details.max_error_beats != null) metrics.push(`erreur maximale ${res.details.max_error_beats} temps (tolérance ${res.details.tolerance_beats})`);
    screen(bar(r.progress, true),
      h('article', {class: `sheet item feedback ${ok ? 'is-ok' : 'is-ko'}`},
        h('p', {class: 'kicker', text: `${item.title} · niveau ${item.level}`}),
        h('h1', {class: 'verdict', text: ok ? 'Juste' : 'Pas encore'}),
        h('p', {class: 'verdict-text', text: res.feedback}),
        metrics.length ? h('p', {class: 'fine', text: metrics.join(' · ')}) : null,
        extra.length ? h('div', {class: 'actions'}, extra) : null,
        predictionNote(res.prediction, ok, item.skill),
        h('div', {class: 'actions next'}, next)));
    const onKey = e => { if (e.key === 'Enter' && document.activeElement?.tagName !== 'BUTTON') next.click(); };
    document.addEventListener('keydown', onKey); cleanup.push(() => document.removeEventListener('keydown', onKey));
  }

  // ---------------------------------------------------------------- summary
  async function summaryScreen(sid) {
    let s;
    try { s = await api.summary(sid); } catch (e) { return fail(e, () => summaryScreen(sid)); }
    learner = await api.learner(learner.id).catch(() => learner);
    const scored = s.predictions.filter(p => p.status === 'ok');
    const meanP = scored.length ? scored.reduce((a, p) => a + p.p, 0) / scored.length : null;
    const obs = scored.length ? scored.filter(p => p.outcome).length / scored.length : null;
    const rows = s.blocks.map(b => h('tr', {}, h('td', {text: b.title}), h('td', {text: `niveau ${b.level}`}),
      h('td', {text: `${b.correct} / ${b.answered}${b.answered < b.planned ? ` (sur ${b.planned} prévues)` : ''}`}), h('td', {class: 'fine', text: b.reason})));
    const t = s.pitch_threshold;
    screen(
      h('header', {class: 'page-head'},
        h('p', {class: 'kicker', text: `${fmt.KIND[s.session.kind]} ${s.session.status === 'terminee' ? 'terminée' : s.session.status}`}),
        h('h1', {text: `${s.correct} réponse${s.correct > 1 ? 's' : ''} juste${s.correct > 1 ? 's' : ''} sur ${s.answered}`}),
        h('p', {class: 'lede', text: s.unanswered_served ? `${s.unanswered_served} question affichée sans réponse : elle ne compte pas comme une erreur.` :
          'Toutes vos réponses sont enregistrées dans votre parcours et serviront à choisir la prochaine séance.'}),
        h('div', {class: 'actions'},
          h('a', {class: 'btn btn-primary', href: '/web/parcours.html', 'data-autofocus': true, text: 'Voir mon parcours'}),
          h('button', {type: 'button', class: 'btn btn-secondary', text: 'Commencer une autre séance', onclick: () => begin({kind: 'seance'})}))),
      s.newly_mastered.length ? h('section', {class: 'sheet pad mastered'}, h('h2', {class: 'h3', text: 'Niveaux maîtrisés pendant cette séance'}),
        h('ul', {}, s.newly_mastered.map(m => h('li', {text: `${m.title} · niveau ${m.level}`})))) : null,
      t ? h('section', {class: 'sheet pad'}, h('h2', {class: 'h3', text: 'Votre seuil de hauteur'}),
        h('p', {text: t.threshold_cents ? `Environ ${t.threshold_cents} cents (100 cents = un demi-ton). Estimation ${t.reliability.startsWith('indicatif') ? 'indicative (moins de 4 changements de sens)' : 'sur 4 changements de sens'}, ${t.trials} essais.` :
          `Pas d’estimation fiable : ${t.reliability}. Plus petit écart réussi : ${t.lowest_correct_cents ?? '—'} cents.`})) : null,
      h('section', {class: 'sheet pad'}, h('h2', {class: 'h3', text: 'Détail par exercice'}),
        h('div', {class: 'table-scroll'}, h('table', {}, h('thead', {}, h('tr', {}, ['Exercice', 'Niveau', 'Réussite', 'Pourquoi'].map(x => h('th', {text: x})))), h('tbody', {}, rows)))),
      s.errors.length ? h('section', {class: 'sheet pad'}, h('h2', {class: 'h3', text: 'Erreurs de la séance'}),
        h('ul', {}, s.errors.slice(0, 6).map(e => h('li', {text: `${e.title} : ${e.error} (${e.count}×)`})))) : null,
      h('section', {class: 'sheet pad'}, h('h2', {class: 'h3', text: 'Les prévisions de cette séance'}),
        h('p', {text: scored.length
          ? `${scored.length} prévision(s) enregistrée(s) avant vos réponses : ${fmt.pct(meanP)} de réussite prévue en moyenne, ${fmt.pct(obs)} observée. ${s.predictions.length - scored.length} question(s) sans prévision (données insuffisantes).`
          : 'Aucune prévision : le modèle de référence attend au moins 5 réponses dans une compétence avant de prévoir. C’est normal en début de parcours.'}),
        h('p', {class: 'fine'}, 'Le détail, et la façon dont la qualité des prévisions évolue avec vos données, est dans ', h('a', {href: '/web/parcours.html#o08', text: 'Mon parcours · O08'}), '.')),
      h('section', {class: 'sheet pad'}, h('h2', {class: 'h3', text: 'Prochaine séance proposée'}),
        h('ol', {class: 'plan'}, s.next_plan.map(b => h('li', {}, h('strong', {text: `${titleOf(b.exercise)} · niveau ${b.level}`}), h('span', {class: 'fine', text: ` — ${b.reason}`}))))));
  }
  const TITLES = {'hauteur-comparaison': 'Plus aigu ou plus grave ?', 'hauteur-seuil': 'Mesure du seuil de hauteur', intervalles: 'Reconnaître un intervalle', accords: 'Couleur des accords',
    melodies: 'Mélodies pareilles ou différentes ?', echo: 'Écho au clavier', pulsation: 'Garder la pulsation', rythmes: 'Rythmes pareils ou différents ?',
    'rythme-echo': 'Reproduire un rythme', lecture: 'Lire une note', degres: 'Degré dans la tonalité', cadences: 'Fins de phrase (cadences)'};
  const titleOf = id => TITLES[id] || id;

  L.booted();
  boot();
})(window.Learn);
