# Phase 8 · Visual architecture: "Le parcours vivant" (The Living Learner)

Scope: frontend experience for O08 plus one read-only presentation adapter. No change to models,
training, preprocessing, evaluation, checkpoints, the registry or existing endpoints.

## 1. Backend presentation adapter: `axis7/living_learner.py`

Router `/api/v7/o08/living`, included in `server.py`. Its only inference path is the existing
`musical_api.musical_forecast` (served EnhancedGRU). It never trains, never imports classical models.

| Endpoint | Returns | Leakage rule |
|---|---|---|
| `GET /learners?source=` | Up to 8 anonymous tokens `01..08`: the first held-out **test** learners in split order with ≥ 6 steps (01 is the Phase 7 demo learner). Model provenance. | No learner id, no outcome. Selection never looks at errors. |
| `GET /state?source&learner&cutoff=c` | Steps `0..c-1` (relative day offsets, exercise, per-concept successes/notes), `skill_states` at `query_time = time(step c)`, co-evaluation edges from past steps, GRU forecast for step `c`, trail of forecasts made at every earlier cutoff `j<c` with step `j`'s outcome, catalogue-bound recommendation, `reveal_receipt`. | Step `c` contributes only its *query definition* (exercise id, concepts evaluated, as in the training protocol); its outcomes are absent. The total number of steps is disclosed (timeline extent), never later outcomes or dates. |
| `POST /reveal {receipt}` | Observed outcome of step `c`, per-concept errors, log-loss (SingPAD), reference errors (train-mean constant, learner's own past mean). | HMAC ticket bound to source, learner, cutoff, data digest, model digest and the predictions; 409 otherwise. |
| `GET /inspect?source&learner&cutoff` | The actual encoded window (`x` restricted to target concepts + counts of other non-zero features, item ids), **recorded** GRU hidden states via a forward hook, head logits, and `matches_served_forecast`. | Same strictly-past rows as `/state`. |

Integrity at load: the prepared archive digest must equal the model's `sha256`, and the public split
provenance recomputed from the archive must equal the model's `splits` (same checks as
`scripts/build_musical_demo.py`). Missing private data → 503, the UI shows an honest unavailable state.

## 2. Frontend: `web/living.html` + `web/living/*.js` (vanilla, no dependency)

Rationale: the repository is deliberately dependency-free and offline (no npm, no CDN, CI runs
`node --check`). SVG is enough: at most 270 concept slots, ~1 000 edges, ~600 fingerprint arcs.
D3/Three.js/WebGL would add a build step and weight without a visual need.

```
living.html
 ├─ store.js        shared state + subscribe (single source of truth)
 ├─ adapters.js     pure, Node-testable: constellation, fingerprint, timeline, errors, labels
 ├─ api.js          fetch, AbortController, stale-response guard, visited-only cache
 ├─ timeline.js     Feature 2 · Machine à remonter le parcours (controls every view)
 ├─ constellation.js Feature 1 · Constellation vivante
 ├─ fingerprint.js  Feature 3 · Empreinte musicale
 ├─ observatory.js  Feature 4 · Observatoire de la décision
 └─ main.js         wiring, keyboard shortcuts, reduced motion
```

**Shared state** `{source, learner, cutoff, stepsTotal, selectedConcept, compareCutoff, playing,
speed, research, stage, reveals{cutoff→payload}, status}`. Only `/state` payloads for cutoffs the
user has visited are cached; **no prefetch ahead** (a prefetched later cutoff would put outcomes
in client memory before the user reaches them). Every response is checked against the current
`(source, learner, cutoff)` before it touches the store.

## 3. Encodings

**Fixed concept sky.** Concept `k` of K sits at angle `2πk/K` and a radius from a deterministic
hash of `k`. The layout depends on the vocabulary only, never on the learner, so it cannot encode
the future and is identical at every cutoff. Angle is shared with the fingerprint (synchronised).
Consecutive SingPAD ids tend to belong to the same exercise; position carries no musical meaning.

| Channel | Meaning |
|---|---|
| Dim dust point | vocabulary slot not yet observed for this learner |
| Node radius | 6 + 2.2·√(notes observed so far) (days for Yousician) |
| Fill colour | descriptive state from `source-skill-state-v1` (legend + text, never colour alone) |
| Translucent dashed node | insufficient evidence (visible but faint); empty dashed node: target concept never observed |
| Fresh halo | concept observed in the most recent step (the one that just entered the past) |
| Gold orbit | concept evaluated in the next step; arc length = GRU probability; ivory arc after reveal |
| Edge | co-evaluated in the same past step (observed structure, not a skill relation). Pairs seen in ≥ 2 steps by default; every pair of the selected concept; opacity ∝ count |

**Camera.** Until the user pans or zooms, the camera eases to the bounding box of the current (past-only)
nodes, so the sky "contracts" when the timeline moves back. Selecting a star centres it; Échap or the
target button returns to evidence framing.

**Empreinte musicale ("sillons").** Polar record: one ring per observed step (centre = oldest),
an arc per concept at the shared angle, colour = success fraction of that concept in that step,
gaps = not evaluated (never coloured as failure). Beside it, seven indicators each on its own
scale with definition, formula, support count and sufficiency: coverage, historical success,
recent success, recent change, variability, recurring weaknesses, evidence sufficiency. Compare
mode overlays two visited cutoffs and only diffs same-unit indicators.

**Timeline.** Past steps as bars (aggregate success), trail markers for forecasts made at earlier
cutoffs vs their outcomes, future slots as empty ticks. Native `<input type=range>` for keyboard
and screen readers; play/pause, speed ×0.5/×1/×2, previous/next.

**Observatory.** Pipeline Historique → Encodage → GRU → Tête → Prévision → Évaluation. Each stage
opens real values. The architecture drawing is labelled as an illustration; the hidden-state
heatmap is labelled as recorded activations, not explanations. No attention is shown because the
served model has none. Research mode adds Phase 7 benchmark tables, active-model test calibration
(population level) and stress tests, labelled as research comparisons.

**Number formats.** SingPAD forecasts are note-success probabilities (`81,2 %`). Yousician forecasts are a
continuous score written `80,6 / 100`, as in the Phase 7 UI, so they are not read as probabilities.

**Rendering.** One render per animation frame with a timer fallback (frames pause in background tabs).
Only the dock, header and selection camera animate; no ambient motion. Expensive effects (blend modes,
backdrop blur, fixed-attachment gradients) were removed after QA showed slow paints.

**Demo links.** `?source&learner&cutoff&concept&stage&research=1#section` opens a prepared view; the reveal
can only be triggered by the user.

## 4. Motion and accessibility

Motion explains change only: nodes fade/grow when evidence arrives, new rings draw in, the camera
eases to a selected concept, the pipeline highlights the active stage. `prefers-reduced-motion`
disables transitions and playback becomes step-by-step. Every graphic has a text/table
alternative; keyboard: ←/→ cutoff, Space play, arrows inside the constellation move between
nodes, Enter selects, Esc clears. Learner-facing copy is French.

## 5. Tests

Python: causality of `/state` (no step ≥ c in payload; result identical when later steps are
mutated), reveal ticket binding, forecast equals `musical_forecast`, inspect equals served
forecast, abstention at c=1, learner id never returned, no classical model on the path, 503 without
data. Node: adapters (layout determinism, no future in fingerprint, gaps ≠ failure, error maths,
stale-response guard). Browser QA at 1440, 1024, 768 and 375 px.
