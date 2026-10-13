"""V2 team boundary. Provisional labels are not teacher-validated constructs."""
from typing import Literal
from pydantic import Field,ConfigDict,model_validator
from .schema import Attempt,SkillObservation,UnitFloat,MUSIC_SKILLS

SKILL_VOCABULARY = {
    'pitch': {'axis':1,'label':'Justesse'}, 'rhythm': {'axis':2,'label':'Rythme'},
    'timing': {'axis':2,'label':'Placement temporel'},
    'score_navigation': {'axis':3,'label':'Lecture de partition'},
    'quality': {'axis':4,'label':'Qualité observée'},
    'articulation': {'axis':4,'label':'Articulation'},
    'technique': {'axis':5,'label':'Technique observée'},
    'fingering': {'axis':5,'label':'Doigté'},
}
PROFILE='provisional-piano-v1'
SUPPORTED_RUBRICS={'provisional-mock-v1','provisional-piano-v1'}
MIN_CONFIDENCE=.6

class ObservationV2(SkillObservation):
    model_update_requested: bool = True

class AttemptV2(Attempt):
    model_config = ConfigDict(extra='forbid',json_schema_extra={
        'if':{'properties':{'producer_axis':{'const':6}}},
        'else':{'required':['observations'],'properties':{'observations':{'minItems':1}}}})
    schema_version: Literal['2.0'] = '2.0'
    model_profile: Literal['provisional-piano-v1'] = PROFILE
    producer_axis: Literal[1,2,3,4,5,6]
    producer_version: str = Field(min_length=1,max_length=80)
    observations: list[ObservationV2] = Field(default_factory=list,max_length=500)
    quality_score: UnitFloat | None = None
    alignment_score: UnitFloat | None = None
    instrument_confidence: UnitFloat | None = None

    @model_validator(mode='after')
    def producer_payload(self):
        if self.producer_axis!=6 and not self.observations:
            raise ValueError('This producer requires a skill observation; axis 6 may send instrument context only')
        return self

def resolve_event(event,vocabulary):
    from .schema import to_record
    if isinstance(event,AttemptV2):
        unknown={o.skill_id for o in event.observations}-set(SKILL_VOCABULARY)
        if unknown:raise ValueError('Unknown canonical skills: '+', '.join(sorted(unknown)))
        mapped=event.model_copy(update={'observations':[o for o in event.observations if o.skill_id in vocabulary]})
        record=to_record(mapped,vocabulary)
        record['obs']=[]
        for o in event.observations:
            reason=('observation_only' if not o.model_update_requested else
                    'missing_binary_outcome' if o.outcome is None else
                    'unmapped_to_saved_model' if o.skill_id not in vocabulary else
                    'unsupported_rubric' if event.rubric_version not in SUPPORTED_RUBRICS else
                    'missing_source_confidence' if o.source_confidence is None else
                    'low_source_confidence' if o.source_confidence<MIN_CONFIDENCE else None)
            record['obs'].append({'k':vocabulary.index(o.skill_id) if o.skill_id in vocabulary else None,
                'skill_id':o.skill_id,'y':o.outcome,'score':o.score,'confidence':o.source_confidence,
                'errors':o.error_types,'evidence_id':o.evidence_id,'eligible':reason is None,
                'eligibility_reason':reason})
        record['producer']={'axis':event.producer_axis,'version':event.producer_version}
        record['signals'].update(quality_score=event.quality_score,alignment_score=event.alignment_score,
                                instrument_confidence=event.instrument_confidence)
    else:
        record=to_record(event,vocabulary)
        for o in record['obs']:
            o['eligible']=o['y'] is not None
            o['eligibility_reason']=None if o['eligible'] else 'missing_binary_outcome'
    record['schema_version']=event.schema_version
    record['model_profile']=PROFILE
    record['update_policy']='binary-evidence-v2' if isinstance(event,AttemptV2) else 'legacy-binary-v1'
    record['request']=event.model_dump(mode='json')
    return record

def registry():
    return {'contract_versions':['1.0','2.0'],'model_profile':PROFILE,
        'skills':SKILL_VOCABULARY,'model_skills':MUSIC_SKILLS,
        'supported_rubrics':sorted(SUPPORTED_RUBRICS),'minimum_source_confidence':MIN_CONFIDENCE,
        'taxonomy_status':'provisional_not_teacher_validated',
        'training_provenance':'synthetic_music_only','unknown_rubric_policy':'persist_without_model_update',
        'instrument_recognition':'context_only_not_a_learner_competency'}

if __name__=='__main__':
    import json
    from .data import ROOT
    path=ROOT/'schemas/attempt-v2.schema.json'
    path.write_text(json.dumps(AttemptV2.model_json_schema(),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(path)
