import numpy as np
import pytest
import torch

from axis7 import cloud_training as cloud
from axis7.scientific_validation import historical_predictions, metrics, learner_bootstrap, collect, train_priors


def rows():
    return [{'time': t, 'exercise': '1', 'obs': [[0, float(t % 2), 1.]]} for t in range(8)]


def test_history_controls_use_only_strict_prefix_and_atomic_groups():
    original = rows(); changed = rows()
    changed[4]['obs'] = [[0, 1., 200.]]; changed[5]['obs'] = [[0, 0., 100.]]
    a = historical_predictions(original, 1, .4, np.array([.4]))
    b = historical_predictions(changed, 1, .4, np.array([.4]))
    for name in a:
        np.testing.assert_array_equal(a[name][:5], b[name][:5])
    assert a['previous'][1, 0] == 0 and a['previous'][2, 0] == 1
    assert a['rolling3'][4, 0] == pytest.approx(2/3)


def test_note_weighted_metrics_equal_expanded_individual_labels():
    grouped = metrics([.25, .8], [.3, .7], [4, 5], True)
    expanded = metrics([1]+[0]*3+[1]*4+[0], [.3]*4+[.7]*5, [1]*9, True)
    for key in ('log_loss', 'brier', 'mae_note', 'roc_auc', 'pr_auc'):
        assert grouped[key] == pytest.approx(expanded[key])
    assert grouped['concept_group_targets'] == 2 and grouped['label_weight'] == 9


def test_reliability_bins_partition_boundary_probabilities_once():
    result = metrics([0, 1, 0, 1], [.3, .5, .7, .9], [1, 2, 3, 4], True)
    assert sum(b['label_weight'] for b in result['calibration']) == 10


def test_bootstrap_resamples_learner_clusters_and_paired_losses():
    data = {'y': np.array([0., 0., 1.]), 'w': np.array([1., 9., 1.]),
            'tags': np.array([[0, 1, 0, 0, 0], [0, 2, 0, 0, 0], [1, 1, 0, 0, 0]]),
            'neural': np.array([.2, .2, .8]), 'previous': np.array([.2, .2, .8])}
    result = learner_bootstrap(data, ('neural', 'previous'), False, repeats=200)
    assert result['learners'] == 2
    assert result['paired_neural_minus_control']['previous'] == pytest.approx([0, 0])
    assert result['intervals_95_percent']['neural'] == pytest.approx([.2, .2])


def test_evaluation_collect_matches_training_window_metrics():
    torch.manual_seed(1)
    learners = {'a': rows(), 'b': rows()[:3]}; model = cloud.model_for('enhanced_gru', 1, {'1': 1}, 16, 4)
    mean, prior, _ = train_priors(learners, ['a'], 1)
    data = collect(model, 'enhanced_gru', learners, ['a', 'b'], 1, {'1': 1}, 4, mean, prior)
    result = metrics(data['y'], data['neural'], data['w'], False)
    reference = cloud.measure(model, 'enhanced_gru', cloud.windows(learners, ['a','b'], 1, {'1':1}, 4),
                              torch.device('cpu'), False, 16)
    assert result['label_weight'] == 9
    assert result['mae'] == pytest.approx(reference['mae'])
    assert len(data['tags']) == len(data['previous']) == 9


@pytest.mark.parametrize('mode', ['no_recent', 'no_counts', 'no_items'])
def test_ablation_transform_preserves_targets_and_dimensions(mode):
    original = cloud.encode(rows(), 1, {'1': 1})
    transformed = cloud.apply_feature_mode(tuple(a.copy() for a in original), 1, mode)
    for index in (4,5): np.testing.assert_array_equal(original[index], transformed[index])
    assert all(a.shape == b.shape for a,b in zip(original, transformed))


def test_checkpoint_paths_cannot_escape_directory(tmp_path):
    import json
    (tmp_path/'resume.json').write_text(json.dumps({'files': [{'name': '../model.pt', 'sha256': 'a'*64}]}))
    with pytest.raises(ValueError, match='Unsafe'):
        cloud.load_resume(tmp_path)
