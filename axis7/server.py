"""Local single-user demonstration API. Not a production student record service."""
import hashlib,json,logging,math,sqlite3,threading
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from pathlib import Path
from typing import Literal
import numpy as np
from fastapi import FastAPI,HTTPException,Query
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from .data import ROOT
from .schema import Attempt,to_record,MUSIC_SKILLS
from .inference import TwinEngine,uses_items
from .contracts import AttemptV2,resolve_event,registry
from .storage import append_event,EventConflict
from .recommendations import EXERCISES
from .responses import ForecastV2

log=logging.getLogger('axis7.api');app=FastAPI(title='DÉCLIC Axis 7',version='4.0.0')
engines={};lock=threading.RLock();DB=ROOT/'runtime/events.sqlite'

def engine(domain):
    with lock:return _engine_locked(domain)

def _engine_locked(domain):
    if domain not in ('music-mock','forget-se'):raise HTTPException(404,'Unknown domain')
    if domain not in engines:
        try:engines[domain]=TwinEngine(domain)
        except FileNotFoundError as e:raise HTTPException(503,str(e)) from e
    e=engines[domain]
    index=ROOT/'artifacts/v2/index.json'
    if index.exists():
        stamp=index.stat().st_mtime_ns
        if getattr(e,'research_stamp',None)!=stamp:
            from .models_v2 import ResearchPredictor
            manifest=json.loads(index.read_text(encoding='utf-8'))
            extras=[]
            for rid in [r for r in e.predictors if r.startswith('v2:')]:del e.predictors[rid]
            for entry in manifest.get('serving',[]):
                if entry['domain']!=domain:continue
                directory=(ROOT/entry['directory']).resolve()
                if not directory.is_relative_to((ROOT/'artifacts/v2').resolve()):
                    raise HTTPException(503,'Research checkpoint outside the versioned registry')
                rid='v2:'+entry['id'];e.predictors[rid]=ResearchPredictor(directory,entry['run_id'])
                extras.append({'id':rid,'name':entry['name'],'version':'v2','seed':entry['seed']})
            defaults=manifest.get('serving_defaults',{}).get(domain,{})
            match=lambda selected:next((x['id'] for x in extras if x['id'].endswith(':'+str(selected))),None)
            e.v2_selected_overall=match(defaults.get('overall'))
            if match(defaults.get('neural')):e.default=match(defaults['neural'])
            e.v2_models=extras;e.research_stamp=stamp
    return e

@contextmanager
def connection():
    DB.parent.mkdir(exist_ok=True);c=sqlite3.connect(DB)
    try:
        c.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, student TEXT, data TEXT)')
        with c:yield c
    finally:c.close()

def _json_safe(value):
    # Echoed input can contain NaN/Infinity, which strict JSON cannot encode.
    if isinstance(value,float) and not math.isfinite(value):return str(value)
    if isinstance(value,dict):return {k:_json_safe(v) for k,v in value.items()}
    if isinstance(value,list):return [_json_safe(v) for v in value]
    return value

@app.exception_handler(RequestValidationError)
async def invalid_request(request,exc:RequestValidationError):
    if request.url.path.startswith('/api/v6/o08'):
        return JSONResponse(status_code=422,content={'detail':[{'loc':e['loc'],'type':e['type'],
            'msg':'Invalid O08 field'} for e in exc.errors()]})
    return JSONResponse(status_code=422,content={'detail':_json_safe(jsonable_encoder(exc.errors()))})

def history(e,student,allow_new=False):
    base=e.learners.get(student)
    with connection() as c:extra=[json.loads(v[0]) for v in c.execute('SELECT data FROM events WHERE student=?',(student,))]
    if base is None and not (e.domain=='music-mock' and (extra or allow_new)):raise HTTPException(404,'Learner not found')
    return (base or [])+sorted(extra,key=lambda r:r['order']) if e.domain=='music-mock' else base

@app.get('/api/health')
def health():return {'status':'ok','domains':['music-mock','forget-se']}

@app.get('/api/learners')
def learners(domain:str='music-mock'):
    e=engine(domain)
    profiles=dict(e.learners)
    if domain=='music-mock':
        with connection() as c:
            for (u,) in c.execute('SELECT DISTINCT student FROM events'):
                profiles[u]=history(e,u)
    return {'metadata':e.meta,'models':[{'id':r['id'],'name':r['name'],'version':'v1'} for r in e.results['runs']]+getattr(e,'v2_models',[]),
        'default_model':e.default,'learners':[{'id':u,'label':(f"Profil simulé {i+1:02}" if u in e.learners else f"Profil intégré {i+1:02}") if domain=='music-mock' else f"Apprenant SE {i+1:02}",
            'groups':len(v),'provenance':sorted({r['provenance'] for r in v})} for i,(u,v) in enumerate(sorted(profiles.items()))]}

@app.get('/api/twin/{student}')
def twin(student:str,domain:str='music-mock',position:int|None=None,model_id:str|None=None,policy:str='balanced'):
    e=engine(domain)
    with lock:
        rows=history(e,student)
        try:return e.snapshot(student,rows,position,model_id,policy)
        except ValueError as err:raise HTTPException(422,str(err)) from err

@app.get('/api/experiments')
def experiments(domain:str='forget-se'):return engine(domain).results

class Simulate(BaseModel):
    student_id:str
    skill_id:str
    scenario:str=Field(pattern='^(mixed|success|difficulty)$',default='mixed')
    model_id:str|None=None
    policy:Literal['balanced','weakest']='balanced'

def known_attempt_ids(e):
    # Attempt IDs are global: a repeated ID under another learner would otherwise fail later as a raw SQLite error.
    with connection() as c:stored={v[0] for v in c.execute('SELECT id FROM events')}
    return stored|{r['id'] for rows in e.learners.values() for r in rows}

def insert_attempt(a,idempotent=False):
    e=engine('music-mock');rows=history(e,a.student_id,allow_new=True)
    record=resolve_event(a,e.meta['skills'])
    if a.instrument not in ('piano','piano-provisional'):raise ValueError('This provisional demo is scoped to piano only')
    if not idempotent and a.attempt_id in known_attempt_ids(e):
        raise ValueError('attempt_id already exists; use a unique identifier')
    fixture_ids={r['id'] for v in e.learners.values() for r in v}
    return append_event(DB,record,e.learners.get(a.student_id,[]),fixture_ids)

def acknowledge(a,idempotent=False,model_id=None,policy='balanced'):
    if a.provenance=='public':raise HTTPException(422,'Do not mix benchmark observations into the music stream')
    with lock:
        e=engine('music-mock')
        if model_id is not None and model_id not in e.predictors:raise HTTPException(422,'Unknown saved model')
        try:record,replayed=insert_attempt(a,idempotent)
        except EventConflict as err:raise HTTPException(409,str(err)) from err
        except (ValueError,sqlite3.IntegrityError) as err:raise HTTPException(422,str(err)) from err
        result={'status':'accepted','attempt_id':a.attempt_id,'idempotent_replay':replayed,
            'record':record,'warning':'Synthetic-trained model; musical transfer remains unvalidated.',
            'eligible_observations':sum(o.get('eligible',False) for o in record['obs']),
            'forecast_status':'ready','twin':None}
        try:
            result['twin']=e.snapshot(a.student_id,history(e,a.student_id),model_id=model_id,policy=policy)
        except Exception:
            log.exception('forecast_failed_after_acceptance attempt=%s',a.attempt_id)
            result.update(forecast_status='unavailable',forecast_error={'code':'INFERENCE_UNAVAILABLE','retryable':True})
        log.info(json.dumps({'event':'event_accepted','attempt_id':a.attempt_id,
            'idempotent_replay':replayed,'eligible_observations':result['eligible_observations'],
            'forecast_status':result['forecast_status']},sort_keys=True))
        return result

@app.post('/api/attempts')
def ingest(a:Attempt,model_id:str|None=None,policy:Literal['balanced','weakest']='balanced'):
    return acknowledge(a,model_id=model_id,policy=policy)

@app.post('/api/v2/events')
def ingest_v2(a:AttemptV2,model_id:str|None=None,policy:Literal['balanced','weakest']='balanced'):
    return acknowledge(a,idempotent=True,model_id=model_id,policy=policy)

@app.get('/api/v2/registry')
def contract_registry():return registry()

@app.get('/api/v2/exercises')
def exercise_registry():return {'exercises':EXERCISES,'teacher_approved':False,'prerequisites':[]}

@app.get('/api/v2/schemas')
def schemas():return {'attempt_v1':Attempt.model_json_schema(),'attempt_v2':AttemptV2.model_json_schema(),'forecast_v2':ForecastV2.model_json_schema()}

def item_supported(predictor,exercise_id):
    if not exercise_id or not uses_items(predictor):return None
    from .models_v2 import item_key
    return item_key({'exercise':exercise_id}) in predictor.items.state['vocabulary']

@app.get('/api/v2/forecast/{student}',response_model=ForecastV2)
def forecast(student:str,domain:str='music-mock',model_id:str|None=None,exercise_id:str|None=None):
    e=engine(domain);rid=model_id or e.default
    if rid not in e.predictors:raise HTTPException(422,'Unknown model identifier')
    with lock:
        rows=history(e,student);predictor=e.predictors[rid]
        if rid.startswith('v2:'):probabilities=predictor.probabilities(rows,exercise_id=exercise_id)[-1]
        else:probabilities=predictor.probabilities(rows)[-1]
    return {'response_version':'2.0','student_id':student,'domain':domain,'model_id':rid,
        'implementation_version':getattr(predictor,'serving_implementation_version',predictor.config.get('implementation_version','legacy-v1')),
        'training_implementation_version':predictor.config.get('implementation_version','legacy-v1'),
        'model_profile':'provisional-piano-v1' if domain=='music-mock' else 'forget-se-full-credit-v1',
        'exercise_id':exercise_id,'conditioning':'exercise' if exercise_id and uses_items(predictor) else 'generic_skill',
        'item_supported':item_supported(predictor,exercise_id),
        'training_provenance':'synthetic' if domain=='music-mock' else 'public_software_engineering',
        'evaluated_scope':'observed_skill_given_attempted_exercise' if uses_items(predictor) else 'skill_only_forecast',
        'query_validity':('exercise_skill_applicability_not_validated' if exercise_id else 'generic_unknown_item_extrapolation') if uses_items(predictor) else 'skill_only_forecast',
        'probabilities':dict(zip(e.meta['skills'],map(float,probabilities))),
        'warning':'Correctness is not mastery or learning benefit. V2 benchmarks evaluate observed skills with known attempted exercises; generic UNK forecasts and unobserved exercise-skill combinations are extrapolations.'}

@app.get('/api/research')
def research():
    index=ROOT/'artifacts/v2/index.json'
    if not index.exists():return {'status':'not_run','historical_results_preserved':True}
    pointer=json.loads(index.read_text(encoding='utf-8'))
    experiment=pointer.get('experiment_id',pointer.get('latest'))
    if not experiment or Path(experiment).name!=experiment:raise HTTPException(503,'Invalid research manifest')
    summary=ROOT/'artifacts/v2'/experiment/'summary.json'
    if not summary.exists():return {'status':'running','manifest':pointer}
    return {'status':'complete','manifest':pointer,'summary':json.loads(summary.read_text(encoding='utf-8'))}

@app.post('/api/simulate')
def simulate(s:Simulate):
    e=engine('music-mock')
    if s.skill_id not in MUSIC_SKILLS:raise HTTPException(422,'Unmapped provisional skill')
    if s.model_id is not None and s.model_id not in e.predictors:raise HTTPException(422,'Unknown saved model')
    with lock:
        rows=history(e,s.student_id);n=len(rows)
        seed=int(hashlib.sha256(f'{s.student_id}:{n}:{s.skill_id}:{s.scenario}'.encode()).hexdigest()[:8],16)
        rng=np.random.default_rng(seed);time=datetime.fromisoformat(rows[-1]['timestamp'])+timedelta(days=3)
        # Independent mock producer. Outcomes are NOT generated from KT predictions.
        values=[1]*4 if s.scenario=='success' else [0]*4 if s.scenario=='difficulty' else [int(v) for v in rng.random(4)<.65]
        sid=f"simulation:{s.student_id}:{n}";aid=f'{sid}:attempt'
        obs=[{'skill_id':s.skill_id,'outcome':v,'score':float(v),'source_confidence':1,
              'error_types':[] if v else ['mock_outcome_failure'],'evidence_id':f'{aid}:note:{i}'} for i,v in enumerate(values)]
        a=Attempt.model_validate({'attempt_id':aid,'student_id':s.student_id,'session_id':sid,'exercise_id':f'mock-focus-{s.skill_id}',
            'instrument':'piano-provisional','timestamp':time.isoformat(),'provenance':'synthetic','rubric_version':'provisional-mock-v1','observations':obs,
            'upstream_versions':{'producer':'independent-mock-v1'}})
        return acknowledge(a,model_id=s.model_id,policy=s.policy)

@app.post('/api/reset/{student}')
def reset(student:str):
    e=engine('music-mock');history(e,student)
    with lock,connection() as c:c.execute('DELETE FROM events WHERE student=?',(student,))
    return {'status':'reset','student':student}

@app.get('/api/export/{student}')
def export(student:str):
    e=engine('music-mock');rows=history(e,student)
    return {'warning':'Synthetic-trained forecast model; record provenance is preserved independently.',
            'provenance_counts':{p:sum(r['provenance']==p for r in rows) for p in {r['provenance'] for r in rows}},
            'observations':rows}

@app.get('/')
def index():return FileResponse(ROOT/'web/index.html',headers={'Cache-Control':'no-store'})

@app.get('/api/figures/{domain}/{name}')
def figure(domain:str,name:str):
    engine(domain)
    if name not in ('learning_curves.png','calibration.png','per_skill.png'):raise HTTPException(404,'Figure not found')
    return FileResponse(ROOT/'artifacts'/domain/name)

from .practice import router as _practice_router
from .team_v3 import router as _team_v3_router
from .forecast_v4 import router as _forecast_v4_router
app.include_router(_practice_router)
app.include_router(_team_v3_router)
app.include_router(_forecast_v4_router)
from .musical_api import router as _musical_router
app.include_router(_musical_router)
from .prospective import router as _prospective_router
from .o08_demo import router as _o08_demo_router
app.include_router(_prospective_router)
app.include_router(_o08_demo_router)
from .living_learner import router as _living_router
app.include_router(_living_router)
from .readiness import router as _readiness_router
app.include_router(_readiness_router)
from .o08_security import O08BodyLimit
app.add_middleware(O08BodyLimit)

app.mount('/web',StaticFiles(directory=ROOT/'web'),name='web')
