"""Inspectable practice policies; no inferred prerequisites or learning-gain claim."""
from .schema import MUSIC_SKILLS,MUSIC_LABELS
from collections import Counter

EXERCISES=[{'id':f'mock-focus-{skill}','skill_ids':[skill],
    'title':f'Atelier ciblé : {label.lower()}', 'difficulty':'introductory',
    'teacher_approved':False,'provenance':'synthetic','prerequisites':[]}
    for skill,label in zip(MUSIC_SKILLS,MUSIC_LABELS)]

def recommend(nodes,policy='balanced'):
    if policy not in ('balanced','weakest'):raise ValueError('Unknown recommendation policy')
    candidates=[]
    for node in nodes:
        evidence=[e for e in node['evidence'] if e.get('eligible',e['outcome'] is not None)]
        if len(evidence)<3:continue
        recent=evidence[-5:];recent_failure=sum(e['outcome']==0 for e in recent)/len(recent)
        codes=Counter(code for e in recent for code in set(e.get('errors',[])))
        recurring={code for code,count in codes.items() if count>=2}
        repeated_errors=sum(bool(recurring.intersection(e.get('errors',[]))) for e in recent)/len(recent)
        trend=node.get('generic_recent_change',0.)
        fragility=1-node['probability']
        score=fragility if policy=='weakest' else .5*fragility+.3*recent_failure+.1*repeated_errors+.1*max(0,-trend)
        spread=node['seed_range'];variation=spread[1]-spread[0] if spread else None
        candidates.append({'skill_id':node['id'],'label':node['label'],'score':float(score),
            'probability':node['probability'],'observations':len(evidence),'recent_failures':recent_failure,
            'recent_n':len(recent),'repeated_error_fraction':repeated_errors,
            'forecast_change':float(trend),'initialization_spread':variation})
    candidates.sort(key=lambda c:(-c['score'],c['skill_id']))
    if not candidates:
        return {'skill_id':None,'title':'Commencer par une courte évaluation',
            'text':'Au moins trois observations binaires utilisables sont nécessaires avant de prioriser une compétence.',
            'policy':policy,'status':'insufficient_evidence','alternatives':[]}
    target=candidates[0];assessment=target['initialization_spread'] is not None and target['initialization_spread']>.15
    exercise=next((e for e in EXERCISES if target['skill_id'] in e['skill_ids']),None)
    return {**target,'title':f"Vérifier {target['label'].lower()}" if assessment else f"Reprendre {target['label'].lower()}",
        'text':f"{round(target['recent_failures']*target['recent_n'])}/{target['recent_n']} difficultés récentes. "
               +('Les initialisations divergent : faire vérifier la cible par l’enseignant avant de modifier la pratique.' if assessment
                 else 'Essayer un exercice comparable, puis vérifier la prévision avec la prochaine observation.'),
        'policy':policy,'status':'heuristic_not_validated_learning_gain','action':'assessment' if assessment else 'practice',
        'exercise_id':exercise['id'] if exercise else None,'exercise':exercise,
        'alternatives':candidates[:3],'eligible_skills':len(candidates),
        'weights':{'fragility':.5,'recent_failures':.3,'repeated_errors':.1,'negative_forecast_change':.1} if policy=='balanced' else {'fragility':1},
        'limitations':['Weights and thresholds are provisional','Initialization spread is not calibrated uncertainty',
                      'No prospective learning-gain evaluation','No prerequisites are inferred']}
