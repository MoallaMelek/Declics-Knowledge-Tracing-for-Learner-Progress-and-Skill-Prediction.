import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pytest
import torch

from axis7 import cloud_training as cloud
from axis7 import musical_registry as registry
from axis7.musical_api import BenchmarkQuery


def archive(tmp_path, filename, text):
    path = tmp_path / 'dataset.zip'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr(filename, text)
    return path


def test_streaming_json_chunks_and_invalid_end():
    content = '[{"x":"é","values":[1,2]}, {"x":3}]'
    assert list(cloud.stream_array(io.StringIO(content), 3)) == json.loads(content)
    for text in ('[{"x":2}', '[{},]', '[{}] {}', '{}'):
        with pytest.raises((ValueError, json.JSONDecodeError)):
            list(cloud.stream_array(io.StringIO(text), 3))


def test_amme_hides_entire_block_and_other_scoretypes(tmp_path):
    text = 'pid,block,sessitem,tune,score,scoretype\na,1,1,x,0.2,7\na,1,2,x,0.8,7\na,1,1,x,0.99,1\na,2,1,x,0.6,7\n'
    rows, audit = cloud.load_amme(archive(tmp_path, 'replicreslong_di.csv', text))
    assert len(rows) == 2
    assert rows[0]['obs'] == [[0, .5, 1.]]
    assert 'not correctness' in audit['score_meaning']


def test_yousician_parts_dedup_and_conflicts(tmp_path):
    def entry(time, part=0, good=3):
        return {'user_id': 'a', 'session_index': 1, 'days_since_signup': time,
                'exercise_id': 1, 'song_id': 1, 'play_mode': 'play', 'exercise_part_index': part,
                'notes_evaluated': 4, 'notes_successful': good, 'chords_evaluated': 0, 'chords_successful': 0}
    raw = [entry(.1), entry(.1), entry(.1, 1), entry(.2, 0, 1), entry(1.1), entry(1.1, 1, 2)]
    rows, audit = cloud.load_yousician(archive(tmp_path, 'yousician.json', json.dumps(raw)))
    assert len(rows) == 1 and rows[0]['obs'] == [[0, .5, 1.]]
    assert audit['exact_duplicates_excluded'] == 1
    assert audit['conflicting_groups_excluded'] == 1


def test_singpad_recording_and_equal_timestamp_atomicity(tmp_path):
    path = tmp_path/'sing.zip'
    import csv
    f = io.StringIO(); w = csv.writer(f)
    w.writerow(['opern_id','qc_array']); w.writerow([1,json.dumps([[3,4],[0,1]])])
    g = io.StringIO(); w = csv.writer(g)
    w.writerow(['user_id','opern_id','record_id','create_time','qa_array'])
    for rid in (1,2):
        w.writerow(['a',1,rid,'2023-01-01 12:00:00',json.dumps([[3,4],[0,1]])])
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('opernDS.csv',f.getvalue()); z.writestr('recordDS.csv',g.getvalue())
    rows, audit = cloud.load_singpad(path)
    assert len(rows) == 1 and len(rows[0]['obs']) == 4
    assert audit['note_labels'] == 4


@pytest.mark.parametrize('name',['dkt','enhanced_gru','item_attention'])
def test_current_and_future_labels_cannot_change_current_forecast(name):
    rows = [{'time':i, 'exercise':'a', 'obs':[[0,float(i%2),1.],[1,.5,2.]]} for i in range(4)]
    changed = json.loads(json.dumps(rows))
    changed[2]['obs'] = [[0,1.,4.],[1,0.,5.]]; changed[3]['obs'] = [[0,0.,10.]]
    a = cloud.encode(rows,2,{'a':1}); b = cloud.encode(changed,2,{'a':1})
    for i in range(4):
        np.testing.assert_equal(a[i][:3],b[i][:3])
    model = cloud.model_for(name,2,{'a':1},16,16).eval()
    inputs = lambda v: [torch.from_numpy(x).unsqueeze(0) for x in v]
    with torch.no_grad():
        pa = cloud.forward(model,name,inputs(a)); pb = cloud.forward(model,name,inputs(b))
    torch.testing.assert_close(pa[:,:3],pb[:,:3])
    assert not np.array_equal(a[0][3],b[0][3])


def test_windows_do_not_double_count_boundary_targets():
    learners = {'a':[{'time':i,'exercise':'','obs':[[0,.5,1.]]} for i in range(10)]}
    samples = cloud.windows(learners,['a'],1,{},4)
    assert sum(s[-1].sum() for s in samples) == 9
    assert max(len(s[0]) for s in samples) <= 4


def test_split_disjoint_and_item_vocabulary_train_only():
    learners = {str(i):[{'exercise':str(i)}] for i in range(20)}
    split = cloud.split_learners(learners,42)
    assert not set(split['train']) & set(split['test'])
    assert split == cloud.split_learners(learners,42)
    items = cloud.fit_items(learners,split['train'])
    assert not set(items) & set(split['test'])
    public = cloud.public_split_provenance(split)
    assert all(set(value) == {'count','sha256'} for value in public.values())
    assert sum(value['count'] for value in public.values()) == len(learners)
    bad = {**split, 'test': split['test'] + [split['train'][0]]}
    with pytest.raises(ValueError,match='leakage'):
        cloud.public_split_provenance(bad)


def test_resume_falls_back_to_intact_generation(tmp_path):
    cloud.save_resume(tmp_path,{'epoch':1})
    cloud.save_resume(tmp_path,{'epoch':2})
    manifest = json.loads((tmp_path/'resume.json').read_text())
    (tmp_path/manifest['files'][0]['name']).write_bytes(b'interrupted')
    assert cloud.load_resume(tmp_path)['epoch'] == 1


def test_mid_epoch_resume_matches_uninterrupted_training(tmp_path,monkeypatch):
    text = 'pid,block,sessitem,tune,score,scoretype\n'
    for p in range(20):
        for b in range(1,5):
            text += f'{p},{b},1,t,{.2+.1*(p%4)+.04*b},7\n'
    data = archive(tmp_path,'replicreslong_di.csv',text)
    full = tmp_path/'full'; resumed = tmp_path/'resumed'
    options = dict(epochs=2,batch_size=3,hidden=16,context=8,checkpoint_batches=1)
    cloud.train('amme',data,full,**options)
    original = cloud.save_resume
    def interrupt(directory,state):
        original(directory,state)
        raise InterruptedError('simulated runtime disconnect')
    monkeypatch.setattr(cloud,'save_resume',interrupt)
    with pytest.raises(InterruptedError):
        cloud.train('amme',data,resumed,**options)
    monkeypatch.setattr(cloud,'save_resume',original)
    cloud.train('amme',data,resumed,**options)
    a = torch.load(full/'model.pt',weights_only=True); b = torch.load(resumed/'model.pt',weights_only=True)
    for key in a['state_dict']:
        torch.testing.assert_close(a['state_dict'][key],b['state_dict'][key],rtol=0,atol=0)
    assert json.loads((full/'metrics.json').read_text())['test'] == json.loads((resumed/'metrics.json').read_text())['test']
    with pytest.raises(ValueError,match='mismatch'):
        cloud.train('amme',data,resumed,seed=43,**options)
    with pytest.raises(ValueError,match='gate failed'):
        registry.install(full,tmp_path/'registry')


def test_bundle_rejects_paths_and_missing_files(tmp_path):
    for filename in ('../model.pt','model.pt'):
        path = archive(tmp_path,filename,'not a model')
        with pytest.raises(ValueError):
            registry.import_bundle(path,tmp_path/'installed')


def test_notebook_code_compiles_and_required_cloud_steps():
    root = Path(__file__).resolve().parents[1]
    for source in cloud.SOURCES:
        nb = json.loads((root/'notebooks'/f'DECLIC_{source}.ipynb').read_text(encoding='utf-8'))
        assert nb['nbformat'] == 4
        code = '\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code')
        for c in nb['cells']:
            if c['cell_type']=='code':
                compile(''.join(c['source']),'<colab>','exec')
        assert 'drive.mount' in code and 'torch.cuda.is_available' in code and 'train(SOURCE' in code


def test_benchmark_time_validation():
    with pytest.raises(ValueError):
        BenchmarkQuery(source='yousician',model_id='x',instrument='ukulele',query_time='tomorrow',history=[])
    with pytest.raises(ValueError):
        BenchmarkQuery(source='singpad',model_id='x',instrument='voice',query_time='2020-01-01T00:00:00+00:00',history=[])


def test_registered_real_model_roundtrip_domain_and_future_exclusion(tmp_path,monkeypatch):
    from axis7 import musical_api
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    root = Path(__file__).resolve().parents[1]
    folder = root/'artifacts/models/phase5/yousician/enhanced_gru'
    if not folder.exists():
        pytest.skip('Real trained artifact not included in this checkout')
    bundle = tmp_path/'model.zip'
    with zipfile.ZipFile(bundle,'w') as z:
        for name in ('model.pt','metrics.json','metrics.csv','history.json'):
            z.write(folder/name,name)
    destination = tmp_path/'registry'
    identifier = registry.import_bundle(bundle,destination)
    monkeypatch.setattr(musical_api,'REGISTRY_ROOT',destination)
    app = FastAPI(); app.include_router(musical_api.router); client = TestClient(app)
    body = {'source':'yousician','model_id':identifier,'instrument':'ukulele','query_time':4,
            'history':[{'time':i,'observations':[{'concept':0,'score':.2+.1*i}]} for i in (0,1,2)]}
    a = client.post('/api/v5/musical/forecast',json=body)
    assert a.status_code == 200 and a.json()['status'] == 'source_benchmark_only'
    body['history'] += [{'time':i,'observations':[{'concept':0,'score':1}]} for i in (4,5)]
    b = client.post('/api/v5/musical/forecast',json=body)
    assert a.json()['predictions'] == b.json()['predictions']
    body['instrument'] = 'piano'
    assert client.post('/api/v5/musical/forecast',json=body).json()['status'] == 'abstained'
    meta = json.loads((destination/identifier/'metrics.json').read_text())
    meta['splits']['test']['sha256'] = meta['splits']['train']['sha256']
    (destination/identifier/'metrics.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError,match='leakage'):
        registry.validate(destination/identifier)
