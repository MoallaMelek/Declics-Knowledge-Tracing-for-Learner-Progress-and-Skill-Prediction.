# Codex final review · Phase 8 (fresh read-only session)

Command: `codex exec review -c 'sandbox_mode="read-only"' --base phase7/personalized-musical-learning`
(custom instructions cannot be combined with `--base` in this CLI version). Reviewed commits 8f85973 and 3b2592f.

Codex ran its own backend checks: state/reveal/inspection consistency passed for both sources (32 checks each),
and confirmed a reveal receipt older than 30 minutes returns 409.

| Finding | Severity | Disposition |
|---|---|---|
| `pointerdown` captures the pointer, so `pointerup` targets the SVG and clicking a star never selects it | P2 | Fixed: the star under the press is stored at `pointerdown`. Verified with a real mouse click in the browser. |
| A visited cutoff stays cached with its reveal receipt; after 30 minutes the reveal fails without recovery | P2 | Fixed: on 409 the client refetches that cutoff (`state(..., {fresh: true})`), checks the predictions are unchanged and retries once. Verified in the browser; Node check added. |

Writer: Claude Code. Reviewer: Codex (fresh session, no prior context). Verification of fixes: Claude Code.
