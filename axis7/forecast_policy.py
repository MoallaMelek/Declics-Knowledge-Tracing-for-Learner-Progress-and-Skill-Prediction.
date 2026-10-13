"""Pure phase4-gate-v1 abstention policy for /api/v4/forecast.

No I/O, no FastAPI, no model loading here -- only a deterministic decision over
counts and flags that forecast_v4.py computes from real stored history. The
minimum counts below are provisional safeguards chosen for this phase, not
empirically optimized thresholds; they exist so the gate has a reproducible,
inspectable shape instead of an implicit one.

The terminal reason `model_not_validated_for_real_music` is always reachable and
is deliberately the last check: the current knowledge-tracing models are trained
on synthetic piano data only, so no musical correctness claim is ever upgraded
to a confident, default-visible prediction. `research_eligible` on that terminal
decision additionally requires every piece of conditioning evidence to be
synthetic -- project-provenance (real) evidence must never be used to produce
even a labeled research-only demonstration, since that would imply validated
real-music predictive ability we have not established.
"""
from dataclasses import dataclass, field

POLICY_VERSION = 'phase4-gate-v1'

MIN_HISTORY_ATTEMPTS = 3
MIN_ELIGIBLE_OBSERVATIONS = 3
# Deliberately stricter than contracts.MIN_CONFIDENCE (0.6): that ingestion-time bar already
# decides whether an observation is eligible to update a model at all, so anything reaching this
# gate as "eligible" already cleared it. This forecast-only bar is a second, stricter check on
# whether recent eligible evidence is confident enough to also support showing a demonstration.
MIN_CONFIDENCE = 0.75
RECENT_CONFIDENCE_WINDOW = 5

SUPPORTED_INSTRUMENTS = frozenset({'piano', 'piano-provisional'})

REASON_MESSAGES = {
    'unsupported_instrument': "Cet instrument n'est pas pris en charge par ce modèle pour le moment.",
    'unsupported_rubric': "La grille d'évaluation de ces observations n'est pas compatible avec un modèle validé.",
    'unknown_exercise': "Cet exercice est inconnu du modèle ; nous ne fabriquons pas de conditionnement pour lui.",
    'insufficient_history': "Nous n'avons pas encore assez de séances pour prévoir ton prochain résultat.",
    'missing': "Les séances disponibles ne comportent pas assez de résultats mesurés pour prévoir ton prochain résultat.",
    'low_confidence': "La confiance des observations récentes est trop faible pour appuyer une prévision.",
    'model_not_validated_for_real_music': "Ce modèle est entraîné sur des données simulées et n'est pas validé pour "
        "de la musique réelle ; aucune prévision n'est affichée par défaut.",
}


@dataclass(frozen=True)
class PolicyInputs:
    instrument: str
    rubrics: frozenset
    supported_rubrics: frozenset
    requires_item_check: bool
    item_known: bool | None
    prefix_count: int
    eligible_observations: int
    recent_confidences: tuple
    provenance_counts: dict = field(default_factory=dict)
    eligible_attempts: int | None = None


@dataclass(frozen=True)
class PolicyDecision:
    reason_code: str
    research_eligible: bool
    user_message: str
    policy_version: str = POLICY_VERSION


def _decision(reason_code, research_eligible):
    return PolicyDecision(reason_code=reason_code, research_eligible=research_eligible,
        user_message=REASON_MESSAGES[reason_code])


def evaluate(inputs: PolicyInputs) -> PolicyDecision:
    if inputs.instrument not in SUPPORTED_INSTRUMENTS:
        return _decision('unsupported_instrument', False)
    if inputs.rubrics and not inputs.rubrics <= inputs.supported_rubrics:
        return _decision('unsupported_rubric', False)
    if inputs.requires_item_check and inputs.item_known is False:
        return _decision('unknown_exercise', False)
    if inputs.prefix_count < MIN_HISTORY_ATTEMPTS:
        return _decision('insufficient_history', False)
    if inputs.eligible_observations < MIN_ELIGIBLE_OBSERVATIONS:
        return _decision('missing', False)
    if inputs.eligible_attempts is not None and inputs.eligible_attempts < MIN_HISTORY_ATTEMPTS:
        return _decision('insufficient_history', False)
    known_confidences = [c for c in inputs.recent_confidences if c is not None]
    if known_confidences and (sum(known_confidences) / len(known_confidences)) < MIN_CONFIDENCE:
        return _decision('low_confidence', False)
    research_eligible = bool(inputs.provenance_counts) and set(inputs.provenance_counts) <= {'synthetic'}
    return _decision('model_not_validated_for_real_music', research_eligible)
