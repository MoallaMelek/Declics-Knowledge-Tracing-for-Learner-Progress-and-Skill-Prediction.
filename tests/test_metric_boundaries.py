import numpy as np
import pytest
from axis7.metrics import calibration_bins, grouped_bootstrap, summary, calibrate

def test_every_bin_edge_is_counted_once_including_one():
    p=np.arange(11)/10
    bins=calibration_bins([0]*11,p)
    assert sum(b['n'] for b in bins)==11
    assert bins[0]['n']==1 and bins[-1]['n']==2

def test_single_class_summary_retains_fixed_confusion_shape():
    result=summary([0,0],[0,0])
    assert result['auc'] is None
    assert result['confusion_matrix']==[[2,0],[0,0]]
    assert result['f1']==0

def test_grouped_bootstrap_is_reproducible_and_identical_reference_has_zero_difference():
    args=([0,1,0,1],[.1,.9,.2,.8],['a','a','b','b'])
    first=grouped_bootstrap(*args,replicates=8,seed=7,reference=args[1])
    assert first==grouped_bootstrap(*args,replicates=8,seed=7,reference=args[1])
    assert first['log_loss_difference_vs_prior']==[0,0]

def test_temperature_one_preserves_interior_probabilities():
    assert calibrate([.1,.5,.9],1)==pytest.approx([.1,.5,.9])
