'use strict';
// Accueil : l'état réel du serveur (/api/readiness) et, si un profil existe, l'action qui le concerne.
(function () {
  window.DECLIC_BOOTED = true;
  const out = document.getElementById('system');
  const say = (text, kind) => { out.textContent = text; out.dataset.state = kind; };

  async function readiness() {
    const guard = new AbortController(), timer = setTimeout(() => guard.abort(), 8000);
    try {
      const response = await fetch('/api/readiness', {signal: guard.signal, cache: 'no-store'});
      const data = await response.json().catch(() => null);
      if (!data) return say('Le serveur DÉCLIC répond mal. Relancez « Lancer DECLIC », puis rechargez cette page.', 'down');
      const ready = data.sources && Object.values(data.sources).some(s => s.ready);
      say(ready ? 'DÉCLIC est prêt : séances, parcours et laboratoire disponibles.'
        : 'DÉCLIC est prêt pour les séances. Le rejeu des réseaux O08 du laboratoire attend ses données de recherche.', ready ? 'ok' : 'warn');
    } catch (e) {
      say('Le serveur DÉCLIC ne répond pas. Lancez « Lancer DECLIC », puis rechargez cette page.', 'down');
    } finally { clearTimeout(timer); }
  }

  async function me() {
    const L = window.Learn; if (!L) return;
    try {
      const {id} = await L.profile.resolve(); if (!id) return;
      const learner = await L.api.learner(id);
      const cta = document.getElementById('cta');
      const label = learner.active_session ? `Reprendre ma séance (${learner.active_session.progress.answered} / ${learner.active_session.progress.total})` : 'Commencer une séance';
      cta.firstChild.textContent = label + ' ';
      document.getElementById('me').textContent = `Bonjour ${learner.name} · dernière activité ${L.fmt.ago(learner.last_activity)}.`;
    } catch (e) { /* the readiness line already says if the server is down */ }
  }
  readiness(); me();
})();
