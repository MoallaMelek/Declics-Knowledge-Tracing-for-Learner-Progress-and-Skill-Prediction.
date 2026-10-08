# Model card · Axis 7 research prototype

## Intended use and output

Local research evaluation and demonstration of history-conditioned success forecasts. Output is a probability of a binary success on a comparable future attempt for a specified skill. It is not a psychological mastery score, diagnosis, grade, or entitlement decision. A skill-conditioned forecast does not control for exercise difficulty.

## Models

Training-only Laplace skill prior; constrained four-parameter BKT without explicit forgetting; PFA using skill identity and log success/failure counts; DKT-style GRU; SAKT-style multihead causal skill-query attention. Neural hidden size 48, context 256, at most 35 epochs, validation early stopping, seeds 7/19/43. Longer histories use bounded sliding contexts; test targets are not silently dropped. GRU and attention models are adaptations with atomic multi-observation targets.

The current attempt is never an input to its own prediction. Simultaneous same-learner events are grouped before any state update. Model selection is separated from temperature calibration and learner-held-out testing. Temperature is fitted per model, bounded to [0.5,5]. All models and initialization results are reported, including worse calibration outcomes.

## Training data and evaluation

FORGET-SE v1, CC BY 4.0, 186 learners / 10,873 rows / 56 questions / 10 skills; full-credit target fixed before fitting. Original timestamp units are unknown, so only chronological ordering is used. Synthetic musical generator: 280 profiles, 12 sessions, provisional six-skill piano vocabulary. Mock labels do not originate from the fitted KT model. No real musical transfer evaluation exists.

Learner-disjoint split 70/7.5/7.5/15%, split seed 2026. Three initialization seeds on one split are not repeated independent evaluation. Reported metrics include ROC/PR-AUC, log loss, Brier, ECE, accuracy, F1, confusion, learner macro performance, skill/history slices, and learner bootstrap intervals. Undefined AUC is null. The 300-replicate bootstrap holds the trained checkpoint and split fixed; it does not account for retraining uncertainty or population shift. On FORGET-SE, the paired learner-bootstrap interval for the selected DKT-7 log loss minus the training prior is [-0.125, -0.054] (negative favours DKT), which excludes zero on this split. Paired intervals against PFA and BKT are not implemented and no such claim is made.

## Interpretation and risks

The real benchmark selected DKT seed 7; synthetic data selected PFA. Neither outcome proves that attention or deep learning universally wins. Small held-out samples, exposure/scheduling shortcuts, BKT identifiability, and unmodelled exercise difficulty remain limitations. There is no exposure-only ablation or cross-corpus transfer result. A larger and stronger model such as AKT remains a research option rather than an implemented result.

Individual seed ranges describe initialization sensitivity, without calibrated coverage. Evidence lists show observations associated with the history, not explanations of the network's causal reasoning. Co-observation edges are descriptive. The minimum-probability practice rule has no prospective or causal learning-gain validation. Prototype results must not be used for consequential student decisions.

## Reproducibility

Configuration, dependency lock, original licensed CSV and metadata, fixed learner splits, saved CPU checkpoints, per-observation predictions, curves, metrics, and tests are supplied. The README explains launch, retraining, and limitations. The synthetic and software-engineering domains remain separate in training, inference, and presentation.
