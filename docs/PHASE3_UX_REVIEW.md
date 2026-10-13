# Musician experience: browser verification and heuristic review

Target: an ordinary beginning piano learner. This is an engineering heuristic review with actual browser interaction, not participant usability research. No tester satisfaction, learning benefit or WCAG certification is claimed.

The old default asked the learner to interpret a skill constellation, forecast percentages, model choice and replay state. It now lives intact in Research & integration. The default has four plain navigation choices: Accueil, Pratiquer, Ma progression, Mon carnet. A visible primary action starts short guided piano exercises. Technical architecture, JSON, thresholds and comparison metrics are absent from the default home. No simulated attempt is presented as AI assessment.

| Finding | Priority | Resolution and actual check |
|---|---|---|
| Main action competed with technical exploration | Release blocking | Home now emphasizes Commencer à jouer; the browser reached exercise selection from that action. |
| Forecast percentage resembled demonstrated mastery | Release blocking | Notebook uses explicitly user/teacher-entered ordinal ratings; one assessment remains insufficient evidence. Synthetic-trained forecasts stay in research mode. |
| Practice needed developer JSON | Release blocking | Guided choose/play/assess/save flow; native radio controls and clear acknowledgments. |
| Score-reading exercise lacked a supplied reference | High | An original four-quarter-note treble-clef motif is rendered locally; no copyrighted score or fake audio analysis. |
| Repeated difficulty explanation lacked exact evidence | High | After three demo attempts, browser showed two difficulties out of three and dated assessments in Why this exercise. |
| Changing rater category could imitate improvement | High | Comparison follows the latest exercise and self/teacher source cohort, with three recent and three earlier ratings. This still does not prove causal improvement or identify a specific teacher. |
| Retry could duplicate or lose an assessment | High | Stable payload retained only for uncertain network/server failures; explicit 422/409 rejection releases the draft for correction. Missing saved profiles offer a new-notebook action while preserving the unavailable reference. Server enforces idempotency. |
| Coverage strategy had no evidence for an unpracticed skill | Moderate | Explanation explicitly shows zero observations rather than inventing a weakness. |
| Layout or font might hide actions on phone | High | Measured desktop 1706x960, tablet 768x1024 and phone 375x812 CSS pixels; all had document widths below viewport width. Radio choices stack; actions remain readable. |

Actual browser journey: initial home -> demonstration profile -> five-note exercise -> entered needs-work assessment -> saved feedback -> progress -> repeat twice -> recommendation explanation -> alternative coverage policy -> notebook. Three fictional demo attempts were stored locally and remain labeled demo. They are not real participant observations. Existing profiles were not deleted or reset.

Native buttons, inputs, labels, fieldsets, legends, visible focus and a skip link support keyboard use. Reduced-motion settings disable the entrance animation. Automated UI harnesses check original research-mode behavior and collection-mode consent, busy guards, retries, progress wording, coverage wording and escaping. Screen-reader testing and real first-time-user studies remain to be performed.

The local-notebook option has a plain-language storage notice and explicit consent for one's own practice. It does not enroll children or institutional classes into research. Scores, taxonomy, catalogue and thresholds remain provisional; teacher attribution is not rubric approval. Export is an unvalidated pseudonymous collection, not training-ready data.
