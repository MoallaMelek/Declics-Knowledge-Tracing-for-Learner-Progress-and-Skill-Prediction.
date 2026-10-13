# Phase 4: licensed practice histories and guarded forecasting

The musician application keeps Accueil, Pratiquer, Ma progression and Mon carnet.
Observed ordinal ratings, descriptive progression, future predictions and teacher-confirmed
development are separate. No teacher confirmation is inferred from a teacher source flag.
The provisional notebook does not update synthetic-trained predictors.

## Executed musical acquisition

See MUSIC_DATA_PHASE4.md and data/music-phase4/README.md for pinned primary sources,
attribution, applicable CC BY-NC-SA 4.0 conditions and exact receipts. Actually acquired:
12 Rach3 MIDI rehearsals across four pianists; PianoVAM raw metadata describing 107 recordings,
of which 106 are solo, across ten solo participants. PianoVAM audio/video was not downloaded.
The sanitized study publishes 118 records, 20 repeated learner/piece groups and 15 groups
spanning distinct calendar days. No performance-assessment targets are available.

Run `python scripts/acquire_phase4_music.py` then `python scripts/analyze_phase4_music.py`.
The first command explicitly downloads pinned releases; the second verifies every source
SHA256 before parsing. Original source bytes are preserved in the acquisition receipts.
Public raw participant names/demographics remain outside the shipped source snapshot.
No fabricated timezone, correctness target, difficulty estimate or mastery score is added.

Rach3 filename prefix: participant, YYMMDD, daily sitting digit, two-digit piece order;
the remaining piece suffix is retained verbatim. Its README's claimed 12-character suffix
conflicts with the inspected 14-character source suffix and is not enforced.
PianoVAM timestamps are local wall-clock values with unspecified timezone. Group by
participant and exact source piece, then hold out the final whole calendar day. Single-day
groups are excluded from the future-day comparison. This is a descriptive within-learner
partition, not learner-disjoint KT validation. Rach3's four participants cannot support
credible population-level neural validation even if later labels become available.

## Scientific result

Zero musical assessment targets, zero newly trained models, and no established real-music
predictive validity. DKT, enhanced GRU, attention, BKT/PFA/statistical models are retained;
none is retrained on duration or MIDI note counts as pretend correctness. ROC-AUC, PR-AUC,
log loss, Brier, calibration and confidence intervals on these acquired records are not
applicable to the requested assessment task and are not invented. Historical 102 training
runs and 40 stress evaluations remain unchanged and keep their original definitions.

SingKT and OcarinaKT were rechecked at the exact prior commits. Neither source supplied
an applicable raw-data reuse grant. SingKT native binary annotations and completion
timestamps make it a promising conditional study; OcarinaKT also needs chronology,
score-array semantics and 35-vs-36-KC reconciliation. No raw CSV was acquired from either.
Author permission would be a future human action, not an email sent by this implementation.

## Descriptive progression and recommendations

`axis7.progression` compares the latest same-exercise/source/provenance cohort. Its strict
ordinal improvement description requires each of the last three ratings to exceed every
rating in the previous three. Overlap is mixed/stable, not proven improvement. Low-confidence
ratings below 0.6 are excluded from these comparisons and their IDs remain auditable;
the threshold is a provisional safeguard, not empirically optimized reliability.
Recommendations rank current comparable cohorts and retain supporting attempt IDs,
coverage alternatives and source identity. Exercise difficulty remains the demonstration
catalogue's introductory descriptor: it is not learned item difficulty. Prerequisites are
not teacher-approved, and prediction_informed/used_model_predictions remain false.
No heuristic is represented as an optimal or prospectively effective learning strategy.

## Working demonstration

Start `python -m uvicorn axis7.server:app --host 127.0.0.1 --port 8771`, open the homepage and use the notebook.
Ma progression shows actual recorded ratings and explicit prediction abstention.
Research mode links `/web/case-study.html`: choose a real published piano history, see only
earlier days, ask whether prediction is possible, then reveal the held-out later day.
The revealed object is an actual recording descriptor, not a held-out assessed outcome.
The page states that no musical model was trained and no improvement can be inferred from
duration. The API is `GET /api/research/music-case-study`.

Version 4 forecasting is additive; see TEAM_PHASE4.md. The default returns an auditable
abstention. Explicit synthetic research mode can query actual retained frozen predictors
at a strict prior-history cutoff, with future/equal-cutoff outcomes excluded. Real/project
musical evidence and the unreviewed notebook cannot become validated probabilities.

## Objective-source revision found

Phase 3 correctly reported that its scoped source inventory lacked revision 1-2. During
Phase 4, the file was found at C:/Users/moall/Downloads/Declic_Deep_Learning_Objectives-1-2.pdf
and extracted in full. Its overview lists learner prediction as O09 and corrective feedback
as O08; its final detailed section instead labels learner prediction O08. O03 still cites
gaze datasets despite describing score/performance alignment. This is an internal source
conflict, not a reason to silently alter v3 mappings. The contract remains explicitly
cached-objectives-1-1 until the team resolves numbering/ownership. Axis 7 responsibilities
remain clear: forecasting from assessed histories, without implementing the other six axes.

## Next eligible real training study

Archive a source-specific applicable grant; pin raw bytes and reconcile source counts;
audit chronology and target annotations; split whole completed performances without
current-target leakage; preserve source KCs. For sufficiently many learners, split
train/selection/calibration/test by learner, use multiple training seeds and validation-only
hyperparameters, compare feature-matched statistical controls, and report valid-target
metrics with learner-cluster intervals/cold-start/per-skill/calibration results. For four
pianists, use a bounded within-learner future-session study with explicit limits instead.
Do not expose real predictions in the musician UI before instrument/rubric/query scope
and uncertainty are validated. Recommendation benefit still needs prospective evidence.
