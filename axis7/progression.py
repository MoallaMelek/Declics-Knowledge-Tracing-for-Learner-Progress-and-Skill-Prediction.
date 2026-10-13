"""Source-comparable descriptions, never predicted mastery or teacher confirmation."""
from collections import defaultdict

LEVELS={'needs_work':0,'developing':1,'comfortable':2}
CONFIDENCE_GATE=0.6  # provisional ingestion safeguard, not a calibrated reliability threshold

def describe(sessions,skills):
    result=[]
    for skill in skills:
        groups=defaultdict(list);omitted=[]
        for session in sessions:
            for rating in session['ratings']:
                if rating['skill_id']!=skill['id'] or rating['rating'] not in LEVELS:continue
                if session.get('confidence') is not None and session['confidence']<CONFIDENCE_GATE:
                    omitted.append(session['attempt_id']);continue
                groups[(session['exercise_id'],session['source'],session['provenance'])].append((session,rating))
        latest=max(groups.values(),key=lambda rows:rows[-1][0]['attempt_sequence']) if groups else []
        n=len(latest);status='insufficient_comparable_evidence';change=None
        if n>=6:
            before=[LEVELS[r['rating']] for _,r in latest[-6:-3]]
            after=[LEVELS[r['rating']] for _,r in latest[-3:]]
            # Ordinal categories are compared without treating their numeric codes as interval distances.
            if min(after)>max(before):status='consistent_higher_ratings';change='higher'
            elif max(after)<min(before):status='consistent_lower_ratings';change='lower'
            else:status='mixed_or_stable_ratings'
        elif n>=3:status='recent_observations_only'
        difficult=sum(r['rating']=='needs_work' for _,r in latest[-3:])>=2
        message=('Vos trois dernières évaluations comparables sont toutes plus favorables que les trois précédentes.'
            if change=='higher' else 'Vos trois dernières évaluations comparables sont toutes moins favorables que les trois précédentes.'
            if change=='lower' else 'Cet exercice revient parmi les difficultés de vos dernières évaluations.'
            if difficult else "Il faut encore des séances comparables pour décrire une évolution régulière."
            if n<6 else "Les dernières évaluations comparables sont stables ou contrastées.")
        result.append({'skill_id':skill['id'],'status':status,'message_fr':message,
            'comparable_observations':n,'exercise_id':latest[-1][0]['exercise_id'] if latest else None,
            'assessment_source':latest[-1][0]['source'] if latest else None,
            'evidence_provenance':latest[-1][0]['provenance'] if latest else None,
            'evidence_ids':[s['attempt_id'] for s,_ in latest[-6:]],'low_confidence_omitted_ids':omitted,
            'confidence_gate':CONFIDENCE_GATE,'confidence_gate_status':'provisional_safeguard',
            'recurring_difficulty':difficult,'teacher_confirmed_development':False,
            'kind':'descriptive_ordinal_comparison','future_prediction':None})
    return result

def notebook_forecast(sessions):
    return {'status':'abstained','policy_version':'phase4-gate-v1','probabilities':None,
        'reason_codes':['rubric_not_approved','no_validated_real_music_model'],
        'message_fr':"Nous ne pouvons pas encore prévoir votre prochain résultat. Votre carnet montre les évaluations déjà enregistrées.",
        'evidence_count':len(sessions),'training_provenance':None,
        'teacher_confirmed_development':False,'validated_for_current_learner':False}
