"""Public, path-free readiness. Local launch diagnostics add paths only on the terminal."""
import json
import os
from pathlib import Path
import subprocess
import secrets
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from .data import ROOT
from . import living_learner as living
from .musical_registry import cached_validate
from .serving_identity import CONTRACT

router = APIRouter()
VERSION = '8.1.0'
REQUIRED = {'/api/v7/o08/living/learners', '/api/v7/o08/living/state',
            '/api/v7/o08/living/inspect', '/api/v7/o08/living/reveal'}


def git_value(*args):
    try:
        return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True,
                                       stderr=subprocess.DEVNULL, timeout=3).strip()
    except (OSError, subprocess.SubprocessError):
        return 'unavailable'


REVISION = git_value('rev-parse', 'HEAD')
BRANCH = git_value('branch', '--show-current')
INSTANCE = os.environ.get('DECLIC_INSTANCE_ID') or secrets.token_hex(16)


def assess(routes):
    sources = {}
    for source in ('singpad', 'yousician'):
        entry = {'model_valid': False, 'prepared_data': False, 'inference': False, 'ready': False}
        try:
            active = json.loads((living.REGISTRY_ROOT/'active.json').read_text(encoding='utf-8'))
            identifier = active[source]
            if not isinstance(identifier, str) or Path(identifier).name != identifier:
                raise ValueError('Invalid active model identifier')
            meta, _ = cached_validate(living.REGISTRY_ROOT/identifier)
            entry.update(model_valid=True, model_id=identifier, architecture=meta['model'],
                         data_mode='synthetic_fixture' if meta.get('fixture') else 'private_research_data')
        except (OSError, KeyError, ValueError, RuntimeError, TypeError):
            entry['reason'] = 'missing_or_invalid_model'
            sources[source] = entry
            continue
        try:
            c = living.cohort(source)
            entry.update(prepared_data=True, generation=c['generation'], learners=c['counts']['shown'])
            if not c['learners']:
                entry['reason'] = 'no_supported_replay_learner'
            else:
                result = living.forecast_at(c, 0, c['learners'][0], 2)
                entry.update(inference=bool(result.get('predictions')))
                entry['ready'] = entry['inference']
                entry['reason'] = 'ready' if entry['ready'] else 'inference_abstained'
        except Exception as exc:
            # Do not disclose paths, learner IDs, payloads or exception details publicly.
            entry['reason'] = 'missing_or_incompatible_prepared_data' if getattr(exc, 'status_code', None) == 503 else 'inference_unavailable'
        sources[source] = entry
    registered = REQUIRED <= set(routes)
    frontend = all((ROOT/'web'/name).is_file() for name in ('living.html', 'living/main.js', 'living/api.js'))
    ready = registered and frontend and all(s['ready'] for s in sources.values())
    return {'alive': True, 'ready': ready, 'application': 'declic-phase8', 'version': VERSION,
            'identity_contract': CONTRACT, 'revision': REVISION, 'branch': BRANCH,
            'instance_id': INSTANCE,
            'routes_registered': registered, 'frontend_available': frontend,
            'data_mode': 'synthetic_fixture' if any(s.get('data_mode') == 'synthetic_fixture' for s in sources.values()) else 'private_research_data',
            'sources': sources, 'recovery': 'Launch.ps1 -Python <environment-python> -PreparedData <prepared-folder> ; inspect model registry and rebuild compatible prepared data if necessary.'}


@router.get('/api/readiness')
def readiness():
    from .server import app
    # FastAPI may retain included routers lazily; raw app.routes then has wrapper
    # objects without .path. The resolved OpenAPI path inventory covers both versions.
    report = assess(app.openapi()['paths'])
    return JSONResponse(report, status_code=200 if report['ready'] else 503)
