"""V3 team evidence boundary: one atomic attempt whose observations each carry their OWN
producer_axis/producer_version (unlike v2's contracts.AttemptV2, which is one producer per
attempt). Builds per-producer subsets, resolves each through the EXISTING, unmodified
contracts.resolve_event/contracts.AttemptV2 machinery, then merges the results into one stored
record via the existing storage.append_event -- using the single attempt timestamp already on
the envelope, never inventing per-producer timestamps.

Objective-id mapping below is CACHED from a prior reading of 'Declic_Deep_Learning_Objectives-1-1'.
Version '1-2' was not available to this module; nothing from it is assumed, guessed, or read as if
it had been seen. If the team's objectives document changes this mapping, update AXIS_OBJECTIVES /
AXIS_CONTEXT_OBJECTIVES here (and docs/TEAM_PHASE3.md) explicitly -- do not silently reinterpret it.
"""
from datetime import datetime
from typing import Literal
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,ConfigDict,Field,StrictBool,StrictInt,field_validator,model_validator
from .schema import UnitFloat
from .contracts import SKILL_VOCABULARY,PROFILE

router=APIRouter()

# Axis -> the one objective it may claim a DIRECT/inferred/recommendation skill observation for.
AXIS_OBJECTIVES={1:'O01',2:'O02',3:'O03',4:'O07',5:'O05',6:'O10',7:'O09'}
# Axis -> an ADDITIONAL objective that axis may only submit as explicitly bounded, context-only evidence.
AXIS_CONTEXT_OBJECTIVES={3:'O04',4:'O08',5:'O06'}
# The explicitly bounded, non-canonical identifiers a context-only objective must use.
OBJECTIVE_CONTEXT_SKILL={'O04':'omr_metadata','O08':'corrective_feedback','O06':'posture_context',
                         'O10':'instrument_context'}
UNSUPPORTED_SKILL_IDS=set(OBJECTIVE_CONTEXT_SKILL.values())
CANONICAL_SKILLS=set(SKILL_VOCABULARY)

class ObservationV3(BaseModel):
    model_config=ConfigDict(extra='forbid')
    skill_id:Literal['pitch','rhythm','timing','score_navigation','quality','articulation',
        'technique','fingering','omr_metadata','corrective_feedback','posture_context','instrument_context']
    producer_axis:StrictInt=Field(ge=1,le=7)
    producer_version:str=Field(min_length=1,max_length=80)
    objective_id:str=Field(min_length=1,max_length=10)
    assessment_kind:Literal['direct','inferred','recommendation','context']
    outcome:StrictInt|None=Field(default=None,ge=0,le=1)
    score:UnitFloat|None=None
    source_confidence:UnitFloat|None=None
    missing:StrictBool=False
    reference_compared:StrictBool|None=None
    error_types:list[str]=Field(default_factory=list,max_length=20)
    evidence_id:str|None=None

    @field_validator('outcome')
    @classmethod
    def binary(cls,v):
        if v is not None and v not in (0,1):raise ValueError('outcome must be 0 or 1')
        return v

    @model_validator(mode='after')
    def coherent(self):
        if self.missing:
            if self.outcome is not None or self.score is not None:
                raise ValueError('missing=true observations must not also carry an outcome or score')
        elif self.outcome is None and self.score is None:
            raise ValueError('a non-missing observation needs an outcome or a scaled score, or missing=true')
        direct=AXIS_OBJECTIVES.get(self.producer_axis)
        context=AXIS_CONTEXT_OBJECTIVES.get(self.producer_axis)
        valid={o for o in (direct,context) if o}
        if self.objective_id not in valid:
            raise ValueError(f"objective_id {self.objective_id!r} is not recognized for producer_axis "
                f"{self.producer_axis} under the cached Declic_Deep_Learning_Objectives-1-1 mapping "
                "(version 1-2 was unavailable and is not assumed)")
        if self.objective_id in OBJECTIVE_CONTEXT_SKILL:
            expected=OBJECTIVE_CONTEXT_SKILL[self.objective_id]
            if self.skill_id!=expected:
                raise ValueError(f'objective {self.objective_id} is context-only and must use skill_id {expected!r}')
        elif self.skill_id not in CANONICAL_SKILLS:
            raise ValueError('Unknown canonical skill_id, and not one of the explicitly bounded unsupported identifiers')
        if self.producer_axis==7 and self.assessment_kind=='direct':
            raise ValueError('Axis 7 cannot submit a direct observation; only inferred, recommendation or context')
        if (self.producer_axis==1 and self.skill_id=='pitch' and self.assessment_kind=='direct'
                and not self.missing and not self.reference_compared):
            raise ValueError('A direct pitch claim from axis 1 requires an explicit reference comparison '
                             '(reference_compared=true); raw transcribed pitch alone is not correctness')
        return self

class AttemptV3(BaseModel):
    model_config=ConfigDict(extra='forbid')
    schema_version:Literal['3.0']='3.0'
    objective_mapping_version:Literal['cached-objectives-1-1']='cached-objectives-1-1'
    attempt_id:str=Field(min_length=1,max_length=120)
    student_id:str=Field(min_length=1,max_length=100)
    session_id:str=Field(min_length=1,max_length=100)
    exercise_id:str=Field(min_length=1,max_length=100)
    instrument:str=Field(min_length=1,max_length=50)
    timestamp:datetime
    provenance:Literal['synthetic','project','public']
    rubric_version:str=Field(min_length=1,max_length=80)
    observations:list[ObservationV3]=Field(min_length=1,max_length=500)

    @model_validator(mode='after')
    def no_duplicate_producer_skill(self):
        seen=set();versions={}
        for o in self.observations:
            if o.producer_axis in versions and versions[o.producer_axis]!=o.producer_version:
                raise ValueError('one producer version per axis is required within an atomic attempt')
            versions[o.producer_axis]=o.producer_version
            key=(o.producer_axis,o.skill_id)
            if key in seen:
                raise ValueError(f'duplicate observation for producer_axis={o.producer_axis}, '
                    f'producer_version={o.producer_version!r}, skill_id={o.skill_id!r}')
            seen.add(key)
        return self

    @field_validator('timestamp',mode='before')
    @classmethod
    def canonical_timestamp(cls,v):
        if not isinstance(v,(str,datetime)):raise ValueError('timestamp must be an ISO 8601 string with timezone')
        return v

    @field_validator('timestamp')
    @classmethod
    def tz(cls,v):
        if v.tzinfo is None or v.utcoffset() is None:raise ValueError('timestamp requires a timezone')
        return v

def resolve_event_v3(event,vocabulary):
    """Groups observations by (producer_axis, producer_version), resolves each canonical-skill
    subset through the existing v2 contract, and folds explicitly bounded / missing observations
    in directly (they are never eligible, so no model-affecting logic is bypassed by skipping v2)."""
    from .contracts import AttemptV2,resolve_event as resolve_v2
    order_map={};canonical_groups={}
    all_producers={}
    for o in event.observations:all_producers.setdefault((o.producer_axis,o.producer_version),None)
    for i,o in enumerate(event.observations):
        if o.skill_id in UNSUPPORTED_SKILL_IDS:reason='context_only_objective'
        elif o.missing:reason='explicit_missing_measurement'
        elif o.producer_axis==7:reason='axis7_self_referential_not_model_update_eligible'
        else:reason=None
        if reason is not None:
            order_map[i]={'k':vocabulary.index(o.skill_id) if o.skill_id in vocabulary else None,
                'skill_id':o.skill_id,'y':o.outcome,'score':o.score,'confidence':o.source_confidence,
                'errors':o.error_types,'evidence_id':o.evidence_id,'eligible':False,'eligibility_reason':reason,
                'objective_id':o.objective_id,'assessment_kind':o.assessment_kind,
                'producer_axis':o.producer_axis,'producer_version':o.producer_version}
        else:
            canonical_groups.setdefault((o.producer_axis,o.producer_version),[]).append((i,o))
    producers=[{'axis':axis,'version':version} for axis,version in all_producers]
    for (axis,version),items in canonical_groups.items():
        sub=AttemptV2.model_validate({'schema_version':'2.0','attempt_id':event.attempt_id,
            'student_id':event.student_id,'session_id':event.session_id,'exercise_id':event.exercise_id,
            'instrument':event.instrument,'timestamp':event.timestamp.isoformat(),'provenance':event.provenance,
            'rubric_version':event.rubric_version,'producer_axis':axis,'producer_version':version,
            'observations':[{'skill_id':o.skill_id,'outcome':o.outcome,'score':o.score,
                'source_confidence':o.source_confidence,'error_types':o.error_types,'evidence_id':o.evidence_id,
                'model_update_requested':o.assessment_kind=='direct'} for _,o in items]})
        sub_record=resolve_v2(sub,vocabulary)
        for (i,o),obs in zip(items,sub_record['obs']):
            obs['objective_id']=o.objective_id;obs['assessment_kind']=o.assessment_kind
            obs['producer_axis']=o.producer_axis;obs['producer_version']=o.producer_version
            order_map[i]=obs
    merged_obs=[order_map[i] for i in range(len(event.observations))]
    upstream_versions={}
    for p in producers:upstream_versions[f"axis-{p['axis']}"]=p['version']
    return {'student':event.student_id,'id':event.attempt_id,'session':event.session_id,
        'exercise':event.exercise_id,'instrument':event.instrument,'timestamp':event.timestamp.isoformat(),
        'order':event.timestamp.timestamp(),'provenance':event.provenance,'rubric':event.rubric_version,
        'obs':merged_obs,
        'signals':{'note_accuracy':None,'rhythm_score':None,'timing_mae_ms':None,'gesture_metrics':{}},
        'upstream_versions':upstream_versions,'schema_version':'3.0','model_profile':PROFILE,
        'objective_mapping_version':event.objective_mapping_version,
        'update_policy':'atomic-multi-producer-v3','producers':producers,
        'request':event.model_dump(mode='json')}

@router.post('/api/v3/evidence')
def ingest_v3(a:AttemptV3,model_id:str|None=None,policy:Literal['balanced','weakest']='balanced'):
    from . import server
    from .storage import append_event,EventConflict
    if a.provenance=='public':
        raise HTTPException(422,'Do not mix benchmark observations into the music stream')
    with server.lock:
        e=server.engine('music-mock')
        if a.instrument not in ('piano','piano-provisional'):
            raise HTTPException(422,'This provisional demo is scoped to piano only')
        if model_id is not None and model_id not in e.predictors:
            raise HTTPException(422,'Unknown saved model')
        record=resolve_event_v3(a,e.meta['skills'])
        fixture_ids={r['id'] for v in e.learners.values() for r in v}
        try:
            stored,replayed=append_event(server.DB,record,e.learners.get(a.student_id,[]),fixture_ids)
        except EventConflict as err:
            raise HTTPException(409,str(err)) from err
        except ValueError as err:
            raise HTTPException(422,str(err)) from err
        result={'status':'accepted','attempt_id':a.attempt_id,'idempotent_replay':replayed,'record':stored,
            'contract':'v3','producers':stored.get('producers',[]),
            'warning':'Synthetic-trained model; musical transfer remains unvalidated. Observation-only, '
                      'inferred, recommendation and axis7 self-referential evidence never silently become '
                      'training labels.',
            'eligible_observations':sum(bool(o.get('eligible')) for o in stored['obs']),
            'forecast_status':'ready','twin':None}
        try:
            result['twin']=e.snapshot(a.student_id,server.history(e,a.student_id),model_id=model_id,policy=policy)
        except Exception:
            result.update(forecast_status='unavailable',
                forecast_error={'code':'INFERENCE_UNAVAILABLE','retryable':True})
        return result

if __name__=='__main__':
    import json
    from .data import ROOT
    path=ROOT/'schemas/attempt-v3.schema.json'
    path.write_text(json.dumps(AttemptV3.model_json_schema(),ensure_ascii=False,indent=2,allow_nan=False)+'\n',
                     encoding='utf-8')
    print(path)
