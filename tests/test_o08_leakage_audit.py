"""Phase 10 audit of the ACTIVE O08 networks (the ones the application serves).

1. Future groups sent with a request cannot change a forecast (no leakage through the API).
2. Earlier outcomes do change it (the network really uses the attempt sequence).
3. Train/validation/test splits are by learner, with distinct digests (checked by the registry).
4. A DÉCLIC learner-loop answer cannot be sent to them: the domain contract abstains.
"""
import json
from pathlib import Path

import pytest

from axis7 import musical_registry as registry
from axis7.musical_api import BenchmarkQuery, forecast_with_model

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = json.loads((ROOT / 'artifacts/models/musical-cloud/active.json').read_text())


def _singpad_history(scores):
    return [{'time': f'2021-03-0{d + 1}T10:00:00', 'exercise': '250',
             'observations': [{'concept': 3, 'score': s}, {'concept': 7, 'score': 1}]} for d, s in enumerate(scores)]


def _query(source, history, **kw):
    base = {'singpad': dict(instrument='voice', query_time='2021-03-09T10:00:00', exercise='250', concepts=[3, 7]),
            'yousician': dict(instrument='ukulele', query_time=10, concepts=[0])}[source]
    return BenchmarkQuery(source=source, model_id=ACTIVE[source], history=history, **{**base, **kw})


@pytest.mark.parametrize('source', ['singpad', 'yousician'])
def test_active_network_ignores_future_groups_and_uses_past_ones(source):
    if source == 'singpad':
        past, future = _singpad_history([1, 0, 1, 1]), [{'time': '2021-03-09T10:00:00', 'observations': [{'concept': 3, 'score': 0}]},
                                                           {'time': '2021-03-10T10:00:00', 'observations': [{'concept': 3, 'score': 0}]}]
        flipped = _singpad_history([1, 0, 0, 0])
    else:
        past = [{'time': d, 'observations': [{'concept': 0, 'score': s}]} for d, s in enumerate([0.4, 0.6, 0.7, 0.8])]
        future = [{'time': d, 'observations': [{'concept': 0, 'score': 0.0}]} for d in (10, 11)]
        flipped = [{'time': d, 'observations': [{'concept': 0, 'score': s}]} for d, s in enumerate([0.4, 0.6, 0.1, 0.0])]
    a = forecast_with_model(_query(source, past))
    b = forecast_with_model(_query(source, past + future))
    c = forecast_with_model(_query(source, flipped))
    assert a['status'] == 'source_benchmark_only' and a['model_id'] == ACTIVE[source]
    assert a['predictions'] == b['predictions'], 'outcomes at or after the query time leaked into the forecast'
    assert a['predictions'] != c['predictions'], 'the forecast does not depend on the attempt history'


@pytest.mark.parametrize('source', ['singpad', 'yousician'])
def test_active_network_splits_are_by_learner_and_disjoint(source):
    meta, _ = registry.cached_validate(ROOT / 'artifacts/models/musical-cloud' / ACTIVE[source])
    digests = {k: v['sha256'] for k, v in meta['splits'].items()}
    assert set(digests) == {'train', 'validation', 'test'} and len(set(digests.values())) == 3
    assert meta['test']['observed_targets'] > 0


@pytest.mark.parametrize('instrument', ['piano', 'keyboard', 'ukulele'])
def test_a_declic_learner_answer_cannot_be_relabelled_as_singing(instrument):
    q = _query('singpad', _singpad_history([1, 0, 1]), instrument=instrument)
    assert forecast_with_model(q)['status'] == 'abstained'
