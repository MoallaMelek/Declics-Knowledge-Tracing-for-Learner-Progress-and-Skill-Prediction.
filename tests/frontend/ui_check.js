// Drives the real web/app.js in a VM with a stubbed DOM and fetch. Responses are real API payloads written by tests/test_frontend.py.
// usage: node ui_check.js <app.js> <fixtures.json>
const fs=require('fs'),vm=require('vm');
const appPath=process.argv[2];
const fx=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const ev={schema_version:'1.0',attempt_id:'ui:new:1',student_id:'ui-new-learner',session_id:'ui-session',exercise_id:'ui-ex',instrument:'piano',timestamp:'2026-03-01T10:00:00+00:00',provenance:'project',rubric_version:'provisional',observations:[{skill_id:'pitch',outcome:1}],upstream_versions:{}};
const els={};
function makeEl(id){
  const e={id,_html:'',_opts:[],textContent:'',hidden:false,className:'',dataset:{},style:{},selectedOptions:[],disabled:false,
    classList:{add(){},remove(){},toggle(){}},setAttribute(){},querySelectorAll(){return []},querySelector(){return null},
    scrollIntoView(){},focus(){},closest(){return null},onclick:null,onchange:null,oninput:null,onkeydown:null};
  Object.defineProperty(e,'innerHTML',{get(){return this._html},set(v){this._html=String(v);this._opts=[...this._html.matchAll(/<option value="([^"]*)"/g)].map(m=>m[1]);this._v=this._opts[0]??'';}});
  Object.defineProperty(e,'value',{get(){return this._v??''},set(x){this._v=(this._opts.length===0||this._opts.includes(String(x)))?String(x):''}});
  return e;
}
function el(id){return els[id]||(els[id]=makeEl(id));}
let learnersPayload=fx.learners0;
const log=[];
async function fetch(url,opts={}){
  const method=opts.method||'GET';log.push(method+' '+url);
  const u=new URL(url,'http://127.0.0.1');const p=u.pathname;let body;
  if(p==='/api/learners')body=learnersPayload;
  else if(p.startsWith('/api/twin/')){if(p.endsWith('ui-new-learner')&&learnersPayload===fx.learners2)return {ok:false,status:404,json:async()=>({detail:'Learner not found'})};body=p.endsWith('ui-new-learner')?fx.ingest.twin:fx.twin0;}
  else if(p==='/api/attempts'&&method==='POST'){body=fx.ingest;learnersPayload=fx.learners1;}
  else if(p.startsWith('/api/reset/')){body=fx.reset;learnersPayload=fx.learners2;}
  else if(p.startsWith('/api/experiments'))body={};
  else body={};
  return {ok:true,status:200,json:async()=>JSON.parse(JSON.stringify(body))};
}
const document={getElementById:el,activeElement:null,querySelectorAll(){return []},createElement(){return {click(){},href:'',download:''}}};
const sandbox={document,fetch,console,URL,Blob:function(){},setTimeout,clearTimeout,Date};
sandbox.URL={createObjectURL(){return 'blob:x'},revokeObjectURL(){}};
const ctx=vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(appPath,'utf8'),ctx);
const tick=()=>new Promise(r=>setTimeout(r,30));
const get=(expr)=>vm.runInContext(expr,ctx);
const results=[];
function check(name,ok,detail=''){results.push([ok,name,detail]);}
(async()=>{
  await tick();
  check('initial learner selected',get('state.student')===fx.learners0.learners[0].id,get('state.student'));
  check('selector matches state initially',el('learner').value===get('state.student'));
  el('event-json').value=JSON.stringify(ev);
  await el('ingest').onclick();await tick();
  check('ingest selects the new learner in state',get('state.student')==='ui-new-learner',get('state.student'));
  check('ingest selector shows new learner',el('learner').value==='ui-new-learner',el('learner').value);
  check('ingest twin belongs to new learner',get('state.twin.student')==='ui-new-learner');
  await el('reset').onclick();await tick();
  check('reset returns to a listed learner',get('state.student')===fx.learners2.learners[0].id,get('state.student'));
  check('reset selector matches state',el('learner').value===get('state.student'),el('learner').value);
  check('reset message reports removal of ingested profile',/supprimé/.test(el('changes').textContent),el('changes').textContent);
  check('no error alert shown',el('alert').hidden===true,el('alert').textContent);
  for(const [ok,name,d] of results)console.log((ok?'PASS ':'FAIL ')+name+(ok?'':'  ['+d+']'));
  const passed=results.filter(r=>r[0]).length;console.log(`${passed}/${results.length} checks passed`);
  if(passed!==results.length)process.exitCode=1;
})().catch(e=>{console.log('HARNESS ERROR',e.message);process.exitCode=2;});
