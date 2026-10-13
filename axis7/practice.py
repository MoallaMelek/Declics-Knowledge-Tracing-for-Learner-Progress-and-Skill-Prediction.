"""Piano practice-collection notebook: pseudonymous local/demo notebook, provisional 3-point
ordinal rubric, teacher-reviewable but NOT teacher-approved. This module never feeds manual or
teacher-recorded ratings into the synthetic-trained knowledge-tracing models in inference.py;
model_update_eligible is always false here. No research enrollment, guardian-consent claim, or
raw media is accepted. 'duration' is a deliberately separate provisional skill id from the
model's own 'timing' concept in schema.py::MUSIC_SKILLS -- it is not a silent alias.
"""
import json,sqlite3,uuid
from collections import Counter
from datetime import datetime,timezone
from typing import Literal
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,ConfigDict,Field,StrictBool,field_validator,model_validator
from .schema import UnitFloat
from .storage import fingerprint

router=APIRouter()

INSTRUMENT='piano'
RUBRIC_VERSION='piano-pilot-v1'
PRIVACY_NOTICE_VERSION='local-pilot-v1'
RATING_VALUES={'needs_work','developing','comfortable','not_assessed'}
LEVEL_SCORE={'needs_work':0,'developing':1,'comfortable':2}
MIN_EVIDENCE=3
RECENT_WINDOW=5

PIANO_SKILLS=[
    {'id':'pitch','label':'Hauteur / justesse',
     'prompt':"Jouer une courte phrase de cinq notes consécutives en position des cinq doigts.",
     'levels':{'needs_work':"Plusieurs notes sont nettement fausses ou hors position.",
               'developing':"La plupart des notes sont correctes, avec une ou deux erreurs isolées.",
               'comfortable':"Toutes les notes sont jouées dans la hauteur attendue."}},
    {'id':'rhythm','label':'Rythme',
     'prompt':"Jouer une suite de noires régulières a un tempo stable choisi par l'élève.",
     'levels':{'needs_work':"Le tempo est instable ou les valeurs ne sont pas respectees.",
               'developing':"Le tempo est globalement tenu, avec quelques écarts.",
               'comfortable':"Les noires restent régulières du debut a la fin."}},
    {'id':'duration','label':'Durée des notes tenues',
     'prompt':"Tenir des notes longues pour toute leur valeur, sans les relâcher trop tôt.",
     'levels':{'needs_work':"Les notes sont relâchées bien avant la fin de leur valeur.",
               'developing':"La tenue est approximative mais perceptible.",
               'comfortable':"Chaque note est tenue pour sa valeur complète."}},
    {'id':'articulation','label':'Articulation (lié / détaché)',
     'prompt':"Jouer la même phrase une fois liée (legato) puis une fois détachée (staccato).",
     'levels':{'needs_work':"Les deux styles ne sont pas distinguables a l'ecoute.",
               'developing':"La difference entre lié et détaché est audible mais irrégulière.",
               'comfortable':"Le lié et le détaché sont nettement et constamment distincts."}},
    {'id':'fingering','label':'Doigté (position cinq doigts)',
     'prompt':"Monter puis descendre la position des cinq doigts avec le doigté 1-2-3-4-5.",
     'levels':{'needs_work':"Plusieurs doigts se substituent les uns aux autres.",
               'developing':"Le doigté est globalement respecté, avec une ou deux substitutions.",
               'comfortable':"Chaque doigt reste sur son role du debut a la fin."}},
    {'id':'score_reading','label':'Lecture de partition (court motif)',
     'prompt':"Lire et jouer un court motif de quatre a six notes sur une partition simplifiée.",
     'levels':{'needs_work':"La plupart des notes ne correspondent pas a la partition.",
               'developing':"La majorité des notes correspondent, avec des hésitations.",
               'comfortable':"Le motif est joué dans l'ordre exact de la partition."}},
]
SKILL_IDS={s['id'] for s in PIANO_SKILLS}
SKILL_LABEL={s['id']:s['label'] for s in PIANO_SKILLS}

PIANO_EXERCISES=[
    {'id':'ex-pitch-five-note','title':'Phrase de cinq notes',
     'description':"Courte phrase mélodique sur cinq notes consécutives en position des cinq doigts.",
     'instructions':["Placer la main en position de cinq doigts.",
                     "Jouer les cinq notes en montant puis en descendant, une fois lentement.",
                     "Vérifier que chaque note correspond a la touche visee avant de recommencer."],
     'skill_ids':['pitch'],'difficulty':'introductory','duration_minutes':3,
     'provenance':'demonstration_catalog','teacher_approved':False,'prerequisites':[]},
    {'id':'ex-rhythm-steady-quarters','title':'Noires régulières',
     'description':"Suite de huit noires jouées a un tempo stable choisi par l'élève.",
     'instructions':["Choisir un tempo confortable et le garder constant.",
                     "Jouer huit noires sur une seule touche.",
                     "Compter a voix haute ou utiliser un metronome si disponible."],
     'skill_ids':['rhythm'],'difficulty':'introductory','duration_minutes':2,
     'provenance':'demonstration_catalog','teacher_approved':False,'prerequisites':[]},
    {'id':'ex-duration-sustained-notes','title':'Notes tenues',
     'description':"Quatre notes longues tenues pour toute leur durée.",
     'instructions':["Jouer une note et compter mentalement quatre temps avant de la relâcher.",
                     "Repeter sur quatre notes differentes.",
                     "Eviter de relâcher la touche avant la fin du comptage."],
     'skill_ids':['duration'],'difficulty':'introductory','duration_minutes':2,
     'provenance':'demonstration_catalog','teacher_approved':False,'prerequisites':[]},
    {'id':'ex-articulation-connected-detached','title':'Lié et détaché',
     'description':"Même phrase jouée une fois liée puis une fois détachée.",
     'instructions':["Jouer la phrase de cinq notes de facon liée, sans coupure de son entre les notes.",
                     "Jouer la même phrase de facon détachée, avec un silence net entre chaque note.",
                     "Comparer les deux versions a l'oreille."],
     'skill_ids':['articulation'],'difficulty':'introductory','duration_minutes':3,
     'provenance':'demonstration_catalog','teacher_approved':False,'prerequisites':[]},
    {'id':'ex-fingering-five-finger-pattern','title':'Doigté cinq doigts',
     'description':"Montée et descente sur la position des cinq doigts avec le doigté 1-2-3-4-5.",
     'instructions':["Placer chaque doigt sur sa touche de depart.",
                     "Monter 1-2-3-4-5 puis redescendre 5-4-3-2-1.",
                     "Vérifier qu'aucun doigt ne se substitue a un autre."],
     'skill_ids':['fingering'],'difficulty':'introductory','duration_minutes':3,
     'provenance':'demonstration_catalog','teacher_approved':False,'prerequisites':[]},
    {'id':'ex-score-reading-short-motif','title':"Lecture d'un court motif",
     'description':"Lecture a vue d'un motif de quatre a six notes sur partition simplifiée.",
     'instructions':["Observer le motif avant de jouer.",
                     "Identifier chaque note sur la portee avant de la jouer.",
                     "Jouer le motif une fois lentement, en suivant la partition."],
     'skill_ids':['score_reading'],'difficulty':'introductory','duration_minutes':4,
     'provenance':'demonstration_catalog','teacher_approved':False,'prerequisites':[]},
]
EXERCISE_BY_ID={e['id']:e for e in PIANO_EXERCISES}

class ProfileRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    mode:Literal['demo','local']
    local_storage_consent:StrictBool=False

class RatingIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    skill_id:str=Field(min_length=1,max_length=80)
    rating:Literal['needs_work','developing','comfortable','not_assessed']

class SessionRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    attempt_id:str=Field(min_length=1,max_length=120)
    student_id:str=Field(min_length=1,max_length=100)
    exercise_id:str=Field(min_length=1,max_length=100)
    timestamp:datetime
    source:Literal['self','teacher']
    rubric_version:str=Field(min_length=1,max_length=80)
    ratings:list[RatingIn]=Field(min_length=1,max_length=20)
    confidence:UnitFloat|None=None

    @field_validator('timestamp',mode='before')
    @classmethod
    def canonical_timestamp(cls,v):
        if not isinstance(v,(str,datetime)):raise ValueError('timestamp must be an ISO 8601 string with timezone')
        return v

    @field_validator('timestamp')
    @classmethod
    def tz(cls,v):
        if v.tzinfo is None or v.utcoffset() is None:raise ValueError('timestamp requires a timezone')
        return v

    @model_validator(mode='after')
    def ratings_shape(self):
        ids=[r.skill_id for r in self.ratings]
        if len(ids)!=len(set(ids)):raise ValueError('duplicate skill_id in ratings')
        if all(r.rating=='not_assessed' for r in self.ratings):
            raise ValueError('at least one measured rating is required; ratings cannot all be not_assessed')
        return self

def _open():
    from . import server
    server.DB.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(server.DB,timeout=10)
    conn.execute('CREATE TABLE IF NOT EXISTS practice_profiles '
                 '(student_id TEXT PRIMARY KEY, mode TEXT, instrument TEXT, consent INTEGER, '
                 'privacy_notice_version TEXT, created_at TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS practice_sessions '
                 '(attempt_id TEXT PRIMARY KEY, student_id TEXT, exercise_id TEXT, timestamp TEXT, '
                 'order_ts REAL, source TEXT, rubric_version TEXT, ratings TEXT, confidence REAL, '
                 'provenance TEXT, attempt_sequence INTEGER, request_fingerprint TEXT, created_at TEXT)')
    conn.execute('CREATE INDEX IF NOT EXISTS practice_sessions_student ON practice_sessions(student_id)')
    return conn

def _profile(conn,student_id):
    row=conn.execute('SELECT student_id,mode,instrument,consent,privacy_notice_version,created_at '
                      'FROM practice_profiles WHERE student_id=?',(student_id,)).fetchone()
    if not row:raise HTTPException(404,'Unknown practice profile')
    keys=('student_id','mode','instrument','consent','privacy_notice_version','created_at')
    return dict(zip(keys,row))

def _load_sessions(conn,student_id):
    rows=conn.execute('SELECT attempt_id,exercise_id,timestamp,source,ratings,confidence,provenance,attempt_sequence '
                       'FROM practice_sessions WHERE student_id=? ORDER BY attempt_sequence ASC',(student_id,)).fetchall()
    sessions=[]
    for attempt_id,exercise_id,ts,source,ratings_json,confidence,provenance,sequence in rows:
        exercise=EXERCISE_BY_ID.get(exercise_id)
        ratings=json.loads(ratings_json)
        sessions.append({'attempt_id':attempt_id,'exercise_id':exercise_id,
            'exercise_title':exercise['title'] if exercise else exercise_id,
            'timestamp':ts,'attempt_sequence':sequence,'source':source,'provenance':provenance,
            'confidence':confidence,
            'ratings':[{'skill_id':r['skill_id'],'label':SKILL_LABEL.get(r['skill_id'],r['skill_id']),
                        'rating':r['rating']} for r in ratings],
            'model_update_eligible':False})
    return sessions

def _skill_touches(sessions,skill_id):
    touches=[]
    for s in sessions:
        for r in s['ratings']:
            if r['skill_id']==skill_id and r['rating']!='not_assessed':
                touches.append({'attempt_id':s['attempt_id'],'exercise_id':s['exercise_id'],
                                 'rating':r['rating'],'sequence':s['attempt_sequence'],
                                 'source':s['source']})
    return touches

def _skill_status(skill_id,touches):
    observations=len(touches);recent=touches[-RECENT_WINDOW:]
    recent_comfortable=sum(t['rating']=='comfortable' for t in recent)
    recent_needs_work=sum(t['rating']=='needs_work' for t in recent)
    if observations<MIN_EVIDENCE:
        return {'status':'insufficient_evidence',
            'explanation':f'{observations} evaluated attempt(s) recorded so far; at least {MIN_EVIDENCE} are needed before describing a trend.',
            'observations':observations,'recent_count':len(recent),
            'recent_comfortable':recent_comfortable,'recent_needs_work':recent_needs_work}
    # A change from self-report to teacher rating must not become improvement.
    comparable=Counter((t['exercise_id'],t['source']) for t in touches)
    (best_exercise,best_source),count=comparable.most_common(1)[0]
    same_exercise=[t for t in touches if (t['exercise_id'],t['source'])==(best_exercise,best_source)]
    recent_difficulty=len({t['attempt_id'] for t in touches[-MIN_EVIDENCE:] if t['rating']=='needs_work'})>=2
    if count>=2*MIN_EVIDENCE:
        last=[LEVEL_SCORE[t['rating']] for t in same_exercise[-MIN_EVIDENCE:]]
        prior=[LEVEL_SCORE[t['rating']] for t in same_exercise[-2*MIN_EVIDENCE:-MIN_EVIDENCE]]
        improved=sum(last)/len(last)>sum(prior)/len(prior)+1/3
    else:
        improved=False
    if improved:
        status='improving'
        explanation=(f'The last {MIN_EVIDENCE} ratings on "{best_exercise}" average higher than the '
                     f'{MIN_EVIDENCE} before them.')
    elif recent_difficulty:
        status='recent_difficulty'
        explanation=f'At least 2 of the last {MIN_EVIDENCE} recorded attempts were rated "needs_work".'
    else:
        status='steady'
        explanation=(f'{recent_comfortable} of the last {len(recent)} recorded attempts were rated "comfortable"; '
                     'not enough same-exercise repeats yet to describe an improving trend.' if count<2*MIN_EVIDENCE
                     else f'{recent_comfortable} of the last {len(recent)} recorded attempts were rated "comfortable".')
    return {'status':status,'explanation':explanation,'observations':observations,'recent_count':len(recent),
        'recent_comfortable':recent_comfortable,'recent_needs_work':recent_needs_work}

def _recommend(skills,sessions,policy):
    total_measured=sum(s['observations'] for s in skills)
    if total_measured<MIN_EVIDENCE:
        first=PIANO_EXERCISES[0]
        return {'exercise_id':first['id'],'title':first['title'],
            'reason':'Not enough recorded attempts yet; start with a short assessment on the first catalogue exercise.',
            'evidence':[],'policy':policy,'used_model_predictions':False,
            'uncertainty':'No ordinal evidence has been recorded yet for this learner; this is a default starting point, not a ranked choice.',
            'alternatives':[],'teacher_approved':False}
    eligible=skills if policy=='coverage' else ([s for s in skills if s['observations']>=MIN_EVIDENCE] or skills)
    def key(s):
        if policy=='coverage':return (-s['observations'],)
        weakness=s['recent_needs_work']-s['recent_comfortable']
        if policy=='weakest':return (weakness,-s['observations'])
        return (weakness,1 if s['status']=='recent_difficulty' else 0,-s['observations'])
    ranked=sorted(eligible,key=key,reverse=True)
    target=ranked[0]
    exercise=next((e for e in PIANO_EXERCISES if target['id'] in e['skill_ids']),PIANO_EXERCISES[0])
    touches=_skill_touches(sessions,target['id'])
    evidence=[{'attempt_id':t['attempt_id'],'skill_id':target['id'],'rating':t['rating']} for t in touches[-3:]]
    alternatives=[{'skill_id':s['id'],'label':s['label'],'status':s['status'],'observations':s['observations']}
                  for s in ranked[:3]]
    return {'exercise_id':exercise['id'],'title':exercise['title'],
        'reason':f'"{target["label"]}" shows {target["status"].replace("_"," ")} based on {target["observations"]} recorded attempt(s).',
        'evidence':evidence,'policy':policy,'used_model_predictions':False,
        'uncertainty':'Ordinal self/teacher ratings are a transparent heuristic, not a calibrated probability.',
        'alternatives':alternatives,'teacher_approved':False}

def build_summary(conn,student_id,policy):
    profile=_profile(conn,student_id)
    sessions=_load_sessions(conn,student_id)
    skills=[]
    for skill in PIANO_SKILLS:
        touches=_skill_touches(sessions,skill['id'])
        status=_skill_status(skill['id'],touches)
        skills.append({'id':skill['id'],'label':skill['label'],**status})
    recommendation=_recommend(skills,sessions,policy)
    return {'student_id':student_id,'mode':profile['mode'],'instrument':profile['instrument'],
        'session_count':len(sessions),'attempt_count':len(sessions),
        'latest':sessions[-1] if sessions else None,'sessions':sessions,'skills':skills,
        'recommendation':recommendation,
        'forecast':{'status':'unavailable','reason':'No validated model for this provisional local collection rubric.'},
        'rubric_version':RUBRIC_VERSION,'taxonomy_status':'provisional',
        'collection_status':'local_notebook_not_validated_dataset'}

@router.get('/api/practice/catalog')
def catalog():
    return {'instrument':INSTRUMENT,'teacher_approved':False,'rubric_version':RUBRIC_VERSION,
        'skills':PIANO_SKILLS,'exercises':PIANO_EXERCISES}

@router.post('/api/practice/profiles')
def create_profile(body:ProfileRequest):
    if body.mode=='local' and not body.local_storage_consent:
        raise HTTPException(422,'Local self-practice storage requires explicit consent (demo mode is exempt)')
    consent=True if body.mode=='demo' else body.local_storage_consent
    student_id=f'piano-{uuid.uuid4()}'
    conn=_open()
    try:
        conn.execute('INSERT INTO practice_profiles(student_id,mode,instrument,consent,privacy_notice_version,created_at) '
                     'VALUES(?,?,?,?,?,?)',(student_id,body.mode,INSTRUMENT,int(consent),PRIVACY_NOTICE_VERSION,
                     datetime.now(timezone.utc).isoformat()))
        conn.commit()
    finally:
        conn.close()
    return {'student_id':student_id,'mode':body.mode,'instrument':INSTRUMENT,
        'privacy_notice_version':PRIVACY_NOTICE_VERSION}

@router.post('/api/practice/sessions')
def create_session(body:SessionRequest):
    exercise=EXERCISE_BY_ID.get(body.exercise_id)
    if exercise is None:raise HTTPException(404,'Unknown exercise_id')
    if body.rubric_version!=RUBRIC_VERSION:raise HTTPException(422,'Unknown or unsupported rubric_version')
    unknown={r.skill_id for r in body.ratings}-SKILL_IDS
    if unknown:raise HTTPException(422,f'Unknown skill_id(s): {sorted(unknown)}')
    not_exercised={r.skill_id for r in body.ratings}-set(exercise['skill_ids'])
    if not_exercised:raise HTTPException(422,'Ratings must reference a skill practiced in this exercise')
    digest=fingerprint(body.model_dump(mode='json'))
    conn=_open()
    try:
        _profile(conn,body.student_id)
        conn.execute('BEGIN IMMEDIATE')
        existing=conn.execute('SELECT student_id,request_fingerprint FROM practice_sessions WHERE attempt_id=?',
                               (body.attempt_id,)).fetchone()
        if existing:
            conn.rollback()
            if existing[0]!=body.student_id:raise HTTPException(409,'attempt_id belongs to a different learner')
            if existing[1]!=digest:raise HTTPException(409,'attempt_id already exists with a different payload')
            return {'status':'accepted','idempotent_replay':True,'summary':build_summary(conn,body.student_id,'balanced')}
        prior=conn.execute('SELECT order_ts,attempt_sequence FROM practice_sessions WHERE student_id=? '
                            'ORDER BY attempt_sequence DESC LIMIT 1',(body.student_id,)).fetchone()
        order_ts=body.timestamp.timestamp()
        if prior and order_ts<=prior[0]:
            conn.rollback()
            raise HTTPException(422,"timestamp must be strictly later than this learner's previous session")
        sequence=(prior[1]+1) if prior else 1
        profile=_profile(conn,body.student_id)
        provenance='demo' if profile['mode']=='demo' else 'local_real'
        conn.execute('INSERT INTO practice_sessions(attempt_id,student_id,exercise_id,timestamp,order_ts,source,'
                     'rubric_version,ratings,confidence,provenance,attempt_sequence,request_fingerprint,created_at) '
                     'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                     (body.attempt_id,body.student_id,body.exercise_id,body.timestamp.isoformat(),order_ts,
                      body.source,body.rubric_version,json.dumps([r.model_dump() for r in body.ratings]),
                      body.confidence,provenance,sequence,digest,datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return {'status':'accepted','idempotent_replay':False,'summary':build_summary(conn,body.student_id,'balanced')}
    except HTTPException:
        raise
    except Exception:
        conn.rollback();raise
    finally:
        conn.close()

@router.get('/api/practice/summary/{student_id}')
def summary(student_id:str,policy:Literal['balanced','weakest','coverage']='balanced'):
    conn=_open()
    try:
        _profile(conn,student_id)
        return build_summary(conn,student_id,policy)
    finally:
        conn.close()

@router.get('/api/practice/export/{student_id}')
def export_student(student_id:str):
    conn=_open()
    try:
        profile=_profile(conn,student_id)
        sessions=_load_sessions(conn,student_id)
        by_source=Counter(s['source'] for s in sessions)
        skill_totals=Counter(r['skill_id'] for s in sessions for r in s['ratings'] if r['rating']!='not_assessed')
        rare=[s['id'] for s in PIANO_SKILLS if skill_totals.get(s['id'],0)<MIN_EVIDENCE]
        return {'schema_version':'practice-export-1.0',
            'profile':{'student_id':student_id,'mode':profile['mode'],'instrument':profile['instrument'],
                'consent':bool(profile['consent']),'privacy_notice_version':profile['privacy_notice_version']},
            'rubric':{'rubric_version':RUBRIC_VERSION,'instrument':INSTRUMENT,'skills':PIANO_SKILLS,
                'teacher_approved':False},
            'catalog':{'instrument':INSTRUMENT,'teacher_approved':False,'rubric_version':RUBRIC_VERSION,
                'skills':PIANO_SKILLS,'exercises':PIANO_EXERCISES},
            'sessions':sessions,
            'quality':{'session_count':len(sessions),'source_breakdown':dict(by_source),
                'rare_skills':rare,'rare_skill_threshold':MIN_EVIDENCE,'mode':profile['mode']},
            'training_ready':False,
            'limitations':['Provisional, teacher-unreviewed rubric and exercise catalogue.',
                'Ordinal 3-point ratings are not a calibrated probability or a validated psychometric score.',
                'No model was updated from these observations; model_update_eligible is always false.',
                'A single-learner notebook export is not a statistically representative pilot by itself.']}
    finally:
        conn.close()
