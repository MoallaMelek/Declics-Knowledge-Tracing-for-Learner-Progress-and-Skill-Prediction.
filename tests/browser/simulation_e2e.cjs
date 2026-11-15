// Élèves virtuels (SYNTHETIC simulation study) in real Chromium against a real server.
// Reads the committed study under artifacts/simulation/: every number checked on screen is
// compared with the API, which only serves those files.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const fs = require('node:fs'), path = require('node:path'), net = require('node:net'), os = require('node:os');
const ROOT = path.resolve(__dirname, '../..');
const OUT = path.resolve(process.env.DECLIC_E2E_OUTPUT || path.join(ROOT, 'runtime/e2e-simulation'));
fs.mkdirSync(OUT, {recursive: true});
const python = process.env.DECLIC_PYTHON || 'python';
const DB = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'declic-sim-')), 'learning.sqlite');
const results = [], logs = [];
let server, browser, base;
const delay = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, label, ms = 30000) { const end = Date.now() + ms; let last; while (Date.now() < end) { try { if (await fn()) return; } catch (e) { last = e; } await delay(75); } throw new Error(`${label}: ${last || 'timeout'}`); }
async function test(name, fn) { await fn(); results.push({name, passed: true}); console.log(`PASS ${name}`); }
async function freePort() { return new Promise(r => { const s = net.createServer(); s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => r(p)); }); }); }
const fr = (v, d) => Number(v).toLocaleString('fr-FR', {minimumFractionDigits: d, maximumFractionDigits: d});

(async () => {
  const env = {...process.env, DECLIC_LEARNING_DB: DB, PYTHONPATH: ROOT, PYTHONUTF8: '1', OMP_NUM_THREADS: '1'};
  base = 'http://127.0.0.1:' + await freePort();
  server = spawn(python, ['-B', '-m', 'uvicorn', 'axis7.server:app', '--host', '127.0.0.1', '--port', base.split(':').pop()], {cwd: ROOT, env, stdio: ['ignore', 'pipe', 'pipe']});
  server.stdout.on('data', b => logs.push(b.toString())); server.stderr.on('data', b => logs.push(b.toString()));
  await until(async () => (await fetch(base + '/api/sim/studies')).ok, 'server', 60000);
  const studies = await (await fetch(base + '/api/sim/studies')).json();
  assert.ok(studies.synthetic && studies.studies.length, 'a committed study is served');
  const study = studies.studies[studies.studies.length - 1].id;
  const overview = await (await fetch(`${base}/api/sim/${study}/overview`)).json();
  browser = await chromium.launch();
  const page = await (await browser.newContext({viewport: {width: 1280, height: 900}})).newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await test('the Laboratoire leads to the study, flagged as synthetic', async () => {
    await page.goto(base + '/web/labo.html');
    await page.getByRole('link', {name: /Élèves virtuels/}).click();
    await until(() => page.getByRole('heading', {name: 'Élèves virtuels', level: 1}).isVisible(), 'page');
    assert.match(await page.locator('.synthetic-flag').innerText(), /DONNÉES SYNTHÉTIQUES|Données synthétiques/i);
    assert.equal(await page.getByRole('navigation', {name: 'Navigation principale'}).getByRole('link', {name: 'Laboratoire'}).getAttribute('aria-current'), 'page');
  });

  await test('population: the counts on screen are the campaign’s real counts', async () => {
    await until(() => page.locator('.kpi').first().isVisible(), 'kpis');
    const a1 = overview.inspection.A1;
    const kpis = await page.locator('.kpi').allInnerTexts();
    assert.ok(kpis.some(t => t.includes(a1.questions.toLocaleString('fr-FR')) && /questions traitées/.test(t)), 'questions');
    assert.ok(kpis.some(t => t.startsWith(String(a1.dropouts)) && /abandons/.test(t)), 'dropouts');
    assert.ok(await page.locator('#view-population svg.chart').count() >= 2);
    await page.selectOption('#campaign', Object.keys(overview.inspection).slice(-1)[0]);
    await until(async () => (await page.locator('.kpi').first().innerText()).startsWith(String(Object.values(overview.inspection).slice(-1)[0].n.toLocaleString('fr-FR'))), 'campaign switch');
    await page.screenshot({path: path.join(OUT, '01-population.png'), fullPage: false});
  });

  await test('one virtual learner: predictions before each answer, hidden truth, sessions', async () => {
    await page.getByRole('tab', {name: 'Un élève'}).click();
    await until(() => page.locator('#learner-chart svg.chart').isVisible(), 'learner chart', 30000);
    const first = await page.locator('#learner option').first().getAttribute('value');
    const api = await (await fetch(`${base}/api/sim/${study}/learner/${first}`)).json();
    assert.ok(api.synthetic && api.questions.length > 0);
    const kpis = await page.locator('#view-eleve .kpi').allInnerTexts();
    assert.ok(kpis.some(t => t.includes(api.questions.length.toLocaleString('fr-FR')) && /questions/.test(t)));
    const options = await page.locator('#learner option').count();
    const other = await page.locator('#learner option').nth(Math.min(5, options - 1)).getAttribute('value');
    const otherApi = await (await fetch(`${base}/api/sim/${study}/learner/${other}`)).json();
    await page.selectOption('#learner', other);
    await until(async () => (await page.locator('#view-eleve .kpi').allInnerTexts()).some(t => t.includes(otherApi.family_label))
      && (await page.locator('#view-eleve .kpi').nth(1).innerText()).includes(otherApi.questions.length.toLocaleString('fr-FR')), 'learner switch');
    await page.selectOption('#skill', 'toutes');
    assert.ok(await page.locator('#learner-chart path').count() >= 4);
    await page.screenshot({path: path.join(OUT, '02-learner.png'), fullPage: true});
  });

  await test('Elo vs GRU vs naive: the table matches the measured results', async () => {
    await page.getByRole('tab', {name: 'Elo, GRU, naïf'}).click();
    await until(() => page.locator('#view-comparaison table.sim').first().isVisible(), 'comparison');
    const seed = String(overview.config.gru.seeds[0]);   // the primary seed shown first
    const m = overview.main.seeds[seed].common.metrics;
    const text = await page.locator('#view-comparaison .panel').first().innerText();
    for (const k of ['elo', 'gru', 'naive']) assert.ok(text.includes(fr(m[k].brier, 4)), `${k} Brier ${fr(m[k].brier, 4)} on screen`);
    assert.match(text, /Lecture\./);
    assert.match(text, new RegExp(`GRU graine ${seed}`));
    await page.screenshot({path: path.join(OUT, '03-comparison.png'), fullPage: true});
  });

  await test('experiments and technical views render from the study files', async () => {
    await page.getByRole('tab', {name: 'Expériences'}).click();
    await until(() => page.locator('#view-experiences h2').isVisible(), 'experiments');
    await page.getByRole('tab', {name: 'Technique'}).click();
    await until(() => page.locator('#view-technique table.sim').first().isVisible(), 'technical');
    const tech = await (await fetch(`${base}/api/sim/${study}/technical`)).json();
    assert.match(await page.locator('#view-technique').innerText(), new RegExp(`Modèles sauvegardés \\(${tech.models.length}\\)`));
  });

  await test('keyboard tabs, deep link and mobile layout without overflow', async () => {
    await page.getByRole('tab', {name: 'Population'}).focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.getByRole('tab', {name: 'Un élève'}).getAttribute('aria-selected'), 'true');
    const mobile = await browser.newContext({viewport: {width: 390, height: 844}});
    const m = await mobile.newPage();
    for (const hash of ['#population', '#eleve', '#comparaison', '#experiences', '#technique']) {
      await m.goto(base + '/web/simulation.html' + hash);
      await until(async () => (await m.locator(`#view-${hash.slice(1)}`).innerText()).length > 40, hash, 30000);
      assert.ok(await m.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), `no horizontal overflow on ${hash}`);
    }
    await m.screenshot({path: path.join(OUT, '04-mobile.png')});
    await mobile.close();
  });

  assert.deepEqual(errors, [], 'no uncaught page error');
  fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({scope: 'synthetic simulation study views', results}, null, 2));
  console.log(`simulation views: ${results.length} scenarios passed`);
})().catch(e => { console.error(e); fs.writeFileSync(path.join(OUT, 'server.log'), logs.join('')); process.exitCode = 1; })
  .finally(async () => { if (browser) await browser.close(); if (server) server.kill('SIGTERM'); });
