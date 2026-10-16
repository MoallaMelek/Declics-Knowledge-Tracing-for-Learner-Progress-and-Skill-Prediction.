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
  try {
    const response=await fetch('/api/v5/musical/research');
    if(!response.ok)throw new Error('Résultats non publiés');
    const report=await response.json(); document.getElementById('robustness-status').remove();
    const parent=document.getElementById('robustness');
    for(const [source,data]of Object.entries(report.sources)){
      add(parent,'h3',source.toUpperCase());
      const loss=data.metric==='mae'?`${(100*data.mean).toFixed(1)} points sur 100`:`log-loss ${data.mean.toFixed(3)}`;
      const control=data.metric==='mae'?`${(100*data.mean_control).toFixed(1)} points`:`${data.mean_control.toFixed(3)}`;
      add(parent,'p',`${data.completed_seeds.length} découpages exécutés. Réseau : ${loss}. Référence historique choisie sur validation : ${control}.`);
      add(parent,'p',data.mean<data.mean_control?'Le réseau a une erreur moyenne plus faible dans ces expériences. La variabilité et les limites restent à examiner.':'La référence historique est au moins aussi bonne en moyenne. La complexité du réseau ne prouve pas une meilleure prédiction.');
      const details=add(parent,'details','');add(details,'summary','Configuration, variabilité et calibration');
      add(details,'p',`Graines : ${data.completed_seeds.join(', ')}. Écart-type entre découpages : ${data.sample_sd===null?'non disponible':data.sample_sd.toFixed(4)}. Les découpages peuvent partager des apprenants.`);
      add(details,'p','Les intervalles à 95 % rééchantillonnent des apprenants entiers. Ils décrivent une métrique du benchmark, pas la confiance dans une prévision individuelle.');
      if(data.seed42_calibration){
        add(details,'p','Calibration du test CPU, graine 42 : les points proches de la diagonale ont une fréquence observée proche de leur probabilité moyenne.');
        const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
        svg.setAttribute('viewBox','0 0 360 320');svg.setAttribute('role','img');svg.setAttribute('aria-label','Diagramme de fiabilité : probabilité prévue en abscisse, réussite observée en ordonnée.');svg.style.maxWidth='420px';svg.style.width='100%';
        const mark=(tag,attrs,text)=>{const el=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))el.setAttribute(k,v);if(text)el.textContent=text;svg.append(el);};
        mark('line',{x1:40,y1:270,x2:310,y2:0,stroke:'#98aaa2','stroke-dasharray':'5 5'});
        mark('line',{x1:40,y1:0,x2:40,y2:270,stroke:'#59666b'});mark('line',{x1:40,y1:270,x2:310,y2:270,stroke:'#59666b'});
        mark('text',{x:110,y:307,fill:'#59666b','font-size':13},'Probabilité prévue');
        for(const bin of data.seed42_calibration)mark('circle',{cx:40+270*bin.prediction,cy:270-270*bin.observed,r:4.5,fill:'#26745f'});
        for(const value of [0,.5,1]){mark('text',{x:40+270*value,y:288,fill:'#59666b','font-size':12},String(value));mark('text',{x:5,y:274-270*value,fill:'#59666b','font-size':12},String(value));}
        details.append(svg);
        const table=document.createElement('table');const head=document.createElement('tr');
        for(const text of ['Probabilité prévue','Réussite observée','Notes'])add(head,'th',text);table.append(head);
        for(const bin of data.seed42_calibration){const row=document.createElement('tr');for(const value of [`${(100*bin.prediction).toFixed(1)} %`,`${(100*bin.observed).toFixed(1)} %`,String(Math.round(bin.weight))])add(row,'td',value);table.append(row);}details.append(table);
      }
    }
    add(parent,'p','Aucune amélioration de l’apprentissage en situation réelle ni transfert au piano n’est démontré. Les détails scientifiques sont disponibles dans le dépôt.');
  } catch(error) { document.getElementById('robustness-status').textContent='Les expériences comparatives ne sont pas disponibles sur ce serveur.'; }
})();
