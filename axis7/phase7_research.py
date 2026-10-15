"""Exploratory past-only representation experiments, never a serving registry.

Uses the Phase 6 atomic labels and learner splits unchanged. No raw learner IDs
or optimizer states belong in public exports. Classical controls stay research-only.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import random
import time
from datetime import datetime

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
import torch
from torch import nn
from threadpoolctl import threadpool_limits

from . import cloud_training as c
from .models_v2 import EnhancedGRU, SimpleKTStyleAttention
from .scientific_validation import metrics, train_priors, historical_predictions

CONDITIONS = ('gru', 'unordered', 'recent3', 'attention', 'no_concept_embedding', 'past_gaps')
LOADED_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_text(encoding='utf-8').replace('\r\n','\n').encode()).hexdigest()


class RepresentationModel(nn.Module):
    def __init__(self, condition, K, item_count, hidden=48, context=64):
        super().__init__()
        if condition not in CONDITIONS:
            raise ValueError('Unknown predefined representation')
        self.condition = condition; self.K = K; self.context = context
        if condition in ('attention', 'no_concept_embedding'):
            self.base = SimpleKTStyleAttention(K, item_count, hidden, context)
            if condition == 'no_concept_embedding':
                nn.init.zeros_(self.base.skill.weight)
                self.base.skill.weight.requires_grad_(False)
        elif condition == 'unordered':
            self.item = nn.Embedding(item_count, 12, padding_idx=0)
            self.head = nn.Sequential(nn.Linear(2*K+12, hidden), nn.ReLU(), nn.Linear(hidden, K))
        else:
            self.base = EnhancedGRU(K, item_count, hidden, context)

    def forward(self, x, previous, current, difficulty):
        if self.condition == 'unordered':
            # Only current cumulative sufficient statistics: invariant to past order.
            return self.head(torch.cat((x[..., 2*self.K:], self.item(current)), -1))
        if self.condition == 'recent3':
            # At slot t, x[t] contains outcome t-1, never outcome t. Reset for
            # each target to exactly three previous groups; omit full-history counts.
            B, T, D = x.shape
            z = x.clone(); z[..., 2*self.K:] = 0
            z = nn.functional.pad(z, (0, 0, 2, 0)).unfold(1, 3, 1).permute(0, 1, 3, 2)
            pi = nn.functional.pad(previous, (2, 0)).unfold(1, 3, 1)
            ci = nn.functional.pad(current, (2, 0)).unfold(1, 3, 1)
            diff = torch.zeros((B*T, 3, 2), device=x.device)
            return self.base(z.reshape(B*T, 3, D), pi.reshape(B*T, 3),
                             ci.reshape(B*T, 3), diff)[:, -1].reshape(B, T, self.K)
        return self.base(x, previous, current, difficulty)


def gap_encode(rows, K, items, condition):
    result = c.encode(rows, K, items)
    if condition == 'past_gaps':
        times = [(c.parse_singpad_time(r['time'])-datetime(2000, 1, 1)).total_seconds() / 86400
                 if isinstance(r['time'], str) else float(r['time']) for r in rows]
        # Only intervals already observed at t; do not use planned/future t date.
        for t in range(2, len(rows)):
            result[3][t, 0] = math.log1p(max(times[t-1]-times[t-2], 0))
    return result


def make_samples(learners, ids, K, items, condition, context=64):
    samples = []
    for learner in ids:
        rows = learners[learner]; values = gap_encode(rows, K, items, condition)
        for start in range(0, len(rows), context-1):
            stop = min(start+context-1, len(rows)); left = max(start-1, 0)
            # recent3 gets sufficient warmup at chunk boundaries. Other variants
            # keep the exact Phase 6 one-group warmup convention.
            if condition == 'recent3': left = max(start-3, 0)
            sample = tuple(a[left:stop].copy() for a in values)
            sample[-1][:start-left] = 0
            if sample[-1].sum(): samples.append(sample)
    return samples


def target_logits(model, inputs):
    """Exact selected-query evaluation, same independent attention queries.

    The mask selects outputs to score, never supplies outcome values to the model.
    No interactions exist between queries in SimpleKTStyleAttention. Evaluation
    equivalence to the dense implementation is regression-tested.
    """
    if model.condition not in ('attention','no_concept_embedding'):
        return model(*inputs[:4])
    x, previous, current, difficulty, _, weights = inputs
    base = model.base; B,T,_ = x.shape; H = base.skill.embedding_dim
    positions = base.position(torch.arange(T,device=x.device))
    memory = base.memory(x)+base.item(previous)+base.difficulty(difficulty[:,:,:1])+positions
    indices = [torch.nonzero(weights[b]>0,as_tuple=False) for b in range(B)]
    N = max(1,max(len(i) for i in indices))
    ts = torch.zeros((B,N),dtype=torch.long,device=x.device); ks = torch.zeros_like(ts)
    for b, values in enumerate(indices):
        if len(values): ts[b,:len(values)]=values[:,0]; ks[b,:len(values)]=values[:,1]
    bi = torch.arange(B,device=x.device)[:,None]
    queries = base.skill(ks)+base.item(current[bi,ts])+base.difficulty(difficulty[bi,ts,1:])+base.position(ts)
    mask = (torch.arange(T,device=x.device)[None,None,:]>ts[:,:,None]).repeat_interleave(base.attn.num_heads,dim=0)
    attended,_ = base.attn(queries,memory,memory,attn_mask=mask,need_weights=False)
    attended = base.norm(attended+queries)
    own_counts = torch.stack((x[bi,ts,2*model.K+ks],x[bi,ts,3*model.K+ks]),-1)
    selected = base.head(torch.cat((attended,queries,own_counts),-1)).squeeze(-1)
    result = torch.zeros_like(weights)
    for b,values in enumerate(indices):
        if len(values): result[b,values[:,0],values[:,1]]=selected[b,:len(values)]
    return result


def predictions(model, samples, device='cpu'):
    ys = []; ps = []; ws = []
    model.eval()
    with torch.inference_mode():
        for i in range(0, len(samples), 16):
            inputs = c.batch(samples[i:i+16], device)
            p = torch.sigmoid(target_logits(model,inputs)).cpu().numpy()
            y, w = (a.cpu().numpy() for a in inputs[4:]); mask = w > 0
            ys.extend(y[mask]); ps.extend(p[mask]); ws.extend(w[mask])
    return tuple(np.asarray(a) for a in (ys, ps, ws))


def calibration(y, p, w, temperature=1.):
    p = expit(logit(np.clip(p, 1e-7, 1-1e-7))/temperature)
    result = metrics(y, p, w, True)
    bins = result['calibration']; total = float(w.sum()); mean = float(np.average(y, weights=w))
    reliability = sum(b['label_weight']*(b['prediction']-b['observed'])**2 for b in bins)/total
    resolution = sum(b['label_weight']*(b['observed']-mean)**2 for b in bins)/total
    uncertainty = mean*(1-mean)
    result.update(ece=sum(b['label_weight']*abs(b['prediction']-b['observed']) for b in bins)/total,
                  brier_binned_decomposition={'reliability': reliability, 'resolution': resolution,
                  'uncertainty': uncertainty, 'within_bin_residual': result['brier']-(reliability-resolution+uncertainty)},
                  binning='10 equal-width bins [i/10,(i+1)/10), final upper bound inclusive',
                  temperature=temperature)
    return result


def fit_temperature(y, p, w):
    z = logit(np.clip(p, 1e-7, 1-1e-7))
    def objective(log_temperature):
        v = z/math.exp(log_temperature)
        return float(np.average(np.logaddexp(0, v)-y*v, weights=w))
    fit = minimize_scalar(objective, bounds=(-2.3, 2.3), method='bounded')
    if not fit.success: raise ValueError('Calibration optimization failed')
    return float(math.exp(fit.x))


def train_representation(prepared, seed, condition, folder, epochs=8):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    learners = prepared['learners']; split = c.split_learners(learners, seed)
    K = max(int(o[0]) for rows in learners.values() for r in rows for o in r['obs'])+1
    items = c.fit_items(learners, split['train'])
    config = {'protocol': 'phase7-exploratory-v1', 'condition': condition, 'seed': seed,
              'dataset_sha256': prepared['sha256'], 'splits': c.public_split_provenance(split),
              'epochs': epochs, 'K': K, 'hidden': 48, 'context': 64,
              'source_sha256': LOADED_SOURCE_SHA256, 'core_sha256': c.SOURCE_HASHES,
              'device': 'cpu', 'torch': torch.__version__, 'numpy': np.__version__}
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.set_num_threads(2)
    model = RepresentationModel(condition, K, len(items)+1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.001)
    sets = {s: make_samples(learners, ids, K, items, condition) for s, ids in split.items()}
    binary = prepared['source'] == 'singpad'; key = 'log_loss' if binary else 'mae'
    best = None; best_loss = float('inf'); stale = 0; history = []; epoch = 0; cursor = 0; order = None
    if (folder/'resume.json').exists():
        state = c.load_resume(folder)
        if state['config'] != config: raise ValueError('Incompatible Phase 7 resume')
        model.load_state_dict(state['model']); optimizer.load_state_dict(state['optimizer'])
        best = state['best']; best_loss = state['best_loss']; stale = state['stale']
        history = state['history']; epoch = state['epoch']; cursor = state['cursor']; order = state['order']
        torch.set_rng_state(state['torch_rng']); random.setstate(state['python_rng'])
    def save():
        c.save_resume(folder, {'config': config, 'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
             'best': best, 'best_loss': best_loss, 'stale': stale, 'history': history,
             'epoch': epoch, 'cursor': cursor, 'order': order,
             'torch_rng': torch.get_rng_state(), 'python_rng': random.getstate()})
    last_save = time.monotonic()
    while epoch < epochs and stale < 3:
        if order is None:
            order = list(range(len(sets['train']))); random.shuffle(order)
        model.train()
        while cursor < len(order):
            inputs = c.batch([sets['train'][i] for i in order[cursor:cursor+16]], 'cpu')
            logits = target_logits(model,inputs); y, w = inputs[4:]
            loss_values = nn.functional.binary_cross_entropy_with_logits(logits, y, reduction='none') if binary else (torch.sigmoid(logits)-y)**2
            loss = (loss_values*w).sum()/w.sum()
            if not torch.isfinite(loss): raise ValueError('Nonfinite training loss')
            optimizer.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step(); cursor += 16
            if cursor % 400 == 0 or time.monotonic()-last_save > 120:
                save(); last_save = time.monotonic()
        y, p, w = predictions(model, sets['validation'])
        validation = metrics(y, p, w, binary); value = validation[key]
        if value < best_loss-1e-7:
            best_loss = value; best = copy.deepcopy(model.state_dict()); stale = 0
        else: stale += 1
        epoch += 1; cursor = 0; order = None
        history.append({'epoch': epoch, 'validation': validation})
        save()
        print(f"{prepared['source']} seed={seed} {condition} epoch={epoch} validation_{key}={value:.6f}", flush=True)
    model.load_state_dict(best)
    validation = predictions(model, sets['validation']); test = predictions(model, sets['test'])
    report = {'config': config, 'source': prepared['source'], 'epochs_completed': epoch,
              'trainable_parameters': sum(p.numel() for p in model.parameters() if p.requires_grad),
              'validation': metrics(*[validation[i] for i in (0,1,2)], binary),
              'test': metrics(*[test[i] for i in (0,1,2)], binary), 'selection': 'minimum validation loss; test never used',
              'status': 'exploratory_research_only', 'individual_uncertainty': 'not validated'}
    if binary:
        temperature = fit_temperature(*validation)
        report['calibration'] = {'fit': 'validation only', 'temperature': temperature,
            'test_raw': calibration(*test), 'test_scaled': calibration(*test, temperature=temperature)}
    torch.save(best, folder/'model.pt')
    report['model_sha256'] = c.digest(folder/'model.pt')
    c.atomic_json(folder/'history.json', history); c.atomic_json(folder/'metrics.json', report)
    return report, model, split, K, items


def tabular(learners, ids, K, prior):
    """Known concept + past sufficient counts, previous/rolling scores and gaps.

    No learner identifier, future timestamp, target score, or future difficulty in X.
    """
    features = []; outcomes = []; weights = []
    for learner in ids:
        rows = learners[learner]; successes = np.zeros(K); totals = np.zeros(K)
        histories = [[] for _ in range(K)]
        for t, r in enumerate(rows):
            values = {}
            for k, y, w in r['obs']:
                a, n = values.get(k, (0., 0.)); values[k] = (a+y*w, n+w)
            if t:
                gap = 0.
                if t >= 2:
                    a, b = rows[t-1]['time'], rows[t-2]['time']
                    gap = (c.parse_singpad_time(a)-c.parse_singpad_time(b)).total_seconds()/86400 if isinstance(a, str) else float(a)-float(b)
                for k, (a, n) in sorted(values.items()):
                    h = histories[k]
                    features.append([k/max(K-1,1), prior[k], math.log1p(successes[k]),
                        math.log1p(totals[k]-successes[k]), (successes[k]+2*prior[k])/(totals[k]+2),
                        h[-1] if h else prior[k], np.mean(h[-3:]) if h else prior[k],
                        math.log1p(t), math.log1p(max(gap, 0))])
                    outcomes.append(a/n); weights.append(n)
            for k, (a, n) in values.items():
                successes[k] += a; totals[k] += n; histories[k].append(a/n)
    return np.asarray(features), np.asarray(outcomes), np.asarray(weights)


def learned_controls(prepared, seed):
    learners = prepared['learners']; split = c.split_learners(learners, seed)
    K = max(int(o[0]) for rows in learners.values() for r in rows for o in r['obs'])+1
    _, prior, _ = train_priors(learners, split['train'], K)
    arrays = {s: tabular(learners, ids, K, prior) for s, ids in split.items()}
    scaler = StandardScaler().fit(arrays['train'][0]); binary = prepared['source'] == 'singpad'
    fitted = {}; validation = {}; key = 'log_loss' if binary else 'mae'
    with threadpool_limits(limits=2):
        for regularization in (.01, 1., 100.):
            x, y, w = arrays['train']; x = scaler.transform(x)
            if binary:
                # Exact successes/failures weighted likelihood; no binarized fractions.
                fit_x = np.concatenate((x, x)); fit_y = np.r_[np.ones(len(y)), np.zeros(len(y))]
                fit_w = np.r_[w*y, w*(1-y)]; keep = fit_w > 0
                model = LogisticRegression(C=regularization, max_iter=500, solver='lbfgs').fit(fit_x[keep], fit_y[keep], sample_weight=fit_w[keep])
            else: model = Ridge(alpha=regularization).fit(x, y, sample_weight=w)
            fitted[str(regularization)] = model
            x, y, w = arrays['validation']
            p = model.predict_proba(scaler.transform(x))[:,1] if binary else np.clip(model.predict(scaler.transform(x)), 0, 1)
            validation[str(regularization)] = metrics(y, p, w, binary)
        selected = min(validation, key=lambda v: validation[v][key]); model = fitted[selected]
        x, y, w = arrays['test']
        p = model.predict_proba(scaler.transform(x))[:,1] if binary else np.clip(model.predict(scaler.transform(x)), 0, 1)
    return {'kind': 'regularized_logistic' if binary else 'ridge', 'seed': seed,
            'selection': 'validation_'+key, 'selected_regularization': selected,
            'validation_candidates': validation, 'test': metrics(y, p, w, binary),
            'features': ['concept_ordinal', 'train_concept_prior', 'past_log_successes', 'past_log_failures',
             'smoothed_past_fraction', 'previous_score', 'rolling3', 'past_groups', 'past_gap'],
            'limitation': 'Ordinal concept ID is a simple control, not a validated musical geometry.',
            'scope': 'research only; not deployed', 'splits': c.public_split_provenance(split)}


def stress_test(model, prepared, split, K, items):
    """Construct each target from a modified strictly earlier prefix; labels untouched."""
    rng = np.random.default_rng(701); results = {}
    for condition in ('intact', 'random_missing_30pct', 'missing_latest2', 'no_target_concept_history'):
        samples = []; target_labels = []; target_weights = []; total_targets = 0
        for learner in split['test']:
            rows = prepared['learners'][learner]
            for t in range(1, len(rows)):
                target = rows[t]; prefix = rows[:t]
                if condition == 'random_missing_30pct': prefix = [r for r in prefix if rng.random() >= .3]
                elif condition == 'missing_latest2': prefix = prefix[:-2]
                elif condition == 'no_target_concept_history':
                    concepts = {o[0] for o in target['obs']}
                    prefix = [{**r, 'obs': [o for o in r['obs'] if o[0] not in concepts]} for r in prefix]
                # No target outcome is encoded as an input, even though it is retained for scoring.
                values = gap_encode(prefix+[{'time': target['time'], 'exercise': target['exercise'], 'obs': []}], K, items, model.condition)
                sample = tuple(a[-64:].copy() for a in values)
                sample[-1][:] = 0
                sample[-2][:] = 0
                for k, y, w in target['obs']:
                    sample[-2][-1,k] += y*w; sample[-1][-1,k] += w
                sample[-2][-1] /= np.maximum(sample[-1][-1], 1)
                samples.append(sample); total_targets += 1
        y, p, w = predictions(model, samples)
        results[condition] = {'metrics': metrics(y, p, w, prepared['source']=='singpad'),
                              'atomic_targets': total_targets,
                              'input_policy': 'modified earlier history only; unchanged target labels'}
    return {'seed': 701, 'scope': 'frozen model input stress test, not retraining',
            'conditions': results, 'limitation': 'Artificial missingness does not identify real missing-data mechanisms; intact uses full prefix last64, distinct from chunked training evaluation.'}
