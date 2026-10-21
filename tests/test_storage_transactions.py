import copy
import pytest
from axis7.storage import append_event, EventConflict, connect

def record(identifier='one', order=1, payload=1):
    return {'id':identifier,'student':'learner','order':order,'request':{'value':payload}}

def test_retry_is_idempotent_and_conflicting_payload_does_not_overwrite(tmp_path):
    path=tmp_path/'events.db'
    saved,repeated=append_event(path,record(),[],set())
    assert not repeated
    again,repeated=append_event(path,record(),[],set())
    assert repeated and again==saved
    with pytest.raises(EventConflict):append_event(path,record(payload=2),[],set())
    with connect(path) as conn:assert conn.execute('SELECT count(*) FROM events').fetchone()[0]==1

def test_rejected_chronology_rolls_back_and_next_valid_append_succeeds(tmp_path):
    path=tmp_path/'events.db'
    append_event(path,record(),[],set())
    with pytest.raises(ValueError,match='strictly later'):append_event(path,record('two',1),[],set())
    _,repeated=append_event(path,record('two',2),[],set())
    assert not repeated

def test_fixture_ids_cannot_be_replaced(tmp_path):
    with pytest.raises(EventConflict,match='immutable fixture'):
        append_event(tmp_path/'events.db',record(),[],{'one'})
