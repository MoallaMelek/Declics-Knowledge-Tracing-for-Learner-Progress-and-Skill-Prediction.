from fastapi.testclient import TestClient
from axis7 import server

def test_real_case_study_api_is_sanitized_and_does_not_claim_predictions(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB',tmp_path/'case.sqlite')
    with TestClient(server.app) as client:
        response=client.get('/api/research/music-case-study')
    assert response.status_code==200
    body=response.json()
    assert len(body['records'])==118
    assert body['summary']['real_music_predictive_validity_established'] is False
    assert all(not {'P1_name','P1_age','P1_skill'}&row.keys() for row in body['records'])

def test_notebook_summary_exposes_descriptive_and_prediction_separately(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB',tmp_path/'notebook.sqlite')
    with TestClient(server.app) as client:
        profile=client.post('/api/practice/profiles',json={'mode':'local','local_storage_consent':True}).json()
        for i in range(6):
            response=client.post('/api/practice/sessions',json={'student_id':profile['student_id'],'attempt_id':f'n{i}',
                'exercise_id':'ex-pitch-five-note','timestamp':f'2026-06-{i+1:02d}T00:00:00Z',
                'source':'self' if i<3 else 'teacher','rubric_version':'piano-pilot-v1',
                'ratings':[{'skill_id':'pitch','rating':'needs_work' if i<3 else 'comfortable'}]})
            assert response.status_code==200
        summary=response.json()['summary']
    progress=summary['descriptive_progression'][0]
    assert progress['status']=='recent_observations_only'
    assert progress['assessment_source']=='teacher'
    assert not progress['teacher_confirmed_development']
    assert summary['prediction']['status']=='abstained' and summary['prediction']['probabilities'] is None
    assert summary['recommendation']['prediction_informed'] is False
    assert summary['recommendation']['difficulty_status']=='demonstration_catalogue_not_empirically_estimated'

def test_forecast_preserves_local_provenance_and_teacher_attribution_without_certification(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB',tmp_path/'provenance.sqlite')
    with TestClient(server.app) as client:
        profile=client.post('/api/practice/profiles',json={'mode':'local','local_storage_consent':True}).json()
        client.post('/api/practice/sessions',json={'student_id':profile['student_id'],'attempt_id':'teacher1',
            'exercise_id':'ex-pitch-five-note','timestamp':'2026-06-01T00:00:00Z','source':'teacher',
            'rubric_version':'piano-pilot-v1','ratings':[{'skill_id':'pitch','rating':'comfortable'}]}).raise_for_status()
        result=client.post('/api/v4/forecast',json={'student_id':profile['student_id'],
            'as_of':'2026-06-02T00:00:00Z','evidence_source':'practice'}).json()
    assert result['evidence_provenance_counts']=={'local_real':1}
    assert result['assessment_source_counts']=={'teacher':1}
    assert result['unknown_confidence_count']==1 and result['known_confidence_count']==0
    assert result['calibrated_uncertainty_available'] is False
    assert result['status']=='abstained' and result['probabilities'] is None
