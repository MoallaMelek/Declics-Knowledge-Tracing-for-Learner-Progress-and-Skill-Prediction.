"""Transactional chronological append and idempotency for the existing SQLite store."""
import hashlib,json,sqlite3
from pathlib import Path
from contextlib import contextmanager

class EventConflict(ValueError):pass

@contextmanager
def connect(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path,timeout=10)
    try:
        conn.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, student TEXT, data TEXT)')
        conn.execute('CREATE INDEX IF NOT EXISTS events_student ON events(student)')
        yield conn
    finally:conn.close()

def fingerprint(request):
    return hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def append_event(path,record,base_rows,fixture_ids):
    digest=fingerprint(record['request']);record['request_fingerprint']=digest
    with connect(path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        try:
            existing=conn.execute('SELECT data FROM events WHERE id=?',(record['id'],)).fetchone()
            if existing:
                old=json.loads(existing[0])
                if old.get('request_fingerprint')!=digest:
                    raise EventConflict('attempt_id already exists with a different payload')
                conn.rollback();return old,True
            if record['id'] in fixture_ids:raise EventConflict('attempt_id belongs to an immutable fixture')
            extras=[json.loads(x[0]) for x in conn.execute('SELECT data FROM events WHERE student=?',(record['student'],))]
            previous=base_rows+extras
            if previous and record['order']<=max(r['order'] for r in previous):
                raise ValueError('Timestamp must be strictly later; merge simultaneous observations into one event')
            conn.execute('INSERT INTO events(id,student,data) VALUES(?,?,?)',
                (record['id'],record['student'],json.dumps(record,ensure_ascii=False,allow_nan=False)))
            conn.commit();return record,False
        except Exception:
            conn.rollback();raise
