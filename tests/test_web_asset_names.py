"""Ad and tracker blockers (uBlock Origin, AdBlock…) refuse scripts whose names look like tracking.

In Edge with uBlock, web/living/fingerprint.js was blocked and the Rejeu O08 never started. Every
script the pages load must keep a neutral name, and every page must list scripts that exist."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKED_WORDS = ('fingerprint', 'analytics', 'tracking', 'tracker', 'beacon', 'pixel', 'advert', 'adserver', 'banner', 'telemetry')


def test_no_web_script_name_looks_like_tracking():
    names = [p.relative_to(ROOT).as_posix() for p in (ROOT / 'web').rglob('*.js')]
    flagged = [n for n in names if any(w in n.lower() for w in BLOCKED_WORDS)]
    assert not flagged, flagged


def test_every_script_a_page_loads_exists():
    for page in (ROOT / 'web').glob('*.html'):
        for src in re.findall(r'<script[^>]+src="([^"?]+)', page.read_text(encoding='utf-8')):
            assert (ROOT / src.lstrip('/')).is_file(), (page.name, src)
