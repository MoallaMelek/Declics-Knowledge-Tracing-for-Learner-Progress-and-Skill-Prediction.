from pathlib import Path
from datetime import datetime, timedelta, timezone
import csv, hashlib, json, urllib.request
from collections import defaultdict
import numpy as np
from .schema import MUSIC_SKILLS, MUSIC_LABELS

ROOT=Path(__file__).resolve().parents[1]
FORGET_URL="https://ndownloader.figshare.com/files/54819392"
FORGET_MD5="f7d297747eda7d5cd0a704a1b710df5d"

def acquire():
    p=ROOT/'data/raw/forget_se.csv'; p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        with urllib.request.urlopen(FORGET_URL,timeout=60) as response:
            p.write_bytes(response.read())
    if hashlib.md5(p.read_bytes()).hexdigest()!=FORGET_MD5: raise ValueError("FORGET-SE v1 checksum mismatch")
    return p

def load_forget(p=None):
    p=Path(p) if p else acquire(); groups=defaultdict(list)
    with p.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            score=float(r['correct'])
            if not np.isfinite(score) or not 0<=score<=1+1e-8: raise ValueError("Invalid original score")
            groups[(r['user_id'],int(r['log_id']))].append({"k":int(r['sequence_id'])-1,
                "y":int(score>=1-1e-8),"score":score,"question":r['qid'],"errors":[]})
    learners=defaultdict(list)
    for (u,order),obs in groups.items():
        if any(not 0<=o['k']<10 for o in obs): raise ValueError("Unexpected FORGET-SE concept")
        learners[u].append({"student":u,"id":f"forget:{u}:{order}","session":None,
            "order":order,"timestamp":None,"exercise":','.join(o['question'] for o in obs),
            "instrument":"software-engineering","provenance":"public","rubric":"full-credit-v1","obs":obs})
    learners={u:sorted(rows,key=lambda r:r['order']) for u,rows in learners.items()}
    return learners,{"domain":"forget-se","name":"FORGET-SE · génie logiciel","skills":[f"se_{i+1}" for i in range(10)],
        "labels":[f"Concept SE {i+1}" for i in range(10)],"provenance":"public",
        "target":"score complet ≥ 1 − 10⁻⁸","order_note":"log_id trié ; ex æquo regroupés ; unités temporelles inconnues"}

def generate_music(seed=2026,students=280,sessions=12):
    """Controlled stochastic process, NOT empirical musical learners or teacher truth."""
    rng=np.random.default_rng(seed); learners={}
    base=datetime(2026,1,1,tzinfo=timezone.utc)
    for i in range(students):
        u=f"mock-{i:03}"; ability=rng.normal(-.25,.85,len(MUSIC_SKILLS)); rows=[]
        preference=rng.dirichlet(np.ones(len(MUSIC_SKILLS))*2)
        for s in range(sessions):
            ability-=rng.uniform(.015,.06,len(ability))
            for j in range(4):
                ks=rng.choice(len(ability),size=2 if rng.random()<.3 else 1,replace=False,p=preference)
                obs=[]
                for k in ks:
                    p=1/(1+np.exp(-ability[k])); y=int(rng.random()<p)
                    obs.append({"k":int(k),"y":y,"score":float(y),"errors":[] if y else ["mock_outcome_failure"],"confidence":1.0})
                time=base+timedelta(days=3*s,minutes=5*j)
                rows.append({"student":u,"id":f"{u}:{s}:{j}","session":f"{u}:session:{s}","order":time.timestamp(),
                    "timestamp":time.isoformat(),"exercise":f"mock-exercise-{ks[0]}","instrument":"piano-provisional",
                    "provenance":"synthetic","rubric":"provisional-mock-v1","obs":obs})
                for k in ks: ability[k]+=rng.uniform(.08,.2)
        learners[u]=rows
    return learners,{"domain":"music-mock","name":"Atelier musical · simulation","skills":MUSIC_SKILLS,
        "labels":MUSIC_LABELS,"provenance":"synthetic","target":"issue binaire simulée",
        "order_note":"Sessions synthétiques ; taxonomie provisoire, sans graphe de prérequis validé"}

def split_students(learners,seed=2026):
    ids=np.array(sorted(learners)); np.random.default_rng(seed).shuffle(ids)
    a,b,c=int(.7*len(ids)),int(.775*len(ids)),int(.85*len(ids))
    return {"train":ids[:a].tolist(),"validation":ids[a:b].tolist(),"calibration":ids[b:c].tolist(),"test":ids[c:].tolist()}

def arrays(rows,K):
    """Input at t contains observations at t-1 only. Targets can have duplicates per KC."""
    T=len(rows); x=np.zeros((T,2*K),np.float32); y=np.zeros((T,K),np.float32); w=np.zeros((T,K),np.float32)
    outcomes=np.zeros((T,2*K),np.float32)
    for t,r in enumerate(rows):
        for o in r['obs']:
            if o['y'] is None: continue
            k,v=o['k'],o['y']; outcomes[t,k+v*K]+=1; y[t,k]+=v; w[t,k]+=1
        outcomes[t]/=max(1,sum(w[t]))
    y/=np.maximum(w,1)
    if T>1:x[1:]=outcomes[:-1]
    return x,y,w

def write_json(path,obj):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--acquire',action='store_true');args=ap.parse_args()
    if args.acquire: print(acquire())
