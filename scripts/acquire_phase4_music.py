"""Acquire pinned, licensed bounded piano material. No assessment targets are created."""
import argparse, hashlib, json, re, urllib.request
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RACH='a9519492b086a6c039a9d0994689ca0f279186bd'
PIANO='1f039ab9d6128626bff708faad6472d220b50eaa'
RBASE=f'https://raw.githubusercontent.com/Rach3Project/rach3_midi_dataset/{RACH}/'
PBASE=f'https://huggingface.co/datasets/PianoVAM/PianoVAM_v1/resolve/{PIANO}/'

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Declic-Axis7-noncommercial-research'})
    with urllib.request.urlopen(req,timeout=60) as response:return response.read()

def acquire(out):
    out.mkdir(parents=True,exist_ok=True)
    tree=fetch(f'https://api.github.com/repos/Rach3Project/rach3_midi_dataset/git/trees/{RACH}?recursive=1')
    inventory=json.loads(tree)
    if inventory.get('truncated'):raise ValueError('Incomplete Rach3 inventory')
    groups=defaultdict(list)
    for entry in inventory['tree']:
        match=re.fullmatch(r'rehearsals/(p[1-4])/\1(\d{6})(\d{3})(.+)\.mid',entry['path'])
        if match:groups[(match[1],match[4])].append(entry['path'])
    chosen=[]
    for learner in ('p1','p2','p3','p4'):
        candidates=[sorted(paths) for (p,_),paths in groups.items() if p==learner and len(paths)>=3]
        if not candidates:raise ValueError(f'No repeated recordings for {learner}')
        # Deterministic bounded coverage; dates differ for the selected three recordings.
        candidates.sort(key=lambda paths:(-len(paths),paths[0]))
        for paths in candidates:
            by_day={}
            for path in paths:by_day.setdefault(Path(path).name[2:8],path)
            if len(by_day)>=3:
                chosen.extend(list(by_day.values())[:3]);break
        else:raise ValueError(f'No distinct-day repeats for {learner}')
    files=[('Rach3/LICENSE',RBASE+'LICENSE'),('Rach3/README.md',RBASE+'README.md'),
           ('PianoVAM/README.md',PBASE+'README.md'),('PianoVAM/metadata.json',PBASE+'metadata.json')]
    files.extend(('Rach3/'+path,RBASE+path) for path in chosen)
    receipts=[]
    for relative,url in files:
        data=fetch(url);target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        receipts.append({'path':relative,'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    license_text=(out/'Rach3/LICENSE').read_text(encoding='utf8')
    card=(out/'PianoVAM/README.md').read_text(encoding='utf8')
    if 'Attribution-NonCommercial-ShareAlike' not in license_text or 'cc-by-nc-sa-4.0' not in card.lower():
        raise ValueError('Pinned rights evidence did not match expected grant')
    result={'version':'phase4-acquisition-1','rach3_commit':RACH,'pianovam_revision':PIANO,
        'rights':'CC-BY-NC-SA-4.0','purpose':'bounded noncommercial research; attribution and share-alike required',
        'rach3_inventory_midi_count':sum(x['path'].endswith('.mid') for x in inventory['tree']),
        'files':receipts,'correctness_targets_available':False,
        'selection':'Three earliest distinct-day recordings of the most frequent piece per pianist; deterministic descriptive sample, not representative.'}
    (out/'acquisition.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'data/music-phase4/raw')
    print(json.dumps(acquire(parser.parse_args().output),indent=2))
