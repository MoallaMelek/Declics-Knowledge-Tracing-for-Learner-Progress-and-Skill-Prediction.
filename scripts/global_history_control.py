"""Exploratory POSTHOC matched-information control; not part of preregistered102-run study.

The design was motivated by seeing that EGRU sees cross-KC history while the main
item-PFA sees target-KC counts only. Run once after the original study finishes,
without changing its artifacts or retraining any neural model. It is a diagnostic,
not a new unbiased confirmatory model-selection experiment.
"""
import os,sys,json,statistics,time
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits
os.environ['PYTHONDONTWRITEBYTECODE']='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from axis7.data import load_forget,generate_music,split_students
from axis7.eligibility import eligible
from axis7.models_v2 import ItemEncoder
from axis7.metrics import summary,grouped_bootstrap


def rows_features(rows,K,items):
    S=np.zeros(K);F=np.zeros(K);X=[];Y=[];records=[]
    for t,r in enumerate(rows):
        iid,difficulty=items.encode(r)
        for n,o in enumerate(r['obs']):
            if not eligible(o):continue
            k=o['k']; own=np.zeros(2*K);own[k]=np.log1p(S[k]);own[K+k]=np.log1p(F[k])
            feat=np.r_[np.eye(K)[k],own,np.log1p(S),np.log1p(F),np.eye(items.size)[iid],
                       difficulty,np.log1p(t),(S.sum()+1)/(S.sum()+F.sum()+2),(S[k]+1)/(S[k]+F[k]+2)]
            X.append(feat);Y.append(o['y']);records.append({'student':r['student'],'attempt':r['id'],
                'observation':n,'position':t,'skill':k,'y':o['y'],'skill_history_count':int(S[k]+F[k])})
        for o in r['obs']:
            if eligible(o):S[o['k']]+=o['y'];F[o['k']]+=1-o['y']
    return np.asarray(X),np.asarray(Y),records


def main():
    index=json.loads((ROOT/'artifacts/v2/index.json').read_text(encoding='utf8'));study=json.loads((ROOT/index['summary']).read_text(encoding='utf8'))
    config={'status':'exploratory_posthoc','estimator':'L2 logistic C1 max_iter2000',
            'features':['skill','target_KC_log_success_failure_counts','all_KC_log_success_failure_counts',
                        'known_atomic_item_onehot','train_only_item_difficulty','log_sequence_position',
                        'smoothed_global_success_fraction','smoothed_target_KC_success_fraction'],
            'selection':'no tuning; compare to existing validation-selected neural; never replace mainstudy selections',
            'retraining':'no neural retraining','threads':2,'bootstrap_replicates':300}
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    output=parser.parse_args().output;output.mkdir(parents=True,exist_ok=False)
    (output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf8')
    results=[]
    for domain in ['forget-se','music-mock']:
        learners,meta=load_forget() if domain=='forget-se' else generate_music();K=len(meta['skills'])
        for split_seed in study['config']['split_seeds']:
            split=split_students(learners,split_seed);parts={p:{u:learners[u] for u in ids} for p,ids in split.items()}
            items=ItemEncoder().fit(parts['train']);samples=[rows_features(r,K,items) for r in parts['train'].values()]
            begin=time.perf_counter()
            with threadpool_limits(limits=2):
                model=LogisticRegression(C=1.,max_iter=2000,random_state=0).fit(np.concatenate([s[0] for s in samples]),np.concatenate([s[1] for s in samples]))
            reports={};test_records=[]
            for part in ['validation','test']:
                all_records=[]
                for user,rows in sorted(parts[part].items()):
                    X,y,records=rows_features(rows,K,items);p=model.predict_proba(X)[:,1]
                    for r,prob in zip(records,p):r['p']=float(prob)
                    all_records.extend(records)
                reports[part]=summary(np.array([r['y'] for r in all_records]),np.array([r['p'] for r in all_records]))
                if part=='test':test_records=all_records
            selected_info=next(r for r in study['splits'] if r['domain']==domain and r['split_seed']==split_seed)
            selected_id=selected_info['selected']['neural'];run=next(r for r in study['rawruns'] if r['domain']==domain and r['split_seed']==split_seed and r['id']==selected_id)
            nn_records=json.loads((ROOT/run['checkpoint_directory']/(selected_id+'-predictions.json')).read_text(encoding='utf8'))
            identity=lambda rs:[(r['student'],r['attempt'],r['observation'],r['y']) for r in rs]
            assert identity(nn_records)==identity(test_records)
            y=np.array([r['y'] for r in nn_records]);p=np.array([r['p_raw'] for r in nn_records]);users=np.array([r['student'] for r in nn_records]);ref=np.array([r['p'] for r in test_records])
            interval=grouped_bootstrap(y,p,users,300,2026,ref)['log_loss_difference_vs_prior']
            result={'domain':domain,'split_seed':split_seed,'status':'exploratory_posthoc','metrics':reports,
                    'selected_neural':selected_id,'selected_neural_auc':run['raw']['auc'],'selected_neural_log_loss':run['raw']['log_loss'],
                    'selected_neural_minus_global_control_log_loss_95':interval,
                    'seconds':time.perf_counter()-begin,'features':len(model.coef_[0])}
            results.append(result)
            rid=f'{domain}-{split_seed}'
            (output/(rid+'-predictions.json')).write_text(json.dumps(test_records,indent=2),encoding='utf8')
            (output/(rid+'-model.json')).write_text(json.dumps({'coef':model.coef_.tolist(),'intercept':model.intercept_.tolist(),'items':items.state,'K':K,'config':config},indent=2),encoding='utf8')
            print(json.dumps(result),flush=True)
    aggregate={d:{m:statistics.mean(r['metrics']['test'][m] for r in results if r['domain']==d) for m in ['auc','log_loss','brier','ece_10']} for d in ['forget-se','music-mock']}
    (output/'summary.json').write_text(json.dumps({'experiment_id':index['latest'],'config':config,'results':results,'aggregate':aggregate},indent=2),encoding='utf8')


if __name__=='__main__':main()

