"""Execute the predefined grid, matched controls and cluster uncertainty."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from axis7 import cloud_training as cloud
from axis7.musical_registry import validate
from axis7.scientific_validation import train_priors, collect, analyze, metrics, CONTROLS


def run(source, archive, output, seeds, ablations=False):
    output = Path(output)
    spec = json.loads((ROOT/'configs/phase6-experiments.json').read_text())
    prepared = cloud.prepare(source, archive, output/'prepared.json.gz')
    binary = cloud.SOURCES[source]['binary']; key = 'log_loss' if binary else 'mae'
    index_path = output/'index.json'
    index = json.loads(index_path.read_text()) if index_path.exists() else {'source': source, 'splits': {}, 'ablations': []}
    models = spec['singpad_architectures'] if binary else spec['continuous_architectures']
    for seed in seeds:
        split = cloud.split_learners(prepared['learners'], seed)
        reports = {}; folders = {}
        for name in models:
            folder = output/f'seed-{seed}'/name
            reports[name] = cloud.train(source, archive, folder, model_name=name, seed=seed,
                                       epochs=spec['epochs'], batch_size=spec['batch_size'])
            folders[name] = folder
            cloud.atomic_json(index_path, {**index, 'last_completed': {'seed': seed, 'model': name}})
        selected = min(reports, key=lambda name: reports[name]['validation'][key])
        for name in models:
            meta, model = validate(folders[name], require_gate=False)
            mean, prior, count = train_priors(prepared['learners'], split['train'], meta['K'])
            val = collect(model, name, prepared['learners'], split['validation'], meta['K'], meta['items'],
                          meta['context'], mean, prior)
            control = min(CONTROLS, key=lambda c: metrics(val['y'], val[c], val['w'], binary)[key])
            test = collect(model, name, prepared['learners'], split['test'], meta['K'], meta['items'],
                           meta['context'], mean, prior)
            analysis = analyze(test, binary, count, control)
            analysis['validation_controls'] = {c: metrics(val['y'], val[c], val['w'], binary) for c in CONTROLS}
            cloud.atomic_json(folders[name]/'analysis.json', analysis)
        index['splits'][str(seed)] = {'selected': selected, 'criterion': 'validation_'+key,
                                     'models': {n: str(folders[n].relative_to(output)) for n in models}}
        cloud.atomic_json(index_path, index)
    if ablations and binary:
        seed = 42; split = cloud.split_learners(prepared['learners'], seed)
        for experiment in spec['ablations_seed_42']:
            name = experiment['model']; mode = experiment['feature_mode']; context = experiment['context']
            label = f'{name}-{mode}-c{context}'
            folder = output/'ablations'/label
            meta = cloud.train(source, archive, folder, model_name=name, seed=seed, epochs=spec['epochs'],
                               feature_mode=mode, context=context)
            _, model = validate(folder, require_gate=False)
            mean, prior, count = train_priors(prepared['learners'], split['train'], meta['K'])
            data = collect(model, name, prepared['learners'], split['test'], meta['K'], meta['items'],
                           context, mean, prior, feature_mode=mode)
            cloud.atomic_json(folder/'analysis.json', analyze(data, True, count, 'frequency'))
            if label not in index['ablations']: index['ablations'].append(label)
            cloud.atomic_json(index_path, index)
    print(json.dumps({'completed': source, 'seeds': seeds, 'index': str(index_path)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=cloud.SOURCES, required=True)
    parser.add_argument('--archive', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--seeds', nargs='+', type=int, default=[42,17,83])
    parser.add_argument('--ablations', action='store_true')
    args = parser.parse_args()
    run(args.source, args.archive, args.output, args.seeds, args.ablations)
