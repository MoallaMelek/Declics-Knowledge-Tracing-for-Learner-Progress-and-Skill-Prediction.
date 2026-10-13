"""Reproducible four-way learner split, causal baselines and neural experiments."""
import argparse,copy,json,logging,random,time,platform,importlib.metadata
from pathlib import Path
import numpy as np
import torch
from torch import nn
from .data import ROOT,load_forget,generate_music,arrays,split_students,write_json
from .models import Baseline,new_neural,neural_predict
from .metrics import summary,evaluate,temperature_fit,calibrate

log=logging.getLogger('axis7.train')

def seed_all(seed):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True);torch.set_num_threads(2)

def flatten_predictions(model,learners,K,name):
    result=[]
    for u,rows in sorted(learners.items()):
        p=model.predict(rows) if name in ('prior','bkt','pfa') else neural_predict(model,rows,K)
        for t,r in enumerate(rows):
            for n,o in enumerate(r['obs']):
                if o['y'] is not None:result.append({'student':u,'attempt':r['id'],'observation':n,'position':t,
                    'skill':o['k'],'y':o['y'],'p':float(p[t,o['k']]),'original_score':o.get('score')})
    return result

def train_neural(name,K,train,val,config,seed):
    seed_all(seed);model=new_neural(name,K,config['hidden'],config['context'])
    opt=torch.optim.AdamW(model.parameters(),lr=config['learning_rate'],weight_decay=config['weight_decay'])
    sequences=[arrays(rows,K) for rows in train.values()]
    if max(len(s[0]) for s in sequences)>config['context']:raise ValueError('Increase context to preserve full training histories')
    best=1e10;best_state=None;stale=0;curve=[];rng=np.random.default_rng(seed)
    for epoch in range(config['epochs']):
        model.train();total=0;weight=0;indices=rng.permutation(len(sequences))
        for start in range(0,len(indices),config['batch_size']):
            batch=[sequences[i] for i in indices[start:start+config['batch_size']]];T=max(len(v[0]) for v in batch)
            x=torch.zeros(len(batch),T,2*K);y=torch.zeros(len(batch),T,K);w=torch.zeros_like(y)
            for j,(xx,yy,ww) in enumerate(batch):
                n=len(xx);x[j,:n]=torch.from_numpy(xx);y[j,:n]=torch.from_numpy(yy);w[j,:n]=torch.from_numpy(ww)
            opt.zero_grad();pred=model(x);losses=nn.functional.binary_cross_entropy_with_logits(pred,y,reduction='none')
            loss=(losses*w).sum()/w.sum();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5);opt.step()
            total+=float(loss.detach())*float(w.sum());weight+=float(w.sum())
        records=flatten_predictions(model,val,K,name);v=summary(np.array([r['y'] for r in records]),np.array([r['p'] for r in records]))
        curve.append({'epoch':epoch+1,'train_loss':total/weight,'validation_log_loss':v['log_loss'],'validation_auc':v['auc']})
        if v['log_loss']<best-1e-5:best=v['log_loss'];best_state=copy.deepcopy(model.state_dict());stale=0
        else:stale+=1
        if epoch%5==0:log.info('%s seed %d epoch %d val %.4f',name,seed,epoch+1,v['log_loss'])
        if stale>=config['patience']:break
    model.load_state_dict(best_state);model.eval()
    return model,curve

def baseline_save(model):
    d={'name':model.name,'K':model.K,'priors':model.priors.tolist()}
    if model.name=='bkt':d['params']=model.params
    if model.name=='pfa':d.update(coef=model.reg.coef_.tolist(),intercept=model.reg.intercept_.tolist())
    return d

def plot_artifacts(results,out):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'figure.facecolor':'#fafaf7','axes.facecolor':'#fafaf7','font.size':10})
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for r in results['runs']:
        if r.get('curve'):
            c=r['curve'];axes[0].plot([x['epoch'] for x in c],[x['train_loss'] for x in c],label=r['id'])
            axes[1].plot([x['epoch'] for x in c],[x['validation_log_loss'] for x in c],label=r['id'])
    axes[0].set(title='Training loss',xlabel='Epoch',ylabel='Binary cross entropy');axes[1].set(title='Validation loss',xlabel='Epoch',ylabel='Log loss')
    axes[1].legend(fontsize=7);fig.suptitle(results['metadata']['name']);fig.tight_layout();fig.savefig(out/'learning_curves.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,5));ax.plot([0,1],[0,1],color='#aaaaaa',linestyle='--')
    for r in results['runs']:
        if r['id'] in results['selected'].values() or r['name']=='prior':
            b=[b for b in r['test']['calibration'] if b['n']]
            ax.plot([v['mean_probability'] for v in b],[v['observed_frequency'] for v in b],marker='o',label=r['id'])
    ax.set(xlabel='Calibrated predicted probability',ylabel='Observed full-credit frequency',title='Held-out learner calibration');ax.legend();fig.tight_layout();fig.savefig(out/'calibration.png',dpi=160);plt.close(fig)
    winner=next(r for r in results['runs'] if r['id']==results['selected']['overall'])
    fig,ax=plt.subplots(figsize=(9,4));sk=winner['test']['per_skill'];ax.bar(list(sk),[v['log_loss'] for v in sk.values()],color='#547d78');ax.set(xlabel='Skill index (see manifest)',ylabel='Log loss',title=f"Per-skill error · {winner['id']}");fig.tight_layout();fig.savefig(out/'per_skill.png',dpi=160);plt.close(fig)

def run(domain,config,output_root=None):
    out=Path(output_root)/domain if output_root else ROOT/'artifacts'/domain
    if (out/'results.json').exists():
        raise FileExistsError('Historical results are immutable. Supply a new --output-root directory.')
    start=time.time();learners,meta=load_forget() if domain=='forget-se' else generate_music()
    K=len(meta['skills']);splits=split_students(learners,config['split_seed']);parts={n:{u:learners[u] for u in ids} for n,ids in splits.items()}
    out.mkdir(parents=True,exist_ok=True)
    write_json(out/'splits.json',splits);write_json(out/'metadata.json',meta)
    # Test data serialized for demo and audit, never used to fit any artifact.
    write_json(out/'heldout_learners.json',parts['test'])
    write_json(out/'dataset_audit.json',{'learners':len(learners),'groups':sum(map(len,learners.values())),
        'observations':sum(len(r['obs']) for rows in learners.values() for r in rows),
        'max_groups':max(map(len,learners.values())), 'split_counts':{n:len(v) for n,v in splits.items()},
        'label_definition':config['target'] if domain=='forget-se' else 'simulated Bernoulli outcome'})
    runs=[];prior_test=None
    for name in config['models']:
        for seed in config['seeds'] if name in ('dkt','sakt') else [0]:
            t=time.time();rid=f'{name}-{seed}'
            if name in ('dkt','sakt'):model,curve=train_neural(name,K,parts['train'],parts['validation'],config,seed)
            else:model=Baseline(name,K).fit(parts['train']);curve=[]
            val=flatten_predictions(model,parts['validation'],K,name)
            cal=flatten_predictions(model,parts['calibration'],K,name)
            ycal=np.array([r['y'] for r in cal]);pcal=np.array([r['p'] for r in cal]);temp=temperature_fit(ycal,pcal)
            test=flatten_predictions(model,parts['test'],K,name)
            raw_test=summary(np.array([r['y'] for r in test]),np.array([r['p'] for r in test]))
            for r in test:r['p_raw']=r['p'];r['p']=float(calibrate(r['p'],temp))
            if name=='prior':prior_test=np.array([r['p'] for r in test])
            metrics=evaluate(test,config['bootstrap_replicates'],prior_test)
            val_metrics=summary(np.array([r['y'] for r in val]),np.array([r['p'] for r in val]))
            checkpoint={'name':name,'K':K,'hidden':config['hidden'],'context':config['context'],'temperature':temp}
            if name in ('dkt','sakt'):torch.save(model.state_dict(),out/f'{rid}.pt')
            else:checkpoint['baseline']=baseline_save(model)
            write_json(out/f'{rid}.json',checkpoint);write_json(out/f'{rid}-predictions.json',test)
            result={'id':rid,'name':name,'seed':seed,'validation':val_metrics,'temperature':temp,'test':metrics,'test_uncalibrated':raw_test,
                'calibration_before':summary(ycal,pcal),'calibration_after':summary(ycal,calibrate(pcal,temp)),
                'curve':curve,'seconds':round(time.time()-t,2)}
            runs.append(result);log.info('%s %s test AUC %s loss %.4f (%.1fs)',domain,rid,metrics['auc'],metrics['log_loss'],result['seconds'])
    selected={'overall':min(runs,key=lambda r:r['validation']['log_loss'])['id'],
        'neural':min([r for r in runs if r['name'] in ('dkt','sakt')],key=lambda r:r['validation']['log_loss'])['id']}
    results={'metadata':meta,'config':config,'selected':selected,'runs':runs,'elapsed_seconds':round(time.time()-start,2),
        'environment':{'python':platform.python_version(),**{n:importlib.metadata.version(n) for n in ['torch','numpy','scikit-learn','pandas']}}}
    write_json(out/'results.json',results);plot_artifacts(results,out)
    # Markdown is a generated report of actual measurements, not manually authored predictions.
    lines=[f"# Measured experiments: {domain}",'',f"Selected by uncalibrated validation log loss: overall **{selected['overall']}**, best neural **{selected['neural']}**.",
        '','Four learner-disjoint sets: train 70%, selection 7.5%, calibration 7.5%, test 15%. Fixed split, three neural initialization seeds; this is not three independent test splits.',
        '', '| Model | Seed | Test ROC-AUC | Test log loss | Brier | ECE 10 |','|---|---:|---:|---:|---:|---:|']
    for r in runs:
        m=r['test'];lines.append(f"| {r['name']} | {r['seed']} | {m['auc']:.4f} | {m['log_loss']:.4f} | {m['brier']:.4f} | {m['ece_10']:.4f} |")
    lines+=['','Synthetic results validate only the controlled pipeline. FORGET-SE is software engineering, never musical performance. The full-credit threshold is fixed before fitting; tied events predicted together. No timestamp duration/forgetting or item-difficulty effect is claimed.',
        '', 'See results.json for learner-bootstrap intervals, paired log-loss differences versus prior, raw/calibrated metrics, cold/early/warm slices, per-skill metrics, confusion matrices, top errors and learning curves. Undefined AUC is null.',
        '', 'Limited sample and fixed split prevent robust population-wide conclusions. Model selection does not use test metrics; all predeclared model results are disclosed. Calibration can worsen held-out performance. Generic model does not validate musical transfer or pedagogical recommendations.']
    (out/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    return results

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    ap=argparse.ArgumentParser();ap.add_argument('--domain',choices=['forget-se','music-mock','all'],default='all');ap.add_argument('--config',default=str(ROOT/'configs/experiment.json'));ap.add_argument('--output-root');args=ap.parse_args()
    config=json.loads(Path(args.config).read_text(encoding='utf-8'))
    for domain in ['forget-se','music-mock'] if args.domain=='all' else [args.domain]:run(domain,config,args.output_root)
