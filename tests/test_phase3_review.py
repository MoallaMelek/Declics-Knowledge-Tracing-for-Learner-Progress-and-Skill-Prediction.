"""Regression of source comparability and imported collection quality."""
import copy
import pytest
from axis7.practice import _skill_status
from axis7.pilot_data import validate_export,guard_binary_conversion_ready
from test_pilot_data import good_export

def test_changing_rater_is_not_evidence_of_improved_skill():
    touches=[{'attempt_id':str(i),'exercise_id':'same','rating':'needs_work' if i<3 else 'comfortable',
              'source':'self' if i<3 else 'teacher'} for i in range(6)]
    assert _skill_status('pitch',touches)['status']!='improving'
    for t in touches:t['source']='teacher'
    assert _skill_status('pitch',touches)['status']=='improving'

@pytest.mark.parametrize('value',['false','true',1,False,None])
def test_truthy_strings_do_not_bypass_rubric_approval(value):
    with pytest.raises(PermissionError):guard_binary_conversion_ready(['a','b','c','d'],
        rubric_frozen=value,target_mapping_approved=True,scope_rights_confirmed=True)

@pytest.mark.parametrize('change',[
    {'timestamp':'2025-01-01T00:00:00Z'}, {'timestamp':'2026-01-02T00:00:00'},
    {'attempt_sequence':'2'}, {'source':'automatic_ai'}, {'provenance':'demo'},
    {'model_update_eligible':True}, {'rubric_version':'different-rubric'}])
def test_import_quality_rejects_chronology_and_provenance_changes(change):
    exported=good_export();exported['sessions'][1].update(change)
    assert validate_export(exported)

def test_malformed_nested_export_does_not_crash_validator():
    exported=good_export();exported['profile']=['unexpected']
    assert validate_export(exported)

def test_team_mapping_revision_is_explicit_and_unknown_revision_rejected():
    import json
    from axis7.data import ROOT
    from axis7.team_v3 import AttemptV3,resolve_event_v3
    payload=json.loads((ROOT/'examples/project-attempt-v3-multi-producer.json').read_text(encoding='utf8'))
    event=AttemptV3.model_validate(payload)
    record=resolve_event_v3(event,['pitch','rhythm','timing','articulation','fingering','score_navigation'])
    assert record['objective_mapping_version']=='cached-objectives-1-1'
    payload['objective_mapping_version']='objectives-1-2'
    with pytest.raises(ValueError):AttemptV3.model_validate(payload)

def test_two_producer_versions_cannot_duplicate_evidence_in_one_attempt():
    import json
    from axis7.data import ROOT
    from axis7.team_v3 import AttemptV3
    payload=json.loads((ROOT/'examples/project-attempt-v3-multi-producer.json').read_text(encoding='utf8'))
    repeated=copy.deepcopy(payload['observations'][0]);repeated['producer_version']='different-version'
    payload['observations'].append(repeated)
    with pytest.raises(ValueError,match='one producer version'):AttemptV3.model_validate(payload)

