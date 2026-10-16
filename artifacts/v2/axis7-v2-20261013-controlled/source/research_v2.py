"""Controlled repeated-split KT study. Historical v1 artifacts are never overwritten.

Raw predictions are primary. Selection sees only selection learners; temperature
fits only calibration learners. Each immutable experiment owns its checkpoints,
predictions, code snapshots, split manifests and uncertainty reports. Only index.json
is a replaceable convenience pointer. No musical empirical validity is implied.
"""
import argparse
import hashlib
import importlib.metadata
import json
import logging
import platform
import random
import shutil
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import torch
from torch import nn
from .data import ROOT, load_forget, generate_music, split_students, write_json
from .eligibility import eligible, compact_history, expand_forecasts
from .models import Baseline
from .models_v2 import (ItemEncoder, StatisticalControl, CoherentGroupedBKT, NEURAL_NAMES, BASELINE_NAMES,
                        make_neural, encode_sequence, neural_logits, research_neural_predict, save_checkpoint,
                        ResearchPredictor)
from .metrics import summary, evaluate, temperature_fit, calibrate

log = logging.getLogger('axis7.research_v2')


def seed_all(seed, threads=2):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True); torch.set_num_threads(threads)


def owned_windows(encoded, context):
    """Every target has exactly one owner. Earlier half-window warms causal memory."""
    T = len(encoded[0]); owner_start = 0; stride = max(1, context//2)
    while owner_start < T:
        end = min(T, context if owner_start == 0 else owner_start+stride)
        start = max(0, end-context)
        values = [v[start:end].copy() for v in encoded]
        values[-1][:max(0, owner_start-start)] = 0
        yield values
        owner_start = end


def batch_windows(windows, indices):
    batch = [windows[i] for i in indices]; T = max(len(v[0]) for v in batch)
    result = []
    for j in range(6):
        array = np.zeros((len(batch), T)+batch[0][j].shape[1:], dtype=batch[0][j].dtype)
        for b, seq in enumerate(batch): array[b, :len(seq[j])] = seq[j]
        result.append(torch.from_numpy(array))
    return result


def sequence_windows(learners, K, items, name, context):
    windows = []
    for rows in learners.values():
        compact, _ = compact_history(rows)
        if not compact: continue
        encoded = encode_sequence(compact, K, items, no_outcome=name.endswith('no_outcome'), no_item=name.endswith('no_item'))
        windows.extend(owned_windows(encoded, context))
    return windows


def weighted_loss(model, name, values):
    logits = neural_logits(model, name, values)
    y, weights = values[-2:]
    losses = nn.functional.binary_cross_entropy_with_logits(logits, y, reduction='none')
    return (losses*weights).sum(), weights.sum()


def train_neural(name, K, items, train, validation, config, seed):
    seed_all(seed, config['torch_threads'])
    model = make_neural(name, K, items, config['hidden'], config['context'])
    optimizer = torch.optim.AdamW(model.parameters(), lr=config['learning_rate'], weight_decay=config['weight_decay'])
    windows = sequence_windows(train, K, items, name, config['context'])
    val_windows = sequence_windows(validation, K, items, name, config['context'])
    rng = np.random.default_rng(seed); best = float('inf'); best_state = None; stale = 0; curve = []
    for epoch in range(config['epochs']):
        model.train(); total = 0.; count = 0.; indices = rng.permutation(len(windows))
        for start in range(0, len(indices), config['batch_size']):
            values = batch_windows(windows, indices[start:start+config['batch_size']])
            optimizer.zero_grad(); numerator, denominator = weighted_loss(model, name, values)
            loss = numerator/denominator; loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 5); optimizer.step()
            total += float(numerator.detach()); count += float(denominator)
        model.eval(); val_total = 0.; val_count = 0.
        with torch.no_grad():
            for start in range(0, len(val_windows), config['batch_size']):
                values = batch_windows(val_windows, range(start, min(start+config['batch_size'], len(val_windows))))
                a, b = weighted_loss(model, name, values); val_total += float(a); val_count += float(b)
        score = val_total/val_count
        curve.append({'epoch': epoch+1, 'train_loss': total/count, 'validation_log_loss': score})
        if score < best-1e-5:
            best = score; best_state = {k:v.clone() for k,v in model.state_dict().items()}; stale = 0
        else: stale += 1
        if stale >= config['patience']: break
    model.load_state_dict(best_state); model.eval()
    return model, curve


def model_probabilities(model, name, rows, K, items, exercise_id=None):
    if name in NEURAL_NAMES:
        return research_neural_predict(model, name, rows, items, exercise_id)
    if name in ('item_pfa', 'exposure'):
        return model.probabilities(rows, exercise_id)
    compact, positions = compact_history(rows)
    return expand_forecasts(model.predict(compact, append_query=True), positions, True)


def prediction_records(model, name, learners, K, items):
    records = []; timings = []
    for user, rows in sorted(learners.items()):
        begin = time.perf_counter(); p = model_probabilities(model, name, rows, K, items); timings.append((time.perf_counter()-begin)*1000)
        counts = np.zeros(K, int)
        for t, row in enumerate(rows):
            for n, o in enumerate(row['obs']):
                if eligible(o):
                    records.append({'student': user, 'attempt': row['id'], 'observation': n, 'position': t,
                                    'skill': o['k'], 'y': o['y'], 'p': float(p[t, o['k']]),
                                    'p_raw': float(p[t, o['k']]), 'skill_history_count': int(counts[o['k']]),
                                    'item': item_key_for_record(row), 'original_score': o.get('score')})
            for o in row['obs']:
                if eligible(o): counts[o['k']] += 1
    return records, {'median_ms': statistics.median(timings), 'max_ms': max(timings),
                     'unit': 'warm CPU per complete learner history; not HTTP or concurrency', 'learners': len(timings)}


def item_key_for_record(row):
    from .models_v2 import item_key
    return item_key(row)


def record_summary(records):
    return summary(np.array([r['y'] for r in records]), np.array([r['p'] for r in records]))


def richer_metrics(records, replicates, reference=None):
    ref = None
    if reference is not None:
        identity = lambda rs: [(r['student'],r['attempt'],r['observation'],r['y']) for r in rs]
        if identity(reference) != identity(records): raise ValueError('Paired comparison rows are not aligned')
        ref = np.array([r['p'] for r in reference])
    m = evaluate(records, replicates, ref)
    if 'log_loss_difference_vs_prior' in m['bootstrap_95']:
        m['bootstrap_95']['log_loss_difference_vs_validation_best_baseline'] = m['bootstrap_95'].pop('log_loss_difference_vs_prior')
    m['first_skill_exposure'] = record_summary([r for r in records if r['skill_history_count']==0])
    m['rare_skill_history_1_to_4'] = record_summary([r for r in records if 1<=r['skill_history_count']<=4])
    return m


def select_winner(runs, baselines_only=False):
    allowed = [r for r in runs if not baselines_only or r['name'] in BASELINE_NAMES]
    return min(allowed, key=lambda r:r['validation']['log_loss'])


def create_experiment(config, experiment_id=None):
    eid = experiment_id or ('study-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()[:8])
    if not eid or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in eid):
        raise ValueError('Experiment ID must be a safe filename')
    output = ROOT/'artifacts/v2'/eid; output.mkdir(parents=True, exist_ok=False)
    write_json(output/'config.json', config)
    return eid, output


def provenance_manifest(output):
    snapshot = output/'source'; snapshot.mkdir()
    sources = {}
    for name in ['models_v2.py','research_v2.py','models.py','data.py','metrics.py','eligibility.py']:
        source = ROOT/'axis7'/name; data = source.read_bytes(); (snapshot/name).write_bytes(data)
        sources['axis7/'+name] = hashlib.sha256(data).hexdigest()
    try:
        git = subprocess.run(['git','rev-parse','HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        dirty = subprocess.run(['git','status','--porcelain'], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError): git = ''; dirty = 'unavailable'
    return {'source_sha256': sources, 'source_snapshot': 'source/', 'git_head': git or None,
            'uncommitted_worktree': bool(dirty), 'python': platform.python_version(), 'platform': platform.platform(),
            'dependencies': {p:importlib.metadata.version(p) for p in ['torch','numpy','scipy','scikit-learn']},
            'data_sha256': hashlib.sha256((ROOT/'data/raw/forget_se.csv').read_bytes()).hexdigest(),
            'started_at_utc': datetime.now(timezone.utc).isoformat()}


def run_split(domain, learners, metadata, split_seed, config, output):
    splits = split_students(learners, split_seed); parts = {part:{u:learners[u] for u in users} for part,users in splits.items()}
    directory = output/domain/f'split-{split_seed}'; directory.mkdir(parents=True)
    write_json(directory/'splits.json', splits); write_json(directory/'metadata.json', metadata)
    items = ItemEncoder().fit(parts['train']); write_json(directory/'items.json', items.state)
    K = len(metadata['skills']); runs = []; baseline_records = {}; raw_records = {}; reference = None; ref_id = None
    for name in config['models']:
        for seed in config['neural_seeds'] if name in NEURAL_NAMES else [0]:
            begin = time.perf_counter(); rid = f'{name}-{seed}'
            log.info('Training %s split=%s %s', domain, split_seed, rid)
            fit_start = time.perf_counter()
            if name in NEURAL_NAMES:
                model, curve = train_neural(name, K, items, parts['train'], parts['validation'], config, seed)
            elif name in ('item_pfa','exposure'):
                model = StatisticalControl(name, K, items).fit(parts['train']); curve = []
            elif name == 'bkt': model = CoherentGroupedBKT(K).fit(parts['train']); curve = []
            else: model = Baseline(name, K).fit(parts['train']); curve = []
            fit_seconds = time.perf_counter()-fit_start
            val, _ = prediction_records(model, name, parts['validation'], K, items)
            cal, _ = prediction_records(model, name, parts['calibration'], K, items)
            test, timing = prediction_records(model, name, parts['test'], K, items)
            temperature = temperature_fit(np.array([r['y'] for r in cal]), np.array([r['p'] for r in cal]))
            if name in NEURAL_NAMES and reference is None:
                ref = select_winner(runs, baselines_only=True); ref_id = ref['id']; reference = baseline_records[ref_id]
            if name in BASELINE_NAMES: baseline_records[rid] = test
            raw_records[rid] = test
            raw = richer_metrics(test, config['bootstrap_replicates'], reference)
            calibrated_records = [dict(r, p=float(calibrate(r['p_raw'],temperature))) for r in test]
            checkpoint = {'name':name,'K':K,'hidden':config['hidden'],'context':config['context'],'split_seed':split_seed,
                          'seed':seed,'domain':domain,'metadata':metadata,'output':'raw_primary',
                          'applicability':'known exercise bundle conditions forecast; omitted exercise uses train-only UNK'}
            save_checkpoint(directory, rid, model, checkpoint, items, temperature)
            for r, cr in zip(test, calibrated_records): r['p_calibrated'] = cr['p']
            write_json(directory/f'{rid}-predictions.json', test)
            run = {'id':rid, 'name':name, 'seed':seed, 'split_seed':split_seed,'domain':domain,
                   'validation':record_summary(val),'test':raw,'raw':raw,'calibrated':record_summary(calibrated_records),
                   'temperature':temperature,'calibration_before':record_summary(cal),'calibration_after':record_summary([dict(r,p=float(calibrate(r['p'],temperature))) for r in cal]),
                   'curve':curve,'fit_seconds':round(fit_seconds,3),'total_seconds':round(time.perf_counter()-begin,3),'inference':timing,
                   'parameter_count':sum(p.numel() for p in model.parameters()) if name in NEURAL_NAMES else None,
                   'checkpoint_directory':str(directory.relative_to(ROOT)).replace('\\','/'),
                   'baseline_reference_id':ref_id,'source':'public software engineering' if domain=='forget-se' else 'synthetic music, not empirical'}
            runs.append(run); log.info('RESULT %s/%s/%s AUC %.4f raw LL %.4f cal LL %.4f %.1fs', domain, split_seed, rid,raw['auc'],raw['log_loss'],run['calibrated']['log_loss'],run['total_seconds'])
            write_json(directory/'progress.json', {'completed_runs':len(runs),'planned_runs':sum(2 if n in NEURAL_NAMES else 1 for n in config['models']), 'last_run':rid})
    # Baseline paired intervals are calculated after baseline selection, without refitting or test selection.
    ref = select_winner(runs, True); ref_id = ref['id']; reference = raw_records[ref_id]
    for r in runs:
        if r['name'] in BASELINE_NAMES:
            r['test'] = richer_metrics(raw_records[r['id']], config['bootstrap_replicates'], reference); r['raw'] = r['test']
        r['baseline_reference_id'] = ref_id
    selected = select_winner(runs); neural = select_winner([r for r in runs if r['name'] in NEURAL_NAMES])
    result = {'domain':domain,'split_seed':split_seed,'metadata':metadata,'split_counts':{k:len(v) for k,v in splits.items()},
              'selected':{'overall':selected['id'],'neural':neural['id'],'baseline':ref_id},'runs':runs}
    write_json(directory/'results.json', result)
    return result


def aggregate_groups(results):
    groups = []
    for domain in sorted({r['domain'] for r in results}):
        for name in results[0]['runs'] and sorted({run['name'] for res in results if res['domain']==domain for run in res['runs']}):
            selected = [run for res in results if res['domain']==domain for run in res['runs'] if run['name']==name]
            splits = sorted({r['split_seed'] for r in selected}); metrics = {}
            for metric in ['auc','pr_auc','log_loss','brier','ece_10']:
                by_split = [statistics.mean(r['raw'][metric] for r in selected if r['split_seed']==s and r['raw'][metric] is not None) for s in splits]
                metrics[metric] = {'mean':statistics.mean(by_split),'std_across_split_means':statistics.stdev(by_split) if len(by_split)>1 else None,
                                   'split_means':by_split}
            groups.append({'domain':domain,'name':name,'runs':len(selected),'splits':len(splits),'metrics':metrics,
                           'calibrated_log_loss_mean':statistics.mean(r['calibrated']['log_loss'] for r in selected),
                           'selection':'descriptive aggregation; no model is selected by test means'})
    return groups


def execute(config, experiment_id=None):
    eid, output = create_experiment(config, experiment_id); manifest = provenance_manifest(output)
    write_json(output/'provenance.json',manifest); started=time.perf_counter(); results=[]; serving=[]; defaults={}
    for domain in config['domains']:
        learners, metadata = load_forget() if domain=='forget-se' else generate_music(seed=config['synthetic_seed'])
        write_json(output/f'{domain}-dataset.json',{'metadata':metadata,'learners':len(learners),'groups':sum(map(len,learners.values())),
                    'observations':sum(len(r['obs']) for rows in learners.values() for r in rows),'generated_seed':config['synthetic_seed'] if domain=='music-mock' else None})
        for split in config['split_seeds']:
            result = run_split(domain,learners,metadata,split,config,output); results.append(result)
            if split==config['serving_split']:
                defaults[domain]=result['selected']
                for run in result['runs']:
                    sid=f'{domain}:{split}:{run["id"]}'
                    serving.append({'id':sid,'domain':domain,'directory':run['checkpoint_directory'],'run_id':run['id'],
                                    'name':run['name'],'split_seed':split,'seed':run['seed'],'validation_log_loss':run['validation']['log_loss'],
                                    'model_profile':{'schema_version':'1.0','skills':metadata['skills'],'rubric':'full-credit-v1' if domain=='forget-se' else 'provisional-mock-v1',
                                                     'provenance':metadata['provenance'],'forecast':'raw; UNK exercise when no item supplied; not psychological mastery'}})
    summary_object={'experiment_id':eid,'study_version':config['study_version'],'config':config,'primary':'raw',
                    'groups':aggregate_groups(results),'rawruns':[r for result in results for r in result['runs']],
                    'splits':[{'domain':r['domain'],'split_seed':r['split_seed'],'selected':r['selected'],'split_counts':r['split_counts']} for r in results],
                    'serving_defaults':defaults,'serving':serving,'provenance':manifest,'elapsed_seconds':round(time.perf_counter()-started,2),
                    'limitations':['FORGET-SE is software engineering, not musical transfer.','Music-mock is synthetic, not learner validation.',
                                   'Repeated splits overlap learners: split SD is descriptive, not three independent population replications.',
                                   'Bootstrap conditions on a fitted checkpoint and test learner set.','Item forecasts condition atomic bundles, not individual note difficulty.',
                                   'No real elapsed-time features, unmeasured learning gains, or invented prerequisites.']}
    write_json(output/'summary.json',summary_object)
    lines=['# Actual repeated-split experiment results','',f'Experiment `{eid}`. Raw forecasts primary; separate temperature calibration secondary.',
           '', '| Domain | Model | Runs | Mean AUC | Mean raw log loss | Split SD log loss | Mean calibrated log loss |','|---|---|---:|---:|---:|---:|---:|']
    for g in summary_object['groups']:
        lines.append(f"| {g['domain']} | {g['name']} | {g['runs']} | {g['metrics']['auc']['mean']:.4f} | {g['metrics']['log_loss']['mean']:.4f} | {g['metrics']['log_loss']['std_across_split_means']:.4f} | {g['calibrated_log_loss_mean']:.4f} |")
    lines+=['','Every selected winner comes from validation loss, not this descriptive table. See per-split results for paired learner intervals against the validation-selected strongest statistical control. No winning claim is guaranteed.','']+summary_object['limitations']
    (output/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    index={'experiment_id':eid,'latest':eid,'summary':str((output/'summary.json').relative_to(ROOT)).replace('\\','/'),
           'serving':serving,'serving_defaults':defaults,'primary':'raw','completed_at_utc':datetime.now(timezone.utc).isoformat()}
    temporary=ROOT/'artifacts/v2/index.tmp.json';write_json(temporary,index);temporary.replace(ROOT/'artifacts/v2/index.json')
    log.info('COMPLETED %s with %s actual runs',eid,len(summary_object['rawruns']))
    return summary_object


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    ap=argparse.ArgumentParser();ap.add_argument('--config',default=str(ROOT/'configs/research-v2.json'));ap.add_argument('--experiment-id');args=ap.parse_args()
    config=json.loads(Path(args.config).read_text(encoding='utf-8'));execute(config,args.experiment_id)
