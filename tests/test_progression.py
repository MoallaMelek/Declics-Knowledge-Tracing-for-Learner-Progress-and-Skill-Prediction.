from axis7.progression import describe,notebook_forecast

def rows(ratings,source='self',exercise='a',confidence=None):
    return [{'attempt_id':str(i),'exercise_id':exercise,'source':source,'provenance':'local_real',
        'attempt_sequence':i+1,'confidence':confidence,'ratings':[{'skill_id':'pitch','rating':r}]} for i,r in enumerate(ratings)]

def test_consistent_ordinal_change_is_descriptive_and_not_teacher_confirmation():
    result=describe(rows(['needs_work']*3+['developing']*3),[{'id':'pitch'}])[0]
    assert result['status']=='consistent_higher_ratings'
    assert len(result['evidence_ids'])==6
    assert not result['teacher_confirmed_development'] and result['future_prediction'] is None

def test_source_switch_or_exercise_switch_does_not_create_improvement():
    for key,value in [('source','teacher'),('exercise_id','b')]:
        sessions=rows(['needs_work']*3+['comfortable']*3)
        for row in sessions[3:]:row[key]=value
        result=describe(sessions,[{'id':'pitch'}])[0]
        assert result['status']=='recent_observations_only' and result['comparable_observations']==3

def test_low_confidence_does_not_become_progress():
    result=describe(rows(['comfortable']*6,confidence=.2),[{'id':'pitch'}])[0]
    assert result['comparable_observations']==0 and len(result['low_confidence_omitted_ids'])==6

def test_overlapping_ordinal_windows_do_not_claim_consistent_improvement():
    result=describe(rows(['needs_work','developing','comfortable','developing','comfortable','comfortable']),[{'id':'pitch'}])[0]
    assert result['status']=='mixed_or_stable_ratings'

def test_notebook_always_abstains_even_with_many_teacher_ratings():
    result=notebook_forecast(rows(['comfortable']*100,source='teacher'))
    assert result['status']=='abstained' and result['probabilities'] is None
    assert result['validated_for_current_learner'] is False


def test_import_order_cannot_reverse_a_progress_description():
    sessions=rows(['needs_work']*3+['comfortable']*3)
    expected=describe(sessions,[{'id':'pitch'}])
    shuffled=[sessions[i] for i in [5,1,3,0,4,2]]
    assert describe(shuffled,[{'id':'pitch'}])==expected
    assert shuffled[0]['attempt_sequence']==6
