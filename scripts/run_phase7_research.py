"""Run the preregistered exploratory comparisons; retain private resume separately."""
import argparse
import json
from pathlib import Path
import sys
import torch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from axis7 import cloud_training as c
from axis7.phase7_research import train_representation, learned_controls, stress_test, RepresentationModel, LOADED_SOURCE_SHA256


def validate_completed(report, prepared, seed, condition):
    allowed=json.loads((ROOT/'configs/phase7-compatible-implementations.json').read_text(encoding='utf-8'))['allowed_source_sha256']
    config=report['config']
    expected={'protocol':'phase7-exploratory-v1','seed':seed,'condition':condition,
              'dataset_sha256':prepared['sha256'],'splits':c.public_split_provenance(c.split_learners(prepared['learners'],seed)),
              'epochs':8,'hidden':48,'context':64,'core_sha256':c.SOURCE_HASHES,
              'torch':torch.__version__,'numpy':np.__version__,'device':'cpu'}
    if report['source']!=prepared['source'] or any(config.get(k)!=v for k,v in expected.items()) or config['source_sha256'] not in allowed:
        raise ValueError('Cached report provenance incompatible; use a separate experiment/output directory')


def restore_model(report,prepared,seed,condition,private):
    config=report['config']; split=c.split_learners(prepared['learners'],seed)
    items=c.fit_items(prepared['learners'],split['train'])
    candidates=[private/f'{seed}/{condition}/model.pt', *sorted((private/str(seed)).glob(f'{condition}-*/model.pt'))]
    weights=next((p for p in candidates if p.exists() and c.digest(p)==report['model_sha256']),None)
    if weights is None: raise ValueError('Completed report has no matching intact model weights')
    model=RepresentationModel(condition,config['K'],len(items)+1)
    model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True))
    return model,split,config['K'],items


def run(source, archive, seeds):
    private = ROOT/'tmp/phase7-private'/source
    public = ROOT/'artifacts/phase7'/source
    prepared = c.prepare(source, archive, private/'prepared.json.gz')
    conditions = ('gru', 'unordered', 'recent3', 'attention', 'no_concept_embedding', 'past_gaps') if source == 'singpad' else ('gru', 'unordered', 'past_gaps') if source == 'yousician' else ('gru', 'unordered')
    for seed in seeds:
        reports = {}
        for condition in conditions:
            completed = public/f'seed-{seed}/{condition}.json'
            if completed.exists():
                report=json.loads(completed.read_text(encoding='utf-8'))
                validate_completed(report,prepared,seed,condition)
                if seed==42 and condition=='gru' and not (public/f'seed-{seed}/stress.json').exists():
                    model,split,K,items=restore_model(report,prepared,seed,condition,private)
                    c.atomic_json(public/f'seed-{seed}/stress.json',stress_test(model,prepared,split,K,items))
                reports[condition] = report
                continue
            # New implementation fingerprint gets its own resumable directory.
            implementation = LOADED_SOURCE_SHA256[:12]
            report, model, split, K, items = train_representation(prepared, seed, condition, private/f'{seed}/{condition}-{implementation}')
            reports[condition] = report
            c.atomic_json(public/f'seed-{seed}/{condition}.json', report)
            if seed == 42 and condition == 'gru':
                c.atomic_json(public/f'seed-{seed}/stress.json', stress_test(model, prepared, split, K, items))
        c.atomic_json(public/f'seed-{seed}/learned-control.json', learned_controls(prepared, seed))
        key = 'log_loss' if source == 'singpad' else 'mae'
        selected = min(reports, key=lambda name: reports[name]['validation'][key])
        c.atomic_json(public/f'seed-{seed}/selection.json', {'selected': selected, 'criterion': 'validation_'+key,
            'results': {name: {'validation': r['validation'][key], 'test': r['test'][key]} for name, r in reports.items()},
            'promotion': 'none; experimental weights remain private, active Phase 6 models unchanged'})
    print(json.dumps({'source': source, 'seeds_completed': seeds}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=c.SOURCES, required=True)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--seeds', type=int, nargs='+', default=[42,17,83])
    args = parser.parse_args()
    run(args.source, args.archive, args.seeds)
