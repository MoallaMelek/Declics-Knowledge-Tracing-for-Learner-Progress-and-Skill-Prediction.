"""Explicit DL experiment eligibility, separate from validation competitiveness.

Read published comparator numbers only. This module never fits or serves a classical model,
and never selects by test scores. Existing registry integrity/chronology gates stay required.
"""
import json
from .data import ROOT

POLICY = 'experimental-dl-v1'


def describe(meta, root=ROOT):
    metric = 'log_loss' if meta['source']=='singpad' else 'mae'
    candidates = {}
    folder = root/'artifacts/phase7'/meta['source']/f"seed-{meta['seed']}"
    try:
        report=json.loads((folder/'strong-controls.json').read_text(encoding='utf-8'))
        if report['splits']==meta['splits'] and report.get('dataset_sha256')==meta['sha256']:
            for name, model in report['models'].items():
                values=model['validation_candidates'];selected=model['selected_parameter']
                if selected==min(values,key=lambda k:values[k][metric]): candidates[name]=values[selected][metric]
    except (OSError,ValueError,KeyError,TypeError): pass
    try:
        report=json.loads((folder/'learned-control.json').read_text(encoding='utf-8'))
        if report['splits']==meta['splits']:
            candidates[report['kind']]=min(v[metric] for v in report['validation_candidates'].values())
    except (OSError,ValueError,KeyError,TypeError): pass
    best=min(candidates,key=candidates.get) if candidates else None
    improves=meta['validation'][metric]<candidates[best] if best else None
    return {'policy':POLICY,'tier':'experimental_dl_source_benchmark',
            'product_engine':'deep_learning_only','selection_criterion':'validation_only',
            'metric':metric,'neural_validation':meta['validation'][metric],
            'best_available_learned_control':best,'control_validation':candidates.get(best),
            'improves_available_learned_controls':improves,
            'statement': ('Prédicteur neuronal expérimental ; avantage sur le contrôle appris de validation non démontré.'
                          if improves is not True else 'Avantage sur les contrôles appris disponibles de validation ; étude exploratoire, sans validation terrain.'),
            'test_scores_used_for_eligibility':False,
            'original_registry_gates':'Retained: checksum/configuration/chronology and validation vs train mean; corrected SingPAD additionally requires historical-control gate.'}
