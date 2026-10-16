"""Regression of practice UI retries/consent against actual backend responses."""
import json,shutil,subprocess
import pytest
from fastapi.testclient import TestClient
from axis7 import server
from axis7.data import ROOT

@pytest.mark.skipif(shutil.which('node') is None,reason='Node.js is not installed')
def test_actual_practice_ui_consent_retry_and_feedback(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB',tmp_path/'practice.sqlite')
    c=TestClient(server.app);catalog=c.get('/api/practice/catalog').json()
    profile=c.post('/api/practice/profiles',json={'mode':'demo','local_storage_consent':False}).json()
    student=profile['student_id'];summary=c.get(f'/api/practice/summary/{student}').json()
    selected=catalog['exercises'][0]
    payload={'attempt_id':'ui-attempt-1','student_id':student,'exercise_id':selected['id'],
        'timestamp':'2026-10-13T12:00:00Z','source':'self','rubric_version':catalog['rubric_version'],
        'ratings':[{'skill_id':selected['skill_ids'][0],'rating':'comfortable'}],'confidence':None}
    saved=c.post('/api/practice/sessions',json=payload);assert saved.status_code==200
    wrong={**payload,'rubric_version':'unsupported-rubric'}
    conflict={**payload,'ratings':[{'skill_id':selected['skill_ids'][0],'rating':'needs_work'}]}
    bad=c.post('/api/practice/sessions',json=wrong);duplicate=c.post('/api/practice/sessions',json=conflict)
    missing=c.get('/api/practice/summary/missing-profile')
    assert (bad.status_code,duplicate.status_code,missing.status_code)==(422,409,404)
    fx=tmp_path/'practice.json';fx.write_text(json.dumps({'catalog':catalog,'profile':profile,
        'summary':summary,'saved':saved.json(),'export':c.get(f'/api/practice/export/{student}').json(),
        'rejections':{'422':bad.json(),'409':duplicate.json(),'404':missing.json()}}),encoding='utf8')
    run=subprocess.run(['node',str(ROOT/'tests/frontend/practice_check.js'),str(ROOT/'web/musician.js'),str(fx)],capture_output=True,text=True,encoding='utf8',timeout=60)
    assert run.returncode==0,run.stdout+run.stderr
    assert '20/20 practice checks passed' in run.stdout
