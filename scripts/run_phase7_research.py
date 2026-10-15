"""Run the preregistered exploratory comparisons; retain private resume separately."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from axis7 import cloud_training as c
from axis7.phase7_research import train_representation, learned_controls, stress_test


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
                reports[condition] = json.loads(completed.read_text(encoding='utf-8'))
                continue
            # New implementation fingerprint gets its own resumable directory.
            implementation = c.digest(ROOT/'axis7/phase7_research.py')[:12]
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
