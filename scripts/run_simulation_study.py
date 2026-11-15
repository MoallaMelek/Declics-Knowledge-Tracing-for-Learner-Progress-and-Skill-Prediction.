"""SYNTHETIC simulation study: inspect campaigns, train DÉCLIC GRUs, compare Elo / GRU / naive.

Every stage reads the campaign databases written by scripts/run_simulation_campaigns.py and writes
artifacts/simulation/<study>/. Models read only what DÉCLIC stored; the hidden folders are read
only to score against the truth.

Usage (each stage can be rerun alone; finished trainings are reused):
  python scripts/run_simulation_study.py inspect
  python scripts/run_simulation_study.py main          # A1 split 70/15/15, 3 GRU seeds, cross-fitting
  python scripts/run_simulation_study.py sensitivity   # A1: longer training (40 epochs), reported beside main
  python scripts/run_simulation_study.py replicate     # A2, A3
  python scripts/run_simulation_study.py shift         # B1 and N1 (other simulator, noisier answers)
  python scripts/run_simulation_study.py size          # L1: cohorts 50 / 200 / 1000
  python scripts/run_simulation_study.py families      # L1: one family absent from training
  python scripts/run_simulation_study.py ui            # interface data
"""
import argparse
from collections import defaultdict, Counter
import gzip
import json
import random
import sqlite3
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from axis7 import cloud_training as ct  # noqa: E402
from axis7 import sim_models as sm  # noqa: E402
from axis7 import sim_learners as sl  # noqa: E402

CFG = json.loads((ROOT / 'configs/simulation-study.json').read_text(encoding='utf-8'))
RUNS = ROOT / 'runtime/simulation' / CFG['study'] / 'campaigns'
OUT = ROOT / 'artifacts/simulation' / CFG['study']
G = CFG['gru']; B = CFG['bootstrap']


def log(msg):
    print(msg, flush=True)


def write(path, value):
    path = OUT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1, allow_nan=False), encoding='utf-8')


def campaign(name):
    folder = RUNS / name
    summary = json.loads((folder / 'campaign.json').read_text(encoding='utf-8'))
    data = sm.load_synthetic(folder / summary['database'])
    items, learners = sm.hidden_truth(folder)
    return folder, summary, data, items, learners


def split(ids, seed=G['split_seed']):
    return ct.split_learners({i: None for i in ids}, seed)


def gru(name, data, splits, seed):
    """Train once; later runs reuse the saved weights (same config, same split digest)."""
    folder = OUT / 'models' / name
    if (folder / 'model.pt').exists():
        model, cfg = sm.load_gru(folder)
        return model, cfg
    model, cfg = sm.train_gru(data, splits, folder, seed=seed, hidden=G['hidden'], context=G['context'], batch_size=G['batch_size'],
                              epochs=G['epochs'], patience=G['patience'], lr=G['lr'], weight_decay=G['weight_decay'], log=log, label=name)
    return model, cfg


def rows_for(data, ids, model, cfg, items, learners):
    return sm.question_table(data, ids, model, cfg, items, learners)


def evaluate(rows, title, extra=None):
    result = {'title': title, **sm.compare(rows, replicates=B['replicates'], seed=B['seed']), 'slices': sm.slices(rows),
              'trend': sm.trend_recovery(rows)}
    if extra:
        result.update(extra)
    return result


# ------------------------------------------------------------------ stage: inspect
def inspect():
    out = {}
    for name in CFG['campaigns']:
        if not (RUNS / name / 'campaign.json').exists():
            log(json.dumps({'inspect': name, 'status': 'missing'}))
            continue
        folder, summary, data, items, learners = campaign(name)
        days = [json.loads(l) for l in gzip.open(folder / 'hidden/days.jsonl.gz', 'rt', encoding='utf-8')]
        events = [json.loads(l) for l in gzip.open(folder / 'hidden/events.jsonl.gz', 'rt', encoding='utf-8')]
        sim_of = {lid: v['sim_id'] for lid, v in learners.items()}
        fam_of = {v['sim_id']: v['family'] for v in learners.values()}
        # weekly hidden ability (mean over the 9 skills), per learner
        weekly = defaultdict(lambda: defaultdict(list))
        for d in days:
            weekly[d['sim_id']][d['day'] // 7].append(np.mean(list(d['ability'].values())))
        curves = {s: [float(np.mean(w[k])) for k in sorted(w)] for s, w in weekly.items()}
        gains = {s: c[-1] - c[0] for s, c in curves.items() if len(c) >= 2}
        rounded = [tuple(round(v, 3) for v in c) for c in curves.values()]
        fam_curves = defaultdict(list)
        for s, c in curves.items():
            fam_curves[fam_of[s]].append(c)
        family_summary = {}
        for f, cs in fam_curves.items():
            L = min(len(c) for c in cs)
            arr = np.array([c[:L] for c in cs])
            g = [gains[s] for s in curves if fam_of[s] == f and s in gains]
            family_summary[f] = {'label': sl.VARIANTS[summary['variant']]['families'][f]['label'], 'learners': len(cs),
                                 'weekly_ability_mean': arr.mean(0).round(4).tolist(), 'weekly_ability_sd': arr.std(0).round(4).tolist(),
                                 'gain_mean': float(np.mean(g)) if g else None, 'gain_sd': float(np.std(g)) if g else None}
        # skill-level learning curves by family (hidden ability at day 0 and at the last day)
        first_last = defaultdict(lambda: defaultdict(list))
        last_day = {}
        for d in days:
            last_day[d['sim_id']] = d
        first_day = {}
        for d in days:
            first_day.setdefault(d['sim_id'], d)
        for s, d in last_day.items():
            for k in sl.SKILLS:
                first_last[fam_of[s]][k].append(d['ability'][k] - first_day[s]['ability'][k])
        skill_gain = {f: {k: float(np.mean(v)) for k, v in sk.items()} for f, sk in first_last.items()}
        # per-week activity and outcomes from what DÉCLIC stored
        active_week = defaultdict(set); answers_week = Counter(); correct_week = Counter()
        for lid, hist in data.items():
            for h in hist:
                day = (np.datetime64(h['answered_at'][:19]) - np.datetime64('2026-09-07T00:00:00')).astype('timedelta64[s]').astype(int) / 86400
                w = int(day // 7)
                active_week[w].add(lid); answers_week[w] += 1; correct_week[w] += h['y']
        by_ex = defaultdict(lambda: [0, 0, []])
        for hist in data.values():
            for h in hist:
                e = by_ex[h['exercise']]; e[0] += 1; e[1] += h['y']; e[2].append(h['level'])
        per_learner_answers = [len(v) for v in data.values()]
        out[name] = {
            'synthetic': True, 'variant': summary['variant'], 'seed': summary['seed'], 'n': summary['n'], 'weeks': summary['weeks'],
            'noise_scale': summary.get('noise_scale', 1.0), 'elapsed_seconds': summary['elapsed_seconds'], 'counters': summary['counters'],
            'learners_with_answers': len(data), 'questions': sum(per_learner_answers),
            'answers_per_learner': {'min': int(min(per_learner_answers)), 'median': float(np.median(per_learner_answers)), 'max': int(max(per_learner_answers))},
            'correct_rate': float(np.mean([h['y'] for v in data.values() for h in v])),
            'active_end': summary['counters']['active_end'], 'dropouts': summary['counters']['dropouts'], 'returns': summary['counters']['returns'],
            'breaks': sum(e['event'] == 'break' for e in events),
            'weekly': [{'week': w + 1, 'active_learners': len(active_week[w]), 'answers': answers_week[w],
                        'correct_rate': correct_week[w] / answers_week[w] if answers_week[w] else None} for w in sorted(active_week)],
            'exercises': {e: {'questions': v[0], 'correct_rate': v[1] / v[0], 'mean_level': float(np.mean(v[2])), 'max_level': int(max(v[2]))}
                          for e, v in sorted(by_ex.items())},
            'families': family_summary, 'skill_gain_by_family': skill_gain,
            'diversity': {'learners': len(curves), 'distinct_weekly_curves': len(set(rounded)),
                          'gain_sd_all': float(np.std(list(gains.values()))), 'gain_min': float(min(gains.values())), 'gain_max': float(max(gains.values())),
                          'share_identical_curves': 1 - len(set(rounded)) / len(rounded)},
            'mastered_levels': {'mean': float(np.mean([l['mastered_levels'] for l in summary['learners']])),
                                'max': int(max(l['mastered_levels'] for l in summary['learners']))},
            'exports_accepted': summary['counters']['exports_accepted'],
        }
        log(json.dumps({'inspect': name, 'questions': out[name]['questions'], 'distinct_curves': out[name]['diversity']['distinct_weekly_curves'],
                        'gain_sd': round(out[name]['diversity']['gain_sd_all'], 4)}))
    write('inspection.json', out)
    import hashlib
    import subprocess
    real = ROOT / 'runtime/learning.sqlite'
    write('reproduce.json', {
        'synthetic': True, 'study': CFG['study'], 'config': 'configs/simulation-study.json',
        'code_revision': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip() or None,
        'commands': ['python scripts/run_simulation_campaigns.py --worker 0   # A1, A2, A3, B1, N1',
                     'python scripts/run_simulation_campaigns.py --worker 1   # L1 (1000 élèves)',
                     'python scripts/run_simulation_study.py inspect main sensitivity replicate shift size families ui',
                     'python -m pytest tests/test_simulation_learners.py tests/test_simulation_models.py'],
        'campaign_outputs': 'runtime/simulation/<étude>/campaigns/<nom>/ (base synthetic-*.sqlite, hidden/, campaign.json ; non versionnés)',
        'real_learner_db_sha256': hashlib.sha256(real.read_bytes()).hexdigest() if real.exists() else None,
        'note': 'L’empreinte de runtime/learning.sqlite permet de vérifier qu’aucune campagne ne l’a modifiée.'})


# ------------------------------------------------------------------ stage: main
def main_stage():
    folder, summary, data, items, learners = campaign('A1')
    ids = sorted(data)
    splits = split(ids)
    results = {'campaign': 'A1', 'protocol': 'learner_disjoint_70_15_15 (split_seed 42); GRU seeds 42, 17, 83',
               'splits': {k: len(v) for k, v in splits.items()}, 'seeds': {}}
    test_rows = None
    for seed in G['seeds']:
        model, cfg = gru(f'A1-s{seed}', data, splits, seed)
        rows = rows_for(data, splits['test'], model, cfg, items, learners)
        results['seeds'][str(seed)] = evaluate(rows, f'A1 · test · GRU graine {seed}', {'gru_config': cfg})
        if seed == G['seeds'][0]:
            test_rows = rows
    # Cross-fitting: every learner predicted by a GRU that never saw them (5 folds).
    rng = random.Random(2026); shuffled = ids[:]; rng.shuffle(shuffled)
    folds = [shuffled[i::5] for i in range(5)]
    cross_rows = []
    for k, fold in enumerate(folds):
        rest = [i for i in ids if i not in set(fold)]
        inner = split(rest)
        fs = {'train': inner['train'] + inner['test'], 'validation': inner['validation'], 'test': fold}
        model, cfg = gru(f'A1-fold{k}', data, fs, G['seeds'][0])
        cross_rows += rows_for(data, fold, model, cfg, items, learners)
    results['crossfit'] = evaluate(cross_rows, 'A1 · 200 élèves · validation croisée (5 plis)')
    write('results/main.json', results)
    with gzip.open(OUT / 'results/A1-crossfit-questions.json.gz', 'wt', encoding='utf-8') as f:
        json.dump(cross_rows, f, ensure_ascii=False)
    log(json.dumps({'main': 'done', 'test_questions': len(test_rows), 'crossfit_questions': len(cross_rows)}))


# ------------------------------------------------------------------ stage: sensitivity (training length)
def sensitivity():
    """The O08 schedule (12 epochs) stopped some A1 runs while validation log-loss was still falling.
    Same split, same seeds, up to 40 epochs with patience 6, chosen on validation only. Reported next
    to the main result, never in its place."""
    folder, summary, data, items, learners = campaign('A1')
    splits = split(sorted(data))
    out = {'protocol': 'A1, même partition ; au plus 40 époques, patience 6 ; meilleur modèle sur la validation', 'seeds': {}}
    for seed in G['seeds']:
        name = f'A1-long-s{seed}'
        mfolder = OUT / 'models' / name
        if (mfolder / 'model.pt').exists():
            model, cfg = sm.load_gru(mfolder)
        else:
            model, cfg = sm.train_gru(data, splits, mfolder, seed=seed, hidden=G['hidden'], context=G['context'], batch_size=G['batch_size'],
                                      epochs=40, patience=6, lr=G['lr'], weight_decay=G['weight_decay'], log=log, label=name)
        rows = rows_for(data, splits['test'], model, cfg, items, learners)
        res = sm.compare(rows, replicates=B['replicates'], seed=B['seed'])
        out['seeds'][str(seed)] = {**res, 'epochs_completed': cfg['epochs_completed'], 'best_epoch': cfg['best_epoch']}
        log(json.dumps({'sensitivity': seed, 'best_epoch': cfg['best_epoch'], 'gru_brier': round(res['common']['metrics']['gru']['brier'], 4)}))
    write('results/sensitivity.json', out)


# ------------------------------------------------------------------ stage: replicate
def replicate():
    out = {}
    for name in ('A2', 'A3'):
        folder, summary, data, items, learners = campaign(name)
        splits = split(sorted(data))
        model, cfg = gru(f'{name}-s{G["seeds"][0]}', data, splits, G['seeds'][0])
        out[name] = evaluate(rows_for(data, splits['test'], model, cfg, items, learners), f'{name} · test')
    write('results/replications.json', out)


# ------------------------------------------------------------------ stage: shift (other simulator, noisier answers)
def shift():
    _, _, a1, _, _ = campaign('A1')
    a1_model, a1_cfg = gru(f'A1-s{G["seeds"][0]}', a1, split(sorted(a1)), G['seeds'][0])
    out = {}
    for name in ('B1', 'N1'):
        folder, summary, data, items, learners = campaign(name)
        splits = split(sorted(data))
        own_model, own_cfg = gru(f'{name}-s{G["seeds"][0]}', data, splits, G['seeds'][0])
        own = rows_for(data, splits['test'], own_model, own_cfg, items, learners)
        moved = rows_for(data, splits['test'], a1_model, a1_cfg, items, learners)
        # The A1 GRU never saw any learner of this population: all 200 can be its test set.
        moved_all = rows_for(data, sorted(data), a1_model, a1_cfg, items, learners)
        out[name] = {'trained_on_same_population': evaluate(own, f'{name} · GRU entraîné sur {name}'),
                     'trained_on_A1': evaluate(moved, f'{name} · GRU entraîné sur A1 (transfert)'),
                     'all_learners_A1_gru': evaluate(moved_all, f'{name} · les {len(data)} élèves · GRU entraîné sur A1 (transfert)')}
        if name == 'B1':
            atyp_all = [r for r in moved_all if r['family'] == 'progression_atypique']
            out[name]['atypical_all_learners_A1_gru'] = {**sm.compare(atyp_all, replicates=B['replicates'], seed=B['seed']),
                                                         'trend': sm.trend_recovery(atyp_all, min_items=8)}
            atyp = [r for r in moved if r['family'] == 'progression_atypique']
            atyp_own = [r for r in own if r['family'] == 'progression_atypique']
            out[name]['atypical_family'] = {'trained_on_A1': sm.compare(atyp, replicates=B['replicates'], seed=B['seed']),
                                            'trained_on_B1': sm.compare(atyp_own, replicates=B['replicates'], seed=B['seed']),
                                            'trend_A1': sm.trend_recovery(atyp, min_items=8), 'trend_B1': sm.trend_recovery(atyp_own, min_items=8)}
    write('results/shift.json', out)


# ------------------------------------------------------------------ stage: size (L1)
def l1_layout(data):
    ids = sorted(data); rng = random.Random(404); rng.shuffle(ids)
    return {'test': ids[:150], 'validation': ids[150:250], 'pool': ids[250:]}


def size():
    folder, summary, data, items, learners = campaign('L1')
    lay = l1_layout(data)
    out = {'layout': {k: len(v) for k, v in lay.items()}, 'cohorts': {}}
    for cohort, n_train in ((50, 35), (200, 140), (1000, 700)):
        per_seed = {}
        for seed in G['seeds']:
            train = random.Random(f'size-{cohort}-{seed}').sample(lay['pool'], n_train)
            model, cfg = gru(f'L1-size{cohort}-s{seed}', data, {'train': train, 'validation': lay['validation'], 'test': lay['test']}, seed)
            rows = rows_for(data, lay['test'], model, cfg, items, learners)
            per_seed[str(seed)] = {**sm.compare(rows, replicates=B['replicates'], seed=B['seed']), 'train_learners': n_train,
                                   'epochs_completed': cfg['epochs_completed'], 'best_epoch': cfg['best_epoch']}
        out['cohorts'][str(cohort)] = per_seed
        log(json.dumps({'size': cohort, 'gru_brier': [round(v['common']['metrics']['gru']['brier'], 4) for v in per_seed.values()]}))
    write('results/size.json', out)


def families():
    folder, summary, data, items, learners = campaign('L1')
    lay = l1_layout(data)
    fam = {lid: v['family'] for lid, v in learners.items()}
    out = {}
    for f in sl.FAMILIES_A:
        without = [i for i in lay['pool'] if fam[i] != f]
        matched = random.Random(f'matched-{f}').sample(lay['pool'], len(without))
        test = [i for i in lay['test'] if fam[i] == f]
        res = {}
        for label, train in (('absente', without), ('presente_meme_taille', matched)):
            model, cfg = gru(f'L1-{label}-{f}', data, {'train': train, 'validation': lay['validation'], 'test': test}, G['seeds'][0])
            res[label] = {**sm.compare(rows_for(data, test, model, cfg, items, learners), replicates=B['replicates'], seed=B['seed']),
                          'train_learners': len(train), 'family_in_train': sum(fam[i] == f for i in train)}
        out[f] = res
        log(json.dumps({'family': f, 'absent': round(res['absente']['common']['metrics']['gru']['brier'], 4),
                        'present': round(res['presente_meme_taille']['common']['metrics']['gru']['brier'], 4)}))
    write('results/families.json', out)


# ------------------------------------------------------------------ stage: ui
def ui():
    """Interface data for A1: every learner, every question, out-of-fold GRU predictions."""
    folder, summary, data, items, learners = campaign('A1')
    with gzip.open(OUT / 'results/A1-crossfit-questions.json.gz', 'rt', encoding='utf-8') as f:
        cross = json.load(f)
    by_learner = defaultdict(list)
    for r in cross:
        by_learner[r['learner']].append(r)
    days = defaultdict(list)
    for line in gzip.open(folder / 'hidden/days.jsonl.gz', 'rt', encoding='utf-8'):
        d = json.loads(line); days[d['sim_id']].append(d)
    events = defaultdict(list)
    for line in gzip.open(folder / 'hidden/events.jsonl.gz', 'rt', encoding='utf-8'):
        e = json.loads(line); events[e['sim_id']].append(e)
    errors = defaultdict(Counter)
    with sqlite3.connect(folder / summary['database']) as conn:
        for lid, ex, res in conn.execute('SELECT learner, exercise, result FROM items WHERE answered_at IS NOT NULL'):
            key = json.loads(res).get('error_key')
            if key:
                errors[lid][f'{ex} · {key}'] += 1
    params = {p['sim_id']: p for p in json.load(open(folder / 'hidden/learners.json', encoding='utf-8'))}
    explorer = []
    for lid, info in learners.items():
        sid = info['sim_id']
        p = params[sid]
        q = [[r['t'], round(r['day'], 3) if r['day'] is not None else None, r['exercise'], r['level'], r['skill'], r['y'],
              None if r['elo'] is None else round(r['elo'], 4), None if r['naive'] is None else round(r['naive'], 4),
              None if r['gru'] is None else round(r['gru'], 4), None if r['p_true'] is None else round(r['p_true'], 4)]
             for r in sorted(by_learner[lid], key=lambda r: r['t'])]
        explorer.append({'sim_id': sid, 'learner': lid, 'family': info['family'],
                         'family_label': sl.FAMILIES_A[info['family']]['label'],
                         'hidden': {'p_day': round(p['p_day'], 3), 'motivation_start': round(p['motivation'], 3), 'lapse': round(p['lapse'], 3),
                                    'rho0': round(p['rho0'], 1), 'tau_mean': round(float(np.mean(list(p['tau'].values()))), 1)},
                         'days': [[d['day'], d['status'][0], int(bool(d['practised'])), [round(d['ability'][k], 3) for k in sl.SKILLS]] for d in days[sid]],
                         'events': [{k: v for k, v in e.items() if k in ('day', 'event', 'kind', 'answered', 'correct', 'stopped', 'until')}
                                    for e in events[sid] if e['event'] != 'created'],
                         'errors': errors[lid].most_common(6), 'questions': q})
    explorer.sort(key=lambda x: x['sim_id'])
    payload = {'schema': 'declic-sim-explorer-v1', 'synthetic': True, 'campaign': 'A1', 'skills': sl.SKILLS,
               'question_columns': ['t', 'jour', 'exercice', 'niveau', 'compétence', 'juste', 'elo', 'naif', 'gru', 'p_vraie'],
               'note': 'GRU : prévisions hors échantillon (validation croisée en 5 plis : chaque élève est prédit par un réseau qui ne l’a jamais vu).',
               'learners': explorer}
    with gzip.open(OUT / 'ui/A1-explorer.json.gz', 'wt', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
    log(json.dumps({'ui': 'explorer', 'learners': len(explorer)}))


STAGES = {'inspect': inspect, 'main': main_stage, 'sensitivity': sensitivity, 'replicate': replicate, 'shift': shift, 'size': size, 'families': families, 'ui': ui}

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stages', nargs='+', choices=list(STAGES))
    for stage in ap.parse_args().stages:
        (OUT / 'ui').mkdir(parents=True, exist_ok=True); (OUT / 'results').mkdir(parents=True, exist_ok=True)
        STAGES[stage]()
