'use strict';
// Network layer: cancels superseded requests and caches only cutoffs the user has visited.
// No prefetch ahead: a later cutoff would bring its outcomes into memory before the user reaches it.
(function (root, factory) {
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else (root.Living = root.Living || {}).api = api;
})(typeof self !== 'undefined' ? self : this, function (root) {
  const BASE = '/api/v7/o08/living';

  function createClient(fetchImpl, {timeoutMs = 20000} = {}) {
    const doFetch = fetchImpl || ((...a) => root.fetch(...a));
    const visited = new Map(), inspections = new Map();
    let controller = null, epoch = 0;
    const generations = new Map();
    function problem(code, status, url) {
      const messages = {
        unreachable: 'Impossible de contacter le serveur DÉCLIC. Vérifiez que l’application est démarrée, puis réessayez.',
        timeout: 'Le serveur met trop de temps à répondre. Vérifiez son état, puis réessayez.',
        cancelled: 'Requête annulée lors du changement de vue.',
        api_unavailable: 'Cette API DÉCLIC est absente. Vérifiez le port et la version du serveur avec Launch.ps1.',
        unavailable: 'Les données préparées ou les modèles ne sont pas prêts. Consultez le diagnostic de démarrage.',
        missing_data: 'Les parcours préparés sont absents ou incompatibles. Consultez le diagnostic de démarrage.',
        missing_model: 'Le modèle neuronal actif est absent ou incompatible. Vérifiez le registre des modèles.',
        wrong_version: 'Cette réponse provient d’une version DÉCLIC incompatible. Relancez la Phase 8 avec Launch.ps1.',
        authentication: 'Accès refusé. Vérifiez les autorisations de ce service.',
        invalid_response: 'Réponse incompatible. Vérifiez la version du serveur, puis réessayez.',
        conflict: 'Le modèle ou les observations ont changé, ou le reçu a expiré. Recalculez la prévision.',
        invalid_request: 'Cette demande ne respecte pas les limites du parcours.',
        server: 'Erreur du serveur. La dernière vue valide reste consultable ; réessayez après vérification.'
      };
      const e = new Error(messages[code]); e.code = code; e.status = status;
      e.diagnostic = `${code} · HTTP ${status || 'sans réponse'} · ${url.split('?')[0]}`;
      if (code === 'cancelled') e.name = 'AbortError';
      return e;
    }

    async function call(url, options = {}) {
      const guard = typeof AbortController !== 'undefined' ? new AbortController() : null;
      let timedOut = false;
      const abort = () => guard && guard.abort();
      if (options.signal) { if (options.signal.aborted) abort(); else options.signal.addEventListener('abort', abort, {once: true}); }
      const timer = setTimeout(() => { timedOut = true; abort(); }, timeoutMs);
      try {
        const response = await doFetch(url, {...options, ...(guard ? {signal: guard.signal} : {})});
        if (!response.ok) {
          const s = response.status;
          let detail; try { detail = (await response.json()).detail; } catch (_) { /* use HTTP category */ }
          const structured = s === 503 && ['missing_data', 'missing_model'].includes(detail?.code) ? detail.code : null;
          throw problem(structured || (s === 404 ? 'api_unavailable' : s === 401 || s === 403 ? 'authentication' : s === 409 ? 'conflict'
            : s === 422 ? 'invalid_request' : s === 503 ? 'unavailable' : 'server'), s, url);
        }
        try { return await response.json(); } catch (_) { throw problem('invalid_response', response.status, url); }
      } catch (e) {
        if (typeof e.code === 'string' && e.diagnostic) throw e;
        throw problem(timedOut ? 'timeout' : guard && guard.signal.aborted ? 'cancelled' : 'unreachable', null, url);
      } finally {
        clearTimeout(timer); if (options.signal) options.signal.removeEventListener('abort', abort);
      }
    }
    const key = (source, learner, cutoff) => `${generations.get(source) || ''}|${source}|${learner}|${cutoff}`;
    function accept(p, source, learner, cutoff, expected) {
      if (!p || p.source !== source || p.learner !== learner || p.cutoff !== cutoff || !p.identity
          || p.identity.source !== source || p.identity.learner !== learner || p.identity.cutoff !== cutoff
          || p.identity.generation !== expected) throw problem('invalid_response', null, BASE);
      return p;
    }

    return {
      async learners(source) {
        const started = epoch, data = await call(`${BASE}/learners?source=${encodeURIComponent(source)}`);
        if (!data || data.source !== source || !Array.isArray(data.learners) || !data.provenance?.generation) throw problem('wrong_version', null, BASE);
        if (started === epoch) generations.set(source, data.provenance.generation);
        return data;
      },
      readiness: () => call('/api/readiness'),
      cached: (source, learner, cutoff) => visited.get(key(source, learner, cutoff)) || null,
      async state(source, learner, cutoff, {fresh = false} = {}) {
        const k = key(source, learner, cutoff), started = epoch, expected = generations.get(source);
        if (fresh) visited.delete(k);   // e.g. a reveal receipt older than its 30-minute validity
        if (controller) controller.abort();
        if (visited.has(k)) return visited.get(k);
        controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
        const q = `source=${encodeURIComponent(source)}&learner=${encodeURIComponent(learner)}&cutoff=${cutoff}`;
        const payload = await call(`${BASE}/state?${q}`, controller ? {signal: controller.signal} : {});
        if (expected && payload.identity?.generation !== expected) throw problem('conflict', 409, BASE);
        accept(payload, source, learner, cutoff, expected || payload.identity?.generation);
        if (started === epoch && (!expected || generations.get(source) === expected)) visited.set(k, payload);
        return payload;
      },
      async inspect(source, learner, cutoff) {
        const k = key(source, learner, cutoff), expected = generations.get(source);
        if (!inspections.has(k)) {
          const pending = call(`${BASE}/inspect?source=${encodeURIComponent(source)}&learner=${encodeURIComponent(learner)}&cutoff=${cutoff}`)
            .then(p => accept(p, source, learner, cutoff, expected || p.identity?.generation))
            .catch(e => { if (inspections.get(k) === pending) inspections.delete(k); throw e; });
          inspections.set(k, pending);
        }
        return inspections.get(k);
      },
      reveal: receipt => call(`${BASE}/reveal`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({receipt})}),
      research: () => call('/api/v6/o08/demo/research'),
      visitedCount: () => visited.size,
      forget() { epoch++; if (controller) controller.abort(); controller = null; visited.clear(); inspections.clear(); generations.clear(); }
    };
  }
  return {createClient, BASE};
});
