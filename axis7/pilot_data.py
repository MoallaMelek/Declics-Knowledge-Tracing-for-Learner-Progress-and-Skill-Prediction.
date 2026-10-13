"""Validates exported practice collections (axis7.practice export shape) and builds a diagnostic
data-quality manifest. This module trains nothing, converts no ordinal rating to a binary label,
and invents no real experiment. It only (a) validates the shape/internal consistency of an
already-exported collection, (b) summarizes it for human review, (c) offers a learner-disjoint
split helper for a FUTURE study, and (d) gates any future binary-target conversion behind
explicit, checkable preconditions that must be supplied by a caller, never assumed true here.
"""
import random
from datetime import datetime
from collections import Counter

REQUIRED_EXPORT_KEYS={'schema_version','profile','rubric','catalog','sessions','quality',
                      'training_ready','limitations'}
RATING_VALUES={'needs_work','developing','comfortable','not_assessed'}
RARE_SKILL_THRESHOLD=3
MIN_LEARNERS_FOR_SPLIT=4

class ExportValidationError(ValueError):pass

def validate_export(export):
    """Returns a list of human-readable problems; an empty list means the export is well-formed
    (not that it is teacher-approved or training-ready -- those remain explicit false flags)."""
    if not isinstance(export,dict):return ['export must be a JSON object']
    errors=[]
    missing=REQUIRED_EXPORT_KEYS-set(export)
    if missing:errors.append(f'missing top-level keys: {sorted(missing)}')
    if export.get('schema_version')!='practice-export-1.0':
        errors.append(f"unsupported schema_version: {export.get('schema_version')!r}")
    if export.get('training_ready') is not False:
        errors.append('training_ready must be explicitly false for an unreviewed pilot export')
    rubric=export.get('rubric') or {}
    if not isinstance(rubric,dict):return errors+['rubric must be an object']
    if rubric.get('teacher_approved') is not False:
        errors.append('rubric.teacher_approved must be false until an actual teacher review happens')
    profile=export.get('profile') or {}
    if not isinstance(profile,dict):return errors+['profile must be an object']
    if not profile.get('student_id'):errors.append('profile.student_id is missing')
    if profile.get('mode') not in ('demo','local'):errors.append('profile.mode must be demo or local')
    sessions=export.get('sessions')
    if not isinstance(sessions,list):
        errors.append('sessions must be a list');sessions=[]
    seen_ids=set();prev_sequence=None;prev_time=None
    for s in sessions:
        if not isinstance(s,dict):
            errors.append('each session must be an object');continue
        attempt_id=s.get('attempt_id')
        if not attempt_id:errors.append('session missing attempt_id')
        elif attempt_id in seen_ids:errors.append(f'duplicate attempt_id in export: {attempt_id}')
        else:seen_ids.add(attempt_id)
        sequence=s.get('attempt_sequence')
        if type(sequence) is not int or sequence<1:
            errors.append('attempt_sequence must be a positive integer')
        else:
            if prev_sequence is not None and sequence<=prev_sequence:
                errors.append(f'attempt_sequence is not strictly increasing at attempt_id={attempt_id}')
            prev_sequence=sequence
        try:
            timestamp=datetime.fromisoformat(s.get('timestamp','').replace('Z','+00:00'))
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:raise ValueError('timezone missing')
            if prev_time is not None and timestamp<=prev_time:errors.append('timestamps are not strictly increasing')
            prev_time=timestamp
        except (ValueError,TypeError,AttributeError):errors.append('invalid timezone-aware practice timestamp')
        if s.get('source') not in ('self','teacher'):errors.append('unknown assessment source')
        expected='demo' if profile.get('mode')=='demo' else 'local_real'
        if s.get('provenance',expected)!=expected:errors.append('session provenance does not match profile mode')
        if s.get('model_update_eligible',False) is not False:errors.append('unreviewed ratings cannot be model-update eligible')
        if s.get('rubric_version',rubric.get('rubric_version'))!=rubric.get('rubric_version'):errors.append('mixed rubric versions in one export')
        ratings=s.get('ratings')
        if not isinstance(ratings,list) or not ratings:
            errors.append(f'session {attempt_id} has no ratings');continue
        for r in ratings:
            if not isinstance(r,dict) or r.get('rating') not in RATING_VALUES:
                errors.append(f"invalid rating value at attempt_id={attempt_id}: {r.get('rating') if isinstance(r,dict) else r!r}")
        ids=[r.get('skill_id') for r in ratings if isinstance(r,dict)]
        if any(not isinstance(k,str) or not k for k in ids) or len(set(ids))!=len(ids):
            errors.append('missing or duplicate rating skill identifiers')
    return errors

def manifest(exports):
    """Aggregates one or more already-validated exports into a diagnostic data-quality manifest.
    Raises ExportValidationError (without aggregating anything) if any export is malformed."""
    by_mode=Counter();by_source=Counter();by_rubric=Counter();skill_totals=Counter()
    all_attempt_ids=set();duplicate_ids=set();not_assessed_count=0;learners=set()
    for export in exports:
        errors=validate_export(export)
        if errors:raise ExportValidationError('; '.join(errors))
        profile=export['profile'];learners.add(profile['student_id'])
        by_mode[profile.get('mode')]+=1
        rubric_version=export['rubric'].get('rubric_version')
        for s in export['sessions']:
            by_source[s.get('source')]+=1
            by_rubric[rubric_version]+=1
            attempt_id=s.get('attempt_id')
            if attempt_id in all_attempt_ids:duplicate_ids.add(attempt_id)
            all_attempt_ids.add(attempt_id)
            for r in s.get('ratings',[]):
                if r.get('rating')=='not_assessed':
                    not_assessed_count+=1
                else:
                    skill_totals[r.get('skill_id')]+=1
    rare_skills={skill_id:count for skill_id,count in skill_totals.items() if count<RARE_SKILL_THRESHOLD}
    return {'learner_count':len(learners),'learners':sorted(learners),
        'real_vs_synthetic':dict(by_mode),'by_source':dict(by_source),'by_rubric_version':dict(by_rubric),
        'duplicate_attempt_ids':sorted(duplicate_ids),'not_assessed_count':not_assessed_count,
        'skill_observation_totals':dict(skill_totals),'rare_skills':rare_skills,
        'rare_skill_threshold':RARE_SKILL_THRESHOLD,'exports_included':len(exports)}

def learner_disjoint_split(student_ids,seed=2026):
    """Round-robins distinct learners into four disjoint, non-empty groups. Never used to turn
    ordinal ratings into a binary target by itself -- see guard_binary_conversion_ready."""
    ids=sorted(set(student_ids))
    if len(ids)<MIN_LEARNERS_FOR_SPLIT:
        raise ValueError('Need at least %d distinct learners for a disjoint train/selection/calibration/test '
                          'split, got %d'%(MIN_LEARNERS_FOR_SPLIT,len(ids)))
    shuffled=ids[:];random.Random(seed).shuffle(shuffled)
    names=['train','selection','calibration','test'];groups={name:[] for name in names}
    for i,student_id in enumerate(shuffled):groups[names[i%4]].append(student_id)
    for name in names:
        if not groups[name]:raise ValueError(f'disjoint split produced an empty {name} group')
    return groups

def guard_binary_conversion_ready(student_ids,*,rubric_frozen,target_mapping_approved,scope_rights_confirmed):
    """Raises PermissionError listing every unmet precondition; returns True only when every
    precondition is explicitly satisfied by the caller. An ordinal rating never auto-passes this
    guard by itself -- rubric_frozen/target_mapping_approved/scope_rights_confirmed must be
    supplied as true by whoever actually obtained that approval, never defaulted here."""
    unmet=[]
    if rubric_frozen is not True:unmet.append('rubric is not frozen/teacher-approved')
    if target_mapping_approved is not True:unmet.append('ordinal-to-binary target mapping is not approved')
    if scope_rights_confirmed is not True:unmet.append('data scope and usage rights are not explicitly confirmed')
    try:
        learner_disjoint_split(student_ids)
    except ValueError as err:
        unmet.append(str(err))
    if unmet:raise PermissionError('Binary-target conversion is not authorized: '+'; '.join(unmet))
    return True
