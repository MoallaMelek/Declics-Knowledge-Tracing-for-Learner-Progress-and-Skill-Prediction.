from pathlib import Path
import json
from collections import Counter
import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from .data import ROOT
from .models import Baseline,new_neural,neural_predict
from .metrics import calibrate
from .eligibility import eligible
from .recommendations import recommend

def uses_items(predictor):
    return predictor.name in ('enhanced_gru','enhanced_gru_no_outcome','item_attention','item_pfa')

class Predictor:
    def __init__(self,directory,rid):
        self.directory=Path(directory);self.rid=rid
        self.config=json.loads((self.directory/f'{rid}.json').read_text(encoding='utf-8'))
        c=self.config;self.K=c['K'];self.name=c['name']
        if self.name in ('dkt','sakt'):
            self.model=new_neural(self.name,c['K'],c['hidden'],c['context'])
            self.model.load_state_dict(torch.load(self.directory/f'{rid}.pt',map_location='cpu',weights_only=True));self.model.eval()
        else:
            b=c['baseline'];self.model=Baseline(self.name,c['K']);self.model.priors=np.array(b['priors'])
            if self.name=='bkt':self.model.params=b['params']
            if self.name=='pfa':
                self.model.reg=LogisticRegression();self.model.reg.coef_=np.array(b['coef']);self.model.reg.intercept_=np.array(b['intercept'])
                self.model.reg.classes_=np.array([0,1]);self.model.reg.n_features_in_=3*self.K
    def probabilities(self,rows):
        p=neural_predict(self.model,rows,self.K,query=True) if self.name in ('dkt','sakt') else self.model.predict(rows,append_query=True)
        return calibrate(p,self.config['temperature'])

class TwinEngine:
    def __init__(self,domain):
        torch.set_num_threads(2);self.domain=domain;self.directory=ROOT/'artifacts'/domain
        if not (self.directory/'results.json').exists():raise FileNotFoundError(f'Train {domain} first: python -m axis7.train --domain {domain}')
        self.results=json.loads((self.directory/'results.json').read_text(encoding='utf-8'))
        self.meta=self.results['metadata'];self.learners=json.loads((self.directory/'heldout_learners.json').read_text(encoding='utf-8'))
        self.predictors={r['id']:Predictor(self.directory,r['id']) for r in self.results['runs']}
        self.default=self.results['selected']['neural'] if domain=='music-mock' else self.results['selected']['overall']

    def snapshot(self,student,rows,position=None,model_id=None,policy='balanced'):
        if model_id is not None and model_id not in self.predictors:raise ValueError('Unknown saved model')
        rid=model_id or self.default;p=self.predictors[rid];position=len(rows) if position is None else position
        if position<0 or position>len(rows):raise ValueError('History position outside learner sequence')
        # Historical outputs condition the known attempted exercise; generic replay queries use only the visible prefix.
        prefix=rows[:position]
        predictions=p.probabilities(prefix)
        current=predictions[-1]
        before=p.probabilities(prefix[:-1])[-1] if position else current
        recent_start=p.probabilities(prefix[:max(0,position-5)])[-1] if position else current
        prefix=rows[:position];evidence=[[] for _ in range(p.K)];co=Counter()
        for t,r in enumerate(prefix):
            observed=set()
            for o in r['obs']:
                k=o['k']
                if k is None or not 0<=k<p.K:continue
                observed.add(k)
                evidence[k].append({'attempt':r['id'],'position':t+1,'session':r.get('session'),
                    'timestamp':r.get('timestamp'),'exercise':r.get('exercise'),
                    'outcome':o['y'],'score':o.get('score'),'errors':o.get('errors',[]),
                    'eligible':eligible(o),'eligibility_reason':o.get('eligibility_reason'),
                    'source_confidence':o.get('confidence'),'provenance':r['provenance'],
                    'probability_before':float(predictions[t,k])})
            for a in observed:
                for b in observed:
                    if a<b:co[(a,b)]+=1
        version=getattr(p,'serving_implementation_version',p.config.get('implementation_version','legacy-v1'))
        members=[v for key,v in self.predictors.items() if v.name==p.name and
                 getattr(v,'serving_implementation_version',v.config.get('implementation_version','legacy-v1'))==version] if hasattr(p.model,'parameters') else []
        spread=np.array([member.probabilities(prefix)[-1] for member in members]) if members else None
        nodes=[]
        for k,label in enumerate(self.meta['labels']):
            seen=[v for v in evidence[k] if v['eligible']];n=len(seen);positive=sum(v['outcome'] for v in seen)
            nodes.append({'id':self.meta['skills'][k],'index':k,'label':label,'probability':float(current[k]),
                'delta':float(current[k]-before[k]) if position else 0,'observations':n,'successes':positive,
                'generic_recent_change':float(current[k]-recent_start[k]),
                'evidence_status':'none' if n==0 else 'limited' if n<5 else 'observed',
                'evidence':evidence[k],
                'seed_range':[float(spread[:,k].min()),float(spread[:,k].max())] if spread is not None else None,
                'curve':[{'position':t,'p':float(predictions[t,k])} for t in range(position+1)]})
        recommendation=recommend(nodes,policy)
        sessions=[]
        for t,r in enumerate(rows):
            key=r.get('session') or r['id']
            if not sessions or sessions[-1]['id']!=key:sessions.append({'id':key,'end':t+1,'timestamp':r.get('timestamp'),'observations':len(r['obs'])})
            else:sessions[-1]['end']=t+1;sessions[-1]['observations']+=len(r['obs'])
        return {'student':student,'domain':self.domain,'metadata':self.meta,'model_id':rid,'model_name':p.name,
            'response_version':'2.0','forecast_semantics':'next_binary_outcome_not_psychological_mastery',
            'training_implementation_version':p.config.get('implementation_version','legacy-v1'),
            'model_provenance':'synthetic' if self.domain=='music-mock' else 'public_software_engineering',
            'model_update_events':sum(any(eligible(o) for o in r['obs']) for r in prefix),
            'observation_only_events':sum(not any(eligible(o) for o in r['obs']) for r in prefix),
            'unmodeled_observations':sum(o.get('k') is None for r in prefix for o in r['obs']),
            'unmodeled_evidence':[{'attempt':r['id'],'timestamp':r.get('timestamp'),'provenance':r['provenance'],
                'skill_id':o.get('skill_id'),'outcome':o.get('y'),'score':o.get('score'),
                'eligibility_reason':o.get('eligibility_reason')} for r in prefix for o in r['obs'] if o.get('k') is None],
            'default_model':self.default,'selected_overall':getattr(self,'v2_selected_overall',None) or self.results['selected']['overall'],
            'curve_conditioning':'known_attempted_exercise_then_generic_next_query' if uses_items(p) else 'skill_only','implementation_version':version,'forecast_conditioning':'unknown_exercise_skill_forecast' if uses_items(p) else 'skill_only',
            'position':position,'total_groups':len(rows),'sessions':sessions,'nodes':nodes,
            'edges':[{'a':a,'b':b,'n':n,'meaning':'co-observed in same attempt, not a prerequisite'} for (a,b),n in co.items()],
            'recommendation':recommendation,'uncertainty_note':'Variation entre initialisations, sans garantie de couverture ; aucune estimation psychologique de maîtrise.',
            'provenance_counts':dict(Counter(r['provenance'] for r in prefix)),
            'last_attempt':prefix[-1] if prefix else None,
            'latest_timestamp':max((r for r in rows if r.get('timestamp')),key=lambda r:r['order'],default={}).get('timestamp')}
