"""Matched historical controls and learner-cluster uncertainty; no raw IDs exported."""
from collections import defaultdict
import math

import numpy as np
import torch
from sklearn.metrics import roc_auc_score, average_precision_score

from .cloud_training import encode, forward, batch, apply_feature_mode

CONTROLS = ('train_mean', 'previous', 'rolling3', 'ewma', 'frequency')


def train_priors(learners, ids, K):
    success = np.zeros(K); count = np.zeros(K)
    for learner in ids:
        for row in learners[learner]:
            for k, value, weight in row['obs']:
                success[k] += value*weight; count[k] += weight
    mean = float(success.sum()/count.sum())
    prior = (success+2*mean)/(count+2)
    return mean, prior, count


def historical_predictions(rows, K, mean, prior):
    """Each concept updated only after the whole timestamp group is predicted."""
    outputs = {name: np.zeros((len(rows), K)) for name in CONTROLS}
    success = np.zeros(K); count = np.zeros(K)
    history = [[] for _ in range(K)]; ewma = prior.copy()
    for t, row in enumerate(rows):
        outputs['train_mean'][t] = mean
        outputs['previous'][t] = [h[-1] if h else prior[k] for k, h in enumerate(history)]
        outputs['rolling3'][t] = [np.mean(h[-3:]) if h else prior[k] for k, h in enumerate(history)]
        outputs['ewma'][t] = ewma
        outputs['frequency'][t] = (success+2*prior)/(count+2)
        positives = np.zeros(K); totals = np.zeros(K)
        for k, value, weight in row['obs']:
            positives[k] += value*weight; totals[k] += weight
        for k in np.flatnonzero(totals):
            score = positives[k]/totals[k]
            history[k].append(score)
            ewma[k] = score if len(history[k]) == 1 else .5*score+.5*ewma[k]
        success += positives; count += totals
    return outputs


def metrics(y, p, weight, binary):
    y = np.asarray(y, dtype=float); p = np.clip(np.asarray(p, dtype=float), 1e-7, 1-1e-7)
    weight = np.asarray(weight, dtype=float)
    if not len(y) or weight.sum() <= 0 or not np.isfinite(p).all():
        raise ValueError('No finite weighted observations')
    avg = lambda a: float(np.average(a, weights=weight))
    result = {'concept_group_targets': len(y), 'label_weight': float(weight.sum()),
              'mae': avg(abs(y-p)), 'rmse': math.sqrt(avg((y-p)**2))}
    if binary:
        result.update(log_loss=avg(-y*np.log(p)-(1-y)*np.log1p(-p)),
                      brier=avg(y*(1-p)**2+(1-y)*p**2),
                      mae_note=avg(y*(1-p)+(1-y)*p))
        counts = np.concatenate((weight*y, weight*(1-y)))
        labels = np.concatenate((np.ones(len(y)), np.zeros(len(y))))
        scores = np.tile(p, 2); present = counts > 0
        result['roc_auc'] = float(roc_auc_score(labels[present], scores[present], sample_weight=counts[present])) if counts[:len(y)].sum() and counts[len(y):].sum() else None
        result['pr_auc'] = float(average_precision_score(labels[present], scores[present], sample_weight=counts[present])) if counts[:len(y)].sum() else None
        bins = []
        assignment = np.minimum((p*10).astype(int), 9)
        for index in range(10):
            mask = assignment == index
            if mask.any():
                bins.append({'lower': index/10, 'label_weight': float(weight[mask].sum()),
                             'prediction': float(np.average(p[mask], weights=weight[mask])),
                             'observed': float(np.average(y[mask], weights=weight[mask]))})
        result['calibration'] = bins
    return result


def collect(model, model_name, learners, ids, K, items, context, mean, prior,
            *, feature_mode='full', batch_size=16):
    """Exact training-window inference and aligned metadata for every target."""
    samples = []; tags = []; controls = {name: [] for name in CONTROLS}
    model.eval(); device = next(model.parameters()).device
    for cluster, learner in enumerate(ids):
        rows = learners[learner]; values = apply_feature_mode(encode(rows, K, items), K, feature_mode)
        predictions = historical_predictions(rows, K, mean, prior)
        for start in range(0, len(rows), context-1):
            stop = min(start+context-1, len(rows)); left = max(start-1, 0)
            sample = tuple(a[left:stop].copy() for a in values)
            if start: sample[-1][0] = 0
            if not sample[-1].sum(): continue
            samples.append(sample)
            row_indices, concepts = np.nonzero(sample[-1] > 0)
            global_indices = row_indices+left
            tags.extend((cluster, int(t), int(k), rows[t]['exercise'] not in items,
                         sum(sum(o[2] for o in r['obs']) for r in rows[:t]))
                        for t, k in zip(global_indices, concepts))
            for name in CONTROLS:
                controls[name].extend(predictions[name][global_indices, concepts].tolist())
    y = []; weights = []; probabilities = []
    with torch.inference_mode():
        for start in range(0, len(samples), batch_size):
            tensors = batch(samples[start:start+batch_size], device)
            p = torch.sigmoid(forward(model, model_name, tensors)).cpu().numpy()
            outcomes, weight = (v.cpu().numpy() for v in tensors[4:])
            mask = weight > 0
            y.extend(outcomes[mask]); weights.extend(weight[mask]); probabilities.extend(p[mask])
    # tags/controls order follows the same sample-major and time/concept-major mask.
    data = {'y': np.asarray(y), 'w': np.asarray(weights), 'neural': np.asarray(probabilities),
            'tags': np.asarray(tags), **{k: np.asarray(v) for k, v in controls.items()}}
    assert all(len(data[k]) == len(y) for k in ('tags', 'neural', *CONTROLS))
    return data


def learner_bootstrap(data, names, binary, repeats=1000, seed=20261015):
    """Percentile intervals and paired differences; resample whole learners."""
    key = 'log_loss' if binary else 'mae'
    clusters = data['tags'][:, 0].astype(int); unique = np.unique(clusters)
    totals = np.bincount(clusters, weights=data['w'], minlength=unique.max()+1)[unique]
    sums = {}
    for name in names:
        p = np.clip(data[name], 1e-7, 1-1e-7); y = data['y']
        loss = -y*np.log(p)-(1-y)*np.log1p(-p) if binary else abs(y-p)
        sums[name] = np.bincount(clusters, weights=loss*data['w'], minlength=unique.max()+1)[unique]
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(unique), size=(repeats, len(unique)))
    denominator = totals[indices].sum(axis=1)
    distributions = {name: sums[name][indices].sum(axis=1)/denominator for name in names}
    interval = lambda values: [float(v) for v in np.quantile(values, [.025, .975])]
    return {'unit': 'whole held-out learner; note/day-weighted statistic', 'metric': key,
            'repeats': repeats, 'seed': seed, 'learners': len(unique),
            'intervals_95_percent': {name: interval(values) for name, values in distributions.items()},
            'paired_neural_minus_control': {name: interval(distributions['neural']-values)
                                            for name, values in distributions.items() if name != 'neural'},
            'limitation': 'Conditional on fitted weights and split; not a confidence interval for an individual prediction.'}


def analyze(data, binary, train_counts, selected_control):
    y = data['y']; w = data['w']; tags = data['tags']
    results = {name: metrics(y, data[name], w, binary) for name in ('neural', *CONTROLS)}
    slices = {}
    masks = {
        'history_1_2_groups': tags[:, 1] <= 2,
        'history_3_9_groups': (tags[:, 1] >= 3) & (tags[:, 1] <= 9),
        'history_10_plus_groups': tags[:, 1] >= 10,
        'unseen_exercise': tags[:, 3] == 1,
        'low_observed_score_under_0_5': y < .5,
        'high_observed_score_at_least_0_8': y >= .8,
    }
    if binary:
        threshold = float(np.median(train_counts[train_counts > 0]))
        masks['rare_train_concepts'] = train_counts[tags[:, 2].astype(int)] < threshold
        masks['frequent_train_concepts'] = ~masks['rare_train_concepts']
    for name, mask in masks.items():
        if mask.any():
            slices[name] = {'neural': metrics(y[mask], data['neural'][mask], w[mask], binary),
                            'control': metrics(y[mask], data[selected_control][mask], w[mask], binary),
                            'learners': len(np.unique(tags[mask, 0]))}
    per_concept = {}
    if binary:
        for k in np.unique(tags[:, 2]).astype(int):
            mask = tags[:, 2] == k
            n = len(np.unique(tags[mask, 0]))
            if n >= 10 and w[mask].sum() >= 100:
                per_concept[str(k)] = {'learners': n, **metrics(y[mask], data['neural'][mask], w[mask], True)}
    errors = abs(y-data['neural'])
    return {'metrics': results, 'validation_selected_control': selected_control,
            'bootstrap': learner_bootstrap(data, ('neural', *CONTROLS), binary),
            'slices': slices, 'per_concept_min_10_learners_100_notes': per_concept,
            'group_fraction_absolute_error_quantiles': {str(q): float(np.quantile(errors, q)) for q in (.5, .9, .95)},
            'weighting': 'note-count weighted binary loss/AUC/Brier; aggregated-fraction MAE separately' if binary else 'one equal-weight target per active day/block',
            'limitations': ['history length is not a validated expertise measure',
                           'subgroup comparisons are descriptive, not causal',
                           'unseen exercise slice uses UNK in offline evaluation; serving abstains']}
