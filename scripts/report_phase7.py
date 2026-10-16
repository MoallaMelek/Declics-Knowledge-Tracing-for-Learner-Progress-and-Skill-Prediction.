"""Consolidate actual runs; assert split and target identity before comparison."""
import json
from pathlib import Path
import shutil
import sys
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from axis7 import cloud_training as c
from axis7.phase7_research import RepresentationModel
from scripts.run_phase7_research import validate_completed


def load(path):return json.loads(path.read_text(encoding='utf-8'))


def report():
    comparisons=[]; variants=[]; calibrations=[]; completed=0; weights=[]
    for source in ('amme','yousician','singpad'):
        key='log_loss' if source=='singpad' else 'mae'
        for seed in (42,17,83):
            directory=ROOT/f'artifacts/phase7/{source}/seed-{seed}'
            reports={p.stem:load(p) for p in directory.glob('*.json') if 'config' in load(p)}
            selected=min(reports,key=lambda n:reports[n]['validation'][key])
            historical=load(ROOT/f'artifacts/models/phase6/{source}/seed-{seed}/enhanced_gru/analysis.json')
            previous=load(ROOT/f'artifacts/models/phase6/{source}/seed-{seed}/enhanced_gru/metrics.json')
            for name,d in reports.items():
                assert d['config']['splits']==previous['splits']
                assert d['config']['dataset_sha256']==previous['sha256']
                assert d['test']['concept_group_targets']==historical['metrics']['neural']['concept_group_targets']
                assert d['test']['label_weight']==historical['metrics']['neural']['label_weight']
                variants.append({'source':source,'seed':seed,'condition':name,
                    'validation':d['validation'][key],'test':d['test'][key],
                    'parameters':d['trainable_parameters'],'epochs':d['epochs_completed']})
                completed+=1
                if source=='singpad':
                    ca=d['calibration'];calibrations.append({'seed':seed,'condition':name,'temperature':ca['temperature'],
                        'raw_log_loss':ca['test_raw']['log_loss'],'scaled_log_loss':ca['test_scaled']['log_loss'],
                        'raw_ece':ca['test_raw']['ece'],'scaled_ece':ca['test_scaled']['ece'],
                        'raw_brier':ca['test_raw']['brier'],'scaled_brier':ca['test_scaled']['brier']})
                private=ROOT/f'tmp/phase7-private/{source}/{seed}'
                candidates=[private/name/'model.pt',*sorted(private.glob(f'{name}-*/model.pt'))]
                weight=next(p for p in candidates if p.exists() and c.digest(p)==d['model_sha256'])
                destination=ROOT/f'artifacts/models/phase7/{source}/seed-{seed}/{name}'
                destination.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(weight,destination/'model.pt')
                shutil.copyfile(directory/f'{name}.json',destination/'metrics.json')
                # Vocabularies are exercise IDs fitted on train learners; no learner IDs.
                prepared=load_private(ROOT/f'tmp/phase7-private/{source}/prepared.json.gz')
                split=c.split_learners(prepared['learners'],seed)
                validate_completed(d,prepared,seed,name)
                verifier=RepresentationModel(name,d['config']['K'],len(c.fit_items(prepared['learners'],split['train']))+1)
                state=torch.load(destination/'model.pt',map_location='cpu',weights_only=True)
                verifier.load_state_dict(state)
                assert all(torch.isfinite(v).all() for v in state.values())
                c.atomic_json(destination/'architecture.json',{'condition':name,'K':d['config']['K'],
                    'hidden':48,'context':64,'items':c.fit_items(prepared['learners'],split['train']),
                    'registry':'research only; never automatically activated'})
                weights.append({'path':(destination/'model.pt').relative_to(ROOT).as_posix(),'sha256':d['model_sha256']})
            simple=load(directory/'learned-control.json')
            assert simple['splits']==previous['splits']
            candidates={simple['kind']:{'validation':simple['validation_candidates'][simple['selected_regularization']][key],
                                       'test':simple['test'][key]}}
            strong=load(directory/'strong-controls.json')
            assert strong['splits']==previous['splits'] and strong['dataset_sha256']==previous['sha256']
            for name,d in strong['models'].items():
                candidates[name]={'validation':d['validation_candidates'][d['selected_parameter']][key],'test':d['test'][key]}
            for name,d in historical['validation_controls'].items():
                candidates['historical_'+name]={'validation':d[key],'test':historical['metrics'][name][key]}
            control=min(candidates,key=lambda n:candidates[n]['validation'])
            learned_names=[n for n in candidates if not n.startswith('historical_')]
            learned=min(learned_names,key=lambda n:candidates[n]['validation'])
            comparisons.append({'source':source,'seed':seed,'metric':key,'selected':selected,
                'neural_validation':reports[selected]['validation'][key],'neural_test':reports[selected]['test'][key],
                'selected_control':control,'control_validation':candidates[control]['validation'],'control_test':candidates[control]['test'],
                'selected_learned_control':learned,'learned_control_test':candidates[learned]['test'],
                'control_candidates':candidates})
    assert completed==33
    context=[]
    for seed in (42,17,83):
        d=load(ROOT/f'artifacts/phase7/yousician-context/seed-{seed}.json')
        context.append({'seed':seed,'validation':d['validation']['mae'],'test':d['test']['mae'],
            'control_validation':d['same_feature_control']['validation']['mae'],
            'control_test':d['same_feature_control']['test']['mae']})
        folder=ROOT/f'artifacts/models/phase7/yousician-context/seed-{seed}'
        assert c.digest(folder/'model.pt')==d['model_sha256']
        from axis7.yousician_context import ContextGRU
        state=torch.load(folder/'model.pt',map_location='cpu',weights_only=True)
        ContextGRU().load_state_dict(state)
        assert all(torch.isfinite(v).all() for v in state.values())
        weights.append({'path':(folder/'model.pt').relative_to(ROOT).as_posix(),'sha256':d['model_sha256']})
    summary={'phase':7,'scope':'Expériences CPU exploratoires sur les partitions par apprenant de Phase 6 ; aucune nouvelle cohorte confirmatoire indépendante.',
        'completed_core_neural_runs':completed,'completed_neural_runs':completed+len(context),'interrupted_dense_attention_runs_excluded':1,
        'comparisons':comparisons,'variants':variants,'calibration':calibrations,
        'means':{s:{'neural':float(np.mean([r['neural_test'] for r in comparisons if r['source']==s])),
                      'neural_sd':float(np.std([r['neural_test'] for r in comparisons if r['source']==s],ddof=1)),
                      'control':float(np.mean([r['control_test'] for r in comparisons if r['source']==s]))}
                 for s in ('amme','yousician','singpad')},
        'yousician_context_extension':context,'weights':weights,'promotion':'none; Phase 6 active models preserved',
        'datasets':{s:{'learners':len(load_private(ROOT/f'tmp/phase7-private/{s}/prepared.json.gz')['learners']),
            'atomic_groups':sum(map(len,load_private(ROOT/f'tmp/phase7-private/{s}/prepared.json.gz')['learners'].values())),
            'preprocessing':load_private(ROOT/f'tmp/phase7-private/{s}/prepared.json.gz')['preprocessing'],
            'audit':load_private(ROOT/f'tmp/phase7-private/{s}/prepared.json.gz')['audit']}
            for s in ('amme','yousician','singpad')},
        'stress':{s:load(ROOT/f'artifacts/phase7/{s}/seed-42/stress.json') for s in ('amme','yousician','singpad')},
        'reliability_example':load(ROOT/'artifacts/phase7/singpad/seed-42/gru.json')['calibration'],
        'work_status':{'experiments':'36 entraînements CPU terminés ; contrôles appris, calibration et données manquantes évalués',
            'skill_states':'États descriptifs livrés ; aucune maîtrise cognitive validée',
            'prospective':'Infrastructure livrée ; contrat de mesure, modèle de terrain et étude réelle en attente',
            'taxonomy':'Circuit de revue livré ; aucune approbation experte ni correspondance activée',
            'piano':'Abstention hors domaine préservée'},
        'limitations':['Les trois découpages ne sont pas trois populations indépendantes.',
            'Huit époques et un protocole CPU exploratoire : ne pas substituer ces scores au benchmark GPU Phase 6.',
            'Aucune supériorité pédagogique, maîtrise cognitive ou généralisation au piano démontrée.',
            'Calibration ajustée sur validation ; aucune garantie de gain sur le test.',
            'Prévisions terrain suspendues à la validation du contrat de mesure ; aucun résultat prospectif inventé.',
            'AMME : petit échantillon et score mélodique continu ; recherche seulement.']}
    c.atomic_json(ROOT/'artifacts/phase7/summary.json',summary)
    lines=['# Phase 7 — résultats réellement exécutés','',summary['scope'],'',
        '| Base | Graine | Réseau choisi sur validation | Test réseau | Contrôle choisi sur validation | Test contrôle |',
        '|---|---:|---|---:|---|---:|']
    lines += [f"| {r['source']} | {r['seed']} | {r['selected']} | {r['neural_test']:.6f} | {r['selected_control']} | {r['control_test']:.6f} |" for r in comparisons]
    lines += ['','## Toutes les variantes','', '| Base | Graine | Condition | Validation | Test | Paramètres | Époques |','|---|---:|---|---:|---:|---:|---:|']
    lines += [f"| {r['source']} | {r['seed']} | {r['condition']} | {r['validation']:.6f} | {r['test']:.6f} | {r['parameters']} | {r['epochs']} |" for r in variants]
    lines += ['','## Calibration SingPAD','', '| Graine | Condition | T validation | Log-loss brute | Log-loss recalibrée | ECE brute | ECE recalibrée |','|---:|---|---:|---:|---:|---:|---:|']
    lines += [f"| {r['seed']} | {r['condition']} | {r['temperature']:.4f} | {r['raw_log_loss']:.6f} | {r['scaled_log_loss']:.6f} | {r['raw_ece']:.6f} | {r['scaled_ece']:.6f} |" for r in calibrations]
    lines += ['','## Extension Yousician : métadonnées passées','',
        '| Graine | Validation GRU enrichi | Test GRU enrichi | Validation arbres mêmes variables | Test arbres mêmes variables |',
        '|---:|---:|---:|---:|---:|']
    lines += [f"| {r['seed']} | {r['validation']:.6f} | {r['test']:.6f} | {r['control_validation']:.6f} | {r['control_test']:.6f} |" for r in context]
    lines += ['','Trois réseaux supplémentaires : 36 entraînements terminés au total. Cette extension est exploratoire et séparée du programme initial.',
        'Moyenne MAE enrichie 0,091059 ; arbres avec les mêmes variables 0,090822. Pas de gain moyen convaincant ni de promotion.',
        '','## Limites']+['','\n'.join(summary['limitations'])]
    (ROOT/'docs/PHASE7_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'runs':completed,'means':summary['means'],'comparisons':comparisons},ensure_ascii=False),flush=True)


_cache={}
def load_private(path):
    import gzip
    if str(path) not in _cache:
        with gzip.open(path,'rt',encoding='utf-8') as f:_cache[str(path)]=json.load(f)
    return _cache[str(path)]


if __name__=='__main__':report()
