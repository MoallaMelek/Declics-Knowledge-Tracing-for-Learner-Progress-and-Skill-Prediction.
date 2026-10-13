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
    np.testing.assert_allclose(noops[:4],base[:4],atol=1e-7)
    np.testing.assert_allclose(noops[4:],base[3:],atol=1e-7)


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
