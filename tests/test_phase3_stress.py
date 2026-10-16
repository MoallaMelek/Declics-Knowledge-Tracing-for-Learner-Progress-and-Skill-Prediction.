from scripts.evaluate_phase3_robustness import perturb
from axis7.models_v2 import ItemEncoder
from axis7.eligibility import eligible

def test_unknown_exercise_stress_removes_question_precedence_without_mutating_target():
    rows=[{'exercise':'a','obs':[{'question':'q1','k':0,'y':1}]}]
    encoder=ItemEncoder().fit({'train':rows})
    changed,keep=perturb(rows,'unknown_item_query',9041)
    assert encoder.encode(rows[0])[0]!=0
    assert encoder.encode(changed[0])[0]==0
    assert rows[0]['obs'][0]['question']=='q1' and changed[0]['obs'][0]['y']==1
    assert keep.tolist()==[True]

def test_missing_history_has_common_target_mask_and_ineligible_inputs():
    rows=[{'exercise':'a','obs':[{'k':0,'y':1}]} for _ in range(40)]
    changed,keep=perturb(rows,'history_dropout_30',9041)
    assert 0<keep.sum()<len(rows)
    assert all(eligible(row['obs'][0])==bool(retained) for row,retained in zip(changed,keep))
    assert all(eligible(row['obs'][0]) for row in rows)
