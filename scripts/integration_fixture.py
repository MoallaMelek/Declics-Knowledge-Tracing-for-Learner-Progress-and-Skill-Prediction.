"""Synthetic replay integration fixture; REAL trained tensors copied, never retrained.

Temporary config/split identities are rewritten to describe synthetic inputs. Original
benchmark metrics are retained as historical evidence, NOT fixture accuracy. No production
artifact is modified. This tool must never be used to publish scientific measurements.
"""
import argparse
from datetime import datetime, timedelta
import gzip
import hashlib
import json
from pathlib import Path
import random
import shutil
import torch
from axis7.cloud_training import split_learners, public_split_provenance, PREPROCESSING
from axis7.data import ROOT
from axis7.serving_identity import canonical_digest


def configure_fixture(model_folder, destination, data):
    target = Path(destination); target.mkdir(parents=True, exist_ok=True)
    original = Path(model_folder)
    for name in ('metrics.json', 'analysis.json'):
        if (original/name).exists(): shutil.copyfile(original/name, target/name)
    payload = torch.load(original/'model.pt', map_location='cpu', weights_only=True)
    meta = json.loads((original/'metrics.json').read_text(encoding='utf-8'))
    data.update(version=meta['version'], preprocessing=meta.get('preprocessing', PREPROCESSING[data['source']]), fixture='synthetic-integration-only')
    data['sha256'] = canonical_digest(data)
    split = public_split_provenance(split_learners(data['learners'], meta['seed']))
    cfg = {**payload['config'], 'sha256': data['sha256'], 'splits': split}
    torch.save({'config': cfg, 'state_dict': payload['state_dict']}, target/'model.pt')
    meta.update(cfg)
    meta.update(model_sha256=hashlib.sha256((target/'model.pt').read_bytes()).hexdigest(),
                fixture='synthetic-integration-only', original_checkpoint_sha256=hashlib.sha256((original/'model.pt').read_bytes()).hexdigest(),
                fixture_scope='Synthetic histories + copied trained tensors; benchmark metrics are NOT fixture validation.')
    (target/'metrics.json').write_text(json.dumps(meta), encoding='utf-8')
    return meta


def build(destination):
    destination = Path(destination); registry = destination/'registry'; prepared = destination/'prepared'
    registry.mkdir(parents=True, exist_ok=True); prepared.mkdir(parents=True, exist_ok=True)
    active = json.loads((ROOT/'artifacts/models/musical-cloud/active.json').read_text()); selected = {}
    for source in ('singpad', 'yousician'):
        original = ROOT/'artifacts/models/musical-cloud'/active[source]
        meta = json.loads((original/'metrics.json').read_text()); items = sorted(k for k in meta['items'] if '|' not in k)
        rng = random.Random(1842); learners = {}
        for i in range(24):
            rows = []
            for t in range(12):
                ks = sorted({(3*t+i)%meta['K'], (3*t+i+1)%meta['K'], (3*t+i+2)%meta['K']}) if source == 'singpad' else [0]
                obs = [[k, rng.randint(0, 1) if source == 'singpad' else round(rng.random(), 6), 1.] for k in ks for _ in range(4 if source=='singpad' else 1)]
                rows.append({'time': (datetime(2023,1,1)+timedelta(days=t)).isoformat() if source=='singpad' else t,
                             'exercise': items[t%len(items)] if source=='singpad' else '', 'difficulty':0., 'obs':obs})
            learners[f'SYNTHETIC-{source}-{i:02}'] = rows
        data = {'source':source,'learners':learners}; folder = registry/(source+'-fixture')
        configure_fixture(original, folder, data)
        with gzip.open(prepared/f'{source}-prepared.json.gz','wt',encoding='utf-8') as f:json.dump(data,f)
        selected[source] = folder.name
    (registry/'active.json').write_text(json.dumps(selected),encoding='utf-8')
    return registry, prepared


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('destination',type=Path)
    a=p.parse_args();registry,prepared=build(a.destination)
    print(json.dumps({'mode':'synthetic_fixture','registry':str(registry.resolve()),'prepared':str(prepared.resolve())}))
