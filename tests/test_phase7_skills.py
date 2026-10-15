import pytest
from pydantic import ValidationError
from axis7.skill_states import skill_states, recommend, catalogue_from_history
from axis7.taxonomy import MappingReview, approved_mappings


def history(scores):
    return [{'time':t,'exercise':'exercise-a','obs':[[0,s,10]]} for t,s in enumerate(scores)]


@pytest.mark.parametrize('scores,state',[
    ([], 'not_evaluated'),([.1,.2], 'insufficient_evidence'),
    ([.3,.4,.3], 'repeatedly_weak_observed_performance'),
    ([.9,.8,1.], 'consistently_strong_observed_performance'),
    ([.6,1.,.7], 'inconsistent_observed_performance'),
    ([.2,.3,.2,.8,.9,.8], 'improving_observed_performance'),
    ([.9,.9,.8,.3,.3,.4], 'declining_observed_performance')])
def test_descriptive_states(scores,state):
    result=skill_states(history(scores),[0],'singpad')
    assert result['states'][0]['estimated_state']==state
    assert result['states'][0]['model_prediction']['value'] is None


def test_recommendations_require_supported_catalogue_and_evidence():
    rows=history([.3,.4,.2]); summary=skill_states(rows,[0,1],'singpad')
    result=recommend(summary,catalogue_from_history(rows,'singpad'))
    assert result['suggestions'][0]['exercise']=='exercise-a'
    assert result['suggestions'][0]['concepts']==[0]
    assert recommend(summary,[])['status']=='abstained'
    assert recommend(summary,[{'exercise':'piano','source':'piano','concepts':[0]}])['status']=='abstained'


def test_future_rejected_and_missing_not_failure():
    with pytest.raises(ValueError):skill_states(history([.2,.3,.4]),[0],'singpad',query_time=2)
    result=skill_states(history([.2,.3,.4]),[1],'singpad')['states'][0]
    assert result['observation']['groups_without_concept']==3
    assert result['estimated_state']=='not_evaluated'


def test_no_automatic_expert_approval():
    record={'source':'singpad','source_concept':'0','proposed_skill':'rhythm',
            'definition':'Candidate definition requiring source verification.',
            'supporting_evidence':['Source definition must be examined by teacher.'],'version':'1','status':'pending_review'}
    assert approved_mappings([record])==[]
    with pytest.raises(ValidationError): MappingReview(**{**record,'status':'approved'})
