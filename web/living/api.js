'use strict';
// Network layer: cancels superseded requests and caches only cutoffs the user has visited.
// No prefetch ahead: a later cutoff would bring its outcomes into memory before the user reaches it.
(function (root, factory) {
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else (root.Living = root.Living || {}).api = api;
})(typeof self !== 'undefined' ? self : this, function (root) {
  const BASE = '/api/v7/o08/living';

  function createClient(fetchImpl) {
    const doFetch = fetchImpl || ((...a) => root.fetch(...a));
    const visited = new Map(), inspections = new Map();
    let controller = null;

    async function call(url, options = {}) {
      const response = await doFetch(url, options);
      if (!response.ok) {
        let detail; try { detail = (await response.json()).detail; } catch (e) { detail = null; }
        const error = new Error(typeof detail === 'string' ? detail : 'Le service est momentanément indisponible.');
        error.status = response.status; throw error;
      }
      return response.json();
    }
    const key = (source, learner, cutoff) => `${source}|${learner}|${cutoff}`;

    return {
      learners: source => call(`${BASE}/learners?source=${encodeURIComponent(source)}`),
      cached: (source, learner, cutoff) => visited.get(key(source, learner, cutoff)) || null,
      async state(source, learner, cutoff, {fresh = false} = {}) {
        const k = key(source, learner, cutoff);
        if (fresh) visited.delete(k);   // e.g. a reveal receipt older than its 30-minute validity
        if (visited.has(k)) return visited.get(k);
        if (controller) controller.abort();
        controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
        const q = `source=${encodeURIComponent(source)}&learner=${encodeURIComponent(learner)}&cutoff=${cutoff}`;
        const payload = await call(`${BASE}/state?${q}`, controller ? {signal: controller.signal} : {});
        visited.set(k, payload);
        return payload;
      },
      async inspect(source, learner, cutoff) {
        const k = key(source, learner, cutoff);
        if (!inspections.has(k)) inspections.set(k, call(`${BASE}/inspect?source=${encodeURIComponent(source)}&learner=${encodeURIComponent(learner)}&cutoff=${cutoff}`)
          .catch(e => { inspections.delete(k); throw e; }));
        return inspections.get(k);
      },
      reveal: receipt => call(`${BASE}/reveal`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({receipt})}),
      research: () => call('/api/v6/o08/demo/research'),
      visitedCount: () => visited.size,
      forget() { visited.clear(); inspections.clear(); }
    };
  }
  return {createClient, BASE};
});
