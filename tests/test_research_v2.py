import copy
import json
import numpy as np
import pytest
import torch
from axis7.data import generate_music, split_students
from axis7.models import Baseline
from axis7.models_v2 import (ItemEncoder, encode_sequence, make_neural, research_neural_predict,
                             StatisticalControl, save_checkpoint, ResearchPredictor, CoherentGroupedBKT)
from axis7.research_v2 import owned_windows, batch_windows, neural_logits, select_winner, create_experiment


@pytest.fixture
def fixture():
    torch.set_num_threads(2); torch.manual_seed(17)
    learners, _ = generate_music(students=12, sessions=3)
    items = ItemEncoder().fit(learners)
    return learners, items


@pytest.mark.parametrize('name',['enhanced_gru','item_attention','enhanced_gru_no_outcome','item_attention_no_item'])
def test_current_labels_and_future_labels_or_items_do_not_change_past(fixture, name):
    learners, items = fixture; rows=next(iter(learners.values())); changed=copy.deepcopy(rows)
    for row in changed[5:]:
        row['exercise']='future-unseen-item'
        for o in row['obs']: o['y']=1-o['y']
    m=make_neural(name,6,items,16,256);m.eval()
    a=research_neural_predict(m,name,rows,items);b=research_neural_predict(m,name,changed,items)
    # Query identity at position5 is allowed to change its forecast; earlier positions are invariant.
    np.testing.assert_allclose(a[:5],b[:5],atol=1e-7)
    labels_only=copy.deepcopy(rows)
    for row in labels_only[5:]:
        for o in row['obs']:o['y']=1-o['y']
    np.testing.assert_allclose(a[:6],research_neural_predict(m,name,labels_only,items)[:6],atol=1e-7)


@pytest.mark.parametrize('name',['enhanced_gru','item_attention','enhanced_gru_no_outcome','item_attention_no_item'])
def test_long_histories_all_targets_and_noops_survive(fixture,name):
    learners,items=fixture;rows=[copy.deepcopy(r) for r in next(iter(learners.values()))*3]
    m=make_neural(name,6,items,16,8);m.eval()
    base=research_neural_predict(m,name,rows,items)
    assert base.shape==(len(rows)+1,6)
    changed=copy.deepcopy(rows)
    for r in changed[17:]:
        for o in r['obs']:o['y']=1-o['y']
    np.testing.assert_allclose(base[:18],research_neural_predict(m,name,changed,items)[:18],atol=1e-7)
    extra=copy.deepcopy(rows);extra.insert(3,{'obs':[{'k':0,'y':None,'score':.8}],'exercise':'unseen'})
    noops=research_neural_predict(m,name,extra,items)
    # Rows before the no-op are untouched by its insertion.
    np.testing.assert_allclose(noops[:3],base[:3],atol=1e-7)
    # The no-op's own forecast is the generic UNK-query prefix forecast (axis7-science-v2.2),
    # not the next eligible row's own-item forecast that `expand_forecasts` would repeat.
    np.testing.assert_allclose(noops[3],research_neural_predict(m,name,rows[:3],items)[-1],atol=1e-7)
    # Everything from the next eligible row onward is unaffected by the no-op, just shifted.
    np.testing.assert_allclose(noops[4:],base[3:],atol=1e-7)


@pytest.mark.parametrize('name',['enhanced_gru','item_attention'])
def test_noop_forecast_is_unk_conditioned_not_future_item_leakage(fixture,name):
    """Regression for the axis7-science-v2.2 serving fix: an observation-only/excluded
    row's forecast must depend only on its causal prefix, never on a later eligible
    row's exercise identity or labels (the historical 0.06048 CLI-reproduced defect)."""
    learners,items=fixture;rows=[copy.deepcopy(r) for r in next(iter(learners.values()))]
    assert len(rows)>=4
    with_noop=copy.deepcopy(rows)
    with_noop.insert(2,{'obs':[{'k':0,'y':None,'score':.7}],'exercise':'excluded-unseen'})
    m=make_neural(name,6,items,16,256);m.eval()
    base=research_neural_predict(m,name,with_noop,items)
    changed=copy.deepcopy(with_noop)
    for row in changed[3:]:
        row['exercise']='future-unseen-item'
        for o in row['obs']:o['y']=1-o['y']
    changed_forecast=research_neural_predict(m,name,changed,items)
    # Changing a later exercise/label must not move the earlier no-op's forecast.
    np.testing.assert_allclose(base[2],changed_forecast[2],atol=1e-7)
    # It must equal the explicit prefix-only, UNK-query forecast...
    expected_unk=research_neural_predict(m,name,rows[:2],items)[-1]
    np.testing.assert_allclose(base[2],expected_unk,atol=1e-7)
    # ...and must differ from naively borrowing the next eligible row's own-item forecast
    # (the historical defect being regressed against).
    borrowed=research_neural_predict(m,name,rows[:3],items,rows[2]['exercise'])[-1]
    assert np.max(np.abs(base[2]-borrowed))>1e-4
    # Neutrality at the next (trailing) query: a no-op appended at the very end still
    # contributes nothing, so the next-query forecast is unchanged by its presence.
    trailing_without_noop=research_neural_predict(m,name,rows,items)[-1]
    trailing_with_noop=research_neural_predict(m,name,rows+[{'obs':[{'k':0,'y':None,'score':.7}],'exercise':'trailing-unseen'}],items)[-1]
    np.testing.assert_allclose(trailing_without_noop,trailing_with_noop,atol=1e-7)


def test_item_pfa_noop_forecast_is_unk_conditioned_not_future_item_leakage(fixture):
    """Same axis7-science-v2.2 regression for the `item_pfa` statistical control."""
    learners,items=fixture;rows=[copy.deepcopy(r) for r in next(iter(learners.values()))]
    assert len(rows)>=4
    model=StatisticalControl('item_pfa',6,items).fit(learners)
    with_noop=copy.deepcopy(rows)
    with_noop.insert(2,{'obs':[{'k':0,'y':None,'score':.7}],'exercise':'excluded-unseen'})
    base=model.probabilities(with_noop)
    changed=copy.deepcopy(with_noop)
    for row in changed[3:]:
        row['exercise']='future-unseen-item'
        for o in row['obs']:o['y']=1-o['y']
    np.testing.assert_allclose(base[2],model.probabilities(changed)[2],atol=1e-7)
    expected_unk=model.probabilities(rows[:2])[-1]
    np.testing.assert_allclose(base[2],expected_unk,atol=1e-7)
    borrowed=model.probabilities(rows[:3],rows[2]['exercise'])[-1]
    assert np.max(np.abs(base[2]-borrowed))>1e-4


def test_no_outcome_ablation_erases_direction_not_just_shifted_label(fixture):
    learners,items=fixture;rows=next(iter(learners.values()));flipped=copy.deepcopy(rows)
    for r in flipped:
        for o in r['obs']:o['y']=1-o['y']
    a=encode_sequence(rows,6,items,no_outcome=True);b=encode_sequence(flipped,6,items,no_outcome=True)
    for i in range(4):np.testing.assert_array_equal(a[i],b[i])
    model=StatisticalControl('exposure',6,items)
    np.testing.assert_array_equal(model.features(rows)[0],model.features(flipped)[0])


def test_item_encoder_uses_training_only_unknown_is_stable(fixture):
    learners,items=fixture
    before=copy.deepcopy(items.state)
    assert items.encode({'obs':[],'exercise':'unseen-test-item'})[0]==0
    rows=next(iter(learners.values()));row=copy.deepcopy(rows[0]);row['exercise']='different'
    items.encode(row);assert items.state==before
    assert items.state['vocabulary'] and min(items.state['vocabulary'].values())==1


def test_duplicate_atomic_permutation_and_count_features(fixture):
    _,items=fixture
    rows=[{'obs':[{'k':0,'y':1,'question':'a'},{'k':0,'y':0,'question':'b'},{'k':1,'y':1,'question':'c'}]}, {'obs':[{'k':0,'y':1}]}]
    reverse=copy.deepcopy(rows);reverse[0]['obs'].reverse()
    a=encode_sequence(rows,6,items);b=encode_sequence(reverse,6,items)
    for x,y in zip(a,b):np.testing.assert_array_equal(x,y)
    assert a[-1][0,0]==2 and a[-2][0,0]==.5
    assert a[0][1,12]==pytest.approx(np.log(2))


@pytest.mark.parametrize('name',['enhanced_gru','item_attention'])
def test_end_padding_does_not_influence_valid_prefix(fixture,name):
    learners,items=fixture;rows=next(iter(learners.values()));encoded=encode_sequence(rows,6,items)
    m=make_neural(name,6,items,16,256);m.eval()
    small=batch_windows([encoded], [0]);long=[v.copy() for v in encoded]
    long=[np.pad(v,[(0,4)]+[(0,0)]*(v.ndim-1)) for v in long]
    padded=batch_windows([encoded,long],[0,1])
    with torch.no_grad():a=neural_logits(m,name,small);b=neural_logits(m,name,padded)
    torch.testing.assert_close(a[0],b[0,:len(rows)],atol=1e-6,rtol=1e-5)


def test_long_training_windows_each_target_has_one_owner(fixture):
    learners,items=fixture;rows=next(iter(learners.values()))*4
    encoded=encode_sequence(rows,6,items);windows=list(owned_windows(encoded,8))
    assert sum(float(w[-1].sum()) for w in windows)==float(encoded[-1].sum())
    assert all(len(w[0])<=8 for w in windows)


@pytest.mark.parametrize('name',['enhanced_gru','item_attention','item_pfa','exposure','bkt'])
def test_checkpoint_reload_and_refuse_overwrite(tmp_path,fixture,name):
    learners,items=fixture;rows=next(iter(learners.values()))
    if name in ('item_pfa','exposure'):model=StatisticalControl(name,6,items).fit(learners);expected=model.probabilities(rows)
    elif name=='bkt':
        model=CoherentGroupedBKT(6).fit(learners);expected=model.predict(rows,append_query=True)
    else:model=make_neural(name,6,items,16,256);model.eval();expected=research_neural_predict(model,name,rows,items)
    save_checkpoint(tmp_path,'run',model,{'name':name,'K':6,'hidden':16,'context':256},items,1.2)
    loaded=ResearchPredictor(tmp_path,'run')
    np.testing.assert_allclose(loaded.probabilities(rows),expected,atol=1e-7)
    assert loaded.probabilities(rows,exercise_id='unknown').shape==(len(rows)+1,6)
    with pytest.raises(FileExistsError):save_checkpoint(tmp_path,'run',model,{'name':name,'K':6,'hidden':16,'context':256},items)


def test_coherent_bkt_group_likelihood_and_large_groups():
    known=.5*.9**30*.1**15;unknown=.5*.2**30*.8**15
    posterior=known/(known+unknown)
    assert Baseline.update(.5,[1]*30+[0]*15,.08,.2,.1)==pytest.approx(posterior+(1-posterior)*.08)
    assert np.exp(Baseline.group_log_likelihood(.5,[1,0],.2,.1))==pytest.approx(.125)


def test_selection_never_uses_test_and_splits_are_disjoint(fixture):
    learners,_=fixture;splits=split_students(learners)
    assert len(set(sum(splits.values(),[])))==len(learners)
    candidates=[{'id':'a','name':'dkt','validation':{'log_loss':.7},'test':{'log_loss':.1}},
                {'id':'b','name':'pfa','validation':{'log_loss':.6},'test':{'log_loss':9}}]
    assert select_winner(candidates)['id']=='b'


def test_item_query_only_changes_next_forecast_not_recorded_past(fixture):
    learners,items=fixture;rows=next(iter(learners.values()));m=make_neural('item_attention',6,items,16,256);m.eval()
    first=research_neural_predict(m,'item_attention',rows,items,rows[0]['exercise'])
    second=research_neural_predict(m,'item_attention',rows,items,'unseen')
    np.testing.assert_allclose(first[:-1],second[:-1],atol=1e-7)


def test_experiment_directory_is_immutable(tmp_path,monkeypatch):
    import axis7.research_v2 as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    create_experiment({'x':1},'test-study')
    with pytest.raises(FileExistsError):create_experiment({'x':1},'test-study')
