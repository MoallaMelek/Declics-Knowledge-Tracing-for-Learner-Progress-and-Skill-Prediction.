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
    for (const c of children.flat()) if (c !== null && c !== undefined && c !== false) node.append(c instanceof Node ? c : document.createTextNode(String(c)));
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
  // Success fraction 0..1 → colour (coral → amber → ivory → sage). Missing values never get a colour.
  const STOPS = [[0, [226, 104, 91]], [0.5, [232, 170, 90]], [0.8, [214, 207, 186]], [1, [124, 196, 160]]];
  function ramp(v) {
    const x = Math.max(0, Math.min(1, v));
    for (let i = 1; i < STOPS.length; i++) {
      if (x <= STOPS[i][0]) {
        const [a, ca] = STOPS[i - 1], [b, cb] = STOPS[i], t = (x - a) / (b - a);
        return `rgb(${ca.map((c, j) => Math.round(c + (cb[j] - c) * t)).join(',')})`;
      }
    }
    return 'rgb(124,196,160)';
  }
  // Diverging blue/orange for recorded activations in [-1, 1].
  function activation(v) {
    const x = Math.max(-1, Math.min(1, v)), t = Math.abs(x);
    const base = [24, 34, 34], pos = [233, 168, 92], neg = [99, 170, 214];
    const c = x >= 0 ? pos : neg;
    return `rgb(${base.map((b, j) => Math.round(b + (c[j] - b) * t)).join(',')})`;
  }
  function tween(duration, step) {
    if (reducedMotion() || duration <= 0) { step(1); return () => {}; }
    let raf = 0; const start = performance.now();
    const frame = now => { const t = Math.min(1, (now - start) / duration); step(1 - Math.pow(1 - t, 3)); if (t < 1) raf = requestAnimationFrame(frame); };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }
  L.dom = {h, s, put, table, reducedMotion, ramp, activation, tween, NS};
})(window.Living = window.Living || {});
