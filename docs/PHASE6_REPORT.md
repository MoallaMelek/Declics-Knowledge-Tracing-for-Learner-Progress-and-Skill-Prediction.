# DÉCLIC - rapport de Phase 6

Date : 15 octobre 2026, heure de Tunis. Axe O08 / Axe 7 seulement.
Branche dédiée : phase6/scientific-validation. Aucun merge dans main.

## Synthèse vérifiée

Le défaut de chronologie SingPAD est corrigé. Les anciens modèles et scores restent archivés
mais sont invalides pour démontrer une prévision du futur. Le jeu reconstruit présente zéro inversion
et zéro doublon de groupe sur 18 328 groupes temporels, pour 1 042 apprenants utilisables.
Les dates originales sont conservées dans les caches privés.

19 entraînements CPU ont été exécutés : AMME 3, Yousician 3, SingPAD 9 comparaisons principales
et 4 ablations. Trois entraînements SingPAD supplémentaires ont été exécutés dans Colab sur un
Tesla T4, avec PyTorch 2.11.0+cu130. Le code cloud est ba93a013003d6435b66c5f0b40dd4b1816eff924.
Les trois exports, leurs analyses et les écritures Drive ont été vérifiés après transfert. La session GPU
a été arrêtée. Les modèles ne dépendent pas d’un Colab permanent pour fonctionner dans DÉCLIC.

Le modèle primaire GPU est EnhancedGRU, choisi sur validation parmi les trois architectures
prédéfinies. Son ROC-AUC test corrigé vaut 0,699104, sa PR-AUC 0,863367, sa log-loss 0,517529
et son Brier 0,170909. Ce test représente 62 152 cibles concept-groupe et 148 076 notes, pas autant
d’apprenants. Le changement de chronologie modifie les premières unités non scorées et certains
dénominateurs ; les anciens chiffres invalides ne sont pas une comparaison scientifique fiable.

## Statut des sept jalons

| Jalon | Statut | Preuve ou limite |
|---|---|---|
| 1. Réparation scientifique | Terminé | Parsing strict, regroupement canonique, audit zéro inversion, versions et refus des anciens modèles. |
| 2. Réentraînement réel | Terminé | DKT-GRU, EnhancedGRU et attention exécutés sur GPU et sur trois découpages CPU. |
| 3. Robustesse | Partiellement terminé | Trois graines, cinq contrôles, bootstrap par apprenant, calibration, slices et quatre ablations ; études avancées restantes ci-dessous. |
| 4. Compétences et fragilités | Partiellement terminé | Descriptifs par concept source et règle de difficultés récurrentes ; pas de maîtrise cognitive ou de taxonomie piano validée. |
| 5. Produit | Terminé dans le périmètre benchmark | Démonstration réelle reproductible, mode recherche, prévisions explicites, résultats masqués puis révélés. |
| 6. Vérification | Terminé pour les changements livrés après les contrôles de livraison | Suite automatisée complète, essais HTTP sur les vrais exemples, revue visuelle et CI ; cela ne vaut pas validation pédagogique. |
| 7. Livraison académique | Terminé | Dossier français, résultats, reproductibilité, questions de soutenance, oral et présentation. |

## Résultats comparatifs principaux

Les chiffres suivants sont les moyennes des trois découpages CPU prédéfinis. Le meilleur contrôle
historique est choisi sur la validation de chaque découpage. Le modèle primaire GPU reste séparé.

| Base / métrique | Réseau moyen | Écart-type entre découpages | Contrôle historique moyen |
|---|---|---|---|
| AMME / MAE | 0,184789 | 0,012268 | 0,182997 |
| Yousician / MAE | 0,091499 | 0,003268 | 0,089837 |
| SingPAD / log-loss | 0,517889 | 0,005053 | 0,540504 |

Sur SingPAD, les modèles choisis sur validation battent le contrôle historique dans les trois tests.
Le modèle choisi n’est pas toujours le plus complexe : EnhancedGRU pour les graines 42 et 17,
DKT-GRU pour 83. Les intervalles de perte et d’écart apparié utilisent 1 000 tirages d’apprenants.
Les écarts-types sont descriptifs : les découpages peuvent partager des apprenants. Les intervalles
ne couvrent pas toutes les sources d’incertitude et ne donnent pas une confiance individuelle.

Sur Yousician, la fréquence historique a une erreur légèrement plus basse dans les trois tests.
Le gain d’environ 17 % contre une moyenne constante de la Phase 5 ne démontre donc pas une
supériorité sur des contrôles plus forts. La tâche du prochain jour actif reste conservée ; on ne
la transforme pas en prévision d’un exercice précis ou d’un autre instrument.

AMME reste recherche seulement. Le premier découpage n’a que 25 cibles de validation et 23
de test. Les répétitions utilisent les mêmes personnes dans d’autres partitions ; elles n’ajoutent
pas de nouveaux élèves réels. Aucun effectif n’a été gonflé par duplication ou génération artificielle.

## Ablations et enseignements

Quatre conditions ont été entraînées à la graine 42 : retirer les cumuls, retirer les résultats récents,
retirer les identités d’exercice de l’attention, réduire la fenêtre GRU de 64 à 16. Les autres réglages
et le découpage sont conservés. Les résultats détaillés figurent dans PHASE6_RESULTS.md.

Retirer les cumuls donne une log-loss test de 0,516194 ; retirer les résultats récents 0,517898 ;
l’attention sans items 0,517026 ; la fenêtre courte 0,518768. Le GRU complet vaut 0,517463
sur ce découpage CPU. Ces résultats ne prouvent pas que chaque ajout améliore le modèle.
Les ablations sont restées des contrôles séparés ; elles n’ont pas été promues en choisissant sur test.
Elles n’ont qu’une graine, sans preuve de causalité ou de bénéfice pédagogique.

## Yousician : audit des groupes exclus

Après retrait des doublons et des lignes de pratique, 101 368 groupes à compteurs cohérents sont
retenus et 23 955 groupes contradictoires exclus, soit environ 19,1 % des groupes concernés.
Le taux varie avec la difficulté enregistrée : environ 7,0 % pour la catégorie 0 et 21,5 % pour la
catégorie 3. Cette différence signale un risque de sélection ; elle ne permet pas de reconstituer
les labels manquants. Le diagnostic par difficulté et ancienneté est publié en JSON agrégé.

Aucun identifiant fiable de tentative n’a été inventé. La représentation par jour garde le comptage
unique des compteurs globaux répétés entre parties. Les effets d’une difficulté passée ou d’un
intervalle passé entre jours ne sont pas entraînés dans cette livraison. Le jour futur et sa difficulté
restent des informations indisponibles à la prévision.

## Produit et architecture livrés

L’API v5 définit la cible, l’horizon, l’échelle, l’instrument, la version et l’historique utilisé. Un modèle
non actif ne peut pas être demandé directement. Les versions SingPAD v1 sont toujours rejetées.
Le cache d’inférence vérifie les empreintes des poids, du rapport et de l’analyse. Les imports gardent
weights_only=True, les contrôles de chemins ZIP, tailles, configurations, valeurs finies et provenance.
Le nouveau modèle SingPAD doit aussi améliorer le meilleur contrôle de validation avant promotion.

La démonstration affiche un vrai apprenant de test anonymisé, sélectionné par une règle fixe et
non par la qualité visuelle de sa prévision. Les archives, notes brutes et identifiants restent privés
dans runtime ou Drive. Le futur n’entre pas dans la requête ; un bouton le révèle après le calcul.
Le graphe historique ne mélange pas une moyenne globale avec des probabilités de concepts.
Les états « non évalué » et « preuve insuffisante » sont visibles et ne sont pas maquillés en réussite.

Les difficultés récurrentes utilisent une règle descriptive explicite et testée sur plusieurs groupes,
pas un diagnostic ou une inférence causale tirée de poids neuronaux. Une suggestion reprend un
concept déjà évalué ; son efficacité reste à tester. Le carnet piano et l’API v4 gardent leur abstention.

## Vérifications et reproductibilité

La suite complète locale après le renforcement de provenance comptait 278 tests réussis. Un test
supplémentaire de confidentialité et de séparation du résultat révélé a ensuite passé : 279 cas au
total, regroupés dans la CI de livraison référencée sur la couverture du PDF final. Les tests couvrent
les dates réelles non complétées de zéros, les transitions calendaires, les égalités et les formats
invalides, les changements de futur, l’alignement des poids par note, les fenêtres, les splits, les
contrôles causaux, les intervalles par apprenant et les chemins de checkpoint.

Une sauvegarde corrompue récente ne fait plus disparaître le dernier backup intact lors de la
sauvegarde suivante. La reprise exacte après interruption au milieu d’une époque est testée sur
CPU. Sur GPU, la reprise des entraînements terminés à l’époque 12 a été exécutée pour l’analyse ;
une coupure volontaire au milieu de l’apprentissage GPU n’est pas revendiquée.

Une limite de provenance des premiers rapports a été identifiée : certains enregistrent le HEAD
au moment de l’écriture, alors que les fonctions ont été chargées auparavant. La révision de lancement
est explicitée dans execution-provenance.json ; les nouveaux runs enregistrent les empreintes des
sources dès leur chargement et refusent une reprise avec un code différent. Les nouveaux notebooks
isolent leur dossier Drive par empreinte de code et figent les versions principales observées du GPU.
La nouvelle forme du notebook avec contraintes et dossier par empreinte est compilée et testée ;
elle n’est pas présentée comme l’interface exacte de l’exécution GPU historique.

Les dossiers Git sans rapport avec DÉCLIC sont conservés. Les changements sont livrés sur une
branche dédiée avec commits et CI, sans fusion dans main. Les sorties publiques ne contiennent
pas de listes d’identifiants d’apprenants ni de caches de données. Les journaux d’essai HTTP ne
publient que des contrôles agrégés de réussite de l’intégration.

## Ce qui reste à faire

Les études de robustesse aux observations manquantes et aux intervalles irréguliers, les ablations
isolant l’ordre temporel ou les embeddings de concept, les contrôles appris classiques, les garanties
individuelles d’incertitude et la calibration ajustée sur validation restent non exécutés. Les tranches
descriptives ne remplacent pas ces expériences. Aucun scheduler supplémentaire n’a été ajouté :
un taux fixe et l’arrêt précoce prédéfinis évitent une nouvelle recherche d’hyperparamètres après test.

Les priorités sont de confirmer les ablations sur plusieurs graines, d’étudier les exclusions Yousician,
de définir avec l’enseignant les compétences réellement observables au piano et de collecter des
résultats objectifs prospectifs. La mesure d’un bénéfice pédagogique demande une étude distincte.
Une authentification, une politique d’accès et un suivi de dérive seraient nécessaires avant un vrai
service déployé ; le serveur livré est une démonstration locale, pas une plateforme certifiée.

## Documents complémentaires

- PHASE6_RESULTS.md : tableaux par découpage et ablations effectivement terminées.
- PHASE6_SCIENCE_FR.md : formulation, méthodes, limites, questions difficiles et oral.
- PHASE6_REPRODUCTION.md : lancer, reprendre, importer, reconstruire les exemples et tester.
- artifacts/phase6/cloud.json : résultats GPU et modèle choisi sur validation.
- artifacts/phase6/results-summary.json : données agrégées exposées par le mode recherche.
- artifacts/phase6/yousician-selection-audit.json : audit agrégé des exclusions.
- artifacts/phase6/e2e-verification.json : vérification HTTP sur les vrais exemples de test.
