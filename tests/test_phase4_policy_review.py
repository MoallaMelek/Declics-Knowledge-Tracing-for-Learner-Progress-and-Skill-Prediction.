from axis7.forecast_policy import PolicyInputs,evaluate

def test_context_events_do_not_satisfy_assessed_attempt_minimum():
    inputs=PolicyInputs(instrument='piano',rubrics=frozenset({'a'}),supported_rubrics=frozenset({'a'}),
        requires_item_check=False,item_known=None,prefix_count=3,eligible_observations=3,
        eligible_attempts=1,recent_confidences=(1,1,1),provenance_counts={'synthetic':3})
    result=evaluate(inputs)
    assert result.reason_code=='insufficient_history' and not result.research_eligible

def test_default_piano_request_cannot_override_stored_guitar_history(tmp_path,monkeypatch):
    from datetime import datetime,timezone,timedelta
    from fastapi.testclient import TestClient
    from axis7 import server
    from axis7.team_v3 import AttemptV3,resolve_event_v3
    monkeypatch.setattr(server,'DB',tmp_path/'instrument.sqlite')
    rows=[]
    for i in range(3):
        body={'attempt_id':f'g{i}','student_id':'guitar-student','session_id':'s','exercise_id':'e',
            'instrument':'guitar','timestamp':(datetime(2026,6,1,tzinfo=timezone.utc)+timedelta(days=i)).isoformat(),
            'provenance':'synthetic','rubric_version':'provisional-mock-v1','observations':[
                {'skill_id':'pitch','producer_axis':1,'producer_version':'explicit-mock',
                 'objective_id':'O01','assessment_kind':'direct','outcome':1,
                 'source_confidence':1.,'reference_compared':True}]}
        rows.append(resolve_event_v3(AttemptV3.model_validate(body),server.engine('music-mock').meta['skills']))
    # Historical/imported rows are an independent trust boundary even when current ingestion rejects guitar.
    monkeypatch.setattr(server,'history',lambda *args,**kwargs:rows)
    with TestClient(server.app) as client:
        result=client.post('/api/v4/forecast',json={'student_id':'guitar-student',
            'as_of':'2026-06-10T00:00:00Z','evidence_source':'team_v3','include_research_predictions':True}).json()
    assert result['status']=='abstained' and result['probabilities'] is None
    assert result['reason_code']=='unsupported_instrument'
    assert result['history_instrument_counts']=={'guitar':3}
