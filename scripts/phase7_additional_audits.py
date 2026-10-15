"""AMME grouped validation and transparent Yousician exclusion strata."""
from collections import defaultdict,Counter
import io
import json
import hashlib
from pathlib import Path
import sys
import zipfile
import numpy as np
from sklearn.model_selection import KFold
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from axis7 import cloud_training as c
from axis7.phase7_research import tabular
from axis7.scientific_validation import train_priors, metrics


def amme_cv(archive):
    prepared=c.prepare('amme',archive,ROOT/'tmp/phase7-private/amme/prepared.json.gz')
    learners=prepared['learners']; ids=np.array(sorted(learners)); results=[]
    for fold,(train_index,test_index) in enumerate(KFold(5,shuffle=True,random_state=701).split(ids)):
        outer=ids[train_index]; test=ids[test_index]
        inner=outer.copy();np.random.default_rng(701+fold).shuffle(inner)
        cut=max(1,int(.8*len(inner))); train=list(inner[:cut]); val=list(inner[cut:])
        _,prior,_=train_priors(learners,train,1)
        arrays={s:tabular(learners,selected,1,prior) for s,selected in [('train',train),('validation',val),('test',list(test))]}
        scaler=StandardScaler().fit(arrays['train'][0]); candidates={}
        for alpha in (.01,1.,100.):
            x,y,w=arrays['train']; model=Ridge(alpha=alpha).fit(scaler.transform(x),y,sample_weight=w)
            vx,vy,vw=arrays['validation']; pred=np.clip(model.predict(scaler.transform(vx)),0,1)
            candidates[alpha]=(metrics(vy,pred,vw,False)['mae'],model)
        selected=min(candidates,key=lambda a:candidates[a][0]); model=candidates[selected][1]
        x,y,w=arrays['test'];pred=np.clip(model.predict(scaler.transform(x)),0,1)
        results.append({'fold':fold,'learners':{'train':len(train),'validation':len(val),'test':len(test)},
            'selected_alpha':selected,'validation_mae':candidates[selected][0], 'test':metrics(y,pred,w,False),
            'median_absolute_error':float(np.median(abs(y-pred))),
            'p90_absolute_error':float(np.quantile(abs(y-pred),.9)),
            'test_by_previous_group_count': {str(block):metrics(y[x[:,7]==np.log1p(block)],pred[x[:,7]==np.log1p(block)],w[x[:,7]==np.log1p(block)],False)
               for block in sorted({int(round(np.expm1(v))) for v in x[:,7]}) if (x[:,7]==np.log1p(block)).any()}})
    report={'method':'5 outer learner-grouped folds; 80/20 inner learner training/validation; fixed seed 701',
        'target':'unchanged AMME scoretype7 next block mean; adjusted melodic similarity, not correctness',
        'folds':results,'mean_test_mae':float(np.mean([r['test']['mae'] for r in results])),
        'sample_sd_test_mae':float(np.std([r['test']['mae'] for r in results],ddof=1)),
        'limitations':['Small sample; fold variation is descriptive.','Median/p90 errors describe outliers, not a robust-regression treatment.','Historical group count is reported; not elapsed practice time.'],
        'status':'research_only'}
    c.atomic_json(ROOT/'artifacts/phase7/amme/grouped-cv.json',report)
    print('AMME grouped CV:',report['mean_test_mae'],flush=True)


def yousician_audit(archive):
    groups={};seen=set();days=defaultdict(set)
    with zipfile.ZipFile(archive) as z:
        member=next(n for n in z.namelist() if n.endswith('.json'))
        with io.TextIOWrapper(z.open(member),encoding='utf-8-sig') as f:
            for r in c.stream_array(f):
                fp=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).digest()
                if fp in seen:continue
                seen.add(fp)
                if r['play_mode']!='play':continue
                key=(str(r['user_id']),int(r['session_index']),float(r['days_since_signup']),str(r['exercise_id']),str(r['song_id']))
                g=groups.setdefault(key,{'counts':set(),'difficulty':set()})
                g['counts'].add(tuple(int(r[k]) for k in ('notes_evaluated','notes_successful','chords_evaluated','chords_successful')))
                g['difficulty'].add(str(r['difficulty_level']));days[key[0]].add(int(key[2]))
    past_days={p:{day:i for i,day in enumerate(sorted(ds))} for p,ds in days.items()}
    strata=defaultdict(Counter)
    for key,g in groups.items():
        status='excluded_contradictory' if len(g['counts'])>1 else 'retained' if sum(next(iter(g['counts']))[::2])>0 else 'zero_evaluated'
        scores=[(a+b)/(n+m) for n,a,m,b in g['counts'] if n+m]
        # Ranges are observed alternative counters, never guessed final outcomes.
        score_bucket='no_evaluation' if not scores else 'all_observed_alternatives_below_0.5' if max(scores)<.5 else 'all_observed_alternatives_at_least_0.8' if min(scores)>=.8 else 'mixed_or_intermediate_observed_alternatives'
        n=past_days[key[0]][int(key[2])]
        history='0_prior_days' if n==0 else '1_2_prior_days' if n<3 else '3_9_prior_days' if n<10 else '10plus_prior_days'
        session='session_index_0_2' if key[1]<3 else 'session_index_3_9' if key[1]<10 else 'session_index_10plus'
        for category in ('all','difficulty:'+'|'.join(sorted(g['difficulty'])),history,session,score_bucket):
            strata[category][status]+=1
    c.atomic_json(ROOT/'artifacts/phase7/yousician/exclusion-diagnostics.json',
       {'unit':'same tied groups as Phase 6 after exact dedup and practice removal',
        'strata':{k:dict(v) for k,v in sorted(strata.items())},
        'performance_definition':'Ranges of recorded counter alternatives, not recovered true outcomes for excluded groups.',
        'history_definition':'Number of earlier distinct recorded signup days, including days with later-excluded groups; diagnostic only.',
        'attempt_reconstruction':'unsupported: no unique attempt identifier; next-active-day target retained',
        'limitations':['Descriptive selection diagnostics, not causal missingness correction.','No missing labels imputed.']})
    print('Yousician diagnostics:',dict(strata['all']),flush=True)


if __name__=='__main__':
    amme_cv(sys.argv[1]);yousician_audit(sys.argv[2])
