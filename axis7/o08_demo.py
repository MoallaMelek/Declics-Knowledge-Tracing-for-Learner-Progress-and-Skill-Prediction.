"""Three real-data demo steps: history, actual inference, then held-out reveal."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .data import ROOT
from .musical_api import BenchmarkQuery, musical_forecast
from .musical_registry import REGISTRY_ROOT, cached_validate
from .skill_states import skill_states, catalogue_from_history, recommend

router = APIRouter(prefix='/api/v6/o08/demo')
# Shared key required when several workers are intentionally configured. The
# default local launcher uses one worker; restarting invalidates old tickets.
SECRET = os.environ.get('DECLIC_DEMO_SIGNING_KEY','').encode() or secrets.token_bytes(32)


def case(source):
    path = ROOT/'runtime/musical-demo'/f'{source}.json'
    try:
        raw = path.read_bytes(); value = json.loads(raw)
        BenchmarkQuery(**value['query'])
        return value, hashlib.sha256(raw).hexdigest()
    except (ValueError, KeyError, OSError):
        raise HTTPException(503,'La démonstration réelle doit être reconstruite depuis l’archive locale.')


def ticket(payload):
    value = {**payload,'expires':int(time.time())+1800}
    encoded = base64.urlsafe_b64encode(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).decode()
    return encoded+'.'+hmac.new(SECRET,encoded.encode(),hashlib.sha256).hexdigest()


def verify(value, stage):
    try:
        encoded,signature = value.split('.')
        expected = hmac.new(SECRET,encoded.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature,expected): raise ValueError()
        payload = json.loads(base64.urlsafe_b64decode(encoded))
        if payload['expires']<time.time() or payload['stage']!=stage: raise ValueError()
        if payload['source'] not in ('singpad','yousician'): raise ValueError()
        data,fingerprint = case(payload['source'])
        if fingerprint!=payload['case_sha256']: raise ValueError()
        return payload,data
    except (ValueError,KeyError,TypeError):
        raise HTTPException(409,'Étape expirée ou historique modifié ; recommencez la démonstration.')


class Step(BaseModel):
    model_config = ConfigDict(extra='forbid')
    receipt: str = Field(max_length=32768)


def rows(query):
    grouped = {}
    for group in query.history:
        if group.time>=query.query_time: continue
        row = grouped.setdefault(group.time,{'time':group.time,'exercise':set(),'obs':[]})
        if group.exercise: row['exercise'].update(group.exercise.split('|'))
        row['obs'].extend([[o.concept,o.score,o.weight] for o in group.observations])
    return [{'time':t,'exercise':'|'.join(sorted(r['exercise'])),'obs':r['obs']} for t,r in sorted(grouped.items())]


@router.get('/history')
def history(source: Literal['singpad','yousician']='singpad'):
    data,fingerprint = case(source); query = BenchmarkQuery(**data['query'])
    history_rows = rows(query)
    summary = skill_states(history_rows,query.concepts,source,query_time=query.query_time)
    return {'provenance':data['provenance'],'history':data['plot_history'],'skill_states':summary,
            'target':{'exercise':query.exercise,'instrument':query.instrument,'concepts':query.concepts,
                      'horizon':'prochain groupe d’enregistrements' if source=='singpad' else 'prochain jour actif'},
            'receipt':ticket({'stage':'history','source':source,'case_sha256':fingerprint}),
            'future_outcome_included':False}


@router.post('/predict')
def predict(body: Step):
    payload,data = verify(body.receipt,'history'); query = BenchmarkQuery(**data['query'])
    start = time.perf_counter(); forecast = musical_forecast(query); elapsed = time.perf_counter()-start
    if forecast['status']!='source_benchmark_only':
        return {'forecast':forecast,'reveal_receipt':None}
    history_rows = rows(query)
    summary = skill_states(history_rows,query.concepts,query.source,forecast['predictions'],query.query_time)
    meta,model = cached_validate(REGISTRY_ROOT/query.model_id)
    length = len(history_rows)+1; context = meta['context']
    left = 0 if length<=context-1 else ((length-1)//(context-1))*(context-1)-1
    receipt = ticket({'stage':'predicted','source':query.source,'case_sha256':payload['case_sha256'],
                      'predictions':forecast['predictions'],'model_id':query.model_id,'model_sha256':meta['model_sha256']})
    return {'forecast':forecast,'skill_states':summary,
            'recommendation':recommend(summary,catalogue_from_history(history_rows,query.source)),
            'technical':{'architecture':meta['model'],'model_id':query.model_id,'dataset':query.source,
                'model_sha256':meta['model_sha256'],
                'K':meta['K'],'tensor_shape':[1,length-max(left,0),4*meta['K']],
                'available_prefix_groups':len(history_rows),'sequence_window_groups':length-max(left,0),
                'parameters':sum(p.numel() for p in model.parameters()),'elapsed_seconds':elapsed,
                'processing':'GRU : mémoire des observations précédentes puis sortie par concept ; cumuls strictement antérieurs.',
                'metric':'log-loss par note' if query.source=='singpad' else 'erreur absolue par jour actif',
                'future_target_in_input':False,'individual_uncertainty':'non validée'},
            'reveal_receipt':receipt}


@router.post('/reveal')
def reveal(body: Step):
    payload,data = verify(body.receipt,'predicted')
    observed = data['observed_target']; predictions = payload['predictions']
    return {'observed_target':observed,'comparison':[
        {'concept':k,'prediction':p,'observed':observed.get(k),
         'absolute_error':abs(p-observed[k]) if k in observed else None}
        for k,p in predictions.items()],
        'model_id':payload['model_id'],
        'model_sha256':payload['model_sha256'],
        'interpretation':'Comparaison descriptive d’un exemple de test ; aucune sélection selon son erreur.'}


@router.get('/research')
def research():
    directory = ROOT/'artifacts/phase7'
    path = directory/'summary.json'
    if not path.exists(): raise HTTPException(503,'Les expériences Phase 7 ne sont pas encore toutes consolidées.')
    return json.loads(path.read_text(encoding='utf-8'))
