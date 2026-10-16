"""Publish actual local training reports and select architectures on validation."""
import json
from pathlib import Path
import platform
import sys
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from axis7.cloud_training import SOURCES, atomic_json

rows = []; selections = {}
for source in SOURCES:
    candidates = []
    for path in sorted((ROOT/'artifacts/models/phase5'/source).glob('*/metrics.json')):
        meta = json.loads(path.read_text(encoding='utf-8'))
        candidates.append(meta)
        rows.append({'source': source, 'model': meta['model'], 'epochs': meta['epochs_completed'],
                     'validation': meta['validation'], 'test': meta['test'],
                     'reference_test': meta['constant_train_mean_reference']['test'],
                     'gate': meta['validation_gate'], 'sha256': meta['sha256'], 'audit': meta['audit']})
    if candidates:
        key = 'log_loss' if SOURCES[source]['binary'] else 'mae'
        selected = min(candidates,key=lambda m:m['validation'][key])
        selections[source] = {'model': selected['model'], 'criterion': 'validation_'+key,
                              'benchmark_accepted': selected['validation_gate']['accepted']}
atomic_json(ROOT/'artifacts/phase5/report.json', {'execution': 'actual local CPU',
    'python': platform.python_version(), 'pytorch': torch.__version__, 'rows': rows, 'selected': selections,
    'scope': 'source benchmark only; not validated for personal DEClic piano practice'})
lines = ['# Phase 5 — résultats réellement exécutés', '',
         'Entraînements exécutés localement sur CPU, sur les archives fournies. Aucun résultat GPU/Colab',
         "n'est déduit de ces résultats locaux. Les architectures sont choisies sur la validation uniquement.", '',
         '| Base | Architecture | Époques | Mesure test | Référence constante test | Contrôle |',
         '|---|---|---:|---:|---:|---|']
for r in rows:
    key = 'log_loss' if SOURCES[r['source']]['binary'] else 'mae'
    lines.append(f"| {r['source']} | {r['model']} | {r['epochs']} | {key}: {r['test'][key]:.4f} | {r['reference_test'][key]:.4f} | {'accepté pour le benchmark' if r['gate']['accepted'] else 'recherche seulement'} |")
lines += ['', 'Sélection sur validation : '+', '.join(f"{s}: {v['model']}" for s,v in selections.items())+'.', '',
          'Pour SingPAD, la ROC-AUC, la PR-AUC, le Brier et les classes de calibration sont dans',
          '`artifacts/phase5/report.json`. AMME manque de cibles de validation/test pour le seuil',
          'de 30 et reste en recherche. Les moyennes constantes sont calculées sur l’entraînement.', '',
          'Un seul découpage nouveaux apprenants et une seule graine : pas d’intervalle de confiance,',
          'pas de preuve de bénéfice pédagogique ni de transfert vers le piano personnel.', '',
          'Le rapport JSON contient les checksums des archives et les audits de nettoyage.']
(ROOT/'docs/PHASE5_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
