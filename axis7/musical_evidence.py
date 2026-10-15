"""Observed source-specific evidence, explicitly distinct from neural predictions."""
from collections import defaultdict

POLICY = {'version': 'observed-fragility-v1', 'min_timestamp_groups': 3, 'min_notes': 10,
          'min_groups_with_failures': 2, 'recent_fraction_below': .65, 'recent_groups': 3}


def evidence(rows, concepts, source):
    grouped = defaultdict(list)
    for row in rows:
        values = defaultdict(lambda: [0., 0.])
        for concept, score, weight in row['obs']:
            values[concept][0] += score*weight; values[concept][1] += weight
        for concept, (success, weight) in values.items():
            grouped[concept].append((success, weight, row.get('exercise', '')))
    result = []
    for concept in concepts:
        history = grouped[concept]
        if not history:
            result.append({'concept': concept, 'status': 'not_evaluated', 'timestamp_groups': 0,
                           'message': 'Ce concept n’a pas encore de résultat observé.'})
            continue
        successful = sum(r[0] for r in history); weight = sum(r[1] for r in history)
        recent = history[-3:]; recent_fraction = sum(r[0] for r in recent)/sum(r[1] for r in recent)
        failed_groups = sum(a < n for a, n, _ in history)
        exercises = {e for _, _, bundle in history for e in bundle.split('|') if e}
        sufficient = len(history) >= 3 and (source != 'singpad' or weight >= 10)
        recurring = sufficient and failed_groups >= 2 and recent_fraction < .65
        status = 'recurring_low_observed_performance' if recurring else 'observed_without_recurring_flag' if sufficient else 'insufficient_evidence'
        before_recent = history[:-3]
        trend = recent_fraction - sum(a for a,n,e in before_recent)/sum(n for a,n,e in before_recent) if before_recent else None
        result.append({'concept': concept, 'status': status, 'timestamp_groups': len(history),
                       'observed_weight': weight, 'observed_fraction': successful/weight,
                       'recent_fraction': recent_fraction, 'groups_with_nonperfect_score': failed_groups,
                       'exercise_coverage': len(exercises), 'recent_minus_earlier_fraction': trend,
                       'uncertainty': 'evidence_limited' if not sufficient else 'no_individual_probability_interval',
                       'message': 'Des résultats faibles se répètent dans plusieurs groupes temporels.' if recurring else
                                  'L’historique est encore trop court pour parler d’une difficulté récurrente.' if not sufficient else
                                  'Les résultats disponibles ne déclenchent pas le signal de difficulté récurrente.',
                       'practice_suggestion': 'Reprendre un exercice déjà évalué sur ce concept et comparer les prochains résultats.' if recurring else None})
    return {'kind': 'observed_historical_summary', 'policy': POLICY, 'source_concepts': result,
            'scope': 'concepts de la source' if source == 'singpad' else 'score global de la base, pas une compétence isolée',
            'taxonomy_mapping': {'status': 'unvalidated', 'target_taxonomy': None},
            'limitations': ['Règle descriptive, pas un diagnostic cognitif.',
                           'Aucun effet pédagogique démontré pour les suggestions.',
                           'Les groupes temporels ne sont pas nécessairement des séances indépendantes.']}
