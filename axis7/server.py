"""Local single-user demonstration API. Not a production student record service."""
import hashlib,json,logging,math,sqlite3,threading
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from pathlib import Path
import numpy as np
from fastapi import FastAPI,HTTPException,Query
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from .data import ROOT
from .schema import Attempt,to_record,MUSIC_SKILLS
from .inference import TwinEngine

log=logging.getLogger('axis7.api');app=FastAPI(title='DÉCLIC Axis 7',version='0.1.0')
engines={};lock=threading.RLock();DB=ROOT/'runtime/events.sqlite'

def engine(domain):
    if domain not in ('music-mock','forget-se'):raise HTTPException(404,'Unknown domain')
    if domain not in engines:
        try:engines[domain]=TwinEngine(domain)
        except FileNotFoundError as e:raise HTTPException(503,str(e)) from e
    return engines[domain]

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
    return {'metadata':e.meta,'models':[{'id':r['id'],'name':r['name']} for r in e.results['runs']],
        'default_model':e.default,'learners':[{'id':u,'label':(f"Profil simulé {i+1:02}" if u in e.learners else f"Profil intégré {i+1:02}") if domain=='music-mock' else f"Apprenant SE {i+1:02}",
            'groups':len(v),'provenance':sorted({r['provenance'] for r in v})} for i,(u,v) in enumerate(sorted(profiles.items()))]}

@app.get('/api/twin/{student}')
def twin(student:str,domain:str='music-mock',position:int|None=None,model_id:str|None=None):
    e=engine(domain)
    with lock:
        rows=history(e,student)
        try:return e.snapshot(student,rows,position,model_id)
        except ValueError as err:raise HTTPException(422,str(err)) from err

@app.get('/api/experiments')
def experiments(domain:str='forget-se'):return engine(domain).results

class Simulate(BaseModel):
    student_id:str
    skill_id:str
    scenario:str=Field(pattern='^(mixed|success|difficulty)$',default='mixed')
    model_id:str|None=None

def known_attempt_ids(e):
    # Attempt IDs are global: a repeated ID under another learner would otherwise fail later as a raw SQLite error.
    with connection() as c:stored={v[0] for v in c.execute('SELECT id FROM events')}
    return stored|{r['id'] for rows in e.learners.values() for r in rows}

def insert_attempt(a):
    e=engine('music-mock');rows=history(e,a.student_id,allow_new=True)
    record=to_record(a,e.meta['skills'])
    if a.instrument not in ('piano','piano-provisional'):raise ValueError('This provisional demo is scoped to piano only')
    if a.attempt_id in known_attempt_ids(e):raise ValueError('attempt_id already exists; use a unique identifier')
    if rows and record['order']<=rows[-1]['order']:raise ValueError('Timestamp must be strictly later; combine simultaneous observations into one attempt')
    # A real project observation does not validate the synthetic-trained model.
    with connection() as c:c.execute('INSERT INTO events(id,student,data) VALUES(?,?,?)',(a.attempt_id,a.student_id,json.dumps(record,ensure_ascii=False)))
    return record

@app.post('/api/attempts')
def ingest(a:Attempt):
    if a.provenance=='public':raise HTTPException(422,'Do not mix benchmark observations into the music stream')
    with lock:
        try:record=insert_attempt(a)
        except (ValueError,sqlite3.IntegrityError) as err:raise HTTPException(422,str(err)) from err
        e=engine('music-mock');return {'record':record,'warning':'Model trained on synthetic music only; musical transfer unvalidated.',
            'twin':e.snapshot(a.student_id,history(e,a.student_id))}

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
        try:record=insert_attempt(a)
        except (ValueError,sqlite3.IntegrityError) as err:raise HTTPException(422,str(err)) from err
        updated=history(e,s.student_id)
        return {'record':record,'twin':e.snapshot(s.student_id,updated,model_id=s.model_id)}

@app.post('/api/reset/{student}')
def reset(student:str):
    e=engine('music-mock');history(e,student)
    with lock,connection() as c:c.execute('DELETE FROM events WHERE student=?',(student,))
    return {'status':'reset','student':student}

@app.get('/api/export/{student}')
def export(student:str):
    e=engine('music-mock');return {'warning':'synthetic/provisional demo stream','observations':history(e,student)}

@app.get('/')
def index():return FileResponse(ROOT/'web/index.html')

@app.get('/api/figures/{domain}/{name}')
def figure(domain:str,name:str):
    engine(domain)
    if name not in ('learning_curves.png','calibration.png','per_skill.png'):raise HTTPException(404,'Figure not found')
    return FileResponse(ROOT/'artifacts'/domain/name)

app.mount('/web',StaticFiles(directory=ROOT/'web'),name='web')
