# Jury walkthrough · about five minutes

Setup: run `Launch.ps1` in this folder and open http://127.0.0.1:8767/. Every step below is an action the interface supports today; nothing is simulated by the slides.

## 1. Frame the claim (30 s)

Say: this is a learning twin built on a knowledge-tracing model. Its probabilities come from saved checkpoints; no language model produces them. The musical data is simulated, and the real benchmark is a software-engineering corpus.

Point at the amber **SIMULATION MUSICALE** badge and the line "transfert musical non validé".

## 2. Inspect a learner's twin (60 s)

- The learner selector shows a simulated profile. Pick another one and the constellation redraws.
- Read the **À surveiller ensuite** line and the sentence under it that explains the rule: lowest forecast among skills with at least three observations.
- Click a skill node, or tab to it and press Enter. The right panel shows its forecast, observation count, and the list of observations behind it, with the forecast before each one.

Say: every number on this panel is a prediction or an observed outcome. Node size is the number of observations. The lines between nodes only mean two skills were observed in the same attempt; they are not prerequisites.

## 3. Replay the history (60 s)

- Drag the timeline slider or press the round play button. The forecasts change as the history grows; the figures shown for each past position use only earlier outcomes.
- Note the "Avant la première observation" marker: before any data, the model shows its learned prior.

## 4. Add a session and watch the twin update (90 s)

- Click **Ajouter une séance simulée**.
- Choose a skill and the scenario "Quatre réussites simulées".
- Click **Incorporer la séance**. The simulated producer creates four outcomes; the saved model receives them and recalculates. The line under the timeline names the two skills that moved most.

Say: the model does not generate its own evidence. The producer is independent of the model and is labelled as simulated.

- Click **Réinitialiser les séances ajoutées** to restore the original history.

## 5. Ingest a project observation (60 s)

- Open **Intégration des observations DÉCLIC** and look at the pre-filled JSON. It follows the versioned schema in `schemas/attempt-v1.schema.json`, with `provenance: project` and a provisional rubric.
- Click **Valider et intégrer**. The record is persisted to `runtime/events.sqlite`.
- Try a malformed event (for example, a misspelled field such as `timing_ms`, or a repeated `attempt_id`): it is refused with a clear message.

Say: the upstream axes send structured outcomes; this axis never sees audio or video.

## 6. Show the evidence for the real benchmark (60 s)

- Switch the domain to **Étude réelle · génie logiciel**. The learners are labelled "Apprenant SE" and no musical label appears.
- Open **Preuves scientifiques**. Read the test table: the selected DKT-7 model has ROC-AUC 0.7276 and log loss 0.5945, against 0.5913 for the training prior.
- Read the limitation card. The paired interval for DKT against the prior excludes zero on this split; comparisons with PFA and BKT are not claimed.

## 7. Close with the boundary (30 s)

Say: this is a research prototype, not a learner record. It has no authentication, no consent workflow, and no validated musical rubric. The next step would be a teacher-validated rubric and a real pilot.

## If something fails during the demo

- Server not responding: restart `Launch.ps1`; checkpoints and data are on disk, so no retraining is needed.
- Learner list empty: the artifacts are missing; see the README "Reproduce and test" section.
- An ingested learner disappears after reset: this is intended; the reset removes profiles created only by ingestion.
