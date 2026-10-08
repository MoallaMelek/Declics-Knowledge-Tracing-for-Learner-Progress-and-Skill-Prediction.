import json
import pytest
from axis7.data import ROOT
from axis7.schema import Attempt, write_schema

SCHEMA = ROOT / 'schemas/attempt-v1.schema.json'
EXAMPLE = ROOT / 'examples/project-attempt.json'

def test_published_schema_is_generated_from_the_validation_model(tmp_path):
    generated = json.loads(write_schema(tmp_path / 'attempt-v1.schema.json').read_text(encoding='utf-8'))
    assert json.loads(SCHEMA.read_text(encoding='utf-8')) == generated

def test_example_is_a_valid_attempt():
    Attempt.model_validate(json.loads(EXAMPLE.read_text(encoding='utf-8')))

def test_example_validates_against_the_published_json_schema():
    jsonschema = pytest.importorskip('jsonschema')
    schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
    example = json.loads(EXAMPLE.read_text(encoding='utf-8'))
    jsonschema.validate(example, schema, cls=jsonschema.Draft202012Validator)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**example, 'timing_ms': 5}, schema, cls=jsonschema.Draft202012Validator)
