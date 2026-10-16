from datetime import timedelta
import json
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from axis7 import prospective as p
from axis7.server import app

LEARNER='learner_0123456789abcdef'


def consent(path,learner=LEARNER):
    p.grant(path,p.Consent(learner_id=learner,consent_version='pilot-v1',granted=True))


def event(**overrides):
    data={'schema_version':'o08-practice-v1','event_id':'event-1','learner_id':LEARNER,
        'instrument':'piano','exercise_id':'exercise-1','exercise_version':'v1','attempt_id':'attempt-1',
        'session_id':'session-1','occurred_at':p.now()-timedelta(hours=1),'available_at':p.now()-timedelta(minutes=30),
        'assessment_source':'teacher_assessment','producer_version':'v1','score_definition':'custom_unvalidated',
        'scale':'continuous_unit_interval','outcomes':[{'concept':0,'value':.6}],
        'provenance':'real_observation'}
    return p.PracticeEvent(**{**data,**overrides})


def plan():
    return p.Plan(learner_id=LEARNER,attempt_id='next-attempt',instrument='piano',exercise_id='exercise-1',
        exercise_version='v1',not_before=p.now()+timedelta(minutes=10),concepts=[0],
        score_definition='custom_unvalidated',scale='continuous_unit_interval',model_id='unvalidated-piano')


def test_idempotency_conflict_consent_and_delete(tmp_path):
    path=tmp_path/'pilot.sqlite'; e=event()
    with pytest.raises(PermissionError):p.ingest(path,e)
    consent(path)
    assert p.ingest(path,e)['status']=='recorded'
    assert p.ingest(path,e)['status']=='duplicate'
    with pytest.raises(p.Conflict):p.ingest(path,event(outcomes=[{'concept':0,'value':.4}]))
    with pytest.raises(p.Conflict):p.ingest(path,event(event_id='another-id'))
    data=p.export(path,LEARNER)
    assert len(data['events'])==1
    p.erase(path,LEARNER)
    with pytest.raises(PermissionError):p.export(path,LEARNER)
    with p.connection(path) as conn:
        assert conn.execute('SELECT count(*) FROM practice').fetchone()[0]==0
        audit=conn.execute('SELECT * FROM audit').fetchall()
        assert LEARNER not in json.dumps(audit)


def test_prediction_immutable_and_future_not_in_input(tmp_path):
    path=tmp_path/'pilot.sqlite'; consent(path); p.ingest(path,event())
    body=plan(); first=p.record_prediction(path,body)
    assert first['output']['status']=='abstained'
    assert first['output']['predictions'] is None
    assert p.record_prediction(path,body)['prediction_id']==first['prediction_id']
    with pytest.raises(p.Conflict):p.record_prediction(path,body.model_copy(update={'exercise_id':'other'}))
    assert p.export(path,LEARNER)['evaluations'][0]['status']=='awaiting_outcome'


def test_future_and_personal_identifiers_rejected():
    with pytest.raises(ValidationError):event(available_at=p.now()+timedelta(days=1))
    with pytest.raises(ValidationError):event(learner_id='name@example.com')
    with pytest.raises(ValidationError):event(extra_personal_name='Unneeded')


def test_backdated_result_received_late_is_not_available_in_previous_forecast(tmp_path):
    path=tmp_path/'pilot.sqlite';consent(path)
    cutoff=p.now();p.ingest(path,event())
    with p.connection(path) as conn:
        assert p.available_history(conn,LEARNER,cutoff)==[]
        assert len(p.available_history(conn,LEARNER,p.now()+timedelta(seconds=1)))==1
    data=p.export(path,LEARNER)
    assert data['event_receipts'][0]['received_at']>=cutoff.isoformat()


def test_access_disabled_by_default_and_cross_learner_private(monkeypatch,tmp_path):
    monkeypatch.setattr(p,'DB',tmp_path/'pilot.sqlite'); monkeypatch.delenv('DECLIC_O08_ADMIN_TOKEN',raising=False)
    client=TestClient(app)
    assert client.get(f'/api/v6/o08/learners/{LEARNER}/export').status_code==503
    monkeypatch.setenv('DECLIC_O08_ADMIN_TOKEN','x'*40)
    assert client.get(f'/api/v6/o08/learners/{LEARNER}/export').status_code==401
    headers={'Authorization':'Bearer '+'x'*40}
    assert client.post('/api/v6/o08/consent',headers=headers,json={'learner_id':LEARNER,'consent_version':'v1','granted':True}).status_code==200
    assert client.get('/api/v6/o08/learners/learner_ffffffffffffffff/export',headers=headers).status_code==403


def test_retention_cascades_predictions_and_events(tmp_path):
    path=tmp_path/'pilot.sqlite'; consent(path); p.ingest(path,event()); p.record_prediction(path,plan())
    with p.connection(path) as conn:
        conn.execute('UPDATE consent SET expires=?',((p.now()-timedelta(days=1)).isoformat(),))
    with pytest.raises(PermissionError):p.export(path,LEARNER)
    with p.connection(path) as conn:
        assert conn.execute('SELECT count(*) FROM consent').fetchone()[0]==0
        assert conn.execute('SELECT count(*) FROM prediction').fetchone()[0]==0
        assert conn.execute('SELECT count(*) FROM practice').fetchone()[0]==0
