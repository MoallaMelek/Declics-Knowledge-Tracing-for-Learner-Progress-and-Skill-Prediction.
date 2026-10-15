# Extension exploratoire Yousician, définie avant exécution

Après le programme principal de 33 réseaux, tester neuf variables strictement historiques :
difficulté moyenne du jour précédent (0-10 normalisée), indicateur de difficulté absente,
diversité d'exercices, quantité de notes/accords évalués, diversité de séances du jour précédent,
quantité cumulée évaluée, diversité cumulée d'exercices, intervalle entre les deux derniers jours
observés et score moyen des trois derniers jours.

Même déduplication et exclusion des compteurs contradictoires. Vérifier chaque cible quotidienne
contre le prétraitement Phase 6, à tolérance 1e-12. Aucune durée de pratique ou difficulté future
inventée. Les compteurs évalués représentent un volume observé, pas une durée.

GRU 48 neurones, tête dense 48, 8 époques maximum, patience 3, graines 42/17/83, AdamW .001,
batch16, contexte64. Mêmes splits par apprenant. Comparateur à arbres boostés recevant exactement
les mêmes variables ; feuilles 7/15, 100 itérations, taux .05, régularisation1, choix validation MAE.
Cette extension change la paramétrisation d'entrée : elle n'isole pas causalement un effet de feature.
Résultats séparés du programme principal ; aucune promotion produit automatique et aucune revendication
confirmatoire sur des splits déjà examinés. Mesurer les cas négatifs.
