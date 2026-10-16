import json
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from axis7 import o08_demo as demo, musical_api, musical_registry as registry


@pytest.fixture
def api(tmp_path,monkeypatch):
    root=Path(__file__).resolve().parents[1]
    registry.install(root/'artifacts/models/phase5/yousician/enhanced_gru',tmp_path/'registry')
    active=json.loads((tmp_path/'registry/active.json').read_text())
    monkeypatch.setattr(musical_api,'REGISTRY_ROOT',tmp_path/'registry')
    monkeypatch.setattr(demo,'REGISTRY_ROOT',tmp_path/'registry')
    monkeypatch.setattr(demo,'ROOT',tmp_path)
    folder=tmp_path/'runtime/musical-demo';folder.mkdir(parents=True)
    case={'query':{'source':'yousician','model_id':active['yousician'],'instrument':'ukulele','query_time':5,
          'history':[{'time':t,'observations':[{'concept':0,'score':.5}]} for t in range(4)]},
          'plot_history':[{'group':i+1,'score':.5} for i in range(4)],
          'provenance':{'kind':'unit_test_fixture'},'observed_target':{'0':.31},
          'private_learner_id':'NEVER_RETURN_THIS'}
    (folder/'yousician.json').write_text(json.dumps(case))
    app=FastAPI();app.include_router(demo.router)
    return TestClient(app),folder/'yousician.json'


def test_result_not_sent_until_after_actual_prediction(api):
    client,_=api
    h=client.get('/api/v6/o08/demo/history?source=yousician').json()
    assert 'observed_target' not in h and 'query' not in h
    assert 'NEVER_RETURN_THIS' not in json.dumps(h)
    assert client.post('/api/v6/o08/demo/reveal',json={'receipt':h['receipt']}).status_code==409
    p=client.post('/api/v6/o08/demo/predict',json={'receipt':h['receipt']}).json()
    assert p['forecast']['predictions'] and 'observed_target' not in p
    assert p['technical']['future_target_in_input'] is False
    r=client.post('/api/v6/o08/demo/reveal',json={'receipt':p['reveal_receipt']}).json()
    assert r['observed_target']=={'0':.31}
    assert r['model_sha256']==p['technical']['model_sha256']
    assert r['comparison'][0]['absolute_error']==pytest.approx(abs(p['forecast']['predictions']['0']-.31))


def test_receipt_tampering_and_case_change_rejected(api):
    client,path=api
    h=client.get('/api/v6/o08/demo/history?source=yousician').json()
    assert client.post('/api/v6/o08/demo/predict',json={'receipt':h['receipt']+'x'}).status_code==409
    content=json.loads(path.read_text());content['observed_target']['0']=.99;path.write_text(json.dumps(content))
    assert client.post('/api/v6/o08/demo/predict',json={'receipt':h['receipt']}).status_code==409
    # A new ticket still yields the same prediction with a different held-out label.
    h2=client.get('/api/v6/o08/demo/history?source=yousician').json()
    p2=client.post('/api/v6/o08/demo/predict',json={'receipt':h2['receipt']}).json()
    content['observed_target']['0']=.01;path.write_text(json.dumps(content))
    h3=client.get('/api/v6/o08/demo/history?source=yousician').json()
    p3=client.post('/api/v6/o08/demo/predict',json={'receipt':h3['receipt']}).json()
    assert p2['forecast']['predictions']==p3['forecast']['predictions']
