'use strict';
(async () => {
  const section = document.getElementById('models');
  const loading = document.getElementById('loading');
  const add = (parent, tag, text) => {
    const el = document.createElement(tag); el.textContent = text; parent.append(el); return el;
  };
  try {
    const response = await fetch('/api/v5/musical/models');
    if (!response.ok) throw new Error('API indisponible');
    const data = await response.json();
    loading.remove();
    if (!data.models.length) add(section, 'p', 'Aucun modèle n’a encore passé les vérifications d’importation.');
    for (const model of data.models) {
      const card = document.createElement('article'); card.className = 'panel';
      add(card, 'h3', `${model.source.toUpperCase()} · ${model.instrument === 'voice' ? 'chant' : model.instrument === 'ukulele' ? 'ukulélé' : 'clavier'}`);
      add(card, 'p', 'Évalué sur des apprenants séparés de ceux utilisés pour apprendre.');
      if (model.source === 'singpad') {
        add(card, 'p', `ROC-AUC : ${model.test.roc_auc.toFixed(3)} · Brier : ${model.test.brier.toFixed(3)}.`);
        add(card, 'p', 'La première mesure indique la capacité à distinguer les réussites des erreurs. La seconde mesure l’écart des probabilités aux résultats : plus elle est petite, mieux c’est.');
      } else {
        add(card, 'p', `Écart moyen au score observé : ${(100 * model.test.mae).toFixed(1)} points sur 100.`);
      }
      add(card, 'p', model.citation);
      add(card, 'p', 'Utilisation limitée à cette cible et à cet instrument.');
      section.append(card);
    }
  } catch (error) {
    loading.textContent = 'Les résultats sont indisponibles. Relancez le serveur DÉCLIC puis actualisez cette page.';
  } finally { section.setAttribute('aria-busy', 'false'); }
})();
