"""Run SYNTHETIC learners through the real DÉCLIC application, on a simulated clock.

Every learner goes through the production routes of axis7.server.app (profile → initial
assessment → sessions → items → scored answers → summaries → Parcours → O08 export), with the
same generation, scoring, mastery and planning code as a human user. Three things are isolated
for the duration of a campaign, and only inside this process:

* the database: DECLIC_LEARNING_DB points at a file named ``synthetic-*.sqlite``; the real
  learner database (runtime/learning.sqlite, profile « Melek ») is refused outright;
* the clock: ``axis7.learning._now`` reads a simulated clock, so eight weeks run in minutes;
  the production clock is untouched outside the context manager;
* item randomness: the server's item seed comes from a seeded generator so a campaign is
  reproducible (production keeps SystemRandom).

What the models may see is only what DÉCLIC stores. The hidden state of every learner (noise
per skill, practice, fatigue, the true success probability of each item) is written to a
separate ``hidden/`` folder that no model code reads.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import gzip
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import time
import types

from . import learning
from . import learning_catalog as cat
from .data import ROOT
from . import sim_learners as sl

REAL_DB = (ROOT / 'runtime/learning.sqlite').resolve()
START = datetime(2026, 9, 7, tzinfo=timezone.utc)      # a Monday; any fixed date works


class SimClock:
    def __init__(self, start=START):
        self.now = start

    def __call__(self):
        return self.now

    def set(self, dt):
        if dt > self.now:
            self.now = dt

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)

    def day(self):
        return (self.now - START).total_seconds() / 86400


def check_synthetic_path(db_path):
    path = Path(db_path).resolve()
    if path == REAL_DB or not path.name.startswith('synthetic-') or not path.suffix == '.sqlite':
        raise PermissionError(f'Refus : la simulation n’écrit que dans un fichier synthetic-*.sqlite, jamais dans {REAL_DB.name}.')
    return path


class _Response:
    def __init__(self, method, path, status, payload):
        self.status_code = status; self._payload = payload
        self.request = types.SimpleNamespace(method=method, url=types.SimpleNamespace(path=path))
        self.text = json.dumps(payload, ensure_ascii=False, default=str)

    def json(self):
        return self._payload


class DirectClient:
    """Calls the SAME route handlers of axis7.learning in-process, with the same request models.

    The HTTP transport (TestClient on axis7.server.app) costs ~10 ms per request; this keeps the
    handlers, validation and SQLite logic identical while removing the transport. A test checks
    that both transports write identical answers, scores and predictions for the same seeds."""
    ROUTES = [
        ('POST', r'/api/learn/learners', lambda m, b: learning.create_learner(learning.NewLearner(**b))),
        ('POST', r'/api/learn/learners/(?P<x>[^/]+)/sessions', lambda m, b: learning.start_session(m['x'], learning.NewSession(**b))),
        ('POST', r'/api/learn/sessions/(?P<x>[^/]+)/next', lambda m, b: learning.next_item(m['x'])),
        ('POST', r'/api/learn/items/(?P<x>[^/]+)/answer', lambda m, b: learning.answer_item(m['x'], learning.Answer(**b))),
        ('POST', r'/api/learn/sessions/(?P<x>[^/]+)/finish', lambda m, b: learning.finish_session(m['x'])),
        ('GET', r'/api/learn/sessions/(?P<x>[^/]+)/summary', lambda m, b: learning.session_summary(m['x'])),
        ('GET', r'/api/learn/learners/(?P<x>[^/]+)/progress', lambda m, b: learning.progress(m['x'])),
        ('GET', r'/api/learn/learners/(?P<x>[^/]+)/export', lambda m, b: learning.export(m['x'])),
    ]

    def _call(self, method, path, body=None):
        import re
        from fastapi import HTTPException
        from fastapi.encoders import jsonable_encoder
        for verb, pattern, handler in self.ROUTES:
            match = re.fullmatch(pattern, path)
            if verb == method and match:
                try:
                    return _Response(method, path, 200, jsonable_encoder(handler(match.groupdict(), body or {})))
                except HTTPException as exc:
                    return _Response(method, path, exc.status_code, {'detail': exc.detail})
        raise KeyError(f'{method} {path}')

    def post(self, path, json=None):
        return self._call('POST', path, json)

    def get(self, path):
        return self._call('GET', path)


@contextmanager
def isolated_app(db_path, clock: SimClock, item_rng: random.Random, transport='direct'):
    """The real learner routes, bound to a synthetic database, simulated clock and seeded items.

    transport='http' goes through axis7.server.app with a TestClient (middlewares included);
    transport='direct' calls the same handlers in-process (identical results, much faster)."""
    path = check_synthetic_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    saved = {'env': os.environ.get('DECLIC_LEARNING_DB'), 'now': learning._now, 'random': learning.random}
    seeded = types.SimpleNamespace(SystemRandom=lambda: item_rng, Random=random.Random)
    os.environ['DECLIC_LEARNING_DB'] = str(path)
    learning._now = clock
    learning.random = seeded
    try:
        if transport == 'http':
            from fastapi.testclient import TestClient
            from .server import app
            with TestClient(app) as client:
                yield client
        else:
            yield DirectClient()
    finally:
        learning._now = saved['now']
        learning.random = saved['random']
        if saved['env'] is None:
            os.environ.pop('DECLIC_LEARNING_DB', None)
        else:
            os.environ['DECLIC_LEARNING_DB'] = saved['env']


def _ok(response):
    if response.status_code != 200:
        raise RuntimeError(f'{response.request.method} {response.request.url.path} → {response.status_code} {response.text[:200]}')
    return response.json()


def _answer_key(db_path, item_id):
    """Oracle-only read of the stored correct answer (to score the true probability)."""
    with sqlite3.connect(db_path) as conn:
        return json.loads(conn.execute('SELECT answer FROM items WHERE id=?', (item_id,)).fetchone()[0])


class HiddenLog:
    """Hidden-side records, kept apart from anything a model reads."""
    def __init__(self, folder):
        self.folder = Path(folder); self.folder.mkdir(parents=True, exist_ok=True)
        self.items = gzip.open(self.folder / 'items.jsonl.gz', 'wt', encoding='utf-8')
        self.days = gzip.open(self.folder / 'days.jsonl.gz', 'wt', encoding='utf-8')
        self.events = gzip.open(self.folder / 'events.jsonl.gz', 'wt', encoding='utf-8')

    def item(self, row):
        self.items.write(json.dumps(row, ensure_ascii=False) + '\n')

    def day(self, row):
        self.days.write(json.dumps(row, ensure_ascii=False) + '\n')

    def event(self, row):
        self.events.write(json.dumps(row, ensure_ascii=False) + '\n')

    def close(self):
        for f in (self.items, self.days, self.events):
            f.close()


def run_session(client, clock, learner, rng, db_path, hidden, learner_id, oracle_samples, counters):
    learner.start_session()
    started = _ok(client.post(f'/api/learn/learners/{learner_id}/sessions', json={'kind': 'auto'}))
    session = started['session']
    sid, kind = session['id'], session['kind']
    hidden.event({'sim_id': learner.sim_id, 'day': round(clock.day(), 4), 'event': 'session_start', 'kind': kind,
                  'resumed': started['resumed'], 'session': sid})
    answered = correct = 0
    stopped = None
    while True:
        nxt = _ok(client.post(f'/api/learn/sessions/{sid}/next'))
        if nxt['status'] == 'complete':
            break
        item = nxt['item']
        _, lv = cat.level_spec(item['exercise'], item['level'])
        answer = _answer_key(db_path, item['id'])
        p_true = sl.true_success_probability(learner, item, answer, random.Random(rng.random()), oracle_samples)
        sigma = learner.sigma(item['skill'])
        result = None
        for attempt in range(3):
            response, meta = sl.respond(learner, item, rng)
            clock.advance(meta['response_ms'] / 1000)
            r = client.post(f'/api/learn/items/{item["id"]}/answer',
                            json={'response': response, 'response_ms': meta['response_ms'], 'replays': meta['replays']})
            if r.status_code == 422:                      # unscorable: DÉCLIC asks again, it is not a failure
                counters['invalid'] += 1
                continue
            result = _ok(r)
            break
        if result is None:
            stopped = 'unscorable'
            break
        ok = bool(result['result']['correct'])
        answered += 1; correct += ok
        feedback = cat.EXERCISE_BY_ID[item['exercise']]['mastery_window'] is not None
        hidden.item({'item': item['id'], 'sim_id': learner.sim_id, 'learner': learner_id, 'session': sid, 'kind': kind,
                     'day': round(clock.day(), 5), 'exercise': item['exercise'], 'level': item['level'], 'skill': item['skill'],
                     'p_true': round(p_true, 4), 'sigma': round(sigma, 5), 'ability': round(learner.ability(item['skill']), 4),
                     'practice': round(learner.practice[item['skill']], 3), 'fatigue': round(learner.fatigue, 4),
                     'lapse_p': round(learner.lapse_now(), 4), 'lapse': meta['lapse'], 'correct': ok,
                     'replays': meta['replays'], 'response_ms': meta['response_ms']})
        learner.practise(item['skill'], ok, feedback)
        learner.last_day = clock.day()
        clock.advance(rng.uniform(2, 6))                # reading the feedback
        if result['progress'].get('complete'):
            break
        floor = 20 if kind == 'evaluation' else 6
        if answered >= floor:
            p_stop = learner.session_stop * (1 + 3 * learner.fatigue) * (1.6 - learner.motivation)
            if rng.random() < p_stop:
                stopped = 'fatigue'
                break
    if stopped == 'fatigue':
        if rng.random() < 0.75:
            _ok(client.post(f'/api/learn/sessions/{sid}/finish'))
            counters['stopped_early'] += 1
        else:
            counters['left_open'] += 1            # resumed by the next 'auto' session, as in the app
    summary = _ok(client.get(f'/api/learn/sessions/{sid}/summary'))
    rate = correct / answered if answered else 0.5
    learner.motivation = min(1.0, max(0.05, learner.motivation + 0.06 * (rate - 0.65) - 0.005))
    counters['sessions'] += 1
    counters['sessions_finished'] += summary['session']['status'] == 'terminee'
    counters['answers'] += answered; counters['correct'] += correct
    hidden.event({'sim_id': learner.sim_id, 'day': round(clock.day(), 4), 'event': 'session_end', 'session': sid, 'kind': kind,
                  'answered': answered, 'correct': correct, 'stopped': stopped, 'status': summary['session']['status']})


def run_learner(client, learner, rng, days, db_path, hidden, oracle_samples, counters):
    clock = learning._now
    clock.now = START
    learner_id = _ok(client.post('/api/learn/learners', json={'name': f'SYNTHÉTIQUE {learner.sim_id}', 'instrument': 'aucun'}))['id']
    hidden.event({'sim_id': learner.sim_id, 'learner': learner_id, 'event': 'created', 'family': learner.family,
                  'variant': learner.variant})
    start_day = rng.randint(0, 6)
    for day in range(start_day, days):
        practised = _one_day(client, clock, learner, rng, day, db_path, hidden, learner_id, oracle_samples, counters)
        hidden.day({'sim_id': learner.sim_id, 'day': day, 'status': learner.status, 'motivation': round(learner.motivation, 3),
                    'practised': practised,
                    'ability': {s: round(learner.ability(s), 4) for s in sl.SKILLS},
                    'sigma': learner.snapshot(), 'practice': {s: round(v, 2) for s, v in learner.practice.items()}})
    return _finish_learner(client, learner, learner_id, counters)


def _one_day(client, clock, learner, rng, day, db_path, hidden, learner_id, oracle_samples, counters):
    """One simulated day; returns the number of sessions done. Forgetting is applied when practice resumes."""
    if True:
        # status transitions (HYPOTHESIS: daily hazards scaled by motivation)
        if learner.status == 'dropped':
            if rng.random() < 0.012:
                learner.status = 'active'; learner.returned += 1; learner.motivation = max(learner.motivation, 0.5)
                hidden.event({'sim_id': learner.sim_id, 'day': day, 'event': 'returned'})
                counters['returns'] += 1
            else:
                return 0
        if learner.status == 'break':
            if day < learner.break_until:
                return 0
            learner.status = 'active'
        if rng.random() < learner.weekly_dropout / 7 * (1.6 - learner.motivation) * 2:
            learner.status = 'dropped'
            hidden.event({'sim_id': learner.sim_id, 'day': day, 'event': 'dropped'})
            counters['dropouts'] += 1
            return 0
        if rng.random() < learner.break_rate * (1.3 - learner.motivation):
            learner.status = 'break'; learner.break_until = day + rng.randint(*learner.break_len)
            hidden.event({'sim_id': learner.sim_id, 'day': day, 'event': 'break', 'until': learner.break_until})
            return 0
        sessions_today = 0
        if rng.random() < learner.p_day * (0.5 + 0.5 * learner.motivation):
            sessions_today = 2 if rng.random() < 0.1 else 1
        for k in range(sessions_today):
            moment = START + timedelta(days=day, hours=min(23.5, learner.hour + 4 * k + rng.uniform(-1, 1)))
            clock.set(moment)
            if learner.last_day is not None:
                learner.rest(clock.day() - learner.last_day)
            run_session(client, clock, learner, rng, db_path, hidden, learner_id, oracle_samples, counters)
        return sessions_today


def _finish_learner(client, learner, learner_id, counters):
    # End of campaign: the learner's Parcours and O08 export, through the real routes.
    progress = _ok(client.get(f'/api/learn/learners/{learner_id}/progress'))
    export = _ok(client.get(f'/api/learn/learners/{learner_id}/export'))
    counters['exports_accepted'] += bool(export['encode_check'].get('accepted'))
    counters['active_end'] += learner.status == 'active'
    return {'sim_id': learner.sim_id, 'learner': learner_id, 'family': learner.family, 'variant': learner.variant,
            'answers': progress['totals']['answers'], 'sessions': progress['totals']['sessions'],
            'sessions_finished': progress['totals']['sessions_finished'], 'status_end': learner.status,
            'returned': learner.returned, 'strengths': progress['strengths'], 'weaknesses': progress['weaknesses'],
            'mastered_levels': sum(m['status'] == 'maitrise' for m in progress['mastery']),
            'o08_quality': progress['o08']['quality'], 'export_groups': export['encode_check'].get('groups')}


def run_campaign(out_dir, *, variant='A', n=200, seed=1, weeks=8, oracle_samples=120, families=None,
                 noise_scale=1.0, transport='direct', log=print):
    """Simulate `n` learners for `weeks` weeks. Returns the campaign summary (also written to disk)."""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    db_path = out / f'synthetic-{variant}{seed}-n{n}.sqlite'
    if db_path.exists():
        raise FileExistsError(f'{db_path} existe déjà : une campagne n’écrase jamais une autre.')
    population = sl.make_population(n, variant, seed, families)
    for learner in population:
        if noise_scale != 1.0:
            learner.lapse = min(0.3, learner.lapse * noise_scale)
            learner.sigma0 = {k: v * noise_scale for k, v in learner.sigma0.items()}
            learner.sigma_inf = {k: v * noise_scale for k, v in learner.sigma_inf.items()}
    hidden = HiddenLog(out / 'hidden')
    with (out / 'hidden' / 'learners.json').open('w', encoding='utf-8') as f:
        json.dump([sl.describe_learner(l) for l in population], f, ensure_ascii=False)
    counters = {k: 0 for k in ('sessions', 'sessions_finished', 'answers', 'correct', 'invalid', 'stopped_early',
                               'left_open', 'dropouts', 'returns', 'exports_accepted', 'active_end')}
    clock = SimClock()
    item_rng = random.Random(f'items-{variant}-{seed}')
    rows = []
    t0 = time.time()
    with isolated_app(db_path, clock, item_rng, transport) as client:
        for i, learner in enumerate(population):
            rows.append(run_learner(client, learner, random.Random(f'{learner.sim_id}-behaviour'), weeks * 7, db_path,
                                    hidden, oracle_samples, counters))
            if (i + 1) % 10 == 0 or i + 1 == len(population):
                log(json.dumps({'campaign': out.name, 'learners_done': i + 1, 'answers': counters['answers'],
                                'elapsed_s': round(time.time() - t0, 1)}))
    hidden.close()
    summary = {'schema': 'declic-simulation-campaign-v1', 'synthetic': True, 'variant': variant, 'seed': seed, 'n': n,
               'weeks': weeks, 'noise_scale': noise_scale, 'transport': transport, 'families': families, 'oracle_samples': oracle_samples,
               'database': db_path.name, 'elapsed_seconds': round(time.time() - t0, 1), 'counters': counters,
               'learners': rows, 'provenance': sl.PROVENANCE}
    with (out / 'campaign.json').open('w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    return summary
