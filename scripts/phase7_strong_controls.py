"""Additional prespecified controls, trained only for scientific comparison.

PFA-style per-concept regularized logistic and histogram gradient boosting.
No classical estimator is promoted to the musical serving registry.
"""
from pathlib import Path
import sys
import warnings
import numpy as np
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier,HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from axis7 import cloud_training as c
from axis7.phase7_research import tabular
from axis7.scientific_validation import train_priors,metrics


def pfa_design(x,K):
    concept=np.rint(x[:,0]*max(K-1,1)).astype(int)
    i=np.arange(len(x)); one=sparse.csr_matrix((np.ones(len(x)),(i,concept)),shape=(len(x),K))
    return sparse.hstack((one,one.multiply(x[:,2,None]),one.multiply(x[:,3,None])),format='csr')


def run(source,archive):
    prepared=c.prepare(source,archive,ROOT/f'tmp/phase7-private/{source}/prepared.json.gz')
    learners=prepared['learners'];binary=source=='singpad';key='log_loss' if binary else 'mae'
    K=max(int(o[0]) for rows in learners.values() for r in rows for o in r['obs'])+1
    for seed in (42,17,83):
        split=c.split_learners(learners,seed);_,prior,_=train_priors(learners,split['train'],K)
        arrays={s:tabular(learners,ids,K,prior) for s,ids in split.items()}
        report={'source':source,'seed':seed,'splits':c.public_split_provenance(split),
            'protocol':'PFA logistic C [.01,1,100]; boosted trees leaves [7,15], 100 iterations, lr .05, l2=1; all choices validation only',
            'dataset_sha256':prepared['sha256'],'scope':'research controls only, no deployed classical ML',
            'models':{}}
        for name in (('pfa_logistic','boosted_trees') if binary else ('boosted_trees',)):
            choices=(.01,1.,100.) if name=='pfa_logistic' else (7,15)
            trained={};validation={}
            for choice in choices:
                x,y,w=arrays['train'];design=pfa_design(x,K) if name=='pfa_logistic' else x
                with threadpool_limits(limits=2),warnings.catch_warnings():
                    warnings.simplefilter('error',ConvergenceWarning)
                    if binary:
                        xx=sparse.vstack((design,design),format='csr') if sparse.issparse(design) else np.concatenate((design,design))
                        yy=np.r_[np.ones(len(y)),np.zeros(len(y))];ww=np.r_[w*y,w*(1-y)];keep=ww>0
                        estimator=LogisticRegression(C=choice,max_iter=2000,solver='lbfgs') if name=='pfa_logistic' else HistGradientBoostingClassifier(max_leaf_nodes=choice,max_iter=100,learning_rate=.05,l2_regularization=1.,early_stopping=False,random_state=seed)
                        estimator.fit(xx[keep],yy[keep],sample_weight=ww[keep])
                    else:
                        estimator=HistGradientBoostingRegressor(max_leaf_nodes=choice,max_iter=100,learning_rate=.05,l2_regularization=1.,early_stopping=False,random_state=seed)
                        estimator.fit(design,y,sample_weight=w)
                trained[str(choice)]=estimator
                x,y,w=arrays['validation'];design=pfa_design(x,K) if name=='pfa_logistic' else x
                pred=estimator.predict_proba(design)[:,1] if binary else np.clip(estimator.predict(design),0,1)
                validation[str(choice)]=metrics(y,pred,w,binary)
            selected=min(validation,key=lambda a:validation[a][key]);estimator=trained[selected]
            x,y,w=arrays['test'];design=pfa_design(x,K) if name=='pfa_logistic' else x
            with threadpool_limits(limits=2):
                pred=estimator.predict_proba(design)[:,1] if binary else np.clip(estimator.predict(design),0,1)
            report['models'][name]={'selected_parameter':selected,'validation_candidates':validation,
                                     'test':metrics(y,pred,w,binary)}
        selected=min(report['models'],key=lambda n:min(v[key] for v in report['models'][n]['validation_candidates'].values()))
        report['selected_strong_control']=selected
        c.atomic_json(ROOT/f'artifacts/phase7/{source}/seed-{seed}/strong-controls.json',report)
        print(source,seed,selected,report['models'][selected]['test'][key],flush=True)


if __name__=='__main__':run(sys.argv[1],sys.argv[2])
