# Phase 8 · Assimilation report (read-only audit)

Author: Claude Code (frontend / visualization lead for O08). Written before any code change.
Base verified: branch `phase7/personalized-musical-learning`, commit `3634fa9`, identical to
`origin/phase7/personalized-musical-learning`. Local suite on that commit: **315 passed** (33 s).
Working tree had only unrelated untracked files (CV assets, `loyalty-platform/`,
`portfolio-cv-update/`, `tmp/`), none touched. Phase 8 work happens in a separate worktree on
`phase8/living-learner-ux`, so the Deep Learning agent's tree is never written.

## 1. Verified repository structure

| Path | Role (verified in code) |
|---|---|
| `axis7/` | FastAPI backend + training/evaluation code. `server.py` mounts every router and serves `web/` at `/web`. |
| `web/` | Static pages, **vanilla JS, no bundler, no npm, no external fonts/CDN**. |
| `tests/` | 315 pytest tests; `tests/frontend/*.js` drive the real `app.js` / `musician.js` in a Node VM with a stubbed DOM. |
| `artifacts/models/musical-cloud/` | Checksummed registry; `active.json` selects the served model per source. |
| `artifacts/phase5..7/` | Reports, figures, `phase7/summary.json` (all 36 Phase 7 runs, controls, calibration, stress). |
| `runtime/` (gitignored) | Private: `musical-demo/{singpad,yousician}.json` (one demo case each) and `*-prepared.json.gz` (all learners of each source, prepared by `cloud_training.prepare`). |
| `scripts/`, `notebooks/`, `configs/`, `schemas/` | Reproduction, Colab notebooks, experiment configs, JSON contracts. |
| `.github/workflows/validate.yml` | CI: `node --check` on each page script, then full pytest on Python 3.12 CPU. |

## 2. Frontend stack

Server-rendered static HTML + one script per page. Pages: `/` (`index.html`/`app.js`, piano
notebook twin on the *synthetic* `music-mock` domain, already has an SVG "armillary" constellation),
`musician.js`, `/web/o08.html` (Phase 7 three-step demo), `/web/musical-cloud.html` (Phase 6
research), `research.html`, `case-study.html`. Two visual identities coexist: the twin's
"ebony & felt" system (`docs/DESIGN.md`) and the O08 paper/green/gold Georgia-serif look (`o08.css`).

## 3. Backend and API architecture

`axis7.server:app` includes: practice, team_v3 (`/api/v3/evidence`), forecast_v4, musical_api
(`/api/v5/musical/*`), prospective (`/api/v6/o08/*`, admin-token gated, field predictions abstain),
o08_demo (`/api/v6/o08/demo/history|predict|reveal|research`). `O08BodyLimit` caps `/api/v6/o08*`
bodies at 512 KiB. The O08 demo chains HMAC-signed tickets: `history` (no target) → `predict`
(runs `musical_forecast`) → `reveal` (only accepts a *predicted* ticket, returns observed target).

**Data flow traced.** private prepared rows → `BenchmarkQuery` (validates source/time format,
one row per day for continuous sources) → `musical_forecast`: checks active registry, domain,
vocabulary, exercise support; drops any row with `time >= query_time`; abstains with < 2 atomic
groups; `encode()` builds strictly-past features; windowing identical to training; `sigmoid`
of the last step → `predictions[concept]`. `skill_states()` raises if any row is not strictly
earlier than `query_time`. The frontend renders tables/SVG from these responses.

## 4. Deep Learning models and roles

| Served (active.json) | Architecture | Data | Test metric vs train-mean reference |
|---|---|---|---|
| `singpad-enhanced_gru-s42-8576d5ba1d6a` | EnhancedGRU, K=270, hidden 48, context 64, 88 item ids | SingPAD, corrected chronology (Phase 6, GPU T4) | log-loss 0.5175 vs 0.5653; ROC-AUC 0.699 |
| `yousician-enhanced_gru-s42-77455ae03f05` | EnhancedGRU, K=1, no items | Yousician active days (v1) | MAE 0.0905 vs 0.1092 |

EnhancedGRU (`models_v2.py`): per step `x[4K]` = previous group's failure/success fractions (2K),
`log1p` cumulative successes and failures (2K, strictly earlier); + previous-item embedding (12) +
difficulty (always 0 here) → GRU(48) → head on `[hidden, current-item embedding, difficulty,
cumulative counts]` → MLP → K logits. **No attention in the served models.** Attention
(`item_attention`) checkpoints exist in the registry but are inactive; DKT/SAKT belong to the
legacy synthetic twin. The 36 Phase 7 CPU weights are research artifacts, explicitly not promoted.
Classical controls (logistic, PFA, Ridge, boosted trees) exist only in research scripts/summary.

## 5. Datasets and supported targets

| Source | Unit | Target actually predicted | Served |
|---|---|---|---|
| SingPAD | timestamp group of recordings | note-success probability per **source concept id** in the next group, given its known exercise | yes |
| Yousician | active signup day | aggregated success fraction of the next active day | yes |
| AMME | ordinal block | next-block melodic similarity (not correctness) | research only |

Concepts are integers only: `configs/source-skill-mapping.json` has **zero validated mappings**;
`skill-taxonomy-review.json` has zero approved mappings. No concept names, no concept relations,
no piano transfer exist. Yousician has no exercise ids and no per-attempt identity.

## 6. Existing user journeys

1. `/web/o08.html`: choose source → see 3 past groups + descriptive states → run GRU → reveal.
2. `/`: provisional piano notebook (synthetic-trained, abstains for real piano claims).
3. `/web/musical-cloud.html`: Phase 6 evidence and research tables.

## 7. Existing visual components

O08: one SVG polyline of 3 group scores + data table, state cards, prediction tiles, technical
table, research tables. Twin: SVG armillary constellation of 4 *provisional synthetic* skills.
Nothing visualizes cutoffs, concept evidence over time, model internals or past forecast errors.

## 8. Scientific constraints to preserve

Learner-disjoint splits (public digests only); strictly-past encoding; equal timestamps hidden
together; abstention for < 2 groups, unseen exercise, inactive model, wrong domain; descriptive
states ≠ mastery (policy `source-skill-state-v1`: ≥3 groups, ≥10 notes, weak < .65, strong ≥ .8,
trend ±.15); absence of a concept is not failure; no individual uncertainty (population calibration
only); classical ML never serves user predictions; no learner ids leave the server.

## 9. Phase 7 functionality reusable as is

`skill_states`, `catalogue_from_history` + `recommend` (catalogue-bound, abstaining suggestions),
`musical_evidence.evidence`, `musical_forecast` (the only inference path), HMAC `ticket`/`verify`
pattern, `cached_validate` (checksummed model load), `artifacts/phase7/summary.json`, test
calibration bins in `metrics.json`. The prospective ledger is token-gated and abstains: not used.

## 10. API fields the four features need

| Need | Exists? |
|---|---|
| Observations up to an arbitrary cutoff T | **No** – demo returns one fixed prefix of 3 groups. |
| Per-concept evidence and state at T | Partly – `skill_states` exists, not exposed per cutoff. |
| GRU prediction made at T for group T | Engine exists (`musical_forecast`); no per-cutoff endpoint. |
| Past forecasts vs outcomes known at T (trail) | No. |
| Actual encoded input and recorded GRU activations | No (only tensor shape). |
| Server-mediated reveal per cutoff | Pattern exists for one case only. |
| Learner list | No (single case per source). |

Key discovery: the private prepared data already contains every held-out test learner; the demo's
own learner ("Parcours réel de test 01", first test learner in split order) has **28 SingPAD groups**
(cut at 3 by the demo) and 9 Yousician days. A per-cutoff causal replay is feasible: 27 forecasts
take ~0.46 s on CPU. → a **presentation adapter** is strictly necessary and sufficient; no model,
training, preprocessing or evaluation change.

## 11. Files likely to change

New: `axis7/living_learner.py` (read-only adapter router), `web/living.html`, `web/living/*.js`,
`web/living.css`, `tests/test_phase8_living.py`, `tests/frontend/living_check.js`, Phase 8 docs.
Touched minimally: `axis7/server.py` (+2 lines include_router), `web/o08.html` (link),
`.github/workflows/validate.yml` (`node --check` lines), `README.md` (link).

## 12. Risks

Leakage through caching/prefetch or hidden DOM; layouts that encode future concepts; colour
scales implying mastery; over-reading hidden states/edges as explanations; scrubbing latency;
SVG cost with 270 concept slots; Yousician (K=1) making a "constellation" trivially small;
private data absent on fresh clones (must degrade honestly, like the existing demo).

## 13. Contradictions and clarifications

1. The brief lists DKT-GRU and causal attention as active; only EnhancedGRU is served.
2. `o08_demo` reports `tensor_shape [1, T, 4K]`: that is the `x` block only; the GRU input is
   4K+13 wide (item embedding + difficulty), the head adds another item embedding. Not wrong, incomplete.
3. `docs/DESIGN.md` bans dark/glow surfaces – it governs the twin page (round 4). The brief asks
   for a dark observatory. Resolved by scoping: the new page has its own documented identity
   reusing O08 serif type and gold/green tokens; the twin page is unchanged.
4. Phase 7 report says AI_TEAM templates were absent; they now exist in `~/.claude/templates`
   and are adopted on the Phase 8 branch.
5. "Session" in the brief ≠ source unit: SingPAD steps are timestamp groups, Yousician steps are
   active days. The UI says "groupe"/"jour actif", never "séance" as an equivalent.
