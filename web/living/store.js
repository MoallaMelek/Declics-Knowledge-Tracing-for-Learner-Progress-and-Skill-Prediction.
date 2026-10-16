'use strict';
// Single shared state for the four synchronised views. Views subscribe; nobody keeps a private copy.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else (root.Living = root.Living || {}).store = api;
})(typeof self !== 'undefined' ? self : this, function () {
  function createStore(initial) {
    let state = initial; const listeners = new Set();
    return {
      get: () => state,
      set(patch) {
        const previous = state; state = Object.assign({}, state, patch);
        for (const fn of listeners) fn(state, previous);
      },
      subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); }
    };
  }
  const initial = () => ({
    source: 'singpad', learner: '01', learners: [], cutoff: 1, stepsTotal: 0,
    snapshot: null,          // /state payload for the current cutoff (past only)
    compareCutoff: null, compareSnapshot: null, comparisonEpoch: 0,
    selected: null,          // concept id or null
    playing: false, speed: 1, research: false, stage: 'history',
    reveals: {},             // cutoff -> /reveal payload, only after an explicit request
    inspection: null, provenance: null, selection: null, counts: null,
    status: 'loading', error: null
  });
  return {createStore, initial};
});
