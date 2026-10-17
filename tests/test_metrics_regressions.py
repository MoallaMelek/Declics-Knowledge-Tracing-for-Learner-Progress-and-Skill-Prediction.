"""Bootstrap accepts the same array-like inputs as summary without resampling misalignment."""
import numpy as np
from axis7.metrics import grouped_bootstrap


def test_bootstrap_accepts_list_reference_probabilities():
    labels = np.array([0, 1, 0, 1])
    probabilities = np.array([.1, .9, .2, .8])
    users = np.array(['a', 'a', 'b', 'b'])
    expected = grouped_bootstrap(labels, probabilities, users, replicates=8,
                                 reference=np.array([.5, .5, .5, .5]))
    actual = grouped_bootstrap(labels, probabilities, users, replicates=8,
                               reference=[.5, .5, .5, .5])
    assert actual == expected


def test_bootstrap_accepts_list_labels_and_predictions():
    expected = grouped_bootstrap(np.array([0, 1]), np.array([.2, .8]),
                                 ['a', 'a'], replicates=8)
    assert grouped_bootstrap([0, 1], [.2, .8], ['a', 'a'], replicates=8) == expected
