"""DÉCLIC-native knowledge tracing on SYNTHETIC learners: data, EnhancedGRU training, comparison.

Inputs are ONLY what DÉCLIC stores in a synthetic database (answered items, in order). The
hidden folder of a campaign is read by ``hidden_truth`` for the analysis and never by the data
builder or the models.

Reused from the O08 pipeline without modification (their source hashes are part of the served
models' provenance): ``cloud_training.encode / windows / batch / model_for / forward / measure /
split_learners / fit_items`` and ``models_v2.EnhancedGRU``. The training loop mirrors
``cloud_training.train`` (AdamW 1e-3, weight decay 1e-3, batches of 16, gradient clip 1,
best validation log-loss, patience 4) because that function is bound to the public archives.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import sqlite3
import time

import numpy as np
import torch
from torch import nn

from . import cloud_training as ct
from . import learning_catalog as cat

SKILLS = [s['id'] for s in cat.SKILLS]
MODELS = ('elo', 'gru', 'naive')
LABELS = {'elo': 'Elo (declic-elo-v1)', 'gru': 'GRU DÉCLIC (EnhancedGRU)', 'naive': 'Naïf (taux lissé au même niveau)'}


# ------------------------------------------------------------------ data DÉCLIC stores
def item_key(exercise, level, cents=None):
    """Same key as the O08 export ('exercise@level'); the staircase also states its gap (in octave
    steps of cents), the information the Elo model receives through d(cents)."""
    if exercise == 'hauteur-seuil' and cents:
        return f'{exercise}@{level}@c{int(round(math.log2(max(cents, 1))))}'
    return f'{exercise}@{level}'


def load_synthetic(db_path):
    """learner -> chronological list of answered items, exactly as DÉCLIC stored them."""
    out = defaultdict(list)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        names = {r['id']: r['name'] for r in conn.execute('SELECT id, name FROM learners')}
        if any(not n.startswith('SYNTHÉTIQUE ') for n in names.values()):
            raise ValueError('Base non synthétique : refus.')
        rows = conn.execute('''SELECT id, learner, session, seq, exercise, level, skill, created_at, answered_at,
                                      correct, served, prediction FROM items
                               WHERE answered_at IS NOT NULL ORDER BY learner, answered_at, seq''').fetchall()
    for r in rows:
        served = json.loads(r['served'])
        pred = json.loads(r['prediction'])
        cents = (served.get('detail') or {}).get('cents')
        out[r['learner']].append({
            'item': r['id'], 'session': r['session'], 'exercise': r['exercise'], 'level': r['level'], 'skill': r['skill'],
            'created_at': r['created_at'], 'answered_at': r['answered_at'], 'y': int(r['correct']),
            'key': item_key(r['exercise'], r['level'], cents),
            'elo': pred.get('p') if pred.get('status') == 'ok' else None, 'elo_status': pred.get('status'),
            'naive': pred.get('baseline'), 'name': names[r['learner']]})
    return dict(out)


def o08_rows(history):
    """The O08 encoder input (same shape as /api/learn/.../export 'o08_prepared_rows')."""
    return [{'exercise': h['key'], 'time': h['answered_at'], 'obs': [[SKILLS.index(h['skill']), float(h['y']), 1.0]]}
            for h in history]


# ------------------------------------------------------------------ training
def _seed_all(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def train_gru(data, splits, out_dir, *, seed=42, hidden=48, context=64, batch_size=16, epochs=12, patience=4,
              lr=1e-3, weight_decay=1e-3, log=print, label='declic-synthetic'):
    """Train an EnhancedGRU on the learners of splits['train'], select on splits['validation']."""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    _seed_all(seed)
    device = torch.device('cpu')
    learners = {k: o08_rows(v) for k, v in data.items()}
    K = len(SKILLS)
    items = ct.fit_items(learners, splits['train'])
    sets = {k: ct.windows(learners, ids, K, items, context) for k, ids in splits.items() if k in ('train', 'validation')}
    model = ct.model_for('enhanced_gru', K, items, hidden, context).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    criterion = nn.BCEWithLogitsLoss(reduction='none')
    best, best_state, stale, records, epoch = float('inf'), None, 0, [], 0
    t0 = time.time()
    while epoch < epochs and stale < patience:
        order = list(range(len(sets['train']))); random.Random(seed + epoch).shuffle(order)
        model.train()
        losses = []
        for offset in range(0, len(order), batch_size):
            values = ct.batch([sets['train'][i] for i in order[offset:offset + batch_size]], device)
            logits = ct.forward(model, 'enhanced_gru', values); y, w = values[4:]
            loss = (criterion(logits, y) * w).sum() / w.sum().clamp_min(1)
            if not torch.isfinite(loss):
                raise ValueError('Non-finite training loss')
            optimizer.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step(); losses.append(float(loss))
        metrics = ct.measure(model, 'enhanced_gru', sets['validation'], device, True, batch_size)
        epoch += 1
        records.append({'epoch': epoch, 'train_loss': float(np.mean(losses)), 'validation': {k: v for k, v in metrics.items() if k != 'calibration_bins'}})
        if metrics['log_loss'] < best:
            best, stale = metrics['log_loss'], 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
        log(json.dumps({'model': label, 'seed': seed, 'epoch': epoch, 'train_loss': round(records[-1]['train_loss'], 5),
                        'validation_log_loss': round(metrics['log_loss'], 5), 'best': round(best, 5)}))
    model.load_state_dict(best_state)
    n_params = sum(p.numel() for p in model.parameters())
    config = {'schema': 'declic-synthetic-gru-v1', 'synthetic': True, 'label': label, 'architecture': 'EnhancedGRU',
              'K': K, 'skills': SKILLS, 'items': items, 'hidden': hidden, 'context': context, 'batch_size': batch_size,
              'epochs_max': epochs, 'patience': patience, 'lr': lr, 'weight_decay': weight_decay, 'seed': seed,
              'epochs_completed': epoch, 'best_epoch': int(np.argmin([r['validation']['log_loss'] for r in records]) + 1),
              'parameters': int(n_params), 'learners': {k: len(v) for k, v in splits.items()},
              'train_windows': len(sets['train']), 'train_seconds': round(time.time() - t0, 1),
              'split_digest': {k: hashlib.sha256(json.dumps(sorted(v)).encode()).hexdigest()[:16] for k, v in splits.items()},
              'reused_from_o08': ['cloud_training.encode', 'cloud_training.windows', 'cloud_training.batch', 'cloud_training.model_for',
                                  'cloud_training.forward', 'cloud_training.measure', 'cloud_training.fit_items', 'models_v2.EnhancedGRU'],
              'inputs': 'Réponses stockées par DÉCLIC uniquement (exercice@niveau, compétence, juste/faux, ordre). Aucun état caché, aucune bonne réponse.'}
    torch.save({'config': config, 'state_dict': best_state}, out / 'model.pt')
    config['model_sha256'] = hashlib.sha256((out / 'model.pt').read_bytes()).hexdigest()
    (out / 'config.json').write_text(json.dumps(config, ensure_ascii=False, indent=1), encoding='utf-8')
    (out / 'history.json').write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding='utf-8')
    return model, config


def load_gru(folder):
    saved = torch.load(Path(folder) / 'model.pt', map_location='cpu', weights_only=False)
    cfg = {**saved['config'], 'model_sha256': hashlib.sha256((Path(folder) / 'model.pt').read_bytes()).hexdigest()}
    model = ct.model_for('enhanced_gru', cfg['K'], cfg['items'], cfg['hidden'], cfg['context'])
    model.load_state_dict(saved['state_dict']); model.eval()
    return model, cfg


def predict_gru(model, cfg, history):
    """P(correct) of every answered item of one learner, from strictly earlier answers only.

    Same chunking as cloud_training.windows (context-1 targets per window, one warm-up step,
    counts carry the whole earlier prefix). The first answer of a learner has no history: no
    prediction (the O08 pipeline reports cold start separately)."""
    rows = o08_rows(history)
    K, context = cfg['K'], cfg['context']
    encoded = ct.encode(rows, K, cfg['items'])
    T = len(rows)
    out = [None] * T
    with torch.no_grad():
        for start in range(0, T, context - 1):
            stop = min(start + context - 1, T)
            left = max(start - 1, 0)
            sample = tuple(a[left:stop].copy() for a in encoded)
            values = ct.batch([sample], torch.device('cpu'))
            prob = torch.sigmoid(ct.forward(model, 'enhanced_gru', values))[0].numpy()
            for t in range(start, stop):
                if t == 0:
                    continue
                out[t] = float(prob[t - left, SKILLS.index(history[t]['skill'])])
    return out


# ------------------------------------------------------------------ hidden truth (analysis only)
def hidden_truth(campaign_dir):
    """item id -> hidden record; learner id -> sim id / family. Analysis side only."""
    folder = Path(campaign_dir) / 'hidden'
    items = {}
    with gzip.open(folder / 'items.jsonl.gz', 'rt', encoding='utf-8') as f:
        for line in f:
            r = json.loads(line); items[r['item']] = r
    learners = {}
    with gzip.open(folder / 'events.jsonl.gz', 'rt', encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            if r['event'] == 'created':
                learners[r['learner']] = {'sim_id': r['sim_id'], 'family': r['family'], 'variant': r['variant']}
    return items, learners


def question_table(data, learner_ids, model, cfg, truth_items, truth_learners):
    """One row per answered question of the given learners, with every model's pre-answer prediction."""
    rows = []
    for lid in learner_ids:
        history = data[lid]
        gru = predict_gru(model, cfg, history) if model is not None else [None] * len(history)
        seen = defaultdict(int)
        prev_time = None
        for t, h in enumerate(history):
            hidden = truth_items.get(h['item'], {})
            at = datetime.fromisoformat(h['answered_at'])
            gap = (at - prev_time).total_seconds() / 86400 if prev_time else None
            rows.append({'learner': lid, 'family': truth_learners.get(lid, {}).get('family'), 't': t, 'item': h['item'],
                         'session': h['session'], 'exercise': h['exercise'], 'level': h['level'], 'skill': h['skill'], 'y': h['y'],
                         'elo': h['elo'], 'naive': h['naive'], 'gru': gru[t], 'p_true': hidden.get('p_true'),
                         'n_prior': t, 'n_prior_skill': seen[h['skill']], 'gap_days': gap,
                         'day': hidden.get('day'), 'answered_at': h['answered_at'], 'kind': hidden.get('kind')})
            seen[h['skill']] += 1
            prev_time = at
    return rows


# ------------------------------------------------------------------ metrics
EPS = 1e-6


def _metrics(y, p):
    y = np.asarray(y, float); p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    out = {'n': int(len(y)), 'brier': float(np.mean((p - y) ** 2)),
           'log_loss': float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
           'observed': float(y.mean()) if len(y) else None, 'mean_predicted': float(p.mean()) if len(p) else None}
    if 0 < y.sum() < len(y):
        from sklearn.metrics import roc_auc_score
        out['auc'] = float(roc_auc_score(y, p))
    bins = np.minimum((p * 10).astype(int), 9)
    ece = 0.0; cal = []
    for b in range(10):
        keep = bins == b
        if keep.any():
            ece += keep.mean() * abs(p[keep].mean() - y[keep].mean())
            cal.append({'from': b / 10, 'count': int(keep.sum()), 'predicted': float(p[keep].mean()), 'observed': float(y[keep].mean())})
    out['ece'] = float(ece); out['calibration'] = cal
    return out


def _per_learner_sums(rows, keys):
    """For the learner bootstrap: per learner, sums of squared errors / log losses / counts."""
    by = defaultdict(lambda: defaultdict(float))
    for r in rows:
        acc = by[r['learner']]
        acc['n'] += 1
        for k in keys:
            p = min(max(r[k], EPS), 1 - EPS)
            acc[f'{k}_se'] += (p - r['y']) ** 2
            acc[f'{k}_ll'] += -(r['y'] * math.log(p) + (1 - r['y']) * math.log(1 - p))
            if r.get('p_true') is not None:
                acc[f'{k}_te'] += (p - r['p_true']) ** 2
        if r.get('p_true') is not None:
            acc['nt'] += 1
    return by


def bootstrap(rows, keys, replicates=1000, seed=2026):
    """Percentile intervals by resampling LEARNERS (all their questions together)."""
    by = _per_learner_sums(rows, keys)
    learners = sorted(by)
    if not learners:
        return {}
    arr = {name: np.array([by[l][name] for l in learners]) for name in by[learners[0]]}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(learners), size=(replicates, len(learners)))
    n = arr['n'][idx].sum(1)
    out = {}
    for k in keys:
        for metric, suffix in (('brier', 'se'), ('log_loss', 'll')):
            values = arr[f'{k}_{suffix}'][idx].sum(1) / n
            out.setdefault(k, {})[metric] = [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]
    pairs = [(a, b) for i, a in enumerate(keys) for b in keys[i + 1:]]
    out['differences'] = {}
    # distance to the hidden probability: only where every row of the slice carries it
    measures = [('brier', 'se', 'n'), ('log_loss', 'll', 'n')]
    if 'nt' in arr and arr['nt'].sum() == arr['n'].sum():
        measures.append(('to_truth', 'te', 'nt'))
    for a, b in pairs:
        for metric, suffix, count in measures:
            n = arr[count][idx].sum(1)
            d = (arr[f'{a}_{suffix}'][idx].sum(1) - arr[f'{b}_{suffix}'][idx].sum(1)) / n
            point = float((arr[f'{a}_{suffix}'].sum() - arr[f'{b}_{suffix}'].sum()) / arr[count].sum())
            out['differences'][f'{a}-{b}:{metric}'] = {'point': point, 'ci95': [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
                                                         'share_below_zero': float((d < 0).mean())}
    return out


def compare(rows, keys=MODELS, replicates=1000, seed=2026):
    """Each model on its own coverage, and all models on the questions every model predicts."""
    total = len(rows)
    own = {}
    for k in keys:
        sub = [r for r in rows if r[k] is not None]
        own[k] = {**_metrics([r['y'] for r in sub], [r[k] for r in sub]), 'coverage': len(sub) / total if total else 0.0,
                  'learners': len({r['learner'] for r in sub})}
    common = [r for r in rows if all(r[k] is not None for k in keys)]
    joint = {k: _metrics([r['y'] for r in common], [r[k] for r in common]) for k in keys}
    with_truth = [r for r in common if r['p_true'] is not None]
    truth = {}
    if with_truth:
        pt = np.array([r['p_true'] for r in with_truth])
        y = np.array([r['y'] for r in with_truth])
        truth['oracle'] = {'brier': float(np.mean((pt - y) ** 2)), 'note': 'Brier de la vraie probabilité cachée : le minimum atteignable en moyenne.'}
        for k in keys:
            p = np.array([r[k] for r in with_truth])
            truth[k] = {'mse_to_truth': float(np.mean((p - pt) ** 2)), 'mae_to_truth': float(np.mean(np.abs(p - pt))),
                        'corr_with_truth': float(np.corrcoef(p, pt)[0, 1]) if p.std() > 0 and pt.std() > 0 else None}
    # Where Elo abstains (fewer than 5 answers in the skill): GRU and naive only.
    early = [r for r in rows if r['elo'] is None and r['gru'] is not None and r['naive'] is not None]
    abstention = None
    if early:
        abstention = {'questions': len(early), 'learners': len({r['learner'] for r in early}),
                      'metrics': {k: _metrics([r['y'] for r in early], [r[k] for r in early]) for k in ('gru', 'naive')},
                      'bootstrap': bootstrap(early, ['gru', 'naive'], replicates, seed)}
    return {'questions': total, 'learners': len({r['learner'] for r in rows}), 'own_coverage': own, 'elo_abstains': abstention,
            'common': {'questions': len(common), 'learners': len({r['learner'] for r in common}), 'metrics': joint,
                       'bootstrap': bootstrap(common, list(keys), replicates, seed)},
            'truth_recovery': truth}


def slices(rows, keys=MODELS):
    """Brier on the common questions, by slice; Elo − GRU with a learner-bootstrap interval (≥ 5 learners)."""
    common = [r for r in rows if all(r[k] is not None for k in keys)]

    def table(name, fn, order=None):
        groups = defaultdict(list)
        for r in common:
            g = fn(r)
            if g is not None:
                groups[g].append(r)
        out = []
        for g in (order or sorted(groups)):
            sub = groups.get(g)
            if not sub:
                continue
            row = {'group': g, 'questions': len(sub), 'learners': len({r['learner'] for r in sub}), 'observed': float(np.mean([r['y'] for r in sub]))}
            for k in keys:
                p = np.array([r[k] for r in sub]); y = np.array([r['y'] for r in sub])
                row[k] = float(np.mean((p - y) ** 2))
                if all(r['p_true'] is not None for r in sub):
                    row[f'{k}_to_truth'] = float(np.mean((p - np.array([r['p_true'] for r in sub])) ** 2))
            if row['learners'] >= 5:
                diff = bootstrap(sub, ['elo', 'gru'], 1000, 2026)['differences']
                row['elo_minus_gru'] = {m: diff[f'elo-gru:{m}'] for m in ('brier', 'to_truth') if f'elo-gru:{m}' in diff}
            out.append(row)
        return {'slice': name, 'rows': out}
    hist_bins = ['5–19', '20–49', '50–99', '100–199', '200+']

    def hist(r):
        n = r['n_prior']
        return None if n < 5 else '5–19' if n < 20 else '20–49' if n < 50 else '50–99' if n < 100 else '100–199' if n < 200 else '200+'

    def gap(r):
        g = r['gap_days']
        return None if g is None else 'même séance (< 1 h)' if g < 1 / 24 else 'moins de 2 jours' if g < 2 else '2 à 6 jours' if g < 7 else '7 jours et plus'
    return [table('compétence', lambda r: r['skill']), table('exercice', lambda r: r['exercise']),
            table('famille', lambda r: r['family']), table('historique (réponses déjà données)', hist, hist_bins),
            table('pause avant la question', gap, ['même séance (< 1 h)', 'moins de 2 jours', '2 à 6 jours', '7 jours et plus'])]


def trend_recovery(rows, keys=MODELS, min_items=12):
    """Do the models follow each learner's TRUE trend? Per learner × skill: change of the hidden
    probability between the first and last third of its items, against the change of each
    model's prediction on the same items (common scale: probability of success)."""
    by = defaultdict(list)
    for r in rows:
        if r['p_true'] is not None and all(r[k] is not None for k in keys):
            by[(r['learner'], r['skill'])].append(r)
    deltas = {k: [] for k in keys}; truth = []
    for seq in by.values():
        if len(seq) < min_items:
            continue
        third = len(seq) // 3
        first, last = seq[:third], seq[-third:]
        truth.append(np.mean([r['p_true'] for r in last]) - np.mean([r['p_true'] for r in first]))
        for k in keys:
            deltas[k].append(np.mean([r[k] for r in last]) - np.mean([r[k] for r in first]))
    truth = np.array(truth)
    out = {'trajectories': int(len(truth)), 'min_items': min_items,
           'true_change_mean': float(truth.mean()) if len(truth) else None}
    for k in keys:
        d = np.array(deltas[k])
        if len(d) > 2:
            out[k] = {'corr_with_true_change': float(np.corrcoef(d, truth)[0, 1]) if d.std() > 0 and truth.std() > 0 else None,
                      'same_direction': float(np.mean(np.sign(d) == np.sign(truth))),
                      'mean_abs_error_of_change': float(np.mean(np.abs(d - truth)))}
    return out
