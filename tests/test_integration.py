import copy
import json
import numpy as np
import pytest
from fastapi.testclient import TestClient
from axis7 import server
from axis7.inference import TwinEngine, Predictor
from test_causality import valid_attempt

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server,'DB',tmp_path/'events.sqlite')
    return TestClient(server.app)

def test_project_observation_creates_learner_and_survives_engine_reload(client):
    payload=valid_attempt();payload['student_id']='integration-new-learner'
    response=client.post('/api/attempts',json=payload)
    assert response.status_code==200, response.text
    snapshot=response.json()['twin']
    assert snapshot['total_groups']==1
    assert snapshot['provenance_counts']=={'project':1}
    assert snapshot['nodes'][0]['observations']==1
    assert snapshot['recommendation']['status']=='insufficient_evidence'
    # Persisted data must remain usable independently of the engine cache.
    server.engines.pop('music-mock',None)
    assert client.get('/api/twin/integration-new-learner').json()['total_groups']==1
    assert client.post('/api/attempts',json=payload).status_code==422
    payload['attempt_id']='old';payload['timestamp']='2025-01-01T00:00:00Z'
    assert client.post('/api/attempts',json=payload).status_code==422
    payload['attempt_id']='unknown';payload['timestamp']='2027-01-01T00:00:00Z'
    payload['observations'][0]['skill_id']='unvalidated-skill'
    assert client.post('/api/attempts',json=payload).status_code==422
    assert client.get('/api/twin/integration-new-learner').json()['total_groups']==1

def test_simulated_session_updates_predictions_and_reset_restores_history(client):
    learner=client.get('/api/learners').json()['learners'][0]['id']
    before=client.get(f'/api/twin/{learner}').json()
    response=client.post('/api/simulate',json={'student_id':learner,'skill_id':'rhythm','scenario':'success'})
    assert response.status_code==200,response.text
    after=response.json()['twin']
    assert after['total_groups']==before['total_groups']+1
    assert after['nodes'][1]['observations']==before['nodes'][1]['observations']+4
    assert [n['probability'] for n in after['nodes']] != [n['probability'] for n in before['nodes']]
    assert client.post(f'/api/reset/{learner}').status_code==200
    restored=client.get(f'/api/twin/{learner}').json()
    np.testing.assert_allclose([n['probability'] for n in restored['nodes']], [n['probability'] for n in before['nodes']],atol=1e-7)

@pytest.mark.parametrize('model_id',['dkt-7','sakt-7','pfa-0'])
def test_saved_predictor_reload_and_displayed_prefix_are_reproducible(model_id):
    e=TwinEngine('music-mock');student=next(iter(e.learners));rows=e.learners[student]
    changed=copy.deepcopy(rows)
    for r in changed[8:]:
        for o in r['obs']:o['y']=1-o['y']
    first=e.snapshot(student,rows,position=8,model_id=model_id)
    later=e.snapshot(student,changed,position=8,model_id=model_id)
    np.testing.assert_allclose([n['probability'] for n in first['nodes']],[n['probability'] for n in later['nodes']],atol=1e-7)
    reloaded=Predictor(e.directory,model_id)
    np.testing.assert_allclose(e.predictors[model_id].probabilities(rows),reloaded.probabilities(rows),atol=1e-7)

def test_non_finite_measurement_is_rejected_before_any_persistence(client):
    # Python's json module accepts NaN literals; the response must still be a clean 422, not a server crash.
    payload=valid_attempt();payload['student_id']='integration-nan';payload['timing_mae_ms']=float('nan')
    response=client.post('/api/attempts',content=json.dumps(payload,allow_nan=True),headers={'content-type':'application/json'})
    assert response.status_code==422
    assert client.get('/api/twin/integration-nan').status_code==404

def test_attempt_id_is_unique_across_learners_with_a_clear_message(client):
    first=valid_attempt();first['student_id']='integration-a';first['attempt_id']='shared-id'
    assert client.post('/api/attempts',json=first).status_code==200
    second=valid_attempt();second['student_id']='integration-b';second['attempt_id']='shared-id'
    response=client.post('/api/attempts',json=second)
    assert response.status_code==422 and 'already exists' in response.json()['detail']
    assert client.get('/api/twin/integration-b').status_code==404

def test_misspelled_observation_field_is_refused_not_silently_dropped(client):
    payload=valid_attempt();payload['student_id']='integration-typo';payload['timing_ms']=5
    assert client.post('/api/attempts',json=payload).status_code==422
    assert client.get('/api/twin/integration-typo').status_code==404

def test_reset_removes_a_learner_created_only_by_ingestion(client):
    payload=valid_attempt();payload['student_id']='integration-temporary'
    assert client.post('/api/attempts',json=payload).status_code==200
    assert 'integration-temporary' in [v['id'] for v in client.get('/api/learners').json()['learners']]
    assert client.post('/api/reset/integration-temporary').status_code==200
    assert 'integration-temporary' not in [v['id'] for v in client.get('/api/learners').json()['learners']]
    assert client.get('/api/twin/integration-temporary').status_code==404

def test_simulation_for_unknown_learner_is_not_found(client):
    assert client.post('/api/simulate',json={'student_id':'no-such-learner','skill_id':'rhythm'}).status_code==404
