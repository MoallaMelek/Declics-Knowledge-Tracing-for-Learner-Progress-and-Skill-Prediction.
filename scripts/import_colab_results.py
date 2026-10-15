"""Verify portable Colab exports, archive all reports and activate accepted models."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from axis7.cloud_training import SOURCES, atomic_json
from axis7.musical_registry import install, validate


def ingest(directory):
    staging = ROOT/'tmp/phase5-colab-import'
    staging.mkdir(parents=True,exist_ok=True)
    reports = {}; active = {}
    for source in SOURCES:
        bundle = Path(directory)/f'{source}-benchmark-bundle.zip'
        with tempfile.TemporaryDirectory(dir=staging) as temporary, zipfile.ZipFile(bundle) as z:
            allowed = {'model.pt','metrics.json','metrics.csv','history.json'}
            if set(z.namelist()) != allowed or len(z.namelist()) != len(allowed):
                raise ValueError('Unexpected bundle entries')
            for item in z.infolist():
                if item.file_size > 100*1024*1024:
                    raise ValueError('Oversized bundle')
                with z.open(item) as src,(Path(temporary)/item.filename).open('wb') as dst:
                    shutil.copyfileobj(src,dst)
            meta,_ = validate(temporary,require_gate=False)
            if meta['source'] != source or meta['device'] != 'cuda':
                raise ValueError('Expected an actual CUDA report for this source')
            reference = json.loads((ROOT/'artifacts/models/phase5'/source/
                'enhanced_gru/metrics.json').read_text(encoding='utf-8'))
            if reference['sha256'] != meta['sha256']:
                raise ValueError('Cloud/local source archive checksum mismatch')
            target = ROOT/'artifacts/models/phase5-cloud'/source/meta['model']
            target.mkdir(parents=True,exist_ok=True)
            for name in allowed:
                shutil.copyfile(Path(temporary)/name,target/name)
            reports[source] = meta
            if meta['validation_gate']['accepted']:
                active[source] = install(target)
    atomic_json(ROOT/'artifacts/phase5/cloud-report.json', {
        'execution':'actual Google Colab CUDA', 'gpu':'Tesla T4', 'pytorch':'2.11.0+cu130',
        'code_revision':'63085813d84ae30c393f7d5a61be06cc49e30c21',
        'date':'2026-10-15', 'timezone':'Africa/Tunis',
        'transfer_verified':'Downloaded from Drive after flush_and_unmount; weights/config checked locally',
        'active':active, 'reports':reports})
    print(json.dumps({'active':active,'research_only':[s for s,m in reports.items()
                    if not m['validation_gate']['accepted']]},ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',required=True)
    ingest(parser.parse_args().directory)
