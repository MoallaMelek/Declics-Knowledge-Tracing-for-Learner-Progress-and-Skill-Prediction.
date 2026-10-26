'use strict';
// Small DOM/SVG helpers shared by the views. Text always goes through textContent.
(function (L) {
  const NS = 'http://www.w3.org/2000/svg';
  function h(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') node.className = v;
      else if (k === 'text') node.textContent = v;
      else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? '' : String(v));
    }
    for (const c of children.flat(Infinity)) if (c !== null && c !== undefined && c !== false) node.append(c instanceof Node ? c : document.createTextNode(String(c)));
    return node;
  }
  function s(tag, attrs, ...children) {
    const node = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'text') node.textContent = v;
      else if (k === 'style') node.setAttribute('style', v);
      else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, String(v));
    }
    for (const c of children.flat()) if (c) node.append(c);
    return node;
  }
  function table(head, rows, caption) {
    return h('div', {class: 'table-scroll'}, h('table', {},
      caption ? h('caption', {text: caption}) : null,
      h('thead', {}, h('tr', {}, head.map(x => h('th', {scope: 'col', text: x})))),
      h('tbody', {}, rows.map(r => h('tr', {}, r.map(v => h('td', {text: v === null || v === undefined ? '—' : String(v)})))))));
  }
  // replaceChildren() would print "null"; optional parts are skipped instead.
  function put(node, ...children) { node.replaceChildren(...children.flat().filter(c => c !== null && c !== undefined && c !== false)); return node; }
  const reducedMotion = () => typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Success fraction 0..1 → one ink-blue scale (pale = few successes, deep = many). It never reaches the paper
  // colour, so a low value stays visible and is never confused with a gap (not measured). Missing values get no colour.
  const STOPS = [[0, [176, 196, 217]], [0.5, [92, 128, 168]], [1, [15, 42, 74]]];
  function ramp(v) {
    const x = Math.max(0, Math.min(1, v));
    for (let i = 1; i < STOPS.length; i++) {
      if (x <= STOPS[i][0]) {
        const [a, ca] = STOPS[i - 1], [b, cb] = STOPS[i], t = (x - a) / (b - a);
        return `rgb(${ca.map((c, j) => Math.round(c + (cb[j] - c) * t)).join(',')})`;
      }
    }
    return 'rgb(15,42,74)';
  }
  // Diverging blue/orange for recorded activations in [-1, 1], from the sheet colour.
  function activation(v) {
    const x = Math.max(-1, Math.min(1, v)), t = Math.abs(x);
    const base = [246, 247, 249], pos = [180, 90, 18], neg = [31, 74, 114];
    const c = x >= 0 ? pos : neg;
    return `rgb(${base.map((b, j) => Math.round(b + (c[j] - b) * t)).join(',')})`;
  }
  // Eased animation; the timer guarantees the final state when frames are paused (background tab, throttling).
  function tween(duration, step) {
    if (reducedMotion() || duration <= 0) { step(1); return () => {}; }
    let raf = 0, done = false; const start = performance.now();
    const finish = () => { if (!done) { done = true; cancelAnimationFrame(raf); step(1); } };
    const frame = now => {
      if (done) return;
      const t = Math.min(1, (now - start) / duration); step(1 - Math.pow(1 - t, 3));
      if (t < 1) raf = requestAnimationFrame(frame); else done = true;
    };
    raf = requestAnimationFrame(frame);
    const timer = setTimeout(finish, duration + 120);
    return () => { done = true; cancelAnimationFrame(raf); clearTimeout(timer); };
  }
  L.dom = {h, s, put, table, reducedMotion, ramp, activation, tween, NS};
})(window.Living = window.Living || {});
