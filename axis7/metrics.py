import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import expit,logit
from sklearn.metrics import roc_auc_score,average_precision_score,log_loss,brier_score_loss,accuracy_score,f1_score,confusion_matrix

def temperature_fit(y,p):
    logits=logit(np.clip(p,1e-6,1-1e-6))
    fit=minimize_scalar(lambda t:log_loss(y,expit(logits/t),labels=[0,1]),bounds=(.5,5),method='bounded')
    return float(fit.x)

def calibrate(p,temperature):return expit(logit(np.clip(p,1e-6,1-1e-6))/temperature)

def calibration_bins(y,p):
    result=[]
    for i in range(10):
        m=(p>=i/10)&(p<(i+1)/10 if i<9 else p<=1)
        result.append({"lower":i/10,"upper":(i+1)/10,"n":int(m.sum()),
            "mean_probability":float(np.mean(p[m])) if m.any() else None,
            "observed_frequency":float(np.mean(y[m])) if m.any() else None})
    return result

def summary(y,p):
    y=np.asarray(y);p=np.asarray(p);pred=p>=.5
    if not len(y):return None
    bins=calibration_bins(y,p)
    return {"n":len(y),"positive_rate":float(np.mean(y)),
        "auc":float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None,
        "pr_auc":float(average_precision_score(y,p)) if np.any(y==1) else None,
        "log_loss":float(log_loss(y,p,labels=[0,1])),"brier":float(brier_score_loss(y,p)),
        "accuracy":float(accuracy_score(y,pred)),"f1":float(f1_score(y,pred,zero_division=0)),
        "ece_10":float(sum(b['n']*abs(b['mean_probability']-b['observed_frequency']) for b in bins if b['n'])/len(y)),
        "confusion_matrix":confusion_matrix(y,pred,labels=[0,1]).tolist(),"calibration":bins}

def grouped_bootstrap(y,p,users,replicates=300,seed=2026,reference=None):
    y=np.asarray(y);p=np.asarray(p);users=np.asarray(users)
    if reference is not None:reference=np.asarray(reference)
    if y.ndim!=1 or p.ndim!=1 or users.ndim!=1 or not (len(y)==len(p)==len(users)):
        raise ValueError('bootstrap inputs must be aligned one-dimensional sequences')
    if not len(y):raise ValueError('bootstrap requires at least one observation')
    if reference is not None and (reference.ndim!=1 or len(reference)!=len(y)):
        raise ValueError('reference predictions must align with observations')
    if isinstance(replicates,bool) or not isinstance(replicates,(int,np.integer)) or replicates<1:
        raise ValueError('replicates must be a positive integer')
    ids=np.unique(users);groups=[np.flatnonzero(users==u) for u in ids]
    rng=np.random.default_rng(seed);stats={'auc':[],'log_loss':[],'brier':[]}
    differences=[]
    for _ in range(replicates):
        idx=np.concatenate([groups[j] for j in rng.integers(0,len(groups),len(groups))])
        yy,pp=y[idx],p[idx]
        if len(np.unique(yy))==2:stats['auc'].append(float(roc_auc_score(yy,pp)))
        stats['log_loss'].append(float(log_loss(yy,pp,labels=[0,1])))
        stats['brier'].append(float(np.mean((yy-pp)**2)))
        if reference is not None:
            differences.append(float(log_loss(yy,pp,labels=[0,1])-log_loss(yy,reference[idx],labels=[0,1])))
    result={k:[float(x) for x in np.quantile(v,[.025,.975])] if v else None for k,v in stats.items()}
    if differences:result['log_loss_difference_vs_prior']=[float(x) for x in np.quantile(differences,[.025,.975])]
    result['unit']='held-out learner';result['replicates']=replicates
    return result

def evaluate(records,replicates=300,reference=None):
    y=np.array([r['y'] for r in records]);p=np.array([r['p'] for r in records]);users=np.array([r['student'] for r in records])
    metrics=summary(y,p);metrics['bootstrap_95']=grouped_bootstrap(y,p,users,replicates,reference=reference)
    skills=sorted({r['skill'] for r in records})
    metrics['per_skill']={str(k):summary(y[[r['skill']==k for r in records]],p[[r['skill']==k for r in records]]) for k in skills}
    metrics['history_slices']={label:summary(y[mask],p[mask]) for label,mask in {
        'cold_start':np.array([r['position']==0 for r in records]),
        'early_1_to_4':np.array([1<=r['position']<=4 for r in records]),
        'warm_5_plus':np.array([r['position']>=5 for r in records])}.items()}
    macro=[summary(y[users==u],p[users==u]) for u in np.unique(users)]
    metrics['macro_learner_log_loss']=float(np.mean([m['log_loss'] for m in macro]))
    valid_auc=[m['auc'] for m in macro if m['auc'] is not None]
    metrics['macro_learner_auc']=float(np.mean(valid_auc)) if valid_auc else None
    metrics['top_errors']=sorted(records,key=lambda r:abs(r['p']-r['y']),reverse=True)[:20]
    return metrics
