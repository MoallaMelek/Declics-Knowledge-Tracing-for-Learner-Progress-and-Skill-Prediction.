"""Run the SYNTHETIC learner campaigns of configs/simulation-study.json (never touches runtime/learning.sqlite).

Usage:
  python scripts/run_simulation_campaigns.py --only A1            # one campaign
  python scripts/run_simulation_campaigns.py --worker 0           # the campaigns of worker 0, in order
Outputs: runtime/simulation/<study>/campaigns/<name>/ (synthetic DB, hidden/, campaign.json).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from axis7.sim_campaign import run_campaign  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default=str(ROOT / 'configs/simulation-study.json'))
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--worker', type=int)
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
    names = args.only or (cfg['workers'][args.worker] if args.worker is not None else list(cfg['campaigns']))
    base = Path(args.out or ROOT / 'runtime/simulation' / cfg['study'] / 'campaigns')
    for name in names:
        spec = cfg['campaigns'][name]
        target = base / name
        if (target / 'campaign.json').exists():
            print(json.dumps({'campaign': name, 'status': 'already complete'}), flush=True)
            continue
        print(json.dumps({'campaign': name, 'status': 'start', **spec}), flush=True)
        summary = run_campaign(target, variant=spec['variant'], n=spec['n'], seed=spec['seed'], weeks=cfg['weeks'],
                               oracle_samples=cfg['oracle_samples'], noise_scale=spec.get('noise_scale', 1.0),
                               log=lambda m: print(m, flush=True))
        print(json.dumps({'campaign': name, 'status': 'done', 'elapsed_s': summary['elapsed_seconds'], **summary['counters']}), flush=True)


if __name__ == '__main__':
    main()
