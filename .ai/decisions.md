# Decisions

- 2026-10-15 · Per-cutoff causal replay served by a new read-only router reusing `musical_forecast`; the existing 3-group demo case is too short for a time machine. Learners: first 8 held-out test learners in split order with >= 6 steps (01 = Phase 7 demo learner); never selected by error.
- 2026-10-15 · No prefetch of later cutoffs on the client; only visited cutoffs are cached, so outcomes never sit in memory before the user reaches them.
- 2026-10-15 · Fixed concept layout (angle = 2πk/K, hashed radius): vocabulary-only, cannot encode the future, shared with the fingerprint.
- 2026-10-15 · Vanilla JS + SVG, no dependency (repo is offline and dependency-free; CI runs node --check).
- 2026-10-15 · Dark observatory identity scoped to the new page; docs/DESIGN.md (twin page) unchanged.
- 2026-10-15 · Absolute SingPAD timestamps are not sent; the UI uses day offsets from the learner's first step.
- 2026-10-15 · Codex consult (fresh read-only session, .ai/handoffs/2026-10-15-architecture-consult.md) adopted: forecasts labelled retrospective and conditional on the recorded exercise/concepts; total length labelled as navigation metadata; inspection on a deep copy of the model; eligible/excluded counts published; references scored on identical notes with concept-specific history.
- 2026-10-15 · Edges shown by default only for pairs co-evaluated in >= 2 past steps (all pairs of the selected concept): readability, still observed structure.
- 2026-10-15 · Yousician forecasts formatted "x / 100" like the Phase 7 UI (continuous score, not a probability).
