// Real musician.js state/DOM logic fed by actual collection API responses.
const fs=require('fs'),vm=require('vm');
const fx=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const elements=new Map();let busyPost=false,resolvePost,failFirst=false,rejectionStatus=null,missingProfile=false;const writes=[];
function el(id){if(!elements.has(id))elements.set(id,{id,hidden:false,textContent:'',innerHTML:'',value:'self',checked:false,disabled:false,attrs:{},setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this.attrs[k]},focus(){},scrollIntoView(){}});return elements.get(id);}
const nav=['home','practice','progress','notebook'].map(page=>({dataset:{page},attrs:{},setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this.attrs[k]},disabled:false}));
const radios={pitch:'comfortable'};
const document={getElementById:el,querySelectorAll(s){return s.includes('nav')?nav:s==='button,select,input'?nav.concat([...elements.values()]):s.includes('#assessment input')?[el('assessment-source')]:[];},querySelector(s){const id=s.match(/rating-([^"\]]+)/)?.[1];return id&&radios[id]?{value:radios[id]}:null;},createElement(){return {click(){}}}};
const storage=new Map();let uuidCounter=0;
const sandbox={document,console,Date,URLSearchParams,location:{search:""},setTimeout,clearTimeout,crypto:{randomUUID:()=>`ui-attempt-${++uuidCounter}`},Blob:function(){},URL:{createObjectURL:()=>'',revokeObjectURL(){}},localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},fetch:async(path,options={})=>{
 if(options.method==='POST'){writes.push({path,body:JSON.parse(options.body)});if(path==='/api/practice/sessions'){if(busyPost)await new Promise(r=>resolvePost=r);if(failFirst){failFirst=false;throw new Error('network interrupted');}if(rejectionStatus)return {ok:false,status:rejectionStatus,json:async()=>fx.rejections[rejectionStatus]};return {ok:true,json:async()=>fx.saved};}return {ok:true,json:async()=>fx.profile};}
 if(missingProfile&&path.includes('/summary/'))return {ok:false,status:404,json:async()=>fx.rejections['404']};
 return {ok:true,json:async()=>path.includes('catalog')?fx.catalog:path.includes('export')?fx.export:fx.summary};}};
const ctx=vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),ctx);const evaluate=s=>vm.runInContext(s,ctx);
const tick=()=>new Promise(r=>setTimeout(r,10));const checks=[];const check=(name,ok)=>{checks.push([name,ok]);if(!ok)throw new Error(name);};
(async()=>{await tick();check('default has a clear start action',el('content').innerHTML.includes('Commencer à jouer'));
check('default hides technical scores and model names',!/(ROC-AUC|Brier|GRU|JSON|DKT)/.test(el('content').innerHTML));
await evaluate("create('local')");check('local consent cannot be bypassed',writes.length===0&&el('error').textContent.includes('Cochez'));
await evaluate(`start(${JSON.stringify(fx.catalog.exercises[0].id)})`);check('first practice creates a labelled demo profile',writes[0].body.mode==='demo'&&evaluate('m.profile.mode')==='demo');
check('exercise displays real instructions without audio claim',el('content').innerHTML.includes('Pas d’écoute automatique'));
evaluate("m.stage='rating';render()");check('ratings use ordinary music language',el('content').innerHTML.includes('À retravailler')&&el('content').innerHTML.includes('À l’aise'));
busyPost=true;const pendingSave=evaluate('save()');await tick();check('save disables navigation',evaluate('m.busy')&&nav.every(n=>n.disabled));evaluate("setPage('progress')");check('cannot leave while save is running',evaluate('m.page')==='practice');resolvePost();await pendingSave;busyPost=false;
check('successful acknowledgment clears retry payload',evaluate('m.pending')===null&&evaluate('m.stage')==='feedback');
check('feedback cannot present one attempt as proven progress',el('content').innerHTML.includes('Une séance ne suffit pas'));
check('coverage explains a skill with zero observations',evaluate(`practiceReason({policy:'coverage',exercise_id:${JSON.stringify(fx.catalog.exercises[2].id)},evidence:[]})`).includes('0 évaluation'));
evaluate("m.stage='rating';m.pending=null;render()");failFirst=true;await evaluate('save()');const retained=evaluate('JSON.stringify(m.pending)');check('network failure preserves idempotent attempt',retained!=='null');
check('pending response is protected from editing',el('assessment-source').disabled);await evaluate('save()');const sent=writes.filter(w=>w.path==='/api/practice/sessions');check('retry sends identical payload',JSON.stringify(sent.at(-1).body)===JSON.stringify(sent.at(-2).body));
evaluate("setPage('progress')");check('progress distinguishes observations from mastery',el('content').innerHTML.includes('pas un score de maîtrise prédit'));
const harmful=evaluate("esc('<script>alert(1)</script>')");check('learner content is escaped',!harmful.includes('<script>'));
for(const status of [422,409]){rejectionStatus=status;evaluate("m.page='practice';m.stage='rating';render()");await evaluate('save()');check(`definitive ${status} releases pending draft and controls`,evaluate('m.pending')===null&&!el('assessment-source').disabled);}rejectionStatus=null;
missingProfile=true;storage.set('declic-practice-profile',JSON.stringify({...fx.profile,student_id:'missing-profile'}));await evaluate('init()');check('missing saved profile offers recovery',el('content').innerHTML.includes('Ouvrir un nouveau carnet'));
el('new-notebook').onclick();check('recovery preserves old reference and allows a new notebook',evaluate('m.profile')===null&&storage.has('declic-practice-unavailable-profile')&&!storage.has('declic-practice-profile')&&el('content').innerHTML.includes('Commencer à jouer'));
console.log(`${checks.length}/${checks.length} practice checks passed`);})().catch(e=>{console.error(e);process.exitCode=1;});
