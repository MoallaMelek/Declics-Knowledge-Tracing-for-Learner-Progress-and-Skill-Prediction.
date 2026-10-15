"""Import checksummed source-benchmark models; never replace the piano twin."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

import torch

from .cloud_training import SOURCES, VERSION, atomic_json, digest, model_for
from .data import ROOT

REGISTRY_ROOT = ROOT / 'artifacts/models/musical-cloud'


def validate(folder, *, require_gate=True):
    folder = Path(folder)
    meta = json.loads((folder/'metrics.json').read_text(encoding='utf-8'))
    source = meta.get('source')
    if source not in SOURCES or meta.get('version') != VERSION:
        raise ValueError('Unknown dataset/implementation')
    if meta.get('instrument') != SOURCES[source]['instrument'] or meta.get('target') != SOURCES[source]['target']:
        raise ValueError('Incompatible source domain/target')
    if digest(folder/'model.pt') != meta.get('model_sha256'):
        raise ValueError('Model checksum mismatch')
    splits = meta.get('splits', {})
    if set(splits) != {'train', 'validation', 'test'} or not all(splits.values()):
        raise ValueError('Missing split provenance')
    if any(not isinstance(v, dict) or set(v) != {'count', 'sha256'} or v['count'] < 1
           or len(v['sha256']) != 64 for v in splits.values()):
        raise ValueError('Expected public split counts/digests; learner IDs must stay private')
    if len({v['sha256'] for v in splits.values()}) != 3:
        raise ValueError('Split digest collision or learner leakage')
    payload = torch.load(folder/'model.pt', map_location='cpu', weights_only=True)
    cfg = payload['config']
    if any(meta.get(k) != v for k, v in cfg.items()):
        raise ValueError('Report/checkpoint config mismatch')
    if not (1 <= cfg['K'] <= 1024 and 1 <= cfg['hidden'] <= 256 and 2 <= cfg['context'] <= 256
            and len(cfg['items']) < 10000):
        raise ValueError('Unsupported model dimensions')
    model = model_for(cfg['model'], cfg['K'], cfg['items'], cfg['hidden'], cfg['context'])
    if any(not isinstance(value, torch.Tensor) or not torch.isfinite(value).all()
           for value in payload['state_dict'].values()):
        raise ValueError('Non-finite or invalid model tensors')
    model.load_state_dict(payload['state_dict'], strict=True); model.eval()
    metric = 'log_loss' if SOURCES[source]['binary'] else 'mae'
    val = meta['validation']; test = meta['test']
    baseline = meta['constant_train_mean_reference']['validation']
    if require_gate and not (meta['validation_gate']['accepted'] and val[metric] < baseline[metric]
            and val['observed_targets'] >= 30 and test['observed_targets'] >= 30):
        raise ValueError('Benchmark validation gate failed; research metrics retained only')
    for report in (val, test):
        import math
        if not math.isfinite(report[metric]):
            raise ValueError('Non-finite benchmark metric')
    return meta, model


def install(folder, destination=REGISTRY_ROOT, *, activate=True):
    meta, _ = validate(folder)
    identifier = f"{meta['source']}-{meta['model']}-s{meta['seed']}-{meta['model_sha256'][:12]}"
    target = Path(destination) / identifier
    target.mkdir(parents=True, exist_ok=True)
    for name in ('model.pt', 'metrics.json', 'metrics.csv', 'history.json'):
        src = Path(folder)/name
        if src.exists():
            shutil.copyfile(src, target/name)
    if activate:
        manifest_path = Path(destination) / 'active.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
        manifest[meta['source']] = identifier
        atomic_json(manifest_path, manifest)
    return identifier


def import_bundle(bundle, destination=REGISTRY_ROOT):
    allowed = {'model.pt', 'metrics.json', 'metrics.csv', 'history.json'}
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=Path(destination).parent) as tmp, zipfile.ZipFile(bundle) as z:
        if len(z.namelist()) != len(set(z.namelist())) or set(z.namelist()) - allowed:
            raise ValueError('Unexpected or duplicate bundle entries')
        if not {'model.pt', 'metrics.json'} <= set(z.namelist()):
            raise ValueError('Missing model/report')
        for info in z.infolist():
            if info.file_size > 100 * 1024 * 1024:
                raise ValueError('Oversized model bundle')
            with z.open(info) as src, (Path(tmp)/info.filename).open('wb') as dst:
                shutil.copyfileobj(src, dst)
        return install(tmp, destination)


def entries(root=REGISTRY_ROOT):
    result = []
    manifest_path = Path(root) / 'active.json'
    try:
        active = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else None
        if active is not None and not isinstance(active, dict):
            return []
    except (ValueError, OSError):
        return []
    for folder in sorted(Path(root).glob('*')):
        if not folder.is_dir():
            continue
        try:
            meta, _ = validate(folder)
            if active is not None and active.get(meta['source']) != folder.name:
                continue
            result.append({'id': folder.name, 'source': meta['source'], 'instrument': meta['instrument'],
                           'target': meta['target'], 'model': meta['model'], 'test': meta['test'],
                           'validation': meta['validation'], 'scope': 'source_benchmark_only',
                           'citation': meta['citation'], 'limitations': meta['limitations']})
        except (ValueError, KeyError, OSError, RuntimeError):
            continue  # Corrupt/incompatible models are not silently served.
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    command = sub.add_parser('import'); command.add_argument('--bundle', required=True)
    command = sub.add_parser('install'); command.add_argument('--folder', required=True)
    sub.add_parser('list')
    args = parser.parse_args()
    if args.command == 'import':
        print(import_bundle(args.bundle))
    elif args.command == 'install':
        print(install(args.folder))
    else:
        print(json.dumps(entries(), ensure_ascii=False, indent=2))
