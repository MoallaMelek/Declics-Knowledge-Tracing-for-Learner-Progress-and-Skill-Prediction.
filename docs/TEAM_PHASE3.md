# V3 team evidence endpoint: per-observation producer attribution

`POST /api/v3/evidence` (implemented in `axis7/team_v3.py`, mounted on `server.app` the same minimal,
lazily-imported way as the practice router) extends the v2 team boundary
(`docs/INTEGRATION.md`, `axis7/contracts.py`) for the one gap v2 explicitly left open: "A future team
collector needs an agreed per-observation source-attribution contract to fuse simultaneous outputs
across axes." V1 (`/api/attempts`) and v2 (`/api/v2/events`, `axis7/contracts.py`,
`axis7/adapters.py`) are **unchanged** -- v3 is additive and does not modify any existing contract,
model, data loader, inference code or test fixture.

## Why v2 wasn't enough for this

`contracts.AttemptV2` attributes the whole attempt to **one** `producer_axis`/`producer_version`. A
real atomic practice attempt can carry simultaneous evidence from several axes at once (axis 1 pitch,
axis 3 score-alignment metadata, axis 6 instrument context, ...). `AttemptV3` moves `producer_axis`,
`producer_version`, `objective_id` and `assessment_kind` onto **each observation**, so one atomic
attempt (one `attempt_id`, one timestamp) can legitimately carry evidence from several producers at
once -- without inventing per-producer timestamps to fake sequencing.

## Objective-id mapping (cached, versioned assumption -- please verify)

The only Declic_Deep_Learning_Objectives reference available to this module during implementation was
version **1-1**; version **1-2** (mentioned in the task) was not accessible here, so nothing from 1-2
is assumed, guessed, or read as if it had been seen. The mapping below is declared explicitly in
`axis7/team_v3.py::AXIS_OBJECTIVES` / `AXIS_CONTEXT_OBJECTIVES` so it is trivial to correct once the
actual document is checked against it:

| Axis | Direct objective | Context-only objective | Bounded context skill_id |
|---|---|---|---|
| 1 | O01 (pitch/note accuracy) | -- | -- |
| 2 | O02 (rhythm/timing) | -- | -- |
| 3 | O03 (score alignment) | O04 | `omr_metadata` |
| 4 | O07 (performance quality) | O08 | `corrective_feedback` |
| 5 | O05 (fingering/technique) | O06 | `posture_context` |
| 6 | O10 (instrument/context) | *(O10 itself is context-only for axis 6)* | `instrument_context` |
| 7 | O09 (Axis 7's own objective: learner skill & future performance prediction) | -- | -- |

**If this mapping is wrong, it is a one-place fix** (the two dicts above); nothing else in the
endpoint depends on the specific objective strings beyond validating membership.

## Validation rules actually enforced

- `skill_id` must be one of the 8 canonical ids in `contracts.SKILL_VOCABULARY`, or one of the 4
  explicitly bounded "unsupported" identifiers (`omr_metadata`, `corrective_feedback`,
  `posture_context`, `instrument_context`) -- nothing else is accepted (422 otherwise, both at the
  Pydantic/JSON-Schema level and at runtime). The schema supplies structural types and this enum;
  cross-field objective/reference/missingness rules, relational duplicates and chronological checks
  are enforced by the API and must not be assumed satisfied from a structural schema check alone.
- `objective_id` must be the axis's declared direct or context objective from the table above (422
  otherwise); a context objective must pair with its exact bounded skill_id (422 otherwise).
- **A direct axis-1 pitch claim (`assessment_kind: "direct"`, a non-missing outcome/score) requires
  `reference_compared: true`.** Raw transcribed pitch is not correctness without an explicit
  reference comparison; omitting or falsifying this (`reference_compared: false`/absent) is rejected
  (422), per the task's explicit instruction.
- `missing: true` observations must not also carry an `outcome`/`score` (422 otherwise); they are
  stored with `eligible: false`, `eligibility_reason: "explicit_missing_measurement"`, and no value.
- The three bounded "unsupported" identifiers (OMR metadata, corrective feedback, instrument context)
  are **always** `eligible: false` / `eligibility_reason: "context_only_objective"`, regardless of
  `assessment_kind` -- a score is never silently thresholded into a binary label for these.
- `producer_axis: 7` may only submit `inferred`/`recommendation`/`context` evidence, never `direct`
  (422 otherwise); when accepted it is stored but always
  `eligibility_reason: "axis7_self_referential_not_model_update_eligible"`, so Axis 7's own
  recommendation output can never feed back into its own model as if it were new ground truth.
- Duplicate `(producer_axis, producer_version, skill_id)` within one atomic attempt is rejected (422).
- `provenance: "public"` is rejected, exactly like v2 (keeps benchmark data out of the music stream).

The envelope records `objective_mapping_version: "cached-objectives-1-1"`. A claimed 1-2 revision
is rejected until that source is actually available and a new mapping is explicitly released.
An atomic attempt accepts one version per producing axis. Repeating that axis/skill under a new
producer version cannot duplicate its update. Context-only producers remain in the provenance list.
O04/O06/O08 context assignments here are proposed adapters, not completed or signed teammate modules.

## How the merge actually happens (reuse, not reimplementation)

`resolve_event_v3` groups observations by `(producer_axis, producer_version)`. Each canonical-skill
group is packaged as a real `contracts.AttemptV2` (sharing the one envelope's `attempt_id`,
`timestamp`, etc.) and resolved through the **existing, unmodified**
`contracts.resolve_event` -- so producer/skill-axis mismatches, rubric support, confidence
thresholds and `model_update_requested` (`= assessment_kind == "direct"`) reuse exactly the same
logic v2 already has and already tests. The bounded/missing/axis-7 observations are built directly
(they are always ineligible, so no v2 behavior is bypassed by not routing them through it -- axis 7
isn't even a valid `AttemptV2.producer_axis` value, so it genuinely cannot go through that path).
The per-group results are re-assembled in the **original submitted order** into one merged record and
appended through the existing, unmodified `axis7.storage.append_event` -- one atomic transaction, one
declared timestamp, the same idempotency/conflict/chronology guarantees v2 already has (same
`attempt_id` + same payload replays; a different payload or a different learner on the same
`attempt_id` is a 409; an out-of-order timestamp for that learner is a 422).

## What this does *not* do

- It does not implement, simulate, or claim to complete any other axis's model. Mock examples (see
  `examples/axis-1-mock-v3.json`, `examples/project-attempt-v3-multi-producer.json`, and the generated
  `schemas/attempt-v3.schema.json`) are illustrative payload shapes only.
- It does not change `evaluated_scope`/`query_validity` semantics of `GET /api/v2/forecast/{student}`
  or the `/api/twin/{student}` snapshot -- a v3-merged attempt is just another row in the same learner
  history those endpoints already read, with the same "correctness is not mastery" warning.
- It does not expose a v3 registry/schema listing endpoint; the static
  `schemas/attempt-v3.schema.json` (generated with `python -m axis7.team_v3`) is the published
  contract, deliberately kept out of the existing `/api/v2/schemas` handler to avoid touching that
  owned code.
