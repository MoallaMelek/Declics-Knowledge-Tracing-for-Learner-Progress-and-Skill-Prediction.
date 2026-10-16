"""Import checksummed source-benchmark models; never replace the piano twin."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile
from functools import lru_cache

import torch

from .cloud_training import SOURCES, VERSION, PREPROCESSING, atomic_json, digest, model_for
from .data import ROOT
from .serving_identity import freeze

REGISTRY_ROOT = Path(os.environ.get('DECLIC_MODEL_REGISTRY', ROOT / 'artifacts/models/musical-cloud'))


@lru_cache(maxsize=8)
def _verified_model(path, report_bytes, model_bytes, analysis_bytes):
    # Validate the SAME bytes used as the cache key. Never reopen mutable paths here.
    meta, model = validate(path, _assets=(report_bytes, model_bytes, analysis_bytes))
    meta['_serving_evidence_sha256'] = hashlib.sha256(analysis_bytes or b'').hexdigest()
    return freeze(meta), model


def cached_validate(folder):
    folder = Path(folder)
    return _verified_model(str(folder.resolve()), (folder/'metrics.json').read_bytes(),
                           (folder/'model.pt').read_bytes(),
                           (folder/'analysis.json').read_bytes() if (folder/'analysis.json').exists() else None)


def validate_comparison(analysis, validation, metric):
    control = analysis['validation_selected_control']
    controls = analysis['validation_controls']
    if control not in controls or control != min(controls, key=lambda name: controls[name][metric]):
        raise ValueError('Control must be selected exclusively on validation')
    if not validation[metric] < controls[control][metric]:
        raise ValueError('Neural model does not improve the stronger validation control')


def validate(folder, *, require_gate=True, _assets=None):
    folder = Path(folder)
    if _assets is None:
        _assets = ((folder/'metrics.json').read_bytes(), (folder/'model.pt').read_bytes(),
                   (folder/'analysis.json').read_bytes() if (folder/'analysis.json').exists() else None)
    report_bytes, model_bytes, analysis_bytes = _assets
    meta = json.loads(report_bytes)
    source = meta.get('source')
    if source not in SOURCES or meta.get('version') not in (VERSION, 'musical-cloud-v1'):
        raise ValueError('Unknown dataset/implementation')
    if source == 'singpad':
        if meta.get('version') != VERSION or meta.get('preprocessing') != PREPROCESSING['singpad']:
            raise ValueError('Invalid historical SingPAD chronology; retraining required')
        chronology = meta.get('audit', {}).get('chronology', {})
        if (chronology.get('chronological_inversions') != 0 or chronology.get('duplicate_time_groups') != 0
                or chronology.get('learners', 0) < 10):
            raise ValueError('Missing or failed SingPAD chronological audit')
    if meta.get('feature_mode', 'full') not in ('full', 'no_counts', 'no_recent', 'no_items'):
        raise ValueError('Unknown feature configuration')
    if meta.get('instrument') != SOURCES[source]['instrument'] or meta.get('target') != SOURCES[source]['target']:
        raise ValueError('Incompatible source domain/target')
    if hashlib.sha256(model_bytes).hexdigest() != meta.get('model_sha256'):
        raise ValueError('Model checksum mismatch')
    splits = meta.get('splits', {})
    if set(splits) != {'train', 'validation', 'test'} or not all(splits.values()):
        raise ValueError('Missing split provenance')
    if any(not isinstance(v, dict) or set(v) != {'count', 'sha256'} or v['count'] < 1
           or len(v['sha256']) != 64 for v in splits.values()):
        raise ValueError('Expected public split counts/digests; learner IDs must stay private')
    if len({v['sha256'] for v in splits.values()}) != 3:
        raise ValueError('Split digest collision or learner leakage')
    payload = torch.load(io.BytesIO(model_bytes), map_location='cpu', weights_only=True)
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
    if require_gate and source == 'singpad':
        if analysis_bytes is None:
            raise ValueError('Corrected SingPAD promotion requires matched historical controls')
        validate_comparison(json.loads(analysis_bytes), val, metric)
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
    for name in ('model.pt', 'metrics.json', 'metrics.csv', 'history.json', 'analysis.json'):
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
    allowed = {'model.pt', 'metrics.json', 'metrics.csv', 'history.json', 'analysis.json'}
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
            meta, _ = cached_validate(folder)
            if active is not None and active.get(meta['source']) != folder.name:
                continue
            comparison = json.loads((folder/'analysis.json').read_text(encoding='utf-8')) if (folder/'analysis.json').exists() else None
            result.append({'id': folder.name, 'source': meta['source'], 'instrument': meta['instrument'],
                           'target': meta['target'], 'model': meta['model'], 'test': meta['test'],
                           'validation': meta['validation'], 'scope': 'source_benchmark_only',
                           'citation': meta['citation'], 'limitations': meta['limitations'],
                           'version': meta['version'], 'preprocessing': meta.get('preprocessing'),
                           'comparison': {'metrics': comparison['metrics'],
                                          'selected_control': comparison['validation_selected_control'],
                                          'bootstrap': comparison['bootstrap']} if comparison else None})
        except (ValueError, KeyError, OSError, RuntimeError, TypeError):
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
