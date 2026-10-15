# Phase 6 - résultats réellement exécutés

Les expériences locales sont CPU. Les trois répétitions changent à la fois les partitions et la graine.
Les apprenants peuvent se retrouver dans plusieurs répétitions : les écarts-types sont descriptifs,
pas une preuve de trois populations indépendantes. Les intervalles bootstrap rééchantillonnent
les apprenants entiers, conditionnellement au modèle et au découpage. Aucun intervalle individuel.

| Base | Graine | Modèle choisi sur validation | Test réseau | Contrôle choisi sur validation | Test contrôle |
|---|---:|---|---:|---|---:|
| amme | 42 | enhanced_gru | 0.185657 | frequency | 0.169944 |
| amme | 17 | enhanced_gru | 0.172111 | rolling3 | 0.195523 |
| amme | 83 | enhanced_gru | 0.196600 | frequency | 0.183524 |
| yousician | 42 | enhanced_gru | 0.090544 | frequency | 0.090284 |
| yousician | 17 | enhanced_gru | 0.088815 | frequency | 0.085350 |
| yousician | 83 | enhanced_gru | 0.095138 | frequency | 0.093877 |
| singpad | 42 | enhanced_gru | 0.517463 | frequency | 0.540880 |
| singpad | 17 | enhanced_gru | 0.523142 | frequency | 0.545671 |
| singpad | 83 | dkt | 0.513062 | frequency | 0.534962 |

## Moyennes des découpages exécutés

| Base | Moyenne | Écart-type | Contrôle moyen | Répétitions |
|---|---:|---:|---:|---:|
| amme | 0.184789 | 0.012268 | 0.182997 | 3 |
| yousician | 0.091499 | 0.003268 | 0.089837 | 3 |
| singpad | 0.517889 | 0.005053 | 0.540504 | 3 |

## Ablations exécutées

| Condition | Validation log-loss | Test log-loss |
|---|---:|---:|
| enhanced_gru-full-c16 | 0.510185 | 0.518768 |
| enhanced_gru-no_counts-c64 | 0.507265 | 0.516194 |
| enhanced_gru-no_recent-c64 | 0.509581 | 0.517898 |
| item_attention-no_items-c64 | 0.509001 | 0.517026 |

Une architecture comparée à une autre n’est pas une ablation isolée. Les ablations retirent
les cumuls, les résultats récents, les embeddings d’exercices, ou réduisent la fenêtre. Le mélange
aléatoire des parcours n’est pas utilisé : il pourrait replacer du futur dans le passé.
Un effet d’ablation reste associatif ; les graines supplémentaires ne sont pas des répétitions de chaque ablation.

AMME reste recherche seulement. Sur Yousician, les références historiques peuvent dépasser le réseau :
le gain contre la constante ne prouve pas une valeur ajoutée par rapport aux contrôles plus forts.
Les résultats détaillés et les dénominateurs sont dans chaque analysis.json.

Limites restantes : pas de bénéfice pédagogique démontré, pas de taxonomie piano validée,
pas d’intervalle pour chaque prévision, pas de contrôle prospectif terrain.
La cible Yousician reste le prochain jour actif. Les concepts SingPAD restent ceux de la source.
