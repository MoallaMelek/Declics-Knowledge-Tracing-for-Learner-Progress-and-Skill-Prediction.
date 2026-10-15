"""Explicit real-source research forecasts, separate from personal piano practice."""
from typing import Literal
import math
import json

from fastapi import APIRouter, HTTPException
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
import torch

from .cloud_training import SOURCES, encode, forward
from .musical_registry import REGISTRY_ROOT, entries, validate

router = APIRouter()


class Observation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    concept: int = Field(ge=0, le=1023)
    score: float = Field(ge=0, le=1, allow_inf_nan=False)
    weight: float = Field(default=1, gt=0, le=100000, allow_inf_nan=False)


class Group(BaseModel):
    model_config = ConfigDict(extra='forbid')
    time: float | str
    exercise: str = Field(default='', max_length=1000)
    observations: list[Observation] = Field(min_length=1, max_length=10000)


class BenchmarkQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source: Literal['amme', 'singpad', 'yousician']
    model_id: str = Field(pattern=r'^[a-z0-9_-]+$', max_length=120)
    instrument: str = Field(max_length=50)
    query_time: float | str
    exercise: str = Field(default='', max_length=1000)
    concepts: list[int] = Field(default_factory=lambda: [0], min_length=1, max_length=1024)
    history: list[Group] = Field(max_length=500)

    @model_validator(mode='after')
    def source_time(self):
        from datetime import datetime
        times = [self.query_time] + [r.time for r in self.history]
        if self.source == 'singpad':
            if any(not isinstance(t, str) for t in times):
                raise ValueError('SingPAD requires source local ISO timestamps')
            parsed = [datetime.fromisoformat(t) for t in times]
            if any(t.tzinfo is not None for t in parsed):
                raise ValueError('SingPAD source timezone is unspecified')
            self.query_time = parsed[0].isoformat()
            for row, t in zip(self.history, parsed[1:]):
                row.time = t.isoformat()
        elif any(not isinstance(t, (float, int)) or not math.isfinite(t) or t < 0 for t in times):
            raise ValueError('AMME block / Yousician signup day must be a finite relative number')
        elif any(int(t) != t for t in times):
            raise ValueError('Use whole AMME block numbers / whole signup day numbers')
        if self.source != 'singpad':
            if len({r.time for r in self.history}) != len(self.history):
                raise ValueError('Continuous-source history must contain one aggregated row per block/day')
            if any(len(r.observations) != 1 or r.observations[0].weight != 1 for r in self.history):
                raise ValueError('Continuous-source history requires one equally weighted score per block/day')
        return self


@router.get('/api/v5/musical/models')
def musical_models():
    return {'status': 'source_benchmark_only', 'models': entries(),
            'message': 'Modèles évalués sur leur base musicale. Le carnet piano conserve son abstention.'}


@router.post('/api/v5/musical/forecast')
def musical_forecast(body: BenchmarkQuery):
    folder = REGISTRY_ROOT / body.model_id
    if not folder.is_dir():
        raise HTTPException(404, 'Unknown registered musical model')
    manifest = REGISTRY_ROOT / 'active.json'
    if manifest.exists():
        try:
            active = json.loads(manifest.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            raise HTTPException(503, 'Model registry temporarily unavailable')
        if not isinstance(active, dict) or active.get(body.source) != body.model_id:
            return {'status': 'abstained', 'reason': 'inactive_model', 'predictions': None}
    try:
        meta, model = validate(folder)
    except (ValueError, OSError, KeyError, RuntimeError):
        raise HTTPException(422, 'Model failed benchmark validation')
    if body.source != meta['source'] or body.instrument != meta['instrument']:
        return {'status': 'abstained', 'reason': 'incompatible_domain', 'predictions': None}
    K = meta['K']
    if any(k < 0 or k >= K for k in body.concepts) or any(o.concept >= K for r in body.history for o in r.observations):
        raise HTTPException(422, 'Concept outside source vocabulary')
    if body.source != 'singpad' and (body.concepts != [0] or any(o.concept != 0 for r in body.history for o in r.observations)):
        raise HTTPException(422, 'Continuous score sources have one source-specific target')
    if body.source == 'singpad' and any(o.score not in (0, 1) for r in body.history for o in r.observations):
        raise HTTPException(422, 'SingPAD needs observed binary note outcomes')
    if body.exercise and body.exercise not in meta['items']:
        return {'status': 'abstained', 'reason': 'unseen_exercise', 'predictions': None}
    if body.source == 'singpad' and meta['model'] != 'dkt' and not body.exercise:
        return {'status': 'abstained', 'reason': 'query_exercise_required', 'predictions': None}
    # Equal timestamps cannot be arbitrarily ordered. Combine before encoding.
    grouped = {}
    for r in body.history:
        if r.time >= body.query_time:
            continue
        g = grouped.setdefault(r.time, {'time': r.time, 'exercise': set(), 'obs': []})
        if r.exercise:
            g['exercise'].update(r.exercise.split('|'))
        g['obs'].extend([[o.concept, o.score, o.weight] for o in r.observations])
    if len(grouped) < 2:
        return {'status': 'abstained', 'reason': 'insufficient_atomic_history', 'predictions': None}
    rows = []
    for t in sorted(grouped):
        r = grouped[t]; r['exercise'] = '|'.join(sorted(r['exercise'])); rows.append(r)
    rows.append({'time': body.query_time, 'exercise': body.exercise, 'obs': []})
    values = encode(rows, K, meta['items'])
    # Same window as training, while counts reflect full earlier history.
    context = meta['context']; length = len(rows)
    left = 0 if length <= context-1 else ((length-1)//(context-1))*(context-1)-1
    tensors = [torch.from_numpy(a[max(left,0):]).unsqueeze(0) for a in values]
    with torch.no_grad():
        prediction = torch.sigmoid(forward(model, meta['model'], tensors))[0,-1].numpy()
    return {'status': 'source_benchmark_only', 'source': body.source, 'instrument': body.instrument,
            'target': meta['target'], 'model_id': body.model_id, 'prefix_groups': len(rows)-1,
            'predictions': {str(k): float(prediction[k]) for k in body.concepts},
            'message': 'Prévision de la cible de cette base ; aucune validation pour un autre instrument.',
            'test_metrics': meta['test']}
