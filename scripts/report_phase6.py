"""Summarize only completed fixed-grid experiments; never infer pending results."""
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from axis7.cloud_training import atomic_json


def summarize():
    sources={};lines=['# Phase 6 - résultats réellement exécutés','',
        'Les expériences locales sont CPU. Les trois répétitions changent à la fois les partitions et la graine.',
        'Les apprenants peuvent se retrouver dans plusieurs répétitions : les écarts-types sont descriptifs,',
        'pas une preuve de trois populations indépendantes. Les intervalles bootstrap rééchantillonnent',
        'les apprenants entiers, conditionnellement au modèle et au découpage. Aucun intervalle individuel.', '',
        '| Base | Graine | Modèle choisi sur validation | Test réseau | Contrôle choisi sur validation | Test contrôle |',
        '|---|---:|---|---:|---|---:|']
    for source in ('amme','yousician','singpad'):
        root=ROOT/'artifacts/models/phase6'/source; index=root/'index.json'
        if not index.exists():continue
        index=json.loads(index.read_text());runs=[]
        key='log_loss' if source=='singpad' else 'mae'
        for seed,entry in index['splits'].items():
            folder=root/entry['models'][entry['selected']].replace('\\','/')
            analysis=json.loads((folder/'analysis.json').read_text())
            meta=json.loads((folder/'metrics.json').read_text())
            control=analysis['validation_selected_control']
            run={'seed':int(seed),'model':entry['selected'],'metric':key,
                 'validation':meta['validation'],'test':meta['test'],
                 'control':control,'control_test':analysis['metrics'][control],
                 'control_validation':analysis['validation_controls'][control],
                 'bootstrap':analysis['bootstrap'],'slices':analysis['slices']}
            runs.append(run)
            lines.append(f"| {source} | {seed} | {entry['selected']} | {meta['test'][key]:.6f} | {control} | {analysis['metrics'][control][key]:.6f} |")
        if not runs:continue
        score=np.asarray([r['test'][key] for r in runs]);controls=np.asarray([r['control_test'][key] for r in runs])
        sources[source]={'metric':key,'completed_seeds':[r['seed'] for r in runs], 'runs':runs,
                         'mean':float(score.mean()),'sample_sd':float(score.std(ddof=1)) if len(score)>1 else None,
                         'best_observed':float(score.min()),'worst_observed':float(score.max()),
                         'mean_control':float(controls.mean()),
                         'seed42_calibration':next((r['test'].get('calibration_bins') for r in runs if r['seed']==42),None)}
    ablations=[]
    for path in sorted((ROOT/'artifacts/models/phase6/singpad/ablations').glob('*/metrics.json')):
        meta=json.loads(path.read_text());ablations.append({'name':path.parent.name,'validation':meta['validation'],
                                                           'test':meta['test'],'epochs':meta['epochs_completed']})
    output={'schema':'phase6-summary-v1','execution':'actual local CPU','sources':sources,
            'ablations':ablations,'historical_singpad_phase5':'invalid; see historical-invalidations.json',
            'scope':'source-specific predictive benchmark; no educational benefit or piano transfer established'}
    cloud=ROOT/'artifacts/phase6/cloud.json'
    if cloud.exists():output['cloud']=json.loads(cloud.read_text())
    atomic_json(ROOT/'artifacts/phase6/results-summary.json',output)
    lines+=['','## Moyennes des découpages exécutés','', '| Base | Moyenne | Écart-type | Contrôle moyen | Répétitions |','|---|---:|---:|---:|---:|']
    for source,r in sources.items():
        sd=f"{r['sample_sd']:.6f}" if r['sample_sd'] is not None else 'non disponible'
        lines.append(f"| {source} | {r['mean']:.6f} | {sd} | {r['mean_control']:.6f} | {len(r['runs'])} |")
    lines+=['','## Ablations exécutées','', '| Condition | Validation log-loss | Test log-loss |','|---|---:|---:|']
    for r in ablations:lines.append(f"| {r['name']} | {r['validation']['log_loss']:.6f} | {r['test']['log_loss']:.6f} |")
    lines+=['','Une architecture comparée à une autre n’est pas une ablation isolée. Les ablations retirent',
            'les cumuls, les résultats récents, les embeddings d’exercices, ou réduisent la fenêtre. Le mélange',
            'aléatoire des parcours n’est pas utilisé : il pourrait replacer du futur dans le passé.',
            'Un effet d’ablation reste associatif ; les graines supplémentaires ne sont pas des répétitions de chaque ablation.', '',
            'AMME reste recherche seulement. Sur Yousician, les références historiques peuvent dépasser le réseau :',
            'le gain contre la constante ne prouve pas une valeur ajoutée par rapport aux contrôles plus forts.',
            'Les résultats détaillés et les dénominateurs sont dans chaque analysis.json.', '',
            'Limites restantes : pas de bénéfice pédagogique démontré, pas de taxonomie piano validée,',
            'pas d’intervalle pour chaque prévision, pas de contrôle prospectif terrain.',
            'La cible Yousician reste le prochain jour actif. Les concepts SingPAD restent ceux de la source.']
    (ROOT/'docs/PHASE6_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'sources':{s:r['completed_seeds'] for s,r in sources.items()},'ablations_completed':len(ablations)}))


if __name__=='__main__':summarize()
