"""Runs the real web/app.js in Node with a stubbed DOM, fed by responses from the real API."""
import json, shutil, subprocess
import pytest
from fastapi.testclient import TestClient
from axis7 import server
from axis7.data import ROOT

EVENT = {'schema_version':'1.0','attempt_id':'ui:new:1','student_id':'ui-new-learner','session_id':'ui-session','exercise_id':'ui-ex',
         'instrument':'piano','timestamp':'2026-03-01T10:00:00+00:00','provenance':'project','rubric_version':'provisional',
         'observations':[{'skill_id':'pitch','outcome':1}],'upstream_versions':{}}

@pytest.mark.skipif(shutil.which('node') is None, reason='Node.js is not installed')
def test_ingest_and_reset_keep_selector_and_state_consistent(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'DB', tmp_path / 'events.sqlite')
    client = TestClient(server.app)
    fixtures = {'learners0': client.get('/api/learners?domain=music-mock').json()}
    first = fixtures['learners0']['learners'][0]['id']
    fixtures['twin0'] = client.get(f'/api/twin/{first}?domain=music-mock').json()
    fixtures['ingest'] = client.post('/api/attempts', json=EVENT).json()
    fixtures['learners1'] = client.get('/api/learners?domain=music-mock').json()
    fixtures['reset'] = client.post('/api/reset/ui-new-learner').json()
    fixtures['learners2'] = client.get('/api/learners?domain=music-mock').json()
    fixture_path = tmp_path / 'fixtures.json'
    fixture_path.write_text(json.dumps(fixtures, ensure_ascii=False), encoding='utf-8')
    run = subprocess.run(['node', str(ROOT / 'tests/frontend/ui_check.js'), str(ROOT / 'web/app.js'), str(fixture_path),str(ROOT / 'web/index.html')],
                         capture_output=True, text=True, encoding='utf-8', timeout=120)
    print(run.stdout)
    assert run.returncode == 0, run.stdout + run.stderr
    assert '16/16 checks passed' in run.stdout
