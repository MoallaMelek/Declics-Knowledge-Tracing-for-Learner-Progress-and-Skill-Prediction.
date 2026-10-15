import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from axis7 import musical_api, musical_registry as registry


@pytest.fixture
def api(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    registry.install(root/'artifacts/models/phase5/yousician/enhanced_gru', tmp_path)
    monkeypatch.setattr(musical_api,'REGISTRY_ROOT',tmp_path)
    app = FastAPI(); app.include_router(musical_api.router)
    client = TestClient(app)
    active = json.loads((tmp_path/'active.json').read_text())
    body = {'source':'yousician','model_id':active['yousician'],'instrument':'ukulele','query_time':5,
            'history':[{'time':t,'observations':[{'concept':0,'score':.2}]} for t in range(4)]}
    return client, body, tmp_path


def test_inactive_models_cannot_be_requested_directly(api):
    client,body,root = api
    (root/'active.json').write_text('{}')
    response = client.post('/api/v5/musical/forecast',json=body)
    assert response.status_code == 200
    assert response.json()['reason'] == 'inactive_model'


def test_response_defines_target_horizon_and_observed_evidence(api):
    client,body,_ = api
    response = client.post('/api/v5/musical/forecast',json=body).json()
    assert response['definition']['horizon'] == 'prochain jour actif'
    assert response['evidence']['kind'] == 'observed_historical_summary'
    assert response['evidence']['source_concepts'][0]['timestamp_groups'] == 4
    body['history'].append({'time':5,'observations':[{'concept':0,'score':1}]})
    changed = client.post('/api/v5/musical/forecast',json=body).json()
    assert changed['predictions'] == response['predictions']
    assert changed['evidence'] == response['evidence']


def test_cached_models_are_invalidated_by_content_changes(api):
    client,body,root = api
    assert client.post('/api/v5/musical/forecast',json=body).status_code == 200
    folder = root/body['model_id']; path=folder/'metrics.json'
    meta=json.loads(path.read_text());meta['model_sha256']='0'*64
    path.write_text(json.dumps(meta))
    assert client.post('/api/v5/musical/forecast',json=body).status_code == 422


@pytest.mark.parametrize('value', ['2023-02-29T12:00:00','2023-08-07', '2023-08-07T12:00:00Z'])
def test_inference_dates_do_not_guess_missing_or_invalid_information(value):
    with pytest.raises(ValueError):
        musical_api.BenchmarkQuery(source='singpad',model_id='x',instrument='voice',query_time=value,history=[])
