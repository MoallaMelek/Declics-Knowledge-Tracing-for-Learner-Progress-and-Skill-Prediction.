# Measured experiments: music-mock

Selected by uncalibrated validation log loss: overall **pfa-0**, best neural **dkt-7**.

Four learner-disjoint sets: train 70%, selection 7.5%, calibration 7.5%, test 15%. Fixed split, three neural initialization seeds; this is not three independent test splits.

| Model | Seed | Test ROC-AUC | Test log loss | Brier | ECE 10 |
|---|---:|---:|---:|---:|---:|
| prior | 0 | 0.4973 | 0.6750 | 0.2410 | 0.0464 |
| bkt | 0 | 0.6788 | 0.6212 | 0.2164 | 0.0242 |
| pfa | 0 | 0.6872 | 0.6182 | 0.2155 | 0.0321 |
| dkt | 7 | 0.6557 | 0.6304 | 0.2213 | 0.0214 |
| dkt | 19 | 0.6449 | 0.6378 | 0.2240 | 0.0258 |
| dkt | 43 | 0.6502 | 0.6354 | 0.2228 | 0.0138 |
| sakt | 7 | 0.5944 | 0.6592 | 0.2336 | 0.0312 |
| sakt | 19 | 0.5795 | 0.6652 | 0.2364 | 0.0362 |
| sakt | 43 | 0.5868 | 0.6606 | 0.2341 | 0.0192 |

Synthetic results validate only the controlled pipeline. FORGET-SE is software engineering, never musical performance. The full-credit threshold is fixed before fitting; tied events predicted together. No timestamp duration/forgetting or item-difficulty effect is claimed.

See results.json for learner-bootstrap intervals, paired log-loss differences versus prior, raw/calibrated metrics, cold/early/warm slices, per-skill metrics, confusion matrices, top errors and learning curves. Undefined AUC is null.

Limited sample and fixed split prevent robust population-wide conclusions. Model selection does not use test metrics; all predeclared model results are disclosed. Calibration can worsen held-out performance. Generic model does not validate musical transfer or pedagogical recommendations.