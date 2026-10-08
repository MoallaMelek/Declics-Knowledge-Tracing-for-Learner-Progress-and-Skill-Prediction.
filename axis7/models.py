import numpy as np
import torch
from torch import nn
from scipy.optimize import minimize
from sklearn.linear_model import LogisticRegression
from .data import arrays

class DKT(nn.Module):
    """DKT-style GRU: a recurrent baseline, not original LSTM paper reproduction."""
    def __init__(self,K,hidden=48,context=256):
        super().__init__();self.K=K;self.context=context
        self.encoder=nn.GRU(2*K,hidden,batch_first=True);self.output=nn.Linear(hidden,K)
    def forward(self,x):
        h,_=self.encoder(x);return self.output(h)

class SAKT(nn.Module):
    """Skill queries attend only to past attempts via a shifted causal memory."""
    def __init__(self,K,hidden=48,context=256):
        super().__init__();self.K=K;self.context=context
        self.memory=nn.Linear(2*K,hidden);self.position=nn.Embedding(context,hidden)
        self.skill=nn.Embedding(K,hidden);self.attn=nn.MultiheadAttention(hidden,4,batch_first=True,dropout=.1)
        self.norm1=nn.LayerNorm(hidden);self.norm2=nn.LayerNorm(hidden)
        self.ff=nn.Sequential(nn.Linear(hidden,hidden*2),nn.ReLU(),nn.Dropout(.1),nn.Linear(hidden*2,hidden))
        self.output=nn.Linear(hidden,1)
    def forward(self,x):
        B,T,_=x.shape
        if T>self.context:raise ValueError("Sequence exceeds saved attention context")
        positions=self.position(torch.arange(T,device=x.device))
        memory=self.memory(x)+positions
        q=(positions[:,None,:]+self.skill.weight[None,:,:]).reshape(T*self.K,-1).unsqueeze(0).expand(B,-1,-1)
        # key j is shifted input (attempt j-1), so j<=t is safe, including BOS at j=0.
        mask=torch.arange(T,device=x.device)[None,:]>torch.arange(T,device=x.device).repeat_interleave(self.K)[:,None]
        a,_=self.attn(q,memory,memory,attn_mask=mask,need_weights=False)
        z=self.norm1(q+a);z=self.norm2(z+self.ff(z))
        return self.output(z).reshape(B,T,self.K)

def new_neural(name,K,hidden,context):return {'dkt':DKT,'sakt':SAKT}[name](K,hidden,context)

def pfa_features(rows,K):
    successes=np.zeros(K);failures=np.zeros(K);result=[]
    for r in rows:
        before={}
        for o in r['obs']:
            k=o['k']; f=np.zeros(3*K);f[k]=1;f[K+k]=np.log1p(successes[k]);f[2*K+k]=np.log1p(failures[k]);before[k]=f
            if o['y'] is not None:result.append((f,o['y']))
        for o in r['obs']:
            if o['y'] is not None:successes[o['k']]+=o['y'];failures[o['k']]+=1-o['y']
    return result

class Baseline:
    def __init__(self,name,K):self.name=name;self.K=K;self.priors=np.ones(K)*.5
    def fit(self,learners):
        success=np.ones(self.K);counts=np.ones(self.K)*2
        for rows in learners.values():
            for r in rows:
                for o in r['obs']:
                    if o['y'] is not None:success[o['k']]+=o['y'];counts[o['k']]+=1
        self.priors=success/counts
        if self.name=='pfa':
            samples=[v for rows in learners.values() for v in pfa_features(rows,self.K)]
            X=np.stack([s[0] for s in samples]);Y=np.array([s[1] for s in samples])
            self.reg=LogisticRegression(C=1.0,max_iter=1000,random_state=0).fit(X,Y)
        if self.name=='bkt':
            self.params=[]
            for k in range(self.K):
                histories=[]
                for rows in learners.values():
                    groups=[[o['y'] for o in r['obs'] if o['k']==k and o['y'] is not None] for r in rows]
                    histories.append([g for g in groups if g])
                def loss(v):
                    L,T,G,S=v;nll=0
                    for groups in histories:
                        m=L
                        for ys in groups:
                            p=np.clip(m*(1-S)+(1-m)*G,1e-7,1-1e-7)
                            nll-=sum(y*np.log(p)+(1-y)*np.log1p(-p) for y in ys)
                            m=self.update(m,ys,T,G,S)
                    return nll
                fits=[minimize(loss,v,bounds=[(.001,.999),(.001,.35),(.01,.49),(.01,.49)],method='L-BFGS-B')
                    for v in [(self.priors[k],.08,.2,.15),(.3,.03,.3,.2)]]
                self.params.append(min(fits,key=lambda v:v.fun).x.tolist())
        return self
    @staticmethod
    def update(m,ys,T,G,S):
        known=m;unknown=1-m
        for y in ys:known*=1-S if y else S;unknown*=G if y else 1-G
        posterior=known/max(known+unknown,1e-12)
        return posterior+(1-posterior)*T
    def predict(self,rows,append_query=False):
        K=self.K;successes=np.zeros(K);failures=np.zeros(K)
        mastery=np.array([p[0] for p in self.params]) if self.name=='bkt' else None
        predictions=[]
        for r in list(rows)+([{'obs':[]}] if append_query else []):
            if self.name=='prior':p=self.priors.copy()
            elif self.name=='pfa':
                X=np.zeros((K,3*K));idx=np.arange(K);X[idx,idx]=1;X[idx,K+idx]=np.log1p(successes);X[idx,2*K+idx]=np.log1p(failures)
                p=self.reg.predict_proba(X)[:,1]
            else:p=np.array([mastery[k]*(1-self.params[k][3])+(1-mastery[k])*self.params[k][2] for k in range(K)])
            predictions.append(p)
            if self.name=='bkt':
                for k in range(K):
                    ys=[o['y'] for o in r['obs'] if o['k']==k and o['y'] is not None]
                    if ys:mastery[k]=self.update(mastery[k],ys,*self.params[k][1:])
            for o in r['obs']:
                if o['y'] is not None:successes[o['k']]+=o['y'];failures[o['k']]+=1-o['y']
        return np.array(predictions)

def neural_predict(model,rows,K,query=False):
    rs=list(rows)+([{'obs':[]}] if query else [])
    if not rs:return np.empty((0,K))
    model.eval();parts=[];context=model.context
    # Complete evaluation, bounded history. Overlapping warm context prevents dropped tail events.
    with torch.no_grad():
        for end in range(1,len(rs)+1) if len(rs)>context else [len(rs)]:
            start=max(0,end-context)
            # Include one previous attempt at boundary in shifted x without using its target.
            x,_,_=arrays(rs[max(0,start-1):end],K)
            if start>0:x=x[1:]
            out=torch.sigmoid(model(torch.from_numpy(x)[None])).numpy()[0]
            parts.append(out[-1:] if len(rs)>context else out)
    return np.concatenate(parts)
