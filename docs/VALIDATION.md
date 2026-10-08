# Validation record · Axis 7

Date: 2026-10-06. Environment: prepared Python 3.12.14 (`work/.venv`), pinned in `requirements.lock.txt`, torch 2.14.1+cpu, CPU only. Command used for every run below:

```powershell
.\..\..\work\.venv\Scripts\python.exe -m pytest -v --basetemp ..\..\work\pytest-final-r3 -p no:cacheprovider
```

The writable `--basetemp` under `work/` avoids the sandbox temporary-directory denial recorded in the handoff. No test was skipped or deselected in the final run.

## Final result

**27 passed, 0 failed, 0 skipped, 0 errors** (exit code 0).

Verbatim output of the final run (`work/pytest-final-r3.txt`):

```text
============================= test session starts =============================
platform win32 -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\moall\Documents\Codex\2026-10-06\files-mentioned-by-the-user-declic\work\.venv\Scripts\python.exe
rootdir: C:\Users\moall\Documents\Codex\2026-10-06\files-mentioned-by-the-user-declic\outputs\declic-axis7
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.15.1
collecting ... collected 27 items

tests/test_causality.py::test_current_and_future_outcomes_cannot_change_past_predictions[DKT] PASSED [  3%]
tests/test_causality.py::test_current_and_future_outcomes_cannot_change_past_predictions[SAKT] PASSED [  7%]
tests/test_causality.py::test_atomic_duplicate_skill_targets_preserve_original_row_weight PASSED [ 11%]
tests/test_causality.py::test_baselines_do_not_use_current_outcomes[prior] PASSED [ 14%]
tests/test_causality.py::test_baselines_do_not_use_current_outcomes[bkt] PASSED [ 18%]
tests/test_causality.py::test_baselines_do_not_use_current_outcomes[pfa] PASSED [ 22%]
tests/test_causality.py::test_real_benchmark_ties_and_split_are_atomic_disjoint PASSED [ 25%]
tests/test_causality.py::test_boundary_unknown_missing_and_invalid_outcomes_are_rejected PASSED [ 29%]
tests/test_causality.py::test_saved_baseline_statistics_only_use_training_learners PASSED [ 33%]
tests/test_causality.py::test_attention_future_inputs_cannot_change_current_logits PASSED [ 37%]
tests/test_causality.py::test_bounded_sliding_context_keeps_predictions_causal[DKT] PASSED [ 40%]
tests/test_causality.py::test_bounded_sliding_context_keeps_predictions_causal[SAKT] PASSED [ 44%]
tests/test_causality.py::test_non_finite_numeric_observation_is_refused_at_the_boundary PASSED [ 48%]
tests/test_frontend.py::test_ingest_and_reset_keep_selector_and_state_consistent PASSED [ 51%]
tests/test_integration.py::test_project_observation_creates_learner_and_survives_engine_reload PASSED [ 55%]
tests/test_integration.py::test_simulated_session_updates_predictions_and_reset_restores_history PASSED [ 59%]
tests/test_integration.py::test_saved_predictor_reload_and_displayed_prefix_are_reproducible[dkt-7] PASSED [ 62%]
tests/test_integration.py::test_saved_predictor_reload_and_displayed_prefix_are_reproducible[sakt-7] PASSED [ 66%]
tests/test_integration.py::test_saved_predictor_reload_and_displayed_prefix_are_reproducible[pfa-0] PASSED [ 70%]
tests/test_integration.py::test_non_finite_measurement_is_rejected_before_any_persistence PASSED [ 74%]
tests/test_integration.py::test_attempt_id_is_unique_across_learners_with_a_clear_message PASSED [ 77%]
tests/test_integration.py::test_misspelled_observation_field_is_refused_not_silently_dropped PASSED [ 81%]
tests/test_integration.py::test_reset_removes_a_learner_created_only_by_ingestion PASSED [ 85%]
tests/test_integration.py::test_simulation_for_unknown_learner_is_not_found PASSED [ 88%]
tests/test_schema.py::test_published_schema_is_generated_from_the_validation_model PASSED [ 92%]
tests/test_schema.py::test_example_is_a_valid_attempt PASSED             [ 96%]
tests/test_schema.py::test_example_validates_against_the_published_json_schema PASSED [100%]

============================== warnings summary ===============================
..\..\work\.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\moall\Documents\Codex\2026-10-06\files-mentioned-by-the-user-declic\work\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 27 passed, 1 warning in 12.34s ========================
```

Baseline before this round, same environment: 15 passed (`work/pytest-baseline`). The 12 added tests are listed in the next section.

## What the added tests protect (defects reproduced before fixing)

Each regression was run against the pre-fix copy (`work/backup-before-claude`) with the new tests copied in. Results:

| Test | Pre-fix result | Defect it guards |
|---|---|---|
| `test_non_finite_numeric_observation_is_refused_at_the_boundary` | FAILED | `timing_mae_ms=inf` and NaN in `gesture_metrics` were accepted |
| `test_non_finite_measurement_is_rejected_before_any_persistence` | FAILED | A NaN literal in the request body crashed the 422 error renderer (`ValueError: Out of range float values are not JSON compliant`) |
| `test_attempt_id_is_unique_across_learners_with_a_clear_message` | FAILED | Duplicate ID under another learner returned the raw text `UNIQUE constraint failed: events.id` |
| `test_misspelled_observation_field_is_refused_not_silently_dropped` | FAILED | Unknown field such as `timing_ms` was silently dropped |
| `test_bounded_sliding_context_keeps_predictions_causal[DKT/SAKT]` | passed | Coverage of the >context path; causal before and after, so no defect |
| `test_reset_removes_a_learner_created_only_by_ingestion` | passed | Backend behaviour was already correct; the UI defect is covered by the frontend test |
| `test_simulation_for_unknown_learner_is_not_found` | passed | Already correct (404); recorded so the handoff gap is closed |
| `test_frontend.py::test_ingest_and_reset_keep_selector_and_state_consistent` | see below | Frontend state mismatch |
| `test_schema.py` (3 tests) | new artifact | Published schema equals the generator output; example validates in Pydantic and in JSON Schema |

Frontend check (`tests/frontend/ui_check.js`, driven by `tests/test_frontend.py` with API responses captured from the real server):

- Fixed `web/app.js`: **9/9 checks passed**.
- Pre-fix `web/app.js`: **7/9**. The two failures were `ingest selects the new learner in state` (state stayed on `mock-004` while the twin belonged to `ui-new-learner`) and `ingest selector shows new learner`.
- Two earlier stub-only artifacts were corrected before this comparison (a browser selects the first option when options are replaced; the server returns 404 for a removed learner). Those corrections are in `tests/frontend/ui_check.js`.

## Backend probes (scratch scripts in `work/probe/`, not part of the suite)

- Non-finite values: before `timing_mae_ms=inf` and NaN in `gesture_metrics` accepted; after, both rejected by the model, and a NaN literal over HTTP returns 422 (`finite_number`).
- Simulate for an unknown learner: 404 before and after.
- Reset of an ingested learner: twin then returns 404, which is the expected server behaviour; the UI now handles it.
- Causality of the bounded window: `work/probe/probe2.py` gave max prefix difference `0.0` for DKT and SAKT at cut points 10, 20, 30 with context 8 and 48 groups.

## Schema validation

- `schemas/attempt-v1.schema.json` regenerated with `python -m axis7.schema` from `Attempt.model_json_schema()`.
- `examples/project-attempt.json` validated with Pydantic (`Attempt.model_validate`) and with `jsonschema` 4.26.0 (Draft 2020-12). A misspelled key (`timing_ms`) is rejected by JSON Schema with "Additional properties are not allowed".

## Research document check

`docs/RESEARCH.md`: mechanical scan for repeated words, double spaces and spacing errors found none. Manual correction of four French/English slips (`concatenation`→`concaténation`, `ties`→`ex æquo` ×3, `rows`→`lignes`, `absence de courant`→`absence de résultat courant`). Facts were not changed; the SingKT field `opern_id` was checked against the supplied notes and is the dataset's own spelling. The document was spot-checked, not proofread line by line.

## Not verified

- **Browser visual verification: not performed.** No browser tool is available in this session (the built-in browser and Chrome tools are not loaded; Figma tools act on Figma files only). Layout, mobile widths, keyboard focus ring appearance and contrast are therefore pending. `docs/preview.jpg` predates the round-3 CSS and JS changes.
- Accessibility contrast was not measured with a WCAG tool.
- Statistical results were not re-run; no retraining was needed (see completion report).
