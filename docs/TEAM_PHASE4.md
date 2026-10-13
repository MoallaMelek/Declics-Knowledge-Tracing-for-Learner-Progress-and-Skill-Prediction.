# V4 future-performance forecast query: `POST /api/v4/forecast`

`POST /api/v4/forecast` (implemented in `axis7/forecast_v4.py`, pure gate logic in
`axis7/forecast_policy.py`, mounted on `server.app` the same minimal, lazily-imported way as the
practice and v3 routers) is a **read-only query** over evidence that already exists: the v1/v2/v3
event-sourced history (`docs/TEAM_PHASE3.md`, `axis7/contracts.py`, `axis7/team_v3.py`) or the
separate piano practice notebook (`axis7/practice.py`). It does not ingest anything, train anything,
or load any model checkpoint outside the already-served registry (`axis7/inference.py`,
`axis7/models_v2.py::ResearchPredictor`). Existing routes remain compatible; Phase 4 adds separate descriptive and prediction fields to notebook summaries.

## Why this exists

The team needs one documented way to ask "what would this frozen model say about this learner's
next attempt, as of this moment, using only what was already observed" -- without that question ever
being answered by a model trained only on synthetic piano data as if it had been validated on real
musical performance. v4 is an explicit **abstention-first gate** in front of the existing predictors,
not a new model and not a new claim of validity.

## Request shape

```json
{
  "student_id": "mock-000",
  "instrument": "piano",
  "exercise_id": "mock-exercise-0",
  "model_id": null,
  "as_of": "2026-06-15T00:00:00+00:00",
  "evidence_source": "team_v3",
  "include_research_predictions": false
}
```

See `schemas/forecast-v4.schema.json` (generated with `python -m axis7.forecast_v4`) for the full
JSON Schema of both the request and the response, and `examples/forecast-v4-request.json` /
`examples/forecast-v4-abstained.json` for complete payload examples.

The shipped request/response examples are taken from the actually executed isolated synthetic
replay, not hand-written results. Their learner lives in that replay's temporary database;
replace student_id with a learner in your running service before using the examples there.
Run `python scripts/replay_phase4_forecast.py --output artifacts/phase4/YOUR-NEW-REPLAY.json`
for a complete v3-ingestion / default-abstention / frozen-prediction / reveal / update flow.

For a running local service, discover the existing source contract and use an existing learner:

```sh
curl -sS http://127.0.0.1:8771/api/v2/registry
curl -sS http://127.0.0.1:8771/api/learners?domain=music-mock
curl -sS -H "Content-Type: application/json" --data-binary @YOUR-V3-ATTEMPT.json http://127.0.0.1:8771/api/v3/evidence
curl -sS -H "Content-Type: application/json" --data-binary @YOUR-V4-QUERY.json http://127.0.0.1:8771/api/v4/forecast
```

Use the existing `schemas/attempt-v3.schema.json`, `examples/axis-1-mock-v3.json` and
`examples/project-attempt-v3-multi-producer.json` as explicitly mock producer illustrations.
The query is read-only. Its minimum-history safeguard counts assessed attempts separately
from context-only events; three skill observations from one attempt are not three practices.

- `student_id` (required, 1-100 chars): must be an **exact, already-existing** learner -- a v2/v3
  fixture learner, or one with at least one previously-accepted event/session. Unknown ->
  **404 `Learner not found`** (team_v3) or **404 `Unknown practice profile`** (practice). This
  endpoint never creates a learner.
- `instrument` (optional, default `"piano"`, 1-50 chars): checked against the model's supported
  instrument set (`forecast_policy.SUPPORTED_INSTRUMENTS = {"piano", "piano-provisional"}`, the same
  set `axis7/team_v3.py` already restricts ingestion to). Anything else does not 422 at the schema
  level -- it is a normal **abstain** response with `reason_code: "unsupported_instrument"`, because
  "this instrument isn't supported" is evidence-shaped information the caller needs, not a malformed
  request.
- `exercise_id` (optional, 1-100 chars): only meaningful for item-aware models (`enhanced_gru`,
  `enhanced_gru_no_outcome`, `item_attention`, `item_pfa`; see `inference.uses_items`). It is never
  validated against existence directly -- it is checked against the chosen model's own fitted item
  vocabulary (`server.item_supported`, unchanged). An item-aware model with an exercise it never saw
  in training -> abstain with `reason_code: "unknown_exercise"`. A non-item-aware model, or no
  `exercise_id` at all, conditions generically (`conditioning: "generic_skill"`), exactly like
  `GET /api/v2/forecast/{student}` already does.
- `model_id` (optional, 1-120 chars): must be an **exact key already present** in the domain's served
  predictor registry (`TwinEngine.predictors`, built only from `artifacts/music-mock/results.json`
  and the versioned `artifacts/v2/index.json` manifest, unchanged). Unknown -> **422 `Unknown saved
  model`**. There is no path parameter, directory, or checkpoint filename accepted from the request;
  only lookup by an existing registry key. Omitted -> the domain's existing default model
  (`TwinEngine.default`).
- `as_of` (required): ISO-8601 datetime, **timezone required** (same rule as `Attempt.timestamp` /
  `AttemptV3.timestamp` / `SessionRequest.timestamp` elsewhere in this project). Missing timezone or
  a non-string/non-datetime value -> 422.
- `evidence_source` (required): `"team_v3"` reads the v1/v2/v3 event-sourced history via the existing
  `server.engine`/`server.history`. `"practice"` reads the separate practice notebook via the existing
  `practice._profile`/`practice._load_sessions`. These are two disjoint identifier spaces (a
  `mock-*`/ingested student id is never a `piano-<uuid>` practice profile id, or vice versa); mixing
  them is simply "unknown student" in the other store. `model_id` is only meaningful for `"team_v3"`
  and is **rejected (422)** if supplied together with `"practice"`.
- `include_research_predictions` (optional, default `false`, strict boolean): see "Default abstention
  vs. research opt-in" below.

## Default abstention vs. research opt-in

**Every real-music validity claim is abstained by default**, regardless of how much history exists,
because the served knowledge-tracing models (`axis7/train.py`, `artifacts/music-mock`,
`artifacts/v2`) are trained exclusively on `generate_music`'s controlled synthetic process
(`axis7/data.py`) or on item-conditioned variants of the same synthetic stream. They have never been
validated against `local_real`, `project`, or `public` real-music evidence. This is true even when
every other check below passes, which is why `model_not_validated_for_real_music` is a **terminal**
reason -- reaching it means the query was well-formed and evidence-sufficient, not that a prediction
is being withheld as a false negative.

`include_research_predictions: true` can expose the frozen predictor's **actual** probabilities
(never a fabricated or hand-written number), labeled `status: "research_only"`, but **only** when:

1. every other gate (instrument, rubric, exercise applicability, minimum history, confidence) passed, and
2. **every** attempt in the visible prefix has `provenance: "synthetic"`.

If any conditioning evidence has `provenance: "project"` (or any other non-synthetic value), the
response stays `status: "abstained"` even with the opt-in -- the policy's `research_eligible` flag is
`false`.  Showing the frozen model's output on top of real evidence would look like a real-music
prediction even though the model was never trained or validated for one; the opt-in is scoped to
"replay the model on synthetic data so the engineering can be inspected", not "predict on real data
quietly". `never_validated_for_real_music` is `true` in **every** response, including
`research_only` ones -- there is no response shape in this endpoint that claims validated accuracy.

## The gate, in order (`axis7/forecast_policy.py`, `policy_version: "phase4-gate-v1"`)

The gate is pure and gets concrete counts/flags computed from real stored data; it does not read
files, call models, or know about FastAPI. The first match wins:

| Order | `reason_code` | Trigger |
|---|---|---|
| 1 | `unsupported_instrument` | requested `instrument` not in the model's supported set |
| 2 | `unsupported_rubric` | any `rubric_version` seen in the visible prefix (or the practice notebook's fixed `piano-pilot-v1`) is outside `contracts.SUPPORTED_RUBRICS` |
| 3 | `unknown_exercise` | an item-aware model was asked about an `exercise_id` outside its fitted vocabulary |
| 4 | `insufficient_history` | fewer than `MIN_HISTORY_ATTEMPTS` (3, a provisional safeguard) attempts strictly before `as_of` |
| 5 | `missing` | enough attempts exist, but fewer than `MIN_ELIGIBLE_OBSERVATIONS` (3) observations in the prefix are actually model-eligible (not `missing: true`, not context-only, not axis-7-self-referential, not below the ingestion-time confidence bar) |
| 6 | `low_confidence` | enough eligible observations exist, but the average `source_confidence` over the most recent `RECENT_CONFIDENCE_WINDOW` (5) of them is below `forecast_policy.MIN_CONFIDENCE` (0.75) -- **deliberately stricter** than `contracts.MIN_CONFIDENCE` (0.6), which only gates whether an observation may update a model at all, not whether it is confident enough to also support showing a demonstration forecast |
| 7 (terminal) | `model_not_validated_for_real_music` | everything else passed; see "Default abstention vs. research opt-in" |

Every `reason_code` carries a fixed, plain-French `user_message` (`forecast_policy.REASON_MESSAGES`)
and the same `policy_version` string, so a UI or a teammate can branch on the stable code and display
the bundled message, or substitute their own copy, without re-deriving the policy.

## Chronology and the "unchanged after a future attempt" guarantee

Only attempts/sessions with a stored order strictly **before** `as_of` are ever visible
(`row['order'] < as_of.timestamp()` for team_v3, `datetime.fromisoformat(session['timestamp']) <
as_of` for practice) -- `as_of` itself is excluded, matching the existing "strictly later" chronology
invariant already enforced at ingestion (`axis7/storage.py::append_event`,
`axis7/practice.py::create_session`). Appending a new, later attempt through the existing `POST
/api/v3/evidence` and then repeating the **same** `/api/v4/forecast` request with the **same**
`as_of` is guaranteed to return the same `prefix_count`, the same `evidence_ids`, and (in
`research_only` mode) the same `probabilities` -- only `excluded_future_count` changes, because the
newly-visible-in-principle attempt is still excluded by the cutoff. This is exercised directly in
`tests/test_forecast_v4.py::test_prediction_and_prefix_are_unchanged_after_appending_a_future_attempt`.
v4 performs no writes, so it has no idempotency/conflict semantics of its own; ingestion's existing
409 (`attempt_id` replay with a different payload) and 422 (out-of-order timestamp) behavior from
`docs/TEAM_PHASE3.md` is unaffected and is simply reflected the next time v4 is queried.

## HTTP status semantics

- **200**: the query was well-formed and resolved to either `abstained` or `research_only`. Abstention
  is a normal, successful response shape -- not an error -- because it is the expected default.
- **404**: `student_id` does not exist as a learner (`team_v3`) or practice profile (`practice`).
- **422**: malformed request body (missing/invalid `as_of` timezone, unknown field, out-of-bounds
  length), an unknown `model_id`, or `model_id` supplied together with `evidence_source: "practice"`.
- **409**: never returned by v4 itself (it writes nothing); only ever relevant to the underlying `POST
  /api/v3/evidence` / `POST /api/practice/sessions` ingestion calls this endpoint reads after the fact.

## Source, rubric, version, reference-comparison, confidence and missingness, mapped to the response

| Response field | What it actually reflects |
|---|---|
| `evidence_source` | which store was read: `team_v3` (v1/v2/v3 event history) or `practice` (notebook) |
| `evidence_provenance_counts` | per-provenance counts in the visible prefix; practice distinguishes demo and local_real |
| `assessment_source_counts` | practice prefix counts by self/teacher; a teacher-entered rating is not teacher-confirmed development |
| `known_confidence_count` / `unknown_confidence_count` | source confidence availability; unknown confidence is never represented as certainty |
| `calibrated_uncertainty_available` | false: no validated real-musical uncertainty interval exists |
| `training_provenance` | always `"synthetic"` for `team_v3` (the domain's models are never trained on anything else); `null` for `practice` (there is no model) |
| `model_profile` / `model_version` | `contracts.PROFILE` and the resolved predictor's `serving_implementation_version`/`implementation_version`; both `null` for `practice` |
| `conditioning` | `"exercise"` or `"generic_skill"`, same semantics as `ForecastV2.conditioning`; `null` for `practice` |
| `accepted_observations` / `omitted_observations` / `omitted_reasons` | eligible vs. ineligible observation counts in the prefix, and a breakdown by the **existing** `eligibility_reason` strings already assigned at ingestion (`missing_source_confidence`, `low_source_confidence`, `explicit_missing_measurement`, `context_only_objective`, `axis7_self_referential_not_model_update_eligible`, `unsupported_rubric`, ...) -- v4 does not invent new omission reasons, it audits the ones ingestion already recorded |
| `prefix_count` / `excluded_future_count` | counts of visible vs. cutoff-excluded attempts/sessions |
| `eligible_attempt_count` | visible attempts with at least one model-eligible outcome; observation-only context events cannot satisfy the minimum assessed-attempt safeguard |
| `evidence_ids` | the attempt/session ids that make up the visible prefix, in chronological order |
| `evaluated_scope` | `abstained_not_evaluated` when abstained; `observed_skill_given_attempted_exercise` / `skill_only_forecast` when `research_only`, matching `ForecastV2.evaluated_scope`; `practice_notebook_no_validated_model` for `practice` |

A direct axis-1 pitch "reference comparison" requirement, and the cached
`Declic_Deep_Learning_Objectives-1-1` producer/objective mapping, are enforced at **ingestion** time
by `axis7/team_v3.py` (see `docs/TEAM_PHASE3.md`) and are unchanged here -- v4 only reads attempts
that already passed those checks; it does not re-validate or re-interpret producer/objective
semantics.

## What this does *not* do

- It does not implement, simulate, or claim real-music predictive validity for any other axis, or for
  Axis 7 itself. `never_validated_for_real_music` is `true` in every response.
- It does not convert the practice notebook's provisional 3-point ordinal ratings into a binary
  outcome, a probability, or model-eligible evidence -- `evidence_source: "practice"` always abstains
  with `reason_code: "unsupported_rubric"`, by the same gate used everywhere else, not a special case.
- It does not add a new model, a new training run, or a new checkpoint format. `axis7/train.py`,
  `axis7/models.py`, `axis7/models_v2.py` and the 162/102/40 preserved baseline artifacts are
  untouched; `TwinEngine`/`ResearchPredictor` are only ever called through their existing
  `probabilities(...)` method.
- It does not expose arbitrary model loading: `model_id` is a lookup key into the already-served,
  versioned registry, never a filesystem path.


## Objectives revision 1-2 discrepancy

Revision 1-2 was located and read during Phase 4. Its overview lists learner prediction as O09, but its detailed learner-prediction section is labeled O08. The existing explicitly cached 1-1 mapping is retained until team resolution. See PHASE4_IMPLEMENTATION.md. This is a source numbering conflict, not a completed teammate integration.
