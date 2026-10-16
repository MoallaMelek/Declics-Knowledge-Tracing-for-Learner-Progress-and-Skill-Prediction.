import numpy as np
import pytest
import torch
from axis7.phase7_research import RepresentationModel, gap_encode, fit_temperature, calibration, tabular, make_samples
from axis7.cloud_training import batch
from axis7.phase7_research import target_logits


def rows():
    return [{'time': i, 'exercise': 'x', 'obs': [[0, y, 1.]]} for i,y in enumerate([0.,1.,0.,1.,1.,0.])]


@pytest.mark.parametrize('condition', ['gru','unordered','recent3','attention','no_concept_embedding','past_gaps'])
def test_future_cannot_change_earlier_outputs(condition):
    torch.manual_seed(7)
    model = RepresentationModel(condition, 2, 2).eval()
    a = rows(); b = rows(); b[-1]['obs'] = [[1, 1., 1.]]
    with torch.no_grad():
        outputs = [model(*batch([gap_encode(r,2,{'x':1},condition)],'cpu')[:4]).numpy() for r in (a,b)]
    np.testing.assert_allclose(outputs[0], outputs[1], atol=1e-6)


def test_unordered_prefix_invariance():
    model = RepresentationModel('unordered', 2, 2).eval()
    a = rows(); b = [a[2],a[0],a[1],*a[3:]]
    with torch.no_grad():
        outputs = [model(*batch([gap_encode(r,2,{'x':1},'unordered')],'cpu')[:4]) for r in (a,b)]
    torch.testing.assert_close(outputs[0][:,3:], outputs[1][:,3:])


def test_recent3_forgets_distant_history():
    model = RepresentationModel('recent3', 2, 2).eval()
    a = rows(); b = rows(); b[0]['obs'] = [[1, 1., 200.]]
    with torch.no_grad():
        outputs = [model(*batch([gap_encode(r,2,{'x':1},'recent3')],'cpu')[:4]) for r in (a,b)]
    torch.testing.assert_close(outputs[0][:,-1], outputs[1][:,-1])


def test_calibration_is_fitted_from_supplied_validation_only():
    y = np.array([0.,1.,0.,1.]); p = np.array([.4,.6,.45,.55]); w = np.ones(4)
    t = fit_temperature(y,p,w)
    assert 0.1 < t < 10
    raw = calibration(y,p,w); adjusted = calibration(y,p,w,t)
    assert adjusted['log_loss'] < raw['log_loss']
    assert raw['ece'] == pytest.approx(.425)
    d = raw['brier_binned_decomposition']
    assert d['reliability']-d['resolution']+d['uncertainty']+d['within_bin_residual'] == pytest.approx(raw['brier'])


def test_gap_uses_previous_interval_not_future_date():
    a = rows(); b = rows(); b[-1]['time'] = 1000
    np.testing.assert_array_equal(gap_encode(a,2,{},'past_gaps')[3], gap_encode(b,2,{},'past_gaps')[3])


def test_tabular_target_not_in_its_features_and_window_labels_once():
    a = rows(); b = rows(); b[-1]['obs'] = [[0,1.,1.]]
    x,y,w = tabular({'a':a},['a'],2,np.array([.5,.5]))
    xx,yy,ww = tabular({'a':b},['a'],2,np.array([.5,.5]))
    np.testing.assert_array_equal(x,xx)
    for condition in ('gru','recent3'):
        samples = make_samples({'a':a},['a'],2,{},condition,context=4)
        assert sum(s[-1].sum() for s in samples) == 5


@pytest.mark.parametrize('condition',['attention','no_concept_embedding'])
def test_sparse_attention_matches_dense_outputs_and_gradients(condition):
    torch.manual_seed(9)
    model=RepresentationModel(condition,2,2).eval()
    inputs=batch([gap_encode(rows(),2,{'x':1},condition)],'cpu')
    mask=inputs[-1]>0
    dense=model(*inputs[:4]); sparse=target_logits(model,inputs)
    torch.testing.assert_close(dense[mask],sparse[mask],atol=1e-6,rtol=1e-5)
    dense[mask].sum().backward(); grads={n:p.grad.clone() for n,p in model.named_parameters() if p.grad is not None}
    model.zero_grad(); target_logits(model,inputs)[mask].sum().backward()
    for n,p in model.named_parameters():
        if n in grads: torch.testing.assert_close(grads[n],p.grad,atol=2e-5,rtol=2e-4)
