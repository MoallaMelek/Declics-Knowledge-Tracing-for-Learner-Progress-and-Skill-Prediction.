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


# Stabilization decisions

- Start from latest audited application plus DOM tests, 6400c7a, on phase8/stabilization-and-audit-fixes in an isolated worktree.
- Keep the trained neural artifacts and numerical prediction contract. Add provenance and operational checks around them.
- A prepared archive's declared source hash is not the identity of its effective observations. Bind actual content, metadata and actual checkpoint to a serving generation; bind each history/target request separately.
- Keep liveness distinct from readiness; missing private data is an explicit partial state. Do not stop unrelated listeners.
- Use identical equal-concept means in the timeline; keep scientific note-weighted loss unchanged.
- Fixture integration is labeled synthetic and never reported as held-out validation.


# Phase 9 UX decisions

- 2026-10-26 · One navigation, four destinations (Accueil, Parcours, Carnet, Laboratoire). `living.html` keeps its URL and becomes *Parcours*; the Phase 8 engine modules are re-hosted, not rewritten, so the causal guards and their three harnesses keep applying.
- 2026-10-26 · `o08.html`, `musical-demo.html`, `musical-cloud.html`, `case-study.html`, `research.html` become archives reachable from the Laboratoire; the simulated twin is labelled as a simulation everywhere it is linked.
- 2026-10-26 · Observatory (tensors, GRU, logits) only in the researcher view; a plain-language forecast card is the learner default. Descriptive concept list is the default representation; the constellation stays as the exploratory view.
- 2026-10-26 · Fonts self-hosted (OFL, from npm @fontsource): Bodoni Moda (display), Atkinson Hyperlegible Next (text), Atkinson Hyperlegible Mono (hashes/tensor shapes only). The repo stays offline at runtime.
- 2026-10-26 · Design skills read from the user's ~/.agents/skills (impeccable, emil-design-eng, design-taste-frontend, redesign-existing-projects…) without running their scripts or binaries; impeccable's `context` launcher and concept-seed roll were not executed.
