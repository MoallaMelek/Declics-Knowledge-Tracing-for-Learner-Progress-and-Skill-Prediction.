import copy
import numpy as np
import pytest
import torch
from axis7.data import arrays,generate_music,split_students,load_forget
from axis7.models import DKT,SAKT,Baseline,neural_predict,pfa_features
from axis7.schema import Attempt,to_record

@pytest.mark.parametrize('model_type',[DKT,SAKT])
def test_current_and_future_outcomes_cannot_change_past_predictions(model_type):
    torch.manual_seed(13);torch.set_num_threads(2)
    rows=next(iter(generate_music(students=1,sessions=3)[0].values()))
    changed=copy.deepcopy(rows)
    for r in changed[4:]:
        for o in r['obs']:o['y']=1-o['y']
    m=model_type(6,hidden=16);m.eval()
    a=neural_predict(m,rows,6);b=neural_predict(m,changed,6)
    np.testing.assert_allclose(a[:5],b[:5],atol=1e-7)

def test_atomic_duplicate_skill_targets_preserve_original_row_weight():
    rows=[{'obs':[{'k':0,'y':1},{'k':0,'y':0},{'k':1,'y':1}]},{'obs':[{'k':1,'y':0}]}]
    x,y,w=arrays(rows,2)
    assert x[0].sum()==0
    assert y[0,0]==.5 and w[0,0]==2
    np.testing.assert_allclose(x[1],[1/3,0,1/3,1/3])
    changed=copy.deepcopy(rows);changed[0]['obs'].reverse()
    for a,b in zip(arrays(rows,2),arrays(changed,2)):np.testing.assert_array_equal(a,b)
    features=pfa_features(rows,2)
    np.testing.assert_array_equal(features[0][0],features[1][0])

@pytest.mark.parametrize('name',['prior','bkt','pfa'])
def test_baselines_do_not_use_current_outcomes(name):
    learners,_=generate_music(students=8,sessions=3);m=Baseline(name,6).fit(learners)
    rows=next(iter(learners.values()));changed=copy.deepcopy(rows)
    for r in changed[4:]:
        for o in r['obs']:o['y']=1-o['y']
    np.testing.assert_allclose(m.predict(rows)[:5],m.predict(changed)[:5])

def test_real_benchmark_ties_and_split_are_atomic_disjoint():
    learners,meta=load_forget();splits=split_students(learners)
    assert sum(len(v) for v in learners.values())==10307
    assert sum(len(r['obs']) for rows in learners.values() for r in rows)==10873
    for rows in learners.values():assert all(a['order']<b['order'] for a,b in zip(rows,rows[1:]))
    ids=[u for v in splits.values() for u in v]
    assert len(ids)==len(set(ids))==186
    assert all(o['y'] in (0,1) for rows in learners.values() for r in rows for o in r['obs'])

def valid_attempt():
    return {'attempt_id':'x','student_id':'u','session_id':'s','exercise_id':'e','instrument':'piano',
        'timestamp':'2026-01-01T00:00:00+00:00','provenance':'project','rubric_version':'provisional',
        'observations':[{'skill_id':'pitch','outcome':1}]}

def test_boundary_unknown_missing_and_invalid_outcomes_are_rejected():
    p=valid_attempt();a=Attempt.model_validate(p);assert to_record(a,['pitch'])['obs'][0]['k']==0
    with pytest.raises(ValueError):to_record(a,['rhythm'])
    for bad in [2,-1,True,'1']:
        p=valid_attempt();p['observations'][0]['outcome']=bad
        with pytest.raises(ValueError):Attempt.model_validate(p)
    p=valid_attempt();p['timestamp']='2026-01-01T00:00:00'
    with pytest.raises(ValueError):Attempt.model_validate(p)
    p=valid_attempt();p['observations']=[{'skill_id':'pitch','score':.8}]
    a=Attempt.model_validate(p);r=to_record(a,['pitch']);x,y,w=arrays([r],1)
    assert w.sum()==0  # no arbitrary conversion of a continuous upstream score

def test_saved_baseline_statistics_only_use_training_learners():
    learners,_=generate_music(students=20,sessions=3);parts=split_students(learners)
    train={u:learners[u] for u in parts['train']};m=Baseline('prior',6).fit(train)
    positive=np.ones(6);count=np.ones(6)*2
    for rows in train.values():
        for r in rows:
            for o in r['obs']:positive[o['k']]+=o['y'];count[o['k']]+=1
    np.testing.assert_allclose(m.priors,positive/count)

def test_attention_future_inputs_cannot_change_current_logits():
    m=SAKT(3,hidden=16);m.eval();x=torch.rand(1,12,6);z=x.clone();z[:,6:]=100
    with torch.no_grad():a=m(x);b=m(z)
    torch.testing.assert_close(a[:,:6],b[:,:6])

@pytest.mark.parametrize('model_type',[DKT,SAKT])
def test_bounded_sliding_context_keeps_predictions_causal(model_type):
    # Histories longer than the saved context use overlapping windows; this path must obey the same rule.
    torch.manual_seed(5);torch.set_num_threads(2)
    rows=next(iter(generate_music(students=1,sessions=12)[0].values()))
    m=model_type(6,hidden=16,context=8);m.eval()
    for cut in (10,20,30):
        changed=copy.deepcopy(rows)
        for r in changed[cut:]:
            for o in r['obs']:o['y']=1-o['y']
        a=neural_predict(m,rows,6,query=True);b=neural_predict(m,changed,6,query=True)
        np.testing.assert_allclose(a[:cut],b[:cut],atol=1e-7)

def test_non_finite_numeric_observation_is_refused_at_the_boundary():
    for field,value in [('timing_mae_ms',float('inf')),('rhythm_score',float('nan'))]:
        p=valid_attempt();p[field]=value
        with pytest.raises(ValueError):Attempt.model_validate(p)
    p=valid_attempt();p['gesture_metrics']={'wrist_angle':float('nan')}
    with pytest.raises(ValueError):Attempt.model_validate(p)
