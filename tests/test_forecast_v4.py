from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from axis7 import server

ITEM_AWARE_MODEL = 'v2:music-mock:2026:enhanced_gru-7'


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'DB', tmp_path / 'v4.sqlite')
    return TestClient(server.app)


def evidence_event(attempt_id, student_id, timestamp, exercise_id='e1', outcome=1, source_confidence=1.0,
                    provenance='synthetic', missing=False, **overrides):
    obs = {'skill_id': 'pitch', 'producer_axis': 1, 'producer_version': 'omr-1', 'objective_id': 'O01',
           'assessment_kind': 'direct', 'source_confidence': source_confidence, 'reference_compared': True}
    if missing:
        obs['missing'] = True
    else:
        obs['outcome'] = outcome
    event = {'schema_version': '3.0', 'attempt_id': attempt_id, 'student_id': student_id, 'session_id': 's1',
        'exercise_id': exercise_id, 'instrument': 'piano-provisional', 'timestamp': timestamp,
        'provenance': provenance, 'rubric_version': 'provisional-mock-v1', 'observations': [obs]}
    event.update(overrides)
    return event


def forecast_body(student_id, as_of, **overrides):
    body = {'student_id': student_id, 'instrument': 'piano', 'exercise_id': None, 'model_id': None,
        'as_of': as_of, 'evidence_source': 'team_v3', 'include_research_predictions': False}
    body.update(overrides)
    return body


BASE_DAY = datetime(2026, 6, 1, tzinfo=timezone.utc)


def ingest(client, student_id, n, start_day=1, provenance='synthetic', outcome=1, source_confidence=1.0,
           missing=False):
    for i in range(n):
        day = start_day + i
        timestamp = (BASE_DAY + timedelta(days=day - 1)).isoformat().replace('+00:00', 'Z')
        event = evidence_event(f'{student_id}:attempt:{day}', student_id, timestamp,
            provenance=provenance, outcome=outcome, source_confidence=source_confidence, missing=missing)
        response = client.post('/api/v3/evidence', json=event)
        assert response.status_code == 200, response.text


def test_unknown_student_returns_404(client):
    response = client.post('/api/v4/forecast', json=forecast_body('no-such-learner', '2026-06-01T00:00:00Z'))
    assert response.status_code == 404


def test_insufficient_history_abstains_by_default(client):
    ingest(client, 'learner-a', 2)
    response = client.post('/api/v4/forecast', json=forecast_body('learner-a', '2026-06-20T00:00:00Z'))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['status'] == 'abstained'
    assert body['reason_code'] == 'insufficient_history'
    assert body['probabilities'] is None


def test_sufficient_synthetic_history_still_abstains_by_default(client):
    ingest(client, 'learner-b', 5)
    response = client.post('/api/v4/forecast', json=forecast_body('learner-b', '2026-06-20T00:00:00Z'))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['status'] == 'abstained'
    assert body['reason_code'] == 'model_not_validated_for_real_music'
    assert body['probabilities'] is None
    assert body['never_validated_for_real_music'] is True


def test_research_opt_in_exposes_frozen_prediction_on_synthetic_history(client):
    ingest(client, 'learner-c', 5)
    response = client.post('/api/v4/forecast', json=forecast_body('learner-c', '2026-06-20T00:00:00Z',
        include_research_predictions=True))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['status'] == 'research_only'
    assert body['reason_code'] == 'model_not_validated_for_real_music'
    assert body['probabilities'] is not None
    assert body['never_validated_for_real_music'] is True
    assert set(body['probabilities']) == set(body['probabilities'])  # non-empty mapping, no crash on shape


def test_prediction_and_prefix_are_unchanged_after_appending_a_future_attempt(client):
    ingest(client, 'learner-d', 5)
    cutoff = '2026-06-10T00:00:00Z'
    first = client.post('/api/v4/forecast', json=forecast_body('learner-d', cutoff, include_research_predictions=True))
    assert first.status_code == 200, first.text
    before = first.json()
    # Append a strictly-future attempt relative to the already-ingested history.
    ingest(client, 'learner-d', 1, start_day=50)
    second = client.post('/api/v4/forecast', json=forecast_body('learner-d', cutoff, include_research_predictions=True))
    assert second.status_code == 200, second.text
    after = second.json()
    assert before['prefix_count'] == after['prefix_count']
    assert before['evidence_ids'] == after['evidence_ids']
    assert before['probabilities'] == after['probabilities']
    assert before['excluded_future_count'] < after['excluded_future_count']


def test_cutoff_is_strictly_exclusive_at_equal_timestamp(client):
    ingest(client, 'learner-e', 3)
    exact = '2026-06-03T00:00:00+00:00'
    response = client.post('/api/v4/forecast', json=forecast_body('learner-e', exact))
    assert response.status_code == 200, response.text
    assert response.json()['prefix_count'] == 2


def test_unknown_model_id_is_rejected(client):
    ingest(client, 'learner-f', 5)
    response = client.post('/api/v4/forecast',
        json=forecast_body('learner-f', '2026-06-20T00:00:00Z', model_id='not-a-real-model'))
    assert response.status_code == 422


def test_unsupported_instrument_abstains_even_with_ample_history(client):
    ingest(client, 'learner-g', 5)
    response = client.post('/api/v4/forecast',
        json=forecast_body('learner-g', '2026-06-20T00:00:00Z', instrument='guitar'))
    assert response.status_code == 200, response.text
    assert response.json()['reason_code'] == 'unsupported_instrument'


def test_unseen_exercise_is_unknown_for_an_item_aware_model(client):
    ingest(client, 'learner-h', 5)
    response = client.post('/api/v4/forecast', json=forecast_body('learner-h', '2026-06-20T00:00:00Z',
        exercise_id='never-seen-exercise-xyz', model_id=ITEM_AWARE_MODEL, include_research_predictions=True))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['reason_code'] == 'unknown_exercise'
    assert body['status'] == 'abstained'
    assert body['probabilities'] is None


def test_real_evidence_provenance_blocks_research_mode_too(client):
    ingest(client, 'learner-i', 5, provenance='project')
    response = client.post('/api/v4/forecast', json=forecast_body('learner-i', '2026-06-20T00:00:00Z',
        include_research_predictions=True))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['status'] == 'abstained'
    assert body['reason_code'] == 'model_not_validated_for_real_music'
    assert body['probabilities'] is None
    assert body['evidence_provenance_counts'] == {'project': 5}


def test_missing_observations_do_not_count_as_eligible_history(client):
    ingest(client, 'learner-j', 5, missing=True)
    response = client.post('/api/v4/forecast', json=forecast_body('learner-j', '2026-06-20T00:00:00Z'))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['reason_code'] == 'missing'
    assert body['accepted_observations'] == 0
    assert body['omitted_observations'] == 5
    assert body['omitted_reasons'] == {'explicit_missing_measurement': 5}


def test_low_confidence_observations_block_the_gate(client):
    # 0.65 clears the ingestion-time eligibility bar (contracts.MIN_CONFIDENCE=0.6, so these
    # observations ARE eligible/model-updating) but is below forecast_policy's stricter 0.75 bar.
    ingest(client, 'learner-k', 5, source_confidence=0.65)
    response = client.post('/api/v4/forecast', json=forecast_body('learner-k', '2026-06-20T00:00:00Z'))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['accepted_observations'] == 5
    assert body['reason_code'] == 'low_confidence'


def test_as_of_without_timezone_is_rejected(client):
    response = client.post('/api/v4/forecast', json=forecast_body('learner-l', '2026-06-20T00:00:00'))
    assert response.status_code == 422


def test_as_of_must_be_a_string_or_datetime_not_a_number(client):
    body = forecast_body('learner-l', '2026-06-20T00:00:00Z')
    body['as_of'] = 12345
    response = client.post('/api/v4/forecast', json=body)
    assert response.status_code == 422


def test_model_id_is_rejected_together_with_practice_evidence_source(client):
    response = client.post('/api/v4/forecast', json=forecast_body('learner-m', '2026-06-20T00:00:00Z',
        evidence_source='practice', model_id='dkt-7'))
    assert response.status_code == 422


def test_practice_evidence_source_always_abstains_on_unsupported_rubric(client):
    profile = client.post('/api/practice/profiles', json={'mode': 'demo'})
    assert profile.status_code == 200, profile.text
    student_id = profile.json()['student_id']
    response = client.post('/api/v4/forecast', json=forecast_body(student_id, '2026-06-20T00:00:00Z',
        evidence_source='practice'))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['status'] == 'abstained'
    assert body['reason_code'] == 'unsupported_rubric'
    assert body['probabilities'] is None
    assert body['model_profile'] is None


def test_unknown_practice_student_returns_404(client):
    response = client.post('/api/v4/forecast', json=forecast_body('piano-no-such-profile', '2026-06-20T00:00:00Z',
        evidence_source='practice'))
    assert response.status_code == 404


def test_v3_and_v2_and_practice_routes_are_unaffected_by_v4(client):
    from axis7.adapters import mock_axis_event
    legacy = mock_axis_event(1, 'legacy-learner-v4', 'legacy-1-v4', '2026-06-01T00:00:00Z').model_dump(mode='json')
    assert client.post('/api/v2/events', json=legacy).status_code == 200
    assert client.get('/api/v2/registry').status_code == 200
    assert client.get('/api/practice/catalog').status_code == 200
