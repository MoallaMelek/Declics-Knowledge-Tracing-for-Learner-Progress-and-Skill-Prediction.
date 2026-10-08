# Completion report · DÉCLIC Axis 7

Date: 2026-10-06. Status: **local research prototype complete for the three handoff tasks, with the browser-level visual check still pending.** This is not production software and must not be presented as production-ready, clinically or pedagogically validated, or as validated for real musicians.

## Tasks

### 01 · Engineering review and fixes — complete

Defects found by reproduction, all fixed, each with a regression test (see `VALIDATION.md` for the pre-fix results):

1. Non-finite numbers (`inf`, NaN) accepted in `timing_mae_ms` and `gesture_metrics`; a NaN in a request body crashed the 422 error renderer. Fixed in `axis7/schema.py` and `axis7/server.py`.
2. Misspelled observation fields were silently dropped. Unknown fields are now refused (`extra="forbid"`).
3. A duplicate `attempt_id` under another learner produced a raw SQLite message. Now a clear 422 across all learners, including the benchmark fixtures.
4. Simulation rejections could surface as 500 errors; now 422.
5. SQLite connections were never closed; `connection()` now closes them.
6. Frontend: after ingesting an event for a new learner, the selector and `state.student` disagreed, so a following simulation would have targeted the previous learner. Fixed in `web/app.js`; verified by the Node harness (9/9 on the fixed file, 7/9 on the pre-fix file).
7. Frontend: reset of a learner created only by ingestion left the UI on a 404 state. Fixed; the list is refreshed and the message says the profile was removed.
8. Frontend: the ingestion JSON template overwrote the user's edits on every re-render. Now regenerated only while untouched.

Checked and found correct (no change): causality of the GRU and attention models on full and bounded (sliding-window) histories; atomic duplicate-skill targets; score-only observations excluded from binary loss; training-only baseline statistics; saved-checkpoint reload reproducibility; the reported metrics in `results.json` and `RESULTS.md` (every headline value in the README matches the file); the bootstrap and calibration code paths.

Not changed, by decision: model architecture, weights, splits, and the measured results. No retraining was needed, since no defect in the learning code was demonstrated.

Known engineering limits left open:
- `POST /api/attempts` accepts `provenance: synthetic` as well as `project`; synthetic events are shown in the musical stream with the synthetic label. Intended for the mock producer; a deployment would restrict it.
- Ingestion persists the event before the response snapshot is computed; an exception in the snapshot after persistence would leave the event stored while the client receives an error. Not observed in testing.
- The server is single-process with a global lock; it is a loopback demonstration, not a concurrent service.

### 02 · Design and interaction — partly complete, visual verification pending

Changes are listed in `DESIGN_CHANGES.md`: keyboard focus ring and focus retention on graph nodes; a rule-explanation sentence for the suggested practice; a simulation stamp on the constellation; larger small text; removal of an external font request; removal of a broken image placeholder; group labelling for the skill picker.

**Not verified:** rendering, focus appearance, mobile layout, reduced-motion effect and contrast. No browser tool was available. `docs/preview.jpg` is from before these changes. Claude's earlier critiques are answered item by item in `DESIGN_CHANGES.md`, with the partial and undone items named.

No Figma or other design-tool file was created; no account, payment or video generation was used.

### 03 · Delivery — complete

- `schemas/attempt-v1.schema.json`: generated directly from `Attempt.model_json_schema()` by `python -m axis7.schema`; a test enforces that it still matches.
- `examples/project-attempt.json`: validates in Pydantic and in JSON Schema (`jsonschema` 4.26.0, Draft 2020-12). The values are illustrative placeholders.
- Documents completed or corrected: README (font claim, test and Node note, new links, schema command), `INTEGRATION.md` (strictness rules, example status), `MODEL_CARD.md` (paired bootstrap result for DKT-7 against the prior), `RESEARCH.md` (four French/English slips corrected; facts unchanged; spot-checked, not fully proofread), `DEMO_SCRIPT.md` (new), `VALIDATION.md` (new, verbatim test output), `DESIGN_CHANGES.md` (new).
- Dependency lock: five packages added (`attrs`, `jsonschema` and its three dependencies); `pyproject.toml` test extra lists `jsonschema`.
- Accidental empty nested directory `outputs/declic-axis7/data/raw` removed after verifying it was inside the project and contained only empty folders.
- Archive: `outputs/declic-axis7.zip` (105 files, about 2.9 MB, including 12 checkpoints and the licensed CSV); excludes `runtime/`, caches, the virtual environment, and bytecode. Extracted and re-tested: 27 passed.

## Test evidence

- Final suite: **27 passed, 0 failed, 0 skipped**, prepared Python, writable `--basetemp` under `work/`. Output saved verbatim in `docs/VALIDATION.md`.
- Baseline before this round: 15 passed.
- The frontend test runs Node and drives the real `web/app.js` with real API responses; it is skipped only when Node is absent.

## Measured results (unchanged; from `artifacts/*/results.json`)

FORGET-SE v1 (real, CC BY 4.0), fixed learner-disjoint split 130/14/14/28, test learners 28:

| Model (representative) | Test ROC-AUC | Test log loss |
|---|---:|---:|
| Training prior | 0.5913 | 0.6850 |
| BKT | 0.5854 | 0.6540 |
| PFA | 0.5937 | 0.6581 |
| DKT-style GRU, seed 7 (selected on validation) | 0.7276 | 0.5945 |
| SAKT-style attention, seed 7 | 0.7099 | 0.6099 |

DKT-7 learner-bootstrap AUC interval [0.6948, 0.7572]; paired log-loss difference against the prior [-0.125, -0.054]. Paired intervals against PFA and BKT are **not implemented**.

Synthetic musical data (controlled generator, pipeline check only): PFA wins overall (log loss 0.6182); DKT-7 is the best neural model (0.6304). These numbers do not validate musical transfer.

## Output paths

- Code: `axis7/`; web: `web/`; configuration: `configs/experiment.json`; artifacts and checkpoints: `artifacts/forget-se/`, `artifacts/music-mock/`; licensed data and attribution: `data/raw/forget_se.csv`, `data/DATA_LICENSE.md`.
- Schema and example: `schemas/attempt-v1.schema.json`, `examples/project-attempt.json`.
- Tests: `tests/`, frontend harness `tests/frontend/ui_check.js`.
- Documents: `docs/`.
- Archive: `outputs/declic-axis7.zip`.
- Original source folder untouched (`C:/Users/moall/OneDrive/Desktop/declic`).

## Genuinely incomplete (auditable list)

1. Browser visual verification, mobile layout, reduced-motion behaviour and contrast measurement (no browser tool in this session).
2. Paired learner-bootstrap comparisons against PFA and BKT.
3. Exposure-only ablation and item-difficulty modelling (not implemented; disclosed).
4. Real music data: none. SingKT/OcarinaKT rights not established; Rach3 licence is non-commercial and requires alignment work. The music view runs on synthetic data only.
5. Teacher-validated taxonomy and rubric; the six skills are provisional.
6. Forgetting and timestamp-duration effects: FORGET-SE timestamp units are unknown, so only chronology is used.
7. Recommendation effectiveness: the minimum-forecast rule has no causal or prospective validation.
8. Authentication, authorization, consent, retention, audit logging, and multi-user concurrency: out of scope for this loopback prototype.
9. `docs/preview.jpg` is stale relative to the round-3 interface.
10. The research synthesis was spot-checked for typos rather than fully proofread.

## Not production-ready

This prototype is a single-user local demonstration. Its probabilities are next-attempt success forecasts from saved models, not measures of psychological mastery, and it makes no diagnosis.
