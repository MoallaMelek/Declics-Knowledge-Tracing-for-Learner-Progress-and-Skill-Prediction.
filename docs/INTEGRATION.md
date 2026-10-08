# Observation boundary v1

`POST /api/attempts` accepts a canonical `Attempt`. `GET /docs` exposes the local OpenAPI interface. See `schemas/attempt-v1.schema.json`, generated from the validation model (`python -m axis7.schema`), and `examples/project-attempt.json`. The example's values are illustrative placeholders, not measurements.

Use a pseudonymous `student_id`, unique `attempt_id`, session and exercise identifiers, timezone-aware timestamp, instrument, provenance, explicit rubric version, and observations. An unfamiliar learner is initialized by the first valid project event; later events must be strictly chronological. Equal timestamps must be combined into one attempt. Duplicate IDs, unknown skills, unsupported instruments, and malformed values are rejected before persistence. Unknown fields are refused rather than dropped, NaN and infinite numbers are refused, and `attempt_id` is unique across all learners.

The demonstration supports `piano`/`piano-provisional` and this provisional vocabulary: `pitch`, `rhythm`, `timing`, `articulation`, `fingering`, `score_navigation`. These are hypotheses requiring partner/teacher validation, not an agreed DÉCLIC curriculum. Changing the vocabulary requires retraining and a versioned migration.

Each observation may contain binary `outcome` (integer 0/1), a score explicitly scaled to [0,1], producer confidence, error codes, and evidence ID. Continuous scores alone are preserved but **do not update binary KT outcomes**. The upstream producer must own, declare, and validate any rubric converting performance to a binary target. Four note outcomes from one exercise can share the same skill; they are predicted together before any of them updates the state.

Optional session signals include note accuracy, rhythm score, timing error in milliseconds, gesture measurements, and upstream version references. These are retained for audit; the current models use only historical skill/outcome events. Source confidence is not predictive uncertainty and does not calibrate the displayed probability. No raw audio/video/image is accepted or processed by Axis 7.

The API response includes the persisted record and updated twin. `GET /api/twin/{student}` supports `position` and `model_id`. `GET /api/learners` lists available profiles. `GET /api/experiments` serves saved results. `POST /api/simulate` is a controlled mock producer for existing musical histories. `POST /api/reset/{student}` removes added runtime events. `GET /api/export/{student}` exports an internal analysis snapshot, not canonical re-import events.

Events with `project` provenance remain identifiable throughout the evidence trail. Adding them does not make a model trained on synthetic musical data validated for actual learners. FORGET-SE benchmark outcomes are kept in a separate immutable domain; public benchmark ingestion into the musical stream is rejected.

Deployment requires a separate consent/retention protocol, authenticated and authorized student access, audit logging, validated rubrics, representative chronological real music data, and an evaluation of learning benefit. The supplied API deliberately binds to loopback for a single-user prototype.
