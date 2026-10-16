"""Explicit adapter for the inspected existing AttemptV3 boundary.

No source-to-piano mapping and no synthetic-to-real conversion. This adapter
only collects direct team measurements; it never trains or activates a model.
"""
from .contracts import SKILL_VOCABULARY
from .team_v3 import AttemptV3
from .prospective import PracticeEvent

NAMESPACE = {name:i for i,name in enumerate(sorted(SKILL_VOCABULARY))}


def adapt_v3(event: AttemptV3, *, pseudonym, exercise_version, available_at):
    if event.provenance!='project':
        raise ValueError('Only explicitly project-observed data can enter this field adapter')
    if event.instrument not in ('piano','voice','ukulele','keyboard','other'):
        raise ValueError('Instrument requires an explicit supported contract value')
    direct = [o for o in event.observations if not o.missing and o.assessment_kind=='direct'
              and o.skill_id in NAMESPACE and o.producer_axis==SKILL_VOCABULARY[o.skill_id]['axis']]
    if not direct: raise ValueError('No direct compatible measurement; inferred/context evidence stays outside outcomes')
    # A separate event per producer preserves its version rather than inventing
    # one merged producer. All share the original session and observation time.
    result=[]
    for axis in sorted({o.producer_axis for o in direct}):
        observations=[o for o in direct if o.producer_axis==axis]
        result.append(PracticeEvent(schema_version='o08-practice-v1',event_id=f'{event.attempt_id}-axis{axis}',
            learner_id=pseudonym,instrument=event.instrument,exercise_id=event.exercise_id,
            exercise_version=exercise_version,attempt_id=f'{event.attempt_id}-axis{axis}',session_id=event.session_id,
            occurred_at=event.timestamp,available_at=available_at,assessment_source='axis_adapter',
            producer_version=observations[0].producer_version,score_definition='custom_unvalidated',
            scale='continuous_unit_interval',outcomes=[{'concept':NAMESPACE[o.skill_id],
                'value':o.outcome if o.outcome is not None else o.score} for o in observations],
            provenance='real_observation'))
    return {'namespace':'team-provisional-skills-v1','concepts':NAMESPACE,'events':result,
            'limit':'Concept IDs are local collection codes, never SingPAD concepts or approved piano mappings.'}
