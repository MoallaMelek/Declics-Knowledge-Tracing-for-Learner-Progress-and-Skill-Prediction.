"""Reevaluate active weights on private held-out data, without fitting or replacing anything."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import torch
from axis7 import cloud_training as training, living_learner as living, musical_registry as registry
from axis7.musical_api import musical_forecast

AUDIT = {'singpad': {'log_loss':.5175285636565014,'roc_auc':.6991037646399885},
         'yousician':{'mae':.09054359412034867}}


def verify(prepared):
    torch.set_num_threads(1)
    living.DATA_DIR=Path(prepared)
    active=json.loads((registry.REGISTRY_ROOT/'active.json').read_text(encoding='utf-8'))
    reports=[]
    for source in ('singpad','yousician'):
        folder=registry.REGISTRY_ROOT/active[source]
        meta,model=registry.cached_validate(folder)
        assert meta['model']=='enhanced_gru' and not meta.get('fixture')
        data=json.loads(gzip.decompress((Path(prepared)/f'{source}-prepared.json.gz').read_bytes()))
        splits=training.split_learners(data['learners'],meta['seed'])
        living.check_integrity(data,meta,splits)
        samples=training.windows(data['learners'],splits['test'],meta['K'],meta['items'],meta['context'],meta.get('feature_mode','full'))
        measured=training.measure(model,meta['model'],samples,'cpu',training.SOURCES[source]['binary'],16)
        differences={k:abs(measured[k]-v) for k,v in AUDIT[source].items()}
        assert all(v<1e-7 for v in differences.values()),differences
        c=living.cohort(source);rows=c['learners'][0];checks=[]
        for cutoff in (2,3,5):
            served=living.forecast_at(c,0,rows,cutoff)
            public=musical_forecast(living.query_for(c,rows,cutoff))
            assert served['predictions']==public['predictions']
            checks.append({'cutoff':cutoff,'pinned_equals_public':True})
        digest=hashlib.sha256((folder/'model.pt').read_bytes()).hexdigest()
        assert digest==meta['model_sha256']
        reports.append({'source':source,'model_id':active[source],'architecture':meta['model'],
                        'checkpoint_sha256':digest,'target':meta['target'],'metrics':measured,
                        'absolute_difference_from_audit':differences,'tolerance':1e-7,
                        'inference_checks':checks,'generation':c['generation'],
                        'data_mode':'real_held_out_data','training_performed':False})
    return reports


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=verify(a.prepared)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([{'source':r['source'],'differences':r['absolute_difference_from_audit'],'training':False} for r in report]))
