"""Remove learner lists from portable artifacts while preserving trained tensors.

Private raw data, prepared caches and resume checkpoints remain untouched.
Only previously created Phase 5 exports are migrated; no new training claims.
"""
from pathlib import Path
import sys
import json
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from axis7.cloud_training import public_split_provenance, atomic_json, digest

for location in ('artifacts/models/phase5', 'artifacts/models/musical-cloud'):
    for report in (ROOT/location).rglob('metrics.json'):
        meta = json.loads(report.read_text(encoding='utf-8'))
        if all(isinstance(v, dict) for v in meta['splits'].values()):
            continue
        payload_path = report.parent/'model.pt'
        payload = torch.load(payload_path, map_location='cpu', weights_only=True)
        public = public_split_provenance(meta['splits'])
        meta['splits'] = public; payload['config']['splits'] = public
        temp = payload_path.with_suffix('.tmp'); torch.save(payload, temp); temp.replace(payload_path)
        meta['model_sha256'] = digest(payload_path)
        atomic_json(report, meta)
        print(report.relative_to(ROOT))
