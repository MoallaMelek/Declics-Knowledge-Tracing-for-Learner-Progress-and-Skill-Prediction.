# Phase 7 — protocole fixé avant exécution

Référence vérifiée : 40351233d5652be9c6c8e1af5f6ea79d0cee8361, branche
phase6/scientific-validation ; SHA distant identique ; CI 38747446308 réussie.
Le PDF Phase 6 existe (109 924 octets). Les résultats historiques restent immuables.
Les fichiers AI_TEAM.md/AGENTS.md et leurs modèles ~/.Codex/templates sont absents :
aucun protocole de collaboration manquant n'est inventé.

## Expériences exploratoires préspécifiées

- Découpages par apprenant identiques à Phase 6, graines 42, 17, 83.
- SingPAD : GRU, agrégats sans ordre, GRU limité aux trois dernières observations,
  attention avec/sans embeddings de concepts, GRU avec intervalles passés.
- AMME/Yousician : GRU, agrégats sans ordre, GRU avec intervalles passés.
- 8 époques maximum, patience 3, AdamW 0,001, hidden 48, batch 16, contexte 64.
  Budget distinct de Phase 6 : comparer les variantes Phase 7 entre elles.
- Aucun mélange de groupes futurs. Les fenêtres récentes gardent les cibles originales.
- Régression logistique régularisée SingPAD et Ridge scores continus ; paramètres
  choisis sur validation seulement. Contrôles de recherche, aucune activation produit.
- Calibration température ajustée sur validation ; ECE 10 intervalles disjoints fixes,
  décomposition de Brier binned avec résidu explicite (pas d'identité exacte non binned).
- Stress tests des modèles gelés : 30 % de groupes historiques supprimés avec graine
  fixe, deux groupes récents absents, concepts cibles absents de l'historique.
  Les labels cibles et leur pondération restent identiques. Inconnus : abstention produit.
- Publier tous les résultats, y compris négatifs. Aucun nouveau modèle promu selon test.
- Ces tests réutilisent les splits déjà inspectés en Phase 6 : analyse exploratoire,
  aucune prétention de nouvel échantillon confirmatoire indépendant.

## Livraison fonctionnelle

États descriptifs explicitement paramétrés, couches observation/prévision/interprétation
séparées ; catalogue tiré uniquement des exercices historiquement disponibles ; mappings
piano en attente de revue. Collecte prospective locale opt-in, pseudonymes, contrôle
d'accès par jeton configuré, prévisions horodatées avant résultats, export/suppression/rétention
et audit sans contenu d'observations. Aucun résultat terrain fabriqué.

Conserver v3/v4/v5, les poids actifs, l'abstention piano et les notebooks Phase 6.
Rapport final : statuts mesuré/livré/en attente, tests et CI effectivement observés.
