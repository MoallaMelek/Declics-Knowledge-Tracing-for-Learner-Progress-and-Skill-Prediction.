'use strict';
// Shared helpers of the learner pages: API client with French errors, profile memory, DOM helper.
(function (root) {
  const Learn = root.Learn = root.Learn || {};

  function h(tag, attrs, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === 'text') el.textContent = v;
      else if (k === 'class') el.className = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else if (k === 'html') throw new Error('no raw html');
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (const c of children.flat(Infinity)) {
      if (c == null || c === false) continue;
      el.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return el;
  }

  class ApiError extends Error {
    constructor(message, status, kind) { super(message); this.status = status; this.kind = kind; }
  }

  async function call(path, {method = 'GET', body, timeout = 15000} = {}) {
    const guard = new AbortController(), timer = setTimeout(() => guard.abort(), timeout);
    let response;
    try {
      response = await fetch(path, {method, signal: guard.signal, cache: 'no-store',
        headers: body ? {'content-type': 'application/json'} : undefined, body: body ? JSON.stringify(body) : undefined});
    } catch (e) {
      throw new ApiError(guard.signal.aborted
        ? 'Le serveur DÉCLIC met trop de temps à répondre. Vérifiez qu’il tourne toujours, puis réessayez.'
        : 'Le serveur DÉCLIC ne répond pas. Relancez « Lancer DECLIC », puis réessayez : vos résultats déjà enregistrés sont conservés.', 0, 'network');
    } finally { clearTimeout(timer); }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      let detail = data && data.detail;
      if (Array.isArray(detail)) detail = 'Requête refusée : ' + detail.map(d => d.msg).join(' ; ');
      throw new ApiError(detail || `Erreur ${response.status} du serveur.`, response.status, response.status >= 500 ? 'server' : 'request');
    }
    return data;
  }

  const api = {
    catalog: () => call('/api/learn/catalog'),
    learners: () => call('/api/learn/learners'),
    learner: id => call(`/api/learn/learners/${encodeURIComponent(id)}`),
    createLearner: name => call('/api/learn/learners', {method: 'POST', body: {name, instrument: 'aucun'}}),
    startSession: (id, body) => call(`/api/learn/learners/${encodeURIComponent(id)}/sessions`, {method: 'POST', body}),
    session: sid => call(`/api/learn/sessions/${encodeURIComponent(sid)}`),
    next: sid => call(`/api/learn/sessions/${encodeURIComponent(sid)}/next`, {method: 'POST'}),
    answer: (iid, body) => call(`/api/learn/items/${encodeURIComponent(iid)}/answer`, {method: 'POST', body}),
    finish: sid => call(`/api/learn/sessions/${encodeURIComponent(sid)}/finish`, {method: 'POST'}),
    summary: sid => call(`/api/learn/sessions/${encodeURIComponent(sid)}/summary`),
    progress: id => call(`/api/learn/learners/${encodeURIComponent(id)}/progress`),
    exportUrl: id => `/api/learn/learners/${encodeURIComponent(id)}/export`,
  };

  const KEY = 'declic-learner';
  const profile = {
    get() { try { return localStorage.getItem(KEY); } catch (e) { return null; } },
    set(id) { try { localStorage.setItem(KEY, id); } catch (e) { /* private mode: the list on the server still works */ } },
    clear() { try { localStorage.removeItem(KEY); } catch (e) { /* ignore */ } },
    // The remembered id if the server still knows it, else the only profile on this computer, else null.
    async resolve() {
      const remembered = profile.get();
      const list = (await api.learners()).learners;
      if (remembered && list.some(l => l.id === remembered)) return {id: remembered, list};
      if (list.length === 1) { profile.set(list[0].id); return {id: list[0].id, list}; }
      return {id: null, list};
    },
  };

  const num = (v, d = 1) => v == null ? '—' : Number(v).toLocaleString('fr-FR', {maximumFractionDigits: d});
  const pct = v => v == null ? '—' : `${Math.round(v * 100)} %`;
  function ago(iso) {
    if (!iso) return 'jamais';
    const days = (Date.now() - new Date(iso).getTime()) / 86400000;
    if (days < 1 / 24) return 'il y a quelques minutes';
    if (days < 1) return `il y a ${Math.round(days * 24)} h`;
    if (days < 2) return 'hier';
    return `il y a ${Math.floor(days)} jours`;
  }
  const date = iso => iso ? new Date(iso).toLocaleDateString('fr-FR', {day: 'numeric', month: 'long', year: 'numeric'}) : '—';
  const dateTime = iso => iso ? new Date(iso).toLocaleString('fr-FR', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}) : '—';
  const KIND = {evaluation: 'Évaluation initiale', seance: 'Séance', ciblee: 'Séance ciblée'};
  const STATUS = {active: 'en cours', terminee: 'terminée', interrompue: 'interrompue'};

  function problem(container, error, retry) {
    container.replaceChildren(h('div', {class: 'problem', role: 'alert'},
      h('h2', {text: error.kind === 'network' ? 'DÉCLIC ne répond pas' : 'Action impossible'}),
      h('p', {text: error.message}),
      retry ? h('div', {class: 'actions'}, h('button', {type: 'button', class: 'btn btn-primary', onclick: retry, text: 'Réessayer'})) : null));
  }

  Learn.h = h; Learn.api = api; Learn.profile = profile; Learn.ApiError = ApiError;
  Learn.fmt = {pct, num, ago, date, dateTime, KIND, STATUS};
  Learn.problem = problem;
  Learn.booted = () => { root.DECLIC_BOOTED = true; };
})(window);
