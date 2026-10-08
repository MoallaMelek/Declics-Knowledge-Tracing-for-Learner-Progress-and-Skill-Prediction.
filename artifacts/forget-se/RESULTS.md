# Measured experiments: forget-se

Selected by uncalibrated validation log loss: overall **dkt-7**, best neural **dkt-7**.

Four learner-disjoint sets: train 70%, selection 7.5%, calibration 7.5%, test 15%. Fixed split, three neural initialization seeds; this is not three independent test splits.

| Model | Seed | Test ROC-AUC | Test log loss | Brier | ECE 10 |
|---|---:|---:|---:|---:|---:|
| prior | 0 | 0.5913 | 0.6850 | 0.2460 | 0.1006 |
| bkt | 0 | 0.5854 | 0.6540 | 0.2318 | 0.0548 |
| pfa | 0 | 0.5937 | 0.6581 | 0.2333 | 0.0559 |
| dkt | 7 | 0.7276 | 0.5945 | 0.2042 | 0.0426 |
| dkt | 19 | 0.7213 | 0.5999 | 0.2062 | 0.0511 |
| dkt | 43 | 0.7283 | 0.5953 | 0.2052 | 0.0447 |
| sakt | 7 | 0.7099 | 0.6099 | 0.2122 | 0.0645 |
| sakt | 19 | 0.6962 | 0.6141 | 0.2134 | 0.0514 |
| sakt | 43 | 0.7110 | 0.6043 | 0.2098 | 0.0497 |

Synthetic results validate only the controlled pipeline. FORGET-SE is software engineering, never musical performance. The full-credit threshold is fixed before fitting; tied events predicted together. No timestamp duration/forgetting or item-difficulty effect is claimed.

See results.json for learner-bootstrap intervals, paired log-loss differences versus prior, raw/calibrated metrics, cold/early/warm slices, per-skill metrics, confusion matrices, top errors and learning curves. Undefined AUC is null.

Limited sample and fixed split prevent robust population-wide conclusions. Model selection does not use test metrics; all predeclared model results are disclosed. Calibration can worsen held-out performance. Generic model does not validate musical transfer or pedagogical recommendations.