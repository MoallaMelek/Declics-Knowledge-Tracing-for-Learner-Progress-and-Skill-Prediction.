# Music data: verified rights, chronology and integration decision

Primary-source verification date:2026-10-13. No external musical logs have been acquired or used for training in this release. Music-mock remains explicitly synthetic. Software-engineering results are a generic methods benchmark.

## SingPAD / SingKT

The EDM2024 paper and authors' repository document real sight-singing histories, learner/score/record IDs, completion timestamps and note-level outcomes/KCs. They are a promising external musical methods benchmark, not DÉCLIC piano learners or teacher-approved DÉCLIC rubrics.

Sources: https://educationaldatamining.org/edm2024/proceedings/2024.EDM-short-papers.30/index.html ; https://github.com/itec-hust/singKT-dataset

**Important correction:** https://zenodo.org/records/12729828 is explicitly a CONFERENCE PAPER deposit. Its file list contains only `2024.EDM-short-papers.30.pdf`,608.6KB,MD5`bb31cd8b696eb881f8652acde5a61e82`. It does not deposit any raw CSV. An open-access/paper license is not an applicable raw-data grant. A preliminary collaborator draft incorrectly treated this paper record as a CC BY licensed dataset release; that conclusion has been removed. No explicit adequate raw-data license was established in the inspected data repository.

Before training acquisition: pin an actual data release; obtain an applicable explicit data grant/license; independently inspect chronology, learner IDs, score scales, atomic multi-note attempts and mapping. Do not feed total lifetime practice counts or current-attempt aggregates as historical inputs. All notes in the next attempt stay hidden until the attempt forecast. Use the source corpus ontology rather than forcing it into six provisional skills. External singing validation would be a legitimate limited methods claim, not DÉCLIC-specific musical transfer.

## OcarinaKT / MPKT

OcarinaKT EXISTS: https://github.com/itec-hust/ocarinaKT-dataset . The authors document1442 learners, level progression restricted to users passing earlier levels, pitch/rhythm score sequences, note question/skill mappings and36 skills spanning pitch, fingering transitions, note values and rhythmic patterns. Record fields list user_id,opern_id,record_id,pitch_score,rhythm_score; no completion timestamp or explicit dataset license was found in the inspected root/README. Record ID ordering and score scale need verification. Passing-level selection affects curriculum/population generalization.

Related MPKT paper: https://link.springer.com/chapter/10.1007/978-3-032-29755-6_50 . This is musical KT research, not a locally implemented architecture or independently licensed dataset in this repository. Preliminary statements that OcarinaKT could not be located were false; the prior `RESEARCH.md` already identified the primary repository/chapter. Published paper AUCs are not our measurements.

Decision: do not acquire/train until raw-data rights, score scale and chronological ordering are established. No external contact has been sent.

## Practical path

The prior inventory identifies Rach3 MIDI (https://github.com/Rach3Project/rach3_midi_dataset), with an explicit CC BY-NC-SA license but only four learners and no ready KT correctness ontology. It may support a labelled longitudinal case study after alignment/teacher rubrics, not robust population generalization. Static audio/video assessment datasets do not become longitudinal KT by renaming raters as learners.

The immediately runnable study uses FORGET-SE v1 under its explicit CC BY4.0 grant and deterministic synthetic music. `MUSIC_COLLECTION_PROTOCOL.md` defines the teacher/institution-reviewed route: one instrument, frozen rubric/version, multiple sessions, independent adjudication, pseudonymous learner IDs, stable exercise IDs and approved participation/retention procedures. No collection or teacher approval has happened here.
