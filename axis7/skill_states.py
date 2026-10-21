"""Versioned descriptive states and catalogue-bound practice suggestions.

Thresholds are transparent product policies, not estimated cognitive mastery or
validated clinical/pedagogical cutoffs. Prediction remains a separate layer.
"""
from datetime import datetime
import math

POLICY = {'version': 'source-skill-state-v1', 'min_groups': 3, 'min_binary_notes': 10,
          'strong_min_fraction': .8, 'weak_max_fraction': .65,
          'trend_min_prior_groups': 3, 'trend_absolute_change': .15,
          'inconsistent_range': .3}


def skill_states(rows, concepts, source, predictions=None, query_time=None):
    rows = sorted(rows, key=lambda row: row['time'])
    predictions = predictions or {}; states = []
    for k in concepts:
        groups = []
        for row in rows:
            if query_time is not None and row['time'] >= query_time:
                raise ValueError('Skill state requires strictly earlier observations')
            observations = [o for o in row['obs'] if o[0] == k]
            n = sum(o[2] for o in observations)
            if n: groups.append({'time': row['time'], 'score': sum(o[1]*o[2] for o in observations)/n,
                                 'weight': n, 'exercise': row.get('exercise', '')})
        observed = {'groups_evaluated': len(groups), 'groups_without_concept': len(rows)-len(groups),
                    'missingness_meaning': 'concept not recorded; absence is not a failed attempt'}
        state = 'not_evaluated'; trend = None
        if groups:
            n = sum(g['weight'] for g in groups); a = sum(g['weight']*g['score'] for g in groups)
            recent = groups[-3:]; recent_score = sum(g['weight']*g['score'] for g in recent)/sum(g['weight'] for g in recent)
            before = groups[:-3]
            trend = recent_score-sum(g['weight']*g['score'] for g in before)/sum(g['weight'] for g in before) if len(before)>=3 else None
            observed.update(evaluated_weight=n, historical_score=a/n, recent_score=recent_score,
                recent_minus_prior=trend, last_observed_time=groups[-1]['time'],
                exercise_coverage=len({e for g in groups for e in g['exercise'].split('|') if e}),
                binary_successes=a if source=='singpad' else None,
                binary_failures=n-a if source=='singpad' else None,
                recency=None)
            if query_time is not None:
                observed['recency'] = {'value': (datetime.fromisoformat(query_time)-datetime.fromisoformat(groups[-1]['time'])).total_seconds()/86400,
                                       'unit': 'days_source_local_time'} if source=='singpad' else {'value': query_time-groups[-1]['time'], 'unit': 'signup_days' if source=='yousician' else 'blocks_not_elapsed_time'}
            sufficient = len(groups)>=3 and (source!='singpad' or n>=10)
            scores = [g['score'] for g in recent]
            if not sufficient: state = 'insufficient_evidence'
            elif trend is not None and trend>=.15: state = 'improving_observed_performance'
            elif trend is not None and trend<=-.15: state = 'declining_observed_performance'
            elif recent_score<.65 and sum(g['score']<.65 for g in recent)>=2: state = 'repeatedly_weak_observed_performance'
            elif min(scores)>=.8: state = 'consistently_strong_observed_performance'
            elif max(scores)-min(scores)>=.3: state = 'inconsistent_observed_performance'
            else: state = 'observed_without_clear_pattern'
        messages = {
            'not_evaluated': 'Ce concept ne dispose pas encore de résultat enregistré.',
            'insufficient_evidence': 'Trop peu de groupes ou de notes pour caractériser une régularité.',
            'improving_observed_performance': 'Les trois derniers résultats sont meilleurs que la période antérieure disponible.',
            'declining_observed_performance': 'Les trois derniers résultats sont moins élevés que la période antérieure disponible.',
            'repeatedly_weak_observed_performance': 'Des résultats faibles se répètent dans les derniers groupes observés.',
            'consistently_strong_observed_performance': 'Les trois derniers groupes montrent des résultats régulièrement élevés.',
            'inconsistent_observed_performance': 'Les résultats récents varient fortement entre les groupes.',
            'observed_without_clear_pattern': 'Les résultats disponibles ne montrent pas de motif net selon cette règle.'}
        p = predictions.get(str(k))
        if p is not None and (not math.isfinite(p) or not 0<=p<=1): raise ValueError('Invalid forecast')
        states.append({'concept': k, 'observation': observed,
            'model_prediction': {'value': p, 'kind': 'note_success_probability' if source=='singpad' else 'continuous_score',
                'individual_interval': None, 'uncertainty': 'individual uncertainty not validated'},
            'estimated_state': state, 'interpretation': messages[state],
            'prediction_interpretation': 'Prévision statistique d’une prochaine note comparable.' if p is not None and source=='singpad' else
                'Prévision statistique du prochain score global.' if p is not None else 'Aucune prévision applicable.',
            'taxonomy_status': 'source concept only; no approved piano mapping'})
    return {'policy': POLICY, 'source': source, 'states': states,
            'scope': 'descriptive performance states, not cognitive mastery',
            'limitations': ['Groupes temporels et séances pédagogiques ne sont pas équivalents.',
                'Seuils descriptifs non validés par une étude pédagogique.',
                'Une absence de mesure n’est pas une mauvaise performance.']}


def catalogue_from_history(rows, source):
    """Only exercises observed before the forecast; atomic bundles stay atomic."""
    catalogue = {}
    for row in rows:
        exercise = row.get('exercise', '')
        if not exercise: continue
        entry = catalogue.setdefault(exercise, {'exercise': exercise, 'source': source,
                                               'concepts': set(), 'evidence_groups': 0})
        entry['concepts'].update(o[0] for o in row['obs']); entry['evidence_groups'] += 1
    return [{**v, 'concepts': sorted(v['concepts']), 'availability': 'observed_source_exercise_id; content not distributed'}
            for _,v in sorted(catalogue.items())]


def recommend(summary, catalogue):
    states = {s['concept']: s for s in summary['states']}
    flagged = {k for k,s in states.items() if s['estimated_state'] in
               ('repeatedly_weak_observed_performance','declining_observed_performance','inconsistent_observed_performance')}
    candidates = []
    for entry in catalogue:
        if entry.get('source') != summary['source'] or not entry.get('exercise'): continue
        related = sorted(flagged.intersection(entry.get('concepts', [])))
        if not related: continue
        candidates.append({'exercise': entry['exercise'], 'concepts': related,
            'reason': 'Cet exercice déjà observé contient les concepts dont les résultats demandent une vérification.',
            'support': [{'concept': k, 'state': states[k]['estimated_state'],
                         'observed_groups': states[k]['observation']['groups_evaluated']} for k in related],
            'exercise_evidence_groups': entry.get('evidence_groups',0),
            'caveat': 'Suggestion descriptive ; contenu à récupérer auprès de la source. Effet pédagogique non démontré.'})
    candidates.sort(key=lambda e: (-len(e['concepts']),-e['exercise_evidence_groups'],e['exercise']))
    return {'status': 'suggested' if candidates else 'abstained', 'suggestions': candidates[:3],
            'reason': None if candidates else 'Aucun exercice connu ne relie une difficulté suffisamment observée à un contenu disponible.',
            'method': 'deterministic evidence rule; no learned ranking', 'educational_effect': 'not evaluated'}
