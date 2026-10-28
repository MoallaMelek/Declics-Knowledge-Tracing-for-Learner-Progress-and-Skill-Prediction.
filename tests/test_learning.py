"""Learner loop (Phase 10): the scenarios of the acceptance brief, through the real HTTP API.

The simulated answers are pipeline tests only. They say nothing about learning or about the
reference model's validity on real learners.
"""
from datetime import datetime, timedelta, timezone
import json
import random
import sqlite3

import pytest
from fastapi.testclient import TestClient

from axis7 import learning, learning_catalog as cat, learning_model as lm
from axis7.server import app


class Clock:
    def __init__(self):
        self.t = datetime(2026, 10, 20, 9, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=3)
        return self.t

    def jump(self, **kw):
        self.t += timedelta(**kw)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv('DECLIC_LEARNING_DB', str(tmp_path / 'learning.sqlite'))
    clock = Clock()
    monkeypatch.setattr(learning, '_now', clock)
    return TestClient(app), clock, tmp_path / 'learning.sqlite'


def stored_answer(db, item_id):
    with sqlite3.connect(db) as c:
        return json.loads(c.execute('SELECT answer FROM items WHERE id=?', (item_id,)).fetchone()[0])


def response_for(db, item, correct=True):
    a = stored_answer(db, item['id'])
    ex, served = item['exercise'], item['served']
    kind = cat.EXERCISE_BY_ID[ex]['response']
    if kind == 'choice':
        values = [o['value'] for o in served['options']]
        if ex == 'hauteur-seuil':
            correct = a['cents'] > 30  # a listener whose true threshold is about 30 cents
        return {'choice': a['value'] if correct else next(v for v in values if v != a['value'])}
    if kind == 'staff':
        if correct:
            return {'choice': a['value'], 'accidental': a['accidental']}
        return {'choice': next(l for l in cat.LETTERS if l != a['value']), 'accidental': a['accidental']}
    if kind == 'keyboard':
        notes = list(a['notes'])
        if not correct:
            notes[-1] += 1
        return {'notes': notes}
    if ex == 'pulsation':
        ioi = a['ioi'] * (1.0 if correct else 0.8)
        jitter = random.Random(1)
        return {'taps': [k * ioi + jitter.uniform(-0.01, 0.01) for k in range(a['sync'] + a['cont'])]}
    onsets = [o * 0.62 for o in a['onsets']]
    if not correct:
        onsets = onsets[:-1]
    return {'taps': [3.0 + o for o in onsets]}


def new_learner(client, name='Melek'):
    r = client.post('/api/learn/learners', json={'name': name, 'instrument': 'aucun'})
    assert r.status_code == 200, r.text
    return r.json()['id']


def play(client, db, session_id, correct=lambda i, item: True, limit=None):
    results, n = [], 0
    while limit is None or n < limit:
        r = client.post(f'/api/learn/sessions/{session_id}/next')
        assert r.status_code == 200, r.text
        body = r.json()
        if body['status'] == 'complete':
            break
        item = body['item']
        r = client.post(f"/api/learn/items/{item['id']}/answer", json={'response': response_for(db, item, correct(n, item)), 'response_ms': 1500})
        assert r.status_code == 200, r.text
        results.append(r.json()); n += 1
    return results


def test_new_learner_without_instrument_first_session_is_the_initial_assessment(env):
    client, clock, db = env
    learner = new_learner(client)
    info = client.get(f'/api/learn/learners/{learner}').json()
    assert info['instrument'] == 'aucun' and info['initial_assessment_done'] is False and info['active_session'] is None
    s = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'auto'}).json()
    assert s['resumed'] is False and s['session']['kind'] == 'evaluation'
    assert [b['exercise'] for b in s['session']['plan']][0] == 'hauteur-seuil'
    # every assessment exercise can be done without an instrument
    for b in s['session']['plan']:
        assert cat.EXERCISE_BY_ID[b['exercise']]['response'] in ('choice', 'keyboard', 'tap', 'staff')
    results = play(client, db, s['session']['id'])
    assert len(results) == sum(b['count'] for b in s['session']['plan'])
    assert results[-1]['progress'].get('complete') is True
    summary = client.get(f"/api/learn/sessions/{s['session']['id']}/summary").json()
    staircase = [r for r in results if r['item']['exercise'] == 'hauteur-seuil']
    assert summary['session']['status'] == 'terminee' and summary['correct'] == summary['answered'] - sum(not r['result']['correct'] for r in staircase)
    assert summary['pitch_threshold']['reversals'] >= 2 and 15 <= summary['pitch_threshold']['threshold_cents'] <= 60
    assert summary['next_plan'], 'a next session must be proposed'
    assert client.get(f'/api/learn/learners/{learner}').json()['initial_assessment_done'] is True
    # the next automatic session is a practice session built from the results
    s2 = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'auto'}).json()
    assert s2['session']['kind'] == 'seance' and all(b['reason'] for b in s2['session']['plan'])


def test_success_and_failure_are_scored_on_the_server_with_feedback(env):
    client, clock, db = env
    learner = new_learner(client)
    sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'ciblee', 'exercise': 'intervalles', 'level': 1}).json()['session']['id']
    item = client.post(f'/api/learn/sessions/{sid}/next').json()['item']
    assert set(item['served']) >= {'prompt', 'audio', 'options'}
    assert 'value' not in item['served'], 'the answer must not be served to the browser'
    ok = client.post(f"/api/learn/items/{item['id']}/answer", json={'response': response_for(db, item, True)}).json()
    assert ok['result']['correct'] is True and ok['result']['feedback'].startswith('Bonne réponse')
    item = client.post(f'/api/learn/sessions/{sid}/next').json()['item']
    bad = client.post(f"/api/learn/items/{item['id']}/answer", json={'response': response_for(db, item, False)}).json()
    assert bad['result']['correct'] is False and 'La réponse était' in bad['result']['feedback'] and bad['result']['error_key']


@pytest.mark.parametrize('exercise,level', [(e['id'], lv['level']) for e in cat.EXERCISES for lv in e['levels']])
def test_every_level_of_every_exercise_generates_and_scores_both_ways(exercise, level):
    rng = random.Random(7)
    for _ in range(5):
        served, answer = cat.generate(exercise, level, rng)
        json.dumps(served)
        item = {'id': None, 'exercise': exercise, 'served': served}
        for correct in (True, False):
            response = _local_response(exercise, served, answer, correct)
            result = cat.evaluate(exercise, level, served, answer, response)
            assert result['correct'] is correct, (exercise, level, correct, result)


def _local_response(exercise, served, a, correct):
    kind = cat.EXERCISE_BY_ID[exercise]['response']
    if kind == 'choice':
        values = [o['value'] for o in served['options']]
        return {'choice': a['value'] if correct else next(v for v in values if v != a['value'])}
    if kind == 'staff':
        return {'choice': a['value'] if correct else next(l for l in cat.LETTERS if l != a['value']), 'accidental': a['accidental']}
    if kind == 'keyboard':
        notes = list(a['notes'])
        if not correct:
            notes[-1] += 1
        return {'notes': notes}
    if exercise == 'pulsation':
        ioi = a['ioi'] * (1.0 if correct else 0.8)
        return {'taps': [k * ioi for k in range(a['sync'] + a['cont'])]}
    onsets = [o * 0.62 for o in a['onsets']]
    return {'taps': onsets if correct else onsets[:-1]}


def test_melody_changes_respect_the_announced_contour_rule():
    rng = random.Random(3)
    for level in (1, 2, 3, 4, 5):
        _, lv = cat.level_spec('melodies', level)
        for _ in range(40):
            first = cat._melody(rng, lv['params']['length'], lv['params']['tonal'], 60, 74, 5)
            second, _ = cat._alter(rng, first, lv['params']['contour'], lv['params']['tonal'])
            same = cat._contour(first) == cat._contour(second)
            assert same == (lv['params']['contour'] == 'preserve') and second != first


def test_several_attempts_lead_to_mastery_and_unlock_the_next_step(env):
    client, clock, db = env
    learner = new_learner(client)
    for _ in range(2):
        sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'ciblee', 'exercise': 'hauteur-comparaison', 'level': 1}).json()['session']['id']
        play(client, db, sid)
    p = client.get(f'/api/learn/learners/{learner}/progress').json()
    level1 = next(m for m in p['mastery'] if m['exercise'] == 'hauteur-comparaison' and m['level'] == 1)
    assert level1['status'] == 'maitrise' and level1['attempts'] == 16
    assert p['frontier']['hauteur-comparaison']['level'] == 2


def test_two_choice_mastery_needs_more_than_chance(env):
    hist = [{'exercise': 'hauteur-comparaison', 'level': 1, 'skill': 'hauteur', 'correct': i not in (0, 5), 'answered_at': f'2026-10-20T09:00:{i:02d}.000000+00:00'} for i in range(10)]
    # 8/10 on a 2-choice task is not significant (p = 0.055): not mastered yet
    assert learning.mastery(hist)[('hauteur-comparaison', 1)]['status'] == 'en_cours'
    hist[0]['correct'] = True
    assert learning.mastery(hist)[('hauteur-comparaison', 1)]['status'] == 'maitrise'


def test_failing_learner_gets_consolidation_not_a_harder_level(env):
    client, clock, db = env
    learner = new_learner(client)
    hist = []
    for level in (1, 2):
        for i in range(10):
            hist.append({'exercise': 'melodies', 'level': level, 'skill': 'memoire', 'correct': level == 1 or i == 0,
                         'answered_at': f'2026-10-20T09:{level:02d}:{i:02d}.000000+00:00'})
    plan = learning.plan_session(hist, 'seance', now=datetime(2026, 10, 21, tzinfo=timezone.utc))
    block = next(b for b in plan if b['exercise'] == 'melodies')
    assert block['level'] == 1 and block['reason'].startswith('Consolidation')


def test_interrupted_session_is_resumed_on_the_same_unanswered_item(env):
    client, clock, db = env
    learner = new_learner(client)
    sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'auto'}).json()['session']['id']
    play(client, db, sid, limit=5)
    pending = client.post(f'/api/learn/sessions/{sid}/next').json()['item']
    # browser closed here; the learner comes back later
    clock.jump(hours=20)
    info = client.get(f'/api/learn/learners/{learner}').json()
    assert info['active_session']['id'] == sid and info['active_session']['progress']['answered'] == 5
    again = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'auto'}).json()
    assert again['resumed'] is True and again['session']['current_item']['id'] == pending['id']
    assert client.post(f'/api/learn/sessions/{sid}/next').json()['item']['id'] == pending['id']
    # the prediction stored before the interruption is unchanged
    assert again['session']['current_item']['prediction'] == pending['prediction']


def test_explicit_new_session_interrupts_the_previous_one_without_inventing_failures(env):
    client, clock, db = env
    learner = new_learner(client)
    sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'auto'}).json()['session']['id']
    play(client, db, sid, limit=3)
    client.post(f'/api/learn/sessions/{sid}/next')
    new = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'ciblee', 'exercise': 'lecture', 'level': 1}).json()
    assert new['interrupted'] == [sid]
    summary = client.get(f'/api/learn/sessions/{sid}/summary').json()
    assert summary['session']['status'] == 'interrompue' and summary['answered'] == 3 and summary['unanswered_served'] == 1
    r = client.post(f'/api/learn/sessions/{sid}/next')
    assert r.status_code == 409


def test_return_after_several_days_keeps_history_and_schedules_spaced_review(env):
    client, clock, db = env
    learner = new_learner(client)
    for _ in range(2):
        sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'ciblee', 'exercise': 'lecture', 'level': 1}).json()['session']['id']
        play(client, db, sid)
    clock.jump(days=4)
    p = client.get(f'/api/learn/learners/{learner}/progress').json()
    assert p['days_since_last'] >= 4 and p['totals']['answers'] == 16
    assert (p['next_plan'][0]['exercise'], p['next_plan'][0]['level']) == ('lecture', 2)


def test_fully_mastered_exercise_comes_back_as_spaced_review():
    hist, t = [], datetime(2026, 10, 1, 9, tzinfo=timezone.utc)
    for level in range(1, 6):
        for i in range(10):
            t += timedelta(seconds=5)
            hist.append({'exercise': 'lecture', 'level': level, 'skill': 'lecture', 'correct': True, 'answered_at': learning._iso(t)})
    plan = learning.plan_session(hist, 'seance', now=t + timedelta(days=5))
    review = [b for b in plan if b['exercise'] == 'lecture']
    assert review and review[0]['reason'].startswith('Révision espacée') and '5 jour' in review[0]['reason']


def test_insufficient_data_abstains_and_enough_data_gives_preregistered_predictions(env):
    client, clock, db = env
    learner = new_learner(client)
    sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'ciblee', 'exercise': 'intervalles', 'level': 1}).json()['session']['id']
    results = play(client, db, sid, correct=lambda i, item: i % 3 != 2)
    statuses = [r['item']['prediction']['status'] for r in results]
    assert statuses[:5] == ['abstained'] * 5 and set(statuses[5:]) == {'ok'}
    with sqlite3.connect(db) as c:
        for created, answered, prediction in c.execute('SELECT created_at, answered_at, prediction FROM items'):
            assert json.loads(prediction)['created_at'] == created and created < answered
    p = client.get(f'/api/learn/learners/{learner}/progress').json()
    q = p['o08']['quality']
    assert q['scored'] == 3 and q['brier_model'] is not None and q['calibration'] is None
    assert p['o08']['abstained'] == 5
    assert all(m['status'] == 'abstained' for m in p['o08']['neural_models'])


def test_profile_with_long_history_reports_quality_trend_and_calibration(env):
    client, clock, db = env
    learner = new_learner(client)
    for k in range(5):
        sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'ciblee', 'exercise': 'accords', 'level': 1 + (k > 2)}).json()['session']['id']
        play(client, db, sid, correct=lambda i, item: (i * 7 + k) % 5 != 0)
    q = client.get(f'/api/learn/learners/{learner}/progress').json()['o08']['quality']
    assert q['scored'] == 35 and q['calibration'] and len(q['rolling']) == 3
    assert {'brier_model', 'brier_baseline', 'skill_vs_baseline'} <= set(q)


def test_predictions_use_only_answers_given_before_the_item(env):
    hist = [{'exercise': 'intervalles', 'level': 1, 'skill': 'intervalles', 'correct': True} for _ in range(6)]
    p_before = lm.predict(hist, 'intervalles', 'intervalles', 1)
    future = hist + [{'exercise': 'intervalles', 'level': 1, 'skill': 'intervalles', 'correct': False} for _ in range(6)]
    assert lm.predict(future[:6], 'intervalles', 'intervalles', 1) == p_before
    assert lm.predict(future, 'intervalles', 'intervalles', 1)['p'] < p_before['p']


def test_advanced_levels_are_playable_and_counted(env):
    client, clock, db = env
    learner = new_learner(client)
    for exercise, level in [('intervalles', 5), ('accords', 5), ('melodies', 5), ('echo', 5), ('lecture', 5), ('degres', 4), ('cadences', 4), ('pulsation', 5), ('rythme-echo', 4)]:
        sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'ciblee', 'exercise': exercise, 'level': level}).json()['session']['id']
        play(client, db, sid, limit=2)
    p = client.get(f'/api/learn/learners/{learner}/progress').json()
    assert p['totals']['answers'] == 18


def test_invalid_inputs_are_refused_without_recording_a_failure(env):
    client, clock, db = env
    learner = new_learner(client)
    assert client.post('/api/learn/learners', json={'name': ''}).status_code == 422
    assert client.post('/api/learn/learners', json={'name': 'x', 'role': 'admin'}).status_code == 422
    assert client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'ciblee', 'exercise': 'inconnu', 'level': 1}).status_code == 422
    assert client.post('/api/learn/learners/apprenant-0000/sessions', json={}).status_code == 404
    sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'ciblee', 'exercise': 'pulsation', 'level': 1}).json()['session']['id']
    item = client.post(f'/api/learn/sessions/{sid}/next').json()['item']
    for bad in ({'taps': []}, {'taps': ['a']}, {'taps': [float('nan')]}, {'choice': 'higher'}, {'taps': [0.1] * 500}):
        r = client.post(f"/api/learn/items/{item['id']}/answer", content=json.dumps({'response': bad}, allow_nan=True), headers={'content-type': 'application/json'})
        assert r.status_code == 422, (bad, r.text)
    with sqlite3.connect(db) as c:
        answered, invalid = c.execute('SELECT answered_at, invalid_attempts FROM items WHERE id=?', (item['id'],)).fetchone()
    assert answered is None and invalid >= 3
    ok = client.post(f"/api/learn/items/{item['id']}/answer", json={'response': response_for(db, item, True)})
    assert ok.status_code == 200
    again = client.post(f"/api/learn/items/{item['id']}/answer", json={'response': response_for(db, item, True)})
    assert again.json()['idempotent'] is True
    changed = client.post(f"/api/learn/items/{item['id']}/answer", json={'response': {'taps': [0, 1, 2, 3]}})
    assert changed.status_code == 409
    big = client.post(f"/api/learn/items/{item['id']}/answer", content=b'{"response":{"taps":[' + b'0,' * 40000 + b'0]}}', headers={'content-type': 'application/json'})
    assert big.status_code == 413


def test_reference_model_failure_is_recorded_not_replaced(env, monkeypatch):
    client, clock, db = env
    learner = new_learner(client)
    def boom(*a, **k):
        raise RuntimeError('model down')
    monkeypatch.setattr(lm, 'predict', boom)
    sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'ciblee', 'exercise': 'lecture', 'level': 1}).json()['session']['id']
    item = client.post(f'/api/learn/sessions/{sid}/next').json()['item']
    assert item['prediction']['status'] == 'error' and 'p' not in item['prediction']
    ok = client.post(f"/api/learn/items/{item['id']}/answer", json={'response': response_for(db, item, True)})
    assert ok.status_code == 200 and ok.json()['result']['prediction']['p'] is None
    monkeypatch.undo()


def test_history_persists_on_disk_across_server_restarts(env):
    client, clock, db = env
    learner = new_learner(client)
    sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'ciblee', 'exercise': 'lecture', 'level': 1}).json()['session']['id']
    play(client, db, sid)
    fresh = TestClient(app)
    assert fresh.get('/api/learn/learners').json()['learners'][0]['answers'] == 8
    assert fresh.get(f'/api/learn/learners/{learner}/progress').json()['totals']['answers'] == 8


def test_export_is_accepted_by_the_o08_encoder_and_contains_no_hidden_answers(env):
    client, clock, db = env
    learner = new_learner(client)
    sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'ciblee', 'exercise': 'intervalles', 'level': 1}).json()['session']['id']
    play(client, db, sid)
    e = client.get(f'/api/learn/learners/{learner}/export').json()
    assert e['encode_check']['accepted'] is True and e['encode_check']['features_shape'] == [8, 4 * len(cat.SKILLS)]
    assert len(e['o08_prepared_rows']) == 8 and all(len(r['obs']) == 1 for r in e['o08_prepared_rows'])


def test_catalog_cards_have_the_ten_fields_and_verifiable_difficulty():
    c = TestClient(app).get('/api/learn/catalog').json()
    assert len(c['exercises']) >= 12 and len(c['skills']) == 9
    for card in c['exercises']:
        for field in ('objective', 'skills_assessed', 'difficulty', 'prerequisites', 'instructions', 'inputs', 'expected', 'correction', 'metrics', 'references'):
            assert card[field] not in (None, '', []) or field == 'prerequisites', (card['id'], field)
        assert card['difficulty']['basis'] and all(lv['criteria'] for lv in card['difficulty']['levels'])
        assert all(r['citation'] for r in card['references'])
    purposes = {e['purpose'] for e in c['exercises']}
    assert 'mesurer' in purposes and 'développer' in purposes


def test_staircase_follows_two_down_one_up():
    trials, cents = [], 200.0
    for k in range(30):
        correct = cents > 25  # a listener whose true threshold is 25 cents
        trials.append((cents, correct))
        cents = cat.staircase_threshold(trials)['next_cents']
    est = cat.staircase_threshold(trials)
    assert est['reversals'] >= 4 and 15 <= est['threshold_cents'] <= 40


# ---- regressions from the independent review -------------------------------------------------
def _h(ex, level, skill, results, start=0, session='s1'):
    t = datetime(2026, 10, 20, 9, tzinfo=timezone.utc)
    return [{'exercise': ex, 'level': level, 'skill': skill, 'correct': ok, 'session': session, 'cents': None,
             'answered_at': learning._iso(t + timedelta(seconds=start + i))} for i, ok in enumerate(results)]


def test_mastery_is_judged_on_the_last_answers_and_a_slump_asks_for_consolidation():
    hist = _h('lecture', 1, 'lecture', [True] * 10 + [False] * 10)
    m = learning.mastery(hist)[('lecture', 1)]
    assert m['status'] == 'a_consolider' and m['mastered_at'] and m['recent'] == {'count': 10, 'successes': 0}
    assert learning.frontier(hist)['lecture']['level'] == 1
    plan = learning.plan_session(hist, 'seance', now=datetime(2026, 10, 21, tzinfo=timezone.utc))
    assert any(b['exercise'] == 'lecture' and b['level'] == 1 for b in plan)


def test_pitch_threshold_uses_the_latest_measurement_only_and_needs_four_reversals_to_place():
    def run(session, true_threshold, start):
        trials, cents, out = [], 200.0, []
        for k in range(12):
            ok = cents > true_threshold
            trials.append((cents, ok))
            out.append({'exercise': 'hauteur-seuil', 'level': 1, 'skill': 'hauteur', 'correct': ok, 'cents': cents, 'session': session,
                        'answered_at': learning._iso(datetime(2026, 10, 20, tzinfo=timezone.utc) + timedelta(seconds=start + k))})
            cents = cat.staircase_threshold(trials)['next_cents']
        return out
    first, second = run('a', 80, 0), run('b', 8, 100)
    alone = learning.pitch_threshold(second)
    both = learning.pitch_threshold(first + second)
    assert both['threshold_cents'] == alone['threshold_cents'] and both['session'] == 'b'
    few = learning.pitch_threshold(second[:7])
    if few['reversals'] < 4:
        assert few['placement_cents'] is None and learning.frontier(second[:7])['hauteur-comparaison']['placed_by_threshold'] is None


def test_initial_assessment_stopped_early_is_not_considered_done(env):
    client, clock, db = env
    learner = new_learner(client)
    sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'auto'}).json()['session']['id']
    play(client, db, sid, limit=3)
    client.post(f'/api/learn/sessions/{sid}/finish')
    assert client.get(f'/api/learn/learners/{learner}').json()['initial_assessment_done'] is False
    assert client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'auto'}).json()['session']['kind'] == 'evaluation'


def test_responses_with_unexpected_fields_blank_names_and_inflated_replays_are_handled(env):
    client, clock, db = env
    assert client.post('/api/learn/learners', json={'name': '   '}).status_code == 422
    learner = new_learner(client)
    sid = client.post(f'/api/learn/learners/{learner}/sessions', json={'kind': 'ciblee', 'exercise': 'intervalles', 'level': 1}).json()['session']['id']
    item = client.post(f'/api/learn/sessions/{sid}/next').json()['item']
    bad = {**response_for(db, item, True), 'junk': 'x' * 1000}
    assert client.post(f"/api/learn/items/{item['id']}/answer", json={'response': bad}).status_code == 422
    assert client.post(f"/api/learn/items/{item['id']}/answer", json={'response': response_for(db, item, True), 'replays': 40}).status_code == 200
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT replays FROM items WHERE id=?', (item['id'],)).fetchone()[0] == item['served']['replays']


def test_generated_stimuli_match_their_level_description():
    rng = random.Random(11)
    for level in (1, 2):
        _, lv = cat.level_spec('melodies', level)
        for _ in range(500):
            first = cat._melody(rng, lv['params']['length'], True, 60, 74, 5)
            second, _ = cat._alter(rng, first, 'violate', True)
            assert 0 not in cat._contour(second) and any(a == -b for a, b in zip(cat._contour(first), cat._contour(second)) if a)
    for level in (4, 5):
        _, lv = cat.level_spec('echo', level)
        for _ in range(800):
            served, a = cat.generate('echo', level, rng)
            assert all(0 < abs(y - x) <= lv['params']['max_leap'] for x, y in zip(a['notes'], a['notes'][1:]))


def test_strengths_and_weaknesses_are_relative_to_chance_not_just_a_ranking():
    hist = (_h('rythmes', 1, 'rythme', [True, False, False, True, False, False, True, False])
            + _h('lecture', 1, 'lecture', [False] * 7 + [True], start=100))
    skills, strengths, weaknesses = learning._skill_summary(hist)
    assert strengths == [] and set(weaknesses) == {'rythme', 'lecture'}
    good = _h('lecture', 1, 'lecture', [True] * 9 + [False], start=200)
    _, strengths, weaknesses = learning._skill_summary(good)
    assert strengths == ['lecture'] and weaknesses == []
