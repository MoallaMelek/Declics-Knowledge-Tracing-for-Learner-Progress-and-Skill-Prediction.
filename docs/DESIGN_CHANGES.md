# Design changes · round 3

Scope: the local twin interface in `web/`. The earlier critiques (`CLAUDE_DESIGN_REVIEW.md`, based on a narrow mobile capture, and the desktop capture `preview.jpg`) were answered item by item below. No account, payment, external service or design tool was needed. Figma was not used for this work.

## What changed

| Area | Change | Where |
|---|---|---|
| Keyboard focus | Graph nodes show a bright ring on `:focus-visible`. Focus is kept on the same node when the graph re-renders after a selection or a simulation. | `web/style.css` (end block), `web/app.js` (`renderGraph`), `node-body` class |
| Answer to "what is fragile next" | A sentence under the headline explains the rule: lowest forecast among skills with at least three observations, with the count of eligible skills, marked "Règle explicite, non validée". | `web/index.html` (`#weakness-reason`), `render()` |
| Simulation honesty on the graph | A stamp "Simulation · données fictives · non validée" sits on the constellation itself for the synthetic domain, not only in the header and footer. | `web/index.html` (`#graph-stamp`), `.graph-stamp` |
| Legibility | Eyebrows 9 → 10 px, uncertainty copy 9 → 11 px, graph caption 9 → 10 px, evidence dates 8 → 10 px. Measured against the desktop screenshot's small text, not against a contrast tool. | `web/style.css` (end block) |
| External dependency | Removed the Google Fonts `@import`. The page now uses local font stacks and makes no external request. | `web/style.css` |
| Broken image | Removed the `/web-placeholder` source on the study charts (it produced a broken image before the charts loaded). | `web/index.html` |
| Accessibility label | The skill picker has `role="group"` so its label is announced. | `web/index.html` |
| Honest JSON template | The ingestion example is regenerated only while the user has not edited it; a learner or skill change clears it. | `web/app.js` (`populateExample`) |
| State consistency | After ingesting an event for a new learner, the selector and state show that learner. After reset, a learner created only by ingestion is removed from the list and the message says so. | `web/app.js` (`fillLearners`, `ingest`, reset handler) |

## Answers to the earlier critiques

1. **Graph as hero.** Partly. Labels are already 13 px inside the SVG, and the graph stays where it was in the layout. No full-bleed or re-ordering was attempted in this round.
2. **Truncated controls.** Not verified. The desktop capture shows the full selector labels. Mobile truncation could not be checked without a browser.
3. **Simulation disclaimer as structure.** Done for the graph (stamp), in addition to the existing header badge and footer.
4. **"GRU causal" overclaim.** Already absent: no UI text or badge claims causality (checked by search for "causal" in `web/`).
5. **Art direction.** Not done. The dark, card-based layout is retained; a new visual identity was judged out of scope for a correctness-and-legibility round.
6. **Weakness answer and interaction.** Partly. The reason sentence is added. The caption "Sélectionnez un nœud pour lire ses observations" was already present; the model-detail control is already a `<button>`.
7. **Contrast.** Sizes raised; WCAG contrast not measured.

## Not done, and why

- Full mobile review and the reduced-motion behaviour in a real browser: the media queries exist (`prefers-reduced-motion` disables animation and transitions), but they were not observed rendering.
- `docs/preview.jpg` was captured before these changes and is therefore stale.

## Verification status

- JavaScript syntax: `node --check web/app.js` passes.
- Interaction flows (ingest, reset, learner selection, state consistency): covered by `tests/frontend/ui_check.js`, which runs the real `app.js` in Node with a stubbed DOM and real API responses. **9/9 pass**; the pre-fix file fails 2 of them.
- Visual rendering, focus appearance, mobile layout and contrast: **pending browser verification.** No browser tool was available in this session, and browser automation through shell or CDP is not authorised by the project policy.
- Authentication: none required for this local prototype. A deployment with real learner data would need the separate consent, access and audit measures listed in `INTEGRATION.md`.
