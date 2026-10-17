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
