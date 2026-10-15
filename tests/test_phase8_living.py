"""Phase 8 living-learner adapter: causal replay, reveal contract, inspection integrity, privacy."""
import gzip
import json
import os
from pathlib import Path
import random
import shutil
import subprocess

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from axis7 import living_learner as living, musical_api, musical_registry as registry
from axis7.musical_api import BenchmarkQuery

ROOT = Path(__file__).resolve().parents[1]


def prepared(seed=0, n=14):
    rng = random.Random(seed); learners = {}
    for i in range(n):
        length = 3 + i % 10
        learners[f'SECRET-learner-{i}'] = [{'time': 2*d, 'exercise': '', 'difficulty': 0.0,
                                            'obs': [[0, round(rng.random(), 6), 1.0]]} for d in range(length)]
    return {'version': 'musical-cloud-v2', 'source': 'yousician', 'sha256': 'f'*64, 'learners': learners}


def write(folder, data):
    path = folder/'yousician-prepared.json.gz'
    with gzip.open(path, 'wt', encoding='utf-8') as handle: json.dump(data, handle)
    stamp = path.stat().st_mtime_ns + 10**9; os.utime(path, ns=(stamp, stamp))
    return path


@pytest.fixture
def env(tmp_path, monkeypatch):
    registry.install(ROOT/'artifacts/models/phase5/yousician/enhanced_gru', tmp_path/'registry')
    for module in (musical_api, living):
        monkeypatch.setattr(module, 'REGISTRY_ROOT', tmp_path/'registry')
    monkeypatch.setattr(living, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(living, 'check_integrity', lambda *a: None)   # fake learners cannot match real split digests
    monkeypatch.setattr(living, '_cohorts', {}); monkeypatch.setattr(living, '_forecasts', {})
    data = prepared(); write(tmp_path, data)
    app = FastAPI(); app.include_router(living.router)
    return TestClient(app), tmp_path, data


def rows_of(client, data, token):
    """Replays the server's fixed selection rule to find the private rows behind a token (test only)."""
    from axis7.cloud_training import split_learners
    meta, _ = registry.cached_validate(living.REGISTRY_ROOT/json.loads((living.REGISTRY_ROOT/'active.json').read_text())['yousician'])
    test = split_learners(data['learners'], meta['seed'])['test']
    eligible = [data['learners'][l] for l in test if len(data['learners'][l]) >= living.MIN_STEPS]
    return eligible[int(token)-1]


def state(client, cutoff, learner='01'):
    r = client.get(f'/api/v7/o08/living/state?source=yousician&learner={learner}&cutoff={cutoff}')
    assert r.status_code == 200, r.text
    return r.json()


def test_learner_ids_never_leave_the_server(env):
    client, _, data = env
    payload = client.get('/api/v7/o08/living/learners?source=yousician').json()
    assert [l['token'] for l in payload['learners']] == [f'{i+1:02}' for i in range(len(payload['learners']))]
    assert payload['counts']['shown'] == len(payload['learners']) and payload['counts']['excluded_short'] >= 0
    s = state(client, 3)
    for text in (json.dumps(payload), json.dumps(s), s['reveal_receipt']):
        assert 'SECRET-learner' not in text


def test_state_contains_only_steps_before_the_cutoff(env):
    client, _, data = env
    rows = rows_of(client, data, '01')
    for cutoff in range(1, len(rows)+1):
        s = state(client, cutoff)
        assert [p['index'] for p in s['past']] == list(range(cutoff))
        assert all(t['index'] < cutoff for t in s['trail'])
        assert s['future_outcome_included'] is False
        assert (s['target'] is None) == (cutoff == len(rows))
        future = {str(r['obs'][0][1]) for r in rows[cutoff:]} - {str(r['obs'][0][1]) for r in rows[:cutoff]}
        body = json.dumps({k: v for k, v in s.items() if k != 'reveal_receipt'})
        assert not any(value in body for value in future)


def test_changing_future_outcomes_does_not_change_the_cutoff_view(env):
    client, folder, data = env
    before = state(client, 4)
    rows = rows_of(client, data, '01')
    for row in rows[4:]: row['obs'][0][1] = 0.999   # target and later outcomes change, definitions unchanged
    write(folder, data); living._forecasts.clear()
    after = state(client, 4)
    strip = lambda s: {k: v for k, v in s.items() if k != 'reveal_receipt'}
    assert strip(after) == strip(before)


def test_forecast_is_the_served_deep_learning_forecast(env):
    client, _, data = env
    rows = rows_of(client, data, '01'); cutoff = 5
    s = state(client, cutoff)
    query = BenchmarkQuery(source='yousician', model_id=s['provenance']['model_id'], instrument='ukulele',
                           query_time=rows[cutoff]['time'], concepts=[0],
                           history=[{'time': r['time'], 'observations': [{'concept': 0, 'score': r['obs'][0][1]}]} for r in rows[:cutoff]])
    assert s['forecast']['predictions'] == musical_api.musical_forecast(query)['predictions']
    assert 'PyTorch' in client.get('/api/v7/o08/living/learners?source=yousician').json()['provenance']['engine']


def test_trail_reuses_forecasts_made_at_earlier_cutoffs(env):
    client, _, data = env
    rows = rows_of(client, data, '01'); s = state(client, 6)
    for entry in s['trail'][1:]:
        earlier = state(client, entry['index'])
        assert entry['predicted_mean'] == pytest.approx(earlier['forecast']['predictions']['0'])
        assert entry['observed_mean'] == pytest.approx(rows[entry['index']]['obs'][0][1])
        assert entry['error'] == pytest.approx(abs(entry['predicted_mean']-entry['observed_mean']))


def test_first_cutoff_abstains_without_inventing_a_value(env):
    client, _, _ = env
    s = state(client, 1)
    assert s['forecast']['status'] == 'abstained' and s['forecast']['predictions'] is None
    assert s['forecast']['reason'] == 'insufficient_atomic_history' and s['reveal_receipt'] is None
    assert client.get('/api/v7/o08/living/inspect?source=yousician&learner=01&cutoff=1').json()['available'] is False


def test_reveal_is_server_mediated_and_bound_to_the_forecast(env):
    client, folder, data = env
    rows = rows_of(client, data, '01'); s = state(client, 5)
    assert client.post('/api/v7/o08/living/reveal', json={'receipt': s['reveal_receipt'][:-2]+'00'}).status_code == 409
    assert client.post('/api/v7/o08/living/reveal', json={'receipt': 'not-a-ticket'}).status_code == 409
    r = client.post('/api/v7/o08/living/reveal', json={'receipt': s['reveal_receipt']}).json()
    observed = rows[5]['obs'][0][1]; p = s['forecast']['predictions']['0']
    assert r['cutoff'] == 5 and r['comparison'][0]['observed'] == pytest.approx(observed)
    assert r['error'] == pytest.approx(abs(p-observed))
    mean = r['references']['train_mean']['value']
    assert r['references']['train_mean']['error'] == pytest.approx(abs(mean-observed))
    personal = sum(row['obs'][0][1] for row in rows[:5])/5
    assert r['references']['learner_concept_history']['error'] == pytest.approx(abs(personal-observed))
    data['sha256'] = 'e'*64; write(folder, data)   # a different archive invalidates old tickets
    assert client.post('/api/v7/o08/living/reveal', json={'receipt': s['reveal_receipt']}).status_code == 409


def test_inspection_uses_an_isolated_copy_and_matches_the_served_forecast(env):
    client, _, _ = env
    s = state(client, 6)
    ins = client.get('/api/v7/o08/living/inspect?source=yousician&learner=01&cutoff=6').json()
    assert ins['available'] and ins['matches_served_forecast'] and ins['max_abs_difference'] < 1e-5
    assert ins['served_predictions'] == s['forecast']['predictions']
    assert len(ins['hidden_states']) == ins['window']['steps_in_window'] == len(ins['steps'])
    assert ins['steps'][-1]['is_query'] and not any(r['is_query'] for r in ins['steps'][:-1])
    assert ins['attention'] is None
    _, model = registry.cached_validate(living.REGISTRY_ROOT/s['provenance']['model_id'])
    assert not model.encoder._forward_hooks   # the served model never carries an inspection hook


def test_bounds_and_missing_private_data(env, tmp_path, monkeypatch):
    client, folder, _ = env
    assert client.get('/api/v7/o08/living/state?source=yousician&learner=01&cutoff=999').status_code == 422
    assert client.get('/api/v7/o08/living/state?source=yousician&learner=99&cutoff=2').status_code == 404
    assert client.get('/api/v7/o08/living/state?source=yousician&learner=..%2F01&cutoff=2').status_code in (404, 422)
    assert client.get('/api/v7/o08/living/state?source=yousician&learner=1e1&cutoff=2').status_code == 404
    monkeypatch.setattr(living, 'DATA_DIR', tmp_path/'absent'); monkeypatch.setattr(living, '_cohorts', {})
    assert client.get('/api/v7/o08/living/learners?source=yousician').status_code == 503


def test_integrity_gate_rejects_foreign_data_and_splits():
    from axis7.cloud_training import public_split_provenance
    splits = {'train': ['a'], 'validation': ['b'], 'test': ['c']}
    meta = {'sha256': 'x', 'splits': public_split_provenance(splits)}
    living.check_integrity({'sha256': 'x'}, meta, splits)
    with pytest.raises(ValueError): living.check_integrity({'sha256': 'y'}, meta, splits)
    with pytest.raises(ValueError): living.check_integrity({'sha256': 'x'}, meta, {'train': ['a'], 'validation': ['c'], 'test': ['b']})


def test_no_classical_model_on_the_living_path():
    source = (ROOT/'axis7/living_learner.py').read_text(encoding='utf-8')
    for name in ('sklearn', 'Ridge', 'LogisticRegression', 'lightgbm', 'HistGradientBoosting', 'phase7_strong_controls'):
        assert name not in source


def test_living_bodies_are_bounded_by_the_o08_limit():
    from axis7 import server
    client = TestClient(server.app)
    assert client.post('/api/v7/o08/living/reveal', content=b'x'*600000, headers={'Content-Type': 'application/json'}).status_code == 413


@pytest.mark.skipif(shutil.which('node') is None, reason='Node.js is not installed')
def test_frontend_adapters_and_network_layer_with_real_payloads(env, tmp_path):
    client, _, _ = env
    learners = client.get('/api/v7/o08/living/learners?source=yousician').json()['learners']
    token = next(l for l in learners if l['steps'] >= 8)
    states = [state(client, c, token['token']) for c in range(1, token['steps']+1)]
    reveal = client.post('/api/v7/o08/living/reveal', json={'receipt': states[4]['reveal_receipt']}).json()
    fixtures = tmp_path/'living-fixtures.json'
    fixtures.write_text(json.dumps({'states': states, 'reveal': reveal}), encoding='utf-8')
    run = subprocess.run(['node', str(ROOT/'tests/frontend/living_check.js'), str(ROOT/'web/living'), str(fixtures)],
                         capture_output=True, text=True, encoding='utf-8', timeout=120)
    print(run.stdout)
    assert run.returncode == 0, run.stdout+run.stderr
    assert 'checks passed' in run.stdout


@pytest.mark.skipif(not (ROOT/'runtime/musical-demo/singpad-prepared.json.gz').exists(), reason='private held-out data not installed')
def test_real_learner_01_reproduces_the_phase7_demo_forecast():
    from axis7 import o08_demo, server
    client = TestClient(server.app)
    h = client.get('/api/v6/o08/demo/history?source=singpad').json()
    demo = client.post('/api/v6/o08/demo/predict', json={'receipt': h['receipt']}).json()['forecast']['predictions']
    s = client.get('/api/v7/o08/living/state?source=singpad&learner=01&cutoff=3').json()
    for k, v in demo.items():
        assert s['forecast']['predictions'][k] == pytest.approx(v, abs=1e-6)
    assert all('recency' not in st['observation'] and 'last_observed_time' not in st['observation'] for st in s['skill_states']['states'])
    ins = client.get('/api/v7/o08/living/inspect?source=singpad&learner=01&cutoff=14').json()
    assert ins['matches_served_forecast']
