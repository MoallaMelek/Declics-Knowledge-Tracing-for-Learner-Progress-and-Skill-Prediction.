# Piano practice collection notebook (local, provisional, not a trained dataset)

This describes `axis7/practice.py`, mounted on the existing `server.app` via a thin, lazily-imported
`APIRouter` (`server.py` only adds `from .practice import router ...; app.include_router(...)`; no
existing route, model or data file changed). It is a separate persistence layer from the v1/v2 model
history: rows live in new `practice_profiles` / `practice_sessions` SQLite tables created through the
same `server.DB` file (so tests that monkeypatch `server.DB` cover this module automatically), never
in the `events` table that `axis7/storage.py` manages for the knowledge-tracing models. Nothing
written here is ever read by `axis7.inference.TwinEngine`; manual/teacher ordinal ratings never
silently become synthetic-model training history.

## Scope and honesty constraints

- Piano only, one provisional rubric (`rubric_version = "piano-pilot-v1"`), `teacher_approved: false`
  everywhere it appears (catalog, exercises, rubric, recommendation, export). This is a demonstration
  catalogue with real practical instructions, not an approved repertoire.
- Six candidate, teacher-reviewable skills, each with a 3-point ordinal rubric
  (`needs_work` / `developing` / `comfortable`), never a fabricated numeric score:
  `pitch`, `rhythm`, `duration`, `articulation`, `fingering`, `score_reading`.
  **`duration` is a deliberately separate skill id from the model's own `timing` concept in
  `axis7/schema.py::MUSIC_SKILLS`** -- it is an observation-only candidate, not a silent alias.
- Profiles are pseudonymous (`student_id = "piano-" + uuid4`); the request body accepts only
  `mode` and `local_storage_consent` -- no name/identity/free-text field exists to accept PII.
- `mode: "demo"` is for synthetic self-demonstration and is consent-exempt; `mode: "local"` is for a
  consenting person's own practice and requires `local_storage_consent: true` or the profile request
  is rejected (422). Every session stores a server-derived `provenance` (`demo` or `local_real`) based
  on the profile's mode -- the client cannot set it, so a demo profile's data is always marked
  synthetic and a local profile's data is always marked real/self-entered, never "AI assessed".
- No research enrollment, guardian-consent or minor-safeguarding claim is made anywhere. If a program
  wants to collect from minors or run this as an actual study, that needs an approved process outside
  this notebook (see `docs/MUSIC_COLLECTION_PROTOCOL.md`); this module intentionally has no such
  pathway.
- No raw audio/video is ever accepted; a session is a server-validated ordinal rating only.
- `model_update_eligible` is hardcoded `false` on every stored/returned session -- there is no path to
  "true" in this module.

## API (implemented exactly as agreed with the UI owner)

- `GET /api/practice/catalog` -- piano instrument, rubric version, the 6 skills (id/label/prompt/3
  level descriptions) and the 6 demonstration exercises (id/title/description/instructions/skill_ids/
  difficulty/duration_minutes/provenance=`demonstration_catalog`/teacher_approved=false/prerequisites=[]
  -- prerequisites stay empty because no teacher has approved an ordering; nothing is inferred).
- `POST /api/practice/profiles` -- `{mode, local_storage_consent}` -> pseudonymous `student_id`,
  `mode`, `instrument`, `privacy_notice_version` (`local-pilot-v1`).
- `POST /api/practice/sessions` -- `{attempt_id, student_id, exercise_id, timestamp, source,
  rubric_version, ratings[], confidence}` -> `{status, idempotent_replay, summary}` where `summary` is
  the same object `GET /api/practice/summary/{id}` returns (so a client doesn't need a second round
  trip after submitting). Validated: unknown profile/exercise/rubric (404/422), duplicate `skill_id`
  within one submission (422), a submission whose ratings are all `not_assessed` (422, at least one
  measured rating is required), a rating referencing a skill the exercise doesn't practice (422).
  `attempt_id` is globally unique and transactionally appended (`BEGIN IMMEDIATE`) with a strictly
  monotone per-learner timestamp; the identical `attempt_id` + identical payload replays idempotently
  (`idempotent_replay: true`, no new row); the same `attempt_id` under a *different* payload or a
  *different* learner returns 409. `attempt_sequence` is derived server-side, never client-supplied.
- `GET /api/practice/summary/{student_id}?policy=balanced|weakest|coverage` -- per-skill status
  (`insufficient_evidence` below 3 measured ratings; `recent_difficulty` when at least 2 of the last 3
  recorded ratings for that skill are `needs_work`; `improving` only once at least 6 ratings exist on
  the *same exercise* and the last 3 average strictly higher than the 3 before them -- a difficulty or
  source change never silently counts as "improving"; otherwise `steady`), a transparent heuristic
  `recommendation` (never a model prediction: `used_model_predictions: false`, evidence lists actual
  `attempt_id`s, 3 alternatives, honest `uncertainty` text), and `forecast: {status: "unavailable",
  reason: "No validated model for this provisional local collection rubric."}` -- always, by design.
- `GET /api/practice/export/{student_id}` -- `schema_version: "practice-export-1.0"`, profile (no
  direct identifiers beyond the pseudonym), rubric, catalog, every session (full source metadata:
  pseudonym, source, confidence, evidence, rubric, ordered UTC timestamps), a `quality` block, and
  `training_ready: false` with an explicit `limitations` list. Scoped strictly to the requested
  `student_id`; never exports another learner's rows.

The existing `POST /api/reset/{student}` is untouched and only deletes from the `events` table, so it
cannot (and does not) remove practice-notebook rows.

## Recommendation heuristics (none of them touch the neural models)

`balanced`/`weakest` only consider skills with >=3 measured ratings (falling back to all 6 skills if
none yet qualify); `weakest` ranks purely by recent needs-work minus recent-comfortable, `balanced`
also prioritizes a skill currently flagged `recent_difficulty`. `coverage` ignores the evidence
threshold and ranks by *fewest* recorded observations, so it recommends an unpracticed skill first.
Below 3 total measured ratings across all skills, every policy falls back to "start with the first
catalogue exercise" (a short assessment), since there isn't enough evidence to prioritize anything.

## Known limitations / next steps

- The improving/steady/recent_difficulty thresholds (3 and 6 ratings, the 1/3-level margin) are
  provisional engineering choices, not a teacher-validated or psychometrically calibrated rule.
- The catalogue, rubric and recommendation heuristics all need an actual piano teacher's review before
  any `teacher_approved` flag anywhere in this module can honestly become `true`.
- `axis7/pilot_data.py` is the validation/manifest/gating layer for turning an export (or a set of
  exports from several learners) into something a future, explicitly-approved study could use; it does
  not do that conversion itself.
