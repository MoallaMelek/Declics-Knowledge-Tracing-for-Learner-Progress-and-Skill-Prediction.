'use strict';
// Accueil : une seule information vivante, l'état réel de la démonstration (/api/readiness). Rien n'est simulé.
(function () {
  const out = document.getElementById('system');
  const NAMES = {singpad: 'chant (SingPAD)', yousician: 'ukulélé (Yousician)'};
  function say(text, kind) { out.textContent = text; out.dataset.state = kind; }

  async function check() {
    const guard = new AbortController(), timer = setTimeout(() => guard.abort(), 8000);
    try {
      const response = await fetch('/api/readiness', {signal: guard.signal, cache: 'no-store'});
      const data = await response.json().catch(() => null);
      if (!data || !data.sources) { say('Le serveur répond, mais sans l’état de démonstration attendu. Le parcours affichera le diagnostic.', 'warn'); return; }
      const ready = Object.entries(data.sources).filter(([, s]) => s.ready).map(([k]) => NAMES[k] || k);
      const missing = Object.entries(data.sources).filter(([, s]) => !s.ready).map(([k]) => NAMES[k] || k);
      const mode = data.data_mode === 'synthetic_fixture'
        ? ' Données synthétiques d’intégration : elles vérifient la mécanique, pas l’apprentissage réel.'
        : data.data_mode === 'private_research_data' ? ' Parcours réels du jeu de test.' : '';
      if (ready.length && !missing.length) say(`Démonstration prête : ${ready.join(' et ')}.${mode}`, 'ok');
      else if (ready.length) say(`Prête pour ${ready.join(' et ')} ; indisponible pour ${missing.join(' et ')}.${mode}`, 'warn');
      else say('Le serveur fonctionne, mais aucun modèle ou parcours n’est prêt. Le Laboratoire détaille le diagnostic.', 'warn');
    } catch (e) {
      say('Le serveur DÉCLIC ne répond pas. Lancez l’application avec Launch.ps1, puis rechargez cette page.', 'down');
    } finally { clearTimeout(timer); }
  }
  check();
})();
