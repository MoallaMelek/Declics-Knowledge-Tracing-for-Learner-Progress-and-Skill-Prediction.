# Phase 10 · DÉCLIC utilisable sans instrument (boucle de l'apprenant)

Writer and tester: Claude (claude.ai session, cloud clone + PC linked through the desktop app). Branch `phase10/declic-learner-loop` from `main` @ 7467e8d.

Scope: additive learner loop (`axis7/learning*.py`, `/api/learn`, web pages Séance/Parcours/Exercices/Guide), boot guard + no-cache, navigation, docs. No model/target/protocol/dataset/contract change.

Reports: docs/PHASE10_LEARNER_LOOP.md, docs/PHASE10_MODEL_AUDIT.md, docs/PHASE10_PEDAGOGY.md, docs/GUIDE_SANS_INSTRUMENT.md.

Status 2026-10-27 (cloud): pytest 507 passed / 3 skipped; learner e2e 12/12; living e2e 16/16 (synthetic fixture, real weights). PC acceptance run: see PHASE10_LEARNER_LOOP.md §6.
