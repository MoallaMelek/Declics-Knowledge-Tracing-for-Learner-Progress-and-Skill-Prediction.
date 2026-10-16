'use strict';
// Drives the real Living Learner page in a VM: web/living.html is parsed into a minimal DOM, the scripts it loads run
// in page order, time is virtual and fetch serves real /api/v7/o08/living payloads written by tests/test_phase8_living.py.
// It checks that the four views (timeline dock, constellation, fingerprint, observatory) and the URL stay in step and
// past-only while the cutoff moves, including late responses, playback and lazy inspection. It runs for both sources:
// Yousician (one indicator, K = 1, active days) and SingPAD (K source concepts, recording groups), where the sky must
// hold only the concepts evaluated up to the hidden next step and contract when the cutoff moves back.
// usage: node living_sync_check.js <web dir> <fixtures.json>
const fs = require('fs'), path = require('path'), vm = require('vm');
const WEB = process.argv[2], fx = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const HTML_NS = 'http://www.w3.org/1999/xhtml', SVG_NS = 'http://www.w3.org/2000/svg';
const pageErrors = [];

// ---- Virtual clock: timers only fire when the harness advances time, so every interleaving is deterministic.
const settle = () => new Promise(r => setImmediate(r));
const clock = (() => {
  let now = 0, seq = 0; const timers = new Map();
  return {
    now: () => now,
    setTimeout: (fn, ms = 0, ...args) => { const id = ++seq; timers.set(id, {id, at: now + Math.max(0, Number(ms) || 0), fn, args}); return id; },
    clearTimeout: id => { timers.delete(id); },
    async advance(ms) {
      const end = now + ms;
      for (;;) {
        await settle();
        let next = null;
        for (const t of timers.values()) if (t.at <= end && (!next || t.at < next.at || (t.at === next.at && t.id < next.id))) next = t;
        if (!next) break;
        timers.delete(next.id); now = next.at;
        try { next.fn(...next.args); } catch (e) { pageErrors.push(e); }
      }
      now = end; await settle();
    }
  };
})();
process.on('unhandledRejection', e => pageErrors.push(e));

// ---- Minimal DOM: just what the page scripts use, with browser semantics where the views depend on them.
class Node {
  constructor() { this.parentNode = null; this.childNodes = []; this.listeners = {}; }
  get children() { return this.childNodes.filter(n => n instanceof Element); }
  get textContent() { return this.childNodes.map(n => n.textContent).join(''); }
  set textContent(v) { this.replaceChildren(); const t = v === null || v === undefined ? '' : String(v); if (t) this.append(t); }
  adopt(n) { if (!(n instanceof Node)) n = new Text(String(n)); if (n.parentNode) n.remove(); n.parentNode = this; return n; }
  append(...ns) { for (const n of ns) this.childNodes.push(this.adopt(n)); }
  prepend(...ns) { this.childNodes.unshift(...ns.map(n => this.adopt(n))); }
  appendChild(n) { this.append(n); return n; }
  replaceChildren(...ns) { for (const c of this.childNodes) c.parentNode = null; this.childNodes = []; this.append(...ns); }
  remove() { const p = this.parentNode; if (p) { p.childNodes = p.childNodes.filter(c => c !== this); this.parentNode = null; } }
  addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); }
  removeEventListener(type, fn) { this.listeners[type] = (this.listeners[type] || []).filter(f => f !== fn); }
  querySelectorAll(sel) { const out = []; walk(this, n => { if (n !== this && matches(n, sel)) out.push(n); }); return out; }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
}
class Text extends Node {
  constructor(data) { super(); this.data = data; }
  get textContent() { return this.data; }
  set textContent(v) { this.data = String(v); }
}
const optionValue = o => o.hasAttribute('value') ? o.getAttribute('value') : o.textContent;
function sanitize(el, v) {
  if (el.getAttribute('type') !== 'range') return String(v);
  const min = Number(el.getAttribute('min') || 0), max = Number(el.getAttribute('max') || 100);
  const x = Number(v);
  return String(Math.round(Math.min(max, Math.max(min, Number.isFinite(x) ? x : (min + max) / 2))));
}
class Element extends Node {
  constructor(name, ns) { super(); this.namespaceURI = ns; this.localName = name; this.attrs = new Map(); this.style = {setProperty(k, v) { this[k] = v; }, removeProperty(k) { delete this[k]; }}; }
  get tagName() { return this.namespaceURI === HTML_NS ? this.localName.toUpperCase() : this.localName; }
  getAttribute(k) { return this.attrs.has(k) ? this.attrs.get(k) : null; }
  setAttribute(k, v) { this.attrs.set(k, String(v)); }
  removeAttribute(k) { this.attrs.delete(k); }
  hasAttribute(k) { return this.attrs.has(k); }
  get id() { return this.getAttribute('id') || ''; }
  set id(v) { this.setAttribute('id', v); }
  get className() { return this.getAttribute('class') || ''; }
  set className(v) { this.setAttribute('class', v); }
  get classList() {
    const el = this, list = () => el.className.split(/\s+/).filter(Boolean);
    const api = {contains: c => list().includes(c),
      add: (...cs) => { el.className = [...new Set([...list(), ...cs])].join(' '); },
      remove: (...cs) => { el.className = list().filter(c => !cs.includes(c)).join(' '); },
      toggle: (c, force) => { const on = force === undefined ? !list().includes(c) : !!force; if (on) api.add(c); else api.remove(c); return on; }};
    return api;
  }
  get dataset() {
    const attr = p => 'data-' + String(p).replace(/[A-Z]/g, m => '-' + m.toLowerCase());
    return new Proxy({}, {get: (_, p) => typeof p === 'string' && this.hasAttribute(attr(p)) ? this.getAttribute(attr(p)) : undefined,
                          set: (_, p, v) => { this.setAttribute(attr(p), v); return true; }});
  }
  get hidden() { return this.hasAttribute('hidden'); }
  set hidden(v) { if (v) this.setAttribute('hidden', ''); else this.removeAttribute('hidden'); }
  get disabled() { return this.hasAttribute('disabled'); }
  set disabled(v) { if (v) this.setAttribute('disabled', ''); else this.removeAttribute('disabled'); }
  get checked() { return !!this.isChecked; }
  set checked(v) { this.isChecked = !!v; }
  get min() { return this.getAttribute('min') || ''; }
  set min(v) { this.setAttribute('min', v); }
  get max() { return this.getAttribute('max') || ''; }
  set max(v) { this.setAttribute('max', v); }
  get value() {
    if (this.localName === 'option') return optionValue(this);
    if (this.localName === 'select') {
      // Options replaced since the last assignment reset the selection, as in a browser.
      const opts = this.querySelectorAll('option');
      if (this.chosen !== undefined && (this.chosen === null || opts.includes(this.chosen))) return this.chosen ? optionValue(this.chosen) : '';
      const o = opts.find(x => x.hasAttribute('selected')) || opts[0]; return o ? optionValue(o) : '';
    }
    return sanitize(this, this.raw !== undefined ? this.raw : (this.getAttribute('value') || ''));
  }
  set value(v) {
    if (this.localName === 'select') { this.chosen = this.querySelectorAll('option').find(o => optionValue(o) === String(v)) || null; return; }
    this.raw = sanitize(this, v);
  }
  get isContentEditable() { return false; }
  matches(sel) { return matches(this, sel); }
  closest(sel) { for (let n = this; n instanceof Element; n = n.parentNode) if (matches(n, sel)) return n; return null; }
  focus() { document.activeElement = this; }
  blur() { if (document.activeElement === this) document.activeElement = null; }
  scrollIntoView() {}
  getBoundingClientRect() { return {x: 0, y: 0, left: 0, top: 0, right: 800, bottom: 800, width: 800, height: 800}; }
  setPointerCapture() {}
  releasePointerCapture() {}
}
class Document extends Node {
  constructor() { super(); this.activeElement = null; }
  get body() { return this.querySelector('body'); }
  get documentElement() { return this.querySelector('html'); }
  createElement(tag) { return new Element(String(tag).toLowerCase(), HTML_NS); }
  createElementNS(ns, tag) { return new Element(tag, ns); }
  createTextNode(t) { return new Text(String(t)); }
  getElementById(id) { let found = null; walk(this, n => { if (!found && n instanceof Element && n.getAttribute('id') === id) found = n; }); return found; }
}
function walk(node, fn) { fn(node); for (const c of node.childNodes) walk(c, fn); }
// Compound selectors only: tag, #id, .class and [attr] / [attr="v"], which is all the page and this harness use.
function matches(el, sel) {
  if (!(el instanceof Element)) return false;
  const m = /^([\w-]*|\*)((?:[#.][\w-]+|\[[\w-]+(?:="[^"]*")?\])*)$/.exec(sel.trim());
  if (!m) throw new Error(`Unsupported selector in harness: ${sel}`);
  if (m[1] && m[1] !== '*' && el.localName.toLowerCase() !== m[1].toLowerCase()) return false;
  for (const p of m[2].matchAll(/([#.])([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]/g)) {
    if (p[1] === '#' && el.id !== p[2]) return false;
    if (p[1] === '.' && !el.classList.contains(p[2])) return false;
    if (p[3] && (!el.hasAttribute(p[3]) || (p[4] !== undefined && el.getAttribute(p[3]) !== p[4]))) return false;
  }
  return true;
}
function fire(target, type, init = {}) {
  const ev = {type, target, bubbles: true, defaultPrevented: false, stopped: false, altKey: false, ctrlKey: false, metaKey: false, shiftKey: false,
    preventDefault() { this.defaultPrevented = true; }, stopPropagation() { this.stopped = true; }, ...init};
  for (let n = target; n && !ev.stopped; n = n.parentNode) {
    ev.currentTarget = n;
    for (const fn of [...(n.listeners[type] || [])]) { try { fn.call(n, ev); } catch (e) { pageErrors.push(e); } }
  }
  return ev;
}

// The page itself: every element, id, initial hidden flag and select option comes from web/living.html.
const decode = t => t.replace(/&(amp|lt|gt|quot|#39|nbsp);/g, (_, e) => ({amp: '&', lt: '<', gt: '>', quot: '"', '#39': "'", nbsp: String.fromCharCode(160)})[e]);
const VOID = new Set(['meta', 'link', 'input', 'br', 'img', 'hr', 'source', 'wbr']);
function parse(doc, src) {
  const stack = [doc], re = /<!--[\s\S]*?-->|<!doctype[^>]*>|<\/([\w-]+)\s*>|<([\w-]+)((?:\s+[^\s"'>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'>]+))?)*)\s*(\/?)>|([^<]+)/gi;
  for (const m of src.matchAll(re)) {
    const top = stack[stack.length - 1];
    if (m[1]) { const name = m[1].toLowerCase(); while (stack.length > 1 && stack.pop().localName.toLowerCase() !== name); }
    else if (m[2]) {
      const svg = m[2].toLowerCase() === 'svg' || (top instanceof Element && top.namespaceURI === SVG_NS);
      const el = new Element(svg ? m[2] : m[2].toLowerCase(), svg ? SVG_NS : HTML_NS);
      for (const a of m[3].matchAll(/([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?/g)) el.setAttribute(a[1], decode(a[2] ?? a[3] ?? a[4] ?? ''));
      top.append(el);
      if (!m[4] && !VOID.has(el.localName)) stack.push(el);
    } else if (m[5]) top.append(decode(m[5]));
  }
}
const document = new Document();
parse(document, fs.readFileSync(path.join(WEB, 'living.html'), 'utf8'));
const $ = id => document.getElementById(id);

// ---- Browser globals and the network stub.
const T = fx.learners.learners.find(l => l.token === fx.token).steps, K = fx.learners.provenance.K;
const START = 2;
const UNIT = fx.source === 'singpad' ? 'groupe' : 'jour actif', READOUT = fx.source === 'singpad' ? 'Groupe' : 'Jour actif';
// Test-only ground truth (never served to the page): the concepts evaluated at each step, and where each first appears.
const firstSeen = new Map();
fx.concepts.forEach((ks, i) => ks.forEach(k => { if (!firstSeen.has(k)) firstSeen.set(k, i); }));
let address = new URL(`http://127.0.0.1/web/living.html?source=${fx.source}&learner=${fx.token}&cutoff=${START}`);
const location = {get href() { return address.href; }, get search() { return address.search; }, get hash() { return address.hash; }, get pathname() { return address.pathname; }};
const history = {replaceState(_s, _t, url) { address = new URL(url, address); }};
const BASE = '/api/v7/o08/living';
const requests = [];
let delayFor = () => 20;
const sandbox = {
  document, location, history, console, URL, URLSearchParams, AbortController, DOMException, Node,
  setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout,
  requestAnimationFrame: cb => clock.setTimeout(() => cb(clock.now()), 16), cancelAnimationFrame: clock.clearTimeout,
  performance: {now: clock.now},
  // Reduced motion: tweens settle at once; render scheduling still goes through requestAnimationFrame and timers.
  matchMedia: q => ({matches: /prefers-reduced-motion:\s*reduce/.test(q), media: q, addEventListener() {}, removeEventListener() {}}),
  fetch(url, opts = {}) {
    const u = new URL(url, 'http://127.0.0.1'), q = u.searchParams;
    const kind = u.pathname.startsWith(BASE + '/') ? u.pathname.slice(BASE.length + 1) : u.pathname;
    const app = sandbox.Living && sandbox.Living.app;
    const req = {kind, url, method: opts.method || 'GET', learner: q.get('learner'), cutoff: q.has('cutoff') ? Number(q.get('cutoff')) : null,
                 at: clock.now(), storeCutoff: app ? app.store.get().cutoff : null, aborted: false, delivered: false};
    requests.push(req);
    let status = 200, body;
    if (kind === 'learners' && q.get('source') === fx.source) body = fx.learners;
    else if (kind === 'state' && req.learner === fx.token && fx.states[req.cutoff]) body = fx.states[req.cutoff];
    else if (kind === 'inspect' && req.learner === fx.token && fx.inspections[req.cutoff]) body = fx.inspections[req.cutoff];
    else { status = 404; body = {detail: 'Not found'}; }
    // Like a real fetch, an aborted request rejects with AbortError and never delivers its body.
    return new Promise((resolve, reject) => {
      const signal = opts.signal;
      const abort = () => { clock.clearTimeout(timer); req.aborted = true; reject(new DOMException('The operation was aborted.', 'AbortError')); };
      const timer = clock.setTimeout(() => {
        if (signal) signal.removeEventListener('abort', abort);
        req.delivered = true;
        resolve({ok: status < 400, status, json: async () => JSON.parse(JSON.stringify(body))});
      }, delayFor(req));
      if (signal) { if (signal.aborted) abort(); else signal.addEventListener('abort', abort); }
    });
  }
};
sandbox.window = sandbox; sandbox.self = sandbox;
const ctx = vm.createContext(sandbox);

const results = [];
const check = (name, ok, detail = '') => results.push([name, !!ok, detail]);
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const stateRequests = () => requests.filter(r => r.kind === 'state');
const escape = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// Outcomes of steps at or after the cutoff (that do not also occur earlier) must not be in the store.
function futureOutcomeIn(text, c) {
  const seen = new Set(fx.outcomes.slice(0, c).map(String));
  return fx.outcomes.slice(c).map(String).find(v => !seen.has(v) && new RegExp(`(^|[^0-9])${escape(v)}([^0-9]|$)`).test(text)) || null;
}

// Concept ids a part of the page names: data-k attributes, "C12" labels and "Concept source 12" in text, titles and ARIA labels.
function mentioned(root) {
  const ids = new Set(), scan = t => { for (const m of t.matchAll(/(?<![\w-])C(\d+)(?!\d)|Concept source (\d+)/g)) ids.add(Number(m[1] ?? m[2])); };
  walk(root, n => {
    if (n instanceof Text) scan(n.data);
    else if (n instanceof Element) {
      if (n.hasAttribute('data-k')) ids.add(Number(n.getAttribute('data-k')));
      for (const a of ['aria-label', 'title']) if (n.hasAttribute(a)) scan(n.getAttribute(a));
    }
  });
  return ids;
}
const skyConcepts = () => $('sky').querySelectorAll('g.node').map(g => Number(g.getAttribute('data-k'))).sort((a, b) => a - b);
const skyRows = () => $('sky-table').querySelectorAll('tbody').flatMap(b => b.querySelectorAll('tr')).map(tr => tr.querySelectorAll('td').map(td => td.textContent));

// Every view, the URL and the store must describe exactly cutoff c, using only what the server sent for c.
function aspects(c) {
  const st = sandbox.Living.app.store.get(), ref = fx.states[c], unit = UNIT, out = [];
  const add = (name, ok, detail) => out.push([name, !!ok, detail]);
  add('store cutoff', st.cutoff === c && st.snapshot && st.snapshot.cutoff === c && st.snapshot.past.length === c && st.learner === fx.token,
      `cutoff ${st.cutoff}, snapshot ${st.snapshot && st.snapshot.cutoff}`);
  const range = $('cutoff');
  add('range input value', range.value === String(c) && range.max === String(T) && range.getAttribute('aria-valuetext').startsWith(`${c} ${unit}(s)`), `${range.value}/${range.max}`);
  const label = $('cutoff-label').textContent, detail = $('cutoff-detail').textContent;
  add('dock readout', label === `${READOUT} ${c} sur ${T}` && (ref.target ? detail.includes(`le résultat du pas ${c + 1} reste caché`) : detail.includes('fin du parcours enregistré'))
      && $('prev').disabled === (c <= 1) && $('next').disabled === (c >= T), `${label} · ${detail}`);
  const track = $('track');
  add('timeline track', track.querySelectorAll('rect.tl-bar').length === c && track.querySelectorAll('rect.tl-next').length === (ref.target ? 1 : 0)
      && track.querySelectorAll('line.tl-future').length === T - c - (ref.target ? 1 : 0), `${track.querySelectorAll('rect.tl-bar').length} bars`);
  const sky = $('sky'), ks = skyConcepts(), rows = skyRows();
  const served = ref.skill_states.states.map(s => s.concept).sort((a, b) => a - b);
  const allowed = new Set([...ref.past.flatMap(p => Object.keys(p.concepts).map(Number)), ...(ref.target ? ref.target.concepts : [])]);
  add('constellation nodes = this cutoff\'s skill states', same(ks, served) && ks.every(k => allowed.has(k)) && rows.length === served.length,
      `${ks} vs ${served}`);
  if (ref.K === 1) {
    const days = sky.querySelectorAll('circle.day'), kind = k => days.filter(d => d.getAttribute('class') === k).length;
    add('constellation orbit lights only observed days', kind('day') === c && kind('day next') === (ref.target ? 1 : 0) && days.length === T, `${kind('day')} lit`);
  } else {
    // Many concepts: no day orbit; labels and the table name the served concepts, counted on steps before c only.
    const labels = sky.querySelectorAll('text.node-label').map(t => t.textContent).sort(), names = rows.map(r => r[0]).sort();
    add('sky labels and table rows name exactly these concepts', same(labels, served.map(k => `C${k}`).sort()) && same(names, served.map(k => `Concept source ${k}`).sort()),
        `${labels.length} labels, ${names.length} rows`);
    const past = fx.concepts.slice(0, c), next = new Set(c < T ? fx.concepts[c] : []);
    const miscounted = rows.filter(r => { const k = Number(r[0].slice('Concept source '.length));
      return r[2] !== String(past.filter(step => step.includes(k)).length) || r[6] !== (next.has(k) ? 'oui' : 'non'); });
    add('sky counts only steps before the cutoff', miscounted.length === 0, miscounted.slice(0, 3).map(r => r.join(' / ')).join(' | '));
    // A concept first evaluated at the hidden next step belongs to its definition only: an empty star with the target ring.
    const newcomers = [...next].filter(k => firstSeen.get(k) === c), star = k => sky.querySelectorAll('g.node').find(g => g.getAttribute('data-k') === String(k));
    const filled = newcomers.filter(k => { const g = star(k); return !g || !g.querySelector('circle.node-core').classList.contains('hollow') || !g.querySelector('circle.node-target').classList.contains('on'); });
    add('concepts first evaluated at the next step are empty target stars', filled.length === 0, `${filled} of ${newcomers}`);
    const later = [...firstSeen].filter(([, i]) => i > c).map(([k]) => k), named = mentioned($('stage'));
    const leaked = later.filter(k => named.has(k)), unknown = [...named].filter(k => !firstSeen.has(k));
    add('no concept that first appears later is anywhere in the sky (stars, labels, table, inspector)', leaked.length === 0 && unknown.length === 0,
        `later ${leaked}, unknown ${unknown}`);
    const dust = sky.querySelectorAll('circle.dust-dot');
    add('vocabulary dust is fixed and anonymous; no day orbit', dust.length === ref.K && dust.every(d => !d.hasAttribute('data-k') && !d.childNodes.length)
        && sky.querySelectorAll('circle.day').length === 0, `${dust.length} dust`);
  }
  const fp = $('fp-main'), grooves = fp.querySelectorAll('circle.fp-groove'), center = fp.querySelector('text.fp-center');
  add('fingerprint rings = cutoff', fp.querySelectorAll('g.fp-ring').length === c && grooves.filter(g => !g.classList.contains('future')).length === c
      && grooves.length === T && center && center.textContent === String(c) && fp.querySelectorAll('g.fp-target').length === (ref.target ? 1 : 0),
      `${fp.querySelectorAll('g.fp-ring').length} rings`);
  if (ref.K > 1) {
    const rim = fp.querySelectorAll('g.fp-rim').flatMap(g => g.querySelectorAll('line')), lit = rim.filter(l => l.classList.contains('lit')).length;
    const past = fx.concepts.slice(0, c), pastKs = new Set(past.flat()), arcs = fp.querySelectorAll('g.fp-ring').flatMap(g => g.querySelectorAll('path.fp-arc'));
    add('fingerprint arcs and lit rim = concepts of past steps only', rim.length === ref.K && lit === pastKs.size
        && arcs.length === past.reduce((a, step) => a + step.length, 0) && arcs.every(a => pastKs.has(Number(a.getAttribute('data-k'))))
        && fp.querySelectorAll('g.fp-target').flatMap(g => g.querySelectorAll('path.fp-next')).length === (c < T ? fx.concepts[c].length : 0),
        `${lit} lit for ${pastKs.size}, ${arcs.length} arcs`);
  }
  const h3 = $('stage-detail').querySelector('h3');
  add('observatory history heading', st.stage === 'history' && h3 && h3.textContent === `${c} ${unit}(s) antérieurs, dans l’ordre`, h3 && h3.textContent);
  add('URL query', location.search === `?source=${fx.source}&learner=${fx.token}&cutoff=${c}`, location.search);
  add('status line', $('status').textContent.includes(`${unit} ${c} sur ${T}`), $('status').textContent);
  const leak = futureOutcomeIn(JSON.stringify(st), c);
  add('store holds no outcome at or after the cutoff', !leak, leak);
  return out;
}
function syncAt(label, c) { for (const [name, ok, detail] of aspects(c)) check(`${label} | ${name}`, ok, detail); }
// Many concepts: moving the cutoff back removes the stars of the steps left behind (the browser check saw 72 -> 45).
function contracts(label, before, after) {
  if (K > 1) check(`${label} | the sky contracts to a subset (${before.length} -> ${after.length} stars)`, after.length < before.length && after.every(k => before.includes(k)));
}
// While the state for `pending` is in flight, the views keep showing `shown` together: no view runs ahead of the others.
function pendingAt(label, shown, pending) {
  const st = sandbox.Living.app.store.get();
  check(`${label} | store waits for ${pending} with ${shown} on screen`, st.cutoff === pending && st.snapshot && st.snapshot.cutoff === shown,
        `cutoff ${st.cutoff}, snapshot ${st.snapshot && st.snapshot.cutoff}`);
  check(`${label} | status announces the load`, $('status').textContent.includes(`Chargement du pas ${pending}`), $('status').textContent);
  // Slider, URL and status may already reflect the request; every view must still describe the snapshot on screen.
  const own = new Set(['store cutoff', 'range input value', 'URL query', 'status line']);
  for (const [name, ok, detail] of aspects(shown)) if (!own.has(name)) check(`${label} | ${name}`, ok, detail);
}

async function slide(...values) {   // a drag over the timeline: one input event per value, faster than the 70 ms debounce
  for (const v of values) { $('cutoff').value = String(v); fire($('cutoff'), 'input'); await clock.advance(20); }
}
const key = k => fire(document.activeElement || document.body, 'keydown', {key: k});
const click = el => fire(el, 'click');
const stageButton = id => $('pipeline').querySelectorAll('.stage-btn').find(b => b.dataset.stage === id);

async function scenario() {
  // Load the scripts exactly as the page lists them.
  const scripts = document.querySelectorAll('script').map(s => s.getAttribute('src').split('?')[0]);
  const files = fs.readdirSync(path.join(WEB, 'living')).filter(f => f.endsWith('.js')).map(f => `/web/living/${f}`).sort();
  check('the page loads every web/living script, main.js last', same([...scripts].sort(), files) && scripts[scripts.length - 1] === '/web/living/main.js', scripts.join(' '));
  for (const src of scripts) vm.runInContext(fs.readFileSync(path.join(WEB, src.replace(/^\/web\//, '')), 'utf8'), ctx, {filename: src});
  const app = sandbox.Living.app, store = app.store, client = app.client;
  const snaps = [];
  store.subscribe((st, prev) => { if (st.snapshot && st.snapshot !== prev.snapshot) snaps.push(st.snapshot.cutoff); });
  check('fixture outcomes are the served past scores', fx.states[T].past.every((p, i) => p.score === fx.outcomes[i]) && fx.outcomes.length === T);
  check('fixture concepts are the served past concepts', fx.states[T].past.every((p, i) => same(Object.keys(p.concepts).map(Number).sort((a, b) => a - b), fx.concepts[i])) && fx.concepts.length === T);

  // 1. Deep link: ?cutoff=2 opens the page on that cutoff.
  await clock.advance(400);
  check('deep link selects the learner and source', $('learner').value === fx.token && $('source').value === fx.source && store.get().stepsTotal === T);
  check('the four views are shown', ['stage', 'fingerprint', 'observatory', 'dock'].every(id => !$(id).hidden));
  check('opening the page fetches only the linked cutoff', same(stateRequests().map(r => r.cutoff), [START]));
  syncAt(`deep link ${START}`, START);

  // 2. Drag forward (the 12 of the browser check 12 -> 20 -> 4): only the cutoff where the drag stops is fetched.
  const A = T - 3, B = 4, dragFrom = clock.now();
  await slide(...Array.from({length: A - START}, (_, i) => START + 1 + i));
  await clock.advance(400);
  check('a drag fetches only where it stops', same(stateRequests().filter(r => r.at >= dragFrom).map(r => r.cutoff), [A]),
        stateRequests().filter(r => r.at >= dragFrom).map(r => r.cutoff).join(','));
  syncAt(`forward to ${A}`, A);

  // 3. End key: last recorded step, nothing left to forecast.
  key('End'); await clock.advance(400);
  syncAt(`end ${T}`, T);
  const endSky = skyConcepts();

  // 4. Back below the start: the sky, the record and the observatory contract to the past of B.
  await slide(B); await clock.advance(400);
  syncAt(`back to ${B}`, B);
  contracts(`back from ${T} to ${B}`, endSky, skyConcepts());
  check(`${START} -> ${A} -> ${T} -> ${B} requests nothing in between`, same(stateRequests().map(r => r.cutoff), [START, A, T, B]), stateRequests().map(r => r.cutoff).join(','));

  // 5. A slow answer for an older cutoff loses to a newer one: aborted when the newer cutoff needs the network...
  const visited = new Set(stateRequests().map(r => r.cutoff));
  const [s1, s2] = Array.from({length: T - 5}, (_, i) => 5 + i).filter(c => !visited.has(c));
  delayFor = r => (r.kind === 'state' && (r.cutoff === s1 || r.cutoff === s2) ? 600 : 20);
  const skyAtB = skyConcepts();
  await slide(s1); await clock.advance(80);
  const slow1 = stateRequests().find(r => r.cutoff === s1) || {};
  check(`slow cutoff ${s1} is in flight`, slow1.url && !slow1.delivered && !slow1.aborted);
  pendingAt(`while ${s1} loads`, B, s1);
  await slide(3); await clock.advance(1200);
  check(`the superseded request for ${s1} is aborted and never reaches the views`, slow1.aborted && !slow1.delivered && !snaps.includes(s1));
  syncAt(`newer cutoff 3 after slow ${s1}`, 3);
  contracts(`back from ${B} to 3`, skyAtB, skyConcepts());

  // ...and ignored by the views when the newer cutoff is served from the cache (nothing aborts the older request).
  await slide(s2); await clock.advance(80);
  const slow2 = stateRequests().find(r => r.cutoff === s2) || {};
  pendingAt(`while ${s2} loads`, 3, s2);
  await slide(B); await clock.advance(100);
  check(`cached ${B} is shown while ${s2} is still pending`, store.get().snapshot.cutoff === B && slow2.url && !slow2.delivered && !slow2.aborted);
  await clock.advance(1200);
  check(`the late answer for ${s2} arrives but never reaches the views`, slow2.delivered && !snaps.includes(s2));
  syncAt(`cached ${B} after late ${s2}`, B);
  delayFor = () => 20;

  // 6. Playback at ×2 walks every step once and stops at the last one.
  $('speed').value = '2'; fire($('speed'), 'change');
  const playFrom = snaps.length; click($('play'));
  const drift = [], shrank = [];
  let last = B, pauseShown = false, sky = skyConcepts();
  for (let t = 0; t < 20000 && last < T; t += 25) {
    await clock.advance(25);
    const snap = store.get().snapshot;
    if (snap && snap.cutoff !== last) {
      last = snap.cutoff; await clock.advance(100);
      pauseShown = pauseShown || ($('play-icon').getAttribute('href') === '#i-pause' && $('play').getAttribute('aria-pressed') === 'true');
      for (const [name, ok, detail] of aspects(last)) if (!ok) drift.push(`${last}: ${name} (${detail})`);
      const now = skyConcepts(); if (!sky.every(k => now.includes(k))) shrank.push(last); sky = now;
    }
  }
  check('playback shows the pause control while playing', pauseShown);
  check('playback advances one step at a time to the end', same(snaps.slice(playFrom), Array.from({length: T - B}, (_, i) => B + 1 + i)), snaps.slice(playFrom).join(','));
  check('every playback step keeps the four views in step', drift.length === 0, drift.slice(0, 3).join(' | '));
  check('playback only adds stars to the sky', shrank.length === 0, shrank.join(','));
  const before = requests.length; await clock.advance(6000);
  check('playback stops at the last step', !store.get().playing && store.get().cutoff === T && $('play-icon').getAttribute('href') === '#i-play'
        && $('play').getAttribute('aria-pressed') === 'false' && requests.length === before);
  syncAt(`after playback ${T}`, T);

  // 7. Observatory internals: lazily inspected for the cutoff on screen only; nothing to inspect at the end.
  click(stageButton('gru')); await clock.advance(300);
  check('no inspection at the last step (no forecast)', !requests.some(r => r.kind === 'inspect') && $('stage-detail').textContent.includes('Fin du parcours enregistré'));
  const gruShows = c => {
    const ins = store.get().inspection, h3 = $('stage-detail').querySelector('h3');
    return ins && ins.cutoff === c && !ins.error && stageButton('gru').classList.contains('on') && h3 && h3.textContent === 'La mémoire du réseau, pas après pas';
  };
  await slide(T - 2); await clock.advance(400);
  check(`the GRU stage follows the slider to ${T - 2}`, gruShows(T - 2));
  key('ArrowRight'); await clock.advance(400);
  check(`the GRU stage follows the arrow key to ${T - 1}`, gruShows(T - 1));
  const inspected = requests.filter(r => r.kind === 'inspect').map(r => [r.cutoff, r.storeCutoff]);
  check('inspection is requested once per cutoff on screen, never ahead', same(inspected, [[T - 2, T - 2], [T - 1, T - 1]]), JSON.stringify(inspected));
  click(stageButton('history')); await clock.advance(300);
  syncAt(`observatory back to history at ${T - 1}`, T - 1);

  // 8. Network discipline over the whole session.
  const states = stateRequests();
  check('every state request is for the cutoff the user is on', states.every(r => r.cutoff === r.storeCutoff), states.filter(r => r.cutoff !== r.storeCutoff).map(r => r.cutoff).join(','));
  const delivered = states.filter(r => r.delivered).map(r => r.cutoff);
  check('no cutoff is downloaded twice', new Set(delivered).size === delivered.length, delivered.join(','));
  const cached = Array.from({length: T}, (_, i) => i + 1).filter(c => client.cached(fx.source, fx.token, c));
  check('the client cache holds exactly the cutoffs that were delivered', same(cached, [...new Set(delivered)].sort((a, b) => a - b)), cached.join(','));
  check('a reveal is never requested without the user', !requests.some(r => r.kind === 'reveal' || r.method === 'POST'));
  check('only known endpoints were called', requests.every(r => ['learners', 'state', 'inspect'].includes(r.kind)) && requests.filter(r => r.kind === 'learners').length === 1,
        requests.map(r => r.kind).join(','));
}

(async () => {
  try { await scenario(); } catch (e) { check('the scenario runs to the end', false, e && e.stack || String(e)); }
  check('no page error', pageErrors.length === 0, pageErrors.map(e => e && e.stack || String(e)).join('\n'));
  const failed = results.filter(r => !r[1]);
  for (const [name, ok, detail] of results) console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}${ok || !detail ? '' : `  [${detail}]`}`);
  console.log(`${results.length - failed.length}/${results.length} checks passed`);
  process.exit(failed.length ? 1 : 0);
})();
