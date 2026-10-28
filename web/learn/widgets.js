'use strict';
// Answer instruments that replace a physical instrument: on-screen keyboard, staff, tap pad.
(function (root) {
  const Learn = root.Learn = root.Learn || {};
  const h = (...a) => Learn.h(...a);
  const NAMES = ['do', 'do♯', 'ré', 'ré♯', 'mi', 'fa', 'fa♯', 'sol', 'sol♯', 'la', 'la♯', 'si'];
  const BLACK = new Set([1, 3, 6, 8, 10]);
  // Physical key positions (event.code), independent of AZERTY/QWERTY: home row = white keys.
  const CODES = ['KeyA', 'KeyW', 'KeyS', 'KeyE', 'KeyD', 'KeyF', 'KeyT', 'KeyG', 'KeyY', 'KeyH', 'KeyU', 'KeyJ',
                 'KeyK', 'KeyO', 'KeyL', 'KeyP', 'Semicolon', 'Quote'];
  const noteName = m => `${NAMES[m % 12]}${Math.floor(m / 12) - 1}`;

  function keyboard(container, {low = 60, high = 83, start = null, max = 16, onChange = () => {}} = {}) {
    const played = [];
    const whites = [], blacks = [];
    const keyFor = {};
    const strip = h('div', {class: 'kb-keys', role: 'group', 'aria-label': 'Clavier : cliquez les touches pour jouer'});
    let whiteIndex = 0;
    for (let m = low; m <= high; m++) {
      const black = BLACK.has(m % 12);
      const key = h('button', {type: 'button', class: `kb-key ${black ? 'kb-black' : 'kb-white'}${m === start ? ' is-start' : ''}`,
        'aria-label': noteName(m) + (m === start ? ' (première note)' : ''), 'data-midi': m,
        onpointerdown: e => { e.preventDefault(); press(m); }, onkeydown: e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); press(m); } }},
        h('span', {class: 'kb-label', text: m % 12 === 0 || m === start ? noteName(m) : ''}), h('span', {class: 'kb-code'}));
      keyFor[m] = key;
      if (black) { key.style.setProperty('--i', whiteIndex); blacks.push(key); } else { whites.push(key); whiteIndex++; }
    }
    strip.style.setProperty('--whites', whiteIndex);
    strip.append(...whites, ...blacks);
    const answer = h('p', {class: 'kb-answer', 'aria-live': 'polite'});
    const undo = h('button', {type: 'button', class: 'btn btn-quiet', text: 'Effacer la dernière note', onclick: () => { played.pop(); render(); }});
    const clear = h('button', {type: 'button', class: 'btn btn-quiet', text: 'Tout effacer', onclick: () => { played.length = 0; render(); }});
    const hint = h('p', {class: 'fine kb-hint', text: 'Au clavier de l’ordinateur : la rangée du milieu joue les touches blanches à partir du do, la rangée du dessus les noires ; Maj monte d’une octave.'});
    container.replaceChildren(h('div', {class: 'kb'}, strip), answer, h('div', {class: 'actions'}, undo, clear), hint);

    function press(m) {
      if (played.length >= max) return;
      Learn.audio.note(m, 0.5);
      played.push(m); render();
      const k = keyFor[m]; if (k) { k.classList.remove('is-hit'); void k.offsetWidth; k.classList.add('is-hit'); }
    }
    function render() {
      answer.textContent = played.length ? `Votre réponse : ${played.map(noteName).join(' · ')}` : 'Votre réponse : aucune note pour l’instant.';
      undo.disabled = clear.disabled = !played.length;
      onChange(played.slice());
    }
    function onKey(e) {
      if (e.repeat || e.ctrlKey || e.altKey || e.metaKey) return;
      const i = CODES.indexOf(e.code); if (i < 0) return;
      const m = low + i + (e.shiftKey ? 12 : 0);
      if (m > high) return;
      e.preventDefault(); press(m);
    }
    document.addEventListener('keydown', onKey);
    if (navigator.keyboard && navigator.keyboard.getLayoutMap) {
      navigator.keyboard.getLayoutMap().then(map => CODES.forEach((code, i) => {
        const k = keyFor[low + i]; if (k && map.get(code)) k.querySelector('.kb-code').textContent = map.get(code).toUpperCase();
      })).catch(() => {});
    }
    render();
    return {notes: () => played.slice(), destroy: () => document.removeEventListener('keydown', onKey)};
  }

  function staff(container, spec) {
    const NS = 'http://www.w3.org/2000/svg';
    const el = (tag, attrs) => { const n = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); return n; };
    const gap = 16, top = 70, left = 20, width = 300;
    const bottomY = top + 4 * gap;
    const svg = el('svg', {viewBox: '0 0 340 210', class: 'staff-svg', role: 'img'});
    const clefName = spec.clef === 'treble' ? 'clé de sol' : 'clé de fa';
    const title = el('title', {}); title.textContent = `Une note sur une portée en ${clefName}`; svg.append(title);
    for (let i = 0; i < 5; i++) svg.append(el('line', {x1: left, x2: left + width, y1: top + i * gap, y2: top + i * gap, class: 'st-line'}));
    const glyph = el('text', {x: left + 4, y: spec.clef === 'treble' ? bottomY + 10 : top + 2 * gap + 4, class: `st-clef st-${spec.clef}`});
    glyph.textContent = spec.clef === 'treble' ? '\u{1D11E}' : '\u{1D122}';
    svg.append(glyph);
    const bottom = spec.clef === 'treble' ? 30 : 18;  // diatonic index of the bottom line: E4 / G2
    const step = spec.octave * 7 + spec.letter - bottom;
    const y = bottomY - step * gap / 2, x = left + 190;
    for (let s = -2; s >= step; s -= 2) svg.append(el('line', {x1: x - 18, x2: x + 18, y1: bottomY - s * gap / 2, y2: bottomY - s * gap / 2, class: 'st-line'}));
    for (let s = 10; s <= step; s += 2) svg.append(el('line', {x1: x - 18, x2: x + 18, y1: bottomY - s * gap / 2, y2: bottomY - s * gap / 2, class: 'st-line'}));
    svg.append(el('ellipse', {cx: x, cy: y, rx: 9.5, ry: 7, transform: `rotate(-20 ${x} ${y})`, class: 'st-head'}));
    const up = step < 4;
    svg.append(el('line', {x1: up ? x + 8.5 : x - 8.5, x2: up ? x + 8.5 : x - 8.5, y1: y, y2: up ? y - 52 : y + 52, class: 'st-stem'}));
    if (spec.accidental) {
      const acc = el('text', {x: x - 34, y: y + 7, class: 'st-acc'});
      acc.textContent = spec.accidental === 'sharp' ? '♯' : '♭'; svg.append(acc);
    }
    container.replaceChildren(svg, h('p', {class: 'fine staff-clef', text: `Clé : ${clefName}${spec.accidental ? ' · une altération est écrite devant la note' : ''}`}));
  }

  function tapper(container, {label = 'Taper', onTap = () => {}} = {}) {
    let origin = null, taps = [], active = false;
    const pad = h('button', {type: 'button', class: 'tap-pad', disabled: true, 'aria-label': 'Zone de frappe : appuyez ici ou sur la barre d’espace'},
      h('span', {class: 'tap-dot'}), h('span', {class: 'tap-label', text: label}));
    const count = h('p', {class: 'tap-count', 'aria-live': 'polite'});
    container.replaceChildren(pad, count);
    function hit(stamp) {
      if (!active || origin == null) return;
      taps.push((stamp - origin) / 1000);
      count.textContent = `${taps.length} frappe${taps.length > 1 ? 's' : ''}`;
      pad.classList.remove('is-hit'); void pad.offsetWidth; pad.classList.add('is-hit');
      onTap(taps.length);
    }
    pad.addEventListener('pointerdown', e => { e.preventDefault(); hit(e.timeStamp || performance.now()); });
    function onKey(e) {
      if (e.code !== 'Space' || e.repeat) return;
      if (!active) return;
      e.preventDefault(); hit(e.timeStamp || performance.now());
    }
    document.addEventListener('keydown', onKey);
    return {
      start(startPerf) { origin = startPerf; taps = []; active = true; pad.disabled = false; count.textContent = '0 frappe'; pad.focus({preventScroll: true}); },
      stop() { active = false; pad.disabled = true; },
      taps: () => taps.slice(),
      destroy() { document.removeEventListener('keydown', onKey); },
    };
  }

  Learn.widgets = {keyboard, staff, tapper, noteName};
})(window);
