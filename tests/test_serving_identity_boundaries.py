import copy
import pytest
from axis7.serving_identity import freeze, canonical_digest, generation, request_identity

def test_nested_generation_cannot_be_mutated_through_aliases():
    source={'rows':[{'outcome':1}]};frozen=freeze(source)
    source['rows'][0]['outcome']=0
    assert frozen['rows'][0]['outcome']==1
    with pytest.raises(TypeError):frozen['rows'][0]['outcome']=0
    with pytest.raises(TypeError):frozen.update({'rows':[]})
    assert copy.deepcopy(frozen) is frozen

def test_digest_is_key_order_independent_and_rejects_nonfinite_values():
    assert canonical_digest({'a':1,'b':2})==canonical_digest({'b':2,'a':1})
    with pytest.raises(ValueError):canonical_digest({'p':float('nan')})

def test_receipt_changes_when_effective_target_or_history_changes():
    cohort={'generation':'g'};rows=[{'y':0},{'y':1}]
    original=request_identity(cohort,0,rows,1)
    rows[1]['y']=0
    assert request_identity(cohort,0,rows,1)!=original
    rows[1]['y']=1;rows[0]['y']=1
    assert request_identity(cohort,0,rows,1)!=original
