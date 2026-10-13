from axis7.forecast_policy import PolicyInputs,evaluate

def test_context_events_do_not_satisfy_assessed_attempt_minimum():
    inputs=PolicyInputs(instrument='piano',rubrics=frozenset({'a'}),supported_rubrics=frozenset({'a'}),
        requires_item_check=False,item_known=None,prefix_count=3,eligible_observations=3,
        eligible_attempts=1,recent_confidences=(1,1,1),provenance_counts={'synthetic':3})
    result=evaluate(inputs)
    assert result.reason_code=='insufficient_history' and not result.research_eligible
