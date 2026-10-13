# Phase 4 release validation

Baseline: commit 6a416871f195bb94de5bc7b82b1ca723e95492f5, 162 tests passed in 21.21 seconds.
After implementation: 216 tests passed, zero failures/skips, 24.72 seconds. One pre-existing
Starlette/httpx deprecation warning remains. Command:

    python -B -m pytest -q -p no:cacheprovider

The original tests are unchanged. New coverage: 21 forecast-policy checks, 18 forecast API
integration checks, six musical acquisition/partition checks, five descriptive progression
checks, three end-to-end source/provenance checks and one assessed-attempt safeguard check.
Existing research and musician frontend harnesses retain their actual API-fed checks.

Independent source verification: every acquired object SHA256 verified, every bundled source
byte matches its receipt, and a fresh analyzer reconstruction equals the saved study exactly.
Actual acquisition: 12 original Rach3 MIDI rehearsals, four source pianists; PianoVAM metadata
106 solo records, ten participants. Combined sanitized study:118records,20repeatgroups,
15multidaygroups,0assessedtargets,0newmodels. No musical accuracy metric is fabricated.

The archived synthetic replay actually calls a frozen enhanced GRU via v4. Default abstains;
research mode uses five prior synthetic attempts; the later scripted outcome is revealed and
appended. At the same cutoff, forecast probabilities and evidence IDs remain exactly unchanged.
At the next cutoff, six attempts are visible and the prediction updates. This is an engineering
demonstration, not real-music validation, measured learning benefit or a new training experiment.

Browser verification: default musician progress/abstention rendered; real-data case-study
learner selection and later-session reveal worked; console errors were absent. Phone375x812
and tablet768x1024 document widths matched their client widths (355/747px), without horizontal
overflow. The phone screenshot was saved. Tablet screenshot capture failed; its DOM width
check succeeded. Viewport overrides were restored. No first-time-musician or screen-reader
study is claimed. Actual screenshots and final PDF are delivered outside the source repository.

Historical data/raw, artifacts/v2, artifacts/phase3 and original model directories remain
unchanged.102trainingruns+40stressdiagnostics are preserved with original provenance.
Read-only independent review, final GitHub checks and exact release hashes are recorded in
the final Phase 4 report. No merge into main is performed.
