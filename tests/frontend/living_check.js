// Checks the Living Learner adapters and network layer against real /api/v7/o08/living payloads written by pytest.
// usage: node living_check.js <web/living dir> <fixtures.json>
const fs = require('fs'), path = require('path');
const A = require(path.join(process.argv[2], 'adapters.js'));
const {createClient} = require(path.join(process.argv[2], 'api.js'));
const fx = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const results = [];
const check = (name, ok) => results.push([name, !!ok]);
const clone = x => JSON.parse(JSON.stringify(x));
const throws = fn => { try { fn(); return false; } catch (e) { return true; } };

(async () => {
  const states = fx.states;
  check('every served cutoff passes the causal guard', states.every(s => A.assertCausal(s) === s));
  const s5 = states.find(s => s.cutoff === 5);
  let bad = clone(s5); bad.past.push({...bad.past[0], index: 5});
  check('a payload with an observation at the cutoff is rejected', throws(() => A.assertCausal(bad)));
  bad = clone(s5); bad.trail.push({index: 5});
  check('a forecast evaluated at or after the cutoff is rejected', throws(() => A.assertCausal(bad)));
  bad = clone(s5); bad.target.index = 6;
  check('a target that is not the next step is rejected', throws(() => A.assertCausal(bad)));
  bad = clone(s5); bad.future_outcome_included = true;
  check('a payload flagged with a future outcome is rejected', throws(() => A.assertCausal(bad)));
  check('stale responses are recognised', A.sameRequest(s5, {source: s5.source, learner: s5.learner, cutoff: 5}) && !A.sameRequest(s5, {source: s5.source, learner: s5.learner, cutoff: 6}));

  // Layout depends on the vocabulary only.
  check('slot layout is deterministic', [0, 7, 133, 269].every(k => JSON.stringify(A.slot(k, 270)) === JSON.stringify(A.slot(k, 270))));
  check('slot radii stay inside the sky', Array.from({length: 270}, (_, k) => A.slot(k, 270)).every(p => Math.hypot(p.x, p.y) <= 451 && Math.hypot(p.x, p.y) >= 150));
  const early = A.constellation(states[2]), late = A.constellation(states[states.length - 1]);
  check('a concept keeps the same position at every cutoff', early.nodes.every(n => { const m = late.nodes.find(x => x.k === n.k); return !m || (m.x === n.x && m.y === n.y); }));
  check('nodes come only from served skill states', states.every(s => { const ks = new Set(s.skill_states.states.map(x => x.concept)); return A.constellation(s).nodes.every(n => ks.has(n.k)); }));
  check('only next-step concepts carry a prediction, and only when the network produced one', states.every(s => A.constellation(s).nodes.every(n =>
    (n.prediction !== null) === (!!s.target && s.target.concepts.includes(n.k) && !!(s.forecast && s.forecast.predictions)))));
  const first = A.constellation(states[0]);
  check('one observation is shown as insufficient evidence, not as a state', first.nodes.every(n => !n.observed || n.state === 'insufficient_evidence'));

  // Fingerprint: one ring per past step, one arc per evaluated concept, nothing for the hidden target outcome.
  check('fingerprint has exactly one ring per observed step', states.every(s => A.fingerprint(s).rings.length === s.cutoff));
  check('fingerprint arcs match evaluated concepts (gaps are not failures)', states.every(s => A.fingerprint(s).rings.every((r, i) => r.arcs.length === Object.keys(s.past[i].concepts).length)));
  check('the target ring carries no value', states.every(s => { const t = A.fingerprint(s).target; return !t || t.arcs.every(a => a.value === undefined); }));
  const ind = s => Object.fromEntries(A.indicators(s).map(i => [i.id, i]));
  check('recent change needs three earlier steps', !ind(states[3]).change.sufficient && ind(states[6]).change.sufficient);
  check('historical success equals the mean of observed day scores', Math.abs(ind(s5).historical.value - A.mean(s5.past.map(p => p.score))) < 1e-12);
  const cmp = A.compareIndicators(states[3], states[6]);
  check('comparison only diffs indicators that are sufficient at both moments', cmp.find(r => r.id === 'change').delta === null && cmp.find(r => r.id === 'historical').delta !== null);
  const tl = A.timeline(s5);
  check('timeline: past, next and future slots', tl.filter(x => x.kind === 'past').length === 5 && tl.filter(x => x.kind === 'next').length === 1 && tl.length === s5.steps_total);
  check('timeline future slots carry no score', tl.filter(x => x.kind === 'future').every(x => x.score === undefined && x.predicted === undefined));

  // Reveal contract and error maths.
  check('the served reveal matches the forecast it was requested for', A.acceptReveal(s5, fx.reveal));
  const forged = clone(fx.reveal); forged.comparison[0].prediction += 0.01;
  check('a reveal for different predictions is refused', !A.acceptReveal(s5, forged));
  check('a reveal for another cutoff is refused', !A.acceptReveal(states.find(s => s.cutoff === 6), fx.reveal));
  check('log-loss per note', Math.abs(A.logLoss(0.8, 3, 4) - -(3 * Math.log(0.8) + Math.log(0.2))) < 1e-12);
  check('calibration bin lookup', A.calibrationBin([{lower: 0.7, observed: 0.75}, {lower: 0.8, observed: 0.85}], 0.84).observed === 0.85 && A.calibrationBin(null, 0.5) === null);
  check('abstention reason is explained, never a number', /abstient/.test(A.reason('insufficient_atomic_history')) && /abstient/.test(A.reason('unknown')));
  check('French number formatting', A.pct(0.8123) === '81,2 %' && A.points(-0.237) === '−23,7 pts');
  check('continuous Yousician forecasts are not shown as probabilities', A.forecast('yousician', 0.806) === '80,6 / 100' && A.forecast('singpad', 0.806) === '80,6 %' && A.forecast('singpad', null) === '—');

  // Network: visited-only cache, no prefetch, superseded requests aborted.
  const log = [], signals = [];
  const fetchStub = async (url, opts = {}) => {
    log.push(url); if (opts.signal) signals.push(opts.signal);
    const cutoff = Number(new URL(url, 'http://x').searchParams.get('cutoff'));
    if (cutoff === 6) await new Promise(r => setTimeout(r, 30));
    return {ok: true, json: async () => states.find(s => s.cutoff === cutoff)};
  };
  const client = createClient(fetchStub);
  await client.state('yousician', '01', 3); await client.state('yousician', '01', 4); await client.state('yousician', '01', 3);
  check('visited cutoffs are served from cache', log.length === 2 && client.visitedCount() === 2);
  check('no cutoff is requested ahead of the user', log.every(u => /cutoff=(3|4)$/.test(u)));
  await client.state('yousician', '01', 3, {fresh: true});
  check('an expired receipt can be refreshed by refetching the same cutoff', log.length === 3 && /cutoff=3$/.test(log[2]));
  const slow = client.state('yousician', '01', 6); const fast = client.state('yousician', '01', 7);
  await fast; await slow.catch(() => null);
  check('a superseded request is aborted', signals.length >= 4 && signals[signals.length - 2].aborted);

  const failed = results.filter(r => !r[1]);
  for (const [name, ok] of results) console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}`);
  console.log(`${results.length - failed.length}/${results.length} checks passed`);
  process.exit(failed.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
