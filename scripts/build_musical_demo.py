"""Rebuild private real held-out cases; never commit histories or learner IDs."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from axis7.cloud_training import prepare, split_learners, public_split_provenance, atomic_json
from axis7.musical_registry import REGISTRY_ROOT, validate


def build(source, archive):
    active = json.loads((REGISTRY_ROOT/'active.json').read_text())
    if source not in active: raise ValueError('No active validated source model')
    meta,_ = validate(REGISTRY_ROOT/active[source])
    data = prepare(source, archive, ROOT/f'runtime/musical-demo/{source}-prepared.json.gz')
    if data['sha256'] != meta['sha256']: raise ValueError('Demo data/model checksum mismatch')
    splits = split_learners(data['learners'], meta['seed'])
    if public_split_provenance(splits) != meta['splits']: raise ValueError('Demo/model learner split mismatch')
    selected = None
    # Fixed selection rule, no choice based on forecast accuracy or interesting errors.
    for learner in splits['test']:
        rows = data['learners'][learner]
        for index in range(3,min(len(rows),50)):
            if source != 'singpad' or rows[index]['exercise'] in meta['items']:
                selected=(rows,index);break
        if selected: break
    if selected is None: raise ValueError('No supported genuine held-out demo prefix')
    rows,index=selected; target=rows[index]
    concepts=sorted({o[0] for o in target['obs']})[:6]
    history=[{'time':r['time'],'exercise':r['exercise'], 'observations':
              [{'concept':k,'score':v,'weight':w} for k,v,w in r['obs']]} for r in rows[:index]]
    observed={str(k):sum(v*w for c,v,w in target['obs'] if c==k)/sum(w for c,v,w in target['obs'] if c==k) for k in concepts}
    case={'provenance':{'kind':'real_held_out_history','source':source,'archive_sha256':data['sha256'],
                        'selection':'first test learner with at least three previous groups and supported query exercise',
                        'anonymous_label':'Parcours réel de test 01','learner_ids_exposed':False,
                        'target_outcomes_used_as_input':False},
          'query':{'source':source,'model_id':active[source],'instrument':meta['instrument'],
                   'query_time':target['time'],'exercise':target['exercise'],'concepts':concepts,'history':history},
          'plot_history':[{'group':i+1,'score':sum(v*w for k,v,w in r['obs'])/sum(w for k,v,w in r['obs'])}
                          for i,r in enumerate(rows[:index])],
          'observed_target':observed}
    atomic_json(ROOT/f'runtime/musical-demo/{source}.json',case)
    print(json.dumps({'source':source,'private_demo_ready':True,'groups':index}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',choices=['singpad','yousician'],required=True)
    parser.add_argument('--archive',required=True)
    args=parser.parse_args();build(args.source,args.archive)
