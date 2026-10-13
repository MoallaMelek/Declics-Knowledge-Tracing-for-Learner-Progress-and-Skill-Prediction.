"""Frozen-checkpoint stress diagnostic, never empirical musical validation.

History errors are injected after fitting. Clean target outcomes remain separate.
For history-dropout, only common retained target rows are scored for both clean
and perturbed inputs. An unknown-item perturbation is not exercise-disjoint fit.
"""
from pathlib import Path
import argparse,copy,hashlib,json,sys
import numpy as np
import torch
from threadpoolctl import threadpool_limits
from scipy.special import expit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from axis7.data import load_forget,generate_music,split_students
from axis7.models_v2 import ResearchPredictor,ItemEncoder
from axis7.metrics import summary,grouped_bootstrap
from scripts.global_history_control import rows_features

def perturb(rows,condition,seed):
    changed=copy.deepcopy(rows);rng=np.random.default_rng(seed);keep=np.ones(len(rows),dtype=bool)
    for t,row in enumerate(changed):
        if condition=='history_dropout_30' and rng.random()<.3:
            keep[t]=False
            for obs in row['obs']:obs['eligible']=False;obs['eligibility_reason']='injected_missing_source'
        if condition.startswith('history_noise_'):
            rate=int(condition.rsplit('_',1)[1])/100
            for obs in row['obs']:
                if rng.random()<rate:obs['y']=1-obs['y']
        if condition=='unknown_item_query':
            row['exercise']='phase3-unseen-item'
            for obs in row['obs']:obs.pop('question',None)
    return changed,keep

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2)
    threadpool_limits(limits=2)
    script_bytes=Path(__file__).read_bytes()
    (args.output/'source.py').write_bytes(script_bytes)
    pointer=json.loads((ROOT/'artifacts/v2/index.json').read_text(encoding='utf8'))
    study=json.loads((ROOT/pointer['summary']).read_text(encoding='utf8'))
    result={'status':'frozen_checkpoint_stress_diagnostic','primary_study_id':study['experiment_id'],
        'split_seed':2026,'perturbation_seed':9041,'no_retraining':True,'target':'original clean binary outcome',
        'conditions':['clean','history_noise_10','history_noise_25','history_dropout_30','unknown_item_query'],
        'limitations':['Real domain is software engineering; musical domain is synthetic.',
        'Noise rates are arbitrary stress levels, not measured upstream error distributions.',
        'Unknown-item perturbation is not an exercise-disjoint training experiment.',
        'Dropout contrasts use identical retained targets; raw cross-condition means are not directly comparable.',
        'Global-history logistic is the separately labelled posthoc comparator, not preregistered.',
        'Only one fixed learner split; bootstrap is conditional on this cohort and frozen fit.'], 'runs':[]}
    for domain in ['forget-se','music-mock']:
        learners,meta=load_forget() if domain=='forget-se' else generate_music()
        split=split_students(learners,2026);test={u:learners[u] for u in sorted(split['test'])};K=len(meta['skills'])
        directory=ROOT/'artifacts/v2'/study['experiment_id']/domain/'split-2026'
        saved_split=json.loads((directory/'splits.json').read_text(encoding='utf8'))
        assert saved_split==split
        models={name:ResearchPredictor(directory,name) for name in ['dkt-7','enhanced_gru-7','item_pfa-0']}
        g=json.loads((ROOT/'artifacts/v2/exploratory-global-control'/f'{domain}-2026-model.json').read_text(encoding='utf8'))
        items=ItemEncoder(g['items']);coefs=np.array(g['coef'][0]);intercept=g['intercept'][0]
        for name in [*models,'global_history_logistic']:
            clean_by_user={}
            for u,rows in test.items():
                clean_by_user[u]=(models[name].probabilities(rows) if name in models else expit(rows_features(rows,K,items)[0]@coefs+intercept))
            for condition in result['conditions']:
                records=[];reference=[];ordinal=0
                for n,(u,rows) in enumerate(test.items()):
                    changed,keep=perturb(rows,condition,9041+n)
                    if name in models:
                        p=models[name].probabilities(changed)
                    else:p=expit(rows_features(changed,K,items)[0]@coefs+intercept)
                    j=0;clean_j=0;counts=np.zeros(K,dtype=int)
                    for t,row in enumerate(rows):
                        for o in row['obs']:
                            if keep[t]:
                                prob=float(p[t,o['k']]) if name in models else float(p[j])
                                before=float(clean_by_user[u][t,o['k']]) if name in models else float(clean_by_user[u][clean_j])
                                records.append({'student':u,'attempt':row['id'],'skill':o['k'],'y':o['y'],'p':prob,'prior_skill_observations':int(counts[o['k']])});reference.append(before);j+=1
                            clean_j+=1
                        if keep[t]:
                            for o in row['obs']:counts[o['k']]+=1
                y=np.array([r['y'] for r in records]);p=np.array([r['p'] for r in records]);users=np.array([r['student'] for r in records]);ref=np.array(reference)
                slices={}
                for label,lo,hi in [('cold_0',0,0),('few_1_2',1,2),('history_3_9',3,9),('history_10_plus',10,10**9)]:
                    ix=np.array([lo<=r['prior_skill_observations']<=hi for r in records]);slices[label]={'n':int(ix.sum()),'metrics':summary(y[ix],p[ix]) if ix.any() else None}
                metric=summary(y,p);clean=summary(y,ref)
                entry={'domain':domain,'model':name,'condition':condition,'targets':len(records),'learners':len(test),'metrics':metric,'same_targets_clean_metrics':clean,
                    'delta_log_loss':metric['log_loss']-clean['log_loss'],
                    'paired_log_loss_delta_95':grouped_bootstrap(y,p,users,300,2026,ref)['log_loss_difference_vs_prior'],
                    'cold_start_slices':slices}
                result['runs'].append(entry)
                (args.output/f'{domain}-{name}-{condition}-predictions.json').write_text(json.dumps(records,separators=(',',':')),encoding='utf8')
                print(json.dumps({k:entry[k] for k in ['domain','model','condition','targets','delta_log_loss']}),flush=True)
    result['script_sha256']=hashlib.sha256(script_bytes).hexdigest()
    result['source_study_summary_sha256']=hashlib.sha256((ROOT/pointer['summary']).read_bytes()).hexdigest()
    (args.output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf8')

if __name__=='__main__':main()
