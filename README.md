# DÉCLIC · Axis 7 — Musical Learning Intelligence

A working local research prototype: independently trainable knowledge tracing, a held-out public benchmark, an explicit observation interface, and an interactive musical learning twin. Probabilities come from trained checkpoints. No LLM produces learner predictions. No video generation is used.

Axis 7 is the longitudinal intelligence component of a seven-person ESPRIT music-learning project. The other six axes own pitch, rhythm, alignment, performance quality, technique and instrument recognition. This repository consumes their observations through versioned contracts; it does not implement their perception models.

## Version 2 upgrade

- Corrected grouped BKT likelihood and stable filtering; score-only and excluded observations leave binary model state unchanged.
- Strict v2 input contracts, six mock producers, confidence/rubric eligibility, transactional chronology and idempotent retries.
- Enhanced GRU with causal success/failure history and training-only exercise difficulty; a declared simpleKT-inspired item attention adaptation.
- Repeated learner splits, separate model selection/calibration learners, exercise/exposure controls and genuine outcome/item ablations.
- Interactive skill maps, trajectories, evidence inspection and two explainable practice heuristics, with explicit provenance and validity limits.

The controlled study configuration is [research-v2.json](configs/research-v2.json). Completed results are published atomically under `artifacts/v2/index.json`; the interface does not report incomplete runs as final evidence. Full methods and model-selection rationale are in [SCIENCE_V2.md](docs/SCIENCE_V2.md).

## Completed controlled study

The fixed-budget v2 study completed **102 runs**: two domains, three learner splits, two neural initialization seeds, five statistical controls and six neural variants. These descriptive means average initializations within each split, then splits; overlapping learner splits are not independent population replications.

| Real FORGET-SE model | Mean ROC-AUC | Mean raw log loss |
|---|---:|---:|
| DKT GRU | 0.7203 | 0.6066 |
| Exercise-aware PFA control | 0.7266 | 0.5980 |
| Enhanced GRU | **0.7610** | **0.5689** |
| Enhanced GRU without learner outcomes | 0.7237 | 0.6045 |
| Item attention adaptation | 0.7263 | 0.6004 |

Validation selected enhanced GRU on each real-data split. Its paired learner-bootstrap raw-loss difference against the validation-selected strongest statistical control was negative on all three splits. The exercise-aware attention adaptation did not clearly improve the comparison; its negative result is retained. This does not isolate recurrence from the enhanced model's cross-skill features, and no psychological mastery or musical transfer is established.

On **synthetic music**, plain PFA and exercise-aware PFA had similar mean raw losses (0.6191 and 0.6196), compared with enhanced GRU (0.6270), DKT (0.6353) and item attention (0.6461). That small descriptive gap does not establish a statistical winner. The default musical neural demonstrator remains DKT-7, selected on the representative split's validation loss, with the validation-selected overall statistical winner disclosed. Architecture complexity is not treated as success.

Full [results](artifacts/v2/axis7-v2-20261013-controlled/RESULTS.md), [machine summary](artifacts/v2/axis7-v2-20261013-controlled/summary.json), per-split predictions, calibration, skill/history slices, intervals, checkpoints and source snapshots remain available. Historical v1 outputs below retain their original calibrated semantics and are not silently pooled with v2 raw results.

## Open the demonstration

Run `Launch.ps1` from PowerShell in this folder. On this delivery machine it finds the prepared environment automatically. Open **http://127.0.0.1:8767/**. Keep the server window running; press Ctrl+C to stop it.

On another machine, use Python 3.12 or newer and create an environment first:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m uvicorn axis7.server:app --host 127.0.0.1 --port 8767
```

The checkpoints and benchmark data are included; opening the demonstration requires no retraining or account. The interface loads no external fonts, scripts, or services and needs no network connection. There is no cloud prediction service.

## Explore the twin

1. Start in **Atelier musical · simulation**. Select a skill to inspect its forecast, observed successes/errors, history, and variation across initializations.
2. Replay sessions or move the history slider. Earlier predictions never consume later outcomes.
3. Open **Ajouter une séance simulée**, choose a skill and scenario, and incorporate it. An independent mock producer creates four outcomes; the saved model then updates its predictions. The model does not manufacture its own evidence.
4. Switch to **Étude réelle · génie logiciel** to inspect held-out FORGET-SE histories without relabelling them as musical skills.
5. Open **Preuves scientifiques** for the measured model comparison and plots. **Détail du modèle** exposes alternate saved models.

Node size reflects usable evidence count. Graph links mean co-observation in one attempt; they are not learned prerequisites. The default practice policy combines forecast fragility, recent failures, recurring errors and generic forecast change; a second policy prioritizes the lowest forecast. Both require three usable observations. These explicit rules have not been validated for learning gains. Seed ranges are model variation, not individual confidence intervals or psychological mastery. V2 curves disclose known attempted-exercise conditioning; the current next forecast uses an unknown exercise unless one is explicitly requested.

## Historical v1 measurements, preserved

The real, licensed fallback is **FORGET-SE v1**, a software engineering corpus with 10,873 observations from 186 learners. After atomic grouping of tied timestamps there are 10,307 attempts. The declared target is *full credit*, not arbitrary conversion of every continuous score to a musical outcome. See [data attribution](data/DATA_LICENSE.md).

Training, selection, calibration, and test learners are disjoint. The fixed split has 130/14/14/28 learners. Three neural initialization seeds share this split. Model selection uses validation loss; temperature scaling uses separate calibration learners.

| Model, representative run | Real test ROC-AUC | Real test log loss |
|---|---:|---:|
| Training skill prior | 0.5913 | 0.6850 |
| BKT | 0.5854 | 0.6540 |
| PFA | 0.5937 | 0.6581 |
| DKT-style GRU, seed 7 | **0.7276** | **0.5945** |
| SAKT-style attention, seed 7 | 0.7099 | 0.6099 |

DKT seed 7 was selected on validation, not on these test numbers. Its learner-bootstrap test AUC interval is approximately [0.6948, 0.7572], conditional on this trained model and split. All runs, raw/calibrated metrics, learner macro scores, skill slices, early-history slices, confusion matrices, errors, and bootstrap results are in [real results](artifacts/forget-se/RESULTS.md) and `results.json`.

On synthetic musical data, **PFA wins overall**; DKT is the best neural candidate. The musical view defaults to DKT to demonstrate the neural integration, with the overall winner disclosed and selectable. See [synthetic results](artifacts/music-mock/RESULTS.md). These measurements do not validate musical transfer.

## Reproduce and test

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m axis7.train --domain all
```

If using this delivery machine's prepared environment, substitute `..\..\work\.venv\Scripts\python.exe`. Historical training now refuses to overwrite existing results; use `--output-root artifacts/new-study` to create a fresh legacy comparison. The v2 framework is run with `python -m axis7.research_v2 --config configs/research-v2.json --experiment-id YOUR-NEW-ID`; every study ID is immutable. It evaluates two domains across split seeds 2026/2027/2028, with neural seeds 7/19, 28 maximum epochs and early stopping, five statistical controls and six neural variants (102 runs). This is a fixed-budget comparison, not an exhaustive tuning study.

Regenerate input schemas with `python -m axis7.schema` and `python -m axis7.contracts`. Exact installed versions are in `requirements.lock.txt`. CI checks JavaScript syntax and the Python/API/frontend regression suite. The old [validation](docs/VALIDATION.md), [design](docs/DESIGN_CHANGES.md) and [completion](docs/COMPLETION_REPORT.md) documents describe the historical v1 delivery; consult the v2 upgrade documentation for current behavior.

The frontend regression test runs `web/app.js` under Node.js when it is installed; without Node it is skipped. Tests cover current/future label leakage in recurrent, attention, and baseline models; atomic duplicate targets; disjoint learner splits; strict observation validation; persisted API ingestion; model reload reproducibility; simulated updates/reset; and displayed historical prefix invariance. API tests use an isolated temporary database.

## Integrate DÉCLIC observations

[Integration guide](docs/INTEGRATION.md) and [JSON schema](schemas/attempt-v1.schema.json) define the boundary. Axes 1–6 retain ownership of media analysis and rubric decisions. Axis 7 consumes versioned, timestamped skill observations only. New pseudonymous learners can be created by their first valid project event. Raw media is neither required nor accepted by this interface.

Added observations persist locally in `runtime/events.sqlite`; attempt IDs are unique across all learners, and NaN, infinite, or misspelled fields are refused before storage. The reset control removes added events for the selected learner; supplied benchmark and mock fixtures remain intact. Export is an analysis snapshot of the internal history, not a canonical event format for re-import.

## Evidence and limits

- [Research and project-document synthesis](docs/RESEARCH.md): all supplied sources, axes mapping, datasets, model literature, and validity requirements.
- [Architecture](docs/ARCHITECTURE.md), [model card](docs/MODEL_CARD.md), [source inventory](docs/SOURCE_MANIFEST.json).
- [Claude architecture critique](docs/CLAUDE_REVIEW.md) and [design critique](docs/CLAUDE_DESIGN_REVIEW.md).

The musical taxonomy and rubric are provisional. No DÉCLIC learner study has been performed. Repeated splits overlap learners, so their standard deviation is descriptive rather than three independent population replications. Exercise features use training-only atomic bundle statistics; they are not teacher-validated psychometric difficulty. Unknown timestamp units prevent elapsed-time forgetting claims. BKT parameters are not validated individual mastery states. Recommendations have no causal evaluation. Neural implementations are declared adaptations, not exact paper reproductions. The runtime is a single-user loopback demonstration, without production authentication, consent management, authorization, or a student-record deployment.

Music data decisions: [rights investigation](docs/MUSIC_DATA_V2.md) and [teacher data-collection protocol](docs/MUSIC_COLLECTION_PROTOCOL.md). A paper's open license is not assumed to grant rights to an undistributed raw dataset. Until rights and longitudinal suitability are established, music results remain explicitly synthetic.

The user's original `declic` source folder was preserved. The requested global AI_TEAM/AGENTS templates were unavailable; no protocol was fabricated. Read-only Codex CLI reviews and Claude CLI consultation worked under the user's explicit authorization.


The separate [exploratory global-history control](artifacts/v2/exploratory-global-control/RESULTS.md) uses a plain logistic model with cross-skill history features. Its paired intervals against the validation-selected neural models on FORGET-SE all include zero. EGRU retains a small numerical advantage, but this experiment does not establish an architecture-specific advantage over the stronger control. This posthoc diagnostic is separate from the fixed 102-run study. Reproduce it with `python scripts/global_history_control.py --output artifacts/new-global-control`.

Final local verification: 92 tests passed (81.18 seconds), including 19 frontend checks. All 102 saved checkpoint predictions were reconstructed exactly; see [verification](artifacts/v2/checkpoint-verification.json).
