// Phase 10 acceptance journey in real Chromium against a real server (fresh local database):
// profile → "Commencer une séance" → initial assessment answered through the interface (buttons,
// on-screen keyboard, space-bar tapping, staff) → interruption and resume → summary → parcours
// and O08 section → library → advanced level → error states and boot guard.
// The answers are read from the test database to play a scripted learner: a pipeline test only,
// never evidence about learning or about the reference model.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const {spawn, spawnSync} = require('node:child_process');
const fs = require('node:fs'), path = require('node:path'), net = require('node:net'), os = require('node:os');
const ROOT = path.resolve(__dirname, '../..');
const OUT = path.resolve(process.env.DECLIC_E2E_OUTPUT || path.join(ROOT, 'runtime/e2e-learner'));
fs.mkdirSync(OUT, {recursive: true});
const python = process.env.DECLIC_PYTHON || 'python';
const DB = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'declic-learner-')), 'learning.sqlite');
const results = [], logs = [];
let server, browser, base;
const delay = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, label, ms = 30000) { const end = Date.now() + ms; let last; while (Date.now() < end) { try { if (await fn()) return; } catch (e) { last = e; } await delay(75); } throw new Error(`${label}: ${last || 'timeout'}`); }
async function test(name, fn) { await fn(); results.push({name, passed: true}); console.log(`PASS ${name}`); }
async function freePort() { return new Promise(r => { const s = net.createServer(); s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => r(p)); }); }); }

function stored(itemId) {
  const code = 'import sqlite3,sys,json;c=sqlite3.connect(sys.argv[1]);r=c.execute("SELECT exercise,level,answer,served FROM items WHERE id=?",(sys.argv[2],)).fetchone();print(json.dumps({"exercise":r[0],"level":r[1],"answer":json.loads(r[2]),"served":json.loads(r[3])}))';
  const run = spawnSync(python, ['-c', code, DB, itemId], {encoding: 'utf8'});
  assert.equal(run.status, 0, run.stderr);
  return JSON.parse(run.stdout);
}
async function currentItemId(page) {
  return page.evaluate(async () => {
    const id = localStorage.getItem('declic-learner');
    const l = await (await fetch(`/api/learn/learners/${id}`)).json();
    const s = await (await fetch(`/api/learn/sessions/${l.active_session.id}`)).json();
    return s.current_item && s.current_item.id;
  });
}

// Answer the item on screen through the interface. `correct` decides the scripted answer.
async function answer(page, correct) {
  await page.waitForSelector('.item:not(.feedback)');
  const id = await currentItemId(page);
  const {exercise, answer: a, served} = stored(id);
  if (await page.locator('.kb-keys').count()) {
    const notes = correct ? a.notes : a.notes.map((n, i) => i === a.notes.length - 1 ? n + 1 : n);
    for (const n of notes) await page.locator(`.kb-key[data-midi="${n}"]`).dispatchEvent('pointerdown');
    await page.getByRole('button', {name: 'Valider ma réponse'}).click();
  } else if (exercise === 'pulsation') {
    await page.getByRole('button', {name: 'Démarrer'}).click();
    await delay(120);
    const ioi = a.ioi * 1000 * (correct ? 1 : 0.8);
    for (let k = 0; k < a.sync + a.cont; k++) { await page.keyboard.press('Space'); await delay(ioi); }
  } else if (exercise === 'rythme-echo') {
    await until(() => page.getByRole('button', {name: 'À moi de taper'}).isEnabled(), 'listening done', 20000);
    await page.getByRole('button', {name: 'À moi de taper'}).click();
    const onsets = correct ? a.onsets : a.onsets.slice(0, -1);
    let prev = 0;
    for (const o of onsets) { await delay((o - prev) * 600); prev = o; await page.keyboard.press('Space'); }
    await page.getByRole('button', {name: 'Valider mon rythme'}).click();
  } else if (exercise === 'lecture') {
    if (served.accidentals) await page.locator(`.acc[data-acc="${a.accidental}"]`).click();
    const value = correct ? a.value : ['do', 'ré', 'mi', 'fa', 'sol', 'la', 'si'].find(l => l !== a.value);
    await page.locator('.options .btn-option', {hasText: new RegExp(`^\\d${value}$`)}).click();
  } else {
    const values = served.options.map(o => o.value);
    const value = correct ? a.value : values.find(v => v !== a.value);
    const label = served.options.find(o => o.value === value).label;
    await page.locator('.options .btn-option', {hasText: label}).first().click();
  }
  await page.waitForSelector('.feedback', {timeout: 30000});
  return exercise;
}
async function next(page) { await page.locator('.next button').click(); await page.waitForSelector('.feedback', {state: 'detached'}); }

(async () => {
  const env = {...process.env, DECLIC_LEARNING_DB: DB, PYTHONPATH: ROOT, PYTHONUTF8: '1', OMP_NUM_THREADS: '1'};
  base = 'http://127.0.0.1:' + await freePort();
  server = spawn(python, ['-B', '-m', 'uvicorn', 'axis7.server:app', '--host', '127.0.0.1', '--port', base.split(':').pop()], {cwd: ROOT, env, stdio: ['ignore', 'pipe', 'pipe']});
  server.stdout.on('data', b => logs.push(b.toString())); server.stderr.on('data', b => logs.push(b.toString()));
  await until(async () => (await fetch(base + '/api/learn/catalog')).ok, 'server', 60000);
  browser = await chromium.launch({headless: true, args: ['--autoplay-policy=no-user-gesture-required'],
    ...(process.env.DECLIC_BROWSER_EXECUTABLE ? {executablePath: process.env.DECLIC_BROWSER_EXECUTABLE} : {})});
  const context = await browser.newContext({viewport: {width: 1280, height: 900}, reducedMotion: 'reduce'});
  const page = await context.newPage(), errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await test('new learner without instrument: home → Commencer une séance → profile → initial assessment', async () => {
    await page.goto(base + '/');
    await page.getByRole('link', {name: /Commencer une séance/}).first().click();
    await page.waitForURL(/seance\.html/);
    await page.getByLabel('Votre prénom ou un pseudonyme').fill('Melek');
    await page.getByRole('button', {name: 'Créer mon profil'}).click();
    await until(() => page.getByRole('heading', {name: 'Bienvenue'}).isVisible(), 'start screen');
    assert.match(await page.locator('main').innerText(), /évaluation initiale/);
    await page.screenshot({path: path.join(OUT, '01-start.png')});
    await page.getByRole('button', {name: 'Commencer une séance'}).click();
    await page.waitForSelector('.item');
    assert.match(await page.locator('.progress').innerText(), /Évaluation initiale · question 1 sur 30/);
  });

  const kinds = new Set();
  await test('first session: success and failure are scored, feedback and prediction note shown', async () => {
    for (let i = 0; i < 10; i++) {
      const ex = await answer(page, i % 4 !== 3);
      assert.equal(await page.locator('.verdict').innerText(), i % 4 !== 3 ? 'Juste' : 'Pas encore', `${ex} #${i}`);
      if (!kinds.has(ex)) { kinds.add(ex); await page.screenshot({path: path.join(OUT, `02-feedback-${ex}.png`)}); }
      assert.ok(await page.locator('.forecast-note').count() === 1, 'every answer shows the prediction or its abstention');
      await next(page);
    }
  });

  await test('interrupted session is resumed on the same question after a reload', async () => {
    const pending = await currentItemId(page);
    await page.goto(base + '/web/seance.html');
    await until(() => page.getByRole('button', {name: /Reprendre ma séance \(10 \/ 30\)/}).isVisible(), 'resume button');
    await page.getByRole('button', {name: /Reprendre ma séance/}).click();
    await page.waitForSelector('.item');
    assert.equal(await currentItemId(page), pending);
    assert.match(await page.locator('.progress').innerText(), /question 11 sur 30/);
  });

  await test('the rest of the assessment through every instrument-free modality, then the summary', async () => {
    for (let i = 10; i < 30; i++) {
      const ex = await answer(page, i % 5 !== 0);
      if (!kinds.has(ex)) { kinds.add(ex); await page.screenshot({path: path.join(OUT, `02-feedback-${ex}.png`)}); }
      await next(page);
    }
    for (const k of ['hauteur-seuil', 'melodies', 'intervalles', 'rythmes', 'pulsation', 'lecture', 'echo']) assert.ok(kinds.has(k), k);
    await until(() => page.getByRole('heading', {name: /réponses? justes? sur 30/}).isVisible(), 'summary');
    const text = await page.locator('main').innerText();
    assert.match(text, /Votre seuil de hauteur/); assert.match(text, /Prochaine séance proposée/); assert.match(text, /Les prévisions de cette séance/);
    await page.screenshot({path: path.join(OUT, '03-summary.png'), fullPage: true});
  });

  await test('parcours: mastery map, skills, history, O08 section with pre-registered predictions', async () => {
    await page.getByRole('link', {name: 'Voir mon parcours'}).click();
    await until(() => page.getByRole('heading', {name: 'Mon parcours'}).isVisible(), 'parcours');
    await until(() => page.getByRole('heading', {name: 'O08 sur mes données'}).isVisible(), 'o08');
    const text = await page.locator('main').innerText();
    assert.match(text, /30\s+réponses corrigées/); assert.match(text, /Évaluation initiale/); assert.match(text, /S’abstient/);
    assert.match(text, /prévisions évaluées/);
    assert.ok(await page.locator('.lvl-next').count() >= 4, 'next steps are marked');
    await page.screenshot({path: path.join(OUT, '04-parcours.png'), fullPage: true});
    const exp = await page.evaluate(async () => (await fetch(document.querySelector('a[download]').href)).json());
    assert.equal(exp.encode_check.accepted, true); assert.equal(exp.o08_prepared_rows.length, 30);
  });

  await test('a new practice session built from the results, stopped early, then a new one', async () => {
    await page.getByRole('link', {name: 'Commencer une séance'}).first().click();
    await until(() => page.getByRole('button', {name: 'Commencer une séance'}).isVisible(), 'start');
    await page.getByRole('button', {name: 'Commencer une séance'}).click();
    await page.waitForSelector('.item');
    assert.match(await page.locator('.progress').innerText(), /^Séance · question 1 sur/);
    await page.getByText('Pourquoi cet exercice ?').click();
    assert.ok((await page.locator('.why p').innerText()).length > 10);
    for (let i = 0; i < 3; i++) { await answer(page, true); await next(page); }
    await page.getByRole('button', {name: 'Terminer maintenant'}).click();
    await until(() => page.locator('.notice-inline').isVisible(), 'confirmation');
    await page.getByRole('button', {name: 'Terminer maintenant'}).click();
    await until(() => page.getByRole('heading', {name: /sur 3$/}).isVisible(), 'early summary');
    assert.match(await page.locator('main').innerText(), /affichée sans réponse|Toutes vos réponses/);
  });

  await test('library: ten-field cards, references, advanced level playable', async () => {
    await page.goto(base + '/web/exercices.html');
    await until(async () => await page.locator('.card').count() === 12, 'cards');
    const card = page.locator('#intervalles');
    for (const f of ['1 · Objectif', '2 · Compétence évaluée', '3 · Difficulté', '4 · Prérequis', '5 · Consignes', '6 · Entrées', '7 · Résultat attendu', '8 · Correction', '9 · Métriques', '10 · Références'])
      assert.equal(await card.getByText(f, {exact: true}).count(), 1, f);
    await page.screenshot({path: path.join(OUT, '05-library.png')});
    await card.locator('tr', {hasText: '5 · 12 intervalles harmoniques'}).getByRole('link', {name: 'S’entraîner'}).click();
    await until(() => page.getByRole('button', {name: 'Commencer cet exercice'}).isVisible(), 'focused start');
    await page.getByRole('button', {name: 'Commencer cet exercice'}).click();
    await page.waitForSelector('.item');
    assert.match(await page.locator('.item .kicker').innerText(), /niveau 5/);
    assert.equal(await page.locator('.options .btn-option').count(), 12);
    await answer(page, true);
    assert.equal(await page.locator('.verdict').innerText(), 'Juste');
  });

  await test('advanced and expert levels of every family are playable without an instrument', async () => {
    for (const [exercise, level] of [['accords', 5], ['melodies', 5], ['echo', 5], ['rythme-echo', 4], ['lecture', 5], ['degres', 4], ['cadences', 4], ['hauteur-comparaison', 6], ['rythmes', 4]]) {
      await page.goto(base + `/web/seance.html?exercise=${exercise}&level=${level}`);
      await page.getByRole('button', {name: 'Commencer cet exercice'}).click();
      await page.waitForSelector('.item');
      assert.match(await page.locator('.item .kicker').innerText(), new RegExp(`niveau ${level}`));
      await answer(page, true);
      assert.equal(await page.locator('.verdict').innerText(), 'Juste', `${exercise} ${level}`);
      await page.screenshot({path: path.join(OUT, `05-advanced-${exercise}-${level}.png`)});
    }
  });

  await test('invalid input is refused without counting as a failure', async () => {
    await page.goto(base + '/web/exercices.html');
    await until(async () => await page.locator('.card').count() === 12, 'cards');
    await page.locator('#pulsation tr', {hasText: '1 · 100 BPM'}).getByRole('link', {name: 'S’entraîner'}).click();
    await page.getByRole('button', {name: 'Commencer cet exercice'}).click();
    await page.waitForSelector('.item');
    await page.getByRole('button', {name: 'Démarrer'}).click();
    await until(() => page.locator('.form-error').innerText().then(t => /Aucune frappe/.test(t)), 'invalid tapping message', 20000);
    assert.equal(await page.getByRole('button', {name: 'Recommencer'}).isEnabled(), true);
    assert.equal(await page.locator('.feedback').count(), 0);
  });

  await test('server down: a French message and a retry, never a fake result', async () => {
    await page.route('**/api/learn/**', r => r.abort());
    await page.goto(base + '/web/parcours.html');
    await until(() => page.getByRole('heading', {name: 'DÉCLIC ne répond pas'}).isVisible(), 'down message');
    await page.screenshot({path: path.join(OUT, '06-server-down.png')});
    await page.unroute('**/api/learn/**');
    await page.getByRole('button', {name: 'Réessayer'}).click();
    await until(() => page.getByRole('heading', {name: 'Mon parcours'}).isVisible(), 'recovered');
  });

  await test('boot guard: scripts that never run produce a recovery message', async () => {
    const p2 = await context.newPage();
    await p2.route('**/web/learn/*.js*', r => r.abort());
    await p2.goto(base + '/web/seance.html');
    await until(() => p2.getByRole('heading', {name: 'La page n’a pas pu démarrer'}).isVisible(), 'seance guard', 15000);
    await p2.route('**/web/living/*.js*', r => r.abort());
    await p2.goto(base + '/web/living.html');
    await until(() => p2.locator('#recovery').isVisible(), 'living guard', 15000);
    assert.match(await p2.locator('#recovery-message').innerText(), /scripts de la page/);
    await p2.close();
  });

  await test('one navigation across the learner pages, mobile layout without overflow', async () => {
    const pages = [['/', 'Accueil'], ['/web/seance.html', 'Séance'], ['/web/parcours.html', 'Parcours'], ['/web/exercices.html', 'Exercices'], ['/web/labo.html', 'Laboratoire']];
    for (const [url, name] of pages) {
      await page.goto(base + url);
      const nav = page.getByRole('navigation', {name: 'Navigation principale'});
      assert.deepEqual(await nav.getByRole('link').allInnerTexts(), pages.map(p => p[1]));
      assert.equal(await nav.getByRole('link', {name, exact: true}).getAttribute('aria-current'), 'page');
    }
    const mobile = await browser.newContext({viewport: {width: 390, height: 844}});
    const m = await mobile.newPage();
    await m.addInitScript(id => localStorage.setItem('declic-learner', id), await page.evaluate(() => localStorage.getItem('declic-learner')));
    for (const url of ['/', '/web/seance.html', '/web/parcours.html', '/web/exercices.html']) {
      await m.goto(base + url); await delay(700);
      assert.ok(await m.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), `no horizontal overflow on ${url}`);
    }
    await m.goto(base + '/web/parcours.html'); await delay(700);
    await m.screenshot({path: path.join(OUT, '07-mobile-parcours.png')});
    await mobile.close();
  });

  assert.deepEqual(errors, [], 'no uncaught page error');
  fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({scope: 'scripted learner on a fresh local database: pipeline evidence only', results}, null, 2));
  console.log(`learner journey: ${results.length} scenarios passed`);
})().catch(e => { console.error(e); fs.writeFileSync(path.join(OUT, 'server.log'), logs.join('')); process.exitCode = 1; })
  .finally(async () => { if (browser) await browser.close(); if (server) server.kill('SIGTERM'); });
