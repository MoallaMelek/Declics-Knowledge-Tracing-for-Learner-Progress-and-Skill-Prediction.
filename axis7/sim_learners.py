"""Virtual DÉCLIC learners (SYNTHETIC): a hidden state, imperfect perception, learning, forgetting.

What this module is
    A simulator of learners who answer the REAL DÉCLIC items. A learner never receives the
    correct answer: every response is computed from the public stimulus the browser would play
    or draw (``served``), passed through a perception with learner-specific noise, then a
    decision rule (nearest option, same/different criterion, reproduction, tapping).
    Errors therefore fall near the right answer, more often on harder stimuli.

What it is not
    Not a model of real people. Functional forms and numbers are documented below as either
    INSPIRED by a cited study (direction or ratio taken from it) or a HYPOTHESIS chosen for
    DÉCLIC. Results obtained on these learners are a simulation study, never a validation on
    human learners.

Two simulator variants exist so that a model cannot succeed merely by recognising one set of
rules: variant 'A' (exponential learning and forgetting, Gaussian noise) and variant 'B'
(power-law learning and forgetting, logistic noise, other family mix, an atypical family).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
import copy
import math
import random

from . import learning_catalog as cat

SKILLS = [s['id'] for s in cat.SKILLS]

# ------------------------------------------------------------------ provenance of parameters
PROVENANCE = {
    'pitch_ratio_musicians': ('inspired', 'micheyl2006',
        'Seuils de hauteur des non-musiciens plus de six fois ceux des musiciens ; l’entraînement les réduit. '
        'Les valeurs absolues (médianes 25 et 4 cents) sont une hypothèse DÉCLIC.'),
    'interval_order': ('inspired', 'stambaugh2020',
        'Intervalles montants plus faciles que descendants, plus faciles qu’harmoniques ; octave la mieux reconnue ; '
        'triton, sixte mineure et septième mineure les plus confondus. Les facteurs numériques sont une hypothèse.'),
    'contour_memory': ('inspired', 'dowling1978',
        'Le contour est retenu avant les intervalles exacts ; les mélodies longues et transposées sont plus difficiles. '
        'Le facteur de longueur est une hypothèse.'),
    'tapping_variability': ('inspired', 'repp2005',
        'La variabilité des intervalles entre frappes mesure la précision ; elle dépend de l’expertise et du tempo. '
        'Les coefficients de variation choisis (3 à 12 %) sont une hypothèse.'),
    'learning_curve_A': ('hypothesis', None, 'Variante A : bruit σ(n) = σ∞ + (σ0 − σ∞)·exp(−n/τ).'),
    'learning_curve_B': ('hypothesis', None, 'Variante B : bruit σ(n) = σ∞ + (σ0 − σ∞)·(1 + n/τ)^−0,8 (loi puissance de la pratique).'),
    'forgetting_A': ('hypothesis', None, 'Variante A : pratique effective n ← n·exp(−Δjours/ρ), ρ croît avec n (consolidation).'),
    'forgetting_B': ('hypothesis', None, 'Variante B : n ← n·(1 + Δjours/ρ)^−0,5.'),
    'transfer': ('hypothesis', None, 'Transfert partiel entre compétences voisines (hauteur → intervalles, etc.).'),
    'lapses_fatigue': ('hypothesis', None, 'Inattention (réponse au hasard) et fatigue qui augmentent au fil de la séance.'),
    'habits': ('hypothesis', None, 'Jours de pratique, pauses, abandons et retours tirés par famille.'),
}

# Transfer of practice between neighbouring skills (HYPOTHESIS).
TRANSFER = {'hauteur': {'intervalles': 0.15}, 'intervalles': {'accords': 0.15, 'tonalite': 0.1},
            'memoire': {'reproduction': 0.2}, 'reproduction': {'memoire': 0.1},
            'pulsation': {'rythme': 0.2}, 'rythme': {'pulsation': 0.1}, 'accords': {'tonalite': 0.1}}

# Per-skill noise scale of a typical BEGINNER and of a typical EXPERT, in the unit the
# perception of that skill uses (HYPOTHESIS except the pitch ratio, see PROVENANCE).
UNITS = {'hauteur': 'cents (seuil 70,7 %)', 'intervalles': 'demi-tons', 'accords': 'demi-tons', 'memoire': 'demi-tons',
         'reproduction': 'demi-tons', 'pulsation': 'coefficient de variation', 'rythme': 'temps (noires)',
         'lecture': 'positions sur la portée', 'tonalite': 'demi-tons'}
BEGINNER = {'hauteur': 25.0, 'intervalles': 1.1, 'accords': 0.9, 'memoire': 0.9, 'reproduction': 0.75,
            'pulsation': 0.085, 'rythme': 0.16, 'lecture': 0.9, 'tonalite': 1.4}
EXPERT = {'hauteur': 4.0, 'intervalles': 0.22, 'accords': 0.2, 'memoire': 0.25, 'reproduction': 0.15,
          'pulsation': 0.03, 'rythme': 0.045, 'lecture': 0.12, 'tonalite': 0.3}


def _lerp_log(a, b, w):
    return math.exp(math.log(a) * (1 - w) + math.log(b) * w)


# ------------------------------------------------------------------ families
# skill_level: 0 = typical beginner, 1 = typical expert, per skill (others use 'default').
FAMILIES_A = {
    'debutant_motive': {'label': 'Débutant motivé', 'share': 0.22, 'skill_level': {'default': 0.1}, 'tau': (50, 110),
                        'p_day': (0.55, 0.85), 'motivation': (0.75, 0.95), 'lapse': (0.02, 0.05), 'rho0': (20, 40),
                        'weekly_dropout': (0.0, 0.02), 'break_rate': (0.01, 0.03), 'break_len': (2, 5), 'session_stop': (0.02, 0.05)},
    'musicien_experimente': {'label': 'Musicien expérimenté', 'share': 0.14, 'skill_level': {'default': 0.85, 'lecture': 0.95},
                        'tau': (120, 260), 'p_day': (0.35, 0.65), 'motivation': (0.6, 0.85), 'lapse': (0.01, 0.03), 'rho0': (40, 80),
                        'weekly_dropout': (0.0, 0.03), 'break_rate': (0.02, 0.05), 'break_len': (2, 6), 'session_stop': (0.02, 0.05)},
    'oreille_forte_rythme_faible': {'label': 'Bonne oreille, rythme faible', 'share': 0.16,
                        'skill_level': {'default': 0.6, 'pulsation': 0.0, 'rythme': 0.0, 'lecture': 0.4},
                        'tau': (70, 160), 'p_day': (0.4, 0.75), 'motivation': (0.6, 0.9), 'lapse': (0.02, 0.05), 'rho0': (20, 45),
                        'weekly_dropout': (0.0, 0.04), 'break_rate': (0.02, 0.05), 'break_len': (2, 6), 'session_stop': (0.03, 0.06)},
    'rythme_fort_melodie_faible': {'label': 'Bon rythme, difficultés mélodiques', 'share': 0.16,
                        'skill_level': {'default': 0.15, 'pulsation': 0.8, 'rythme': 0.75, 'lecture': 0.3},
                        'tau': (70, 160), 'p_day': (0.4, 0.75), 'motivation': (0.6, 0.9), 'lapse': (0.02, 0.05), 'rho0': (20, 45),
                        'weekly_dropout': (0.0, 0.04), 'break_rate': (0.02, 0.05), 'break_len': (2, 6), 'session_stop': (0.03, 0.06)},
    'irregulier': {'label': 'Irrégulier, longues pauses', 'share': 0.16, 'skill_level': {'default': 0.35},
                        'tau': (60, 150), 'p_day': (0.25, 0.55), 'motivation': (0.4, 0.75), 'lapse': (0.03, 0.07), 'rho0': (8, 18),
                        'weekly_dropout': (0.03, 0.08), 'break_rate': (0.06, 0.12), 'break_len': (5, 15), 'session_stop': (0.05, 0.1)},
    'en_difficulte': {'label': 'En difficulté, progresse lentement', 'share': 0.16, 'skill_level': {'default': -0.15},
                        'tau': (110, 220), 'p_day': (0.35, 0.7), 'motivation': (0.4, 0.75), 'lapse': (0.05, 0.1), 'rho0': (20, 40),
                        'weekly_dropout': (0.02, 0.08), 'break_rate': (0.03, 0.07), 'break_len': (3, 9), 'session_stop': (0.06, 0.12)},
}
# Variant B shifts every family and adds an atypical progression (plateau, then late take-off).
FAMILIES_B = {k: dict(v, share=s) for (k, v), s in zip(FAMILIES_A.items(), (0.14, 0.18, 0.12, 0.12, 0.18, 0.12))}
FAMILIES_B['debutant_motive'] = dict(FAMILIES_B['debutant_motive'], skill_level={'default': 0.0}, tau=(80, 180))
FAMILIES_B['musicien_experimente'] = dict(FAMILIES_B['musicien_experimente'], skill_level={'default': 0.7, 'lecture': 0.9})
FAMILIES_B['progression_atypique'] = {'label': 'Progression atypique (plateau puis décollage)', 'share': 0.14,
                        'skill_level': {'default': 0.05}, 'tau': (40, 90), 'plateau_items': (150, 300),
                        'p_day': (0.45, 0.8), 'motivation': (0.6, 0.9), 'lapse': (0.02, 0.06), 'rho0': (15, 35),
                        'weekly_dropout': (0.0, 0.03), 'break_rate': (0.02, 0.05), 'break_len': (2, 6), 'session_stop': (0.03, 0.07)}

VARIANTS = {'A': {'families': FAMILIES_A, 'curve': 'exponential', 'forgetting': 'exponential', 'noise': 'gaussian'},
            'B': {'families': FAMILIES_B, 'curve': 'power', 'forgetting': 'power', 'noise': 'logistic'}}


# ------------------------------------------------------------------ hidden state
@dataclass
class Learner:
    """Everything here is HIDDEN: models only ever see the answers stored by DÉCLIC."""
    sim_id: str
    family: str
    variant: str
    sigma0: dict
    sigma_inf: dict
    tau: dict
    practice: dict
    p_day: float
    motivation: float
    lapse: float
    rho0: float
    weekly_dropout: float
    break_rate: float
    break_len: tuple
    session_stop: float
    fatigue_rate: float
    base_rt: float
    replay_tendency: float
    same_bias: float
    criterion_mem: float
    criterion_rhythm: float
    span: float
    tempo_bias: float
    tempo_factor_sd: float
    clef_confusion: float
    plateau: float = 0.0
    hour: float = 18.0
    noise_kind: str = 'gaussian'
    curve: str = 'exponential'
    forgetting: str = 'exponential'
    fatigue: float = 0.0
    items_in_session: int = 0
    status: str = 'active'            # active | break | dropped
    break_until: float = -1.0
    returned: int = 0
    last_day: float | None = None
    log: list = field(default_factory=list)

    # ---- skill noise from effective practice
    def sigma(self, skill):
        n = max(0.0, self.practice[skill] - self.plateau) if self.plateau else self.practice[skill]
        s0, si, t = self.sigma0[skill], self.sigma_inf[skill], self.tau[skill]
        if self.curve == 'exponential':
            base = si + (s0 - si) * math.exp(-n / t)
        else:
            base = si + (s0 - si) * (1 + n / t) ** -0.8
        return base * (1 + self.fatigue)

    def lapse_now(self):
        return min(0.35, self.lapse * (1 + 2 * self.fatigue))

    def snapshot(self):
        return {s: round(self.sigma(s), 5) for s in SKILLS}

    def ability(self, skill):
        """A common 0..1 scale for display: 0 = typical beginner noise, 1 = typical expert noise."""
        s = self.sigma(skill) / (1 + self.fatigue)
        a = math.log(BEGINNER[skill] / s) / math.log(BEGINNER[skill] / EXPERT[skill])
        return max(-0.5, min(1.5, a))

    def practise(self, skill, correct, feedback):
        gain = 1.0 + (0.3 if (not correct and feedback) else 0.0)
        self.practice[skill] += gain
        for other, k in TRANSFER.get(skill, {}).items():
            self.practice[other] += k * gain
        self.items_in_session += 1
        self.fatigue = self.fatigue_rate * max(0, self.items_in_session - 8) / 10

    def rest(self, days):
        """Forgetting between two moments separated by `days`."""
        if days <= 0:
            return
        for s in SKILLS:
            rho = self.rho0 * (1 + self.practice[s] / 100)
            if self.forgetting == 'exponential':
                self.practice[s] *= math.exp(-days / rho)
            else:
                self.practice[s] *= (1 + days / rho) ** -0.5

    def start_session(self):
        self.items_in_session = 0
        self.fatigue = 0.0


def _u(rng, lo_hi):
    lo, hi = lo_hi
    return rng.uniform(lo, hi)


def make_learner(sim_id, family, variant, rng: random.Random):
    """Draw an individual from a family: every parameter varies, so no two learners are clones."""
    fam = VARIANTS[variant]['families'][family]
    sigma0, sigma_inf, tau = {}, {}, {}
    for s in SKILLS:
        level = fam['skill_level'].get(s, fam['skill_level']['default']) + rng.gauss(0, 0.18)
        start = _lerp_log(BEGINNER[s], EXPERT[s], max(-0.6, min(1.2, level)))
        floor = _lerp_log(EXPERT[s], BEGINNER[s], max(0.0, min(0.6, 0.15 + rng.gauss(0, 0.08) - 0.1 * level)))
        sigma0[s] = start
        sigma_inf[s] = min(floor, start * 0.95)
        tau[s] = _u(rng, fam['tau']) * math.exp(rng.gauss(0, 0.25))
    variant_spec = VARIANTS[variant]
    return Learner(
        sim_id=sim_id, family=family, variant=variant, sigma0=sigma0, sigma_inf=sigma_inf, tau=tau,
        practice={s: 0.0 for s in SKILLS}, p_day=_u(rng, fam['p_day']), motivation=_u(rng, fam['motivation']),
        lapse=_u(rng, fam['lapse']), rho0=_u(rng, fam['rho0']), weekly_dropout=_u(rng, fam['weekly_dropout']),
        break_rate=_u(rng, fam['break_rate']), break_len=fam['break_len'], session_stop=_u(rng, fam['session_stop']),
        fatigue_rate=rng.uniform(0.05, 0.25), base_rt=rng.uniform(2.0, 4.5), replay_tendency=rng.uniform(0.2, 0.8),
        same_bias=rng.gauss(0, 0.15), criterion_mem=rng.uniform(0.45, 0.85), criterion_rhythm=rng.uniform(0.12, 0.22),
        span=rng.uniform(5.0, 8.5), tempo_bias=rng.gauss(-0.015, 0.02), tempo_factor_sd=rng.uniform(0.04, 0.12),
        clef_confusion=rng.uniform(0.05, 0.3), plateau=_u(rng, fam['plateau_items']) if 'plateau_items' in fam else 0.0,
        hour=rng.uniform(8, 22), noise_kind=variant_spec['noise'], curve=variant_spec['curve'], forgetting=variant_spec['forgetting'])


def make_population(n, variant='A', seed=1, families=None):
    """n learners whose families follow the variant's shares (exact proportional allocation)."""
    fams = VARIANTS[variant]['families']
    names = [f for f in fams if families is None or f in families]
    total = sum(fams[f]['share'] for f in names)
    counts = {f: int(n * fams[f]['share'] / total) for f in names}
    for f in sorted(names, key=lambda f: -(n * fams[f]['share'] / total % 1))[:n - sum(counts.values())]:
        counts[f] += 1
    rng = random.Random(f'declic-sim-{variant}-{seed}')
    out, i = [], 0
    for f in names:
        for _ in range(counts[f]):
            out.append(make_learner(f'{variant}{seed}-{i:04d}', f, variant, random.Random(rng.random())))
            i += 1
    rng.shuffle(out)
    return out


# ------------------------------------------------------------------ perception helpers
def _noise(learner, rng, sd):
    if sd <= 0:
        return 0.0
    if learner.noise_kind == 'gaussian':
        return rng.gauss(0, sd)
    u = min(max(rng.random(), 1e-12), 1 - 1e-12)          # logistic with the same standard deviation
    return sd * math.sqrt(3) / math.pi * math.log(u / (1 - u))


def _averaged(learner, rng, sd, listens):
    """Re-listening averages independent perceptions: noise / sqrt(listens)."""
    return _noise(learner, rng, sd / math.sqrt(max(1, listens)))


def _options(served):
    return [o['value'] for o in served.get('options', [])]


def _tones(served):
    return [e for e in served.get('audio', []) if 'click' not in e]


def _midi(e):
    return e['midi'] if 'midi' in e else 69 + 12 * math.log2(e['hz'] / 440)


def _confidence(margin, sd):
    return 1 - math.exp(-abs(margin) / max(sd, 1e-9))


def _listens(learner, served, rng, conf_first):
    """1 listen, plus replays when unsure (the interface allows served['replays'])."""
    replays = 0
    allowed = int(served.get('replays', 0))
    while replays < allowed and conf_first < 0.55 and rng.random() < learner.replay_tendency:
        replays += 1
        conf_first += 0.2
    return replays


# ------------------------------------------------------------------ one response per exercise
def respond(learner: Learner, item: dict, rng: random.Random):
    """The learner's response to a public item (as returned by /api/learn/.../next).

    Returns (response_dict, meta) where meta holds replays, response time and whether the
    answer came from a lapse. Never uses the stored correct answer."""
    exercise, level, served = item['exercise'], item['level'], item['served']
    _, lv = cat.level_spec(exercise, level)
    params = lv['params']
    lapse = rng.random() < learner.lapse_now()
    fn = _RESPONDERS[exercise]
    response, conf, duration, replays = fn(learner, served, params, rng, lapse)
    rt = learner.base_rt * math.exp(rng.gauss(0, 0.3)) * (1 + 0.8 * (1 - conf)) + duration * (1 + replays)
    if lapse:
        rt *= rng.uniform(0.4, 0.9)
    return response, {'replays': replays, 'response_ms': int(min(rt, 600) * 1000), 'lapse': lapse, 'confidence': round(conf, 3)}


def _pitch(learner, served, params, rng, lapse):
    opts = _options(served)
    if lapse:
        return {'choice': rng.choice(opts)}, 0.2, 1.4, 0
    f0, f1 = served['audio'][0]['hz'], served['audio'][1]['hz']
    cents = 1200 * math.log2(f1 / f0)
    sd = learner.sigma('hauteur') / 0.545           # threshold = 70.7 % point of a cumulative normal
    first = cents + _noise(learner, rng, sd)
    replays = _listens(learner, served, rng, _confidence(first, sd))
    perceived = (first + sum(cents + _noise(learner, rng, sd) for _ in range(replays))) / (1 + replays)
    choice = 'higher' if perceived > 0 else 'lower'
    return {'choice': choice}, _confidence(perceived, sd), 1.4, replays


def _interval_factor(size, mode):
    f = {'up': 1.0, 'down': 1.25, 'harmonic': 1.5}[mode]
    if size == 12:
        f *= 0.6
    if size in (6, 8, 10):
        f *= 1.25
    return f


def _intervals(learner, served, params, rng, lapse):
    opts = _options(served)
    if lapse:
        return {'choice': rng.choice(opts)}, 0.2, 1.7, 0
    a, b = [_midi(e) for e in _tones(served)[:2]]
    size = abs(b - a)
    sd = learner.sigma('intervalles') * _interval_factor(round(size), params['mode'])
    first = size + _noise(learner, rng, sd)
    sizes = [int(v) for v in opts]
    margin = lambda p: sorted(abs(p - s) for s in sizes)[1] - sorted(abs(p - s) for s in sizes)[0] if len(sizes) > 1 else 1
    replays = _listens(learner, served, rng, _confidence(margin(first), sd))
    perceived = (first + sum(size + _noise(learner, rng, sd) for _ in range(replays))) / (1 + replays)
    choice = min(sizes, key=lambda s: abs(perceived - s))
    return {'choice': str(choice)}, _confidence(margin(perceived), sd), 1.7, replays


def _chords(learner, served, params, rng, lapse):
    opts = _options(served)
    if lapse:
        return {'choice': rng.choice(opts)}, 0.2, 1.6, 0
    notes = sorted(_midi(e) for e in _tones(served))
    sd = learner.sigma('accords') * (1.3 if params.get('inversions') else 1.0)

    def perceive():
        return [n + _noise(learner, rng, sd) for n in notes]

    def best(perceived):
        scores = {}
        for q in opts:
            template = cat.CHORDS[q][1]
            options = []
            for root in perceived:
                rel = sorted(((p - root) % 12) for p in perceived)
                tpl = sorted(t % 12 for t in template)
                if len(rel) == len(tpl):
                    options.append(sum(min(abs(r - t), 12 - abs(r - t)) for r, t in zip(rel, tpl)))
            scores[q] = min(options) if options else 99
        ranked = sorted(scores.items(), key=lambda kv: kv[1])
        return ranked[0][0], (ranked[1][1] - ranked[0][1]) if len(ranked) > 1 else 1
    choice, margin = best(perceive())
    replays = _listens(learner, served, rng, _confidence(margin, sd))
    for _ in range(replays):
        # Each listen gives a new perception; the learner keeps the clearest one.
        c2, m2 = best(perceive())
        if m2 > margin:
            choice, margin = c2, m2
    return {'choice': choice}, _confidence(margin, sd), 1.6, replays


def _split_melodies(served):
    tones = _tones(served)
    half = len(tones) // 2
    return [_midi(e) for e in tones[:half]], [_midi(e) for e in tones[half:]]


def _melodies(learner, served, params, rng, lapse):
    opts = _options(served)
    first, second = _split_melodies(served)
    duration = 0.42 * len(first) * 2 + 1.0
    if lapse:
        return {'choice': rng.choice(opts)}, 0.2, duration, 0
    L = len(first)
    memory = 1 + 0.12 * (L - 3) + (0.2 if params.get('transpose') else 0) + (0.25 if not params.get('tonal', True) else 0)
    sd = learner.sigma('memoire') * memory

    def compare():
        i1 = [b - a + _noise(learner, rng, sd) for a, b in zip(first, first[1:])]
        i2 = [b - a + _noise(learner, rng, sd * 0.7) for a, b in zip(second, second[1:])]
        sign = lambda v: 0 if abs(v) < 0.35 else (1 if v > 0 else -1)
        contour_changes = sum(sign(x) != sign(y) for x, y in zip(i1, i2))
        diff = max(abs(x - y) for x, y in zip(i1, i2))
        return contour_changes, diff
    changes, diff = compare()
    criterion = learner.criterion_mem + learner.same_bias
    margin = abs(diff - criterion) if not changes else 1.0
    replays = _listens(learner, served, rng, _confidence(margin, sd))
    for _ in range(replays):
        c2, d2 = compare()
        changes, diff = (changes + c2) / 2, (diff + d2) / 2
    different = changes >= 1 or diff > criterion
    return {'choice': 'different' if different else 'same'}, _confidence(abs(diff - criterion), sd), duration, replays


def _echo(learner, served, params, rng, lapse):
    target = [int(round(_midi(e))) for e in _tones(served)]
    kb = served['keyboard']
    L = len(target)
    duration = 0.55 * L + 1.5 * L
    if lapse:
        notes = [kb['start']] + [min(kb['high'], max(kb['low'], kb['start'] + rng.randint(-5, 7))) for _ in range(L - 1)]
        return {'notes': notes}, 0.2, duration, 0
    sd = learner.sigma('reproduction') * (1 + 0.1 * (L - 3))
    replays = _listens(learner, served, rng, 0.4 if L > 4 else 0.8)
    sd /= math.sqrt(1 + replays)
    scale = set(cat.MAJOR)
    played = [kb['start']]
    for i in range(1, L):
        step = target[i] - target[i - 1] + _noise(learner, rng, sd)
        nxt = played[-1] + round(step)
        # Tonal snapping: a confident learner pulls an off-scale note back into C major.
        if not params.get('chromatic') and (nxt - 60) % 12 not in scale and rng.random() < 0.5:
            nxt += 1 if rng.random() < 0.5 else -1
        played.append(int(min(108, max(21, nxt))))
    # Memory span: beyond it, a note may be dropped.
    overflow = max(0.0, L - learner.span)
    if overflow and rng.random() < min(0.8, 0.25 * overflow) and len(played) > 2:
        del played[rng.randrange(1, len(played))]
    conf = 1 - min(1, sd)
    return {'notes': played}, max(0.05, conf), duration, replays


def _pulse(learner, served, params, rng, lapse):
    tap = served['tap']
    ioi, sync, cont = tap['ioi'], tap['sync'], tap['cont']
    cv = learner.sigma('pulsation')
    slow = 1 + max(0, (0.75 - ioi)) * -0.5 + max(0, ioi - 0.75) * 0.6        # slow tempi are harder to hold
    cv *= slow
    taps = [k * ioi + rng.gauss(-0.03, cv * ioi * 0.8) for k in range(sync)]
    t = taps[-1]
    drift = learner.tempo_bias * ioi + rng.gauss(0, 0.01 * ioi)
    stop_early = lapse and rng.random() < 0.5
    n_cont = cont if not stop_early else rng.randint(1, max(1, cont // 2 - 1))
    for k in range(n_cont):
        t += ioi + drift * (1 + k / max(cont, 1)) + _noise(learner, rng, cv * ioi)
        taps.append(t)
    if lapse and not stop_early:
        # a doubled or missing tap
        if rng.random() < 0.5 and len(taps) > 4:
            del taps[rng.randrange(sync, len(taps))]
        else:
            i = rng.randrange(sync, len(taps))
            taps.insert(i, taps[i] - ioi * rng.uniform(0.15, 0.3))
    duration = (sync + cont) * ioi + 1.0
    return {'taps': [round(x, 4) for x in sorted(taps)]}, max(0.05, 1 - cv / 0.1), duration, 0


def _split_rhythms(served):
    beat = 60 / 90
    clicks = [e['t'] for e in served['audio'] if 'click' in e]
    first = [t / beat for t in clicks if t < 4 * beat - 1e-6]
    second = [t / beat - 6 for t in clicks if t >= 6 * beat - 1e-6]
    return first, second


def _rhythms(learner, served, params, rng, lapse):
    opts = _options(served)
    if lapse:
        return {'choice': rng.choice(opts)}, 0.2, 9.0, 0
    a, b = _split_rhythms(served)
    sd = learner.sigma('rythme')

    def compare():
        pa = [t + _noise(learner, rng, sd) for t in a]
        pb = [t + _noise(learner, rng, sd) for t in b]
        # Counting dense onsets (sixteenths) can fail when timing is coarse.
        miscount = min(abs(x - y) for x, y in zip(sorted(a), sorted(a)[1:])) < 2.2 * sd if len(a) > 1 else False
        if len(pa) != len(pb):
            return (0.0 if miscount and rng.random() < 0.5 else 1.0), 1.0
        return max(abs(x - y) for x, y in zip(pa, pb)), 0.0
    diff, counted = compare()
    criterion = learner.criterion_rhythm + learner.same_bias * 0.1
    replays = _listens(learner, served, rng, _confidence(diff - criterion, sd))
    for _ in range(replays):
        d2, _ = compare()
        diff = (diff + d2) / 2
    return {'choice': 'different' if diff > criterion else 'same'}, _confidence(diff - criterion, sd), 9.0, replays


def _rhythm_echo(learner, served, params, rng, lapse):
    beat = 60 / 90
    onsets = [(e['t'] - 4 * beat) / beat for e in served['audio'] if 'click' not in e]
    sd = learner.sigma('rythme')
    tempo = 1 + rng.gauss(0, learner.tempo_factor_sd)
    start = rng.uniform(0.3, 0.8)
    beats = list(onsets)
    smallest = min(b - a for a, b in zip(onsets, onsets[1:])) if len(onsets) > 1 else 1
    # Very short values may be merged or doubled when timing is coarse (HYPOTHESIS).
    if lapse or (smallest <= 0.25 and rng.random() < min(0.6, sd * 2.5)):
        if rng.random() < 0.5 and len(beats) > 2:
            del beats[rng.randrange(1, len(beats))]
        else:
            beats.insert(1, beats[0] + smallest / 2)
    taps = [start + o * beat * tempo + _noise(learner, rng, sd * beat) for o in beats]
    replays = _listens(learner, served, rng, 0.8 - sd * 2)
    if replays:
        taps = [start + o * beat * tempo + _noise(learner, rng, sd * beat / math.sqrt(1 + replays)) for o in beats]
    taps = sorted(taps)
    for i in range(1, len(taps)):                     # a key cannot be pressed twice at the same instant
        taps[i] = max(taps[i], taps[i - 1] + 0.03)
    return {'taps': [round(t, 4) for t in taps]}, max(0.05, 1 - sd * 4), 9.0 + 4 * (1 + replays), replays


TREBLE_STAFF, BASS_STAFF = (30, 38), (18, 26)


def _reading(learner, served, params, rng, lapse):
    staff = served['staff']
    index = staff['letter'] + 7 * staff['octave']
    if lapse:
        out = {'choice': rng.choice(cat.LETTERS)}
        if served.get('accidentals'):
            out['accidental'] = rng.choice(['natural', 'sharp', 'flat'])
        return out, 0.2, 0.0, 0
    sd = learner.sigma('lecture')
    lo, hi = TREBLE_STAFF if staff['clef'] == 'treble' else BASS_STAFF
    ledger = max(0, lo - index, index - hi) / 2           # ledger lines make positions harder to count
    perceived = index + round(_noise(learner, rng, sd * (1 + 0.6 * ledger)))
    # Reading the bass clef as if it were the treble clef shifts the name by a third (sol -> mi).
    confusion = learner.clef_confusion * (sd / BEGINNER['lecture'])
    if staff['clef'] == 'bass' and rng.random() < confusion:
        perceived += 12
    out = {'choice': cat.LETTERS[perceived % 7]}
    if served.get('accidentals'):
        true_acc = staff.get('accidental') or 'natural'
        out['accidental'] = true_acc if rng.random() > min(0.6, sd * 0.4) else 'natural'
    conf = 1 - min(1, sd * (1 + 0.6 * ledger))
    return out, max(0.05, conf), 0.0, 0


def _tonic_and_roots(served):
    chords = {}
    for e in served['audio']:
        chords.setdefault(round(e['t'], 3), []).append(_midi(e))
    times = sorted(chords)
    return [min(chords[t]) for t in times], times


def _degrees(learner, served, params, rng, lapse):
    opts = _options(served)
    if lapse:
        return {'choice': rng.choice(opts)}, 0.2, 5.0, 0
    basses, times = _tonic_and_roots(served)
    target = basses[-1]                             # the final single tone
    tonic = basses[0] + 24                          # the cadence starts on I (bass two octaves below)
    scale = cat.HARMONIC_MINOR if params['mode'] == 'minor' else cat.MAJOR
    sd = learner.sigma('tonalite')
    true = (target - tonic) % 12

    def perceive():
        return (true + _noise(learner, rng, sd)) % 12

    def nearest(p):
        dist = {d: min(abs(p - scale[int(d) - 1]), 12 - abs(p - scale[int(d) - 1])) for d in opts}
        ranked = sorted(dist.items(), key=lambda kv: kv[1])
        return ranked[0][0], (ranked[1][1] - ranked[0][1]) if len(ranked) > 1 else 1
    p = perceive()
    choice, margin = nearest(p)
    replays = _listens(learner, served, rng, _confidence(margin, sd))
    if replays:
        p = sum([p] + [perceive() for _ in range(replays)]) / (1 + replays)
        choice, margin = nearest(p)
    return {'choice': choice}, _confidence(margin, sd), 5.0, replays


ROMAN_ROOT = {'I': 0, 'ii': 2, 'IV': 5, 'V': 7, 'vi': 9, 'i': 0, 'iv': 5}


def _cadences(learner, served, params, rng, lapse):
    opts = _options(served)
    if lapse:
        return {'choice': rng.choice(opts)}, 0.2, 5.0, 0
    basses, _ = _tonic_and_roots(served)
    counts = {}
    for b in basses:
        counts[b % 12] = counts.get(b % 12, 0) + 1
    tonic_pc = max(counts, key=lambda pc: (counts[pc], pc == basses[0] % 12))
    roots = [(b - tonic_pc) % 12 for b in basses]
    sd = learner.sigma('tonalite') * 1.2
    progression = bool(params.get('progression'))

    def perceive():
        return [(r + _noise(learner, rng, sd)) % 12 for r in roots]

    def nearest(p):
        dist = {}
        for o in opts:
            romans = cat.PROGRESSIONS[o] if progression else cat.CADENCES[o][1]
            tpl = [ROMAN_ROOT[r] for r in romans]
            pairs = list(zip(p, tpl)) if progression else list(zip(p[-2:], tpl[-2:]))
            dist[o] = sum(min(abs(a - b), 12 - abs(a - b)) for a, b in pairs)
        ranked = sorted(dist.items(), key=lambda kv: kv[1])
        return ranked[0][0], (ranked[1][1] - ranked[0][1]) if len(ranked) > 1 else 1
    p = perceive()
    choice, margin = nearest(p)
    replays = _listens(learner, served, rng, _confidence(margin, sd))
    if replays:
        ps = [p] + [perceive() for _ in range(replays)]
        p = [sum(v) / len(v) for v in zip(*ps)]
        choice, margin = nearest(p)
    return {'choice': choice}, _confidence(margin, sd), 5.0, replays


_RESPONDERS = {'hauteur-comparaison': _pitch, 'hauteur-seuil': _pitch, 'intervalles': _intervals, 'accords': _chords,
               'melodies': _melodies, 'echo': _echo, 'pulsation': _pulse, 'rythmes': _rhythms, 'rythme-echo': _rhythm_echo,
               'lecture': _reading, 'degres': _degrees, 'cadences': _cadences}


# ------------------------------------------------------------------ hidden truth (oracle)
def true_success_probability(learner: Learner, item: dict, answer: dict, rng: random.Random, samples=120):
    """Probability that THIS learner, in THIS hidden state, answers THIS item correctly.

    Monte-Carlo over the learner's own response process, scored with the REAL DÉCLIC rules
    (learning_catalog.evaluate). It is an oracle for the analysis only: the `answer` it reads is
    never passed to `respond`, and the learner's state is copied so nothing changes."""
    probe = copy.copy(learner)
    probe.log = []
    hits = 0
    valid = 0
    for _ in range(samples):
        response, _meta = respond(probe, item, rng)
        try:
            result = cat.evaluate(item['exercise'], item['level'], item['served'], answer, response)
        except cat.InvalidResponse:
            continue                               # an unscorable response is retried by DÉCLIC, not failed
        valid += 1
        hits += bool(result['correct'])
    return hits / valid if valid else 0.0


def describe_learner(learner: Learner):
    d = asdict(learner)
    d.pop('log', None)
    return d
