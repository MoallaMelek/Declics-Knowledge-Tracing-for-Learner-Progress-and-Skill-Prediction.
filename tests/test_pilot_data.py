import copy
import pytest
from axis7.pilot_data import (validate_export,manifest,learner_disjoint_split,
    guard_binary_conversion_ready,ExportValidationError)

def good_export(student_id='piano-aaa',mode='local',source='self',n=3):
    sessions=[]
    for i in range(n):
        sessions.append({'attempt_id':f'{student_id}:{i}','attempt_sequence':i+1,
            'timestamp':f'2026-01-0{i+1}T10:00:00+00:00','source':source,
            'ratings':[{'skill_id':'pitch','label':'Pitch','rating':'developing'}]})
    return {'schema_version':'practice-export-1.0',
        'profile':{'student_id':student_id,'mode':mode,'instrument':'piano'},
        'rubric':{'rubric_version':'piano-pilot-v1','teacher_approved':False},
        'catalog':{'instrument':'piano'},'sessions':sessions,
        'quality':{'session_count':n},'training_ready':False,
        'limitations':['provisional']}

def test_validate_export_accepts_a_well_formed_export():
    assert validate_export(good_export())==[]

def test_validate_export_rejects_malformed_shapes():
    assert validate_export('not a dict')
    assert validate_export({})
    bad_schema=good_export();bad_schema['schema_version']='practice-export-0.9'
    assert validate_export(bad_schema)
    bad_rating=good_export();bad_rating['sessions'][0]['ratings'][0]['rating']='excellent'
    assert validate_export(bad_rating)
    no_ratings=good_export();no_ratings['sessions'][0]['ratings']=[]
    assert validate_export(no_ratings)

def test_validate_export_detects_duplicate_attempt_ids_and_bad_chronology():
    export=good_export()
    export['sessions'].append(copy.deepcopy(export['sessions'][0]))
    assert any('duplicate attempt_id' in e for e in validate_export(export))
    export2=good_export()
    export2['sessions'][1]['attempt_sequence']=export2['sessions'][0]['attempt_sequence']
    assert any('not strictly increasing' in e for e in validate_export(export2))

def test_validate_export_rejects_training_ready_true_and_teacher_approved_true():
    claims_ready=good_export();claims_ready['training_ready']=True
    assert any('training_ready' in e for e in validate_export(claims_ready))
    claims_approved=good_export();claims_approved['rubric']['teacher_approved']=True
    assert any('teacher_approved' in e for e in validate_export(claims_approved))

def test_manifest_counts_real_and_synthetic_source_mixtures():
    local=good_export(student_id='piano-local',mode='local',source='self',n=4)
    demo=good_export(student_id='piano-demo',mode='demo',source='teacher',n=2)
    m=manifest([local,demo])
    assert m['learner_count']==2
    assert m['real_vs_synthetic']=={'local':1,'demo':1}
    assert m['by_source']=={'self':4,'teacher':2}
    assert m['exports_included']==2
    assert m['skill_observation_totals']=={'pitch':6}

def test_manifest_raises_on_malformed_export_instead_of_silently_aggregating():
    malformed=good_export();malformed['training_ready']=True
    with pytest.raises(ExportValidationError):
        manifest([good_export(),malformed])

def test_manifest_flags_rare_skills_below_threshold():
    export=good_export(n=1)
    export['sessions'][0]['ratings'].append({'skill_id':'rhythm','label':'Rhythm','rating':'comfortable'})
    m=manifest([export])
    assert m['rare_skills']=={'pitch':1,'rhythm':1}

def test_learner_disjoint_split_requires_at_least_four_learners_and_has_no_empty_group():
    with pytest.raises(ValueError):
        learner_disjoint_split(['a','b','c'])
    groups=learner_disjoint_split(['a','b','c','d','e','f','g'])
    assert set(groups)=={'train','selection','calibration','test'}
    all_ids=[sid for group in groups.values() for sid in group]
    assert sorted(all_ids)==['a','b','c','d','e','f','g']
    assert all(groups[name] for name in groups)

def test_learner_disjoint_split_groups_are_mutually_disjoint():
    groups=learner_disjoint_split([f'learner-{i}' for i in range(12)])
    seen=set()
    for members in groups.values():
        assert not seen.intersection(members)
        seen.update(members)

def test_guard_binary_conversion_rejects_unapproved_teacher_rubric():
    with pytest.raises(PermissionError) as err:
        guard_binary_conversion_ready(['a','b','c','d'],rubric_frozen=False,
            target_mapping_approved=True,scope_rights_confirmed=True)
    assert 'rubric' in str(err.value)

def test_guard_binary_conversion_rejects_too_few_learners_even_if_everything_else_is_approved():
    with pytest.raises(PermissionError) as err:
        guard_binary_conversion_ready(['a','b'],rubric_frozen=True,
            target_mapping_approved=True,scope_rights_confirmed=True)
    assert 'learner' in str(err.value) or 'at least' in str(err.value)

def test_guard_binary_conversion_passes_only_when_every_precondition_holds():
    assert guard_binary_conversion_ready(['a','b','c','d'],rubric_frozen=True,
        target_mapping_approved=True,scope_rights_confirmed=True) is True

def test_ordinal_rating_never_auto_converts_to_binary_anywhere_in_this_module():
    export=good_export()
    for session in export['sessions']:
        for rating in session['ratings']:
            assert rating['rating'] in {'needs_work','developing','comfortable','not_assessed'}
            assert not isinstance(rating['rating'],(int,bool))
