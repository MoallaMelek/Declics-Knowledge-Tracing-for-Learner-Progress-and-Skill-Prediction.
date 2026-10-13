# Axis 7 observation boundary v2

The recommended team endpoint is `POST /api/v2/events`. The old `/api/attempts` remains available for v1 callers. Both preserve the original observations; v2 adds explicit compatibility and update eligibility. This is a local, single-user integration demonstrator, not an authenticated student service.

## Producer contract

Use `schema_version: "2.0"`, `model_profile: "provisional-piano-v1"`, `producer_axis: 1..6`, and a nonempty `producer_version`, plus the existing event identity, session, exercise, instrument, provenance and timestamp fields. Examples for every producer are in `examples/axis-1-mock-v2.json` through `axis-6-mock-v2.json`; `axis7.adapters.example_workflow()` creates the complete synthetic workflow. These are mock boundaries, not implementations of the other axes.

`GET /api/v2/registry` publishes the provisional vocabulary and compatibility policy. Pitch, rhythm, timing, articulation, fingering and score navigation map to saved models. Quality and technique measurements are retained with no fabricated model target. Axis 6 sends instrument context and may omit observations; instrument recognition is not a learner competency. Other producers must supply at least one observation. This demonstration accepts piano only. A new instrument or taxonomy needs an explicit trained profile and migration.

Each observation requires a strict integer binary outcome or a finite score in [0,1]. Score-only observations never update a binary model. V2 binary updates also require a mapped skill, supported rubric, producer confidence of at least 0.6, and `model_update_requested: true`. The confidence threshold is a provisional policy, not calibrated predictive uncertainty. Missing confidence, incompatible rubric and explicit observation-only events are stored with an `eligibility_reason`. Supported rubrics are `provisional-piano-v1` and `provisional-mock-v1`; neither is teacher-validated. V1 retains legacy binary eligibility for compatibility, so migrate producers to v2 to use these gates.

Use timezone-aware ISO timestamps. A later event must be strictly later than the learner's last stored event; simultaneous measurements belong in one atomic attempt. Storage enforces this inside a SQLite transaction, including concurrent retries. Original fixture histories are immutable.

## Retry and acknowledgment

An identical v2 event ID and canonical payload returns the stored event with `idempotent_replay: true`; it adds no second observation. Reusing an ID with a changed payload returns HTTP 409. Invalid chronology or observations return HTTP 422. V1 duplicate submissions still return HTTP 422. Check the response before inventing a new ID after a network failure.

Successful persistence returns `status: accepted`, the record, eligible observation count and `forecast_status`. If forecasting fails after storage, acceptance remains successful, `twin` is null, and `forecast_error` contains `INFERENCE_UNAVAILABLE` and `retryable: true`. Retry the same event or request the forecast; do not assume a missing forecast means the event was lost. Logs contain acceptance metadata, not raw event bodies.

## Forecast contract

`GET /api/v2/forecast/{student}?domain=music-mock&exercise_id=...` returns the typed `ForecastV2` envelope: response version, learner, domain, saved model ID, conditioning, item support, training provenance, skill probabilities and validity warning. Omit `exercise_id` for a generic next query. V2 checkpoints map unseen or omitted exercises to UNK with training-only global difficulty. Their known exercise IDs represent atomic exercise bundles, not individual notes. Legacy v1 predictors remain skill-only even if an exercise is supplied.

`GET /api/twin/{student}?position=N&model_id=...&policy=balanced` supplies the dashboard. Generic replay predictions use only the visible history prefix; future exercise metadata is not consumed. Historical curves show predictions conditioned on known attempted exercises, with a generic next query at the final point. The response exposes `curve_conditioning`, implementation version, model name, update counts, evidence eligibility and record provenance. Initialization ranges are descriptive model variation.

`GET /api/v2/schemas`, `/docs` and `/openapi.json` provide machine-readable contracts. Checked-in input schemas are generated with `python -m axis7.schema` and `python -m axis7.contracts`. `GET /api/research` exposes only completed v2 summaries; `/api/experiments` preserves historical v1 evidence.

## Practice policies

`balanced` combines forecast fragility (0.5), recent failures (0.3), recurring error types (0.1) and negative generic forecast change (0.1). `weakest` ranks forecast fragility alone. Both require three usable observations. A spread above 0.15 across saved initializations requests teacher assessment. The API discloses features, weights and alternatives. The exercise bank is synthetic, introductory and not teacher-approved; no prerequisites are inferred. These policies have no prospective evidence of learning gain. Missing trustworthy time gaps means no time-since-practice feature is claimed.

## Historical v1 details

`POST /api/attempts` accepts a canonical `Attempt`. `GET /docs` exposes the local OpenAPI interface. See `schemas/attempt-v1.schema.json`, generated from the validation model (`python -m axis7.schema`), and `examples/project-attempt.json`. The example's values are illustrative placeholders, not measurements.

Use a pseudonymous `student_id`, unique `attempt_id`, session and exercise identifiers, timezone-aware timestamp, instrument, provenance, explicit rubric version, and observations. An unfamiliar learner is initialized by the first valid project event; later events must be strictly chronological. Equal timestamps must be combined into one attempt. Duplicate IDs, unknown skills, unsupported instruments, and malformed values are rejected before persistence. Unknown fields are refused rather than dropped, NaN and infinite numbers are refused, and `attempt_id` is unique across all learners.

The demonstration supports `piano`/`piano-provisional` and this provisional vocabulary: `pitch`, `rhythm`, `timing`, `articulation`, `fingering`, `score_navigation`. These are hypotheses requiring partner/teacher validation, not an agreed DÉCLIC curriculum. Changing the vocabulary requires retraining and a versioned migration.

Each observation may contain binary `outcome` (integer 0/1), a score explicitly scaled to [0,1], producer confidence, error codes, and evidence ID. Continuous scores alone are preserved but **do not update binary KT outcomes**. The upstream producer must own, declare, and validate any rubric converting performance to a binary target. Four note outcomes from one exercise can share the same skill; they are predicted together before any of them updates the state.

Optional session signals include note accuracy, rhythm score, timing error in milliseconds, gesture measurements, and upstream version references. These are retained for audit; the current models use only historical skill/outcome events. Source confidence is not predictive uncertainty and does not calibrate the displayed probability. No raw audio/video/image is accepted or processed by Axis 7.

The API response includes the persisted record and updated twin. `GET /api/twin/{student}` supports `position` and `model_id`. `GET /api/learners` lists available profiles. `GET /api/experiments` serves saved results. `POST /api/simulate` is a controlled mock producer for existing musical histories. `POST /api/reset/{student}` removes added runtime events. `GET /api/export/{student}` exports an internal analysis snapshot, not canonical re-import events.

Events with `project` provenance remain identifiable throughout the evidence trail. Adding them does not make a model trained on synthetic musical data validated for actual learners. FORGET-SE benchmark outcomes are kept in a separate immutable domain; public benchmark ingestion into the musical stream is rejected.

Deployment requires a separate consent/retention protocol, authenticated and authorized student access, audit logging, validated rubrics, representative chronological real music data, and an evaluation of learning benefit. The supplied API deliberately binds to loopback for a single-user prototype.
