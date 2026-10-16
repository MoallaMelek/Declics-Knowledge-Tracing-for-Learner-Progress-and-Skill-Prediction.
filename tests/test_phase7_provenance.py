import copy
import json
from pathlib import Path
import numpy as np
import torch
import pytest
from axis7 import cloud_training as c
from scripts.run_phase7_research import validate_completed


def test_cached_reports_reject_changed_data_or_split():
    learners={str(i):[] for i in range(10)}
    allowed=json.loads((Path(__file__).resolve().parents[1]/'configs/phase7-compatible-implementations.json').read_text())['allowed_source_sha256']
    prepared={'source':'amme','sha256':'real-archive-fingerprint','learners':learners}
    config={'protocol':'phase7-exploratory-v1','seed':42,'condition':'gru','dataset_sha256':prepared['sha256'],
        'splits':c.public_split_provenance(c.split_learners(learners,42)),'epochs':8,'hidden':48,'context':64,
        'core_sha256':c.SOURCE_HASHES,'torch':torch.__version__,'numpy':np.__version__,'device':'cpu','source_sha256':allowed[0]}
    report={'source':'amme','config':config}
    validate_completed(report,prepared,42,'gru')
    with pytest.raises(ValueError):validate_completed(report,{**prepared,'sha256':'changed'},42,'gru')
    changed=copy.deepcopy(report);changed['config']['splits']['test']['sha256']='changed'
    with pytest.raises(ValueError):validate_completed(changed,prepared,42,'gru')
    changed=copy.deepcopy(report);changed['config']['source_sha256']='unreviewed-code'
    with pytest.raises(ValueError):validate_completed(changed,prepared,42,'gru')
