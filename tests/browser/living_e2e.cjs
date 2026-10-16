// Real Chromium + real HTTP + trained PyTorch tensors. Synthetic fixture mode is explicit.
// Optional DECLIC_E2E_REAL=1 uses private held-out data via DECLIC_PREPARED_DATA and unchanged registry.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const {spawn, spawnSync} = require('node:child_process');
const fs = require('node:fs'), path = require('node:path'), net = require('node:net');
const ROOT = path.resolve(__dirname, '../..'), OUT = path.resolve(process.env.DECLIC_E2E_OUTPUT || path.join(ROOT, 'runtime/e2e'));
fs.mkdirSync(OUT, {recursive: true});
const python = process.env.DECLIC_PYTHON || 'python', real = process.env.DECLIC_E2E_REAL === '1';
const results = [], logs = [];
let server, browser, base;
const delay = ms => new Promise(r => setTimeout(r, ms));
async function until(fn, label, ms=30000) { const end=Date.now()+ms; let last; while(Date.now()<end) { try { if(await fn()) return; } catch(e) {last=e;} await delay(75); } throw new Error(`${label}: ${last || 'timeout'}`); }
async function test(name, fn) { await fn(); results.push({name, passed:true}); console.log(`PASS ${name}`); }
async function freePort() {return new Promise(r=>{const s=net.createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>r(p));});});}
async function start(env) {
  server=spawn(python,['-B','-m','uvicorn','axis7.server:app','--host','127.0.0.1','--port',base.split(':').pop()],{cwd:ROOT,env,stdio:['ignore','pipe','pipe']});
  server.stdout.on('data',b=>logs.push(b.toString()));server.stderr.on('data',b=>logs.push(b.toString()));
  await until(async()=>{const r=await fetch(base+'/api/readiness');const s=await r.json();if(!r.ok)throw new Error(JSON.stringify(s));assert.equal(s.application,'declic-phase8');assert.equal(s.identity_contract,'living-generation-v1');assert.equal(s.data_mode,real?'private_research_data':'synthetic_fixture');return s.ready;},'readiness',60000);
}
async function stop() {if(!server || server.exitCode!==null)return;const p=server;await new Promise(resolve=>{p.once('exit',resolve);p.kill('SIGTERM');});}
async function selected(page,source,learner='01',cutoff=3) {await until(async()=>{const q=new URL(page.url()).searchParams;return q.get('source')===source&&q.get('learner')===learner&&q.get('cutoff')===String(cutoff)&&await page.locator('#fp-main .fp-ring').count()===cutoff;},'synchronized selection');}
async function views(page,cutoff) {assert.equal(await page.locator('#fp-main .fp-ring').count(),cutoff);assert.equal(await page.locator('#track .tl-bar').count(),cutoff);assert.equal(await page.locator('#cutoff').inputValue(),String(cutoff));assert.match(await page.locator('#cutoff-label').innerText(),new RegExp(` ${cutoff} sur `));}

(async()=>{
  const env={...process.env,OMP_NUM_THREADS:'1',MKL_NUM_THREADS:'1',PYTHONPATH:ROOT,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8'};
  if(!real) {
    const fixture=path.join(OUT,'fixture');
    const run=spawnSync(python,['-B','-m','scripts.integration_fixture',fixture],{cwd:ROOT,env,encoding:'utf8'});
    assert.equal(run.status,0,run.stdout+run.stderr);
    env.DECLIC_MODEL_REGISTRY=path.join(fixture,'registry');env.DECLIC_PREPARED_DATA=path.join(fixture,'prepared');
  }
  base='http://127.0.0.1:'+await freePort();await start(env);
  browser=await chromium.launch({headless:true,...(process.env.DECLIC_BROWSER_EXECUTABLE?{executablePath:process.env.DECLIC_BROWSER_EXECUTABLE}:{})});
  const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
  const page=await context.newPage(), errors=[];page.on('pageerror',e=>errors.push(e.message));
  await test('real readiness, frontend and neural inference, both sources',async()=>{
    for(const source of ['singpad','yousician']) {
      await page.goto(base+`/web/living.html?source=${source}&learner=01&cutoff=3`);await selected(page,source);await views(page,3);
      await page.getByRole('button',{name:/03 Mémoire GRU/}).click();
      await until(()=>page.getByRole('heading',{name:'La mémoire du réseau, pas après pas'}).isVisible(),'real GRU inspection');
      const r=await fetch(base+`/api/v7/o08/living/inspect?source=${source}&learner=01&cutoff=3`), i=await r.json();
      assert.equal(i.matches_served_forecast,true);assert.equal(i.architecture,'enhanced_gru');
      await page.getByRole('button',{name:/06 Évaluation/}).click();
      await page.getByRole('button',{name:'Révéler le résultat du pas 4'}).click();
      await until(async()=>/révélé après/.test(await page.locator('#status').innerText()),'real reveal');
      await page.screenshot({path:path.join(OUT,source+'-desktop.png'),fullPage:false});
    }
  });
  await test('refresh restores stage, research, concept and pinned comparison',async()=>{
    await page.goto(base+'/web/living.html?source=singpad&learner=01&cutoff=3&stage=gru&research=1&concept=3');await selected(page,'singpad');
    const node=page.locator('#sky g.node').first(), concept=await node.getAttribute('data-k');await node.click();
    await until(()=>new URL(page.url()).searchParams.get('concept')===concept,'selected concept URL');
    await page.getByRole('button',{name:'Comparer deux moments',exact:true}).click();
    await page.getByRole('button',{name:'Pas suivant',exact:true}).click();await selected(page,'singpad','01',4);
    await until(()=>new URL(page.url()).searchParams.get('compare')==='3','comparison URL');
    const before=new URL(page.url()).searchParams;await page.reload();await selected(page,'singpad','01',4);
    await until(()=>page.getByRole('heading',{name:'La mémoire du réseau, pas après pas'}).isVisible(),'restored GRU');
    assert.equal(await page.getByRole('checkbox',{name:'Mode recherche'}).isChecked(),true);
    assert.equal(new URL(page.url()).searchParams.get('concept'),before.get('concept'));
    await until(()=>page.locator('#fp-compare-figure').isVisible(),'restored comparison');
  });
  await test('ABA late cohort success cannot replace learner 02',async()=>{
    let release, captured=false;const gate=new Promise(r=>release=r);let first=true;
    const pattern='**/api/v7/o08/living/learners?source=singpad';
    await page.route(pattern,async route=>{if(first){first=false;const response=await route.fetch();captured=true;await gate;await route.fulfill({response});}else await route.continue();});
    await page.goto(base+'/web/living.html?source=singpad&cutoff=3');await until(()=>captured,'held request');
    await page.getByRole('combobox',{name:'Instrument et base',exact:true}).selectOption('yousician');await selected(page,'yousician');
    await page.getByRole('combobox',{name:'Instrument et base',exact:true}).selectOption('singpad');await selected(page,'singpad');
    await page.getByRole('combobox',{name:'Parcours réel de test',exact:true}).selectOption('02');await selected(page,'singpad','02');
    release();await delay(300);await selected(page,'singpad','02');await page.unroute(pattern);
  });
  await test('revisiting the same cutoff during pending inspection does not stall',async()=>{
    let release,captured=false;const gate=new Promise(r=>release=r);
    const pattern='**/api/v7/o08/living/inspect?source=singpad&learner=01&cutoff=3';
    await page.route(pattern,async route=>{const response=await route.fetch();captured=true;await gate;await route.fulfill({response});});
    await page.goto(base+'/web/living.html?source=singpad&learner=01&cutoff=3&stage=gru');await until(()=>captured,'held inspection');
    await page.locator('#cutoff').focus();await page.keyboard.press('Home');await selected(page,'singpad','01',1);
    await page.keyboard.press('ArrowRight');await page.keyboard.press('ArrowRight');await selected(page,'singpad','01',3);
    release();await until(()=>page.getByRole('heading',{name:'La mémoire du réseau, pas après pas'}).isVisible(),'inspection after revisit');await page.unroute(pattern);
  });
  await test('late URL comparison cannot override a newer pinned moment',async()=>{
    let release,captured=false;const gate=new Promise(r=>release=r);
    const pattern='**/api/v7/o08/living/state?source=singpad&learner=01&cutoff=3';
    await page.route(pattern,async route=>{const response=await route.fetch();captured=true;await gate;await route.fulfill({response});});
    await page.goto(base+'/web/living.html?source=singpad&learner=01&cutoff=4&compare=3');await selected(page,'singpad','01',4);await until(()=>captured,'pending comparison');
    await page.getByRole('button',{name:'Comparer deux moments',exact:true}).click();
    release();await delay(300);assert.equal(new URL(page.url()).searchParams.get('compare'),'4');await page.unroute(pattern);
  });
  await test('inspection connection failure offers recovery and retry',async()=>{
    const pattern='**/api/v7/o08/living/inspect?*';await page.route(pattern,r=>r.abort('connectionreset'));
    await page.goto(base+'/web/living.html?source=singpad&learner=01&cutoff=3&stage=gru');await selected(page,'singpad');
    await until(()=>page.locator('#recovery').isVisible(),'inspection transport error');
    assert.match(await page.locator('#status').innerText(),/Impossible de contacter/);await page.unroute(pattern);
    await page.getByRole('button',{name:'Réessayer le chargement'}).click();
    await until(()=>page.getByRole('heading',{name:'La mémoire du réseau, pas après pas'}).isVisible(),'inspection retry');
  });
  await test('obsolete source error cannot hide current valid source',async()=>{
    let release, captured=false;const gate=new Promise(r=>release=r), pattern='**/api/v7/o08/living/learners?source=yousician';
    await page.route(pattern,async route=>{captured=true;await gate;await route.fulfill({status:503,contentType:'application/json',body:'{"detail":"delayed failure"}'});});
    await page.getByRole('combobox',{name:'Instrument et base',exact:true}).selectOption('yousician');await until(()=>captured,'held failure');
    await page.getByRole('combobox',{name:'Instrument et base',exact:true}).selectOption('singpad');await selected(page,'singpad');
    release();await delay(250);assert.equal(await page.locator('#stage').isVisible(),true);assert.equal(await page.locator('#recovery').isVisible(),false);await page.unroute(pattern);
  });
  await test('wrong-model reveal rejected and expired receipt safely refreshed once',async()=>{
    const pattern='**/api/v7/o08/living/reveal';
    await page.route(pattern,async route=>{const response=await route.fetch(),p=await response.json();p.identity.model_id='wrong-model';p.model_id='wrong-model';await route.fulfill({response,json:p});});
    await page.getByRole('button',{name:/06 Évaluation/}).click();await page.getByRole('button',{name:'Révéler le résultat du pas 4'}).click();
    await until(()=>page.locator('#recovery').isVisible(),'rejected reveal');assert.match(await page.locator('#status').innerText(),/incohérente/);await page.unroute(pattern);
    let count=0;
    await page.route(pattern,async route=>{count++;if(count===1)await route.fulfill({status:409,contentType:'application/json',body:'{"detail":"expired"}'});else await route.continue();});
    await page.getByRole('button',{name:'Révéler le résultat du pas 4'}).click();await until(async()=>/révélé après/.test(await page.locator('#status').innerText()),'expiry refresh');assert.equal(count,2);await page.unroute(pattern);
  });
  await test('interrupted connection gets French recovery and successful retry',async()=>{
    const pattern='**/api/v7/o08/living/state?*';await page.route(pattern,r=>r.abort('connectionreset'));
    await page.getByRole('button',{name:'Pas suivant',exact:true}).click();await until(()=>page.locator('#recovery').isVisible(),'transport error');
    assert.match(await page.locator('#status').innerText(),/Impossible de contacter/);await views(page,3);
    assert.equal(new URL(page.url()).searchParams.get('cutoff'),'3');
    await page.screenshot({path:path.join(OUT,'network-recovery.png')});await page.unroute(pattern);
    await page.getByRole('button',{name:'Réessayer le chargement'}).click();await selected(page,'singpad','01',4);assert.equal(await page.locator('#recovery').isVisible(),false);
  });
  await test('stopped backend and restart recover without retry storm',async()=>{
    await stop();await page.getByRole('button',{name:'Pas suivant',exact:true}).click();await until(()=>page.locator('#recovery').isVisible(),'connection refusal');
    await start(env);await page.getByRole('button',{name:'Réessayer le chargement'}).click();await selected(page,'singpad','01',5);await views(page,5);
  });
  await test('HTTP404/503 are diagnosed and recover after restoration',async()=>{
    const pattern='**/api/v7/o08/living/learners?*';
    for(const code of [404,503]) {
      await page.route(pattern,r=>r.fulfill({status:code,contentType:'application/json',body:'{"detail":"controlled"}'}));
      await page.goto(base+'/web/living.html');await until(()=>page.locator('#recovery').isVisible(),'HTTP'+code);
      assert.match(await page.locator('#status').innerText(),code===404?/API.*absente/:/pas prêts/);await page.unroute(pattern);
    }
    await page.getByRole('button',{name:'Réessayer le chargement'}).click();await selected(page,'singpad');
  });
  await test('keyboard, mobile and no false never-transmitted statement',async()=>{
    await page.locator('#cutoff').focus();await page.keyboard.press('End');await until(async()=>Number(await page.locator('#cutoff').inputValue())>3,'end');
    await page.keyboard.press('Home');await until(()=>page.locator('#fp-main .fp-ring').count().then(x=>x===1),'rewind');
    assert.doesNotMatch(await page.locator('#status').innerText(),/n.a pas été transmis/);
    await page.setViewportSize({width:391,height:827});await page.screenshot({path:path.join(OUT,'mobile.png')});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
  });
  assert.deepEqual(errors,[]);await browser.close();browser=null;await stop();
  await until(async()=>{try{await fetch(base+'/api/health');return false;}catch{return true;}},'clean shutdown');
  results.push({name:'clean server shutdown',passed:true});
  fs.writeFileSync(path.join(OUT,'results.json'),JSON.stringify({mode:real?'real_held_out_data':'synthetic_fixture_real_weights',results,errors,base},null,2));
  console.log(JSON.stringify({passed:results.length,mode:real?'real_held_out_data':'synthetic_fixture_real_weights'}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();await stop();fs.writeFileSync(path.join(OUT,'server.log'),logs.join(''));});
