# DÉCLIC · Axis 7 — Learning Digital Twin

A working local research prototype: independently trainable knowledge tracing, a held-out public benchmark, an explicit observation interface, and an interactive musical learning twin. Probabilities come from trained checkpoints. No LLM produces learner predictions. No video generation is used.

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

Node size reflects evidence count. Graph links mean co-observation in one attempt; they are not learned prerequisites. The lowest forecast among skills with at least three binary observations drives the visible practice suggestion. That explicit rule has not been validated for learning gains. Seed ranges are model variation, not individual confidence intervals or psychological mastery.

## What was actually measured

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

If using this delivery machine's prepared environment, substitute `..\..\work\.venv\Scripts\python.exe`. Training overwrites the corresponding artifact directory. Schema and example: `.\.venv\Scripts\python.exe -m axis7.schema` regenerates the JSON Schema. Delivery documents: [demo script](docs/DEMO_SCRIPT.md), [validation record](docs/VALIDATION.md), [design changes](docs/DESIGN_CHANGES.md), [completion report](docs/COMPLETION_REPORT.md). The preregistered configuration is [configs/experiment.json](configs/experiment.json); exact installed versions are in `requirements.lock.txt`. CPU training uses seeds 7, 19, and 43. The generator is deterministic. Checkpoints, learner splits, original data metadata, predictions, audit, and figures are included.

The frontend regression test runs `web/app.js` under Node.js when it is installed; without Node it is skipped. Tests cover current/future label leakage in recurrent, attention, and baseline models; atomic duplicate targets; disjoint learner splits; strict observation validation; persisted API ingestion; model reload reproducibility; simulated updates/reset; and displayed historical prefix invariance. API tests use an isolated temporary database.

## Integrate DÉCLIC observations

[Integration guide](docs/INTEGRATION.md) and [JSON schema](schemas/attempt-v1.schema.json) define the boundary. Axes 1–6 retain ownership of media analysis and rubric decisions. Axis 7 consumes versioned, timestamped skill observations only. New pseudonymous learners can be created by their first valid project event. Raw media is neither required nor accepted by this interface.

Added observations persist locally in `runtime/events.sqlite`; attempt IDs are unique across all learners, and NaN, infinite, or misspelled fields are refused before storage. The reset control removes added events for the selected learner; supplied benchmark and mock fixtures remain intact. Export is an analysis snapshot of the internal history, not a canonical event format for re-import.

## Evidence and limits

- [Research and project-document synthesis](docs/RESEARCH.md): all supplied sources, axes mapping, datasets, model literature, and validity requirements.
- [Architecture](docs/ARCHITECTURE.md), [model card](docs/MODEL_CARD.md), [source inventory](docs/SOURCE_MANIFEST.json).
- [Claude architecture critique](docs/CLAUDE_REVIEW.md) and [design critique](docs/CLAUDE_DESIGN_REVIEW.md).

The musical taxonomy and rubric are provisional. No DÉCLIC learner study has been performed. The small single test split, curriculum/exposure shortcuts, unmodelled item difficulty, and unknown timestamp units limit interpretation. BKT parameters are not validated individual mastery states. Recommendations have no causal evaluation. The SAKT and GRU implementations are declared variants, not exact paper reproductions. The runtime is a single-user loopback demonstration, without production authentication, consent management, authorization, or a student-record deployment.

The user's original `declic` source folder was preserved. The requested global AI_TEAM/AGENTS templates and Codex CLI executable were unavailable; no protocol was fabricated. Claude CLI consultation worked under the user's explicit authorization.
