"""Audit regressions on deterministic fixtures with copied trained tensors, no training.

These prove engineering contracts, not source-benchmark accuracy. Integrity checks stay ON.
"""
import copy
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import socket
import sys
import pytest
from fastapi.testclient import TestClient
from test_phase8_living import env, singpad_env, state, rows_of, write
from axis7 import living_learner as living, musical_registry as registry
from axis7.serving_identity import MAX_HISTORY, canonical_digest, freeze


def test_same_declared_archive_changed_past_misses_cache_and_receipt(env):
    client, folder, data = env
    original = state(client, 5)
    rows = rows_of(client, data, '01')
    archive_hash = data['sha256']
    for row in rows[:5]: row['obs'][0][1] = 1. - row['obs'][0][1]
    old_stat = (folder/'yousician-prepared.json.gz').stat()
    write(folder, data)
    os.utime(folder/'yousician-prepared.json.gz', ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
    changed = state(client, 5)   # no manual cache clear; same declared archive + preserved mtime
    assert data['sha256'] == archive_hash
    assert changed['identity'] != original['identity']
    assert changed['forecast']['predictions'] != original['forecast']['predictions']
    assert client.post('/api/v7/o08/living/reveal', json={'receipt':original['reveal_receipt']}).status_code == 409
    assert client.post('/api/v7/o08/living/reveal', json={'receipt':changed['reveal_receipt']}).status_code == 200


def test_target_only_change_invalidates_receipt_not_neural_prediction(env):
    client, folder, data = env; before = state(client, 5)
    rows_of(client, data, '01')[5]['obs'][0][1] = .123456
    write(folder, data); after = state(client, 5)
    assert before['forecast']['predictions'] == after['forecast']['predictions']
    assert before['identity'] != after['identity']
    assert client.post('/api/v7/o08/living/reveal',json={'receipt':before['reveal_receipt']}).status_code == 409


def test_immutable_loaded_data_and_cloned_changed_history(env):
    client, _, _ = env; state(client, 5)
    c = living.cohort('yousician'); rows=c['learners'][0]
    with pytest.raises(TypeError): rows[0]['obs'][0][1] = .9
    with pytest.raises(TypeError): c['meta']['context'] = 7
    # Cloned counterexample: an internal caller supplies different actual rows under old metadata.
    cloned=json.loads(json.dumps(rows)); first=living.forecast_at(c,0,rows,5)
    for r in cloned[:5]:r['obs'][0][1] = 1-r['obs'][0][1]
    second=living.forecast_at(c,0,cloned,5)
    assert first['predictions'] != second['predictions']


def test_metadata_only_replacement_changes_generation(env):
    client, _, _ = env; before=state(client,5)
    path=living.REGISTRY_ROOT/before['provenance']['model_id']/'metrics.json'
    meta=json.loads(path.read_text());meta['limitations'].append('Added evidence annotation')
    path.write_text(json.dumps(meta),encoding='utf-8');after=state(client,5)
    assert before['identity'] != after['identity']
    assert before['forecast']['predictions']==after['forecast']['predictions']
    assert client.post('/api/v7/o08/living/reveal',json={'receipt':before['reveal_receipt']}).status_code==409


def test_checkpoint_corruption_is_not_served(env):
    client, _, _ = env;s=state(client,5)
    path=living.REGISTRY_ROOT/s['provenance']['model_id']/'model.pt'
    content=bytearray(path.read_bytes()); content[-12] ^= 1;path.write_bytes(content)
    response=client.get('/api/v7/o08/living/state?source=yousician&cutoff=5')
    assert response.status_code==503 and response.json()['detail']['code']=='missing_model'


@pytest.mark.parametrize('kind',['gzip','score','weight'])
def test_invalid_prepared_content_returns_controlled_data_error(env,kind):
    client,folder,data=env
    if kind=='gzip':(folder/'yousician-prepared.json.gz').write_bytes(b'\x1f\x8b')
    else:
        row=rows_of(client,data,'01')[0]
        row['obs'][0][1 if kind=='score' else 2]=2. if kind=='score' else 0.
        write(folder,data)
    r=client.get('/api/v7/o08/living/state?source=yousician&cutoff=3')
    assert r.status_code==503 and r.json()['detail']['code']=='missing_data'


def test_generation_bound_state_inspect_and_reveal(env):
    client,_,_=env;s=state(client,5)
    i=client.get('/api/v7/o08/living/inspect?source=yousician&cutoff=5').json()
    r=client.post('/api/v7/o08/living/reveal',json={'receipt':s['reveal_receipt']}).json()
    assert s['identity']==i['identity']==r['identity']
    assert i['matches_served_forecast']


def test_501_is_controlled_and_long_replay_is_explicitly_excluded(env):
    client,folder,data=env
    rows=rows_of(client,data,'01')
    rows[:] = [{'time':t,'exercise':'','obs':[[0,.5,1.]],'difficulty':0.} for t in range(503)]
    write(folder,data)
    listing=client.get('/api/v7/o08/living/learners?source=yousician').json()
    assert listing['counts']['excluded_over_limit']==1
    assert all(x['steps']<=MAX_HISTORY for x in listing['learners'])
    assert client.get('/api/v7/o08/living/state?source=yousician&cutoff=501').status_code==422
    assert client.get('/api/v7/o08/living/inspect?source=yousician&cutoff=501').status_code==422
    with pytest.raises(Exception) as e: living.query_for(living.cohort('yousician'),rows,501)
    assert getattr(e.value,'status_code',None)==422


def test_readiness_does_not_pass_old_or_partial_configuration(env,monkeypatch,tmp_path):
    from axis7 import readiness
    client,_,_=env
    report=readiness.assess([])
    assert not report['ready'] and not report['routes_registered']
    monkeypatch.setattr(living,'DATA_DIR',tmp_path/'absent')
    report=readiness.assess(readiness.REQUIRED)
    assert not report['ready'] and report['routes_registered']
    assert all(not s['prepared_data'] for s in report['sources'].values())
    text=json.dumps(report)
    assert str(tmp_path) not in text and 'SECRET-' not in text


def test_readiness_is_successful_with_both_validated_fixture_sources(tmp_path,monkeypatch):
    from scripts.integration_fixture import build
    from axis7 import readiness
    root,prepared=build(tmp_path)
    monkeypatch.setattr(living,'REGISTRY_ROOT',root);monkeypatch.setattr(living,'DATA_DIR',prepared)
    monkeypatch.setattr(living,'_cohorts',{});monkeypatch.setattr(living,'_forecasts',{})
    report=readiness.assess(readiness.REQUIRED)
    assert report['ready'] and all(x['inference'] for x in report['sources'].values())
    from axis7.server import app
    actual=TestClient(app).get('/api/readiness')
    assert actual.status_code==200 and actual.json()['routes_registered']
    # Fixture generation/splits/config are validated; no monkeypatched integrity function.
    assert all(living.provenance(living.cohort(s))['data_mode']=='synthetic_fixture' for s in ('singpad','yousician'))


def test_canonical_serialization_rejects_nonfinite_and_respects_sequence_order():
    assert canonical_digest({'b':2,'a':1})==canonical_digest({'a':1,'b':2})
    assert canonical_digest([1,2])!=canonical_digest([2,1])
    with pytest.raises(ValueError):canonical_digest({'x':float('nan')})


def test_yousician_experimental_policy_never_selects_on_test():
    from axis7.model_eligibility import describe
    from axis7.data import ROOT
    root=ROOT/'artifacts/models/musical-cloud';active=json.loads((root/'active.json').read_text(encoding='utf-8'))
    meta=json.loads((root/active['yousician']/'metrics.json').read_text(encoding='utf-8'))
    p=describe(meta)
    assert p['tier']=='experimental_dl_source_benchmark'
    assert p['improves_available_learned_controls'] is False
    assert p['neural_validation']==pytest.approx(.0955381028794489)
    assert p['control_validation']==pytest.approx(.0947175630636283)
    meta['test']['mae']=0.
    assert describe(meta)==p


def test_occupied_port_is_not_killed_or_misreported():
    from axis7 import launch
    from argparse import Namespace
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));listener.listen()
        args=Namespace(host='127.0.0.1',port=listener.getsockname()[1],prepared_data=None,timeout=5,allow_partial=False,check=True)
        assert launch.run(args)==2
        assert listener.fileno()!=-1


def test_launcher_rejects_even_same_revision_from_another_process():
    from axis7.launch import matches_instance
    report={'application':'declic-phase8','revision':'abc','identity_contract':'living-generation-v1','instance_id':'own'}
    assert matches_instance(report,'abc','own')
    assert not matches_instance(report,'abc','other')
    assert not matches_instance(report,'old-revision','own')
    assert not matches_instance({'alive':True},'abc','own')


def test_unrelated_listener_with_json_array_is_not_a_readiness_report(monkeypatch):
    import io
    from axis7 import launch
    monkeypatch.setattr(launch.urllib.request,'urlopen',lambda *a,**k:io.StringIO('[]'))
    assert launch.read_status('http://127.0.0.1/api/readiness') is None


@pytest.mark.parametrize('outside',[False,True])
@pytest.mark.skipif(shutil.which('pwsh') is None,reason='PowerShell launcher integration runs on Windows/pwsh; Python supervisor covered separately')
def test_windows_launcher_two_working_directories(tmp_path,outside):
    from scripts.integration_fixture import build
    from axis7.data import ROOT
    registry_root,prepared=build(tmp_path/'fixture')
    env={**os.environ,'DECLIC_MODEL_REGISTRY':str(registry_root),'OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    run=subprocess.run(['pwsh','-NoProfile','-File',str(ROOT/'Launch.ps1'),'-Python',sys.executable,
                        '-Port',str(port),'-PreparedData',str(prepared),'-Check'],
                       cwd=tmp_path if outside else ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=100)
    assert run.returncode==0,run.stdout+run.stderr
    assert '"ready": true' in run.stdout and '"application": "declic-phase8"' in run.stdout
    assert sys.executable in run.stdout
    assert not __import__('axis7.launch',fromlist=['occupied']).occupied('127.0.0.1',port)
