# Practical protocol: collecting a real DÉCLIC musical knowledge-tracing dataset

This is a **practical team protocol**, not a trained artifact and not a claim that data collection has
happened. It exists because `docs/MUSIC_DATA_V2.md` concludes that no insufficiently licensed or unverified external dataset should be substituted
for DÉCLIC's own musical validity claim, and because the v1 audit's single clearest gap is "no empirical
DÉCLIC learner dataset, teacher adjudication protocol, validated skill ontology." This document is that
protocol, written so a non-ML teammate (a teacher, or another axis owner) can execute it without needing to
read `axis7/models_v2.py` first.

## 1. Decide the rubric and ontology *before* collecting anything

- Pick **one** instrument and **one** concrete skill ontology to start (reuse the six provisional labels in
  `axis7/schema.py::MUSIC_SKILLS` only if a teacher confirms they are pedagogically meaningful for that
  instrument; otherwise define new ones — do not silently keep provisional labels because changing them is
  inconvenient).
- For each skill, write one sentence a teacher would agree captures "what counts as correct" (e.g. "pitch:
  the learner's sung/played note lands within <N> cents of the target note's center for >=X% of its
  duration" — the actual threshold is a teacher/rubric decision, not an ML decision).
- Decide the **outcome granularity** up front: one binary outcome per exercise, or multiple skill
  observations per exercise (atomic group), matching the existing `SkillObservation`/`Attempt` schema
  (`axis7/schema.py`) — the protocol defines what the
  teacher actually fills in, not a new schema.
- Freeze a `rubric_version` string the day the rubric is agreed. Any later change to thresholds gets a new
  `rubric_version`, never a silent edit of the same one (this is what `axis7/schema.py`'s
  `rubric_version` field and the ML-6 audit finding are there to prevent).

## 2. Consent and data-protection steps (do this before the first real learner record)

1. Identify whether any participant is a minor. If yes, the consent process needs **parental/guardian
   consent** in addition to, or in place of, the learner's own consent, per your institution's standard
   ethics process (ESPRIT's own research-ethics guidance, or the relevant conservatory/school's policy if
   data comes from an external partner institution).
2. Write a one-page plain-language consent form stating: what is recorded (attempt-level correctness per
   skill, timestamps, exercise id — **not** raw audio/video unless a separate, explicit consent for that is
   obtained), who can see it (the research team, the teacher), how long it is kept, and that participation
   is optional and does not affect grading.
3. Get the consent form and the ontology/rubric reviewed by the **same teacher** who will grade or validate
   outcomes, before the first session — not after, when relabeling would be needed.
4. Use pseudonymous learner IDs in any exported file (no names, emails, or student numbers in `student_id`);
   keep the mapping from pseudonym to real identity, if one must exist for grading purposes, in a separate
   access-controlled file never checked into this repository.
5. Record provenance explicitly: every real attempt should be stored with `provenance="project"` (per the
   existing `Attempt.provenance` literal in `axis7/schema.py`) so it is never confusable with
   `"synthetic"` or `"public"` rows downstream.

## 3. What to actually log per attempt (mapping onto the existing schema, no schema change needed)

| Field (existing `axis7/schema.py::Attempt` / `SkillObservation`) | What the teacher/app should supply |
|---|---|
| `student_id`, `session_id`, `exercise_id` | Pseudonymous learner id; one id per practice session; a stable id per piece/exercise (**this is the "item id" the v2 models can use — keep it stable across sessions, it is the single most valuable field to get right**) |
| `timestamp` (timezone-aware) | Real wall-clock time of the attempt — enables a *future*, honestly-labelled, time-aware model; do not backfill fake times |
| `observations[].skill_id`, `.outcome` | One row per skill judged in that attempt, binary pass/fail per the frozen rubric |
| `observations[].score`, `.source_confidence` | Optional finer-grained score and the teacher's/system's confidence in that judgment, if available — these already exist in the schema and are already preserved, just not fed to any v1/v2 model as a training input |
| `rubric_version` | The frozen string from step 1 |
| `instrument` | The one instrument chosen for this collection round |

## 4. Minimum viable collection target

- At least enough **distinct learners** to support a learner-disjoint train/validation/calibration/test split
  comparable to FORGET-SE's structure (`ml.md`: 186 learners split 130/14/14/28). A pilot with far fewer
  learners (e.g. 20–40) can still be useful for a **qualitative** pipeline check, but should be reported as
  a pilot, not as a statistically meaningful benchmark — do not present a 20-learner pilot with the same
  bootstrap-CI apparatus as a 186-learner result without flagging the sample-size difference prominently.
- At least a few sessions per learner over real elapsed time (weeks, not one sitting), so that any future
  temporal-forgetting feature has honest, known-unit timestamps to work from — directly closing the
  `log_id`-units gap that currently blocks any time-aware model on FORGET-SE.

## 5. Handoff into the v2 framework once real data exists

1. Export attempts as `Attempt` JSON records validated against the existing `axis7/schema.py` (no new
   loader schema needed).
2. Write a new `load_*` function analogous to `axis7.data.load_forget`, in a new module (not an edit to
   `axis7/data.py` under this agent's ownership boundary — that call belongs to whoever owns `data.py` at
   the time), consuming `axis7.schema.to_record(attempt, vocabulary)` output.
3. Extend and test the explicit domain loader dispatch in `axis7/research_v2.py`; the delivered runner supports
   FORGET-SE and synthetic music. Re-run applicable models, splits and ablations against the new empirical
   domain only after validating the adapter. Do not assume an unimplemented domain registration exists.
4. Only at that point does it become honest to replace "musical demonstration stays synthetic" language
   anywhere in the docs — and only for the specific instrument/skill/rubric actually collected, not as a
   blanket claim.

