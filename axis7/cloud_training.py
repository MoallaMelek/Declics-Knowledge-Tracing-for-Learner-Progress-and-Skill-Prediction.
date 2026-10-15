"""Real musical benchmarks: atomic groups, learner-disjoint evaluation, resumable DL.

No source outcomes are interpreted as general musical mastery. ZIPs are read in
place; neither untrusted archive code nor arbitrary pickle files are executed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import random
import re
import subprocess
import platform
from datetime import datetime
import time
import zipfile

import numpy as np
import torch
from torch import nn
from sklearn.metrics import average_precision_score, roc_auc_score

from .models import DKT
from .models_v2 import EnhancedGRU, SimpleKTStyleAttention

VERSION = 'musical-cloud-v2'
PREPROCESSING = {'singpad': 'singpad-datetime-v2', 'amme': 'amme-block-v1',
                 'yousician': 'yousician-active-day-v1'}


def parse_singpad_time(value):
    """Explicit local calendar formats; no timezone or locale inference."""
    if not isinstance(value, str):
        raise ValueError('SingPAD timestamp must be a string')
    match = re.fullmatch(r'(\d{4})([/\-])(\d{1,2})\2(\d{1,2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?', value)
    if match is None:
        raise ValueError('Unsupported SingPAD local timestamp format')
    year, _, month, day, hour, minute, second = match.groups()
    try:
        return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second or 0))
    except ValueError as error:
        raise ValueError('Invalid SingPAD calendar timestamp') from error


def chronological_audit(learners):
    """Check parsed local times, strictly increasing atomic groups, no raw IDs."""
    inversions = duplicates = 0
    for rows in learners.values():
        times = [parse_singpad_time(r['time']) for r in rows]
        inversions += sum(a > b for a, b in zip(times, times[1:]))
        duplicates += len(times) - len(set(times))
    return {'learners': len(learners), 'time_groups': sum(map(len, learners.values())),
            'chronological_inversions': inversions, 'duplicate_time_groups': duplicates}
SOURCES = {
    'amme': {'instrument': 'keyboard', 'target': 'next_block_pitch_dtw_coverage_adjusted_score',
             'citation': 'Chmiel et al. (2025), doi:10.1371/journal.pone.0320055; OSF 2GVTY',
             'binary': False},
    'singpad': {'instrument': 'voice', 'target': 'next_recording_note_success_by_source_concept',
                'citation': 'Zhang et al. (2024), SingPAD, doi:10.5281/zenodo.12729828',
                'binary': True},
    'yousician': {'instrument': 'ukulele', 'target': 'next_active_day_success_fraction',
                  'citation': 'Yousician Open Data, https://yousician.com/open-data',
                  'binary': False},
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def csv_member(z, suffix):
    names = [n for n in z.namelist() if n.endswith(suffix) and not n.startswith('__MACOSX/')]
    if len(names) != 1:
        raise ValueError(f'Expected one {suffix}, found {len(names)}')
    return csv.DictReader(io.TextIOWrapper(z.open(names[0]), encoding='utf-8-sig', newline=''))


def stream_array(f, chunk_size=1024 * 1024):
    """Incremental JSON array reader (never loads the 585 MB document at once)."""
    decoder = json.JSONDecoder()
    buf = ''; started = False; ended = False; need_value = True; first = True
    while True:
        chunk = f.read(chunk_size)
        eof = not chunk
        buf += chunk
        while True:
            buf = buf.lstrip()
            if not started:
                if not buf:
                    break
                if buf[0] != '[':
                    raise ValueError('Expected a top-level JSON array')
                started = True; buf = buf[1:]; continue
            if ended:
                if buf:
                    raise ValueError('Trailing JSON content')
                break
            if not buf:
                break
            if need_value:
                if buf[0] == ']':
                    if not first:
                        raise ValueError('Trailing comma')
                    ended = True; buf = buf[1:]; continue
                try:
                    value, pos = decoder.raw_decode(buf)
                except json.JSONDecodeError:
                    if eof:
                        raise
                    break
                if not isinstance(value, dict):
                    raise ValueError('Each JSON entry must be an object')
                yield value
                buf = buf[pos:]; need_value = False; first = False
            elif buf[0] == ',':
                buf = buf[1:]; need_value = True
            elif buf[0] == ']':
                buf = buf[1:]; ended = True
            else:
                raise ValueError('Expected comma or array end')
        if eof:
            if not ended:
                raise ValueError('Truncated JSON array')
            return


def load_amme(path):
    groups = {}; conflicts = set(); count = 0
    aliases = {'lilij': 'fahif', 'jojav': 'tikit', 'holar': 'gokaj'}
    with zipfile.ZipFile(path) as z:
        for r in csv_member(z, 'replicreslong_di.csv'):
            count += 1
            if int(r['scoretype']) != 7:
                continue
            pid = aliases.get(r['pid'], r['pid'])
            key = (pid, int(r['block']), r['sessitem'], r['tune'])
            score = float(r['score'])
            if not 0 <= score <= 1 or not math.isfinite(score):
                raise ValueError('Invalid AMME score')
            if key in groups and groups[key] != score:
                conflicts.add(key)
            groups[key] = score
    # Within-block calendar order is not documented: hide the entire block.
    blocks = defaultdict(list)
    for key, score in groups.items():
        if key not in conflicts:
            blocks[key[:2]].append(score)
    rows = [{'learner': p, 'time': b, 'exercise': '', 'difficulty': 0.,
             'obs': [[0, float(np.mean(vals)), 1.]]} for (p, b), vals in blocks.items()]
    return rows, {'raw_rows': count, 'conflicting_performances_excluded': len(conflicts),
                  'unit': 'block mean of scoretype 7; all same-block outcomes hidden',
                  'score_meaning': 'pitch similarity adjusted by aligned coverage, not correctness'}


def load_singpad(path):
    mapping = {}; seen = {}; grouped = {}; duplicate = 0
    with zipfile.ZipFile(path) as z:
        for r in csv_member(z, 'opernDS.csv'):
            questions, concepts = json.loads(r['qc_array'])
            if len(questions) != len(concepts):
                raise ValueError('Invalid question/concept mapping')
            for q, c in zip(questions, concepts):
                key = (str(r['opern_id']), str(q))
                if key in mapping and mapping[key] != int(c):
                    raise ValueError('Conflicting concept mapping')
                mapping[key] = int(c)
        for r in csv_member(z, 'recordDS.csv'):
            rid = str(r['record_id'])
            if rid in seen:
                if seen[rid] != r:
                    raise ValueError('Conflicting recording ID')
                duplicate += 1; continue
            seen[rid] = r
            questions, outcomes = json.loads(r['qa_array'])
            if len(questions) != len(outcomes):
                raise ValueError('Invalid recording arrays')
            # Timestamp precision is a minute, with no timezone. Ties form one unit.
            parsed_time = parse_singpad_time(r['create_time'])
            key = (str(r['user_id']), parsed_time)
            g = grouped.setdefault(key, {'exercises': set(), 'obs': [], 'original_timestamps': set(),
                                         'recording_count': 0})
            g['exercises'].add(str(r['opern_id']))
            g['original_timestamps'].add(r['create_time'])
            g['recording_count'] += 1
            for q, y in zip(questions, outcomes):
                if y not in (0, 1):
                    raise ValueError('Invalid note outcome')
                g['obs'].append([mapping[(str(r['opern_id']), str(q))], int(y), 1.])
    rows = [{'learner': p, 'time': t.isoformat(), 'exercise': '|'.join(sorted(g['exercises'])),
             'original_timestamps': sorted(g['original_timestamps']),
             'recording_count': g['recording_count'],
             'difficulty': 0., 'obs': g['obs']} for (p, t), g in sorted(grouped.items())]
    return rows, {'recordings': len(seen), 'exact_duplicates_excluded': duplicate,
                  'note_labels': sum(len(r['obs']) for r in rows),
                  'unit': 'entire recording; equal timestamps hidden together',
                  'timezone': 'source local time, unspecified; never converted to UTC'}


def load_yousician(path):
    seen = set(); groups = {}; conflicts = set(); duplicates = 0; raw = 0; ignored = 0
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.endswith('.json') and not n.startswith('__MACOSX/')]
        if len(names) != 1:
            raise ValueError('Expected one Yousician JSON')
        with io.TextIOWrapper(z.open(names[0]), encoding='utf-8-sig') as f:
            for r in stream_array(f):
                raw += 1
                h = hashlib.sha256(json.dumps(r, sort_keys=True, separators=(',', ':')).encode()).digest()
                if h in seen:
                    duplicates += 1; continue
                seen.add(h)
                if r['play_mode'] != 'play':
                    ignored += 1; continue
                day = float(r['days_since_signup'])
                if not math.isfinite(day) or day < 0:
                    raise ValueError('Invalid relative time')
                key = (str(r['user_id']), int(r['session_index']), day,
                       str(r['exercise_id']), str(r['song_id']))
                counts = tuple(int(r[k]) for k in ('notes_evaluated', 'notes_successful',
                                                  'chords_evaluated', 'chords_successful'))
                n, a, c, b = counts
                if min(counts) < 0 or a > n or b > c:
                    raise ValueError('Invalid success counters')
                if key in groups and groups[key] != counts:
                    conflicts.add(key)
                groups[key] = counts
    days = defaultdict(lambda: [0, 0])
    zero = 0
    for key, (n, a, c, b) in groups.items():
        if key in conflicts:
            continue
        if n + c == 0:
            zero += 1; continue
        g = days[(key[0], int(math.floor(key[2])))]
        g[0] += a + b; g[1] += n + c
    # No future day exercise mix/difficulty/playing duration is available at query.
    rows = [{'learner': p, 'time': d, 'exercise': '', 'difficulty': 0.,
             'obs': [[0, a / n, 1.]]} for (p, d), (a, n) in days.items()]
    return rows, {'raw_rows': raw, 'exact_duplicates_excluded': duplicates,
                  'practice_rows_excluded': ignored, 'conflicting_groups_excluded': len(conflicts),
                  'zero_evaluation_groups_excluded': zero, 'unit': 'next active signup day',
                  'part_policy': 'global counters counted once per tied exercise/session/time group',
                  'target_weighting': 'each active day equally weighted; evaluated counters within day',
                  'limitation': 'no unique attempt ID; ambiguous repeated counters excluded, not guessed'}


def prepare(source, archive, cache):
    fingerprint = digest(archive)
    cache = Path(cache)
    if cache.exists():
        with gzip.open(cache, 'rt', encoding='utf-8') as f:
            result = json.load(f)
        if (result['sha256'] == fingerprint and result['version'] == VERSION
                and result.get('preprocessing') == PREPROCESSING[source] and result['source'] == source):
            if source == 'singpad':
                audit = chronological_audit(result['learners'])
                if audit['chronological_inversions'] or audit['duplicate_time_groups']:
                    raise ValueError('Corrupt chronological cache')
            return result
    rows, audit = {'amme': load_amme, 'singpad': load_singpad, 'yousician': load_yousician}[source](archive)
    learners = defaultdict(list)
    for row in rows:
        learners[row.pop('learner')].append(row)
    audit['single_group_learners_excluded'] = sum(len(rs) < 2 for rs in learners.values())
    order = (lambda r: parse_singpad_time(r['time'])) if source == 'singpad' else (lambda r: r['time'])
    learners = {p: sorted(rs, key=order) for p, rs in learners.items() if len(rs) >= 2}
    if source == 'singpad':
        audit['chronology'] = chronological_audit(learners)
        if audit['chronology']['chronological_inversions'] or audit['chronology']['duplicate_time_groups']:
            raise ValueError('SingPAD chronological integrity failed')
    result = {'version': VERSION, 'preprocessing': PREPROCESSING[source], 'source': source, 'sha256': fingerprint,
              'learners': learners, 'audit': audit}
    cache.parent.mkdir(parents=True, exist_ok=True)
    temp = cache.with_suffix('.tmp')
    with gzip.open(temp, 'wt', encoding='utf-8') as f:
        json.dump(result, f, separators=(',', ':'))
    temp.replace(cache)
    return result


def split_learners(learners, seed):
    ids = sorted(learners); random.Random(seed).shuffle(ids)
    if len(ids) < 10:
        raise ValueError('Need at least ten learners for disjoint evaluation')
    a = int(.7 * len(ids)); b = int(.85 * len(ids))
    return {'train': ids[:a], 'validation': ids[a:b], 'test': ids[b:]}


def fit_items(learners, ids):
    return {v: i + 1 for i, v in enumerate(sorted({r['exercise'] for p in ids for r in learners[p]
                                                 if r['exercise']}))}


def public_split_provenance(splits):
    """Publish counts/digests, never individual learner IDs; private resume keeps IDs."""
    groups = [set(splits[k]) for k in ('train', 'validation', 'test')]
    if any(groups[a] & groups[b] for a, b in ((0, 1), (0, 2), (1, 2))):
        raise ValueError('Learner leakage between splits')
    return {k: {'count': len(ids),
                'sha256': hashlib.sha256(json.dumps(sorted(ids), separators=(',', ':')).encode()).hexdigest()}
            for k, ids in splits.items()}


def encode(rows, K, items):
    """At t every outcome/count comes strictly from earlier atomic time groups."""
    T = len(rows); x = np.zeros((T, 4*K), np.float32)
    y = np.zeros((T, K), np.float32); w = np.zeros((T, K), np.float32)
    pi = np.zeros(T, np.int64); ci = np.zeros(T, np.int64); diff = np.zeros((T, 2), np.float32)
    success = np.zeros(K); failure = np.zeros(K); previous = np.zeros(2*K); prev_item = 0
    for t, r in enumerate(rows):
        x[t, :2*K] = previous
        x[t, 2*K:3*K] = np.log1p(success); x[t, 3*K:] = np.log1p(failure)
        pi[t] = prev_item; ci[t] = items.get(r['exercise'], 0)
        totals = np.zeros(K); positives = np.zeros(K)
        for k, v, weight in r['obs']:
            totals[k] += weight; positives[k] += v * weight
        y[t] = positives / np.maximum(totals, 1)
        # Cold start is reported separately, not scored as a history forecast.
        if t > 0:
            w[t] = totals
        previous = np.concatenate((totals - positives, positives)) / max(totals.sum(), 1)
        success += positives; failure += totals - positives; prev_item = ci[t]
    return x, pi, ci, diff, y, w


def apply_feature_mode(values, K, mode='full'):
    if mode == 'no_counts': values[0][:, 2*K:] = 0
    elif mode == 'no_recent': values[0][:, :2*K] = 0
    elif mode == 'no_items': values[1][:] = 0; values[2][:] = 0
    elif mode != 'full': raise ValueError('Unknown controlled ablation')
    return values


def windows(learners, ids, K, items, context, feature_mode='full'):
    samples = []
    for p in ids:
        encoded = apply_feature_mode(encode(learners[p], K, items), K, feature_mode)
        # Nonoverlapping target chunks; full past counts, one warm-up before chunks.
        for start in range(0, len(learners[p]), context - 1):
            stop = min(start + context - 1, len(learners[p]))
            left = max(start - 1, 0)
            sample = tuple(a[left:stop].copy() for a in encoded)
            if start:
                sample[-1][0] = 0
            if sample[-1].sum() > 0:
                samples.append(sample)
    return samples


def batch(samples, device):
    T = max(len(s[0]) for s in samples)
    result = []
    for i in range(6):
        shape = (len(samples), T) + samples[0][i].shape[1:]
        arr = np.zeros(shape, dtype=samples[0][i].dtype)
        for j, s in enumerate(samples):
            arr[j, :len(s[i])] = s[i]
        result.append(torch.from_numpy(arr).to(device))
    return result


def model_for(name, K, items, hidden, context):
    if name == 'dkt':
        return DKT(K, hidden)
    if name == 'enhanced_gru':
        return EnhancedGRU(K, len(items) + 1, hidden, context)
    if name == 'item_attention':
        return SimpleKTStyleAttention(K, len(items) + 1, hidden, context)
    raise ValueError('Only PyTorch deep learning models are supported')


def forward(model, name, inputs):
    return model(inputs[0][:, :, :2*model.K]) if name == 'dkt' else model(*inputs[:4])


def measure(model, name, samples, device, binary, batch_size, constant=None):
    ys = []; ps = []; weights = []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(samples), batch_size):
            values = batch(samples[start:start+batch_size], device)
            pred = torch.sigmoid(forward(model, name, values)).cpu().numpy()
            y, w = values[4].cpu().numpy(), values[5].cpu().numpy()
            mask = w > 0
            ys.extend(y[mask].tolist()); weights.extend(w[mask].tolist())
            ps.extend((pred[mask] if constant is None else np.full(mask.sum(), constant)).tolist())
    y = np.asarray(ys); p = np.clip(ps, 1e-7, 1-1e-7); w = np.asarray(weights)
    if not len(y) or not np.isfinite(p).all():
        raise ValueError('Empty or non-finite evaluation')
    avg = lambda v: float(np.average(v, weights=w))
    result = {'observed_targets': int(len(y)), 'label_weight': float(w.sum()),
              'mae': avg(abs(y-p)), 'rmse': math.sqrt(avg((y-p)**2))}
    if binary:
        result.update(log_loss=avg(-y*np.log(p)-(1-y)*np.log1p(-p)),
                      brier=avg(y*(1-p)**2+(1-y)*p**2),
                      mae_note=avg(y*(1-p)+(1-y)*p),
                      rmse_note=math.sqrt(avg(y*(1-p)**2+(1-y)*p**2)))
        # Exact weighted binary metrics from concept-level success/failure counts.
        labels = np.concatenate((np.ones(len(y)), np.zeros(len(y))))
        scores = np.tile(p, 2); counts = np.concatenate((w*y, w*(1-y)))
        result['roc_auc'] = float(roc_auc_score(labels, scores, sample_weight=counts)) if min(counts[:len(y)].sum(), counts[len(y):].sum()) > 0 else None
        result['pr_auc'] = float(average_precision_score(labels, scores, sample_weight=counts)) if counts[:len(y)].sum() > 0 else None
        bins = []
        assignments = np.minimum((p*10).astype(int), 9)
        for bin_index in range(10):
            lo = bin_index / 10
            keep = assignments == bin_index
            if keep.any():
                bins.append({'lower': float(lo), 'weight': float(w[keep].sum()),
                             'prediction': float(np.average(p[keep], weights=w[keep])),
                             'observed': float(np.average(y[keep], weights=w[keep]))})
        result['calibration_bins'] = bins
    return result


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temp.replace(path)


def save_resume(directory, state):
    """Keep two immutable generations + checksummed manifest (Drive interruption)."""
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / 'resume.json'
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'files': []}
    filename = f'checkpoint-{time.time_ns()}.pt'
    path = directory / filename; temp = path.with_suffix('.tmp')
    torch.save(state, temp); temp.replace(path)
    entry = {'name': filename, 'sha256': digest(path)}
    atomic_json(manifest_path, {'files': [entry] + old['files'][:1]})
    for entry in old['files'][1:]:
        (directory / entry['name']).unlink(missing_ok=True)


def load_resume(directory):
    path = Path(directory) / 'resume.json'
    if not path.exists():
        return None
    for entry in json.loads(path.read_text())['files']:
        if not re.fullmatch(r'checkpoint-\d+\.pt', entry['name']):
            raise ValueError('Unsafe checkpoint path')
        candidate = path.parent / entry['name']
        if candidate.exists() and digest(candidate) == entry['sha256']:
            return torch.load(candidate, map_location='cpu', weights_only=True)
    raise ValueError('No intact checkpoint; retain files and inspect Drive sync')


def train(source, archive, output, *, model_name='enhanced_gru', epochs=12,
          batch_size=16, hidden=48, context=64, seed=42, checkpoint_batches=25, resume=True,
          feature_mode='full'):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(min(4, torch.get_num_threads()))
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    prepared = prepare(source, archive, output / 'prepared.json.gz')
    learners = prepared['learners']; splits = split_learners(learners, seed)
    K = max(o[0] for rs in learners.values() for r in rs for o in r['obs']) + 1
    items = fit_items(learners, splits['train'])
    cfg = {'version': VERSION, 'preprocessing': PREPROCESSING[source],
           'source': source, 'sha256': prepared['sha256'], 'seed': seed,
           'model': model_name, 'hidden': hidden, 'context': context, 'K': K, 'items': items,
           'batch_size': batch_size, 'feature_mode': feature_mode,
           'protocol': 'learner_disjoint_70_15_15', 'splits': splits}
    sets = {key: windows(learners, ids, K, items, context, feature_mode) for key, ids in splits.items()}
    model = model_for(model_name, K, items, hidden, context).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.001)
    binary = SOURCES[source]['binary']; criterion = nn.BCEWithLogitsLoss(reduction='none') if binary else None
    vals = [(v, weight) for p in splits['train'] for r in learners[p] for _, v, weight in r['obs']]
    prior = sum(v*w for v, w in vals) / sum(w for _, w in vals)
    epoch = 0; cursor = 0; best = float('inf'); best_state = None; records = []; stale = 0
    saved = load_resume(output) if resume else None
    if saved:
        if saved['config'] != cfg:
            raise ValueError('Checkpoint config/data mismatch; use a different output folder')
        model.load_state_dict(saved['model']); optimizer.load_state_dict(saved['optimizer'])
        epoch, cursor, best, best_state, records, stale = (saved[k] for k in ('epoch', 'cursor', 'best', 'best_state', 'records', 'stale'))
        torch.set_rng_state(saved['rng'])
        if device.type == 'cuda' and saved.get('cuda_rng'):
            torch.cuda.set_rng_state_all(saved['cuda_rng'])
    def persist():
        save_resume(output, {'config': cfg, 'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
            'epoch': epoch, 'cursor': cursor, 'best': best, 'best_state': best_state, 'records': records,
            'stale': stale, 'rng': torch.get_rng_state(),
            'cuda_rng': torch.cuda.get_rng_state_all() if device.type == 'cuda' else []})
    last_save = time.monotonic()
    print(json.dumps({'device': str(device), 'source': source, 'model': model_name,
                      'learners': {k: len(v) for k, v in splits.items()}, 'resume_epoch': epoch}), flush=True)
    while epoch < epochs and stale < 4:
        order = list(range(len(sets['train']))); random.Random(seed + epoch).shuffle(order)
        model.train()
        for offset in range(cursor, len(order), batch_size):
            values = batch([sets['train'][i] for i in order[offset:offset+batch_size]], device)
            logits = forward(model, model_name, values); y, w = values[4:]
            errors = criterion(logits, y) if binary else (torch.sigmoid(logits)-y)**2
            loss = (errors*w).sum()/w.sum().clamp_min(1)
            if not torch.isfinite(loss):
                raise ValueError('Non-finite training loss')
            optimizer.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step(); cursor = min(offset + batch_size, len(order))
            if (offset//batch_size + 1) % checkpoint_batches == 0 or time.monotonic()-last_save > 120:
                persist(); last_save = time.monotonic()
        metrics = measure(model, model_name, sets['validation'], device, binary, batch_size)
        key = 'log_loss' if binary else 'mae'
        score = metrics[key]
        if score < best:
            best = score; best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}; stale = 0
        else:
            stale += 1
        records.append({'epoch': epoch+1, 'validation': metrics})
        epoch += 1; cursor = 0; persist(); last_save = time.monotonic()
        atomic_json(output/'history.json', records)
        print(json.dumps({'epoch': epoch, 'validation': score, 'best': best}), flush=True)
    if best_state is None:
        raise ValueError('No completed validation epoch')
    model.load_state_dict(best_state)
    validation = measure(model, model_name, sets['validation'], device, binary, batch_size)
    test = measure(model, model_name, sets['test'], device, binary, batch_size)
    base_val = measure(model, model_name, sets['validation'], device, binary, batch_size, prior)
    base_test = measure(model, model_name, sets['test'], device, binary, batch_size, prior)
    key = 'log_loss' if binary else 'mae'
    accepted = validation[key] < base_val[key] and validation['observed_targets'] >= 30 and test['observed_targets'] >= 30
    public_cfg = {**cfg, 'splits': public_split_provenance(splits)}
    try:
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True,
                                          cwd=Path(__file__).resolve().parents[1]).strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'],
                                            text=True, cwd=Path(__file__).resolve().parents[1]).strip())
    except (OSError, subprocess.SubprocessError):
        revision, dirty = None, None
    metadata = {**public_cfg, **SOURCES[source], 'device': str(device), 'epochs_completed': epoch,
        'execution': {'code_revision': revision, 'tracked_worktree_dirty': dirty,
                      'python': platform.python_version(), 'torch': torch.__version__,
                      'numpy': np.__version__},
        'audit': prepared['audit'], 'validation': validation, 'test': test,
        'constant_train_mean_reference': {'mean': prior, 'validation': base_val, 'test': base_test},
        'validation_gate': {'accepted': bool(accepted), 'rule': 'validation improves train-only mean; >=30 validation/test targets',
                            'scope': 'source benchmark only; not validation for DEClic piano practice'},
        'limitations': ['Learner-disjoint benchmark, not a randomized educational experiment.',
            'No generic mastery interpretation or cross-instrument validation.',
            'Windowed recurrent memory; counts retain the strictly earlier full prefix.',
            'Single fixed split/seed; estimates have no confidence interval.']}
    temp = output/'model.tmp'; torch.save({'config': public_cfg, 'state_dict': best_state}, temp); temp.replace(output/'model.pt')
    metadata['model_sha256'] = digest(output/'model.pt')
    atomic_json(output/'metrics.json', metadata)
    with (output/'metrics.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f); writer.writerow(['split', 'metric', 'value'])
        for split, data in [('validation', validation), ('test', test)]:
            writer.writerows((split, k, v) for k, v in data.items() if not isinstance(v, list))
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=SOURCES, required=True)
    parser.add_argument('--archive', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--model', choices=['dkt', 'enhanced_gru', 'item_attention'], default='enhanced_gru')
    parser.add_argument('--epochs', type=int, default=12); parser.add_argument('--batch-size', type=int, default=16)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    if args.epochs < 1 or args.batch_size < 1:
        parser.error('epochs and batch-size must be positive')
    train(args.source, args.archive, args.output, model_name=args.model, epochs=args.epochs,
          batch_size=args.batch_size, seed=args.seed)


if __name__ == '__main__':
    main()
