# Phase 6 - execution plan and acceptance criteria

1. Scientific repair: strict local timestamp parser, canonical grouping, raw time provenance,
   chronological dataset audit, source schema migration, invalidation of old SingPAD artifacts.
   Accept only zero inversions and zero duplicate time groups; tests must catch genuinely future
   label changes, stale caches, stale checkpoint/configs and inactive artifact requests.
2. Fresh training: DKT-GRU, EnhancedGRU and causal attention, 12-epoch cap, seeds 42/17/83,
   source-disjoint 70/15/15 learner partitions; original seed 42 retained as a corrected historical
   comparator. Select architecture per split on validation alone. Never resume Phase 5 SingPAD.
3. Robustness: same-target history controls (last value, rolling average, EWMA, smoothed
   frequency), cluster bootstrap by learner, error slices and calibration; report negative results.
   AMME repeated learner splits remain research-only. Predefine ablations before test evaluation.
4. Evidence layer: source-concept descriptions, support counts, recurring failures across
   distinct timestamp groups and exercise coverage; never label these as cognitive diagnosis.
5. Product: genuine anonymized held-out demonstration, separate from personal piano,
   clear target/instrument/horizon/version and evidence-derived explanations.
6. Verification: complete regression suite, live inference, browser review, checkpoint tests,
   code review, milestone commits/push and remote CI; no main merge.
7. Academic delivery: executed metrics, comparison caveats, French defense/oral and detailed
   completion status. Unexecuted experiments explicitly pending.

Resource bounds: initially three fixed seeds and existing small architectures; no tuning against
test. Cloud GPU when available, CPU fallback clearly labeled. More complex learned classical
comparators deferred: new production and training contribution remains DL-only as requested;
unfitted historical controls are sufficient for the first robustness contrast.

Existing unrelated untracked files are preserved. AI_TEAM.md and user template files were
absent on inspection; no collaboration protocol invented.
