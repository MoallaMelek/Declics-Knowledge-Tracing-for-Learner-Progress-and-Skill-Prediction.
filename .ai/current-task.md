# Phase 9 · Refonte UX de DÉCLIC (frontend)

Writer: Claude (claude.ai session, cloud clone of the GitHub repository). No other agent consulted for this task so far.
Branch `phase9/declic-ux-rebirth` from `main` @ 831ca85, which already contains the Phase 8 stabilization (PR #4) and the 17/10 hardening (PR #5). The previous task (Phase 8 stabilization, writer Codex desktop) is closed and merged.

Scope: frontend only (web/, frontend test harnesses, docs). No change to models, targets, evaluation protocol, datasets or API contracts.
Baseline before changes: 425 pytest passed / 3 skipped; Playwright e2e 13/13 (synthetic fixture + real copied weights).

Environment notes: download.pytorch.org and cdn.playwright.dev are refused by this session's egress policy; torch installed from PyPI, Chromium from the preinstalled /opt/pw-browsers via DECLIC_BROWSER_EXECUTABLE. Real held-out data is private and not available in the cloud: real-data browser validation must run on the delivery machine.

Plan and audit: docs/PHASE9_UX_REBIRTH.md.
