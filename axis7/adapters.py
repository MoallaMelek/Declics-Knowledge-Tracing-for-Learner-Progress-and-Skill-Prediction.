"""Six independently simulated producer adapters. These are not perception models."""
from datetime import datetime,timezone
from .contracts import AttemptV2

AXIS_SKILL={1:'pitch',2:'rhythm',3:'score_navigation',4:'quality',5:'fingering',6:'technique'}

def mock_axis_event(axis,student,attempt_id,timestamp=None,success=True):
    if axis not in AXIS_SKILL:raise ValueError('Axis must be 1..6')
    # Quality and instrument/context examples are observation-only: no fabricated skill mapping.
    binary=axis not in (4,6)
    return AttemptV2.model_validate({
        'schema_version':'2.0','attempt_id':attempt_id,'student_id':student,
        'session_id':f'mock-axis-{axis}-session','exercise_id':f'mock-axis-{axis}-exercise',
        'instrument':'piano-provisional','timestamp':timestamp or datetime.now(timezone.utc).isoformat(),
        'provenance':'synthetic','rubric_version':'provisional-mock-v1',
        'producer_axis':axis,'producer_version':'mock-adapter-v2',
        'observations':[] if axis==6 else [{'skill_id':AXIS_SKILL[axis],'outcome':int(success) if binary else None,
            'score':float(success),'source_confidence':1.0,'model_update_requested':binary,
            'error_types':[] if success else [f'mock-axis-{axis}-failure']}],
        'instrument_confidence':1.0 if axis==6 else None,
        'upstream_versions':{f'axis-{axis}':'simulated-only'}})

def example_workflow(student='team-demo'):
    from datetime import timedelta
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    return [mock_axis_event(axis,student,f'team-mock:{axis}',(start+timedelta(minutes=axis)).isoformat()).model_dump(mode='json')
            for axis in range(1,7)]

if __name__=='__main__':
    import json
    print(json.dumps(example_workflow(),ensure_ascii=False,indent=2))
