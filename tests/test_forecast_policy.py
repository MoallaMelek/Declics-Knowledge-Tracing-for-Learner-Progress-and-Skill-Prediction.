import pytest
from axis7.forecast_policy import (MIN_CONFIDENCE, MIN_ELIGIBLE_OBSERVATIONS, MIN_HISTORY_ATTEMPTS,
    POLICY_VERSION, PolicyInputs, evaluate)

SUPPORTED = frozenset({'provisional-mock-v1', 'provisional-piano-v1'})


def base_inputs(**overrides):
    values = dict(instrument='piano', rubrics=frozenset({'provisional-mock-v1'}), supported_rubrics=SUPPORTED,
        requires_item_check=False, item_known=None, prefix_count=MIN_HISTORY_ATTEMPTS,
        eligible_observations=MIN_ELIGIBLE_OBSERVATIONS, recent_confidences=(1.0, 1.0, 1.0),
        provenance_counts={'synthetic': MIN_HISTORY_ATTEMPTS})
    values.update(overrides)
    return PolicyInputs(**values)


def test_policy_version_is_stable():
    assert POLICY_VERSION == 'phase4-gate-v1'


def test_fully_supported_synthetic_history_is_terminal_and_research_eligible():
    decision = evaluate(base_inputs())
    assert decision.reason_code == 'model_not_validated_for_real_music'
    assert decision.research_eligible is True
    assert decision.user_message


def test_unsupported_instrument_overrides_every_other_check():
    decision = evaluate(base_inputs(instrument='guitar', rubrics=frozenset({'unknown-rubric'}),
        prefix_count=0, eligible_observations=0))
    assert decision.reason_code == 'unsupported_instrument'
    assert decision.research_eligible is False


def test_unsupported_rubric_overrides_insufficient_history():
    decision = evaluate(base_inputs(rubrics=frozenset({'piano-pilot-v1'}), prefix_count=0, eligible_observations=0))
    assert decision.reason_code == 'unsupported_rubric'


def test_empty_rubric_set_does_not_itself_trigger_unsupported_rubric():
    decision = evaluate(base_inputs(rubrics=frozenset(), prefix_count=0, eligible_observations=0))
    assert decision.reason_code == 'insufficient_history'


def test_unknown_exercise_overrides_insufficient_history():
    decision = evaluate(base_inputs(requires_item_check=True, item_known=False, prefix_count=0, eligible_observations=0))
    assert decision.reason_code == 'unknown_exercise'


def test_known_exercise_does_not_block_the_gate():
    decision = evaluate(base_inputs(requires_item_check=True, item_known=True))
    assert decision.reason_code == 'model_not_validated_for_real_music'


def test_insufficient_history_when_too_few_attempts():
    decision = evaluate(base_inputs(prefix_count=MIN_HISTORY_ATTEMPTS - 1))
    assert decision.reason_code == 'insufficient_history'


def test_missing_when_attempts_exist_but_too_few_eligible_observations():
    decision = evaluate(base_inputs(eligible_observations=MIN_ELIGIBLE_OBSERVATIONS - 1))
    assert decision.reason_code == 'missing'


def test_low_confidence_when_recent_eligible_average_is_below_threshold():
    decision = evaluate(base_inputs(recent_confidences=(MIN_CONFIDENCE - 0.1,) * 3))
    assert decision.reason_code == 'low_confidence'


def test_unknown_confidence_values_do_not_count_as_low_confidence():
    decision = evaluate(base_inputs(recent_confidences=(None, None, None)))
    assert decision.reason_code == 'model_not_validated_for_real_music'


def test_mixed_known_and_unknown_confidence_only_averages_known_values():
    decision = evaluate(base_inputs(recent_confidences=(None, 1.0, 1.0)))
    assert decision.reason_code == 'model_not_validated_for_real_music'


def test_research_eligible_is_false_when_any_non_synthetic_provenance_present():
    decision = evaluate(base_inputs(provenance_counts={'synthetic': 2, 'project': 1}))
    assert decision.reason_code == 'model_not_validated_for_real_music'
    assert decision.research_eligible is False


def test_research_eligible_is_false_with_no_provenance_at_all():
    decision = evaluate(base_inputs(provenance_counts={}))
    assert decision.research_eligible is False


@pytest.mark.parametrize('reason', ['unsupported_instrument', 'unsupported_rubric', 'unknown_exercise',
    'insufficient_history', 'missing', 'low_confidence', 'model_not_validated_for_real_music'])
def test_every_reason_code_has_a_non_empty_french_user_message(reason):
    from axis7.forecast_policy import REASON_MESSAGES
    assert isinstance(REASON_MESSAGES[reason], str) and REASON_MESSAGES[reason]


def test_required_item_check_must_have_positive_confirmation():
    decision = evaluate(base_inputs(requires_item_check=True, item_known=None))
    assert decision.reason_code == 'unknown_exercise'
    assert decision.research_eligible is False
