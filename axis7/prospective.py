"""Opt-in local O08 event collection and immutable prospective forecast ledger.

Administrative token API, not a multi-user identity provider. No private dataset
is imported here automatically. SQLite and token are local operational secrets.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator

from .data import ROOT

router = APIRouter(prefix='/api/v6/o08', tags=['local prospective collection'])
DB = ROOT/'runtime/prospective.sqlite'


def now():
    return datetime.now(timezone.utc)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Consent(Strict):
    learner_id: str = Field(pattern=r'^learner_[a-f0-9]{16}$')
    consent_version: str = Field(pattern=r'^[a-zA-Z0-9_.-]{1,40}$')
    granted: Literal[True]
    retention_days: int = Field(default=30, ge=1, le=365)


class Result(Strict):
    concept: int = Field(ge=0, le=1023)
    value: float = Field(ge=0, le=1, allow_inf_nan=False)
    evaluated_count: int = Field(default=1, ge=1, le=100000)


class PracticeEvent(Strict):
    schema_version: Literal['o08-practice-v1']
    event_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    learner_id: str = Field(pattern=r'^learner_[a-f0-9]{16}$')
    instrument: Literal['voice','ukulele','keyboard','piano','other']
    exercise_id: str = Field(pattern=r'^[a-zA-Z0-9_|.-]{1,1000}$')
    exercise_version: str = Field(pattern=r'^[a-zA-Z0-9_.-]{1,40}$')
    attempt_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    session_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    occurred_at: AwareDatetime
    available_at: AwareDatetime
    assessment_source: Literal['teacher_assessment','axis_adapter','dataset_import']
    producer_version: str = Field(pattern=r'^[a-zA-Z0-9_.-]{1,40}$')
    score_definition: Literal['singpad_note_binary','yousician_active_day_fraction','amme_scoretype7_block_mean','custom_unvalidated']
    scale: Literal['binary_notes','continuous_unit_interval']
    outcomes: list[Result] = Field(min_length=1, max_length=1024)
    evaluation_confidence: None = None
    provenance: Literal['real_observation','retrospective_dataset']

    @model_validator(mode='after')
    def coherence(self):
        if self.available_at < self.occurred_at: raise ValueError('Outcome cannot be available before attempt')
        if self.available_at > now(): raise ValueError('Future observed outcomes are forbidden')
        if len({o.concept for o in self.outcomes}) != len(self.outcomes): raise ValueError('Merge duplicate concepts explicitly')
        if self.score_definition == 'singpad_note_binary':
            if self.instrument != 'voice' or self.scale != 'binary_notes' or any(o.value not in (0.,1.) for o in self.outcomes):
                raise ValueError('SingPAD contract requires binary voice outcomes per concept')
        if self.score_definition in ('yousician_active_day_fraction','amme_scoretype7_block_mean'):
            expected = 'ukulele' if self.score_definition.startswith('yousician') else 'keyboard'
            if self.instrument != expected or self.scale != 'continuous_unit_interval' or len(self.outcomes)!=1 or self.outcomes[0].concept!=0 or self.outcomes[0].evaluated_count!=1:
                raise ValueError('Continuous source requires one equal-weight global day/block score')
        return self


class Plan(Strict):
    learner_id: str = Field(pattern=r'^learner_[a-f0-9]{16}$')
    attempt_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    instrument: Literal['voice','ukulele','keyboard','piano','other']
    exercise_id: str = Field(pattern=r'^[a-zA-Z0-9_|.-]{1,1000}$')
    exercise_version: str = Field(pattern=r'^[a-zA-Z0-9_.-]{1,40}$')
    not_before: AwareDatetime
    concepts: list[int] = Field(min_length=1, max_length=1024)
    score_definition: Literal['singpad_note_binary','yousician_active_day_fraction','amme_scoretype7_block_mean','custom_unvalidated']
    scale: Literal['binary_notes','continuous_unit_interval']
    model_id: str = Field(pattern=r'^[a-z0-9_-]{1,120}$')

    @model_validator(mode='after')
    def supported_indices(self):
        if any(k<0 or k>1023 for k in self.concepts) or len(set(self.concepts))!=len(self.concepts):
            raise ValueError('Invalid/duplicate concept')
        return self


class Conflict(ValueError):
    pass


@contextmanager
def connection(path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript('''
      CREATE TABLE IF NOT EXISTS consent(learner TEXT PRIMARY KEY, data TEXT NOT NULL, expires TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS practice(id TEXT PRIMARY KEY, learner TEXT NOT NULL REFERENCES consent(learner) ON DELETE CASCADE,
        attempt TEXT NOT NULL, received TEXT NOT NULL, data TEXT NOT NULL, UNIQUE(learner,attempt));
      CREATE TABLE IF NOT EXISTS prediction(id TEXT PRIMARY KEY, learner TEXT NOT NULL REFERENCES consent(learner) ON DELETE CASCADE,
        attempt TEXT NOT NULL, created TEXT NOT NULL, plan TEXT NOT NULL, output TEXT NOT NULL, UNIQUE(learner,attempt));
      CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, at TEXT NOT NULL, action TEXT NOT NULL, subject_digest TEXT NOT NULL);
      CREATE INDEX IF NOT EXISTS practice_learner ON practice(learner);
    ''')
    try:
        conn.execute('BEGIN IMMEDIATE')
        expired = conn.execute('SELECT learner FROM consent WHERE expires<=?', (now().isoformat(),)).fetchall()
        for (learner,) in expired:
            conn.execute('DELETE FROM consent WHERE learner=?', (learner,)); audit(conn,'retention_delete',learner)
        # Retention must survive rejection/rollback of the requested operation.
        conn.commit()
        conn.execute('BEGIN IMMEDIATE')
        yield conn
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


def audit(conn, action, learner):
    conn.execute('INSERT INTO audit(at,action,subject_digest) VALUES(?,?,?)',
                 (now().isoformat(),action,hashlib.sha256(learner.encode()).hexdigest()))
    # No permanent per-learner traces: bounded 90-day audit retention.
    conn.execute('DELETE FROM audit WHERE at<?', ((now()-timedelta(days=90)).isoformat(),))


def require_consent(conn, learner):
    if not conn.execute('SELECT 1 FROM consent WHERE learner=? AND expires>?',(learner,now().isoformat())).fetchone():
        raise PermissionError('Consent absent or expired')


def grant(path, body: Consent):
    with connection(path) as conn:
        conn.execute('INSERT INTO consent VALUES(?,?,?) ON CONFLICT(learner) DO UPDATE SET data=excluded.data,expires=excluded.expires',
                     (body.learner_id,body.model_dump_json(),(now()+timedelta(days=body.retention_days)).isoformat()))
        audit(conn,'consent_granted',body.learner_id)
    return {'status':'consent_recorded','limitation':'declaration by authorized local operator; no external identity verification'}


def ingest(path, body: PracticeEvent):
    payload = canonical(body.model_dump(mode='json'))
    with connection(path) as conn:
        require_consent(conn,body.learner_id)
        old = conn.execute('SELECT data FROM practice WHERE id=?',(body.event_id,)).fetchone()
        if old:
            if old[0]!=payload: raise Conflict('Event ID reused with a different payload')
            return {'status':'duplicate','event_id':body.event_id}
        try:
            conn.execute('INSERT INTO practice VALUES(?,?,?,?,?)',
                         (body.event_id,body.learner_id,body.attempt_id,now().isoformat(),payload))
        except sqlite3.IntegrityError as exc: raise Conflict('Attempt already has an outcome; no silent overwrite') from exc
        audit(conn,'event_ingested',body.learner_id)
    return {'status':'recorded','event_id':body.event_id}


def available_history(conn,learner,cutoff):
    events=[PracticeEvent.model_validate_json(data) for data,received in
            conn.execute('SELECT data,received FROM practice WHERE learner=?',(learner,))
            if datetime.fromisoformat(received)<cutoff]
    return sorted((e for e in events if e.available_at<cutoff and e.occurred_at<cutoff),
                  key=lambda e:(e.occurred_at,e.available_at,e.event_id))


def record_prediction(path, plan: Plan):
    with connection(path) as conn:
        require_consent(conn,plan.learner_id)
        old = conn.execute('SELECT id,plan,output,created FROM prediction WHERE learner=? AND attempt=?',
                           (plan.learner_id,plan.attempt_id)).fetchone()
        encoded_plan = canonical(plan.model_dump(mode='json'))
        if old:
            if old[1]!=encoded_plan: raise Conflict('An immutable prediction already exists for this attempt')
            return {'prediction_id':old[0],'created_at':old[3],'output':json.loads(old[2]),'idempotent':True}
        created = now()
        if plan.not_before <= created: raise ValueError('Prospective attempt must start after prediction request')
        if conn.execute('SELECT 1 FROM practice WHERE learner=? AND attempt=?',(plan.learner_id,plan.attempt_id)).fetchone():
            raise Conflict('Outcome already recorded; prospective prediction forbidden')
        events = available_history(conn,plan.learner_id,created)
        compatible = [e for e in events if e.instrument==plan.instrument and e.score_definition==plan.score_definition
                      and e.scale==plan.scale and e.exercise_version==plan.exercise_version and e.available_at<created]
        # No automatic transfer from benchmark scores to field assessments. A pilot
        # needs an approved target/measurement contract before a live model is enabled.
        output = {'status':'abstained','reason':'prospective_measurement_contract_not_validated',
                  'predictions':None, 'model_id':plan.model_id,
                  'compatible_history_events':len(compatible), 'requested_concepts':plan.concepts,
                  'scope':'prospective infrastructure only; no validated field model'}
        prediction_id = uuid4().hex
        conn.execute('INSERT INTO prediction VALUES(?,?,?,?,?,?)',
            (prediction_id,plan.learner_id,plan.attempt_id,created.isoformat(),encoded_plan,canonical(output)))
        audit(conn,'prediction_recorded',plan.learner_id)
    return {'prediction_id':prediction_id,'created_at':created.isoformat(),'output':output,'idempotent':False}


def export(path, learner):
    with connection(path) as conn:
        require_consent(conn,learner)
        records=conn.execute('SELECT data,received FROM practice WHERE learner=? ORDER BY received,id',(learner,)).fetchall()
        events=sorted((json.loads(r[0]) for r in records),key=lambda e:(datetime.fromisoformat(e['occurred_at']),e['event_id']))
        forecasts = [{'id':r[0],'created_at':r[1],'plan':json.loads(r[2]),'output':json.loads(r[3])}
                     for r in conn.execute('SELECT id,created,plan,output FROM prediction WHERE learner=? ORDER BY created,id',(learner,))]
        evaluations = []
        for prediction in forecasts:
            plan = Plan(**prediction['plan']); output = prediction['output']
            outcome = next((e for e in events if e['attempt_id']==plan.attempt_id),None)
            status = 'awaiting_outcome' if outcome is None else 'not_scored_abstention'
            errors = None
            if outcome is not None and output.get('predictions'):
                e = PracticeEvent(**outcome)
                compatible = (e.occurred_at>=plan.not_before and e.occurred_at>datetime.fromisoformat(prediction['created_at'])
                    and e.instrument==plan.instrument and e.exercise_id==plan.exercise_id and e.exercise_version==plan.exercise_version
                    and e.score_definition==plan.score_definition and e.scale==plan.scale)
                status = 'evaluated' if compatible else 'incompatible_outcome'
                if compatible:
                    errors = {str(o.concept):abs(output['predictions'][str(o.concept)]-o.value)
                              for o in e.outcomes if str(o.concept) in output['predictions']}
                    if not errors: status = 'no_matched_concepts'; errors = None
            evaluations.append({'prediction_id':prediction['id'],'status':status,'absolute_errors':errors})
        audit(conn,'learner_export',learner)
        return {'schema':'o08-export-v1','consent':json.loads(conn.execute('SELECT data FROM consent WHERE learner=?',(learner,)).fetchone()[0]),
                'events':events,'predictions':forecasts,'evaluations':evaluations,
                'event_receipts':[{'event_id':json.loads(data)['event_id'],'received_at':received} for data,received in records],
                'limitations':'No real prospective study has been performed; abstentions are never scored as predictions.'}


def erase(path, learner):
    with connection(path) as conn:
        conn.execute('DELETE FROM consent WHERE learner=?',(learner,))
        audit(conn,'learner_deleted',learner)
    return {'status':'deleted','scope':'events, predictions and consent in active local store; external backups are operator responsibility'}


def authorize(authorization: str | None = Header(default=None)):
    token = os.environ.get('DECLIC_O08_ADMIN_TOKEN','')
    if len(token)<32: raise HTTPException(503,'Collecte désactivée : configurer un jeton administrateur local de 32 caractères minimum.')
    if not authorization or not hmac.compare_digest(authorization.encode('utf-8'),('Bearer '+token).encode('utf-8')): raise HTTPException(401,'Unauthorized')


def operation(fn, *args):
    try: return fn(DB,*args)
    except PermissionError: raise HTTPException(403,'Consent absent ou expiré')
    except Conflict as exc: raise HTTPException(409,str(exc))
    except ValueError as exc: raise HTTPException(422,str(exc))


@router.post('/consent',dependencies=[Depends(authorize)])
def consent_endpoint(body: Consent): return operation(grant,body)

@router.post('/events',dependencies=[Depends(authorize)])
def events_endpoint(body: PracticeEvent): return operation(ingest,body)

@router.post('/predictions',dependencies=[Depends(authorize)])
def prediction_endpoint(body: Plan): return operation(record_prediction,body)

@router.get('/learners/{learner}/export',dependencies=[Depends(authorize)])
def export_endpoint(learner: str): return operation(export,learner)

@router.delete('/learners/{learner}',dependencies=[Depends(authorize)])
def erase_endpoint(learner: str): return operation(erase,learner)
