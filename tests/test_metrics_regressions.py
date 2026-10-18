"""Bootstrap accepts the same array-like inputs as summary without resampling misalignment."""
import numpy as np
import pytest
from axis7.metrics import grouped_bootstrap


@pytest.mark.parametrize('probability', [np.nan, np.inf, -np.inf, -.1, 1.1])
def test_calibration_bins_reject_probabilities_that_would_disappear(probability):
    from axis7.metrics import calibration_bins
    with pytest.raises(ValueError, match='probabilities'):
        calibration_bins([0, 1], [.2, probability])


@pytest.mark.parametrize('labels,probabilities', [([], []), ([0], [.2, .8]), ([[0, 1]], [[.2, .8]]), ([0, 1], [.2, np.nan]), ([0, 2], [.2, .8])])
def test_temperature_fit_requires_usable_validation_data(labels, probabilities):
    from axis7.metrics import temperature_fit
    with pytest.raises(ValueError, match='temperature fitting'):
        temperature_fit(labels, probabilities)


def test_temperature_fit_returns_finite_positive_temperature():
    from axis7.metrics import temperature_fit
    temperature = temperature_fit([0, 1, 0, 1], [.2, .8, .3, .7])
    assert np.isfinite(temperature) and temperature > 0


@pytest.mark.parametrize('probability', [np.nan, np.inf, -np.inf])
def test_calibrate_does_not_hide_nonfinite_predictions(probability):
    from axis7.metrics import calibrate
    with pytest.raises(ValueError, match='probabilities'):
        calibrate([.2, probability], 1)


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
