"""Virtual learners (SYNTHETIC): perception, learning, forgetting, fatigue, reproducibility, isolation."""
import hashlib
import json
import math
import os
import random
import sqlite3
from pathlib import Path

import pytest

from axis7 import learning, learning_catalog as cat
from axis7 import sim_campaign as sc
from axis7 import sim_learners as sl

ROOT = Path(__file__).resolve().parents[1]


def learner(family='debutant_motive', variant='A', seed=0):
    return sl.make_learner(f't-{family}-{seed}', family, variant, random.Random(seed))


def item(exercise, level, seed=0, cents=None):
    served, answer = cat.generate(exercise, level, random.Random(seed), cents=cents)
    ex = cat.EXERCISE_BY_ID[exercise]
    return {'id': f'x{seed}', 'exercise': exercise, 'level': level, 'skill': ex['skill'], 'served': served}, answer


def accuracy(lrn, exercise, level, n=300, cents=None):
    hits = 0
    rng = random.Random(1)
    for k in range(n):
        it, ans = item(exercise, level, seed=k, cents=cents)
        resp, _ = sl.respond(lrn, it, rng)
        hits += cat.evaluate(exercise, level, it['served'], ans, resp)['correct']
    return hits / n


def test_pitch_accuracy_grows_with_the_gap_and_with_expertise():
    beginner, expert = learner('debutant_motive'), learner('musicien_experimente')
    accs = [accuracy(beginner, 'hauteur-seuil', 1, cents=c) for c in (6, 25, 100, 400)]
    assert accs == sorted(accs) and accs[-1] > 0.9 and accs[0] < 0.75
    assert accuracy(expert, 'hauteur-seuil', 1, cents=12) > accuracy(beginner, 'hauteur-seuil', 1, cents=12) + 0.1


def test_interval_errors_fall_near_the_right_answer():
    lrn = learner('en_difficulte', seed=3)
    rng = random.Random(2)
    distances = []
    for k in range(400):
        it, ans = item('intervalles', 3, seed=k)
        resp, meta = sl.respond(lrn, it, rng)
        if resp['choice'] != ans['value'] and not meta['lapse']:
            distances.append(abs(int(resp['choice']) - int(ans['value'])))
    assert distances, 'a struggling learner must make some errors'
    assert sum(d <= 2 for d in distances) / len(distances) > 0.8   # neighbours, not random picks


def test_harder_levels_are_harder_for_the_same_learner():
    lrn = learner('debutant_motive', seed=5)
    assert accuracy(lrn, 'intervalles', 1) > accuracy(lrn, 'intervalles', 5)
    assert accuracy(lrn, 'melodies', 1) > accuracy(lrn, 'melodies', 5)
    assert accuracy(lrn, 'lecture', 1) > accuracy(lrn, 'lecture', 5)


@pytest.mark.parametrize('variant', ['A', 'B'])
def test_practice_lowers_noise_and_rest_brings_part_of_it_back(variant):
    family = 'debutant_motive'
    lrn = learner(family, variant, seed=4)
    before = lrn.sigma('intervalles')
    for _ in range(200):
        lrn.practise('intervalles', True, True)
    lrn.start_session()                                    # measured rested: fatigue is a within-session effect
    trained = lrn.sigma('intervalles')
    assert trained < before
    assert lrn.practice['accords'] > 0                     # partial transfer to a neighbouring skill
    lrn.rest(30)
    assert trained < lrn.sigma('intervalles') < before     # forgetting, not erasing


def test_fatigue_is_bounded_by_session_length():
    lrn = learner('en_difficulte', seed=1)
    lrn.start_session()
    for _ in range(30):                                    # the longest DÉCLIC session (initial assessment)
        lrn.practise('lecture', True, True)
    assert lrn.fatigue <= 0.25 * 22 / 10 + 1e-9


def test_fatigue_and_lapses_rise_within_a_session():
    lrn = learner('irregulier', seed=2)
    lrn.start_session()
    fresh_sigma, fresh_lapse = lrn.sigma('rythme'), lrn.lapse_now()
    for _ in range(25):
        lrn.practise('lecture', True, True)
    assert lrn.sigma('rythme') > fresh_sigma and lrn.lapse_now() > fresh_lapse
    lrn.start_session()
    assert lrn.fatigue == 0


def test_atypical_family_plateaus_then_takes_off():
    lrn = learner('progression_atypique', 'B', seed=1)
    s0 = lrn.sigma('memoire')
    for _ in range(int(lrn.plateau) - 5):
        lrn.practise('memoire', True, True)
    lrn.start_session()
    assert lrn.sigma('memoire') == pytest.approx(s0)       # nothing yet
    for _ in range(150):
        lrn.practise('memoire', True, True)
    lrn.start_session()
    assert lrn.sigma('memoire') < 0.8 * s0


def test_population_is_reproducible_and_not_made_of_clones():
    a, b = sl.make_population(60, 'A', 7), sl.make_population(60, 'A', 7)
    assert [sl.describe_learner(x) for x in a] == [sl.describe_learner(x) for x in b]
    c = sl.make_population(60, 'A', 8)
    assert [x.sigma0 for x in a] != [x.sigma0 for x in c]
    fam = [x for x in a if x.family == 'debutant_motive']
    assert len({round(x.sigma0['hauteur'], 3) for x in fam}) == len(fam)
    counts = {f: sum(x.family == f for x in a) for f in sl.FAMILIES_A}
    assert sum(counts.values()) == 60 and min(counts.values()) >= 8


def test_responses_only_depend_on_the_public_item():
    lrn = learner('debutant_motive', seed=9)
    for exercise, level in [('intervalles', 2), ('melodies', 3), ('echo', 3), ('pulsation', 2), ('rythme-echo', 3), ('lecture', 5), ('degres', 3), ('cadences', 4), ('accords', 3)]:
        it, answer = item(exercise, level, seed=11)
        assert 'value' not in it['served'] and 'onsets' not in it['served']    # the key is never served
        r1 = sl.respond(lrn, it, random.Random(3))
        r2 = sl.respond(lrn, json.loads(json.dumps(it)), random.Random(3))
        assert r1 == r2


def test_oracle_matches_the_closed_form_for_pitch():
    lrn = learner('debutant_motive', seed=6)
    lrn.lapse = 0.0
    lrn.replay_tendency = 0.0
    it, answer = item('hauteur-seuil', 1, seed=4, cents=20)
    expected = 0.5 * (1 + math.erf((20 / (lrn.sigma('hauteur') / 0.545)) / math.sqrt(2)))
    p = sl.true_success_probability(lrn, it, answer, random.Random(1), samples=3000)
    assert p == pytest.approx(expected, abs=0.03)


def test_the_real_learner_database_is_refused(tmp_path):
    with pytest.raises(PermissionError):
        sc.check_synthetic_path(ROOT / 'runtime/learning.sqlite')
    with pytest.raises(PermissionError):
        sc.check_synthetic_path(tmp_path / 'learning.sqlite')
    assert sc.check_synthetic_path(tmp_path / 'synthetic-x.sqlite').name == 'synthetic-x.sqlite'


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).exists() else None


def _answers(db):
    with sqlite3.connect(db) as conn:
        return conn.execute('''SELECT l.name, i.exercise, i.level, i.correct, i.score, i.prediction, i.answered_at, i.response
                               FROM items i JOIN learners l ON l.id = i.learner WHERE i.answered_at IS NOT NULL
                               ORDER BY l.name, i.answered_at''').fetchall()


def test_campaign_isolation_reproducibility_and_transport_equivalence(tmp_path):
    real = ROOT / 'runtime/learning.sqlite'
    before = _digest(real)
    env, now = os.environ.get('DECLIC_LEARNING_DB'), learning._now
    a = sc.run_campaign(tmp_path / 'a', n=3, seed=3, weeks=1, oracle_samples=10, log=lambda m: None)
    b = sc.run_campaign(tmp_path / 'b', n=3, seed=3, weeks=1, oracle_samples=10, log=lambda m: None)
    h = sc.run_campaign(tmp_path / 'h', n=3, seed=3, weeks=1, oracle_samples=10, transport='http', log=lambda m: None)
    assert _digest(real) == before                                       # « Melek » untouched
    assert os.environ.get('DECLIC_LEARNING_DB') == env and learning._now is now   # production clock restored
    rows = [_answers(tmp_path / x / f'synthetic-A3-n3.sqlite') for x in 'abh']
    assert rows[0] and rows[0] == rows[1] == rows[2]                      # reproducible, and same through HTTP
    assert a['counters'] == b['counters'] == h['counters']
    assert a['counters']['exports_accepted'] == 3
    hidden = (tmp_path / 'a' / 'hidden' / 'items.jsonl.gz')
    assert hidden.exists() and not list((tmp_path / 'a').glob('hidden/*.sqlite'))
    with pytest.raises(FileExistsError):
        sc.run_campaign(tmp_path / 'a', n=3, seed=3, weeks=1, oracle_samples=10, log=lambda m: None)


def test_synthetic_profiles_are_labelled(tmp_path):
    sc.run_campaign(tmp_path / 'c', n=2, seed=1, weeks=1, oracle_samples=5, log=lambda m: None)
    with sqlite3.connect(tmp_path / 'c' / 'synthetic-A1-n2.sqlite') as conn:
        names = [r[0] for r in conn.execute('SELECT name FROM learners')]
    assert names and all(n.startswith('SYNTHÉTIQUE ') for n in names)
