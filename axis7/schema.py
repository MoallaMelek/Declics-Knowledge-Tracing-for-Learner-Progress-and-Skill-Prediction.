"""Versioned canonical observation boundary. No media recognition lives here."""
from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

MUSIC_SKILLS = ["pitch", "rhythm", "timing", "articulation", "fingering", "score_navigation"]
MUSIC_LABELS = ["Justesse", "Rythme", "Placement temporel", "Articulation", "Doigté", "Lecture de partition"]

# NaN and infinities are not valid measurements; they would also break strict JSON storage.
UnitFloat = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False,strict=True)]
NonNegativeFloat = Annotated[float, Field(ge=0, allow_inf_nan=False,strict=True)]
FiniteFloat = Annotated[float, Field(allow_inf_nan=False,strict=True)]

class SkillObservation(BaseModel):
    # Unknown keys are rejected: a misspelled field must not be silently dropped.
    model_config = ConfigDict(extra="forbid", json_schema_extra={"anyOf": [
        {"required": ["outcome"], "properties": {"outcome": {"type": "integer", "minimum": 0, "maximum": 1}}},
        {"required": ["score"], "properties": {"score": {"type": "number", "minimum": 0, "maximum": 1}}}
    ]})
    skill_id: str = Field(min_length=1, max_length=80)
    outcome: StrictInt | None = Field(default=None, ge=0, le=1)
    score: UnitFloat | None = None
    source_confidence: UnitFloat | None = None
    error_types: list[str] = Field(default_factory=list, max_length=20)
    evidence_id: str | None = None

    @model_validator(mode="after")
    def has_measurement(self):
        if self.outcome is None and self.score is None:
            raise ValueError("each observation needs an outcome or a scaled score")
        return self

    @field_validator("outcome")
    @classmethod
    def binary(cls, v):
        if v is not None and v not in (0,1): raise ValueError("outcome must be 0 or 1")
        return v

class Attempt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    attempt_id: str = Field(min_length=1, max_length=120)
    student_id: str = Field(min_length=1, max_length=100)
    session_id: str = Field(min_length=1, max_length=100)
    exercise_id: str = Field(min_length=1, max_length=100)
    instrument: str = Field(min_length=1, max_length=50)
    timestamp: datetime
    provenance: Literal["synthetic", "project", "public"]
    rubric_version: str = Field(min_length=1, max_length=80)
    observations: list[SkillObservation] = Field(min_length=1, max_length=500)
    note_accuracy: UnitFloat | None = None
    rhythm_score: UnitFloat | None = None
    timing_mae_ms: NonNegativeFloat | None = None
    gesture_metrics: dict[str, FiniteFloat] = Field(default_factory=dict)
    upstream_versions: dict[str, str] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def timezone(cls,v):
        if v.tzinfo is None or v.utcoffset() is None: raise ValueError("timestamp requires a timezone")
        return v

    @field_validator('timestamp',mode='before')
    @classmethod
    def canonical_timestamp(cls,v):
        if not isinstance(v,(str,datetime)):
            raise ValueError('timestamp must be an ISO 8601 string with timezone')
        return v

    @model_validator(mode="after")
    def evidence(self):
        if any(o.outcome is None and o.score is None for o in self.observations):
            raise ValueError("each observation needs a binary outcome or an explicitly scaled score")
        return self

def to_record(a: Attempt, vocabulary: list[str]) -> dict:
    unknown={o.skill_id for o in a.observations} - set(vocabulary)
    if unknown: raise ValueError("Unmapped skills: " + ", ".join(sorted(unknown)))
    return {
        "student": a.student_id, "id": a.attempt_id, "session": a.session_id,
        "exercise": a.exercise_id, "instrument": a.instrument,
        "timestamp": a.timestamp.isoformat(), "order": a.timestamp.timestamp(),
        "provenance": a.provenance, "rubric": a.rubric_version,
        "obs": [{"k":vocabulary.index(o.skill_id),"y":o.outcome,"score":o.score,
                 "confidence":o.source_confidence,"errors":o.error_types,"evidence_id":o.evidence_id}
                for o in a.observations],
        "signals": {"note_accuracy": a.note_accuracy, "rhythm_score":a.rhythm_score,
                    "timing_mae_ms":a.timing_mae_ms,"gesture_metrics":a.gesture_metrics},
        "upstream_versions":a.upstream_versions,
    }

def write_schema(path):
    """Writes the published JSON Schema generated directly from the validation model."""
    import json
    from pathlib import Path
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(Attempt.model_json_schema(),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return p

if __name__=='__main__':
    from .data import ROOT
    print(write_schema(ROOT/'schemas/attempt-v1.schema.json'))
