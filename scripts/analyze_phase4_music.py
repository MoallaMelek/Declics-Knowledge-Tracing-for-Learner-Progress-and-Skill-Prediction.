"""Reproduce the Phase 4 descriptive piano study from checked pinned acquisitions."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from axis7.music_case_study import analyze
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,default=ROOT/'data/music-phase4/raw')
    p.add_argument('--output',type=Path,default=ROOT/'artifacts/phase4/music-case-study.json');args=p.parse_args()
    result=analyze(args.raw);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps(result['summary'],indent=2))
