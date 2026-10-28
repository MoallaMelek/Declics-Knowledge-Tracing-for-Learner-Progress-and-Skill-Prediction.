import copy
import pytest
from fastapi.testclient import TestClient
from axis7 import server
from axis7.team_v3 import AttemptV3

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB',tmp_path/'v3.sqlite')
    return TestClient(server.app)

def base_event(attempt_id='v3:1',student_id='v3-learner',timestamp='2026-06-01T00:00:00Z',**overrides):
    event={'schema_version':'3.0','attempt_id':attempt_id,'student_id':student_id,'session_id':'s1',
        'exercise_id':'e1','instrument':'piano-provisional','timestamp':timestamp,'provenance':'synthetic',
        'rubric_version':'provisional-mock-v1',
        'observations':[{'skill_id':'pitch','producer_axis':1,'producer_version':'omr-1','objective_id':'O01',
            'assessment_kind':'direct','outcome':1,'source_confidence':1.0,'reference_compared':True}]}
    event.update(overrides)
    return event

def test_atomic_multi_producer_attempt_is_merged_into_one_stored_record(client):
    event=base_event(observations=[
        {'skill_id':'pitch','producer_axis':1,'producer_version':'omr-1','objective_id':'O01',
         'assessment_kind':'direct','outcome':1,'source_confidence':1.0,'reference_compared':True},
        {'skill_id':'rhythm','producer_axis':2,'producer_version':'timing-1','objective_id':'O02',
         'assessment_kind':'direct','outcome':0,'source_confidence':0.9},
        {'skill_id':'omr_metadata','producer_axis':3,'producer_version':'omr-1','objective_id':'O04',
         'assessment_kind':'context','score':0.9,'source_confidence':1.0},
    ])
    response=client.post('/api/v3/evidence',json=event)
    assert response.status_code==200,response.text
    body=response.json()
    assert body['eligible_observations']==2
    assert {p['axis'] for p in body['producers']}=={1,2,3}
    assert client.get('/api/twin/v3-learner').json()['total_groups']==1

def test_unsupported_identifiers_are_always_context_only_regardless_of_assessment_kind(client):
    for i,(skill_id,axis,objective,kind) in enumerate([('omr_metadata',3,'O04','inferred'),
            ('corrective_feedback',4,'O08','recommendation'),('instrument_context',6,'O10','context')]):
        event=base_event(attempt_id=f'ctx:{skill_id}',timestamp=f'2026-06-01T00:0{i}:00Z',observations=[
            {'skill_id':skill_id,'producer_axis':axis,'producer_version':'v1','objective_id':objective,
             'assessment_kind':kind,'missing':True}])
        response=client.post('/api/v3/evidence',json=event)
        assert response.status_code==200,response.text
        obs=response.json()['record']['obs'][0]
        assert obs['eligible'] is False and obs['eligibility_reason']=='context_only_objective'

def test_missing_measurement_is_explicit_and_never_eligible(client):
    event=base_event(observations=[{'skill_id':'pitch','producer_axis':1,'producer_version':'omr-1',
        'objective_id':'O01','assessment_kind':'direct','missing':True}])
    response=client.post('/api/v3/evidence',json=event)
    assert response.status_code==200,response.text
    obs=response.json()['record']['obs'][0]
    assert obs['eligible'] is False and obs['eligibility_reason']=='explicit_missing_measurement'

@pytest.mark.parametrize('bad_obs',[
    {'skill_id':'pitch','producer_axis':1,'producer_version':'v1','objective_id':'O01',
     'assessment_kind':'direct','outcome':1,'source_confidence':1.0},  # no reference_compared
    {'skill_id':'pitch','producer_axis':1,'producer_version':'v1','objective_id':'O01',
     'assessment_kind':'direct','outcome':1,'source_confidence':1.0,'reference_compared':False},
])
def test_raw_pitch_correctness_without_reference_comparison_is_rejected(client,bad_obs):
    event=base_event(observations=[bad_obs])
    response=client.post('/api/v3/evidence',json=event)
    assert response.status_code==422

def test_objective_id_must_match_the_cached_axis_mapping(client):
    event=base_event(observations=[{'skill_id':'rhythm','producer_axis':2,'producer_version':'v1',
        'objective_id':'O01','assessment_kind':'direct','outcome':1,'source_confidence':1.0}])
    assert client.post('/api/v3/evidence',json=event).status_code==422

def test_context_objective_must_use_its_bounded_skill_id(client):
    event=base_event(observations=[{'skill_id':'pitch','producer_axis':3,'producer_version':'v1',
        'objective_id':'O04','assessment_kind':'context','missing':True}])
    assert client.post('/api/v3/evidence',json=event).status_code==422

def test_axis_seven_cannot_submit_a_direct_observation(client):
    event=base_event(observations=[{'skill_id':'pitch','producer_axis':7,'producer_version':'v1',
        'objective_id':'O09','assessment_kind':'direct','outcome':1,'source_confidence':1.0}])
    assert client.post('/api/v3/evidence',json=event).status_code==422

def test_axis_seven_recommendation_evidence_is_retained_but_never_model_eligible(client):
    event=base_event(observations=[{'skill_id':'pitch','producer_axis':7,'producer_version':'v1',
        'objective_id':'O09','assessment_kind':'recommendation','outcome':1,'source_confidence':1.0}])
    response=client.post('/api/v3/evidence',json=event)
    assert response.status_code==200,response.text
    obs=response.json()['record']['obs'][0]
    assert obs['eligible'] is False and obs['eligibility_reason']=='axis7_self_referential_not_model_update_eligible'

def test_unknown_canonical_skill_is_rejected_by_schema_and_runtime(client):
    event=base_event(observations=[{'skill_id':'unknown-musical-construct','producer_axis':1,
        'producer_version':'v1','objective_id':'O01','assessment_kind':'direct','outcome':1,
        'source_confidence':1.0,'reference_compared':True}])
    assert client.post('/api/v3/evidence',json=event).status_code==422

def test_duplicate_observation_same_producer_and_skill_is_rejected(client):
    event=base_event(observations=[
        {'skill_id':'pitch','producer_axis':1,'producer_version':'v1','objective_id':'O01',
         'assessment_kind':'direct','outcome':1,'source_confidence':1.0,'reference_compared':True},
        {'skill_id':'pitch','producer_axis':1,'producer_version':'v1','objective_id':'O01',
         'assessment_kind':'direct','outcome':0,'source_confidence':1.0,'reference_compared':True},
    ])
    assert client.post('/api/v3/evidence',json=event).status_code==422

def test_idempotent_replay_and_conflict_on_changed_payload(client):
    event=base_event()
    first=client.post('/api/v3/evidence',json=event)
    second=client.post('/api/v3/evidence',json=event)
    assert first.status_code==second.status_code==200
    assert not first.json()['idempotent_replay'] and second.json()['idempotent_replay']
    changed=copy.deepcopy(event);changed['observations'][0]['outcome']=0
    assert client.post('/api/v3/evidence',json=changed).status_code==409

def test_chronology_is_atomic_and_uses_the_single_declared_timestamp(client):
    first=base_event(attempt_id='v3:first',timestamp='2026-06-02T00:00:00Z')
    older=base_event(attempt_id='v3:older',timestamp='2026-06-01T00:00:00Z')
    assert client.post('/api/v3/evidence',json=first).status_code==200
    assert client.post('/api/v3/evidence',json=older).status_code==422

def test_v2_contract_route_is_unaffected_by_v3(client):
    from axis7.adapters import mock_axis_event
    legacy=mock_axis_event(1,'legacy-learner','legacy-1','2026-06-01T00:00:00Z').model_dump(mode='json')
    assert client.post('/api/v2/events',json=legacy).status_code==200

def test_public_provenance_is_rejected_for_v3_same_as_v2(client):
    event=base_event(**{'provenance':'public'})
    assert client.post('/api/v3/evidence',json=event).status_code==422

@pytest.mark.parametrize('invalid_axis',[0,8,True])
def test_producer_axis_is_bounded_and_not_a_boolean(client,invalid_axis):
    event=base_event(observations=[{'skill_id':'pitch','producer_axis':invalid_axis,'producer_version':'v1',
        'objective_id':'O01','assessment_kind':'direct','outcome':1,'source_confidence':1.0,
        'reference_compared':True}])
    assert client.post('/api/v3/evidence',json=event).status_code==422
