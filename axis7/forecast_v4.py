"""v4 future-performance forecast query: POST /api/v4/forecast.

This is a read-only query over EXISTING stored history (team_v3/v2/v1 events, or
the separate practice notebook), the EXISTING frozen predictors in inference.py,
and the EXISTING v3 producer/provenance metadata. It trains nothing, loads no
checkpoint outside the already-served registry, and never fabricates an
exercise-skill conditioning the model was not trained to answer.

Only observations with timestamp strictly earlier than `as_of` are ever visible
to a prediction (equal-to-cutoff is excluded, matching the "no leakage" causal
contract already enforced elsewhere in this project).

Default behaviour is to abstain (see forecast_policy.POLICY_VERSION): the
knowledge-tracing models here are trained on synthetic piano data only, so no
musical correctness claim is shown by default regardless of how much history
exists. `include_research_predictions=true` may expose the frozen model's
actual probabilities, labeled `research_only` and `never_validated_for_real_music`,
and only when every piece of conditioning evidence in the prefix is itself
synthetic (see forecast_policy.evaluate's research_eligible rule).
"""
from collections import Counter
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

from .contracts import PROFILE, SUPPORTED_RUBRICS
from .eligibility import eligible
from .forecast_policy import POLICY_VERSION, RECENT_CONFIDENCE_WINDOW, PolicyInputs, evaluate
from .inference import uses_items
from .schema import UnitFloat

router = APIRouter()

LIMITATIONS = [
    "La prévision ne mesure pas une maîtrise psychologique ni un bénéfice pédagogique.",
    "Les modèles sont entraînés uniquement sur des données simulées ; aucune validité prédictive sur de la "
    "musique réelle n'a été établie.",
    "Le mode recherche démontre le modèle gelé sur des données explicitement synthétiques ; ce n'est jamais "
    "une validation sur de la musique réelle.",
]


class ForecastV4Request(BaseModel):
    model_config = ConfigDict(extra='forbid')
    student_id: str = Field(min_length=1, max_length=100)
    instrument: str = Field(default='piano', min_length=1, max_length=50)
    exercise_id: str | None = Field(default=None, min_length=1, max_length=100)
    model_id: str | None = Field(default=None, min_length=1, max_length=120)
    as_of: datetime
    evidence_source: Literal['team_v3', 'practice']
    include_research_predictions: StrictBool = False

    @field_validator('as_of', mode='before')
    @classmethod
    def canonical_timestamp(cls, v):
        if not isinstance(v, (str, datetime)):
            raise ValueError('as_of must be an ISO 8601 string with timezone')
        return v

    @field_validator('as_of')
    @classmethod
    def tz(cls, v):
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError('as_of requires a timezone')
        return v


class ForecastV4Response(BaseModel):
    model_config = ConfigDict(extra='forbid')
    response_version: Literal['4.0'] = '4.0'
    student_id: str
    instrument: str
    exercise_id: str | None
    model_id: str | None
    as_of: datetime
    evidence_source: Literal['team_v3', 'practice']
    status: Literal['abstained', 'research_only']
    reason_code: str
    user_message: str
    policy_version: Literal['phase4-gate-v1']
    model_profile: str | None
    model_version: str | None
    training_provenance: Literal['synthetic'] | None
    conditioning: Literal['exercise', 'generic_skill'] | None
    evaluated_scope: str
    probabilities: dict[str, UnitFloat] | None
    prefix_count: int
    eligible_attempt_count: int = 0
    excluded_future_count: int
    evidence_ids: list[str]
    evidence_provenance_counts: dict[str, int]
    history_instrument_counts: dict[str, int] = Field(default_factory=dict)
    assessment_source_counts: dict[str, int] = Field(default_factory=dict)
    known_confidence_count: int = 0
    unknown_confidence_count: int = 0
    calibrated_uncertainty_available: StrictBool = False
    accepted_observations: int
    omitted_observations: int
    omitted_reasons: dict[str, int]
    never_validated_for_real_music: StrictBool
    limitations: list[str]


def _team_v3_forecast(body: ForecastV4Request) -> ForecastV4Response:
    from . import server
    with server.lock:
        e = server.engine('music-mock')
        if body.model_id is not None and body.model_id not in e.predictors:
            raise HTTPException(422, 'Unknown saved model')
        rows = sorted(server.history(e, body.student_id), key=lambda r: r['order'])
        as_of_ts = body.as_of.timestamp()
        prefix = [r for r in rows if r['order'] < as_of_ts]
        excluded_future_count = len(rows) - len(prefix)

        rid = body.model_id or e.default
        predictor = e.predictors[rid]
        item_known = server.item_supported(predictor, body.exercise_id)
        requires_item_check = item_known is not None

        rubrics = frozenset(r['rubric'] for r in prefix)
        all_obs = [o for r in prefix for o in r['obs']]
        eligible_obs = [o for o in all_obs if eligible(o)]
        eligible_attempts = sum(any(eligible(o) for o in r['obs']) for r in prefix)
        omitted = [o for o in all_obs if not eligible(o)]
        omitted_reasons = Counter(o.get('eligibility_reason') or 'unspecified' for o in omitted)
        recent_confidences = tuple(o.get('confidence') for o in eligible_obs[-RECENT_CONFIDENCE_WINDOW:])
        provenance_counts = dict(Counter(r['provenance'] for r in prefix))

        decision = evaluate(PolicyInputs(instrument=body.instrument, rubrics=rubrics,
            supported_rubrics=frozenset(SUPPORTED_RUBRICS), requires_item_check=requires_item_check,
            item_known=item_known, prefix_count=len(prefix), eligible_observations=len(eligible_obs),
            recent_confidences=recent_confidences, provenance_counts=provenance_counts,
            eligible_attempts=eligible_attempts,
            history_instruments=frozenset(r.get('instrument','unknown') for r in prefix)))

        conditioning = 'exercise' if (body.exercise_id and uses_items(predictor)) else 'generic_skill'
        status = 'abstained'
        probabilities = None
        if (decision.reason_code == 'model_not_validated_for_real_music'
                and body.include_research_predictions and decision.research_eligible):
            status = 'research_only'
            if rid.startswith('v2:'):
                probs = predictor.probabilities(prefix, exercise_id=body.exercise_id)[-1]
            else:
                probs = predictor.probabilities(prefix)[-1]
            probabilities = dict(zip(e.meta['skills'], map(float, probs)))

        evaluated_scope = ('observed_skill_given_attempted_exercise' if status == 'research_only' and conditioning == 'exercise'
            else 'skill_only_forecast' if status == 'research_only' else 'abstained_not_evaluated')

        message = ('Simulation : prévision du modèle gelé à partir des seules observations simulées antérieures. '
                   'Ce résultat ne valide pas une prévision musicale réelle.' if status == 'research_only'
                   else decision.user_message)
        return ForecastV4Response(student_id=body.student_id, instrument=body.instrument,
            exercise_id=body.exercise_id, model_id=rid, as_of=body.as_of, evidence_source='team_v3',
            status=status, reason_code=decision.reason_code, user_message=message,
            policy_version=POLICY_VERSION, model_profile=PROFILE,
            model_version=getattr(predictor, 'serving_implementation_version',
                                   predictor.config.get('implementation_version', 'legacy-v1')),
            training_provenance='synthetic', conditioning=conditioning, evaluated_scope=evaluated_scope,
            probabilities=probabilities, prefix_count=len(prefix), excluded_future_count=excluded_future_count,
            eligible_attempt_count=eligible_attempts,
            evidence_ids=[r['id'] for r in prefix], evidence_provenance_counts=provenance_counts,
            history_instrument_counts=dict(Counter(r.get('instrument','unknown') for r in prefix)),
            known_confidence_count=sum(o.get('confidence') is not None for o in all_obs),
            unknown_confidence_count=sum(o.get('confidence') is None for o in all_obs),
            accepted_observations=len(eligible_obs), omitted_observations=len(omitted),
            omitted_reasons=dict(omitted_reasons), never_validated_for_real_music=True,
            limitations=LIMITATIONS)


def _practice_forecast(body: ForecastV4Request) -> ForecastV4Response:
    from .practice import RUBRIC_VERSION as PRACTICE_RUBRIC_VERSION, _load_sessions, _open, _profile
    conn = _open()
    try:
        _profile(conn, body.student_id)
        sessions = _load_sessions(conn, body.student_id)
    finally:
        conn.close()
    prefix = [s for s in sessions if datetime.fromisoformat(s['timestamp']) < body.as_of]
    excluded_future_count = len(sessions) - len(prefix)
    all_ratings = [r for s in prefix for r in s['ratings'] if r['rating'] != 'not_assessed']
    omitted_reasons = Counter('ordinal_rating_not_binary_outcome' for _ in all_ratings)

    decision = evaluate(PolicyInputs(instrument=body.instrument, rubrics=frozenset({PRACTICE_RUBRIC_VERSION}),
        supported_rubrics=frozenset(SUPPORTED_RUBRICS), requires_item_check=False, item_known=None,
        prefix_count=len(prefix), eligible_observations=0, recent_confidences=(), provenance_counts={}))

    return ForecastV4Response(student_id=body.student_id, instrument=body.instrument,
        exercise_id=body.exercise_id, model_id=None, as_of=body.as_of, evidence_source='practice',
        status='abstained', reason_code=decision.reason_code, user_message=decision.user_message,
        policy_version=POLICY_VERSION, model_profile=None, model_version=None, training_provenance=None,
        conditioning=None, evaluated_scope='practice_notebook_no_validated_model', probabilities=None,
        prefix_count=len(prefix), excluded_future_count=excluded_future_count,
        evidence_ids=[s['attempt_id'] for s in prefix],
        history_instrument_counts={'piano':len(prefix)} if prefix else {},
        evidence_provenance_counts=dict(Counter(s['provenance'] for s in prefix)),
        assessment_source_counts=dict(Counter(s['source'] for s in prefix)),
        known_confidence_count=sum(s.get('confidence') is not None for s in prefix),
        unknown_confidence_count=sum(s.get('confidence') is None for s in prefix),
        accepted_observations=0, omitted_observations=len(all_ratings), omitted_reasons=dict(omitted_reasons),
        never_validated_for_real_music=True, limitations=LIMITATIONS)


@router.post('/api/v4/forecast', response_model=ForecastV4Response)
def forecast_v4(body: ForecastV4Request):
    if body.model_id is not None and body.evidence_source != 'team_v3':
        raise HTTPException(422, 'model_id is only applicable when evidence_source is "team_v3"')
    if body.evidence_source == 'team_v3':
        return _team_v3_forecast(body)
    return _practice_forecast(body)


if __name__ == '__main__':
    import json
    from .data import ROOT
    path = ROOT / 'schemas/forecast-v4.schema.json'
    path.write_text(json.dumps({'request': ForecastV4Request.model_json_schema(),
        'response': ForecastV4Response.model_json_schema()}, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print(path)
