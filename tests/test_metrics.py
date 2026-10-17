import numpy as np
import pytest

from axis7.metrics import grouped_bootstrap


def test_bootstrap_accepts_sequences_and_matches_arrays():
    y = [0, 1, 0, 1]
    p = [.2, .7, .3, .8]
    users = ["a", "a", "b", "b"]
    reference = [.5] * 4
    actual = grouped_bootstrap(y, p, users, replicates=5, reference=reference)
    expected = grouped_bootstrap(np.array(y), np.array(p), np.array(users),
                                 replicates=5, reference=np.array(reference))
    assert actual == expected
    assert "log_loss_difference_vs_prior" in actual


@pytest.mark.parametrize("y,p,users,kwargs", [
    ([], [], [], {}),
    ([0, 1], [.2], ["a", "b"], {}),
    ([[0, 1]], [[.2, .8]], [["a", "b"]], {}),
    ([0, 1], [.2, .8], ["a", "b"], {"reference": [.5]}),
    ([0, 1], [.2, .8], ["a", "b"], {"replicates": 0}),
    ([0, 1], [.2, .8], ["a", "b"], {"replicates": True}),
])
def test_bootstrap_rejects_invalid_cohorts(y, p, users, kwargs):
    with pytest.raises(ValueError):
        grouped_bootstrap(y, p, users, **kwargs)


@pytest.mark.parametrize("temperature", [0, -1, np.nan, np.inf, -np.inf, [1]])
def test_calibration_rejects_invalid_temperature(temperature):
    from axis7.metrics import calibrate
    with pytest.raises(ValueError, match="temperature"):
        calibrate([.2, .8], temperature)


def test_calibration_preserves_probabilities_at_unit_temperature():
    from axis7.metrics import calibrate
    np.testing.assert_allclose(calibrate([.2, .8], 1), [.2, .8])


def test_empty_evaluation_fails_with_actionable_error():
    from axis7.metrics import evaluate
    with pytest.raises(ValueError, match="held-out observation"):
        evaluate([])
