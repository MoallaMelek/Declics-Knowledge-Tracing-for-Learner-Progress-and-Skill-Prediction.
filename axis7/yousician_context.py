"""Historical day metadata; no next-day difficulty, duration or exercise mix."""
from collections import defaultdict
import hashlib
import io
import json
import math
import zipfile
import numpy as np
from torch import nn
import torch
from . import cloud_training as c

FEATURES=['previous_day_difficulty_scaled','previous_day_difficulty_missing',
    'previous_day_exercise_diversity_log','previous_day_evaluated_counter_log',
    'previous_day_session_diversity_log','cumulative_evaluated_counter_log',
    'cumulative_exercise_diversity_log','previous_observed_day_gap_log','rolling3_day_score']


def enrich(archive,prepared):
    groups={};seen=set()
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
                g['difficulty'].add(float(r['difficulty_level']))
    days=defaultdict(lambda:{'success':0,'total':0,'difficulty_sum':0.,'difficulty_count':0.,'exercises':set(),'sessions':set()})
    for key,g in groups.items():
        if len(g['counts'])!=1:continue
        n,a,m,b=next(iter(g['counts']));weight=n+m
        if not weight:continue
        d=days[(key[0],int(math.floor(key[2])))];d['success']+=a+b;d['total']+=weight
        d['exercises'].add(key[3]);d['sessions'].add(key[1])
        if len(g['difficulty'])==1:
            difficulty=next(iter(g['difficulty']))
            if not math.isfinite(difficulty) or not 0<=difficulty<=10:raise ValueError('Invalid documented difficulty scale')
            d['difficulty_sum']+=difficulty*weight;d['difficulty_count']+=weight
    result={}
    for learner,rows in prepared['learners'].items():
        previous=None;all_exercises=set();total=0;history=[];new=[]
        for t,row in enumerate(rows):
            day=days[(learner,row['time'])]
            if not np.isclose(day['success']/day['total'],row['obs'][0][1],rtol=0,atol=1e-12):
                raise ValueError('Enriched daily labels differ from validated preprocessing')
            gap=rows[t-1]['time']-rows[t-2]['time'] if t>=2 else 0
            context=np.zeros(len(FEATURES),np.float32)
            if previous:
                context=np.array([previous['difficulty_sum']/previous['difficulty_count']/10 if previous['difficulty_count'] else 0.,
                    float(previous['difficulty_count']==0),math.log1p(len(previous['exercises'])),math.log1p(previous['total']),
                    math.log1p(len(previous['sessions'])),math.log1p(total),math.log1p(len(all_exercises)),
                    math.log1p(max(gap,0)),np.mean(history[-3:])],np.float32)
            new.append({**row,'context':context.tolist()})
            previous=day;total+=day['total'];all_exercises.update(day['exercises']);history.append(row['obs'][0][1])
        result[learner]=new
    return {**prepared,'learners':result,'context_features':FEATURES,
            'context_preprocessing':'retained-day-past-metadata-v1'}


def encode(rows,items):
    values=list(c.encode(rows,1,items))
    values[0]=np.concatenate((values[0],np.asarray([r['context'] for r in rows],np.float32)),axis=1)
    return tuple(values)


def samples(learners,ids,items):
    result=[]
    for p in ids:
        values=encode(learners[p],items)
        for start in range(0,len(learners[p]),63):
            left=max(start-1,0);stop=min(start+63,len(learners[p]))
            sample=tuple(a[left:stop].copy() for a in values)
            if start:sample[-1][0]=0
            if sample[-1].sum():result.append(sample)
    return result


class ContextGRU(nn.Module):
    def __init__(self):
        super().__init__();self.K=1
        self.encoder=nn.GRU(4+len(FEATURES),48,batch_first=True)
        self.output=nn.Sequential(nn.Linear(48+2+len(FEATURES),48),nn.ReLU(),nn.Linear(48,1))

    def forward(self,x,*unused):
        hidden,_=self.encoder(x)
        return self.output(torch.cat((hidden,x[...,2:]),-1))
