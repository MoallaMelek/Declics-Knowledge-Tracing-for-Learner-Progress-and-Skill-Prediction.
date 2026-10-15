# Handoff · architecture critique request (Claude → Codex, read-only)

Objective: critique the Phase 8 presentation-adapter design before implementation, focusing on temporal leakage and scientific honesty.

Constraints: no change to models, training, preprocessing, evaluation, registry, or existing endpoints. Served inference must remain `axis7/musical_api.musical_forecast` (EnhancedGRU). Classical ML never on the user path. Learner ids never leave the server. Private data in `runtime/musical-demo/*-prepared.json.gz` (gitignored).

Relevant files: docs/PHASE8_ASSIMILATION.md, docs/PHASE8_VISUAL_ARCHITECTURE.md, axis7/o08_demo.py, axis7/musical_api.py, axis7/skill_states.py, axis7/cloud_training.py (encode, split_learners, public_split_provenance), scripts/build_musical_demo.py.

Decisions already made: per-cutoff replay router `/api/v7/o08/living` (learners, state, reveal, inspect); first 8 test learners in split order with >= 6 steps; step c's exercise id + evaluated concept ids are exposed as the query definition (as in training/BenchmarkQuery) but not its outcomes; total step count disclosed; client caches visited cutoffs only, no prefetch; hidden states captured by a forward hook on `model.encoder`; reference errors (train-mean constant from metrics.json, learner's own past mean) shown at reveal.

Tests so far: baseline suite 315 passed on 3634fa9.

Uncertainties: (1) is exposing the next step's evaluated concept ids acceptable leakage-wise; (2) is disclosing total history length acceptable; (3) any way the forward-hook inspection could diverge from the served forecast; (4) selection rule bias; (5) anything in the design that would mislead a professor.

Response wanted: critique. Include risks, recommendation, alternatives considered, confidence level. Keep it under 500 words.
