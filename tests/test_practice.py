import pytest
from fastapi.testclient import TestClient
from axis7 import server

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB',tmp_path/'practice.sqlite')
    return TestClient(server.app)

def make_profile(client,mode='local',consent=True):
    return client.post('/api/practice/profiles',json={'mode':mode,'local_storage_consent':consent}).json()

def post_session(client,student_id,attempt_id,rating='developing',exercise_id='ex-pitch-five-note',
                  skill_id='pitch',timestamp='2026-01-01T10:00:00Z',source='self'):
    return client.post('/api/practice/sessions',json={'attempt_id':attempt_id,'student_id':student_id,
        'exercise_id':exercise_id,'timestamp':timestamp,'source':source,'rubric_version':'piano-pilot-v1',
        'ratings':[{'skill_id':skill_id,'rating':rating}]})

def test_catalog_is_a_provisional_demonstration_catalog_not_approved_repertoire(client):
    body=client.get('/api/practice/catalog').json()
    assert body['instrument']=='piano' and body['teacher_approved'] is False
    assert body['rubric_version']=='piano-pilot-v1'
    skill_ids={s['id'] for s in body['skills']}
    assert skill_ids=={'pitch','rhythm','duration','articulation','fingering','score_reading'}
    assert 'timing' not in skill_ids
    for exercise in body['exercises']:
        assert exercise['provenance']=='demonstration_catalog' and exercise['teacher_approved'] is False
        assert exercise['prerequisites']==[] and exercise['instructions']

def test_profile_is_pseudonymous_and_has_no_pii_fields(client):
    with pytest.raises(Exception):
        client.post('/api/practice/profiles',json={'mode':'local','local_storage_consent':True,
            'name':'Real Name'}).raise_for_status()
    profile=make_profile(client)
    assert profile['student_id'].startswith('piano-')
    assert profile['mode']=='local' and profile['privacy_notice_version']=='local-pilot-v1'

def test_local_mode_requires_explicit_consent_demo_is_exempt(client):
    rejected=client.post('/api/practice/profiles',json={'mode':'local','local_storage_consent':False})
    assert rejected.status_code==422
    demo=client.post('/api/practice/profiles',json={'mode':'demo'})
    assert demo.status_code==200

def test_session_rejects_unknown_profile_exercise_and_rubric(client):
    profile=make_profile(client)
    assert client.post('/api/practice/sessions',json={'attempt_id':'a','student_id':'piano-unknown',
        'exercise_id':'ex-pitch-five-note','timestamp':'2026-01-01T10:00:00Z','source':'self',
        'rubric_version':'piano-pilot-v1','ratings':[{'skill_id':'pitch','rating':'developing'}]}).status_code==404
    assert post_session(client,profile['student_id'],'a',exercise_id='unknown-exercise').status_code==404
    assert client.post('/api/practice/sessions',json={'attempt_id':'a','student_id':profile['student_id'],
        'exercise_id':'ex-pitch-five-note','timestamp':'2026-01-01T10:00:00Z','source':'self',
        'rubric_version':'not-a-rubric','ratings':[{'skill_id':'pitch','rating':'developing'}]}).status_code==422

def test_session_rejects_duplicate_skill_and_all_not_assessed_and_unexercised_skill(client):
    profile=make_profile(client)
    sid=profile['student_id']
    dup={'attempt_id':'a','student_id':sid,'exercise_id':'ex-pitch-five-note','timestamp':'2026-01-01T10:00:00Z',
         'source':'self','rubric_version':'piano-pilot-v1',
         'ratings':[{'skill_id':'pitch','rating':'developing'},{'skill_id':'pitch','rating':'comfortable'}]}
    assert client.post('/api/practice/sessions',json=dup).status_code==422
    all_na={**dup,'ratings':[{'skill_id':'pitch','rating':'not_assessed'}]}
    assert client.post('/api/practice/sessions',json=all_na).status_code==422
    wrong_skill={**dup,'ratings':[{'skill_id':'rhythm','rating':'developing'}]}
    assert client.post('/api/practice/sessions',json=wrong_skill).status_code==422

def test_idempotent_replay_same_payload_and_conflicts_on_change_or_wrong_learner(client):
    p1=make_profile(client);p2=make_profile(client)
    first=post_session(client,p1['student_id'],'shared-id')
    assert first.status_code==200 and first.json()['idempotent_replay'] is False
    replay=post_session(client,p1['student_id'],'shared-id')
    assert replay.status_code==200 and replay.json()['idempotent_replay'] is True
    changed=post_session(client,p1['student_id'],'shared-id',rating='comfortable')
    assert changed.status_code==409
    wrong_learner=post_session(client,p2['student_id'],'shared-id')
    assert wrong_learner.status_code==409

def test_timestamps_must_be_strictly_monotone_per_learner(client):
    profile=make_profile(client)
    sid=profile['student_id']
    assert post_session(client,sid,'a1',timestamp='2026-01-02T10:00:00Z').status_code==200
    assert post_session(client,sid,'a2',timestamp='2026-01-01T10:00:00Z').status_code==422
    assert post_session(client,sid,'a2',timestamp='2026-01-02T10:00:00Z').status_code==422

def test_sessions_are_never_model_update_eligible_and_demo_vs_local_provenance_differ(client):
    local=make_profile(client,mode='local');demo=make_profile(client,mode='demo')
    post_session(client,local['student_id'],'a1')
    post_session(client,demo['student_id'],'a1-demo')
    local_summary=client.get(f"/api/practice/summary/{local['student_id']}").json()
    demo_summary=client.get(f"/api/practice/summary/{demo['student_id']}").json()
    assert local_summary['sessions'][0]['model_update_eligible'] is False
    assert local_summary['sessions'][0]['provenance']=='local_real'
    assert demo_summary['sessions'][0]['provenance']=='demo'

def test_summary_requires_three_measured_observations_before_a_trend_status(client):
    profile=make_profile(client)
    sid=profile['student_id']
    post_session(client,sid,'a1',timestamp='2026-01-01T10:00:00Z')
    summary=client.get(f'/api/practice/summary/{sid}').json()
    pitch=next(s for s in summary['skills'] if s['id']=='pitch')
    assert pitch['status']=='insufficient_evidence'
    assert summary['recommendation']['exercise_id']=='ex-pitch-five-note'
    assert summary['recommendation']['evidence']==[]

def test_repeated_needs_work_is_flagged_as_recent_difficulty(client):
    profile=make_profile(client)
    sid=profile['student_id']
    for i,(rating,ts) in enumerate([('comfortable','2026-01-01T10:00:00Z'),
            ('needs_work','2026-01-02T10:00:00Z'),('needs_work','2026-01-03T10:00:00Z')]):
        assert post_session(client,sid,f'a{i}',rating=rating,timestamp=ts).status_code==200
    summary=client.get(f'/api/practice/summary/{sid}').json()
    pitch=next(s for s in summary['skills'] if s['id']=='pitch')
    assert pitch['status']=='recent_difficulty'

def test_improving_requires_six_comparable_same_exercise_ratings_not_mixed_exercises(client):
    profile=make_profile(client)
    sid=profile['student_id']
    ratings=['needs_work','needs_work','needs_work','comfortable','comfortable','comfortable']
    for i,rating in enumerate(ratings):
        ts=f'2026-01-{i+1:02}T10:00:00Z'
        assert post_session(client,sid,f'a{i}',rating=rating,timestamp=ts).status_code==200
    summary=client.get(f'/api/practice/summary/{sid}').json()
    pitch=next(s for s in summary['skills'] if s['id']=='pitch')
    assert pitch['status']=='improving'
    # A seventh rating on a DIFFERENT exercise must not be silently folded into the same trend.
    assert post_session(client,sid,'a-other',rating='comfortable',exercise_id='ex-rhythm-steady-quarters',
        skill_id='rhythm',timestamp='2026-01-10T10:00:00Z').status_code==200
    summary2=client.get(f'/api/practice/summary/{sid}').json()
    rhythm=next(s for s in summary2['skills'] if s['id']=='rhythm')
    assert rhythm['status']=='insufficient_evidence'

def test_recommendation_policies_are_transparent_heuristics_not_model_predictions(client):
    profile=make_profile(client)
    sid=profile['student_id']
    for i,rating in enumerate(['needs_work','needs_work','needs_work']):
        post_session(client,sid,f'a{i}',rating=rating,timestamp=f'2026-01-0{i+1}T10:00:00Z')
    for i,rating in enumerate(['comfortable','comfortable','comfortable']):
        post_session(client,sid,f'b{i}',rating=rating,exercise_id='ex-rhythm-steady-quarters',
            skill_id='rhythm',timestamp=f'2026-02-0{i+1}T10:00:00Z')
    weakest=client.get(f'/api/practice/summary/{sid}?policy=weakest').json()['recommendation']
    assert weakest['used_model_predictions'] is False and weakest['teacher_approved'] is False
    assert weakest['exercise_id']=='ex-pitch-five-note'
    coverage=client.get(f'/api/practice/summary/{sid}?policy=coverage').json()['recommendation']
    assert coverage['exercise_id'] not in ('ex-pitch-five-note','ex-rhythm-steady-quarters')

def test_forecast_is_always_unavailable_for_the_provisional_local_rubric(client):
    profile=make_profile(client)
    summary=client.get(f"/api/practice/summary/{profile['student_id']}").json()
    assert summary['forecast']=={'status':'unavailable',
        'reason':'No validated model for this provisional local collection rubric.'}
    assert summary['taxonomy_status']=='provisional'
    assert summary['collection_status']=='local_notebook_not_validated_dataset'

def test_export_is_scoped_to_one_learner_and_never_claims_training_ready(client):
    p1=make_profile(client);p2=make_profile(client)
    post_session(client,p1['student_id'],'a1')
    post_session(client,p2['student_id'],'b1')
    export=client.get(f"/api/practice/export/{p1['student_id']}").json()
    assert export['schema_version']=='practice-export-1.0'
    assert export['training_ready'] is False
    assert export['rubric']['teacher_approved'] is False
    assert len(export['sessions'])==1 and export['sessions'][0]['attempt_id']=='a1'
    assert export['limitations']

def test_reset_endpoint_does_not_touch_practice_tables(client):
    profile=make_profile(client)
    sid=profile['student_id']
    post_session(client,sid,'a1')
    client.post(f'/api/reset/{sid}')
    summary=client.get(f'/api/practice/summary/{sid}').json()
    assert summary['session_count']==1
