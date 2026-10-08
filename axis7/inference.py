from pathlib import Path
import json
from collections import Counter
import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from .data import ROOT
from .models import Baseline,new_neural,neural_predict
from .metrics import calibrate

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

    def snapshot(self,student,rows,position=None,model_id=None):
        if model_id is not None and model_id not in self.predictors:raise ValueError('Unknown saved model')
        rid=model_id or self.default;p=self.predictors[rid];position=len(rows) if position is None else position
        if position<0 or position>len(rows):raise ValueError('History position outside learner sequence')
        # Run complete history once; causal outputs at index position are unaffected by later labels.
        predictions=p.probabilities(rows);current=predictions[position];before=predictions[max(0,position-1)]
        prefix=rows[:position];evidence=[[] for _ in range(p.K)];co=Counter()
        for t,r in enumerate(prefix):
            observed=set()
            for o in r['obs']:
                k=o['k'];observed.add(k)
                evidence[k].append({'attempt':r['id'],'position':t+1,'session':r.get('session'),
                    'timestamp':r.get('timestamp'),'exercise':r.get('exercise'),
                    'outcome':o['y'],'score':o.get('score'),'errors':o.get('errors',[]),
                    'source_confidence':o.get('confidence'),'provenance':r['provenance'],
                    'probability_before':float(predictions[t,k])})
            for a in observed:
                for b in observed:
                    if a<b:co[(a,b)]+=1
        members=[v for key,v in self.predictors.items() if v.name==p.name] if p.name in ('dkt','sakt') else []
        spread=np.array([member.probabilities(rows)[position] for member in members]) if members else None
        nodes=[]
        for k,label in enumerate(self.meta['labels']):
            seen=[v for v in evidence[k] if v['outcome'] is not None];n=len(seen);positive=sum(v['outcome'] for v in seen)
            nodes.append({'id':self.meta['skills'][k],'index':k,'label':label,'probability':float(current[k]),
                'delta':float(current[k]-before[k]) if position else 0,'observations':n,'successes':positive,
                'evidence_status':'none' if n==0 else 'limited' if n<5 else 'observed',
                'evidence':evidence[k],
                'seed_range':[float(spread[:,k].min()),float(spread[:,k].max())] if spread is not None else None,
                'curve':[{'position':t,'p':float(predictions[t,k])} for t in range(position+1)]})
        observed=[n for n in nodes if n['observations']>=3]
        if observed:
            target=min(observed,key=lambda n:n['probability'])
            recommendation={'skill_id':target['id'],'label':target['label'],'probability':target['probability'],
                'policy':'min_probability_among_skills_with_at_least_3_observations',
                'title':f"Reprendre {target['label'].lower()}",
                'text':f"Cette compétence a la plus faible probabilité prévue parmi celles avec au moins 3 observations ({target['observations']} ici). Répéter un exercice comparable et faire vérifier la cible par l’enseignant.",
                'status':'heuristic_not_validated_learning_gain','exercise_id':next((v['exercise'] for v in reversed(target['evidence']) if v['exercise']),None)}
        else:recommendation={'skill_id':None,'title':'Recueillir davantage d’observations','text':'Aucune compétence ne dispose de 3 observations binaires. Faire une courte évaluation avant de prioriser la pratique.','status':'insufficient_evidence','policy':'assessment_first'}
        sessions=[]
        for t,r in enumerate(rows):
            key=r.get('session') or r['id']
            if not sessions or sessions[-1]['id']!=key:sessions.append({'id':key,'end':t+1,'timestamp':r.get('timestamp'),'observations':len(r['obs'])})
            else:sessions[-1]['end']=t+1;sessions[-1]['observations']+=len(r['obs'])
        return {'student':student,'domain':self.domain,'metadata':self.meta,'model_id':rid,
            'default_model':self.default,'selected_overall':self.results['selected']['overall'],
            'position':position,'total_groups':len(rows),'sessions':sessions,'nodes':nodes,
            'edges':[{'a':a,'b':b,'n':n,'meaning':'co-observed in same attempt, not a prerequisite'} for (a,b),n in co.items()],
            'recommendation':recommendation,'uncertainty_note':'Variation entre initialisations, sans garantie de couverture ; aucune estimation psychologique de maîtrise.',
            'provenance_counts':dict(Counter(r['provenance'] for r in prefix)),
            'last_attempt':prefix[-1] if prefix else None}
