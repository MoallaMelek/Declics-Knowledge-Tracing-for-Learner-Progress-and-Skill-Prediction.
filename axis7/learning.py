"""DÉCLIC learner loop: profile → initial assessment → sessions → scored items → progress.

Additive module (Phase 10). It does not touch the trained O08 networks, their targets, their
evaluation protocol or any existing API contract. Everything is stored locally in SQLite
(runtime/learning.sqlite, or DECLIC_LEARNING_DB). Answers are scored on the server; the
reference-model prediction for an item is written BEFORE the item is shown and never edited.

Vocabulary (also shown in the interface):
  Compétence  what you learn (9 skills, e.g. intervals);
  Exercice    an activity with ordered levels that trains or measures one skill;
  Évaluation  the scoring of one answer, and the initial placement assessment;
  Séance      a sitting of ~15 items chosen from your results, resumable;
  Parcours    your progression map: every exercise level with its mastery status.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import learning_catalog as cat
from . import learning_model as lm
from .data import ROOT

router = APIRouter(prefix='/api/learn', tags=['learner loop'])
SCHEMA = 'declic-learning-v1'

PREREQUISITES = {
    'intervalles': [('hauteur-comparaison', 2)],
    'accords': [('intervalles', 1)],
    'echo': [('melodies', 1)],
    'rythme-echo': [('rythmes', 1), ('pulsation', 1)],
    'degres': [('intervalles', 2)],
    'cadences': [('accords', 1), ('degres', 1)],
}
ASSESSMENT = [('hauteur-seuil', 1, 12, 'Mesure de votre seuil de hauteur'),
              ('melodies', 1, 4, 'Mémoire mélodique, niveau de départ'),
              ('intervalles', 1, 4, 'Intervalles, niveau de départ'),
              ('rythmes', 1, 4, 'Perception du rythme, niveau de départ'),
              ('pulsation', 1, 1, 'Régularité du tempo'),
              ('lecture', 1, 4, 'Lecture de notes, niveau de départ'),
              ('echo', 1, 1, 'Reproduction au clavier')]
SLOW = {'echo', 'pulsation', 'rythme-echo'}


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    # Fixed-width UTC timestamps so that text order is time order in SQLite.
    return dt.astimezone(timezone.utc).isoformat(timespec='microseconds')


def db_path():
    return Path(os.environ.get('DECLIC_LEARNING_DB', ROOT / 'runtime/learning.sqlite'))


@contextmanager
def connect(write=False):
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript('''
      CREATE TABLE IF NOT EXISTS learners(id TEXT PRIMARY KEY, name TEXT NOT NULL, instrument TEXT NOT NULL,
        created_at TEXT NOT NULL, schema TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, learner TEXT NOT NULL REFERENCES learners(id) ON DELETE CASCADE,
        kind TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, finished_at TEXT, plan TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY, session TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        learner TEXT NOT NULL REFERENCES learners(id) ON DELETE CASCADE, seq INTEGER NOT NULL, block INTEGER NOT NULL,
        exercise TEXT NOT NULL, level INTEGER NOT NULL, skill TEXT NOT NULL, created_at TEXT NOT NULL,
        served TEXT NOT NULL, answer TEXT NOT NULL, prediction TEXT NOT NULL, answered_at TEXT, response TEXT,
        correct INTEGER, score REAL, result TEXT, response_ms INTEGER, replays INTEGER, invalid_attempts INTEGER NOT NULL DEFAULT 0,
        UNIQUE(session, seq));
      CREATE INDEX IF NOT EXISTS items_learner ON items(learner, answered_at);
    ''')
    try:
        if write:
            conn.execute('BEGIN IMMEDIATE')
        yield conn
        if write:
            conn.commit()
    except Exception:
        if write:
            conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------- request bodies
class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class NewLearner(Strict):
    name: str = Field(min_length=1, max_length=40)

    @field_validator('name')
    @classmethod
    def visible(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('Le nom ne peut pas être vide.')
        return v
    instrument: Literal['aucun', 'piano', 'voix', 'guitare', 'autre'] = 'aucun'


class NewSession(Strict):
    kind: Literal['auto', 'evaluation', 'seance', 'ciblee'] = 'auto'
    exercise: str | None = Field(default=None, max_length=60)
    level: int | None = Field(default=None, ge=1, le=9)


class Answer(Strict):
    response: dict
    response_ms: int | None = Field(default=None, ge=0, le=3_600_000)
    replays: int = Field(default=0, ge=0, le=50)


# ---------------------------------------------------------------- helpers
def _learner(conn, learner_id):
    row = conn.execute('SELECT * FROM learners WHERE id=?', (learner_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Profil inconnu sur cet ordinateur.')
    return dict(row)


def _session(conn, session_id):
    row = conn.execute('SELECT * FROM sessions WHERE id=?', (session_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Séance inconnue.')
    s = dict(row)
    s['plan'] = json.loads(s['plan'])
    return s


def _history(conn, learner_id, before=None):
    rows = conn.execute('SELECT * FROM items WHERE learner=? AND answered_at IS NOT NULL ORDER BY answered_at, seq', (learner_id,)).fetchall()
    out = []
    for r in rows:
        if before is not None and r['answered_at'] >= before:
            continue
        served = json.loads(r['served'])
        out.append({'id': r['id'], 'session': r['session'], 'exercise': r['exercise'], 'level': r['level'], 'skill': r['skill'],
                    'correct': bool(r['correct']), 'score': r['score'], 'answered_at': r['answered_at'], 'created_at': r['created_at'],
                    'cents': (served.get('detail') or {}).get('cents'), 'result': json.loads(r['result']) if r['result'] else None,
                    'prediction': json.loads(r['prediction']), 'response_ms': r['response_ms']})
    return out


def _binomial_tail(k, n, p):
    if p <= 0:
        return 0.0 if k > 0 else 1.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def _meets(items, window, chance_level):
    k = sum(h['correct'] for h in items)
    return len(items) == window and k / window >= 0.8 and _binomial_tail(k, window, chance_level) < 0.05


def mastery(history):
    """Per (exercise, level), Bloom-style criterion on the LAST W answers at that level.

    'maitrise'    the last W answers meet the criterion now;
    'a_consolider' the criterion was met once (mastered_at) but the last W answers no longer meet it;
    'en_cours'    started, criterion never met."""
    out = {}
    for ex in cat.EXERCISES:
        window = ex['mastery_window']
        for lv in ex['levels']:
            items = [h for h in history if h['exercise'] == ex['id'] and h['level'] == lv['level']]
            entry = {'exercise': ex['id'], 'level': lv['level'], 'attempts': len(items),
                     'successes': sum(h['correct'] for h in items), 'window': window, 'status': 'non_commence', 'mastered_at': None}
            if window is None:
                entry['status'] = 'mesure'
            elif items:
                c = cat.chance(ex['id'], lv['level'])
                first = next((items[i - 1]['answered_at'] for i in range(window, len(items) + 1) if _meets(items[i - window:i], window, c)), None)
                entry['mastered_at'] = first
                entry['status'] = 'maitrise' if _meets(items[-window:], window, c) else 'a_consolider' if first else 'en_cours'
                recent = items[-window:]
                entry['recent'] = {'count': len(recent), 'successes': sum(h['correct'] for h in recent)}
            out[(ex['id'], lv['level'])] = entry
    return out


def _mastered(m, exercise, level):
    # Prerequisites count a level mastered once (a later slump sends you back to consolidate it,
    # it does not re-lock what was unlocked).
    return any(m[(exercise, l)]['mastered_at'] for l in range(level, 10) if (exercise, l) in m)


def pitch_threshold(history):
    """Threshold of the LATEST measurement session only (a staircase is never pooled across sessions)."""
    sessions = [h['session'] for h in history if h['exercise'] == 'hauteur-seuil' and h['cents']]
    if not sessions:
        return None
    latest = sessions[-1]
    trials = [(h['cents'], h['correct']) for h in history if h['exercise'] == 'hauteur-seuil' and h['cents'] and h['session'] == latest]
    out = cat.staircase_threshold(trials)
    out['session'] = latest
    out['measured_at'] = next(h['answered_at'] for h in reversed(history) if h['session'] == latest and h['exercise'] == 'hauteur-seuil')
    # Placement only from a reliable estimate (>= 4 reversals), or from a run without any error
    # (then the threshold is below the smallest gap tested; the lowest correct gap is a safe bound).
    if out['reversals'] >= 4:
        out['placement_cents'] = out['threshold_cents']
    elif out['trials'] >= 8 and all(ok for _, ok in trials):
        out['placement_cents'] = out['lowest_correct_cents']
    else:
        out['placement_cents'] = None
    return out


def frontier(history, m=None):
    """Lowest level of each exercise not mastered yet (the step the parcours proposes)."""
    m = m or mastery(history)
    out = {}
    threshold = pitch_threshold(history)
    for ex in cat.EXERCISES:
        if ex['mastery_window'] is None:
            continue
        levels = [lv['level'] for lv in ex['levels']]
        level = next((l for l in levels if m[(ex['id'], l)]['status'] != 'maitrise'), None)
        placed = None
        reference = threshold and threshold['placement_cents']
        if ex['id'] == 'hauteur-comparaison' and reference:
            fitting = [lv['level'] for lv in ex['levels'] if lv['params']['cents'] >= 1.5 * reference]
            placed = max(fitting) if fitting else 1
            if level is not None:
                level = max(level, placed)
        out[ex['id']] = {'level': level, 'placed_by_threshold': placed}
    placed = out.get('hauteur-comparaison', {}).get('placed_by_threshold') or 0

    def met(e, l):
        # A level below the one the threshold measurement placed you at counts as validated.
        return _mastered(m, e, l) or (e == 'hauteur-comparaison' and placed > l)
    for ex_id, info in out.items():
        prereq = PREREQUISITES.get(ex_id, [])
        info['available'] = all(met(e, l) for e, l in prereq)
        info['prerequisites'] = [{'exercise': e, 'title': cat.EXERCISE_BY_ID[e]['title'], 'level': l, 'met': met(e, l)} for e, l in prereq]
    return out


def plan_session(history, kind, exercise=None, level=None, now=None):
    now = now or _now()
    if kind == 'evaluation':
        return [{'exercise': e, 'level': l, 'count': n, 'reason': r} for e, l, n, r in ASSESSMENT]
    if kind == 'ciblee':
        try:
            cat.level_spec(exercise, level)
        except KeyError:
            raise HTTPException(422, 'Exercice ou niveau inconnu.')
        if exercise == 'hauteur-seuil':
            return [{'exercise': exercise, 'level': 1, 'count': 12, 'reason': 'Mesure choisie dans la bibliothèque'}]
        return [{'exercise': exercise, 'level': level, 'count': 4 if exercise in SLOW else 8, 'reason': 'Exercice choisi dans la bibliothèque'}]
    m = mastery(history)
    f = frontier(history, m)
    last_seen = {}
    for h in history:
        last_seen[h['skill']] = h['answered_at']
    candidates = []
    for ex in cat.EXERCISES:
        info = f.get(ex['id'])
        if not info or info['level'] is None or not info['available']:
            continue
        lvl = info['level']
        at = [h for h in history if h['exercise'] == ex['id'] and h['level'] == lvl][-10:]
        rate = (sum(h['correct'] for h in at) + 1) / (len(at) + 2)
        reason = f"Niveau {lvl} en cours : {sum(h['correct'] for h in at)}/{len(at)} réussis récemment." if at else f'Prochaine étape du parcours : niveau {lvl}.'
        use_level = lvl
        if len(at) >= 6 and sum(h['correct'] for h in at[-6:]) / 6 < 0.5 and lvl > 1:
            use_level = lvl - 1
            reason = f"Consolidation : moins de 50 % de réussite au niveau {lvl} sur les 6 derniers essais, retour au niveau {lvl - 1}."
        seen = last_seen.get(ex['skill'])
        days = (now - datetime.fromisoformat(seen)).total_seconds() / 86400 if seen else None
        started = any(h['exercise'] == ex['id'] for h in history)
        # In-progress steps first (the weaker, the sooner), then discovery of a new exercise;
        # a skill left aside for days gains priority (spaced practice).
        priority = ((1 - rate) + 0.2 if started else 0.6) + (min(days, 7) / 7 * 0.3 if days is not None else 0.15)
        candidates.append({'exercise': ex['id'], 'level': use_level, 'skill': ex['skill'], 'priority': priority, 'reason': reason, 'started': started})
    candidates.sort(key=lambda c: -c['priority'])
    blocks, skills = [], set()
    for c in candidates:
        if c['skill'] in skills:
            continue
        skills.add(c['skill'])
        blocks.append({'exercise': c['exercise'], 'level': c['level'], 'count': 2 if c['exercise'] in SLOW else 4,
                       'reason': c['reason'] + ('' if c['started'] else ' Nouvel exercice débloqué.')})
        if len(blocks) == 3:
            break
    review = []
    for (e, l), entry in m.items():
        if entry['status'] == 'maitrise':
            done = [h for h in history if h['exercise'] == e and h['level'] == l]
            age = (now - datetime.fromisoformat(done[-1]['answered_at'])).total_seconds() / 86400
            if age >= 1 and e not in [b['exercise'] for b in blocks]:
                review.append((age, e, l))
    if review:
        age, e, l = max(review)
        blocks.append({'exercise': e, 'level': l, 'count': 2 if e in SLOW else 3,
                       'reason': f'Révision espacée : niveau maîtrisé, pas retravaillé depuis {int(age)} jour(s).'})
    if not blocks:
        blocks = [{'exercise': 'melodies', 'level': 1, 'count': 4, 'reason': 'Point de départ.'}]
    return blocks


ASSESSMENT_MIN_ANSWERS = sum(n for _, _, n, _ in ASSESSMENT) // 2


def _assessment_done(conn, learner_id):
    # An initial assessment stopped before half of its questions does not count as done.
    return conn.execute("""SELECT COUNT(*) FROM sessions s WHERE s.learner=? AND s.kind='evaluation' AND
        (SELECT COUNT(*) FROM items i WHERE i.session=s.id AND i.answered_at IS NOT NULL) >= ?""", (learner_id, ASSESSMENT_MIN_ANSWERS)).fetchone()[0] > 0


def _block_of(plan, seq):
    total = 0
    for i, b in enumerate(plan):
        if seq < total + b['count']:
            return i, b, seq - total
        total += b['count']
    return None, None, None


def _item_public(row, include_result=False):
    served = json.loads(row['served'])
    pred = json.loads(row['prediction'])
    out = {'id': row['id'], 'seq': row['seq'], 'exercise': row['exercise'], 'level': row['level'], 'skill': row['skill'],
           'title': cat.EXERCISE_BY_ID[row['exercise']]['title'], 'response_type': cat.EXERCISE_BY_ID[row['exercise']]['response'],
           'served': served, 'prediction': pred, 'answered': row['answered_at'] is not None}
    if include_result and row['answered_at']:
        out['result'] = json.loads(row['result'])
    return out


def _progress_of(conn, session):
    total = sum(b['count'] for b in session['plan'])
    answered = conn.execute('SELECT COUNT(*) FROM items WHERE session=? AND answered_at IS NOT NULL', (session['id'],)).fetchone()[0]
    correct = conn.execute('SELECT COUNT(*) FROM items WHERE session=? AND correct=1', (session['id'],)).fetchone()[0]
    return {'total': total, 'answered': answered, 'correct': correct}


def _session_public(conn, s):
    current = conn.execute('SELECT * FROM items WHERE session=? AND answered_at IS NULL ORDER BY seq LIMIT 1', (s['id'],)).fetchone()
    blocks = [dict(b, title=cat.EXERCISE_BY_ID[b['exercise']]['title'], skill=cat.EXERCISE_BY_ID[b['exercise']]['skill']) for b in s['plan']]
    return {'id': s['id'], 'learner': s['learner'], 'kind': s['kind'], 'status': s['status'], 'created_at': s['created_at'],
            'finished_at': s['finished_at'], 'plan': blocks, 'progress': _progress_of(conn, s),
            'current_item': _item_public(current) if current else None}


# ---------------------------------------------------------------- endpoints
@router.get('/catalog')
def catalog():
    return {'schema': SCHEMA, 'skills': cat.SKILLS, 'exercises': [cat.card(e) for e in cat.EXERCISES],
            'references': cat.REFERENCES, 'prerequisites': {k: [{'exercise': e, 'level': l} for e, l in v] for k, v in PREREQUISITES.items()},
            'mastery_rule': "Un niveau est maîtrisé quand, sur les W dernières réponses à ce niveau, au moins 80 % sont justes ET ce score est très improbable au hasard (test binomial, p < 0,05). W = 10 pour les exercices à choix, 6 pour clavier et tapotement.",
            'teacher_approved': False}


@router.post('/learners')
def create_learner(body: NewLearner):
    learner_id = 'apprenant-' + uuid.uuid4().hex[:16]
    with connect(write=True) as conn:
        conn.execute('INSERT INTO learners VALUES(?,?,?,?,?)', (learner_id, body.name.strip(), body.instrument, _iso(_now()), SCHEMA))
    return {'id': learner_id, 'name': body.name.strip(), 'instrument': body.instrument}


@router.get('/learners')
def list_learners():
    with connect() as conn:
        rows = conn.execute('SELECT * FROM learners ORDER BY created_at').fetchall()
        out = []
        for r in rows:
            last = conn.execute('SELECT MAX(answered_at) FROM items WHERE learner=?', (r['id'],)).fetchone()[0]
            n = conn.execute('SELECT COUNT(*) FROM items WHERE learner=? AND answered_at IS NOT NULL', (r['id'],)).fetchone()[0]
            out.append({'id': r['id'], 'name': r['name'], 'created_at': r['created_at'], 'last_activity': last, 'answers': n})
    return {'learners': out}


@router.get('/learners/{learner_id}')
def get_learner(learner_id: str):
    with connect() as conn:
        learner = _learner(conn, learner_id)
        active = conn.execute("SELECT * FROM sessions WHERE learner=? AND status='active' ORDER BY created_at DESC LIMIT 1", (learner_id,)).fetchone()
        evaluated = _assessment_done(conn, learner_id)
        last = conn.execute('SELECT MAX(answered_at) FROM items WHERE learner=?', (learner_id,)).fetchone()[0]
        active_public = None
        if active:
            s = dict(active); s['plan'] = json.loads(s['plan'])
            active_public = {'id': s['id'], 'kind': s['kind'], 'created_at': s['created_at'], 'progress': _progress_of(conn, s)}
    return {**learner, 'active_session': active_public, 'initial_assessment_done': evaluated > 0, 'last_activity': last}


@router.delete('/learners/{learner_id}')
def delete_learner(learner_id: str):
    with connect(write=True) as conn:
        _learner(conn, learner_id)
        conn.execute('DELETE FROM learners WHERE id=?', (learner_id,))
    return {'status': 'deleted'}


@router.post('/learners/{learner_id}/sessions')
def start_session(learner_id: str, body: NewSession):
    with connect(write=True) as conn:
        _learner(conn, learner_id)
        active = conn.execute("SELECT * FROM sessions WHERE learner=? AND status='active' ORDER BY created_at DESC", (learner_id,)).fetchall()
        if body.kind == 'auto' and active:
            s = dict(active[0]); s['plan'] = json.loads(s['plan'])
            return {'resumed': True, 'session': _session_public(conn, s)}
        kind = body.kind
        if kind == 'auto':
            kind = 'seance' if _assessment_done(conn, learner_id) else 'evaluation'
        if kind == 'ciblee' and (body.exercise is None or body.level is None):
            raise HTTPException(422, 'Choisissez un exercice et un niveau.')
        plan = plan_session(_history(conn, learner_id), kind, body.exercise, body.level)
        for a in active:
            conn.execute("UPDATE sessions SET status='interrompue', finished_at=? WHERE id=?", (_iso(_now()), a['id']))
        sid = 'seance-' + uuid.uuid4().hex[:16]
        conn.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?)', (sid, learner_id, kind, 'active', _iso(_now()), None, json.dumps(plan, ensure_ascii=False)))
        s = _session(conn, sid)
        return {'resumed': False, 'interrupted': [a['id'] for a in active], 'session': _session_public(conn, s)}


@router.get('/sessions/{session_id}')
def get_session(session_id: str):
    with connect() as conn:
        return _session_public(conn, _session(conn, session_id))


@router.post('/sessions/{session_id}/next')
def next_item(session_id: str):
    with connect(write=True) as conn:
        s = _session(conn, session_id)
        if s['status'] == 'terminee':
            return {'status': 'complete', 'progress': _progress_of(conn, s)}
        if s['status'] != 'active':
            raise HTTPException(409, 'Cette séance a été interrompue ; commencez-en une nouvelle.')
        open_item = conn.execute('SELECT * FROM items WHERE session=? AND answered_at IS NULL ORDER BY seq LIMIT 1', (session_id,)).fetchone()
        if open_item:
            return {'status': 'item', 'item': _item_public(open_item), 'progress': _progress_of(conn, s)}
        seq = conn.execute('SELECT COUNT(*) FROM items WHERE session=?', (session_id,)).fetchone()[0]
        index, block, _ = _block_of(s['plan'], seq)
        if block is None:
            return {'status': 'complete', 'progress': _progress_of(conn, s)}
        exercise, level = block['exercise'], block['level']
        ex = cat.EXERCISE_BY_ID[exercise]
        cents = None
        if exercise == 'hauteur-seuil':
            prior = conn.execute('SELECT served, correct FROM items WHERE session=? AND exercise=? AND answered_at IS NOT NULL ORDER BY seq',
                                 (session_id, exercise)).fetchall()
            trials = [(json.loads(r['served'])['detail']['cents'], bool(r['correct'])) for r in prior]
            cents = cat.staircase_threshold(trials)['next_cents'] if trials else 200.0
        seed = random.SystemRandom().randrange(2 ** 31)
        served, answer = cat.generate(exercise, level, random.Random(seed), cents=cents)
        created = _iso(_now())
        history = _history(conn, s['learner'])
        try:
            prediction = lm.predict(history, ex['skill'], exercise, level, cents)
        except Exception as exc:  # the item stays usable; the failure is recorded, never replaced by a value
            prediction = {'status': 'error', 'reason': 'reference_model_error', 'detail': type(exc).__name__, 'model': lm.MODEL_ID}
        prediction['created_at'] = created
        served = {**served, 'block': index, 'block_reason': block['reason']}
        iid = 'item-' + uuid.uuid4().hex[:16]
        conn.execute('INSERT INTO items(id,session,learner,seq,block,exercise,level,skill,created_at,served,answer,prediction) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                     (iid, session_id, s['learner'], seq, index, exercise, level, ex['skill'], created,
                      json.dumps(served, ensure_ascii=False), json.dumps(answer), json.dumps(prediction)))
        row = conn.execute('SELECT * FROM items WHERE id=?', (iid,)).fetchone()
        return {'status': 'item', 'item': _item_public(row), 'progress': _progress_of(conn, s)}


@router.post('/items/{item_id}/answer')
def answer_item(item_id: str, body: Answer):
    with connect(write=True) as conn:
        row = conn.execute('SELECT * FROM items WHERE id=?', (item_id,)).fetchone()
        if not row:
            raise HTTPException(404, 'Exercice inconnu.')
        s = _session(conn, row['session'])
        stored_response = json.dumps(body.response, sort_keys=True)
        if row['answered_at']:
            if row['response'] == stored_response:
                return {'idempotent': True, 'item': _item_public(row, include_result=True), 'result': json.loads(row['result']), 'progress': _progress_of(conn, s)}
            raise HTTPException(409, 'Cette question a déjà reçu une réponse ; elle ne peut pas être modifiée.')
        if s['status'] != 'active':
            raise HTTPException(409, 'Cette séance est terminée ou a été interrompue.')
        served, answer = json.loads(row['served']), json.loads(row['answer'])
        try:
            result = cat.evaluate(row['exercise'], row['level'], served, answer, body.response)
        except cat.InvalidResponse as exc:
            conn.execute('UPDATE items SET invalid_attempts=invalid_attempts+1 WHERE id=?', (item_id,))
            conn.commit()
            raise HTTPException(422, str(exc))
        answered = _now()
        created = datetime.fromisoformat(row['created_at'])
        if answered <= created:  # a prediction must strictly precede its outcome
            answered = created + timedelta(microseconds=1)
        prediction = json.loads(row['prediction'])
        result['prediction'] = {'status': prediction['status'], 'p': prediction.get('p'), 'baseline': prediction.get('baseline'),
                                'n_skill': prediction.get('n_skill'), 'needed': prediction.get('needed')}
        conn.execute('UPDATE items SET answered_at=?, response=?, correct=?, score=?, result=?, response_ms=?, replays=? WHERE id=?',
                     (_iso(answered), stored_response, int(result['correct']), result['score'], json.dumps(result, ensure_ascii=False),
                      body.response_ms, min(body.replays, served.get('replays', 0)), item_id))
        row = conn.execute('SELECT * FROM items WHERE id=?', (item_id,)).fetchone()
        progress = _progress_of(conn, s)
        if progress['answered'] >= progress['total']:
            conn.execute("UPDATE sessions SET status='terminee', finished_at=? WHERE id=?", (_iso(answered), s['id']))
            progress['complete'] = True
        return {'idempotent': False, 'item': _item_public(row, include_result=True), 'result': result, 'progress': progress}


@router.post('/sessions/{session_id}/finish')
def finish_session(session_id: str):
    with connect(write=True) as conn:
        s = _session(conn, session_id)
        if s['status'] == 'active':
            # Served-but-unanswered items stay unanswered: they are not failures.
            conn.execute("UPDATE sessions SET status='terminee', finished_at=? WHERE id=?", (_iso(_now()), session_id))
    return session_summary(session_id)


@router.get('/sessions/{session_id}/summary')
def session_summary(session_id: str):
    with connect() as conn:
        s = _session(conn, session_id)
        rows = conn.execute('SELECT * FROM items WHERE session=? ORDER BY seq', (session_id,)).fetchall()
        history_before = _history(conn, s['learner'], before=s['created_at'])
        history_all = _history(conn, s['learner'])
    answered = [r for r in rows if r['answered_at']]
    by_block = []
    for i, b in enumerate(s['plan']):
        mine = [r for r in answered if r['block'] == i]
        by_block.append({'exercise': b['exercise'], 'title': cat.EXERCISE_BY_ID[b['exercise']]['title'], 'level': b['level'],
                         'reason': b['reason'], 'answered': len(mine), 'planned': b['count'], 'correct': sum(r['correct'] for r in mine)})
    before, after = mastery(history_before), mastery(history_all)
    newly = [{'exercise': e, 'title': cat.EXERCISE_BY_ID[e]['title'], 'level': l} for (e, l), v in after.items()
             if v['status'] == 'maitrise' and before[(e, l)]['status'] != 'maitrise']
    predictions = []
    for r in answered:
        p = json.loads(r['prediction'])
        predictions.append({'seq': r['seq'], 'exercise': r['exercise'], 'level': r['level'], 'status': p['status'],
                            'p': p.get('p'), 'baseline': p.get('baseline'), 'outcome': bool(r['correct'])})
    threshold = pitch_threshold([h for h in history_all if h['session'] == session_id])
    errors = {}
    for r in answered:
        res = json.loads(r['result'])
        if res.get('error_key') and cat.EXERCISE_BY_ID[r['exercise']]['mastery_window']:
            key = (r['exercise'], res['error_key'])
            errors[key] = errors.get(key, 0) + 1
    return {'session': {'id': s['id'], 'kind': s['kind'], 'status': s['status'], 'created_at': s['created_at'], 'finished_at': s['finished_at']},
            'answered': len(answered), 'planned': sum(b['count'] for b in s['plan']), 'unanswered_served': len(rows) - len(answered),
            'correct': sum(r['correct'] for r in answered), 'blocks': by_block, 'newly_mastered': newly,
            'pitch_threshold': threshold, 'predictions': predictions,
            'errors': [{'exercise': e, 'title': cat.EXERCISE_BY_ID[e]['title'], 'error': k, 'count': n} for (e, k), n in sorted(errors.items(), key=lambda x: -x[1])],
            'next_plan': plan_session(history_all, 'seance')}


def _skill_summary(history):
    out = []
    practice = [h for h in history if cat.EXERCISE_BY_ID[h['exercise']]['mastery_window']]  # measures converge on ~71 % by design
    for skill in cat.SKILLS:
        items = [h for h in practice if h['skill'] == skill['id']]
        entry = {'id': skill['id'], 'label': skill['label'], 'attempts': len(items), 'status': 'pas_assez_de_donnees'}
        if items:
            recent = items[-20:]
            chance = sum(lm.item_chance(h['exercise'], h['level']) for h in recent) / len(recent)
            rate = sum(h['correct'] for h in recent) / len(recent)
            entry.update(recent_rate=round(rate, 3), recent_count=len(recent), chance=round(chance, 3),
                         above_chance=round((rate - chance) / (1 - chance), 3) if chance < 1 else None,
                         last_practiced=items[-1]['answered_at'])
            if len(items) >= 10:
                half = len(items) // 2
                first, second = items[:half], items[half:]
                # Compare like with like: success weighted by the level reached.
                entry['trend'] = {'first_rate': round(sum(h['correct'] for h in first) / len(first), 3),
                                  'second_rate': round(sum(h['correct'] for h in second) / len(second), 3),
                                  'first_mean_level': round(sum(h['level'] for h in first) / len(first), 2),
                                  'second_mean_level': round(sum(h['level'] for h in second) / len(second), 2)}
            if len(items) >= 6:
                entry['status'] = 'evalue'
        out.append(entry)
    rated = [s for s in out if s['status'] == 'evalue']
    rated.sort(key=lambda s: (s['above_chance'] if s['above_chance'] is not None else 0))
    return out, [s['id'] for s in rated[::-1][:3]], [s['id'] for s in rated[:3]]


@router.get('/learners/{learner_id}/progress')
def progress(learner_id: str):
    with connect() as conn:
        learner = _learner(conn, learner_id)
        history = _history(conn, learner_id)
        sessions = [dict(r) for r in conn.execute('SELECT * FROM sessions WHERE learner=? ORDER BY created_at', (learner_id,)).fetchall()]
        session_rows = []
        for s in sessions:
            plan = json.loads(s['plan'])
            prog = _progress_of(conn, {**s, 'plan': plan})
            session_rows.append({'id': s['id'], 'kind': s['kind'], 'status': s['status'], 'created_at': s['created_at'],
                                 'finished_at': s['finished_at'], **prog})
        active = next((s for s in session_rows if s['status'] == 'active'), None)
    now = _now()
    m = mastery(history)
    f = frontier(history, m)
    skills, strengths, weaknesses = _skill_summary(history)
    recent = history[-40:]
    errors = {}
    for h in recent:
        key = (h['result'] or {}).get('error_key')
        if key and cat.EXERCISE_BY_ID[h['exercise']]['mastery_window']:
            errors.setdefault((h['exercise'], key), []).append(h['answered_at'])
    recurring = [{'exercise': e, 'title': cat.EXERCISE_BY_ID[e]['title'], 'error': k, 'count': len(v), 'last': max(v)}
                 for (e, k), v in errors.items() if len(v) >= 2]
    recurring.sort(key=lambda r: -r['count'])
    days = {}
    for h in history:
        d = h['answered_at'][:10]
        days.setdefault(d, {'date': d, 'answers': 0, 'correct': 0, 'skills': {}})
        days[d]['answers'] += 1; days[d]['correct'] += h['correct']
        sk = days[d]['skills'].setdefault(h['skill'], {'answers': 0, 'correct': 0})
        sk['answers'] += 1; sk['correct'] += h['correct']
    scored, abstained, errored = [], 0, 0
    for h in history:
        p = h['prediction']
        if p['status'] == 'ok':
            scored.append({'p': p['p'], 'baseline': p['baseline'], 'y': 1 if h['correct'] else 0, 'at': h['answered_at'], 'chance': p.get('chance'),
                           'exercise': h['exercise'], 'title': cat.EXERCISE_BY_ID[h['exercise']]['title'], 'level': h['level'], 'skill': h['skill'], 'n_skill': p['n_skill']})
        elif p['status'] == 'abstained':
            abstained += 1
        else:
            errored += 1
    state = lm.replay(history)
    upcoming = []
    for ex in cat.EXERCISES:
        info = f.get(ex['id'])
        if not info or info['level'] is None:
            continue
        pred = lm.predict(history, ex['skill'], ex['id'], info['level'])
        upcoming.append({'exercise': ex['id'], 'title': ex['title'], 'level': info['level'], 'available': info['available'], **pred})
    last = history[-1]['answered_at'] if history else None
    return {
        'learner': {'id': learner['id'], 'name': learner['name'], 'created_at': learner['created_at'], 'instrument': learner['instrument']},
        'last_activity': last, 'days_since_last': round((now - datetime.fromisoformat(last)).total_seconds() / 86400, 2) if last else None,
        'totals': {'answers': len(history), 'correct': sum(h['correct'] for h in history),
                   'sessions_finished': sum(s['status'] == 'terminee' for s in session_rows), 'sessions': len(session_rows)},
        'active_session': active, 'sessions': session_rows,
        'skills': skills, 'strengths': strengths, 'weaknesses': weaknesses,
        'mastery': [dict(v, title=cat.EXERCISE_BY_ID[v['exercise']]['title'], label=next(lv['label'] for lv in cat.EXERCISE_BY_ID[v['exercise']]['levels'] if lv['level'] == v['level'])) for v in m.values()],
        'frontier': f, 'pitch_threshold': pitch_threshold(history),
        'recurring_errors': recurring[:8], 'days': sorted(days.values(), key=lambda d: d['date']),
        'o08': {
            'reference_model': {'id': lm.MODEL_ID, 'min_skill_history': lm.MIN_SKILL_HISTORY,
                                'skills': {k: {'theta': round(v['theta'], 3), 'answers': v['n']} for k, v in state.items()},
                                'formula': 'P = c + (1 − c)·σ(θ − d) ; θ ← θ + U(n)·(résultat − P) ; U(n) = 1/(1 + 0,05·n)'},
            'predictions': scored[-200:], 'abstained': abstained, 'errors': errored,
            'quality': lm.quality(scored), 'upcoming': upcoming,
            'neural_models': neural_compatibility(),
        },
        'next_plan': plan_session(history, 'seance'),
    }


def neural_compatibility():
    """Why the trained O08 networks abstain on DÉCLIC learner data (checked against the registry)."""
    try:
        from .musical_registry import entries
        models = entries()
    except Exception:
        models = []
    out = []
    for m in models:
        source = m.get('source')
        out.append({'model_id': m.get('id'), 'source': source, 'instrument': m.get('instrument'),
                    'target': m.get('target'), 'architecture': m.get('model'), 'status': 'abstained',
                    'reason': {'singpad': 'Attend des résultats binaires par note chantée, sur les 270 concepts de la base SingPAD. Les compétences DÉCLIC ne leur correspondent pas.',
                               'yousician': 'Attend un score quotidien de réussite au ukulélé (base Yousician). Un score DÉCLIC a la même forme mais pas le même sens ; le contrat refuse tout autre instrument.',
                               'amme': 'Attend un score de similarité de hauteur par bloc de jeu au clavier (recherche AMME) ; non servi par défaut.'}.get(source, 'Domaine différent.')})
    return out


@router.get('/learners/{learner_id}/export')
def export(learner_id: str):
    with connect() as conn:
        learner = _learner(conn, learner_id)
        history = _history(conn, learner_id)
    vocab = [s['id'] for s in cat.SKILLS]
    items = sorted({f"{h['exercise']}@{h['level']}" for h in history})
    rows = [{'learner': learner_id, 'time': h['answered_at'], 'exercise': f"{h['exercise']}@{h['level']}",
             'obs': [[vocab.index(h['skill']), 1.0 if h['correct'] else 0.0, 1.0]]} for h in history]
    check = encode_check(rows, vocab, items)
    return {'schema': 'declic-learner-export-v1', 'learner': {'id': learner_id, 'name': learner['name']},
            'skill_vocabulary': vocab, 'item_vocabulary': items,
            'attempts': [{k: h[k] for k in ('exercise', 'level', 'skill', 'correct', 'score', 'answered_at', 'created_at', 'response_ms')} | {'prediction': h['prediction']} for h in history],
            'o08_prepared_rows': rows, 'encode_check': check,
            'limitations': ["Format compatible avec l’encodeur O08 (cloud_training.encode) ; aucun réseau n’est entraîné sur ces compétences.",
                            'Un seul apprenant ne suffit pas à entraîner ni à valider un réseau : il faut de nombreux apprenants et une partition par apprenant.']}


def encode_check(rows, vocab, items):
    try:
        from .cloud_training import encode
        x, pi, ci, diff, y, w = encode([{'exercise': r['exercise'], 'obs': r['obs']} for r in rows], len(vocab), {k: i + 1 for i, k in enumerate(items)})
        return {'accepted': True, 'groups': len(rows), 'features_shape': list(x.shape), 'targets_shape': list(y.shape),
                'note': 'Chaque réponse est un groupe atomique ; les caractéristiques du pas t ne viennent que des pas précédents.'}
    except Exception as exc:
        return {'accepted': False, 'error': type(exc).__name__}
