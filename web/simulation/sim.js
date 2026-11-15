'use strict';
// Élèves virtuels: read-only views of the SYNTHETIC simulation study (/api/sim). Every number on
// this page comes from files written by scripts/run_simulation_study.py; nothing is computed here
// except chart scales and per-learner summaries of the served questions.
(function () {
  const $ = id => document.getElementById(id);
  const NS = 'http://www.w3.org/2000/svg';
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === 'text') el.textContent = v; else if (k === 'class') el.className = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v); else el.setAttribute(k, v === true ? '' : v);
    }
    for (const c of kids.flat(Infinity)) if (c != null && c !== false) el.append(c instanceof Node ? c : document.createTextNode(String(c)));
    return el;
  }
  function s(tag, attrs, ...kids) {
    const el = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) if (v != null) el.setAttribute(k, v);
    for (const c of kids.flat(Infinity)) if (c != null) el.append(c instanceof Node ? c : document.createTextNode(String(c)));
    return el;
  }
  const fr = (v, d = 3) => v == null || !isFinite(v) ? '—' : Number(v).toLocaleString('fr-FR', {minimumFractionDigits: d, maximumFractionDigits: d});
  const int = v => v == null ? '—' : Number(v).toLocaleString('fr-FR');
  const pct = v => v == null ? '—' : `${Math.round(v * 100)} %`;
  const MODELS = [['elo', 'Elo', 'c-elo'], ['gru', 'GRU', 'c-gru'], ['naive', 'Naïf', 'c-naive']];
  const COLOR = {truth: 'var(--m-truth)', elo: 'var(--m-elo)', gru: 'var(--m-gru)', naive: 'var(--m-naive)'};
  const SKILL_LABEL = {hauteur: 'Hauteur', intervalles: 'Intervalles', accords: 'Accords', memoire: 'Mémoire mélodique', reproduction: 'Reproduction',
                       pulsation: 'Pulsation', rythme: 'Rythme', lecture: 'Lecture', tonalite: 'Fonctions tonales'};
  async function get(path) {
    const r = await fetch(path, {cache: 'no-store'});
    if (!r.ok) throw new Error(`${path} → ${r.status}`);
    return r.json();
  }

  // ---------------------------------------------------------------- charts (inline SVG)
  function lineChart({series, xs, ymin = 0, ymax = 1, height = 240, xlabel = '', ylabel = '', ticks = 5, band, dots, xfmt = v => v}) {
    const W = 720, H = height, L = 46, R = 12, T = 12, Bm = 34;
    const n = xs.length;
    const xmin = Math.min(...xs), xmax = Math.max(...xs, xmin + 1);
    const X = v => L + (v - xmin) / (xmax - xmin) * (W - L - R);
    const Y = v => T + (1 - (v - ymin) / (ymax - ymin)) * (H - T - Bm);
    const svg = s('svg', {class: 'chart', viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': ylabel});
    // round tick values (0 ; 0,2 ; 0,4 …) inside [ymin, ymax], never "-0"
    const raw = (ymax - ymin) / ticks, mag = 10 ** Math.floor(Math.log10(raw));
    const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(v => v >= raw);
    const dec = step >= 1 ? 0 : (String(+step.toFixed(6)).split('.')[1] || '').length;
    for (let v = Math.ceil(ymin / step - 1e-9) * step; v <= ymax + 1e-9; v += step) {
      const t = Math.abs(v) < 1e-9 ? 0 : v;
      svg.append(s('line', {class: 'grid', x1: L, x2: W - R, y1: Y(t), y2: Y(t)}), s('text', {x: L - 6, y: Y(t) + 4, 'text-anchor': 'end'}, fr(t, dec)));
    }
    const xt = Math.min(8, n);
    for (let i = 0; i < xt; i++) {
      const v = xs[Math.round(i * (n - 1) / Math.max(1, xt - 1))];
      svg.append(s('text', {x: X(v), y: H - Bm + 16, 'text-anchor': 'middle'}, xfmt(v)));
    }
    if (xlabel) svg.append(s('text', {x: W - R, y: H - 4, 'text-anchor': 'end'}, xlabel));
    if (band) {
      const pts = xs.map((x, i) => `${X(x)},${Y(band.hi[i])}`).concat(xs.map((x, i) => `${X(x)},${Y(band.lo[i])}`).reverse());
      svg.append(s('polygon', {points: pts.join(' '), fill: band.color, opacity: 0.12}));
    }
    for (const se of series) {
      let d = '', pen = false;
      se.values.forEach((v, i) => {
        if (v == null || !isFinite(v)) { pen = false; return; }
        d += `${pen ? 'L' : 'M'}${X(xs[i]).toFixed(1)},${Y(v).toFixed(1)}`; pen = true;
      });
      svg.append(s('path', {d, fill: 'none', stroke: se.color, 'stroke-width': se.width || 2, 'stroke-dasharray': se.dash || null, opacity: se.opacity || 1}));
    }
    if (dots) for (const p of dots) svg.append(s('circle', {cx: X(p.x), cy: Y(p.y), r: p.r || 2.5, fill: p.color}));
    return svg;
  }
  function barsChart({groups, keys, height = 220, ymax, ylabel = '', fmt = v => fr(v)}) {
    const W = 720, H = height, L = 46, R = 8, T = 10, Bm = 42;
    const top = ymax || Math.max(1e-9, ...groups.flatMap(g => keys.map(([k]) => g.values[k] || 0))) * 1.1;
    const Y = v => T + (1 - v / top) * (H - T - Bm);
    const gw = (W - L - R) / groups.length, bw = Math.min(26, gw / (keys.length + 1));
    const svg = s('svg', {class: 'chart', viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': ylabel});
    for (let i = 0; i <= 4; i++) { const v = top * i / 4; svg.append(s('line', {class: 'grid', x1: L, x2: W - R, y1: Y(v), y2: Y(v)}), s('text', {x: L - 6, y: Y(v) + 4, 'text-anchor': 'end'}, fmt(v))); }
    groups.forEach((g, gi) => {
      const x0 = L + gi * gw + (gw - bw * keys.length) / 2;
      keys.forEach(([k, color], ki) => {
        const v = g.values[k];
        if (v == null) return;
        svg.append(s('rect', {x: x0 + ki * bw, y: Y(v), width: bw - 2, height: Math.max(0, Y(0) - Y(v)), fill: color}, s('title', {}, `${g.label} · ${k} : ${fmt(v)}`)));
        if (g.ci && g.ci[k]) svg.append(s('line', {x1: x0 + ki * bw + bw / 2 - 1, x2: x0 + ki * bw + bw / 2 - 1, y1: Y(g.ci[k][0]), y2: Y(g.ci[k][1]), stroke: 'var(--ink)', 'stroke-width': 1.5}));
      });
      svg.append(s('text', {x: L + gi * gw + gw / 2, y: H - Bm + 16, 'text-anchor': 'middle'}, g.label));
    });
    return svg;
  }
  const legend = items => h('div', {class: 'legend'}, items.map(([label, cls, kind]) => h('span', {class: cls}, h('i', {class: kind || ''}), label)));
  function table(head, rows, numeric = []) {
    return h('div', {class: 'table-scroll'}, h('table', {class: 'sim'},
      h('thead', {}, h('tr', {}, head.map((t, i) => h('th', {class: numeric.includes(i) ? 'num' : null, text: t})))),
      h('tbody', {}, rows.map(r => h('tr', {class: r.cls || null}, (r.cells || r).map((c, i) => h('td', {class: numeric.includes(i) ? 'num' + (c && c.win ? ' win' : '') : null}, c && c.node ? c.node : (c && c.text !== undefined ? c.text : c))))))));
  }
  const cellCI = (v, ci, win) => ({node: h('span', {}, h('span', {class: win ? 'win-mark' : null, text: fr(v, 4)}), ci ? h('span', {class: 'ci', text: `IC 95 % ${fr(ci[0], 4)} – ${fr(ci[1], 4)}`}) : null), win});

  const put = (el, ...kids) => el.replaceChildren(...kids.flat(Infinity).filter(k => k != null && k !== false));
  // ---------------------------------------------------------------- state
  let study, overview, learners = [], tech;
  const TABS = ['population', 'eleve', 'comparaison', 'experiences', 'technique'];
  const built = {};

  function select(name, focus) {
    TABS.forEach(t => {
      const on = t === name;
      $('tab-' + t).setAttribute('aria-selected', String(on)); $('tab-' + t).tabIndex = on ? 0 : -1;
      $('view-' + t).hidden = !on;
    });
    if (focus) $('tab-' + name).focus();
    if (location.hash !== '#' + name) history.replaceState(null, '', '#' + name);
    if (!built[name]) { built[name] = true; RENDER[name]().catch(fail($('view-' + name))); }
  }
  TABS.forEach((t, i) => {
    $('tab-' + t).addEventListener('click', () => select(t));
    $('tab-' + t).addEventListener('keydown', e => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); select(TABS[(i + (e.key === 'ArrowRight' ? 1 : TABS.length - 1)) % TABS.length], true); }
    });
  });
  const fail = box => e => put(box, h('div', {class: 'problem', role: 'alert'}, h('h2', {text: 'Données indisponibles'}), h('p', {text: String(e.message || e)})));

  // ---------------------------------------------------------------- population
  function population() {
    const box = $('view-population');
    const insp = overview.inspection;
    const names = Object.keys(insp);
    const pick = h('select', {id: 'campaign'}, names.map(n => h('option', {value: n, text: `${n} · ${insp[n].n} élèves · simulateur ${insp[n].variant}${insp[n].noise_scale !== 1 ? ' · bruit ×' + insp[n].noise_scale : ''}`})));
    const body = h('div');
    const draw = () => {
      const c = insp[pick.value];
      const fams = Object.entries(c.families);
      const weeks = c.weekly.map(w => w.week);
      const famLabel = f => overview.family_labels[f] || f;
      const palette = ['#1F4A72', '#A27C12', '#1E7A50', '#6A55AE', '#B45A12', '#A3304E', '#237F86'];
      const famSeries = fams.map(([f, v], i) => ({name: famLabel(f), values: v.weekly_ability_mean, color: palette[i % palette.length]}));
      const nWeeks = Math.max(...famSeries.map(x => x.values.length));
      put(body, 
        h('div', {class: 'sim-row'}, [
          [int(c.n), 'élèves simulés'], [int(c.learners_with_answers), 'élèves actifs au moins une fois'], [int(c.counters.sessions), 'séances'],
          [int(c.counters.sessions_finished), 'séances terminées'], [int(c.questions), 'questions traitées'], [pct(c.correct_rate), 'réponses justes'],
          [int(c.dropouts), 'abandons'], [int(c.returns), 'retours après abandon'], [int(c.breaks), 'pauses'], [int(c.active_end), 'actifs à la fin'],
          [int(c.exports_accepted), 'exports O08 acceptés'], [fr(c.mastered_levels.mean, 1), 'niveaux maîtrisés en moyenne']
        ].map(([v, l]) => h('div', {class: 'kpi'}, h('b', {text: v}), h('span', {text: l})))),
        h('div', {class: 'sim-grid'},
          h('div', {class: 'panel'}, h('h3', {text: 'Activité semaine par semaine'}),
            h('p', {text: 'Élèves qui ont répondu à au moins une question dans la semaine, et taux de réponses justes.'}),
            barsChart({groups: c.weekly.map(w => ({label: `S${w.week}`, values: {actifs: w.active_learners}})), keys: [['actifs', 'var(--cover-deep)']], fmt: v => int(Math.round(v)), ylabel: 'élèves actifs'}),
            table(['Semaine', 'Actifs', 'Questions', 'Justes'], c.weekly.map(w => [`S${w.week}`, int(w.active_learners), int(w.answers), pct(w.correct_rate)]), [1, 2, 3])),
          h('div', {class: 'panel'}, h('h3', {text: 'Niveau caché moyen, par famille'}),
            h('p', {text: 'Moyenne des 9 compétences sur une échelle commune : 0 = bruit d’un débutant typique, 1 = bruit d’un expert typique. Lu dans l’état caché, jamais montré aux modèles.'}),
            lineChart({xs: [...Array(nWeeks).keys()].map(i => i + 1), series: famSeries, ymin: -0.4, ymax: 1.2, xlabel: 'semaine', xfmt: v => `S${v}`, ylabel: 'niveau caché moyen'}),
            legend(famSeries.map((f, i) => [f.name, '', '']).map(([l], i) => [l, `fam-${i}`, ''])),
          )),
        h('h3', {text: 'Les familles ne progressent pas pareil'}),
        table(['Famille', 'Élèves', 'Gain moyen sur la période', 'Écart-type du gain', ...Object.keys(SKILL_LABEL).map(k => SKILL_LABEL[k])],
          fams.map(([f, v]) => [famLabel(f), int(v.learners), fr(v.gain_mean, 3), fr(v.gain_sd, 3), ...Object.keys(SKILL_LABEL).map(k => fr((c.skill_gain_by_family[f] || {})[k], 2))]),
          [1, 2, 3, ...Object.keys(SKILL_LABEL).map((_, i) => i + 4)]),
        h('p', {class: 'sub', text: `Diversité vérifiée : ${int(c.diversity.distinct_weekly_curves)} courbes hebdomadaires distinctes sur ${int(c.diversity.learners)} élèves (${pct(c.diversity.share_identical_curves)} identiques) ; gain individuel de ${fr(c.diversity.gain_min, 2)} à ${fr(c.diversity.gain_max, 2)}, écart-type ${fr(c.diversity.gain_sd_all, 3)}.`}),
        h('h3', {text: 'Exercices réellement proposés par DÉCLIC'}),
        table(['Exercice', 'Questions', 'Réussite', 'Niveau moyen', 'Niveau max atteint'],
          Object.entries(c.exercises).sort((a, b) => b[1].questions - a[1].questions).map(([e, v]) => [e, int(v.questions), pct(v.correct_rate), fr(v.mean_level, 1), int(v.max_level)]), [1, 2, 3, 4]));
      body.querySelectorAll('.legend span').forEach((el, i) => { el.style.color = palette[i % palette.length]; });
    };
    pick.addEventListener('change', draw);
    put(box, h('h2', {text: 'Population'}),
      h('p', {class: 'sub', text: 'Chaque campagne est exécutée par les vraies routes de DÉCLIC (profil, évaluation, séances, correction, bilan, Parcours, export O08), sur une base synthétique séparée et une horloge simulée.'}),
      h('div', {class: 'controls'}, h('label', {for: 'campaign'}, 'Campagne', pick)), body);
    draw();
    return Promise.resolve();
  }

  // ---------------------------------------------------------------- one learner
  async function eleve() {
    const box = $('view-eleve');
    if (!learners.length) {
      const list = await get(`/api/sim/${study}/learners`);
      learners = list.learners;
    }
    const byFam = {};
    learners.forEach(l => (byFam[l.family_label] = byFam[l.family_label] || []).push(l));
    const pick = h('select', {id: 'learner'}, Object.entries(byFam).map(([f, ls]) => h('optgroup', {label: f}, ls.map(l => h('option', {value: l.sim_id, text: `${l.sim_id} · ${l.questions} questions · ${pct(l.correct_rate)}`})))));
    const skillPick = h('select', {id: 'skill'});
    const body = h('div');
    let current;
    const drawSkill = () => {
      const x = current, skill = skillPick.value;
      const qs = x.questions.filter(q => skill === 'toutes' || q[4] === skill);
      const xs = qs.map((_, i) => i + 1);
      const col = k => qs.map(q => q[{elo: 6, naive: 7, gru: 8, truth: 9}[k]]);
      const dots = qs.map((q, i) => ({x: i + 1, y: q[5] ? 1.03 : -0.03, color: q[5] ? 'var(--m-good)' : 'var(--m-bad)', r: 2}));
      const chart = lineChart({xs: xs.length ? xs : [0, 1], series: [
        {values: col('truth'), color: COLOR.truth, width: 2.5}, {values: col('elo'), color: COLOR.elo},
        {values: col('gru'), color: COLOR.gru, dash: '6 4'}, {values: col('naive'), color: COLOR.naive, width: 1.5}], ymin: -0.06, ymax: 1.06,
        dots, xlabel: 'question (dans l’ordre)', ylabel: 'probabilité de réussite', height: 280});
      const brier = k => { const v = qs.filter(q => q[{elo: 6, naive: 7, gru: 8}[k]] != null && q[6] != null && q[8] != null); return v.length ? v.reduce((a, q) => a + (q[{elo: 6, naive: 7, gru: 8}[k]] - q[5]) ** 2, 0) / v.length : null; };
      const toTruth = k => { const v = qs.filter(q => q[6] != null && q[8] != null && q[9] != null); return v.length ? v.reduce((a, q) => a + (q[{elo: 6, naive: 7, gru: 8}[k]] - q[9]) ** 2, 0) / v.length : null; };
      $('learner-chart').replaceChildren(chart,
        legend([['Vraie probabilité (cachée)', 'c-truth'], ['Elo', 'c-elo'], ['GRU', 'c-gru', 'dash'], ['Naïf', 'c-naive'], ['juste', 'c-good', 'dot'], ['pas encore', 'c-bad', 'dot']]),
        table(['Sur ces questions', 'Elo', 'GRU', 'Naïf'], [
          ['Brier (questions où Elo et GRU prévoient)', fr(brier('elo'), 4), fr(brier('gru'), 4), fr(brier('naive'), 4)],
          ['Écart quadratique à la vraie probabilité', fr(toTruth('elo'), 4), fr(toTruth('gru'), 4), fr(toTruth('naive'), 4)]], [1, 2, 3]));
    };
    const show = async () => {
      const x = current = await get(`/api/sim/${study}/learner/${encodeURIComponent(pick.value)}`);
      const counts = {};
      x.questions.forEach(q => { counts[q[4]] = (counts[q[4]] || 0) + 1; });
      put(skillPick, h('option', {value: 'toutes', text: 'Toutes les compétences'}),
        Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([k, n]) => h('option', {value: k, text: `${SKILL_LABEL[k]} (${n})`})));
      skillPick.value = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'toutes';
      const days = x.days.map(d => d[0]);
      const skillSeries = x.skills.map((k, i) => ({name: SKILL_LABEL[k], values: x.days.map(d => d[3][i]), color: ['#1F4A72', '#A27C12', '#1E7A50', '#6A55AE', '#B45A12', '#A3304E', '#237F86', '#5C677C', '#8A93A3'][i]}));
      const sessions = x.events.filter(e => e.event === 'session_end');
      const breaks = x.events.filter(e => e.event === 'break' || e.event === 'dropped' || e.event === 'returned');
      put(body, 
        h('div', {class: 'sim-row'}, [[x.family_label, 'famille'], [int(x.questions.length), 'questions'], [int(sessions.length), 'séances'],
          [pct(x.questions.reduce((a, q) => a + q[5], 0) / Math.max(1, x.questions.length)), 'réponses justes'],
          [fr(x.hidden.p_day, 2), 'probabilité de pratiquer un jour donné (caché)'], [fr(x.hidden.lapse, 3), 'taux d’inattention (caché)']].map(([v, l]) => h('div', {class: 'kpi'}, h('b', {text: v}), h('span', {text: l})))),
        h('div', {class: 'panel', style: 'margin-top:var(--s5)'}, h('h3', {text: 'Prévisions avant chaque réponse, et vraie probabilité'}),
          h('p', {text: x.note + ' Elo et le naïf sont les prévisions que DÉCLIC a enregistrées avant chaque question.'}),
          h('div', {class: 'controls'}, h('label', {for: 'skill'}, 'Compétence', skillPick)), h('div', {id: 'learner-chart'})),
        h('div', {class: 'sim-grid'},
          h('div', {class: 'panel'}, h('h3', {text: 'Niveau caché par compétence, jour après jour'}),
            h('p', {text: '0 = débutant typique, 1 = expert typique. La pratique fait monter, les pauses font redescendre (oubli).'}),
            lineChart({xs: days, series: skillSeries, ymin: -0.6, ymax: 1.5, xlabel: 'jour', ylabel: 'niveau caché', height: 260}),
            h('div', {class: 'legend'}, skillSeries.map(se => h('span', {style: `color:${se.color}`}, h('i'), se.name)))),
          h('div', {class: 'panel'}, h('h3', {text: 'Séances, pauses et erreurs'}),
            table(['Jour', 'Événement', 'Détail'], [...sessions.slice(-8).map(e => [fr(e.day, 1), e.kind === 'evaluation' ? 'Évaluation initiale' : 'Séance', `${e.correct}/${e.answered} justes${e.stopped ? ' · arrêtée (fatigue)' : ''}`]),
              ...breaks.map(e => [fr(e.day, 0), {break: 'Pause', dropped: 'Abandon', returned: 'Retour'}[e.event], e.until ? `jusqu’au jour ${e.until}` : ''])].sort((a, b) => parseFloat(String(a[0]).replace(',', '.')) - parseFloat(String(b[0]).replace(',', '.'))), [0]),
            h('h3', {text: 'Erreurs les plus fréquentes'}),
            x.errors.length ? h('ul', {}, x.errors.map(([k, n]) => h('li', {text: `${k} · ${n} fois`}))) : h('p', {class: 'muted', text: 'Aucune erreur récurrente.'}))));
      drawSkill();
    };
    pick.addEventListener('change', show);
    skillPick.addEventListener('change', drawSkill);
    put(box, h('h2', {text: 'Un élève virtuel'}),
      h('p', {class: 'sub', text: 'Huit semaines d’un élève de la campagne A1 : ce qu’il a fait, son niveau caché, et ce que chaque modèle prévoyait avant chacune de ses réponses.'}),
      h('div', {class: 'controls'}, h('label', {for: 'learner'}, 'Élève', pick)), body);
    await show();
  }

  // ---------------------------------------------------------------- Elo vs GRU vs naive
  function resultTable(res, opts = {}) {
    const m = res.common.metrics, b = res.common.bootstrap, own = res.own_coverage;
    const best = Math.min(...MODELS.map(([k]) => m[k].brier));
    return table(['Modèle', 'Brier', 'Log-loss', 'AUC', 'Calibration (ECE)', 'Élèves évalués', 'Couverture des prévisions'],
      MODELS.map(([k, label]) => ({cls: m[k].brier === best ? 'best' : null, cells: [h('span', {class: 'win-mark ' + MODELS.find(x => x[0] === k)[2], text: label}),
        cellCI(m[k].brier, b[k] && b[k].brier, m[k].brier === best), cellCI(m[k].log_loss, b[k] && b[k].log_loss), fr(m[k].auc, 3), fr(m[k].ece, 3),
        int(own[k].learners), pct(own[k].coverage)]})), [1, 2, 3, 4, 5, 6]);
  }
  function diffTable(res) {
    const d = res.common.bootstrap.differences;
    const name = {'elo-gru': 'Elo − GRU', 'elo-naive': 'Elo − naïf', 'gru-naive': 'GRU − naïf'};
    return table(['Différence (négatif = le premier est meilleur)', 'Brier', 'IC 95 % (élèves)', 'Log-loss', 'IC 95 % (élèves)', 'Écart à la vraie probabilité (IC 95 %)'],
      Object.keys(name).map(k => [name[k], fr(d[k + ':brier'].point, 4), `${fr(d[k + ':brier'].ci95[0], 4)} – ${fr(d[k + ':brier'].ci95[1], 4)}`,
        fr(d[k + ':log_loss'].point, 4), `${fr(d[k + ':log_loss'].ci95[0], 4)} – ${fr(d[k + ':log_loss'].ci95[1], 4)}`,
        d[k + ':to_truth'] ? `${fr(d[k + ':to_truth'].point, 4)} (${fr(d[k + ':to_truth'].ci95[0], 4)} – ${fr(d[k + ':to_truth'].ci95[1], 4)})` : '—']), [1, 2, 3, 4, 5]);
  }
  function verdict(res) {
    const d = res.common.bootstrap.differences['elo-gru:brier'];
    const lo = d.ci95[0], hi = d.ci95[1];
    const text = hi < 0 ? 'Elo est meilleur que le GRU sur ces questions : tout l’intervalle de la différence est négatif.'
      : lo > 0 ? 'Le GRU est meilleur qu’Elo sur ces questions : tout l’intervalle de la différence est positif.'
      : 'Pas de différence démontrée entre Elo et le GRU : l’intervalle de la différence contient zéro.';
    return h('p', {class: 'verdict'}, h('b', {text: 'Lecture. '}), text);
  }
  function calibration(res) {
    const series = [], dots = [];
    MODELS.forEach(([k]) => {
      const cal = res.common.metrics[k].calibration;
      series.push({values: [], color: COLOR[k]});
      cal.forEach(c => dots.push({x: c.predicted, y: c.observed, color: COLOR[k], r: Math.max(2.5, Math.min(7, Math.sqrt(c.count) / 4))}));
    });
    return lineChart({xs: [0, 1], series: [{values: [0, 1], color: 'var(--line-strong)', dash: '4 4'}], dots, xlabel: 'probabilité prévue', ylabel: 'réussite observée', xfmt: v => fr(v, 1)});
  }
  // Elo − GRU per group, with its learner-bootstrap interval: left of zero, Elo has less error.
  function diffChart(rows) {
    const shown = rows.filter(r => r.d);
    if (!shown.length) return null;
    const W = 720, rowH = 26, T = 30, B = 26, L = 230, R = 16, H = T + B + rowH * shown.length;
    const span = Math.max(0.01, ...shown.flatMap(r => r.d.ci95.map(Math.abs))) * 1.08;
    const X = v => L + (v + span) / (2 * span) * (W - L - R);
    const svg = s('svg', {class: 'chart', viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Elo moins GRU, Brier, intervalle à 95 %'});
    svg.append(s('text', {x: X(-span) + 2, y: 16}, '← Elo a moins d’erreur'), s('text', {x: X(span) - 2, y: 16, 'text-anchor': 'end'}, 'le GRU a moins d’erreur →'),
      s('line', {class: 'grid', x1: X(0), x2: X(0), y1: T - 6, y2: H - B + 4, 'stroke-width': 1.5}));
    [-span / 2, span / 2].forEach(v => svg.append(s('text', {x: X(v), y: H - 6, 'text-anchor': 'middle'}, fr(v, 3))));
    svg.append(s('text', {x: X(0), y: H - 6, 'text-anchor': 'middle'}, '0'));
    shown.forEach((r, i) => {
      const y = T + i * rowH + rowH / 2, [lo, hi] = r.d.ci95;
      const color = hi < 0 ? COLOR.elo : lo > 0 ? COLOR.gru : 'var(--line-strong)';
      svg.append(s('text', {x: L - 10, y: y + 4, 'text-anchor': 'end'}, r.label.length > 32 ? r.label.slice(0, 31) + '…' : r.label),
        s('line', {x1: X(lo), x2: X(hi), y1: y, y2: y, stroke: color, 'stroke-width': 3, 'stroke-linecap': 'round'}),
        s('circle', {cx: X(r.d.point), cy: y, r: 4.5, fill: color}, s('title', {}, `${r.label} : ${fr(r.d.point, 4)} (${fr(lo, 4)} – ${fr(hi, 4)})`)));
    });
    return svg;
  }
  const groupLabel = (name, g) => name === 'famille' ? (overview.family_labels[g] || g) : name === 'compétence' ? (SKILL_LABEL[g] || g) : g;
  function sliceChart(res, name) {
    const sl = res.slices.find(x => x.slice === name);
    if (!sl) return h('p', {class: 'muted', text: 'Tranche indisponible.'});
    const rows = sl.rows.map(r => ({...r, label: groupLabel(name, r.group), d: r.elo_minus_gru && r.elo_minus_gru.brier}));
    const word = d => !d ? 'trop peu d’élèves' : d.ci95[1] < 0 ? 'Elo meilleur' : d.ci95[0] > 0 ? 'GRU meilleur' : 'pas de différence nette';
    return h('div', {class: 'panel'},
      diffChart(rows) || h('p', {class: 'muted', text: 'Pas assez d’élèves par tranche pour un intervalle.'}),
      table([name[0].toUpperCase() + name.slice(1), 'Questions', 'Élèves', 'Brier Elo', 'Brier GRU', 'Brier naïf', 'Elo − GRU (IC 95 %)', 'Lecture'], rows.map(r => {
        const best = Math.min(r.elo, r.gru, r.naive);
        return [r.label, int(r.questions), int(r.learners), {text: fr(r.elo, 4), win: r.elo === best}, {text: fr(r.gru, 4), win: r.gru === best}, {text: fr(r.naive, 4), win: r.naive === best},
          r.d ? `${fr(r.d.point, 4)} (${fr(r.d.ci95[0], 4)} – ${fr(r.d.ci95[1], 4)})` : '—', word(r.d)];
      }), [1, 2, 3, 4, 5, 6]));
  }
  function comparaison() {
    const box = $('view-comparaison');
    const main = overview.main;
    if (!main) { put(box, h('div', {class: 'empty', text: 'Comparaison pas encore calculée.'})); return Promise.resolve(); }
    const seeds = Object.keys(main.seeds);
    const t = main.seeds[seeds[0]];
    const cf = main.crossfit;
    const tr = res => table(['Écart à la vraie probabilité', 'Elo', 'GRU', 'Naïf'], [
      ['Erreur quadratique moyenne', ...MODELS.map(([k]) => fr(res.truth_recovery[k].mse_to_truth, 4))],
      ['Corrélation avec la vraie probabilité', ...MODELS.map(([k]) => fr(res.truth_recovery[k].corr_with_truth, 3))],
      ['Tendance : même sens que la vraie évolution', ...MODELS.map(([k]) => pct(res.trend[k] && res.trend[k].same_direction))],
      ['Tendance : corrélation avec la vraie évolution', ...MODELS.map(([k]) => fr(res.trend[k] && res.trend[k].corr_with_true_change, 3))]], [1, 2, 3]);
    put(box, h('h2', {text: 'Elo, GRU et méthode naïve'}),
      h('p', {class: 'sub', text: 'Mêmes questions, mêmes élèves : chaque prévision est faite avant la réponse, avec le seul passé. Les intervalles viennent de 1 000 tirages d’élèves entiers (bootstrap par élève). Le Brier de la vraie probabilité cachée est le meilleur score possible en moyenne.'}),
      h('div', {class: 'sim-stack'},
        h('div', {class: 'panel'}, h('h3', {text: `Test : ${int(t.common.learners)} élèves jamais vus par le GRU`}),
          h('p', {text: `Campagne A1, partition par élève 70/15/15 (${main.splits.train} / ${main.splits.validation} / ${main.splits.test}). GRU graine ${seeds[0]}. ${int(t.common.questions)} questions où les trois modèles prévoient.`}),
          resultTable(t), verdict(t), diffTable(t), h('p', {class: 'sub', text: `Meilleur Brier possible (vraie probabilité) : ${fr(t.truth_recovery.oracle.brier, 4)}.`})),
        h('div', {class: 'panel'}, h('h3', {text: `Les ${int(cf.common.learners)} élèves, en validation croisée`}),
          h('p', {text: `Cinq GRU, chacun entraîné sans un cinquième des élèves, puis évalué sur eux : chaque élève est prédit par un réseau qui ne l’a jamais vu. ${int(cf.common.questions)} questions.`}),
          resultTable(cf), verdict(cf), diffTable(cf), h('p', {class: 'sub', text: `Meilleur Brier possible : ${fr(cf.truth_recovery.oracle.brier, 4)}.`}))),
      h('div', {class: 'sim-grid'},
        h('div', {class: 'panel'}, h('h3', {text: 'Fiabilité des probabilités'}), h('p', {text: 'Chaque point : un groupe de prévisions. Sur la diagonale, une probabilité de 70 % se réalise 7 fois sur 10.'}),
          calibration(cf), legend([['Elo', 'c-elo', 'dot'], ['GRU', 'c-gru', 'dot'], ['Naïf', 'c-naive', 'dot']])),
        h('div', {class: 'panel'}, h('h3', {text: 'Retrouver le niveau caché'}),
          h('p', {text: 'Un niveau Elo et un état GRU ne se comparent pas directement au niveau caché. Mesure commune : la probabilité de réussir chaque question. Tendance : variation entre le premier et le dernier tiers des questions de chaque élève et compétence.'}),
          tr(cf))),
      cf.elo_abstains ? h('div', {class: 'panel', style: 'margin-top:var(--s5)'}, h('h3', {text: 'Quand Elo s’abstient'}),
        h('p', {text: `Elo ne prévoit pas tant qu’une compétence a moins de 5 réponses (${int(cf.elo_abstains.questions)} questions, ${int(cf.elo_abstains.learners)} élèves). Le GRU et le naïf prévoient quand même :`}),
        table(['Modèle', 'Brier', 'Log-loss', 'Calibration (ECE)'], [['GRU', 'gru'], ['Naïf', 'naive']].map(([l, k]) => [l, fr(cf.elo_abstains.metrics[k].brier, 4), fr(cf.elo_abstains.metrics[k].log_loss, 4), fr(cf.elo_abstains.metrics[k].ece, 3)]), [1, 2, 3]),
        (d => h('p', {class: 'sub', text: `GRU − naïf : ${fr(d.point, 4)} (IC 95 % ${fr(d.ci95[0], 4)} – ${fr(d.ci95[1], 4)}). Ce n’est pas une erreur d’Elo : c’est sa règle d’abstention.`}))(cf.elo_abstains.bootstrap.differences['gru-naive:brier'])) : null,
      h('h3', {text: 'Selon la quantité d’historique'}), h('p', {class: 'sub', text: 'Nombre de réponses déjà données par l’élève avant la question. Elo s’abstient avant 5 réponses dans la compétence : ces questions sont hors de la comparaison commune.'}),
      sliceChart(cf, 'historique (réponses déjà données)'),
      h('h3', {text: 'Par compétence'}), sliceChart(cf, 'compétence'),
      h('h3', {text: 'Par famille d’élèves'}), sliceChart(cf, 'famille'),
      h('h3', {text: 'Après une pause (oubli)'}), sliceChart(cf, 'pause avant la question'),
      h('h3', {text: 'Par exercice'}), sliceChart(cf, 'exercice'),
      h('h3', {text: 'Stabilité selon la graine du GRU'}),
      table(['Graine', 'Brier Elo', 'Brier GRU', 'Brier naïf', 'Elo − GRU (IC 95 %)', 'Époques'], seeds.map(sd => {
        const r = main.seeds[sd], d = r.common.bootstrap.differences['elo-gru:brier'];
        return [sd, fr(r.common.metrics.elo.brier, 4), fr(r.common.metrics.gru.brier, 4), fr(r.common.metrics.naive.brier, 4), `${fr(d.point, 4)} (${fr(d.ci95[0], 4)} – ${fr(d.ci95[1], 4)})`, int(r.gru_config.epochs_completed)];
      }), [1, 2, 3, 5]),
      overview.replications ? h('div', {}, h('h3', {text: 'Autres populations du même simulateur'}),
        table(['Campagne', 'Questions', 'Brier Elo', 'Brier GRU', 'Brier naïf', 'Elo − GRU (IC 95 %)'], Object.entries(overview.replications).map(([n, r]) => {
          const d = r.common.bootstrap.differences['elo-gru:brier'];
          return [n, int(r.common.questions), fr(r.common.metrics.elo.brier, 4), fr(r.common.metrics.gru.brier, 4), fr(r.common.metrics.naive.brier, 4), `${fr(d.point, 4)} (${fr(d.ci95[0], 4)} – ${fr(d.ci95[1], 4)})`];
        }), [1, 2, 3, 4])) : null);
    return Promise.resolve();
  }

  // ---------------------------------------------------------------- experiments
  function experiences() {
    const box = $('view-experiences');
    const parts = [h('h2', {text: 'Expériences'}), h('p', {class: 'sub', text: 'Chaque expérience change une seule chose : la taille des données, le simulateur, le bruit des réponses ou les familles vues à l’entraînement.'})];
    const size = overview.size;
    if (size) {
      const cohorts = Object.keys(size.cohorts);
      const mean = (c, k) => { const v = Object.values(size.cohorts[c]).map(r => r.common.metrics[k].brier); return v.reduce((a, b) => a + b, 0) / v.length; };
      const spread = c => { const v = Object.values(size.cohorts[c]).map(r => r.common.metrics.gru.brier); return [Math.min(...v), Math.max(...v)]; };
      parts.push(h('h3', {text: 'Le GRU s’améliore-t-il avec plus d’élèves ?'}),
        h('p', {class: 'sub', text: `Cohorte L1 (1 000 élèves). Test fixe de ${size.layout.test} élèves, validation fixe de ${size.layout.validation} ; entraînement sur 70 % d’une cohorte de 50, 200 ou 1 000 élèves, trois graines chacune. Elo et le naïf ne dépendent pas de la cohorte.`}),
        barsChart({groups: cohorts.map(c => ({label: `${c} élèves`, values: {elo: mean(c, 'elo'), gru: mean(c, 'gru'), naive: mean(c, 'naive')}, ci: {gru: spread(c)}})), keys: MODELS.map(([k]) => [k, COLOR[k]]), ylabel: 'Brier', fmt: v => fr(v, 3)}),
        legend([['Elo', 'c-elo'], ['GRU (barre noire : écart entre graines)', 'c-gru'], ['Naïf', 'c-naive']]),
        table(['Cohorte', 'Élèves d’entraînement', 'Brier GRU par graine', 'Brier Elo', 'Brier naïf', 'Elo − GRU, graine 42 (IC 95 %)'], cohorts.map(c => {
          const r = size.cohorts[c], s0 = Object.values(r)[0], d = s0.common.bootstrap.differences['elo-gru:brier'];
          return [c, int(s0.train_learners), Object.values(r).map(x => fr(x.common.metrics.gru.brier, 4)).join(' · '), fr(s0.common.metrics.elo.brier, 4), fr(s0.common.metrics.naive.brier, 4), `${fr(d.point, 4)} (${fr(d.ci95[0], 4)} – ${fr(d.ci95[1], 4)})`];
        }), [1, 3, 4]));
    }
    const sens = overview.sensitivity, mainRes = overview.main;
    if (sens && mainRes) {
      parts.push(h('h3', {text: 'Le GRU était-il sous-entraîné ?'}),
        h('p', {class: 'sub', text: 'Le réglage O08 (12 époques au plus) s’est parfois arrêté pendant que la validation progressait encore. Même partition A1, mêmes graines, jusqu’à 40 époques (patience 6), modèle choisi sur la validation seulement.'}),
        table(['Graine', 'Meilleure époque (12 max)', 'Brier GRU (12 max)', 'Meilleure époque (40 max)', 'Brier GRU (40 max)', 'Brier Elo'], Object.entries(sens.seeds).map(([sd, r]) => {
          const m = mainRes.seeds[sd];
          return [sd, m ? int(m.gru_config.best_epoch) : '—', m ? fr(m.common.metrics.gru.brier, 4) : '—', int(r.best_epoch), fr(r.common.metrics.gru.brier, 4), fr(r.common.metrics.elo.brier, 4)];
        }), [1, 2, 3, 4, 5]));
    }
    const shift = overview.shift;
    if (shift) {
      const row = (label, r) => { const d = r.common.bootstrap.differences['elo-gru:brier']; return [label, int(r.common.questions), fr(r.common.metrics.elo.brier, 4), fr(r.common.metrics.gru.brier, 4), fr(r.common.metrics.naive.brier, 4), `${fr(d.point, 4)} (${fr(d.ci95[0], 4)} – ${fr(d.ci95[1], 4)})`, fr(r.truth_recovery.gru.mse_to_truth, 4)]; };
      parts.push(h('h3', {text: 'Un autre simulateur, des réponses plus bruyantes'}),
        h('p', {class: 'sub', text: 'B1 : lois d’apprentissage et d’oubli en puissance, bruit logistique, autres proportions de familles et une famille atypique (plateau puis décollage). N1 : même simulateur que A, bruit et inattention ×1,5. Le GRU entraîné sur A1 est évalué sans réentraînement (transfert), à côté d’un GRU entraîné sur la population elle-même.'}),
        table(['Évaluation', 'Questions', 'Brier Elo', 'Brier GRU', 'Brier naïf', 'Elo − GRU (IC 95 %)', 'GRU → vérité'], [
          row('B1 · GRU entraîné sur A1 (transfert)', shift.B1.trained_on_A1), row('B1 · GRU entraîné sur B1', shift.B1.trained_on_same_population),
          row('N1 · GRU entraîné sur A1 (transfert)', shift.N1.trained_on_A1), row('N1 · GRU entraîné sur N1', shift.N1.trained_on_same_population)], [1, 2, 3, 4, 6]));
      const at = shift.B1.atypical_family;
      if (at && at.trained_on_A1.common.questions) {
        const r1 = at.trained_on_A1, r2 = at.trained_on_B1;
        parts.push(h('h3', {text: 'Élèves à progression inhabituelle'}),
          h('p', {class: 'sub', text: `Famille « plateau puis décollage » de B1, absente de A. ${int(r1.common.learners)} élèves de test, ${int(r1.common.questions)} questions.`}),
          table(['', 'Brier Elo', 'Brier GRU', 'Brier naïf', 'Tendance GRU : même sens', 'Tendance Elo : même sens'], [
            ['GRU entraîné sur A1', fr(r1.common.metrics.elo.brier, 4), fr(r1.common.metrics.gru.brier, 4), fr(r1.common.metrics.naive.brier, 4), pct(at.trend_A1.gru && at.trend_A1.gru.same_direction), pct(at.trend_A1.elo && at.trend_A1.elo.same_direction)],
            ['GRU entraîné sur B1', fr(r2.common.metrics.elo.brier, 4), fr(r2.common.metrics.gru.brier, 4), fr(r2.common.metrics.naive.brier, 4), pct(at.trend_B1.gru && at.trend_B1.gru.same_direction), pct(at.trend_B1.elo && at.trend_B1.elo.same_direction)]], [1, 2, 3, 4, 5]));
      }
    }
    const fam = overview.families;
    if (fam) {
      parts.push(h('h3', {text: 'Une famille absente de l’entraînement'}),
        h('p', {class: 'sub', text: 'Cohorte L1. Pour chaque famille : un GRU entraîné sans elle, comparé à un GRU de même taille qui l’a vue, tous deux testés sur les élèves de cette famille.'}),
        table(['Famille', 'Élèves testés', 'Brier GRU sans la famille', 'Brier GRU avec (même taille)', 'Brier Elo', 'Brier naïf'], Object.entries(fam).map(([f, r]) =>
          [overview.family_labels[f] || f, int(r.absente.common.learners), fr(r.absente.common.metrics.gru.brier, 4), fr(r.presente_meme_taille.common.metrics.gru.brier, 4), fr(r.absente.common.metrics.elo.brier, 4), fr(r.absente.common.metrics.naive.brier, 4)]), [1, 2, 3, 4, 5]));
    }
    if (parts.length === 2) parts.push(h('div', {class: 'empty', text: 'Expériences pas encore calculées.'}));
    put(box, ...parts);
    return Promise.resolve();
  }

  // ---------------------------------------------------------------- technical
  async function technique() {
    const box = $('view-technique');
    tech = tech || await get(`/api/sim/${study}/technical`);
    const main = tech.models.find(m => m.name === 'A1-s42') || tech.models[0];
    const c = main ? main.config : null;
    const hist = main ? main.history : [];
    const prov = Object.entries(tech.provenance);
    put(box, h('h2', {text: 'Technique'}),
      c ? h('div', {class: 'sim-grid'},
        h('div', {class: 'panel'}, h('h3', {text: 'Le GRU DÉCLIC'}),
          table(['', ''], [['Architecture', `${c.architecture} (réutilisée du pipeline O08)`], ['Paramètres entraînables', int(c.parameters)],
            ['Entrée', `${c.K} compétences DÉCLIC × 4 (échecs et réussites récents, cumuls) + exercice précédent et demandé (${int(main.items)} exercices@niveau)`],
            ['Mémoire GRU', `${c.hidden} nombres, contexte ${c.context} réponses`], ['Entraînement', `AdamW, taux ${c.lr}, weight decay ${c.weight_decay}, lots de ${c.batch_size}, ${c.epochs_max} époques max, arrêt après ${c.patience} sans progrès`],
            ['Époques faites / meilleure', `${c.epochs_completed} / ${c.best_epoch}`], ['Élèves (entraînement / validation / test)', `${c.learners.train} / ${c.learners.validation} / ${c.learners.test}`],
            ['Durée d’entraînement (CPU)', `${fr(c.train_seconds, 1)} s`], ['Empreinte du fichier', c.model_sha256 ? c.model_sha256.slice(0, 16) + '…' : '—'], ['Entrées', c.inputs]], [])),
        h('div', {class: 'panel'}, h('h3', {text: 'Courbe d’entraînement (A1, graine 42)'}),
          lineChart({xs: hist.map(r => r.epoch), series: [{values: hist.map(r => r.train_loss), color: 'var(--m-naive)'}, {values: hist.map(r => r.validation.log_loss), color: 'var(--m-gru)'}],
                     ymin: Math.min(...hist.map(r => Math.min(r.train_loss, r.validation.log_loss))) - 0.01, ymax: Math.max(...hist.map(r => Math.max(r.train_loss, r.validation.log_loss))) + 0.01, xlabel: 'époque', ylabel: 'log-loss'}),
          legend([['Entraînement', 'c-naive'], ['Validation (sélection)', 'c-gru']]))) : h('div', {class: 'empty', text: 'Aucun modèle entraîné.'}),
      h('h3', {text: `Modèles sauvegardés (${tech.models.length})`}),
      table(['Nom', 'Élèves d’entraînement', 'Époques', 'Meilleure', 'Log-loss validation', 'Empreinte'], tech.models.map(m => {
        const best = m.history.reduce((a, r) => Math.min(a, r.validation.log_loss), Infinity);
        return [m.name, int(m.config.learners.train), int(m.config.epochs_completed), int(m.config.best_epoch), fr(best, 4), (m.config.model_sha256 || '').slice(0, 12)];
      }), [1, 2, 3, 4]),
      h('h3', {text: 'D’où viennent les paramètres du simulateur'}),
      table(['Élément', 'Nature', 'Source', 'Détail'], prov.map(([k, [kind, ref, text]]) => [k, h('span', {class: 'tag tag-' + kind, text: kind === 'inspired' ? 'inspiré d’une étude' : 'hypothèse'}), ref || '—', text]), []),
      h('h3', {text: 'Bruit de perception d’un débutant et d’un expert typiques'}),
      table(['Compétence', 'Unité', 'Débutant', 'Expert'], Object.keys(tech.units).map(k => [SKILL_LABEL[k], tech.units[k], fr(tech.beginner[k], 3), fr(tech.expert[k], 3)]), [2, 3]),
      h('h3', {text: 'Reproduire'}),
      h('pre', {class: 'cmd', text: (tech.reproduce && tech.reproduce.commands || ['python scripts/run_simulation_campaigns.py --worker 0', 'python scripts/run_simulation_campaigns.py --worker 1', 'python scripts/run_simulation_study.py inspect main replicate shift size families ui']).join('\n')}),
      h('p', {class: 'sub', text: 'Isolation : la simulation n’écrit que dans des fichiers synthetic-*.sqlite et refuse runtime/learning.sqlite ; l’horloge et le générateur de questions simulés ne sont actifs que dans le processus de simulation.'}));
  }

  const RENDER = {population, eleve, comparaison, experiences, technique};

  async function boot() {
    try {
      const list = await get('/api/sim/studies');
      if (!list.studies.length) { $('status').textContent = 'Aucune étude de simulation sur ce serveur.'; return; }
      study = list.studies[list.studies.length - 1].id;
      overview = await get(`/api/sim/${study}/overview`);
      const a1 = overview.inspection.A1;
      $('status').textContent = `Étude ${study} · ${Object.keys(overview.inspection).length} campagne${Object.keys(overview.inspection).length > 1 ? 's' : ''}` + (a1 ? ` · campagne principale : ${int(a1.n)} élèves, ${int(a1.questions)} questions sur ${a1.weeks} semaines.` : '.');
      const start = TABS.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'population';
      select(start);
      window.addEventListener('hashchange', () => { const t = location.hash.slice(1); if (TABS.includes(t)) select(t); });
    } catch (e) { fail($('view-population'))(e); $('status').textContent = 'Étude indisponible.'; }
  }
  window.DECLIC_BOOTED = true;
  boot();
})();
