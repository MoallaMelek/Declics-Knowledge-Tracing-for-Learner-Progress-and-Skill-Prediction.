# Science v2: controlled item-aware knowledge tracing

This describes implemented `axis7/models_v2.py` and `axis7/research_v2.py`. Completed measurements are published only after the immutable experiment finishes; `artifacts/v2/index.json` points to its summary. Historical v1 artifacts are preserved.

## Literature and justified scope

| Candidate | Primary paper / reference code | Decision |
|---|---|---|
| DKT | https://arxiv.org/abs/1506.05908 | Rerun existing GRU adaptation as a matched comparator |
| SAKT | https://arxiv.org/abs/1907.06837 | Rerun existing skill-query attention adaptation |
| simpleKT | https://arxiv.org/abs/2302.06881 ; https://github.com/pykt-team/pykt-toolkit/blob/main/pykt/models/simplekt.py | Item-specific variation plus ordinary attention motivates the compact new attention adaptation |
| AKT | https://arxiv.org/abs/2007.12324 | Research option; full contextual-distance attention not implemented |
| DKVMN | https://arxiv.org/abs/1611.08108 | Valid memory-network alternative, deferred to retain a controlled CPU grid |
| GKT | https://doi.org/10.1145/3350546.3352513 | Learned concept graph is possible, but must not be presented as validated teacher prerequisites; deferred |
| DKT+ | https://arxiv.org/abs/1806.02180 | Reconstruction/waviness regularizers remain a future ablation, not an implemented model |
| DKT+forgetting | https://doi.org/10.1145/3308558.3313565 | Real elapsed-time features require verified timestamp units |
| pyKT | https://arxiv.org/abs/2206.11460 | Supports standardized protocols, atomic groups and disclosure of negative results |

**Correction to preliminary collaborator draft:** AKT uses contextual sequence distance; it does not require known elapsed-clock timestamps. FORGET's unknown clock units do not make AKT impossible. We select plain attention to isolate item/count effects within a modest declared experiment budget. Neither a small KC count nor absent teacher prerequisites proves that DKVMN/GKT cannot work. Their benefit requires another controlled comparison. No existing paper's AUC on another dataset is claimed as our result.

## Implemented candidates and controls

`EnhancedGRU` adds causal exact success/failure counts, previous-item embeddings, known query-item identity and train-only smoothed item difficulty to a GRU backbone. It retains shifted normalized outcomes. It does not implement DKT+ regularization.

`SimpleKTStyleAttention` combines skill, learned position, known query item and difficulty in a query; ordinary four-head causal attention reads memory key j carrying attempt j-1. Query identities from future times are never memory keys. Its head also sees causal per-skill counts. This is an explicitly simplified **simpleKT-inspired adaptation**, not exact paper reproduction or AKT. Learned item offsets are not the original precise Rasch factorization. There are no pretrained audio embeddings, fabricated forgetting durations or prerequisite graphs.

The item is an **atomic exercise bundle**: sorted unique question IDs for a simultaneous FORGET attempt, otherwise an exercise ID. Same-KC duplicate targets share a pre-group forecast but retain each original row's weight. This is not a distinct forecast for each sub-question within a bundle. Vocabulary and Laplace-smoothed difficulty are fitted only on training learners. Unseen/omitted items use fixed UNK embedding and train-only global difficulty. Training-only difficulty is supervised target encoding, not independently validated psychometric difficulty; no within-training cross-fitting is claimed.

Controls: training skill prior; coherent shared-latent grouped BKT with log-domain filtering and recorded optimization diagnostics; PFA count baseline; `item_pfa` with known query-item one-hot, train-only difficulty and causal success/failure counts; `exposure` with skill identity, total prior skill exposure and sequence position but no correctness direction or item/difficulty features. BKT preserves the original bounds/two starts for comparison; those bounds are not asserted optimal.

## Genuine ablations

- `enhanced_gru_no_outcome` removes every learner-history correctness direction, including separate success/failure counts. It retains total exposure, previous-group skill exposure, known items and train-only difficulty. This ablates learner response history, not supervised training labels or item statistics.
- `item_attention_no_item` zeros all past/current item IDs and difficulty while retaining the same attention architecture and history/count inputs.

A baseline-architecture comparison is not an isolated item ablation. Whole-history shuffling can move future evidence into earlier positions and is not implemented. A future prefix-order experiment must explicitly preserve its causal information set.

## Fixed protocol and artifact semantics

`configs/research-v2.json` fixes domains FORGET-SE/music-mock; learner split seeds 2026/2027/2028; neural seeds 7/19; hidden48/context256;28 maximum epochs;patience6;batch24;AdamW lr.002;weightdecay.0001;gradientclip5;CPU2threads;300 learner bootstrap samples. Five statistical controls and six neural variants with two seeds produce17 runs per split,102 planned runs in two domains. All use disjoint70/7.5/7.5/15% train/selection/calibration/test learners.

**Selection sees raw selection log loss only.** Raw test predictions are primary. Temperature fits separate calibration learners; calibrated results are secondary and never determine a winner. Per-run reports include ROC/PR-AUC, log loss, Brier, ECE10, confusion, learner macro scores, per-KC metrics, global-sequence cold/early/warm slices, first-ever-KC exposure and rare-KC-history slices. Paired learner bootstrap intervals compare against the strongest statistical control selected on validation for that split. Bootstrap conditions on checkpoint/test learners; it does not include retraining or external population shift. Split means overlap learners and are descriptive robustness, not independent population replicates.

Long training histories use overlapping windows with unique target ownership and zero target weights in warm context; no tails or groups are dropped. Causal accumulated counts retain the full available prefix, while recurrent/attention memory is bounded. Long inference returns every prediction. Eligibility compaction makes score-only/excluded events no-ops while retaining their displayed evidence timeline. End-padding cannot influence valid causal prefixes.

Each run owns config, learner splits, train-only item state, safe reconstruction JSON, CPU checkpoints, source snapshots/SHA256, Git HEAD/dirty flag, runtime versions, data SHA256, predictions, raw/calibrated metrics, curves and training/inference timing. Reusing an experiment directory or checkpoint refuses overwrite. `index.json` is the mutable convenience pointer; neither historical artifact directory is touched.

## Serving contract

`ResearchPredictor(directory, run_id)` exposes `K`, `name`, `config` and `probabilities(rows, exercise_id=None)` with shape `[len(original_rows)+1,K]`. Raw is default. `calibrated=True` applies the separately fitted secondary temperature. The last row is the next-query forecast; no next exercise means UNK generic forecast. Generic UI forecasts are not the same task as the item-conditioned historical benchmark. The manifest serves all representative split2026 runs and publishes validation-selected overall/neural/baseline defaults, never test-best split selection.

Example:

```python
from axis7.models_v2 import ResearchPredictor
p = ResearchPredictor(checkpoint_directory, run_id)
raw = p.probabilities(rows, exercise_id=None)
secondary = p.probabilities(rows, exercise_id='known-exercise', calibrated=True)
```

### axis7-science-v2.2: no-op/excluded-row serving correction

`ResearchPredictor.serving_implementation_version` is `'axis7-science-v2.2'`, distinct
from and independent of the immutable checkpoint's own training-time
`config['implementation_version']` (`'axis7-science-v2.1'`, written once by
`save_checkpoint` and never rewritten). Checkpoints, predictions and metrics from the
102-run study are unchanged; only the live serving computation in
`research_neural_predict` and `StatisticalControl.probabilities` (`item_pfa`) was
corrected.

**Defect (v2.1 serving):** an observation-only or explicitly excluded original row
(no eligible observation) is dropped by `compact_history` before encoding, and
`expand_forecasts` then mapped that position to the **next eligible row's** own
forecast — which was conditioned on that later row's known exercise/item. Changing a
later exercise therefore silently changed an earlier no-op's displayed
`probability_before` (CLI-reproduced difference: `0.06048` on a small `enhanced_gru`
example; the same expansion path affected `item_pfa`).

**Fix (v2.2 serving):** at every no-op/excluded original position, the forecast is now
a generic forecast conditioned only on the causal prefix up to that point, with the
current query forced to the unknown/UNK item (current-item embedding zeroed,
difficulty set to the fitted `unknown_difficulty`) — never the next eligible row's
real item. Eligible/benchmark rows and the trailing next-query slot are completely
unaffected (bit-identical to v2.1 serving); `dkt`, `sakt` and the `*_no_item` ablation
never used item identity in the first place, so the correction is a verified no-op
for them. See `tests/test_research_v2.py::test_noop_forecast_is_unk_conditioned_not_future_item_leakage`
and `::test_item_pfa_noop_forecast_is_unk_conditioned_not_future_item_leakage` for the
regression, and `work/science-v2-result.md` for the exhaustive proof that this
correction changes **zero** rows of the predeclared 102-run study (every primary
observation in both domains is eligible/binary, so no no-op position exists there at
all; the defect only ever affected live/generic serving of observation-only events).

### Posthoc exploratory control: does EGRU's gain survive a cross-KC-matched baseline?

`scripts/global_history_control.py` (output: `artifacts/v2/exploratory-global-control/`,
status `exploratory_posthoc`, **not** part of this predeclared study, no neural
retraining, no test-set selection) fits a plain L2 logistic regression with the same
cross-KC causal success/failure counts `EnhancedGRU` sees — `item_pfa` here only sees
target-KC counts — on the same 3 fixed splits, and compares it against the main
study's own validation-selected neural model with the same paired-bootstrap method.
On forget-se (the only domain where `enhanced_gru` is actually validation-selected),
all 3 splits' paired 95% intervals against this stronger control include zero: EGRU's
measured advantage over the main study's `item_pfa` baseline does not fully survive
once that one feature-visibility confound (cross-KC vs. target-KC counts) is removed.
This does not show EGRU performs worse than a logistic model; it shows that
recurrence/architecture alone should not be credited with the full gain. Full detail:
`work/science-v2-result.md` §5.

## Limits

FORGET-SE is software engineering; music-mock is synthetic. No musical transfer or learning-gain effect is established. Known items/curriculum can explain forecast gains without proving a cognitive learning model. Eligibility comes from the versioned integration boundary, not a newly trained confidence estimator. More complex candidates may lose and all measured outcomes remain available. Forecasts are not psychological mastery and practice rules remain heuristics.

Known-item benchmark metrics score only the skill(s) actually observed for that item bundle. The K-dimensional vector is an interface convenience: outputs for a skill never associated with a supplied item are not validated cross-skill forecasts. An explicit exercise view should use teacher/catalog skill applicability; an omitted/UNK exercise is an extrapolative generic summary, not the measured item-conditioned test task. No UNK-query augmentation was fitted in this declared study.
