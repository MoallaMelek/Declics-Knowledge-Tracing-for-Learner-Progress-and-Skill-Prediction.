from fastapi.testclient import TestClient
from axis7.server import app
from axis7.prospective_adapter import adapt_v3
from axis7.team_v3 import AttemptV3
from datetime import datetime,timezone
import pytest


def test_body_size_and_no_input_reflection(monkeypatch):
    monkeypatch.setenv('DECLIC_O08_ADMIN_TOKEN','x'*40)
    client=TestClient(app);headers={'Authorization':'Bearer '+'x'*40}
    assert client.post('/api/v6/o08/events',content=b'x'*524289,headers=headers).status_code==413
    response=client.post('/api/v6/o08/events',json={'private_personal_field':'DO_NOT_REFLECT'},headers=headers)
    assert response.status_code==422
    assert 'DO_NOT_REFLECT' not in response.text
    response=client.post('/api/v6/o08/events',content=iter([b'x'*300000,b'x'*300000]),headers=headers)
    assert response.status_code==413


def test_team_adapter_keeps_unvalidated_namespace_and_rejects_simulation():
    event=AttemptV3(attempt_id='attempt-1',student_id='upstream-private-id',session_id='session-1',
        exercise_id='exercise-1',instrument='piano',timestamp='2026-10-01T10:00:00Z',
        provenance='project',rubric_version='team-unvalidated-v1',observations=[
            {'skill_id':'rhythm','producer_axis':2,'producer_version':'v1','objective_id':'O02',
             'assessment_kind':'direct','score':.5}])
    adapted=adapt_v3(event,pseudonym='learner_0123456789abcdef',exercise_version='v1',available_at=datetime.now(timezone.utc))
    assert adapted['events'][0].score_definition=='custom_unvalidated'
    assert adapted['events'][0].assessment_source=='axis_adapter'
    assert 'upstream-private-id' not in adapted['events'][0].model_dump_json()
    with pytest.raises(ValueError):adapt_v3(event.model_copy(update={'provenance':'synthetic'}),pseudonym='learner_0123456789abcdef',exercise_version='v1',available_at=datetime.now(timezone.utc))
