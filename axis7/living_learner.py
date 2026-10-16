"""Phase 8 read-only presentation adapter: retrospective causal replay of held-out learners.

Inference goes exclusively through musical_api.musical_forecast (the served EnhancedGRU).
For a cutoff c, every payload uses steps strictly before c. Step c only contributes its
recorded query definition (exercise id and evaluated concept ids), as in BenchmarkQuery:
forecasts are therefore conditional on the recorded exercise and evaluated concepts.
The total number of steps is navigation metadata of a retrospective replay, never an input.
"""
import base64
import copy
from datetime import datetime
import gzip
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import threading
import time
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
import torch

from . import o08_demo
from .cloud_training import SOURCES, VERSION, PREPROCESSING, apply_feature_mode, encode, forward, public_split_provenance, split_learners
from .data import ROOT
from .musical_api import BenchmarkQuery, forecast_with_model
from .musical_registry import REGISTRY_ROOT, cached_validate
from .serving_identity import MAX_HISTORY, CONTRACT, canonical_digest, freeze, generation, request_identity
from .skill_states import catalogue_from_history, recommend, skill_states
from .model_eligibility import describe as eligibility

router = APIRouter(prefix='/api/v7/o08/living')
DATA_DIR = Path(os.environ.get('DECLIC_PREPARED_DATA', ROOT/'runtime/musical-demo'))
MAX_LEARNERS = 8
MIN_STEPS = 6
SELECTION = (f'Les {MAX_LEARNERS} premiers apprenants du test (ordre de la partition du modèle actif) ayant au moins '
             f'{MIN_STEPS} pas enregistrés. Sélection fixe, jamais selon l’erreur ; elle favorise les parcours longs '
             'et ne représente pas toute la population de test.')
UNITS = {'singpad': 'groupe d’enregistrements', 'yousician': 'jour actif'}
_lock = threading.RLock()
_cohorts = {}
_forecasts = {}


def check_integrity(data, meta, splits):
    # Same gates as scripts/build_musical_demo.py: data and learner split must be the model's own.
    if data.get('sha256') != meta.get('sha256'):
        raise ValueError('Prepared data digest differs from the served model')
    if public_split_provenance(splits) != meta['splits']:
        raise ValueError('Learner split differs from the served model')


def validate_observations(data, meta):
    """Validate the actual parsed observations before publishing an immutable generation."""
    if data.get('preprocessing') != meta.get('preprocessing', PREPROCESSING[meta['source']]):
        raise ValueError('Prepared preprocessing mismatch')
    for rows in data['learners'].values():
        previous = None
        for row in rows:
            t = datetime.fromisoformat(row['time']) if meta['source']=='singpad' else float(row['time'])
            if previous is not None and t <= previous: raise ValueError('Unordered prepared groups')
            if meta['source'] != 'singpad' and not math.isfinite(t): raise ValueError('Invalid prepared time')
            previous = t
            if not isinstance(row['exercise'], str) or len(row['exercise'])>1000 or not row['obs']:
                raise ValueError('Invalid prepared group')
            for k, value, weight in row['obs']:
                if (type(k) is not int or not 0<=k<meta['K'] or not math.isfinite(value)
                        or not 0<=value<=1 or not math.isfinite(weight) or not 0<weight<=100000
                        or meta['source']=='singpad' and value not in (0,1)):
                    raise ValueError('Invalid prepared observation')


def cohort(source):
    try:
        active = json.loads((REGISTRY_ROOT/'active.json').read_text(encoding='utf-8'))
        model_id = active[source]
        if not isinstance(model_id, str) or not re.fullmatch(r'[a-z0-9_-]{1,120}', model_id):
            raise ValueError('Invalid model registry identifier')
        meta, model = cached_validate(REGISTRY_ROOT/model_id)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        raise HTTPException(503, {'code': 'missing_model', 'message': 'Modèle actif absent ou incompatible ; vérifiez le registre.'})
    try:
        path = DATA_DIR/f'{source}-prepared.json.gz'
        # Read/hash the compressed bytes once per boundary, including equal-size writes
        # whose timestamp was preserved. Canonical JSON is hashed only on a new generation.
        compressed = path.read_bytes()
        key = (source, model_id, canonical_digest(meta), hashlib.sha256(compressed).hexdigest())
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        raise HTTPException(503, {'code': 'missing_data', 'message': 'Données privées préparées absentes ; reconstruisez les parcours.'})
    with _lock:
        if source in _cohorts and _cohorts[source][0] == key:
            return _cohorts[source][1]
        try:
            data = json.loads(gzip.decompress(compressed))
            # Yousician's active v1 weights predate the implementation version bump for
            # SingPAD chronology. Its own unchanged daily preparation is compatible v2.
            compatible = data.get('version') == meta['version'] or (
                source == 'yousician' and meta['version'] == 'musical-cloud-v1'
                and data.get('version') == VERSION and data.get('preprocessing') == PREPROCESSING[source])
            if data.get('source') != source or not compatible:
                raise ValueError('Prepared source/schema mismatch')
            if data.get('fixture') != meta.get('fixture'):
                raise ValueError('Fixture and real-source modes cannot be mixed')
            splits = split_learners(data['learners'], meta['seed'])
            check_integrity(data, meta, splits)
            validate_observations(data, meta)
            content_digest, generation_id = generation(data, meta, model_id)
        except (OSError, ValueError, KeyError, TypeError, EOFError):
            raise HTTPException(503, {'code': 'missing_data', 'message': 'Données préparées incompatibles avec le modèle actif ; reconstruisez-les.'})
        eligible = [data['learners'][l] for l in splits['test'] if len(data['learners'][l]) >= MIN_STEPS]
        # A replay is bounded explicitly, not silently truncated. Longer histories stay
        # in research data; this interface advertises the same 500-group API contract.
        supported = [rows for rows in eligible if len(rows) <= MAX_HISTORY]
        frozen_meta = freeze(meta)
        value = {'source': source, 'model_id': model_id, 'meta': meta, 'digest': data['sha256'],
                 'content_digest': content_digest, 'generation': generation_id,
                 'validated': (frozen_meta, model),
                 'learners': freeze(supported[:MAX_LEARNERS]),
                 'counts': {'test_learners': len(splits['test']), 'eligible': len(eligible),
                            'shown': min(len(supported), MAX_LEARNERS),
                            'excluded_over_limit': len(eligible)-len(supported),
                            'excluded_short': len(splits['test'])-len(eligible)}}
        value['meta'] = frozen_meta
        # Discard only this source's obsolete forecast generations; no cross-source purge.
        for previous in list(_forecasts):
            if previous[0] == source and previous[1] != generation_id:
                del _forecasts[previous]
        _cohorts[source] = (key, value)
        return value


def learner_rows(c, learner):
    if not learner.isdigit() or not 1 <= int(learner) <= len(c['learners']):
        raise HTTPException(404, 'Parcours inconnu')
    return int(learner)-1, c['learners'][int(learner)-1]


def day(row, first, source):
    if source == 'singpad':
        return round((datetime.fromisoformat(row['time'])-datetime.fromisoformat(first['time'])).total_seconds()/86400, 2)
    return row['time']-first['time']


def tally(row):
    per = {}
    for k, v, w in row['obs']:
        s = per.setdefault(k, [0., 0.]); s[0] += v*w; s[1] += w
    return per


def step_view(index, row, first, source):
    per = tally(row); successes = sum(s for s, _ in per.values()); notes = sum(n for _, n in per.values())
    return {'index': index, 'day': day(row, first, source), 'exercise': row['exercise'] or None,
            'score': successes/notes, 'weight': notes,
            'concepts': {str(k): [s, n] for k, (s, n) in sorted(per.items())}}


def provenance(c):
    meta = c['meta']
    return {'model_id': c['model_id'], 'architecture': meta['model'], 'model_sha256': meta['model_sha256'],
            'generation': c['generation'], 'data_content_sha256': c['content_digest'], 'identity_contract': CONTRACT,
            'max_history': MAX_HISTORY,
            'eligibility': eligibility(meta),
            'data_mode': 'synthetic_fixture' if meta.get('fixture') else 'private_research_data',
            'dataset': c['source'], 'instrument': meta['instrument'], 'target': meta['target'],
            'K': meta['K'], 'hidden': meta['hidden'], 'context': meta['context'], 'seed': meta['seed'],
            'citation': meta['citation'], 'version': meta['version'], 'splits': meta['splits'],
            'test': {k: v for k, v in meta['test'].items() if k != 'calibration_bins'},
            'calibration_bins': meta['test'].get('calibration_bins'),
            'train_mean_reference': meta['constant_train_mean_reference']['mean'],
            'train_mean_test': {k: v for k, v in meta['constant_train_mean_reference'].get('test', {}).items()
                                if k != 'calibration_bins'},
            'limitations': meta['limitations'], 'unit': UNITS[c['source']],
            'engine': 'PyTorch EnhancedGRU servi par musical_forecast ; aucun modèle classique sur ce chemin.'}


def query_for(c, rows, j):
    if j > MAX_HISTORY:
        raise HTTPException(422, f'Historique limité explicitement à {MAX_HISTORY} groupes ; aucun passé tronqué.')
    target = rows[j]
    return BenchmarkQuery(source=c['source'], model_id=c['model_id'], instrument=c['meta']['instrument'],
                          query_time=target['time'], exercise=target['exercise'],
                          concepts=sorted({o[0] for o in target['obs']}),
                          history=[{'time': r['time'], 'exercise': r['exercise'],
                                    'observations': [{'concept': k, 'score': v, 'weight': w} for k, v, w in r['obs']]}
                                   for r in rows[:j]])


def forecast_at(c, li, rows, j):
    key = (c['source'], c['generation'], request_identity(c, li, rows, j))
    with _lock:
        if key not in _forecasts:
            _forecasts[key] = forecast_with_model(query_for(c, rows, j), c['validated'])
        return _forecasts[key]


def note_log_loss(p, successes, notes):
    p = min(max(p, 1e-7), 1-1e-7)
    return -(successes*math.log(p)+(notes-successes)*math.log(1-p))


def score(source, predictions, per):
    """Note-weighted log-loss (SingPAD) or absolute error (Yousician) on identical targets."""
    keys = [k for k in predictions if int(k) in per]
    if not keys:
        return None
    if SOURCES[source]['binary']:
        notes = sum(per[int(k)][1] for k in keys)
        return sum(note_log_loss(predictions[k], *per[int(k)]) for k in keys)/notes
    return sum(abs(predictions[k]-per[int(k)][0]/per[int(k)][1]) for k in keys)/len(keys)


def trail_entry(c, li, rows, j):
    f = forecast_at(c, li, rows, j); per = tally(rows[j])
    entry = {'index': j, 'status': f['status'], 'reason': f.get('reason')}
    if f.get('predictions'):
        p = f['predictions']
        entry.update(predicted_mean=sum(p.values())/len(p),
                     observed_mean=sum(per[int(k)][0]/per[int(k)][1] for k in p)/len(p),
                     error=score(c['source'], p, per),
                     metric='log-loss par note' if SOURCES[c['source']]['binary'] else 'erreur absolue',
                     concepts={k: [v, per[int(k)][0], per[int(k)][1]] for k, v in p.items()})
    return entry


def edges(past):
    counts = {}
    for row in past:
        ks = sorted({o[0] for o in row['obs']})
        for a in range(len(ks)):
            for b in range(a+1, len(ks)):
                counts[(ks[a], ks[b])] = counts.get((ks[a], ks[b]), 0)+1
    return [[a, b, n] for (a, b), n in sorted(counts.items())]


def states_at(c, past, concepts, predictions, query_time):
    summary = skill_states(past, concepts, c['source'], predictions, query_time)
    for state in summary['states']:
        observed = state['observation']
        # Recency and absolute dates would disclose when the next step happened.
        observed.pop('recency', None)
        last = observed.pop('last_observed_time', None)
        if last is not None:
            observed['last_observed_step'] = max(i for i, r in enumerate(past) if r['time'] == last)
    return summary


@router.get('/learners')
def learners(source: Literal['singpad', 'yousician'] = 'singpad'):
    c = cohort(source)
    return {'source': source, 'selection': SELECTION, 'counts': c['counts'], 'provenance': provenance(c),
            'learners': [{'token': f'{i+1:02}', 'label': f'Parcours de test {i+1:02}', 'steps': len(rows)}
                         for i, rows in enumerate(c['learners'])],
            'replay': 'Rejeu rétrospectif exploratoire : la longueur totale du parcours sert à la navigation, '
                      f'jamais d’entrée au modèle. Parcours de plus de {MAX_HISTORY} pas exclus de cette interface.'}


@router.get('/state')
def state(source: Literal['singpad', 'yousician'] = 'singpad', learner: str = Query('01', max_length=4),
          cutoff: int = Query(1, ge=1, le=MAX_HISTORY)):
    c = cohort(source); li, rows = learner_rows(c, learner)
    if cutoff > len(rows):
        raise HTTPException(422, 'Point de coupure hors du parcours')
    past = rows[:cutoff]; first = rows[0]
    target = rows[cutoff] if cutoff < len(rows) else None
    target_concepts = sorted({o[0] for o in target['obs']}) if target else []
    forecast = forecast_at(c, li, rows, cutoff) if target else None
    predictions = forecast.get('predictions') if forecast else None
    observed = sorted({o[0] for r in past for o in r['obs']})
    summary = states_at(c, past, sorted(set(observed) | set(target_concepts)), predictions,
                        target['time'] if target else None)
    receipt = None
    identity = {'generation': c['generation'], 'request_id': request_identity(c, li, rows, cutoff),
                'model_id': c['model_id'], 'model_sha256': c['meta']['model_sha256'],
                'source': source, 'learner': learner, 'cutoff': cutoff,
                'target_index': cutoff if target else None}
    if predictions:
        receipt = o08_demo.ticket({'stage': 'living-predicted', 'source': source, 'learner': learner,
                                   'cutoff': cutoff, 'digest': c['digest'],
                                   'identity': identity,
                                   'model_sha256': c['meta']['model_sha256'], 'predictions': predictions})
    return {'source': source, 'learner': learner, 'cutoff': cutoff, 'steps_total': len(rows),
            'identity': identity,
            'unit': UNITS[source], 'K': c['meta']['K'],
            'past': [step_view(i, r, first, source) for i, r in enumerate(past)],
            'skill_states': summary, 'edges': edges(past),
            'target': None if target is None else {
                'index': cutoff, 'exercise': target['exercise'] or None,
                'exercise_supported': (not target['exercise']) or target['exercise'] in c['meta']['items'],
                'concepts': target_concepts,
                'definition': 'Prévision rétrospective conditionnelle à l’exercice enregistré et aux concepts évalués '
                              'de ce pas ; ses résultats sont exclus de cette réponse.' if source == 'singpad' else
                              'Prévision rétrospective du score agrégé du prochain jour actif, sans connaître ce jour '
                              'ni ses exercices ; son résultat est exclu de cette réponse.'},
            'forecast': None if forecast is None else {k: forecast.get(k) for k in
                        ('status', 'reason', 'predictions', 'model_id', 'prefix_groups', 'target')},
            'trail': [trail_entry(c, li, rows, j) for j in range(1, cutoff)],
            'recommendation': recommend(summary, catalogue_from_history(past, source)),
            'reveal_receipt': receipt, 'future_outcome_included': False,
            'provenance': {'model_id': c['model_id'], 'model_sha256': c['meta']['model_sha256'],
                           'generation': c['generation'], 'data_content_sha256': c['content_digest']}}


class Reveal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    receipt: str = Field(max_length=32768)


def verify(receipt):
    try:
        encoded, signature = receipt.split('.')
        expected = hmac.new(o08_demo.SECRET, encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected): raise ValueError()
        payload = json.loads(base64.urlsafe_b64decode(encoded))
        if payload['expires'] < time.time() or payload['stage'] != 'living-predicted': raise ValueError()
        if payload['source'] not in ('singpad', 'yousician'): raise ValueError()
        return payload
    except (ValueError, KeyError, TypeError):
        raise HTTPException(409, 'Révélation expirée ou parcours modifié ; recalculez la prévision.')


@router.post('/reveal')
def reveal(body: Reveal):
    payload = verify(body.receipt); c = cohort(payload['source'])
    identity = payload.get('identity', {})
    if (payload['digest'] != c['digest'] or payload['model_sha256'] != c['meta']['model_sha256']
            or identity.get('generation') != c['generation'] or identity.get('model_id') != c['model_id']):
        raise HTTPException(409, 'Révélation expirée ou parcours modifié ; recalculez la prévision.')
    li, rows = learner_rows(c, payload['learner']); j = payload['cutoff']
    if not 1 <= j < len(rows):
        raise HTTPException(409, 'Révélation expirée ou parcours modifié ; recalculez la prévision.')
    if identity.get('request_id') != request_identity(c, li, rows, j):
        raise HTTPException(409, 'Les observations ont changé ; recalculez la prévision.')
    predictions = payload['predictions']; per = tally(rows[j]); past = rows[:j]
    binary = SOURCES[c['source']]['binary']
    comparison = []
    for k, p in sorted(predictions.items(), key=lambda item: int(item[0])):
        s, n = per[int(k)]
        comparison.append({'concept': int(k), 'prediction': p, 'observed': s/n, 'notes': n, 'successes': s,
                           'absolute_error': abs(p-s/n), 'log_loss': note_log_loss(p, s, n)/n if binary else None})
    mean = c['meta']['constant_train_mean_reference']['mean']
    history = {}
    for row in past:
        for k, (s, n) in tally(row).items():
            h = history.setdefault(k, [0., 0.]); h[0] += s; h[1] += n
    supported = {k: v for k, v in predictions.items() if int(k) in history}
    personal = {k: history[int(k)][0]/history[int(k)][1] for k in supported}
    return {'cutoff': j, 'learner': payload['learner'], 'model_id': c['model_id'],
            'source': c['source'], 'identity': identity,
            'model_sha256': c['meta']['model_sha256'], 'comparison': comparison,
            'error': score(c['source'], predictions, per),
            'metric': 'log-loss par note' if binary else 'erreur absolue',
            'predicted_mean': sum(predictions.values())/len(predictions),
            'observed_mean': sum(r['observed'] for r in comparison)/len(comparison),
            'references': {
                'scope': 'Références simples non apprises, évaluées sur exactement les mêmes notes ; '
                         'elles ne remplacent pas les contrôles appris de la recherche.',
                'train_mean': {'value': mean, 'error': score(c['source'], {k: mean for k in predictions}, per),
                               'targets': len(predictions)},
                'learner_concept_history': {
                    'definition': 'Fréquence de réussite passée du même concept chez cet apprenant ; '
                                  'concepts sans passé exclus et réseau rescoré sur le même sous-ensemble.',
                    'targets': len(personal), 'excluded': len(predictions)-len(personal),
                    'error': score(c['source'], personal, per) if personal else None,
                    'model_error_same_targets': score(c['source'], supported, per) if personal else None}},
            'interpretation': 'Exemple de test choisi par une règle fixe ; erreurs conservées, aucune sélection.'}


@router.get('/inspect')
def inspect(source: Literal['singpad', 'yousician'] = 'singpad', learner: str = Query('01', max_length=4),
            cutoff: int = Query(2, ge=1, le=MAX_HISTORY)):
    c = cohort(source); li, rows = learner_rows(c, learner)
    if not 1 <= cutoff < len(rows):
        raise HTTPException(422, 'Aucune prévision à inspecter à ce point de coupure')
    served = forecast_at(c, li, rows, cutoff)
    if not served.get('predictions'):
        return {'available': False, 'reason': served.get('reason'), 'cutoff': cutoff,
                'source': source, 'learner': learner,
                'identity': {'generation': c['generation'], 'request_id': request_identity(c, li, rows, cutoff),
                             'model_id': c['model_id'], 'model_sha256': c['meta']['model_sha256'],
                             'source': source, 'learner': learner, 'cutoff': cutoff, 'target_index': cutoff}}
    meta, model = c['validated']; K = meta['K']
    query = query_for(c, rows, cutoff)
    # Same grouping, encoding and window as musical_forecast; the comparison below checks it.
    grouped = {}
    for r in query.history:
        if r.time >= query.query_time: continue
        g = grouped.setdefault(r.time, {'time': r.time, 'exercise': set(), 'obs': []})
        if r.exercise: g['exercise'].update(r.exercise.split('|'))
        g['obs'].extend([[o.concept, o.score, o.weight] for o in r.observations])
    encoded = []
    for t in sorted(grouped):
        g = grouped[t]; g['exercise'] = '|'.join(sorted(g['exercise'])); encoded.append(g)
    encoded.append({'time': query.query_time, 'exercise': query.exercise, 'obs': []})
    values = apply_feature_mode(encode(encoded, K, meta['items']), K, meta.get('feature_mode', 'full'))
    context = meta['context']; length = len(encoded)
    left = max(0 if length <= context-1 else ((length-1)//(context-1))*(context-1)-1, 0)
    tensors = [torch.from_numpy(a[left:]).unsqueeze(0) for a in values]
    # A private copy keeps the hook isolated from concurrent served requests.
    probe = copy.deepcopy(model).eval(); captured = []
    handle = probe.encoder.register_forward_hook(lambda m, i, o: captured.append(o[0].detach().clone())) \
        if hasattr(probe, 'encoder') else None
    try:
        with torch.no_grad():
            logits = forward(probe, meta['model'], tensors)[0, -1]
    finally:
        if handle is not None: handle.remove()
    probabilities = torch.sigmoid(logits).numpy()
    concepts = query.concepts
    difference = max(abs(float(probabilities[k])-served['predictions'][str(k)]) for k in concepts)
    x = values[0][left:]; prev_item = values[1][left:]; cur_item = values[2][left:]
    names = {v: k for k, v in meta['items'].items()}
    steps = []
    for t in range(x.shape[0]):
        row = x[t]; target_cols = set()
        features = {}
        for k in concepts:
            cols = (K+k, k, 2*K+k, 3*K+k)
            target_cols.update(cols)
            features[str(k)] = [round(float(row[col]), 5) for col in cols]
        steps.append({'step': left+t, 'is_query': left+t == length-1,
                      'previous_exercise': names.get(int(prev_item[t])), 'previous_item': int(prev_item[t]),
                      'current_exercise': names.get(int(cur_item[t])), 'current_item': int(cur_item[t]),
                      'features': features,
                      'other_nonzero_features': int(sum(1 for i, v in enumerate(row) if v != 0 and i not in target_cols))})
    hidden = captured[0][0].numpy() if len(captured) == 1 else None
    return {'available': True, 'cutoff': cutoff, 'architecture': meta['model'],
            'source': source, 'learner': learner,
            'identity': {'generation': c['generation'], 'request_id': request_identity(c, li, rows, cutoff),
                         'model_id': c['model_id'], 'model_sha256': meta['model_sha256'],
                         'source': source, 'learner': learner, 'cutoff': cutoff, 'target_index': cutoff},
            'window': {'available_steps': cutoff, 'window_start': left, 'steps_in_window': len(steps),
                       'context': context, 'counts_cover_full_prefix': True},
            'tensors': {'x': [1, len(steps), 4*K], 'previous_item': [1, len(steps)], 'current_item': [1, len(steps)],
                        'difficulty': [1, len(steps), 2],
                        'gru_input_width': getattr(getattr(probe, 'encoder', None), 'input_size', None),
                        'hidden_size': getattr(getattr(probe, 'encoder', None), 'hidden_size', None)},
            'feature_order': ['réussite du pas précédent (part des notes)', 'échec du pas précédent (part des notes)',
                              'log(1 + réussites cumulées antérieures)', 'log(1 + échecs cumulés antérieurs)'],
            'steps': steps,
            'hidden_states': None if hidden is None else [[round(float(v), 4) for v in h] for h in hidden],
            'head': {'inputs': ['état caché GRU', 'exercice demandé (embedding)', 'difficulté (nulle ici)',
                                'cumuls antérieurs des K concepts'],
                     'logits': {str(k): float(logits[k]) for k in concepts},
                     'probabilities': {str(k): float(probabilities[k]) for k in concepts}},
            'served_predictions': served['predictions'],
            'matches_served_forecast': difference < 1e-5, 'max_abs_difference': difference,
            'layers': [{'name': n, 'shape': list(p.shape)} for n, p in probe.named_parameters()],
            'parameters': sum(p.numel() for p in probe.parameters()),
            'attention': None,
            'attention_note': 'Le modèle servi (EnhancedGRU) ne contient pas d’attention : aucune carte n’est affichée.',
            'activation_note': 'Valeurs réellement calculées pour cette entrée ; elles ne constituent pas une explication causale.'}
