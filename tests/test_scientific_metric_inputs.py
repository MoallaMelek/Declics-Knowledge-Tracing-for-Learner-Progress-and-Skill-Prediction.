

import numpy as np
import pytest
from axis7.scientific_validation import metrics,train_priors

@pytest.mark.parametrize('y,p,w', [([0,1],[.2],[1,1]), ([[0,1]],[[.2,.8]],[[1,1]]),([0,1],[.2,np.inf],[1,1]),([0,np.nan],[.2,.8],[1,1]),([0,1],[.2,.8],[1,-1]),([0,1],[.2,.8],[1,np.nan]),([0,1],[-.1,.8],[1,1])])
def test_weighted_metrics_refuse_invalid_measurements(y,p,w):
    with pytest.raises(ValueError):metrics(y,p,w,True)

def test_zero_weight_calibration_bin_is_omitted():
    result=metrics([0,1],[.2,.8],[0,1],True)
    assert len(result['calibration'])==1
    assert result['calibration'][0]['label_weight']==1
    assert np.isfinite(result['log_loss'])


def test_training_priors_refuse_an_empty_training_partition():
    for learners,ids in [({},[]),({'empty':[]},['empty'])]:
        with pytest.raises(ValueError,match='Training priors'):
            train_priors(learners,ids,2)

def test_unobserved_concepts_use_the_observed_training_mean():
    mean,prior,counts=train_priors({'a':[{'obs':[[0,.75,4]]}]},['a'],2)
    assert mean==.75 and prior[1]==.75 and counts.tolist()==[4,0]
