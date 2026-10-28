import json
from pathlib import Path
import pytest
from axis7.music_case_study import rach_identity,load_pianovam,descriptive_split,analyze

def test_rach_source_chronology_preserves_full_piece_suffix():
    row=rach_identity('rehearsals/p3/p3240606001hanoncexercsmi.mid')
    assert row['calendar_date']=='2024-06-06'
    assert row['daily_session']==0 and row['piece_order']==1
    assert row['exercise_id']=='hanoncexercsmi'
    assert row['time_precision']=='calendar_day_and_source_order'
    with pytest.raises(ValueError):rach_identity('p3999999001anything.mid')

def test_future_day_partition_never_splits_simultaneous_day():
    rows=[{'learner_id':'a','exercise_id':'x','calendar_date':d,'attempt_id':str(i)}
          for i,d in enumerate(['2024-01-01','2024-01-02','2024-01-02'])]
    split=descriptive_split(rows)
    assert split['earlier']==['0'] and split['future']==['1','2']
    assert split['usable_for_knowledge_tracing'] is False
    assert split['target_available'] is False

def test_single_day_not_misrepresented_as_future_progression():
    row={'learner_id':'a','exercise_id':'x','calendar_date':'2024-01-01','attempt_id':'a'}
    assert descriptive_split([row])['single_day_excluded']==['a']

def test_metadata_drops_demographics_and_does_not_use_static_skill_as_label():
    metadata={'1':{'performance_method':'Solo','P1_name':'Public Name','P1_skill':'Advanced',
        'record_time':'2024-02-14_19-10-09','duration':'0 days 00:12:25.493.000000',
        'composer':'Composer','piece':'Piece'}}
    rows=load_pianovam(metadata)
    assert rows[0]['outcome'] is None and rows[0]['duration_seconds']==745.493
    assert 'Public Name' not in json.dumps(rows) and 'Advanced' not in json.dumps(rows)
    assert 'timezone_unspecified' in rows[0]['time_precision']

def test_acquisition_checksum_fails_closed(tmp_path):
    (tmp_path/'file').write_bytes(b'changed')
    (tmp_path/'acquisition.json').write_text(json.dumps({'files':[{'path':'file','sha256':'bad'}]}))
    with pytest.raises(ValueError,match='checksum'):analyze(tmp_path)

def test_actual_case_study_has_no_fabricated_outcomes():
    root=Path(__file__).resolve().parents[1]
    study=json.loads((root/'artifacts/phase4/music-case-study.json').read_text(encoding='utf8'))
    assert study['summary']['rach3_recordings']==12
    assert study['summary']['pianovam_solo_recordings']==106
    assert study['summary']['usable_assessment_targets']==0
    assert study['summary']['models_trained']==0
    assert all(row['outcome'] is None and row['assessment_available'] is False for row in study['records'])
    earlier=set(study['partitions']['earlier']);future=set(study['partitions']['future'])
    assert earlier and future and not earlier&future
    byid={row['attempt_id']:row for row in study['records']}
    for id in future:
        row=byid[id];prior=[byid[k] for k in earlier if byid[k]['learner_id']==row['learner_id'] and byid[k]['exercise_id']==row['exercise_id']]
        assert prior and max(r['calendar_date'] for r in prior)<row['calendar_date']
