# DÉCLIC twin · design system ("ebony & felt")

Round 4 replaced the dark "glowing hologram" look with a light working surface. The rules below are what later passes (Claude, Codex or a person) should keep, so the interface does not drift back to generic defaults.

## Method

- Guidance applied: Impeccable (pbakaus/impeccable, Apache-2.0), read as Markdown only (SKILL.md, critique, polish, colorize, typeset, craft-floor, mode-operate). Its launcher binary, hooks and `detect` CLI were **not** run, so there is no deterministic detector score.
- Cross-checked with unslop-ui-skill (MIT, local zip inspected before use: text files only).
- Mode: **Operate**. The visitor completes a task (read a learner's state, replay sessions, add an observation). The music world lends type, palette, density and one signature move, never a costume.

## World

- **Ground**: white page; the constellation sits on a light stage (`--stage #f4f4f2`). No dark mode in this round: the use scenes (practice room, teacher review, jury projector) are lit rooms.
- **Shell**: one ebony bar (`--ebony #18161b`) with the wordmark and the two views as underline tabs.
- **Felt red** (`--felt #b3261e`, piano hammer felt): selection, focus, the current session, "to watch next". Used sparingly.
- **Probability scale** (shared by graph, evidence, picker, legend): green `#1d6a4e` ≥ 65 %, brass `#946000` 45–65 %, felt `#b3261e` < 45 %. Always paired with the number, never colour alone.
- **Type**: Sitka (engraved serif, local) for headings and explanatory prose; Bahnschrift (DIN, local) for controls, labels and every number (`tabular-nums`). Monospace only in the JSON textarea. No external font request (offline demo).
- **Signature move**: the constellation, kept three-dimensional as an *armillary engraving*. Skills ride a tilted orbit (nearer = slightly larger), shaded as porcelain spheres with a probability ring; the selected skill turns ebony. A porcelain bust of the learner (contour hatching, soft plinth shadow) sits at the centre; each orbit's far half is dashed behind it and its near half solid in front. The equator passes through the two side skills. The meridian's slow 24 s turn is the only ambient motion (off under `prefers-reduced-motion`; phase follows the clock so re-renders do not restart it). This replaces the earlier dark hologram bust and glows, not the 3D structure.

## Bans kept

No eyebrow/kicker labels above headings, no uppercase spaced labels, no glows, decorative gradients (the only gradients are the sphere/porcelain shading inside the constellation), dotted-grid backgrounds, or idle animations beyond the single meridian turn, no Unicode glyphs as icons (inline SVG sprite, one stroke weight), no em-dash in UI copy, no soft-shadow cards (1 px hairlines, 6 px radius).

## Verification (round 4)

- `pytest`: 27 passed (includes the Node harness driving the real `app.js`, 9/9).
- Rendered at 1513×725, 1440 wide, 900 wide (headless Edge) and 375×812 (app browser): no horizontal overflow at 375 px; the whole constellation is in the first screen at 1513×725.
- Not done: the study charts are still default matplotlib PNGs (English labels, default colours); `docs/preview.jpg` and `declic-axis7.zip` predate this round.
