"""Versioned, item-aware KT adaptations; not exact simpleKT/AKT reproductions.

Only known current exercise identity conditions a query. Labels and item identities
from future attempts never influence an earlier forecast. Item statistics/vocabulary
are fitted exclusively on training learners. Observation-only events are no-ops.
"""
from pathlib import Path
import json
import numpy as np
import torch
from torch import nn
from scipy.special import expit
from scipy.optimize import minimize
from sklearn.linear_model import LogisticRegression
from .eligibility import eligible, compact_history, expand_forecasts
from .models import Baseline, new_neural, neural_predict
from .metrics import calibrate

NEURAL_NAMES = ('dkt', 'sakt', 'enhanced_gru', 'item_attention',
                'enhanced_gru_no_outcome', 'item_attention_no_item')
BASELINE_NAMES = ('prior', 'bkt', 'pfa', 'item_pfa', 'exposure')


def item_key(row):
    """Atomic item bundle, not an invented mapping of question IDs to skills."""
    questions = sorted({str(o['question']) for o in row.get('obs', []) if o.get('question') is not None})
    if questions:
        return '|'.join(questions)
    exercise = str(row.get('exercise') or '')
    return '|'.join(sorted(set(exercise.split(',')))) if ',' in exercise else exercise


class ItemEncoder:
    def __init__(self, state=None):
        self.state = state or {'vocabulary': {}, 'difficulty': {}, 'unknown_difficulty': .5}

    def fit(self, learners):
        totals = {}; positives = 0; count = 0
        for rows in learners.values():
            for row in rows:
                ys = [o['y'] for o in row['obs'] if eligible(o)]
                if not ys:
                    continue
                key = item_key(row)
                if key:
                    value = totals.setdefault(key, [0, 0]); value[0] += sum(ys); value[1] += len(ys)
                positives += sum(ys); count += len(ys)
        self.state = {'vocabulary': {key: i + 1 for i, key in enumerate(sorted(totals))},
                      'difficulty': {key: 1 - (a + 1) / (b + 2) for key, (a, b) in totals.items()},
                      'unknown_difficulty': 1 - (positives + 1) / (count + 2),
                      'fit_unit': 'training learners only; atomic exercise bundle'}
        return self

    @property
    def size(self):
        return len(self.state['vocabulary']) + 1

    def encode(self, row):
        key = item_key(row)
        return (self.state['vocabulary'].get(key, 0),
                self.state['difficulty'].get(key, self.state['unknown_difficulty']))


def encode_sequence(rows, K, items, query=False, exercise_id=None, no_outcome=False, no_item=False):
    """All history/count features at t precede t; query item at t is known, label is not."""
    rs = list(rows) + ([{'obs': [], 'exercise': exercise_id}] if query else [])
    T = len(rs)
    x = np.zeros((T, 4 * K), np.float32); y = np.zeros((T, K), np.float32)
    weights = np.zeros((T, K), np.float32)
    previous_item = np.zeros(T, np.int64); current_item = np.zeros(T, np.int64)
    difficulty = np.zeros((T, 2), np.float32)
    successes = np.zeros(K); failures = np.zeros(K); previous = np.zeros(2 * K)
    prev_id = 0; prev_difficulty = 0.
    for t, row in enumerate(rs):
        x[t, :2*K] = previous
        if no_outcome:
            x[t, 2*K:3*K] = np.log1p(successes + failures)
        else:
            x[t, 2*K:3*K] = np.log1p(successes); x[t, 3*K:] = np.log1p(failures)
        iid, diff = (0, 0.) if no_item else items.encode(row)
        previous_item[t] = prev_id; current_item[t] = iid
        difficulty[t] = (prev_difficulty, diff)
        outcomes = np.zeros(2*K); exposure = np.zeros(K)
        for o in row['obs']:
            if not eligible(o):
                continue
            k, v = o['k'], o['y']; y[t, k] += v; weights[t, k] += 1
            outcomes[k + v*K] += 1; exposure[k] += 1
        y[t] /= np.maximum(weights[t], 1)
        total = max(exposure.sum(), 1)
        if no_outcome:
            previous = np.concatenate([exposure / total, np.zeros(K)])
        else:
            previous = outcomes / total
        for o in row['obs']:
            if eligible(o):
                successes[o['k']] += o['y']; failures[o['k']] += 1-o['y']
        prev_id, prev_difficulty = iid, diff
    return x, previous_item, current_item, difficulty, y, weights


class EnhancedGRU(nn.Module):
    """GRU + outcome counts + train-only item context and known query item."""
    def __init__(self, K, item_count, hidden=48, context=256):
        super().__init__(); self.K = K; self.context = context
        self.item = nn.Embedding(item_count, 12, padding_idx=0)
        self.encoder = nn.GRU(4*K + 13, hidden, batch_first=True)
        self.output = nn.Sequential(nn.Linear(hidden + 12 + 1 + 2*K, hidden), nn.ReLU(), nn.Linear(hidden, K))

    def forward(self, x, previous_item, current_item, difficulty):
        memory = torch.cat([x, self.item(previous_item), difficulty[:, :, :1]], -1)
        hidden, _ = self.encoder(memory)
        return self.output(torch.cat([hidden, self.item(current_item), difficulty[:, :, 1:], x[:, :, 2*self.K:]], -1))


class SimpleKTStyleAttention(nn.Module):
    """Plain causal attention with item-conditioned queries; simplified Rasch-inspired adaptation."""
    def __init__(self, K, item_count, hidden=48, context=256):
        super().__init__(); self.K = K; self.context = context
        self.memory = nn.Linear(4*K, hidden)
        self.item = nn.Embedding(item_count, hidden, padding_idx=0)
        self.difficulty = nn.Linear(1, hidden, bias=False)
        self.position = nn.Embedding(context, hidden); self.skill = nn.Embedding(K, hidden)
        self.attn = nn.MultiheadAttention(hidden, 4, batch_first=True, dropout=.1)
        self.norm = nn.LayerNorm(hidden)
        self.head = nn.Sequential(nn.Linear(2*hidden + 2, hidden), nn.ReLU(), nn.Dropout(.1), nn.Linear(hidden, 1))

    def forward(self, x, previous_item, current_item, difficulty):
        B, T, _ = x.shape
        if T > self.context:
            raise ValueError('Attention window exceeds saved context')
        positions = self.position(torch.arange(T, device=x.device))
        memory = self.memory(x) + self.item(previous_item) + self.difficulty(difficulty[:, :, :1]) + positions
        queries = (self.skill.weight[None,None] + self.item(current_item)[:, :, None] +
                   self.difficulty(difficulty[:, :, 1:])[:, :, None] + positions[None, :, None]).reshape(B, T*self.K, -1)
        # Memory key j carries attempt j-1. Current/future query items are not memory keys.
        mask = torch.arange(T, device=x.device)[None, :] > torch.arange(T, device=x.device).repeat_interleave(self.K)[:,None]
        attended, _ = self.attn(queries, memory, memory, attn_mask=mask, need_weights=False)
        attended = self.norm(attended + queries)
        own_counts = torch.stack([x[:, :, 2*self.K:3*self.K], x[:, :, 3*self.K:]], -1).reshape(B, T*self.K, 2)
        return self.head(torch.cat([attended, queries, own_counts], -1)).reshape(B, T, self.K)


def make_neural(name, K, items, hidden=48, context=256):
    if name in ('dkt', 'sakt'):
        return new_neural(name, K, hidden, context)
    cls = EnhancedGRU if name.startswith('enhanced_gru') else SimpleKTStyleAttention
    return cls(K, items.size, hidden, context)


def neural_logits(model, name, inputs):
    x, previous, current, difficulty = inputs[:4]
    return model(x[:, :, :2*model.K]) if name in ('dkt', 'sakt') else model(x, previous, current, difficulty)


def _noop_mask(positions):
    """True at each original position whose row contributed no eligible observation.

    The trailing next-query slot (index len(positions)-1) is never a no-op: it keeps
    whatever explicit/UNK query the caller asked for.
    """
    n = len(positions) - 1
    mask = np.zeros(len(positions), dtype=bool)
    mask[:n] = positions[1:n + 1] == positions[:n]
    return mask


def _merge_noop_forecasts(known, unk, positions):
    """At no-op/excluded original positions, use the prefix-only UNK forecast instead
    of the next eligible row's known-item forecast that `expand_forecasts` repeats.
    """
    merged = known.copy()
    mask = _noop_mask(positions)
    merged[mask] = unk[mask]
    return merged


def _unk_query_inputs(inputs, unknown_difficulty):
    """Same prefix (x, previous item/difficulty) with a generic unknown current query."""
    x, previous_item, current_item, difficulty = inputs
    current_item = torch.zeros_like(current_item)
    difficulty = difficulty.clone(); difficulty[..., 1] = unknown_difficulty
    return [x, previous_item, current_item, difficulty]


def research_neural_predict(model, name, rows, items, exercise_id=None):
    compact, positions = compact_history(rows)
    no_item = name.endswith('no_item')
    encoded = encode_sequence(compact, model.K, items, True, exercise_id,
                              no_outcome=name.endswith('no_outcome'), no_item=no_item)
    # Observation-only/excluded original rows never had a known item of their own;
    # 0./no_item models already force this, item-aware models get it explicitly.
    unknown_difficulty = 0. if no_item else items.state['unknown_difficulty']
    T = len(encoded[0]); model.eval()
    with torch.no_grad():
        if T <= model.context:
            inp = [torch.from_numpy(v)[None] for v in encoded[:4]]
            p = torch.sigmoid(neural_logits(model, name, inp)).numpy()[0]
            p_unk = torch.sigmoid(neural_logits(model, name, _unk_query_inputs(inp, unknown_difficulty))).numpy()[0]
        else:
            # Every target survives; global causal counts remain available, recurrent memory is bounded.
            parts = []; parts_unk = []
            for end in range(1, T+1):
                start = max(0, end-model.context)
                inp = [torch.from_numpy(v[start:end])[None] for v in encoded[:4]]
                parts.append(torch.sigmoid(neural_logits(model, name, inp)).numpy()[0, -1])
                parts_unk.append(torch.sigmoid(neural_logits(model, name, _unk_query_inputs(inp, unknown_difficulty))).numpy()[0, -1])
            p = np.asarray(parts); p_unk = np.asarray(parts_unk)
    known = expand_forecasts(p, positions, True)
    unk = expand_forecasts(p_unk, positions, True)
    return _merge_noop_forecasts(known, unk, positions)


class StatisticalControl:
    def __init__(self, name, K, items):
        self.name = name; self.K = K; self.items = items

    def features(self, rows, query=True, exercise_id=None, force_unk=False):
        compact, positions = compact_history(rows)
        x, _, ids, diff, _, _ = encode_sequence(compact, self.K, self.items, query, exercise_id,
                                               no_outcome=self.name == 'exposure')
        if force_unk:
            # Observation-only/excluded original rows never had a known item of their
            # own; never let their forecast borrow the next eligible row's real item.
            ids = np.zeros_like(ids)
            diff = diff.copy(); diff[:, 1] = self.items.state['unknown_difficulty']
        result = []
        for t in range(len(x)):
            features = []
            for k in range(self.K):
                skill = np.eye(self.K)[k]
                if self.name == 'exposure':
                    # No direction of any label: recover total count from causal log counts.
                    exposure = x[t, 2*self.K:3*self.K]
                    f = np.r_[skill, exposure, np.log1p(t)]
                else:
                    counts = np.zeros(2*self.K); counts[k] = x[t, 2*self.K+k]; counts[self.K+k] = x[t, 3*self.K+k]
                    f = np.r_[skill, counts, np.eye(self.items.size)[ids[t]], diff[t, 1]]
                features.append(f)
            result.append(features)
        return np.asarray(result), positions

    def fit(self, learners):
        X = []; Y = []
        for rows in learners.values():
            compact, _ = compact_history(rows); features, _ = self.features(compact, query=False)
            for t, row in enumerate(compact):
                for o in row['obs']:
                    X.append(features[t, o['k']]); Y.append(o['y'])
        self.reg = LogisticRegression(C=1.0, max_iter=1500, random_state=0).fit(np.asarray(X), np.asarray(Y))
        return self

    def probabilities(self, rows, exercise_id=None):
        features, positions = self.features(rows, True, exercise_id)
        p = self.reg.predict_proba(features.reshape(-1, features.shape[-1]))[:, 1].reshape(-1, self.K)
        known = expand_forecasts(p, positions, True)
        features_unk, _ = self.features(rows, True, exercise_id, force_unk=True)
        p_unk = self.reg.predict_proba(features_unk.reshape(-1, features_unk.shape[-1]))[:, 1].reshape(-1, self.K)
        unk = expand_forecasts(p_unk, positions, True)
        return _merge_noop_forecasts(known, unk, positions)


class CoherentGroupedBKT(Baseline):
    """Same corrected joint likelihood as core BKT, vectorized across learners for fitting."""
    def __init__(self, K):
        super().__init__('bkt', K)

    def fit(self, learners):
        # Prior is not an optimization surrogate; this call only estimates train priors.
        self.priors = Baseline('prior', self.K).fit(learners).priors
        self.params = []; self.optimization = []
        for k in range(self.K):
            sequences = []
            for rows in learners.values():
                groups = [[o['y'] for o in r['obs'] if eligible(o) and o['k'] == k] for r in rows]
                sequences.append([(sum(g), len(g)-sum(g)) for g in groups if g])
            T = max(map(len, sequences)); a = np.zeros((len(sequences), T)); b = a.copy(); valid = a.copy().astype(bool)
            for i, seq in enumerate(sequences):
                for t, (s, f) in enumerate(seq): a[i, t] = s; b[i, t] = f; valid[i, t] = True
            def loss(v):
                L, learn, guess, slip = v; m = np.full(len(sequences), L); value = 0.
                lk = a*np.log1p(-slip) + b*np.log(slip)
                lu = a*np.log(guess) + b*np.log1p(-guess)
                for t in range(T):
                    known = np.log(np.clip(m, 1e-15, 1-1e-15)) + lk[:, t]
                    unknown = np.log1p(-np.clip(m, 1e-15, 1-1e-15)) + lu[:, t]
                    total = np.logaddexp(known, unknown); mask = valid[:, t]
                    value -= total[mask].sum()
                    posterior = np.exp(known-total); updated = posterior+(1-posterior)*learn
                    m = np.where(mask, updated, m)
                return float(value)
            fits = [minimize(loss, initial, method='L-BFGS-B', bounds=[(.001,.999),(.001,.35),(.01,.49),(.01,.49)])
                    for initial in [(self.priors[k],.08,.2,.15),(.3,.03,.3,.2)]]
            winner = min(fits, key=lambda f:f.fun); self.params.append(winner.x.tolist())
            self.optimization.append({'skill': k, 'success': bool(winner.success), 'message': str(winner.message),
                                      'objective': float(winner.fun), 'starts': len(fits)})
        return self


def save_checkpoint(directory, run_id, model, config, items, temperature=1.):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    target = directory / f'{run_id}.json'
    if target.exists() or (directory / f'{run_id}.pt').exists():
        raise FileExistsError(f'Immutable checkpoint already exists: {run_id}')
    c = dict(config, items=items.state, temperature=float(temperature), implementation_version='axis7-science-v2.1')
    if config['name'] in NEURAL_NAMES:
        torch.save(model.state_dict(), directory / f'{run_id}.pt')
    elif config['name'] in ('item_pfa', 'exposure'):
        c['statistical'] = {'coef': model.reg.coef_.tolist(), 'intercept': model.reg.intercept_.tolist()}
    else:
        c['baseline'] = {'priors': model.priors.tolist()}
        if model.name == 'bkt':
            c['baseline']['params'] = model.params; c['bkt_objective'] = 'shared_latent_group_joint_log_likelihood'
            c['optimization'] = getattr(model, 'optimization', [])
        if model.name == 'pfa':
            c['baseline'].update(coef=model.reg.coef_.tolist(), intercept=model.reg.intercept_.tolist())
    target.write_text(json.dumps(c, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def restore_regression(state):
    reg = LogisticRegression(); reg.coef_ = np.asarray(state['coef']); reg.intercept_ = np.asarray(state['intercept'])
    reg.classes_ = np.array([0, 1]); reg.n_features_in_ = reg.coef_.shape[1]
    return reg


class ResearchPredictor:
    # Serving-side forecast correction (no-op/excluded rows use a generic UNK query
    # instead of borrowing the next eligible row's item); the immutable checkpoint's
    # training-time `config['implementation_version']` ('axis7-science-v2.1') is unchanged.
    serving_implementation_version = 'axis7-science-v2.2'

    def __init__(self, directory, run_id):
        self.directory = Path(directory); self.run_id = run_id
        self.config = json.loads((self.directory / f'{run_id}.json').read_text(encoding='utf-8'))
        c = self.config; self.K = c['K']; self.name = c['name']; self.items = ItemEncoder(c['items'])
        if self.name in NEURAL_NAMES:
            self.model = make_neural(self.name, self.K, self.items, c['hidden'], c['context'])
            self.model.load_state_dict(torch.load(self.directory / f'{run_id}.pt', map_location='cpu', weights_only=True)); self.model.eval()
        elif self.name in ('item_pfa', 'exposure'):
            self.model = StatisticalControl(self.name, self.K, self.items); self.model.reg = restore_regression(c['statistical'])
        else:
            self.model = Baseline(self.name, self.K); b = c['baseline']; self.model.priors = np.asarray(b['priors'])
            if self.name == 'bkt': self.model.params = b['params']
            if self.name == 'pfa': self.model.reg = restore_regression(b)

    def probabilities(self, rows, exercise_id=None, calibrated=False):
        if self.name in NEURAL_NAMES:
            p = research_neural_predict(self.model, self.name, rows, self.items, exercise_id)
        elif self.name in ('item_pfa', 'exposure'):
            p = self.model.probabilities(rows, exercise_id)
        else:
            compact, positions = compact_history(rows)
            p = expand_forecasts(self.model.predict(compact, append_query=True), positions, True)
        return calibrate(p, self.config['temperature']) if calibrated else p
