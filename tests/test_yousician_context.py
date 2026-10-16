import copy
import json
import zipfile
import numpy as np
import torch
import pytest
from axis7.yousician_context import enrich,encode,ContextGRU,FEATURES


def test_current_day_metadata_never_enters_current_forecast(tmp_path):
    source=[{'user_id':'private-user','session_index':i,'days_since_signup':day,'exercise_id':str(i),
        'song_id':'song','notes_evaluated':10,'notes_successful':5+i,'chords_evaluated':0,'chords_successful':0,
        'difficulty_level':i,'play_mode':'play'} for i,day in enumerate([1,2,10])]
    prepared={'learners':{'private-user':[{'time':r['days_since_signup'],'exercise':'','obs':[[0,r['notes_successful']/10,1.]]} for r in source]}}
    path=tmp_path/'data.zip'
    def load(rows):
        with zipfile.ZipFile(path,'w') as z:z.writestr('data.json',json.dumps(rows))
        return enrich(path,prepared)['learners']['private-user']
    a=load(source);changed=copy.deepcopy(source);changed[-1]['difficulty_level']=10;changed[-1]['exercise_id']='unknown-future-exercise'
    b=load(changed)
    np.testing.assert_array_equal(encode(a,{})[0],encode(b,{})[0])
    assert a[-1]['context'][7]==pytest.approx(np.log1p(1)) # previous interval 2-1, never future 10-2


def test_context_gru_is_causal():
    torch.manual_seed(42);model=ContextGRU().eval()
    a=torch.rand(1,5,4+len(FEATURES));b=a.clone();b[:,-1]=100
    with torch.no_grad():
        pa=model(a);pb=model(b)
    torch.testing.assert_close(pa[:,:-1],pb[:,:-1])
