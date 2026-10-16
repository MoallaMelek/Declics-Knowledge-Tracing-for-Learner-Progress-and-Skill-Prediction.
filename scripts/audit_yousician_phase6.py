"""Selection-bias diagnostics for excluded tied counter groups; no guessed attempts."""
from collections import Counter, defaultdict
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from axis7.cloud_training import stream_array,atomic_json


def audit(archive):
    seen=set();groups={};conflicts=set();categories=defaultdict(set)
    with zipfile.ZipFile(archive) as z:
        member=next(n for n in z.namelist() if n.endswith('.json'))
        with io.TextIOWrapper(z.open(member),encoding='utf-8-sig') as f:
            for row in stream_array(f):
                fingerprint=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).digest()
                if fingerprint in seen:continue
                seen.add(fingerprint)
                if row['play_mode']!='play':continue
                key=(str(row['user_id']),int(row['session_index']),float(row['days_since_signup']),
                     str(row['exercise_id']),str(row['song_id']))
                counts=tuple(int(row[k]) for k in ('notes_evaluated','notes_successful','chords_evaluated','chords_successful'))
                if key in groups and groups[key]!=counts:conflicts.add(key)
                groups[key]=counts
                categories[key].add(str(row['difficulty_level']))
    summaries=defaultdict(Counter)
    for key,counts in groups.items():
        difficulty='|'.join(sorted(categories[key]))
        day_bucket='days_0_6' if key[2]<7 else 'days_7_29' if key[2]<30 else 'days_30_plus'
        outcome='contradictory_excluded' if key in conflicts else 'zero_evaluation' if counts[0]+counts[2]==0 else 'retained'
        summaries['all'][outcome]+=1
        summaries['difficulty:'+difficulty][outcome]+=1
        summaries[day_bucket][outcome]+=1
    result={'unit':'unique tied user/session/relative-time/exercise/song group after exact dedup and practice exclusion',
            'groups':{k:dict(v) for k,v in summaries.items()},
            'unique_attempt_id_reconstructed':False,
            'interpretation':'Different exclusion rates are a selection-bias diagnostic, not proof that missing outcomes are recoverable.',
            'future_covariates':'Historical difficulty/day gaps could be studied separately; neither future difficulty nor future day gap is available to current forecast.'}
    atomic_json(ROOT/'artifacts/phase6/yousician-selection-audit.json',result)
    print(json.dumps(result['groups']['all']))


if __name__=='__main__':audit(sys.argv[1])
