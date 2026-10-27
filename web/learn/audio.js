'use strict';
// Sound for the exercises, synthesised in the browser (Web Audio): no file, no network, no instrument.
// An item is a list of events {t, d, midi|hz|click, v}; t and d in seconds from the start.
(function (root) {
  const Learn = root.Learn = root.Learn || {};
  let ctx = null, master = null, wave = null, live = [];

  function context() {
    const AC = root.AudioContext || root.webkitAudioContext;
    if (!AC) throw new Error('Ce navigateur ne peut pas produire de son (Web Audio indisponible).');
    if (!ctx) {
      ctx = new AC();
      master = ctx.createGain(); master.gain.value = 0.9; master.connect(ctx.destination);
      // A soft, piano-like spectrum: decreasing harmonics.
      const real = new Float32Array([0, 1, 0.42, 0.22, 0.12, 0.06, 0.03]), imag = new Float32Array(real.length);
      wave = ctx.createPeriodicWave(real, imag);
    }
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
  }

  const hzOf = e => e.hz || 440 * Math.pow(2, (e.midi - 69) / 12);

  function tone(at, e) {
    const osc = ctx.createOscillator(), gain = ctx.createGain();
    osc.setPeriodicWave(wave); osc.frequency.value = hzOf(e);
    const peak = 0.22 * (e.v == null ? 0.8 : e.v);
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(peak, at + 0.012);
    gain.gain.exponentialRampToValueAtTime(peak * 0.35, at + Math.max(0.05, e.d * 0.8));
    gain.gain.exponentialRampToValueAtTime(0.0001, at + e.d + 0.08);
    osc.connect(gain); gain.connect(master);
    osc.start(at); osc.stop(at + e.d + 0.1);
    live.push(osc);
  }

  function click(at, accent) {
    const osc = ctx.createOscillator(), gain = ctx.createGain();
    osc.type = 'triangle'; osc.frequency.value = accent ? 2400 : 1700;
    gain.gain.setValueAtTime(accent ? 0.5 : 0.35, at);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.045);
    osc.connect(gain); gain.connect(master);
    osc.start(at); osc.stop(at + 0.05);
    live.push(osc);
  }

  function stop() {
    for (const o of live) { try { o.stop(); } catch (e) { /* already stopped */ } }
    live = [];
  }

  // Plays the events. Returns {startPerf, done}: startPerf is performance.now() at t = 0,
  // used to time-stamp taps relative to the first event (a constant device latency cancels out
  // in every measure DÉCLIC computes).
  function play(events, {extra = []} = {}) {
    context(); stop();
    const startAt = ctx.currentTime + 0.12;
    let end = 0;
    for (const e of [...events, ...extra]) {
      const at = startAt + e.t;
      if (e.click) click(at, e.click === 'accent');
      else tone(at, e);
      end = Math.max(end, e.t + (e.d || 0.05));
    }
    let startPerf = performance.now() + 120;
    if (ctx.getOutputTimestamp) {
      const ts = ctx.getOutputTimestamp();
      if (ts && ts.performanceTime) startPerf = ts.performanceTime + (startAt - ts.contextTime) * 1000;
    }
    const done = new Promise(resolve => setTimeout(resolve, (startAt - ctx.currentTime + end) * 1000 + 60));
    return {startPerf, done, duration: end};
  }

  function note(midi, d = 0.6) { return play([{t: 0, d, midi, v: 0.8}]); }

  Learn.audio = {context, play, note, stop, available: () => !!(root.AudioContext || root.webkitAudioContext)};
})(window);
