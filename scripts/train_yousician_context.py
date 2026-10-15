"""Exploratory metadata extension: 8 epochs, seeds42/17/83, no test-based promotion."""
import copy
import gzip
import json
from pathlib import Path
import random
import sys
import numpy as np
import torch
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from axis7 import cloud_training as c
from axis7.phase7_research import predictions
from axis7.scientific_validation import metrics
from axis7.yousician_context import enrich,samples,ContextGRU,FEATURES


def run(archive):
    private=ROOT/'tmp/phase7-private/yousician-context';private.mkdir(parents=True,exist_ok=True)
    original=c.prepare('yousician',archive,ROOT/'tmp/phase7-private/yousician/prepared.json.gz')
    prepared=enrich(archive,original)
    with gzip.open(private/'prepared.json.gz','wt',encoding='utf-8') as f:json.dump(prepared,f)
    source_hashes={str(p.relative_to(ROOT)):c.digest(p) for p in (Path(__file__).resolve(),ROOT/'axis7/yousician_context.py')}
    for seed in (42,17,83):
        random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.set_num_threads(2)
        split=c.split_learners(prepared['learners'],seed);sets={s:samples(prepared['learners'],ids,{}) for s,ids in split.items()}
        config={'source':'yousician','condition':'historical_metadata_gru','seed':seed,'epochs':8,
            'dataset_sha256':prepared['sha256'],'splits':c.public_split_provenance(split),'features':FEATURES,
            'source_hashes':source_hashes,'device':'cpu','torch':torch.__version__,'numpy':np.__version__}
        folder=private/f'seed-{seed}';model=ContextGRU();model.condition='historical_metadata_gru'
        optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.001)
        best=None;best_loss=float('inf');epoch=0;stale=0;history=[];cursor=0;order=None
        if (folder/'resume.json').exists():
            state=c.load_resume(folder)
            if state['config']!=config:raise ValueError('Incompatible context checkpoint')
            model.load_state_dict(state['model']);optimizer.load_state_dict(state['optimizer'])
            best=state['best'];best_loss=state['best_loss'];epoch=state['epoch'];stale=state['stale'];history=state['history']
            cursor=state['cursor'];order=state['order'];random.setstate(state['random']);torch.set_rng_state(state['torch_rng'])
        def save():
            c.save_resume(folder,{'config':config,'model':model.state_dict(),'optimizer':optimizer.state_dict(),
                'best':best,'best_loss':best_loss,'epoch':epoch,'stale':stale,'history':history,
                'cursor':cursor,'order':order,'random':random.getstate(),'torch_rng':torch.get_rng_state()})
        while epoch<8 and stale<3:
            if order is None:order=list(range(len(sets['train'])));random.shuffle(order)
            model.train()
            while cursor<len(order):
                inputs=c.batch([sets['train'][i] for i in order[cursor:cursor+16]],'cpu')
                p=torch.sigmoid(model(*inputs[:4]));y,w=inputs[4:];loss=((p-y)**2*w).sum()/w.sum()
                if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
                optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step();cursor+=16
                if cursor%400==0:save()
            y,p,w=predictions(model,sets['validation']);value=metrics(y,p,w,False)['mae']
            if value<best_loss-1e-7:best_loss=value;best=copy.deepcopy(model.state_dict());stale=0
            else:stale+=1
            epoch+=1;cursor=0;order=None;history.append({'epoch':epoch,'validation_mae':value});save()
            print('yousician-context',seed,epoch,value,flush=True)
        model.load_state_dict(best);result={'config':config,'validation':metrics(*predictions(model,sets['validation']),False),
            'test':metrics(*predictions(model,sets['test']),False),'history':history,'status':'exploratory_research_only',
            'comparison_caveat':'Different input dimension and parameterization; feature gain is not an isolated causal effect.'}
        # Same enhanced features to a serious learned control, never a weaker-information comparison.
        arrays={}
        for s,ss in sets.items():
            xx=[];yy=[];ww=[]
            for sample in ss:
                mask=sample[-1][:,0]>0
                xx.extend(sample[0][mask]);yy.extend(sample[-2][mask,0]);ww.extend(sample[-1][mask,0])
            arrays[s]=(np.asarray(xx),np.asarray(yy),np.asarray(ww))
        candidates={}
        with threadpool_limits(limits=2):
            for leaves in (7,15):
                x,y,w=arrays['train'];tree=HistGradientBoostingRegressor(max_leaf_nodes=leaves,max_iter=100,learning_rate=.05,l2_regularization=1.,early_stopping=False,random_state=seed).fit(x,y,sample_weight=w)
                x,y,w=arrays['validation'];val=metrics(y,np.clip(tree.predict(x),0,1),w,False)
                candidates[leaves]=(val,tree)
            chosen=min(candidates,key=lambda v:candidates[v][0]['mae']);x,y,w=arrays['test']
            result['same_feature_control']={'kind':'boosted_trees','selected_leaves':chosen,'validation':candidates[chosen][0],
                'test':metrics(y,np.clip(candidates[chosen][1].predict(x),0,1),w,False),'selection':'validation MAE only'}
        public=ROOT/f'artifacts/models/phase7/yousician-context/seed-{seed}';public.mkdir(parents=True,exist_ok=True)
        torch.save(best,public/'model.pt');result['model_sha256']=c.digest(public/'model.pt')
        c.atomic_json(public/'metrics.json',result);c.atomic_json(ROOT/f'artifacts/phase7/yousician-context/seed-{seed}.json',result)
    print('context runs complete',flush=True)


if __name__=='__main__':run(sys.argv[1])
