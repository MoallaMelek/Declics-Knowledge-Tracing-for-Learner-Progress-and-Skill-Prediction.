'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const add = (parent,tag,text) => { const node=document.createElement(tag);node.textContent=text;parent.append(node);return node; };
  const pct = value => `${(100*value).toFixed(1)} %`;
  let revealed = {};
  let generation = 0;
  const plot = history => {
    const ns='http://www.w3.org/2000/svg'; const svg=document.createElementNS(ns,'svg');
    svg.setAttribute('viewBox','0 0 700 260');svg.setAttribute('role','img');svg.setAttribute('aria-label','Scores observés dans les groupes précédents, entre zéro et cent.');
    const node = (tag,attrs,text) => {const el=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);if(text)el.textContent=text;svg.append(el);return el;};
    for(const score of [0,.5,1]){const y=220-180*score;node('line',{x1:55,y1:y,x2:670,y2:y,stroke:'#dce6df'});node('text',{x:10,y:y+4,fill:'#59666b'},String(score*100));}
    const points=history.map((r,i)=>[55+615*i/Math.max(history.length-1,1),220-180*r.score]);
    node('polyline',{points:points.map(p=>p.join(',')).join(' '),fill:'none',stroke:'#26745f','stroke-width':3});
    points.forEach(([x,y],i)=>{node('circle',{cx:x,cy:y,r:5,fill:'#26745f'});node('text',{x,y:245,'text-anchor':'middle',fill:'#59666b'},`G${i+1}`);});
    $('plot').replaceChildren(svg);
  };
  async function load(){
    const current=++generation; const source=$('source').value;
    for(const id of ['history','forecast','skills','observed'])$(id).hidden=true;
    $('status').textContent='Chargement du parcours réel…';
    try{
      const response=await fetch(`/api/v5/musical/demo?source=${encodeURIComponent(source)}`);
      if(!response.ok)throw new Error('Cette démonstration réelle est indisponible. Elle doit être reconstruite avec les données locales et un modèle actif.');
      const data=await response.json();if(current!==generation)return;
      const f=data.forecast;if(f.status!=='source_benchmark_only')throw new Error('Le modèle s’abstient pour ce parcours. Consultez les résultats de recherche.');
      $('status').textContent=`${data.provenance.anonymous_label} · historique réel de test · aucun résultat futur donné au réseau.`;
      $('history-caption').textContent=source==='singpad'?'Chaque point est la fraction de notes réussies dans un groupe temporel antérieur, tous concepts confondus. Les probabilités ci-dessous concernent des concepts précis.':'Chaque point est le score d’un jour de jeu évalué. Deux jours actifs ne sont pas forcément consécutifs.';
      plot(data.history);
      $('definition').textContent=source==='singpad'?`Au prochain enregistrement connu, exercice ${f.definition.exercise}, probabilité de réussite d’une note pour chaque concept de la source.`:'Au prochain jour actif : score global prévu, entre 0 et 100. Le jour de retour et les exercices futurs ne sont pas prévus.';
      $('predictions').replaceChildren();
      for(const [concept,value] of Object.entries(f.predictions)){
        const tile=add($('predictions'),'div','');tile.className='prediction-tile';
        add(tile,'span',source==='singpad'?`Concept source ${concept}`:'Score du prochain jour');add(tile,'strong',source==='singpad'?pct(value):`${(100*value).toFixed(1)} / 100`);
      }
      $('limits').textContent=`${f.prefix_groups} groupes antérieurs. Pas d’intervalle de confiance individuel validé. `+(source==='singpad'?'Une probabilité de réussite n’est pas une confiance dans le modèle.':'Un score prévu ne garantit pas la réussite d’un exercice.');
      $('evidence').replaceChildren();
      for(const e of f.evidence.source_concepts){
        const row=add($('evidence'),'div','');row.className='evidence-row';add(row,'h3',source==='singpad'?`Concept source ${e.concept}`:'Évolution du score global');add(row,'p',e.message);
        if(e.timestamp_groups){add(row,'p',`${e.timestamp_groups} groupes observés · ${source==='singpad'?`${e.observed_weight} notes évaluées`:'jours de jeu évalués'} · résultat récent : ${pct(e.recent_fraction)}.`);}
        if(e.practice_suggestion)add(row,'p',e.practice_suggestion);
      }
      revealed=data.observed_target; $('observed').replaceChildren();
      for(const id of ['history','forecast','skills'])$(id).hidden=false;
    }catch(error){if(current===generation)$('status').textContent=error.message;}
  }
  $('source').addEventListener('change',load);
  $('reveal').addEventListener('click',()=>{ $('observed').replaceChildren();add($('observed'),'h3','Résultats réels, révélés après la prévision');for(const [concept,value]of Object.entries(revealed))add($('observed'),'p',`${$('source').value==='singpad'?`Concept ${concept}`:'Score observé'} : ${pct(value)}.`);$('observed').hidden=false; });
  load();
})();
