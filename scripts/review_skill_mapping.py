"""Validate a teacher's review file; never invent mappings or mutate serving models."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from axis7.taxonomy import MappingReview

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file',help='JSON review record prepared by reviewer')
    parser.add_argument('--output',required=True,help='Versioned review archive file')
    args=parser.parse_args()
    review=MappingReview(**json.loads(Path(args.file).read_text(encoding='utf-8')))
    target=Path(args.output)
    if target.exists(): raise FileExistsError('Preserve existing review versions; choose a new output path')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(review.model_dump(mode='json'),ensure_ascii=False,indent=2),encoding='utf-8')
    print('Review structurally validated. No model or production mapping activated.')
