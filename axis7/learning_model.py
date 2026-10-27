"""O08 reference model for the DÉCLIC learner loop: transparent, per learner, pre-registered.

Why not the trained O08 networks? They take SingPAD note outcomes on 270 opaque singing
concepts or one Yousician ukulele score per day, and their serving contract refuses any other
instrument. DÉCLIC's instrument-free exercises have their own skill vocabulary, so feeding them
to those networks would be a relabelling, not a prediction. Until a network is trained on
DÉCLIC-native attempts from many learners, the learner loop uses this documented model:

    P(success) = c + (1 - c) * sigmoid(theta_skill - d_level)        (Pelánek 2016, Elo)
    theta     <- theta + U(n) * (outcome - P),  U(n) = A / (1 + B * n)

c is the chance level of the item (1/number of choices; 0 for keyboard/tapping), d_level is
fixed a priori from the level index (not estimated: one learner cannot identify item
difficulty), theta starts at 0. Every prediction is computed from answers given BEFORE the
item was created and stored with the item, so it can be scored honestly afterwards.
A naive comparator (Laplace success rate at the same exercise and level) is stored beside it.
"""
from __future__ import annotations

import math

from .learning_catalog import level_spec

MODEL_ID = 'declic-elo-v1'
A, B = 1.0, 0.05
MIN_SKILL_HISTORY = 5
CALIBRATION_MIN = 30
WINDOW = 10


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def difficulty(exercise_id, level, cents=None):
    if exercise_id == 'hauteur-seuil' and cents:
        equivalent = 1 + math.log2(200 / max(cents, 1e-6))
        return -1.0 + 0.7 * (equivalent - 1)
    return -1.0 + 0.7 * (level - 1)


def item_chance(exercise_id, level):
    _, lv = level_spec(exercise_id, level)
    return 1 / lv['choices'] if lv.get('choices') else 0.0


def replay(history):
    """history: answered items in chronological order, dicts with skill, exercise, level, cents, correct.
    Returns per-skill state {'theta','n'}."""
    state = {}
    for h in history:
        s = state.setdefault(h['skill'], {'theta': 0.0, 'n': 0})
        c = item_chance(h['exercise'], h['level'])
        p = c + (1 - c) * sigmoid(s['theta'] - difficulty(h['exercise'], h['level'], h.get('cents')))
        s['theta'] += A / (1 + B * s['n']) * ((1.0 if h['correct'] else 0.0) - p)
        s['n'] += 1
    return state


def baseline(history, exercise_id, level):
    same = [h for h in history if h['exercise'] == exercise_id and h['level'] == level]
    return (sum(h['correct'] for h in same) + 1) / (len(same) + 2), len(same)


def predict(history, skill, exercise_id, level, cents=None):
    """Prediction for the next item, using only `history` (answers already given)."""
    state = replay(history)
    s = state.get(skill, {'theta': 0.0, 'n': 0})
    base, base_n = baseline(history, exercise_id, level)
    c = item_chance(exercise_id, level)
    common = {'model': MODEL_ID, 'skill': skill, 'n_skill': s['n'], 'needed': MIN_SKILL_HISTORY,
              'baseline': round(base, 4), 'baseline_n': base_n, 'chance': round(c, 4)}
    if s['n'] < MIN_SKILL_HISTORY:
        return {'status': 'abstained', 'reason': 'insufficient_data', **common}
    d = difficulty(exercise_id, level, cents)
    p = c + (1 - c) * sigmoid(s['theta'] - d)
    return {'status': 'ok', 'p': round(p, 4), 'theta': round(s['theta'], 4), 'd': round(d, 4), **common}


def _brier(pairs):
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def _logloss(pairs):
    eps = 1e-6
    return -sum(y * math.log(max(p, eps)) + (1 - y) * math.log(max(1 - p, eps)) for p, y in pairs) / len(pairs)


def quality(scored):
    """scored: chronological list of {'p','baseline','y'} for items with a model prediction."""
    n = len(scored)
    out = {'model': MODEL_ID, 'scored': n, 'window': WINDOW, 'calibration_min': CALIBRATION_MIN}
    if n == 0:
        out['status'] = 'no_scored_predictions'
        return out
    model = [(s['p'], s['y']) for s in scored]
    base = [(s['baseline'], s['y']) for s in scored]
    out.update(status='ok', brier_model=round(_brier(model), 4), brier_baseline=round(_brier(base), 4),
               logloss_model=round(_logloss(model), 4), logloss_baseline=round(_logloss(base), 4),
               observed_rate=round(sum(s['y'] for s in scored) / n, 4), mean_predicted=round(sum(s['p'] for s in scored) / n, 4))
    out['skill_vs_baseline'] = round(1 - out['brier_model'] / out['brier_baseline'], 4) if out['brier_baseline'] > 0 else None
    out['rolling'] = [{'from': i + 1, 'to': min(i + WINDOW, n),
                       'brier_model': round(_brier(model[i:i + WINDOW]), 4),
                       'brier_baseline': round(_brier(base[i:i + WINDOW]), 4)}
                      for i in range(0, n, WINDOW) if len(model[i:i + WINDOW]) == WINDOW]
    if n >= CALIBRATION_MIN:
        bins = []
        for lo in (0.0, 0.2, 0.4, 0.6, 0.8):
            members = [s for s in scored if lo <= s['p'] < lo + 0.2 or (lo == 0.8 and s['p'] == 1.0)]
            if members:
                bins.append({'from': lo, 'to': round(lo + 0.2, 1), 'count': len(members),
                             'mean_predicted': round(sum(s['p'] for s in members) / len(members), 4),
                             'observed': round(sum(s['y'] for s in members) / len(members), 4)})
        out['calibration'] = bins
    else:
        out['calibration'] = None
    return out
