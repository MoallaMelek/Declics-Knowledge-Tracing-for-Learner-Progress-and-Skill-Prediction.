import csv
import gzip
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pytest
import torch

from axis7 import cloud_training as cloud
from axis7 import musical_registry as registry


def fixture_archive(path, times, outcomes=None):
    outcomes = outcomes or [i % 2 for i in range(len(times))]
    a = io.StringIO(); writer = csv.writer(a)
    writer.writerow(['opern_id', 'qc_array']); writer.writerow([1, '[[10],[0]]'])
    b = io.StringIO(); writer = csv.writer(b)
    writer.writerow(['user_id', 'opern_id', 'record_id', 'create_time', 'qa_array'])
    for i, (time, y) in enumerate(zip(times, outcomes)):
        writer.writerow(['private-student', 1, i, time, json.dumps([[10], [y]])])
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('opernDS.csv', a.getvalue()); z.writestr('recordDS.csv', b.getvalue())
    return path


@pytest.mark.parametrize('values', [
    ['2023/8/10 12:00', '2023/8/7 12:00'],
    ['2023/10/1 12:00', '2023/2/1 12:00'],
    ['2024/1/1 00:00', '2023/12/31 23:59'],
    ['2023-08-10T12:00:00', '2023/8/7 12:00'],
])
def test_calendar_order_and_original_provenance(tmp_path, values):
    rows, _ = cloud.load_singpad(fixture_archive(tmp_path/'raw.zip', values))
    assert [cloud.parse_singpad_time(r['time']) for r in rows] == sorted(map(cloud.parse_singpad_time, values))
    assert sorted(t for r in rows for t in r['original_timestamps']) == sorted(values)
    result = cloud.prepare('singpad', tmp_path/'raw.zip', tmp_path/'cache.gz')
    assert result['audit']['chronology']['chronological_inversions'] == 0


def test_equivalent_timestamps_group_before_ordering(tmp_path):
    times = ['2023/8/7 1:05', '2023-08-07T01:05:00', '2023/08/07 01:05', '2023/8/8 01:05']
    rows, audit = cloud.load_singpad(fixture_archive(tmp_path/'raw.zip', times))
    assert len(rows) == 2 and rows[0]['recording_count'] == 3
    assert len(rows[0]['obs']) == 3 and len(rows[0]['original_timestamps']) == 3
    assert audit['recordings'] == 4


@pytest.mark.parametrize('value', ['', '07/08/2023 12:00', '2023/2/29 12:00',
    '2023/8/7 24:00', '2023/8/7 12:60', '2023-08/07 12:00',
    '2023-08-07T12:00:00Z', '2023-08-07T12:00:00+01:00',
    '2023/8/7', ' 2023/8/7 12:00', '2023/8/7 12:00 rubbish', None])
def test_malformed_or_ambiguous_calendar_rejected(value):
    with pytest.raises(ValueError):
        cloud.parse_singpad_time(value)


def test_empty_and_single_recording_are_not_predictive_histories(tmp_path):
    for values in ([], ['2023/8/7 12:00']):
        source = fixture_archive(tmp_path/'raw.zip', values)
        result = cloud.prepare('singpad', source, tmp_path/'cache.gz')
        assert result['learners'] == {}
        assert result['audit']['chronology']['chronological_inversions'] == 0


def test_stale_cache_is_rebuilt_and_corrupt_current_cache_rejected(tmp_path):
    source = fixture_archive(tmp_path/'raw.zip', ['2023/8/10 12:00', '2023/8/7 12:00'])
    cache = tmp_path/'cache.gz'
    old = {'sha256': cloud.digest(source), 'source': 'singpad', 'version': 'musical-cloud-v1',
           'learners': {'private-student': []}}
    with gzip.open(cache, 'wt') as f: json.dump(old, f)
    current = cloud.prepare('singpad', source, cache)
    assert current['version'] == cloud.VERSION
    assert current['preprocessing'] == cloud.PREPROCESSING['singpad']
    current['learners']['private-student'].reverse()
    with gzip.open(cache, 'wt') as f: json.dump(current, f)
    with pytest.raises(ValueError, match='chronological'):
        cloud.prepare('singpad', source, cache)


@pytest.mark.parametrize('name', ['dkt', 'enhanced_gru', 'item_attention'])
def test_actual_future_date_cannot_affect_earlier_prediction(tmp_path, name):
    times = ['2023/8/10 12:00', '2023/8/7 12:00', '2023/8/8 12:00']
    first, _ = cloud.load_singpad(fixture_archive(tmp_path/'a.zip', times, [0, 1, 0]))
    changed, _ = cloud.load_singpad(fixture_archive(tmp_path/'b.zip', times, [1, 1, 0]))
    a = cloud.encode(first, 1, {'1': 1}); b = cloud.encode(changed, 1, {'1': 1})
    model = cloud.model_for(name, 1, {'1': 1}, 16, 8).eval()
    inputs = lambda v: [torch.from_numpy(x).unsqueeze(0) for x in v]
    with torch.no_grad():
        pa = cloud.forward(model, name, inputs(a)); pb = cloud.forward(model, name, inputs(b))
    torch.testing.assert_close(pa, pb, rtol=0, atol=0)
    assert first[-1]['obs'] != changed[-1]['obs']


def test_phase5_singpad_weights_cannot_be_imported_even_without_gate():
    root = Path(__file__).resolve().parents[1]
    old = root/'artifacts/models/phase5-cloud/singpad/item_attention'
    if not old.exists(): pytest.skip('Historical artifact not present')
    with pytest.raises(ValueError, match='chronology'):
        registry.validate(old, require_gate=False)


def test_old_checkpoint_config_cannot_resume_new_preprocessing(tmp_path):
    source = fixture_archive(tmp_path/'raw.zip', ['2023/8/7 12:00', '2023/8/10 12:00'])
    # Use ten learners to reach the config-compatibility check.
    def fake_prepare(*args):
        rows, _ = cloud.load_singpad(source)
        return {'learners': {str(i): rows for i in range(10)}, 'sha256': cloud.digest(source), 'audit': {}}
    from unittest.mock import patch
    cloud.save_resume(tmp_path/'out', {'config': {'version': 'musical-cloud-v1'}})
    with patch.object(cloud, 'prepare', fake_prepare), pytest.raises(ValueError, match='mismatch'):
        cloud.train('singpad', source, tmp_path/'out', epochs=1)


def test_dataset_wide_strict_increasing_audit():
    audit = cloud.chronological_audit({'x': [{'time': '2023/8/10 12:00'}, {'time': '2023/8/7 12:00'},
                                         {'time': '2023-08-07T12:00:00'}]})
    assert audit['chronological_inversions'] == 1 and audit['duplicate_time_groups'] == 1
    assert cloud.chronological_audit({})['time_groups'] == 0
