import copy,json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import numpy as np
import pytest
from jsonschema import Draft202012Validator
from axis7.schema import Attempt,SkillObservation
from axis7.contracts import AttemptV2
from axis7.adapters import mock_axis_event,example_workflow
from axis7.models import Baseline
from axis7.inference import TwinEngine,Predictor
from axis7.storage import append_event,EventConflict
from axis7 import server
from fastapi.testclient import TestClient

def event(**updates):
    payload=mock_axis_event(1,'v2-learner','v2-event','2026-06-01T00:00:00Z').model_dump(mode='json')
    payload.update(updates);return payload

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB',tmp_path/'events.sqlite')
    return TestClient(server.app)

@pytest.mark.parametrize('bad',[{'skill_id':'pitch','outcome':2},{'skill_id':'pitch'},{'skill_id':'pitch','outcome':None}])
def test_published_observation_contract_and_runtime_reject_invalid_targets(bad):
    assert list(Draft202012Validator(SkillObservation.model_json_schema()).iter_errors(bad))
    with pytest.raises(ValueError):SkillObservation.model_validate(bad)

@pytest.mark.parametrize('run',['dkt-7','sakt-7','bkt-0','pfa-0'])
def test_observation_only_and_excluded_events_are_exact_forecast_noops(run):
    e=TwinEngine('music-mock');rows=next(iter(e.learners.values()))[:12]
    p=Predictor(e.directory,run);before=p.probabilities(rows)[-1]
    for obs in [[{'k':0,'y':None,'score':.8}], [{'k':0,'y':1,'eligible':False}], [{'k':None,'y':1,'eligible':False}]]:
        after=p.probabilities(rows+[{'obs':obs}])[-1]
        np.testing.assert_array_equal(before,after)

@pytest.mark.parametrize('count',[1,3,45,500])
def test_bkt_group_posterior_matches_stable_likelihood(count):
    m,T,G,S=.5,.08,.2,.1
    posterior=1/(1+((1-m)/m)*(G/(1-S))**count)
    assert Baseline.update(m,[1]*count,T,G,S)==pytest.approx(posterior+(1-posterior)*T,abs=1e-12)
    assert np.isfinite(Baseline.group_log_likelihood(m,[1]*count,G,S))

def test_bkt_joint_group_likelihood_is_not_product_of_marginals():
    assert np.exp(Baseline.group_log_likelihood(.5,[1,0],.2,.1))==pytest.approx(.5*.9*.1+.5*.2*.8)

def test_retry_same_event_is_idempotent_changed_payload_conflicts(client):
    p=event();first=client.post('/api/v2/events',json=p);second=client.post('/api/v2/events',json=p)
    assert first.status_code==second.status_code==200
    assert not first.json()['idempotent_replay'] and second.json()['idempotent_replay']
    assert second.json()['twin']['total_groups']==1
    changed=copy.deepcopy(p);changed['observations'][0]['outcome']=0
    assert client.post('/api/v2/events',json=changed).status_code==409

def test_acceptance_remains_acknowledged_if_inference_fails(client,monkeypatch):
    engine=server.engine('music-mock')
    monkeypatch.setattr(engine,'snapshot',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('test failure')))
    response=client.post('/api/v2/events',json=event()).json()
    assert response['status']=='accepted' and response['forecast_status']=='unavailable'
    assert response['twin'] is None and response['forecast_error']['retryable']
    assert client.post('/api/v2/events',json=event()).json()['idempotent_replay']

@pytest.mark.parametrize('change,reason',[
    ({'rubric_version':'not-compatible'},'unsupported_rubric'),
    ({'source_confidence':None},'missing_source_confidence'),
    ({'source_confidence':.2},'low_source_confidence'),
    ({'model_update_requested':False},'observation_only')])
def test_update_eligibility_is_explicit_not_silent(client,change,reason):
    p=event()
    if 'rubric_version' in change:p.update(change)
    else:p['observations'][0].update(change)
    result=client.post('/api/v2/events',json=p).json()
    assert result['eligible_observations']==0
    assert result['record']['obs'][0]['eligibility_reason']==reason
    assert result['twin']['model_update_events']==0

def test_chronological_transaction_rolls_back_invalid_append(client):
    assert client.post('/api/v2/events',json=event()).status_code==200
    older=event(attempt_id='old',timestamp='2026-05-01T00:00:00Z')
    assert client.post('/api/v2/events',json=older).status_code==422
    assert client.get('/api/twin/v2-learner').json()['total_groups']==1

def test_concurrent_duplicate_is_one_stored_event(tmp_path):
    from axis7.contracts import resolve_event
    from axis7.schema import MUSIC_SKILLS
    record=resolve_event(AttemptV2.model_validate(event()),MUSIC_SKILLS)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:append_event(tmp_path/'db.sqlite',copy.deepcopy(record),[],set()),range(4)))
    assert sum(not replay for _,replay in results)==1

def test_six_mock_adapters_retain_unmodeled_context_without_fake_updates(client):
    for p in example_workflow():
        response=client.post('/api/v2/events',json=p)
        assert response.status_code==200,response.text
    snapshot=client.get('/api/twin/team-demo').json()
    assert snapshot['total_groups']==6 and snapshot['model_update_events']==4
    assert snapshot['unmodeled_observations']==1
    assert client.get('/api/v2/registry').json()['taxonomy_status']=='provisional_not_teacher_validated'

@pytest.mark.parametrize('architecture',['dkt','sakt'])
def test_bounded_long_history_preserves_causality_and_noop_alignment(architecture):
    from axis7.models import new_neural,neural_predict
    from axis7.data import generate_music
    model=new_neural(architecture,6,16,8)
    rows=next(iter(generate_music(students=1,sessions=8)[0].values()))
    changed=copy.deepcopy(rows)
    for row in changed[18:]:
        for obs in row['obs']:obs['y']=1-obs['y']
    original=neural_predict(model,rows,6,query=True)
    assert original.shape==(len(rows)+1,6)
    np.testing.assert_allclose(original[:19],neural_predict(model,changed,6,query=True)[:19],atol=1e-7)
    extra=copy.deepcopy(rows);extra.insert(12,{'obs':[{'k':0,'y':None,'score':.7}]})
    aligned=neural_predict(model,extra,6,query=True)
    np.testing.assert_array_equal(original, np.delete(aligned,13,axis=0))

def test_old_training_command_cannot_overwrite_historical_results():
    from axis7.train import run
    from axis7.data import ROOT
    config=json.loads((ROOT/'configs/experiment.json').read_text(encoding='utf-8'))
    with pytest.raises(FileExistsError):run('forget-se',config)

def test_instrument_context_has_no_fabricated_technique_target(client):
    p=mock_axis_event(6,'instrument-only','instrument-event','2026-06-01T00:00:00Z').model_dump(mode='json')
    assert p['observations']==[]
    response=client.post('/api/v2/events',json=p).json()
    assert response['eligible_observations']==0 and response['twin']['model_update_events']==0
    p['producer_axis']=1
    assert client.post('/api/v2/events',json=p).status_code==422
    assert list(Draft202012Validator(AttemptV2.model_json_schema()).iter_errors(p))

def test_historical_replay_template_uses_actual_latest_instant(client):
    first=event(timestamp='2026-06-01T15:00:00+03:00')
    second=event(attempt_id='later',timestamp='2026-06-01T13:00:00Z')
    assert client.post('/api/v2/events',json=first).status_code==200
    assert client.post('/api/v2/events',json=second).status_code==200
    snapshot=client.get('/api/twin/v2-learner?position=1').json()
    assert snapshot['latest_timestamp']=='2026-06-01T13:00:00+00:00'

def test_generic_replay_does_not_condition_future_exercise():
    class ItemAware:
        K=6;name='item_attention';model=None;config={'implementation_version':'test-v2'}
        def probabilities(self,rows):
            result=np.full((len(rows)+1,6),.2)
            for t,row in enumerate(rows):result[t]=.9 if row['exercise']=='future-item' else .4
            return result
    e=TwinEngine('music-mock');e.predictors['v2:test']=ItemAware()
    rows=copy.deepcopy(next(iter(e.learners.values()))[:4]);rows[2]['exercise']='future-item'
    replay=e.snapshot('replay',rows,position=2,model_id='v2:test')
    assert replay['nodes'][0]['probability']==.2
    changed=copy.deepcopy(rows);changed[2]['exercise']='different-future-item'
    assert replay['nodes']==e.snapshot('replay',changed,position=2,model_id='v2:test')['nodes']
    assert replay['forecast_conditioning']=='unknown_exercise_skill_forecast'

def test_recurring_errors_require_repeated_error_type():
    from axis7.recommendations import recommend
    node={'id':'pitch','label':'Pitch','probability':.5,'seed_range':None,
          'generic_recent_change':-.1,'evidence':[{'outcome':0,'errors':[code]} for code in ['flat','sharp','missed']]}
    assert recommend([node])['repeated_error_fraction']==0
    node['evidence'][1]['errors']=['flat']
    assert recommend([node])['repeated_error_fraction']==pytest.approx(2/3)

def test_forecast_envelope_is_documented_and_validated(client):
    from axis7.responses import ForecastV2
    learner=client.get('/api/learners').json()['learners'][0]['id']
    payload=client.get(f'/api/v2/forecast/{learner}').json()
    ForecastV2.model_validate(payload)
    assert not list(Draft202012Validator(ForecastV2.model_json_schema()).iter_errors(payload))
    assert client.get('/openapi.json').json()['paths']['/api/v2/forecast/{student}']['get']['responses']['200']['content']['application/json']['schema']['$ref'].endswith('ForecastV2')

@pytest.mark.parametrize('invalid',[1234567890,'2026-06-01T12:00:00'])
def test_timestamps_reject_numeric_or_missing_timezone(invalid):
    with pytest.raises(ValueError):AttemptV2.model_validate(event(timestamp=invalid))
