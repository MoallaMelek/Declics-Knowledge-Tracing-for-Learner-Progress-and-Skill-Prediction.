"""DÉCLIC GRU on SYNTHETIC learners: inputs, causality, isolation from the hidden truth, metrics, API."""
import gzip
import json
import math
import random

import numpy as np
import pytest
from fastapi.testclient import TestClient

from axis7 import cloud_training as ct
from axis7 import learning
from axis7 import sim_api
from axis7 import sim_campaign as sc
from axis7 import sim_models as sm


@pytest.fixture(scope='module')
def campaign(tmp_path_factory):
    out = tmp_path_factory.mktemp('sim') / 'c'
    summary = sc.run_campaign(out, n=12, seed=2, weeks=2, oracle_samples=10, log=lambda m: None)
    data = sm.load_synthetic(out / summary['database'])
    return out, summary, data


@pytest.fixture(scope='module')
def trained(campaign, tmp_path_factory):
    out, summary, data = campaign
    splits = ct.split_learners(data, 42)
    model, cfg = sm.train_gru(data, splits, tmp_path_factory.mktemp('gru'), epochs=2, log=lambda m: None)
    return model, cfg, splits


def test_inputs_are_the_o08_export_of_each_learner(campaign):
    out, summary, data = campaign
    lid = next(iter(data))
    with sc.isolated_app(out / summary['database'], sc.SimClock(), random.Random(0)) as client:
        export = client.get(f'/api/learn/learners/{lid}/export').json()
    rows = sm.o08_rows(data[lid])
    assert export['encode_check']['accepted']
    assert len(rows) == len(export['o08_prepared_rows'])
    for mine, theirs in zip(rows, export['o08_prepared_rows']):
        assert mine['obs'] == theirs['obs'] and mine['time'] == theirs['time']
        # same item key, except the staircase which also states its gap (as Elo's d(cents) does)
        assert mine['exercise'] == theirs['exercise'] or mine['exercise'].startswith(theirs['exercise'] + '@c')


def test_the_stored_elo_and_naive_predictions_precede_each_answer(campaign):
    out, summary, data = campaign
    for history in data.values():
        for h in history:
            assert h['created_at'] < h['answered_at']
            assert h['naive'] is not None


def test_gru_predictions_are_causal(trained, campaign):
    model, cfg, splits = trained
    out, summary, data = campaign
    lid = max(data, key=lambda k: len(data[k]))
    history = data[lid]
    base = sm.predict_gru(model, cfg, history)
    assert base[0] is None and all(p is not None for p in base[1:])
    cut = len(history) // 2
    flipped = [dict(h, y=1 - h['y']) if i >= cut else h for i, h in enumerate(history)]
    after = sm.predict_gru(model, cfg, flipped)
    assert after[:cut + 1] == base[:cut + 1]                 # the future never changes a past prediction
    assert after[cut + 1:] != base[cut + 1:]                 # the past does change the future


def test_the_hidden_truth_never_reaches_the_model(trained, campaign, tmp_path):
    model, cfg, splits = trained
    out, summary, data = campaign
    lid = splits['test'][0]
    before = sm.predict_gru(model, cfg, data[lid])
    # Overwrite the hidden folder: data and predictions must not move.
    hidden = out / 'hidden' / 'items.jsonl.gz'
    saved = hidden.read_bytes()
    try:
        with gzip.open(hidden, 'wt') as f:
            f.write('')
        data2 = sm.load_synthetic(out / summary['database'])
        assert data2 == data
        assert sm.predict_gru(model, cfg, data2[lid]) == before
    finally:
        hidden.write_bytes(saved)
    assert 'p_true' not in json.dumps(cfg) and 'sigma' not in json.dumps(cfg['items'])


def test_splits_never_share_a_learner(trained):
    model, cfg, splits = trained
    sets = [set(v) for v in splits.values()]
    assert all(not (a & b) for i, a in enumerate(sets) for b in sets[i + 1:])
    assert cfg['learners'] == {k: len(v) for k, v in splits.items()}


def test_comparison_uses_the_same_questions_for_every_model(trained, campaign):
    model, cfg, splits = trained
    out, summary, data = campaign
    items, learners = sm.hidden_truth(out)
    rows = sm.question_table(data, list(data), model, cfg, items, learners)
    result = sm.compare(rows, replicates=50)
    common = [r for r in rows if all(r[k] is not None for k in sm.MODELS)]
    assert result['common']['questions'] == len(common)
    for k in sm.MODELS:
        m = result['common']['metrics'][k]
        assert m['n'] == len(common)
        assert m['brier'] == pytest.approx(np.mean([(r[k] - r['y']) ** 2 for r in common]))
        lo, hi = result['common']['bootstrap'][k]['brier']
        assert lo <= m['brier'] <= hi
    assert result['own_coverage']['naive']['coverage'] == 1.0
    assert result['own_coverage']['elo']['coverage'] < 1.0       # Elo abstains before 5 answers per skill
    assert 0 <= result['truth_recovery']['oracle']['brier'] < 0.25
    # where Elo abstains, only the GRU and the naive baseline are scored, on exactly those questions
    early = [r for r in rows if r['elo'] is None and r['gru'] is not None]
    assert result['elo_abstains']['questions'] == len(early)
    assert set(result['elo_abstains']['metrics']) == {'gru', 'naive'}
    # Elo − GRU distance to the hidden probability comes with its own learner interval
    d = result['common']['bootstrap']['differences']['elo-gru:to_truth']
    assert d['ci95'][0] <= d['point'] <= d['ci95'][1]
    for sl_ in sm.slices(rows):
        for r in sl_['rows']:
            assert ('elo_minus_gru' in r) == (r['learners'] >= 5)


def test_bootstrap_resamples_whole_learners():
    rows = [{'learner': 'a', 'y': 1, 'elo': 0.9, 'gru': 0.1, 'naive': 0.5, 'p_true': None}] * 50 + \
           [{'learner': 'b', 'y': 0, 'elo': 0.1, 'gru': 0.9, 'naive': 0.5, 'p_true': None}] * 50
    out = sm.bootstrap(rows, ['elo', 'gru', 'naive'], replicates=200)
    assert out['differences']['elo-gru:brier']['ci95'][1] < 0      # Elo clearly better on both learners


def test_the_real_database_name_is_refused_by_the_loader(tmp_path):
    import sqlite3
    db = tmp_path / 'synthetic-x.sqlite'
    with sqlite3.connect(db) as conn:
        conn.executescript('CREATE TABLE learners(id TEXT, name TEXT); CREATE TABLE items(id TEXT, learner TEXT, session TEXT, seq INT, exercise TEXT, level INT, skill TEXT, created_at TEXT, answered_at TEXT, correct INT, served TEXT, prediction TEXT);')
        conn.execute("INSERT INTO learners VALUES('x', 'Melek')")
    with pytest.raises(ValueError):
        sm.load_synthetic(db)


def test_sim_api_serves_only_the_study_files(tmp_path, monkeypatch):
    monkeypatch.setattr(sim_api, 'BASE', tmp_path)
    from axis7.server import app
    client = TestClient(app)
    assert client.get('/api/sim/studies').json() == {'synthetic': True, 'studies': []}
    assert client.get('/api/sim/../../etc/overview').status_code == 404
    (tmp_path / 's1' / 'ui').mkdir(parents=True)
    (tmp_path / 's1' / 'inspection.json').write_text(json.dumps({'A1': {'n': 2}}))
    with gzip.open(tmp_path / 's1' / 'ui' / 'A1-explorer.json.gz', 'wt') as f:
        json.dump({'campaign': 'A1', 'note': 'n', 'skills': [], 'question_columns': [],
                   'learners': [{'sim_id': 'A1-0001', 'family': 'irregulier', 'family_label': 'Irrégulier', 'days': [[0, 'a', 1, []]],
                                 'questions': [[0, 0.1, 'lecture', 1, 'lecture', 1, None, 0.5, None, 0.6]]}]}, f)
    assert client.get('/api/sim/studies').json()['studies'][0]['id'] == 's1'
    ov = client.get('/api/sim/s1/overview').json()
    assert ov['synthetic'] is True and ov['inspection'] == {'A1': {'n': 2}} and ov['main'] is None
    assert client.get('/api/sim/s1/learners').json()['learners'][0]['correct_rate'] == 1.0
    assert client.get('/api/sim/s1/learner/A1-0001').json()['family'] == 'irregulier'
    assert client.get('/api/sim/s1/learner/nobody').status_code == 404
