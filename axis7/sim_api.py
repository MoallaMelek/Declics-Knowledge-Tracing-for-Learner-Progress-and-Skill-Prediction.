"""Read-only API of the SYNTHETIC simulation study (artifacts/simulation/<study>/).

Serves files produced by scripts/run_simulation_study.py; it never computes, trains or writes,
and never reads the real learner database. Every payload carries ``synthetic: true``.
"""
from __future__ import annotations

from functools import lru_cache
import gzip
import json
from pathlib import Path
import re

from fastapi import APIRouter, HTTPException

from .data import ROOT
from . import sim_learners as sl

router = APIRouter(prefix='/api/sim', tags=['simulation (synthétique)'])
BASE = ROOT / 'artifacts/simulation'
SAFE = re.compile(r'^[A-Za-z0-9_.-]{1,80}$')


def _study(study):
    if not SAFE.fullmatch(study) or not (BASE / study / 'inspection.json').exists():
        raise HTTPException(404, 'Étude de simulation inconnue.')
    return BASE / study


def _read(path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=4)
def _explorer(path_str, mtime):
    with gzip.open(path_str, 'rt', encoding='utf-8') as f:
        return json.load(f)


def explorer(study):
    path = _study(study) / 'ui/A1-explorer.json.gz'
    if not path.exists():
        raise HTTPException(404, 'Données d’exploration absentes : lancez « run_simulation_study.py ui ».')
    return _explorer(str(path), path.stat().st_mtime_ns)


@router.get('/studies')
def studies():
    out = []
    if BASE.exists():
        for d in sorted(BASE.iterdir()):
            if (d / 'inspection.json').exists():
                out.append({'id': d.name, 'campaigns': list(_read(d / 'inspection.json', {}).keys())})
    return {'synthetic': True, 'studies': out}


@router.get('/{study}/overview')
def overview(study: str):
    d = _study(study)
    return {'synthetic': True, 'study': study, 'config': _read(ROOT / 'configs/simulation-study.json'),
            'inspection': _read(d / 'inspection.json', {}), 'main': _read(d / 'results/main.json'),
            'replications': _read(d / 'results/replications.json'), 'shift': _read(d / 'results/shift.json'),
            'size': _read(d / 'results/size.json'), 'families': _read(d / 'results/families.json'),
            'sensitivity': _read(d / 'results/sensitivity.json'),
            'family_labels': {**{k: v['label'] for k, v in sl.FAMILIES_B.items()}, **{k: v['label'] for k, v in sl.FAMILIES_A.items()}}}


@router.get('/{study}/learners')
def learners(study: str):
    data = explorer(study)
    rows = []
    for x in data['learners']:
        q = x['questions']
        rows.append({'sim_id': x['sim_id'], 'family': x['family'], 'family_label': x['family_label'], 'questions': len(q),
                     'correct_rate': (sum(r[5] for r in q) / len(q)) if q else None,
                     'status_end': x['days'][-1][1] if x['days'] else None})
    return {'synthetic': True, 'campaign': data['campaign'], 'note': data['note'], 'learners': rows}


@router.get('/{study}/learner/{sim_id}')
def learner(study: str, sim_id: str):
    data = explorer(study)
    for x in data['learners']:
        if x['sim_id'] == sim_id:
            return {'synthetic': True, 'campaign': data['campaign'], 'skills': data['skills'],
                    'question_columns': data['question_columns'], 'note': data['note'], **x}
    raise HTTPException(404, 'Élève virtuel inconnu.')


@router.get('/{study}/technical')
def technical(study: str):
    d = _study(study)
    models = []
    for folder in sorted((d / 'models').glob('*')):
        cfg = _read(folder / 'config.json')
        if cfg:
            models.append({'name': folder.name, 'config': {k: v for k, v in cfg.items() if k != 'items'},
                           'items': len(cfg.get('items', {})), 'history': _read(folder / 'history.json', [])})
    return {'synthetic': True, 'models': models, 'provenance': sl.PROVENANCE,
            'units': sl.UNITS, 'beginner': sl.BEGINNER, 'expert': sl.EXPERT,
            'families': {'A': {k: {kk: vv for kk, vv in v.items()} for k, v in sl.FAMILIES_A.items()},
                         'B': {k: {kk: vv for kk, vv in v.items()} for k, v in sl.FAMILIES_B.items()}},
            'reproduce': _read(d / 'reproduce.json')}
