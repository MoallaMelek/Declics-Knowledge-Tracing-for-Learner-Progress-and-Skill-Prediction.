

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
