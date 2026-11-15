# Phase 11 · Élèves virtuels : étude de simulation Elo vs GRU sur DÉCLIC

> **Étude de simulation.** Les élèves sont simulés. Un modèle entraîné sur eux peut apprendre les règles du simulateur au lieu de vraies habitudes d’apprentissage musical. Rien ici ne démontre qu’un modèle est meilleur avec de vrais élèves. Les chiffres détaillés sont dans [PHASE11_SIMULATION_RESULTS.md](PHASE11_SIMULATION_RESULTS.md), généré automatiquement depuis `artifacts/simulation/sim-2026-11/`.

## Résultat principal (étude de simulation)

Campagne A1 : 200 élèves simulés pendant 8 semaines, 48 263 réponses passées par les vraies routes DÉCLIC. Les 197 élèves qui ont répondu au moins une fois sont tous prévus par un GRU qui ne les a jamais vus (validation croisée en 5 plis). Les colonnes Brier et log-loss portent sur les **41 732 questions où les trois modèles prévoient** ; la couverture est la part des 48 263 questions que chaque modèle accepte de prévoir.

| Modèle | Brier | Log-loss | Élèves évalués | Couverture des prévisions |
|---|---|---|---|---|
| Elo (`declic-elo-v1`) | 0,1858 | 0,5454 | 197 | 86 % |
| GRU DÉCLIC (EnhancedGRU) | 0,1841 | 0,5388 | 197 | 100 % |
| Baseline naïve | 0,1913 | 0,5614 | 197 | 100 % |

Intervalles à 95 % (1 000 tirages d’élèves entiers) : Elo − GRU = 0,0017 [0,0007 ; 0,0029] en Brier, 0,0066 [0,0033 ; 0,0099] en log-loss. Pour repère, la vraie probabilité cachée obtient un Brier de 0,1225 : c’est le minimum atteignable en moyenne.

**En une phrase :** dans ce simulateur, le GRU fait un peu mieux qu’Elo dès qu’il est entraîné sur au moins 200 élèves. L’écart est petit, du même ordre que celui entre Elo et la méthode naïve. Elo fait mieux avec 50 élèves, après les longues pauses, sur l’écho au clavier, et sur une population plus bruyante quand le GRU n’y a pas été entraîné.

## 1. Architecture construite

```
configs/simulation-study.json          campagnes, graines, réglages du GRU (tout est figé ici)
axis7/sim_learners.py                  élèves virtuels : état caché, perception, apprentissage, oubli, fatigue, familles A et B
axis7/sim_campaign.py                  moteur temporel + exécution par les vraies routes DÉCLIC, base et horloge isolées
axis7/sim_models.py                    données stockées → encodeur O08 → EnhancedGRU ; comparaison Elo / GRU / naïf
axis7/sim_api.py                       API en lecture seule /api/sim (fichiers de l’étude uniquement)
scripts/run_simulation_campaigns.py    lance les campagnes (2 processus en parallèle)
scripts/run_simulation_study.py        inspection, entraînements, comparaisons, expériences, données d’interface
scripts/report_simulation.py           écrit PHASE11_SIMULATION_RESULTS.md depuis les fichiers de résultats
web/simulation.html, web/simulation/   interface « Élèves virtuels » (Laboratoire)
tests/test_simulation_learners.py      perception, apprentissage, oubli, fatigue, reproductibilité, isolation
tests/test_simulation_models.py        entrées = export O08, causalité, vérité cachée inaccessible, métriques, API
tests/browser/simulation_e2e.cjs       les cinq vues dans Chromium, chiffres comparés à l’API
```

### 1.1 Moteur d’élèves virtuels (`sim_learners.py`)

Chaque élève a un **état caché** que les modèles ne voient jamais : un bruit de perception par compétence (hauteur en cents, intervalles et accords en demi-tons, mémoire, reproduction, régularité du tapotement, placement rythmique, lecture, fonctions tonales), une vitesse d’apprentissage, une vitesse d’oubli, un taux d’inattention, une fatigue, une motivation, des habitudes (jours de pratique, pauses, abandon), un biais de réponse, une capacité de mémoire, un biais de tempo.

**Il ne reçoit jamais la bonne réponse.** Il lit seulement ce que le navigateur jouerait ou dessinerait (`served` : notes MIDI, fréquences, clics, portée), le perçoit avec son bruit, puis décide :

| Exercice | Perception | Décision | Erreurs qui en sortent |
|---|---|---|---|
| Hauteur (comparaison, seuil) | écart en cents + bruit | signe | se trompe surtout sur les petits écarts |
| Intervalles | taille + bruit (plus fort en descendant et en harmonique, plus faible pour l’octave, plus fort pour triton, sixte mineure, septième mineure) | option la plus proche | intervalles voisins |
| Accords | chaque note + bruit, renversements plus bruités | qualité dont le gabarit est le plus proche | majeur ↔ augmenté, mineur ↔ diminué |
| Mélodies pareilles/différentes | intervalles des deux mélodies + bruit (mémoire qui baisse avec la longueur, la transposition, l’atonalité) | contour différent, ou écart > critère | rate les petits changements qui gardent le contour |
| Écho au clavier | chaque intervalle + bruit, arrondi, ramené dans la gamme ; capacité de mémoire | notes jouées une à une | une note décalée, une note oubliée |
| Pulsation | asynchronie puis intervalles + bruit, biais de tempo, dérive | frappes | presse, ralentit, irrégulier, s’arrête trop tôt |
| Rythmes pareils/différents | attaques + bruit | écart max > critère | rate les petits déplacements |
| Reproduire un rythme | attaques + bruit, tempo personnel | frappes | valeurs courtes fusionnées ou doublées |
| Lecture | position + bruit (lignes supplémentaires plus dures), confusion de clé | nom de la note | voisine, ou une tierce (clé de fa lue en clé de sol) |
| Degrés, cadences | hauteur relative à la tonique + bruit | degré ou cadence la plus proche | degrés voisins, parfaite ↔ plagale |

Les réécoutes réduisent le bruit (moyenne de perceptions) quand l’élève hésite. L’inattention donne une réponse au hasard. La fatigue augmente le bruit et l’inattention au fil de la séance. La pratique réduit le bruit (variante A : exponentielle ; B : loi puissance), avec un léger transfert entre compétences voisines ; les pauses font oublier (A : exponentielle ; B : puissance).

La **vraie probabilité de réussite** de chaque question (l’oracle) est calculée avant la réponse, par 100 tirages du même processus de réponse sur une copie de l’état, notés avec les vraies règles de correction de DÉCLIC. Elle est écrite dans `hidden/`, jamais lue par un modèle.

### 1.2 Familles et paramètres

Variante A, six familles : débutant motivé, musicien expérimenté, bonne oreille / rythme faible, bon rythme / difficultés mélodiques, irrégulier avec longues pauses, en difficulté qui progresse lentement. Chaque élève tire tous ses paramètres autour de ceux de sa famille : aucun clone. Variante B : autres lois (puissance), bruit logistique, autres proportions, et une septième famille « progression atypique » (plateau puis décollage).

Provenance : le rapport musiciens / non-musiciens des seuils de hauteur s’inspire de Micheyl et al. (2006), l’ordre de difficulté des intervalles de Stambaugh et Nichols (2020), la mémoire du contour de Dowling (1978), la variabilité du tapotement de Repp (2005). **Toutes les valeurs numériques, les formes des courbes, l’oubli, le transfert, la fatigue et les habitudes sont des hypothèses DÉCLIC**, listées dans `sim_learners.PROVENANCE` et dans la vue Technique.

### 1.3 Moteur temporel et exécution réelle (`sim_campaign.py`)

Chaque élève vit jour après jour : pratique ou non selon sa régularité et sa motivation, pauses, abandons, retours. Chaque séance passe par **les routes de DÉCLIC** : création du profil, évaluation initiale de 30 questions, séances planifiées par le vrai planificateur, réponses corrigées par les vraies règles, bilan, Parcours et export O08 en fin de campagne. Les prévisions Elo et naïve sont celles que DÉCLIC enregistre **avant** chaque question.

Isolation, vérifiée par les tests :
- base : uniquement des fichiers `synthetic-*.sqlite` ; `runtime/learning.sqlite` est refusé, son empreinte est contrôlée avant et après ;
- horloge : `learning._now` lit une horloge simulée, seulement dans le processus de simulation, puis est restaurée ;
- questions : la graine des questions vient d’un générateur fixé (reproductible) au lieu de `SystemRandom` ;
- profils nommés `SYNTHÉTIQUE <identifiant>` ;
- transport : par défaut, appel direct des mêmes fonctions de route (10 fois plus rapide). Un test vérifie que le passage par HTTP (`axis7.server.app`) produit exactement les mêmes réponses, notes et prévisions.

### 1.4 GRU DÉCLIC (`sim_models.py`)

Réutilisation sans modification du pipeline O08 : `cloud_training.encode / windows / batch / model_for / forward / measure / split_learners / fit_items` et `models_v2.EnhancedGRU`. Ces fichiers ne sont pas modifiés, car leurs empreintes font partie de la provenance des modèles servis. Les entrées sont exactement l’export O08 de chaque élève : compétence, juste ou faux, exercice@niveau, dans l’ordre. Seule exception : l’exercice de seuil indique aussi l’ordre de grandeur de l’écart (en octaves de cents), information qu’Elo reçoit déjà par d(cents). Partition par élève 70/15/15, aucun élève dans deux groupes. Entraînement identique au pipeline O08 : AdamW 0,001, weight decay 0,001, lots de 16, gradient plafonné à 1, au plus 12 époques, arrêt après 4 sans progrès, meilleur modèle sur la log-loss de validation.

### 1.5 Comparaison

Les trois modèles prévoient **les mêmes questions, pour les mêmes élèves**, avec le seul passé. Elo s’abstient sous 5 réponses dans la compétence ; le GRU ne prévoit pas la toute première réponse d’un élève ; le naïf prévoit toujours. Les mesures principales portent sur les questions où les trois prévoient. Chaque modèle est aussi mesuré sur sa propre couverture. Intervalles à 95 % : 1 000 tirages d’élèves entiers. Mesure commune avec l’état caché : la probabilité de réussir la question ; on mesure l’écart de chaque modèle à la vraie probabilité, et s’il suit la vraie évolution de chaque élève dans chaque compétence.

## 2. Élèves et exercices réellement simulés

| Campagne | Rôle | Élèves | Réponses | Réussite | Abandons | Exports O08 acceptés |
|---|---|---|---|---|---|---|
| A1 | campagne principale (simulateur A, graine 1) | 200 | 48 263 | 70 % | 58 | 200 |
| A2, A3 | même simulateur, autres populations (graines 2 et 3) | 2 × 200 | 47 864 et 49 767 | 69 % et 70 % | 55 et 48 | 400 |
| B1 | deuxième simulateur (lois en puissance, bruit logistique, famille atypique) | 200 | 46 581 | 68 % | 43 | 200 |
| N1 | simulateur A, bruit et inattention × 1,5 | 200 | 43 472 | 57 % | 58 | 200 |
| L1 | cohorte de 1 000 élèves (taille, familles absentes) | 1 000 | 243 162 | 70 % | 263 | 1 000 |

Au total : **2 000 élèves simulés et 479 109 réponses**, toutes corrigées par DÉCLIC, sans aucune réponse refusée par l’API. Chaque campagne de 200 élèves prend 11 à 15 minutes sur un cœur de CPU ; L1 a pris 70 minutes. Détails semaine par semaine et par exercice : [PHASE11_SIMULATION_RESULTS.md](PHASE11_SIMULATION_RESULTS.md), section 1.

Ce que DÉCLIC a réellement proposé (A1) : surtout lecture (10 913 questions), mélodies (9 440), rythmes (9 152), pulsation, hauteur, écho. Les degrés (133) et les cadences (4) sont presque absents, car la règle de maîtrise (80 % et p < 0,05) fait avancer lentement : 4,7 niveaux maîtrisés en moyenne par élève, au plus 26 sur toute la campagne. Un élève a répondu à 251 questions (médiane ; de 20 à 550).

## 3. Courbes d’apprentissage des familles (A1)

Niveau caché moyen, sur l’échelle commune (0 = bruit de perception d’un débutant typique, 1 = celui d’un expert typique), de la semaine 1 à la semaine 8 :

| Famille | Élèves | S1 | S8 | Gain moyen | Écart-type du gain |
|---|---|---|---|---|---|
| Débutant motivé | 44 | 0,124 | 0,248 | 0,123 | 0,041 |
| Bonne oreille, rythme faible | 32 | 0,448 | 0,503 | 0,055 | 0,025 |
| Bon rythme, difficultés mélodiques | 32 | 0,316 | 0,370 | 0,053 | 0,026 |
| En difficulté, progresse lentement | 32 | −0,147 | −0,122 | 0,025 | 0,015 |
| Irrégulier, longues pauses | 32 | 0,345 | 0,356 | 0,011 | 0,010 |
| Musicien expérimenté | 28 | 0,825 | 0,840 | 0,015 | 0,007 |

- **Pas de clones :** 200 courbes hebdomadaires distinctes sur 200 élèves, et autant dans les autres campagnes (1 000 sur 1 000 dans L1). Gain individuel de −0,002 à 0,214.
- **Les familles se comportent comme prévu :** le débutant motivé progresse le plus. Les familles « oreille » et « rythme » progressent surtout sur leur point faible (voir le gain par compétence dans la vue Population). L’irrégulier oublie pendant ses pauses presque autant qu’il gagne. L’expert est déjà près de son plafond.
- **Les progrès sont modestes en huit semaines.** C’est un choix de paramètres (hypothèse DÉCLIC), pas une mesure. Les modèles doivent donc suivre de petites évolutions.
- **Famille atypique de B1 :** le décollage prévu après le plateau n’a pas eu lieu en huit semaines (gain moyen ≈ 0). L’expérience « progression inhabituelle » teste donc un plateau prolongé, pas un décollage.

## 4. Entraînement du GRU

- **Modèle :** EnhancedGRU du pipeline O08, 19 149 paramètres, mémoire de 48, contexte de 64 réponses, 9 compétences, 50 exercices@niveau.
- **Partition principale A1 :** 137 élèves pour l’entraînement, 30 pour la validation, 30 pour le test. Environ 8 secondes d’entraînement par modèle sur CPU.
- **Trois graines (42, 17, 83) :** Brier GRU sur le test de 0,1864, 0,1864 et 0,1879, contre 0,1879 pour Elo. Le résultat ne dépend pas d’une graine chanceuse, mais sur 30 élèves l’écart avec Elo n’est jamais démontré : tous les intervalles contiennent 0.
- **Le réglage O08 était suffisant :** 12 époques au plus ; la meilleure époque est souvent la dernière. Avec jusqu’à 40 époques, le Brier change de −0,0009, +0,0001 et +0,0001 selon la graine. Le GRU n’était donc pas pénalisé par un entraînement trop court.
- **36 modèles enregistrés** dans `artifacts/simulation/sim-2026-11/models/`. Chacun a sa configuration, sa courbe d’entraînement, l’empreinte SHA-256 de ses poids et l’empreinte des élèves de chaque groupe.
- **Entrées :** uniquement ce que DÉCLIC stocke. Deux tests le vérifient : `test_the_hidden_truth_never_reaches_the_model` (changer tout l’état caché ne change aucune prévision) et `test_gru_predictions_are_causal` (changer la suite ne change pas le passé).

## 5. Elo vs GRU vs méthode naïve

**Sur les mêmes questions, les deux modèles battent nettement la méthode naïve.** Le GRU bat Elo de peu :

| Évaluation | Élèves | Questions communes | Elo − GRU (Brier) | IC 95 % | Lecture |
|---|---|---|---|---|---|
| A1, test (graine 42) | 30 | 6 419 | 0,0015 | [−0,0021 ; 0,0047] | pas de différence démontrée |
| A1, validation croisée | 197 | 41 732 | 0,0017 | [0,0007 ; 0,0029] | GRU meilleur |
| A2, test | 30 | 5 547 | 0,0047 | [0,0027 ; 0,0068] | GRU meilleur |
| A3, test | 30 | 7 213 | 0,0026 | [0,0002 ; 0,0047] | GRU meilleur |

- **Fiabilité des probabilités :** le GRU est le mieux calibré (erreur de calibration 0,007, contre 0,021 pour Elo et 0,048 pour le naïf). Elo est trop pessimiste quand il annonce moins de 50 % : 8 % annoncés pour 27 % observés, 26 % pour 35 %. Cela vient de ses difficultés fixées a priori.
- **Retrouver la vérité cachée.** Mesure commune : la probabilité de réussir la question.
  - Écart quadratique à la vraie probabilité : 0,0621 pour le GRU, 0,0643 pour Elo, 0,0697 pour le naïf. La différence Elo − GRU vaut 0,0021 [0,0011 ; 0,0032].
  - Tendance individuelle (951 trajectoires élève × compétence) : le GRU suit la vraie évolution dans le bon sens dans 69 % des cas, Elo dans 63 %, le naïf dans 64 %. Corrélations avec la vraie évolution : 0,557, 0,489 et 0,286.
- **Abstention :** Elo refuse de prévoir 14 % des questions, celles où une compétence a moins de 5 réponses. Sur ces 6 334 questions, le GRU obtient un Brier de 0,1789 et le naïf 0,1960 ; l’écart vaut −0,0170 [−0,0198 ; −0,0142]. Ce n’est pas une erreur d’Elo : c’est sa règle d’abstention.
- **Début vs après plusieurs séances.** Le GRU est surtout meilleur au début : avant 50 réponses, Elo − GRU = 0,0051 [0,0019 ; 0,0085] entre 20 et 49 réponses. Entre 50 et 199 réponses, la différence n’est plus démontrée. Au-delà de 200, le GRU redevient un peu meilleur : 0,0024 [0,0002 ; 0,0046].

### Pourquoi Elo est-il si proche ?

- **Le simulateur a la même forme qu’Elo :** un niveau par compétence qui monte avec la pratique. Elo est un bon modèle de ce monde-là.
- **Une partie de l’erreur est inaccessible à tous les modèles.** Sur les mélodies et les rythmes « pareil / différent », la vraie probabilité dépend de ce qui est joué : une paire identique est presque toujours réussie, un petit changement presque toujours manqué. Aucun des trois modèles ne reçoit ce contenu. Leur écart à la vérité y reste énorme (0,11 à 0,15) et presque identique. C’est la principale raison pour laquelle tous les modèles restent loin du Brier minimal (0,1225).

## 6. Par compétence et par type d’élève (A1, validation croisée)

**Le GRU fait mieux** (intervalle entièrement au-dessus de zéro) sur :

| Exercice | Elo − GRU | IC 95 % | Pourquoi |
|---|---|---|---|
| Reproduire un rythme | 0,0552 | [0,0312 ; 0,0841] | Elo met la reproduction de rythme dans la même compétence que « rythmes pareils/différents », avec la même difficulté fixée par niveau. Il prévoit 0,63 là où les élèves réussissent à 0,83. Le GRU apprend une difficulté par exercice. |
| Accords | 0,0107 | [0,0049 ; 0,0160] | difficulté propre à l’exercice |
| Hauteur (seuil et comparaison) | 0,0052 et 0,0017 | les deux > 0 | |

Familles où le GRU est meilleur : débutant motivé (0,0042 [0,0025 ; 0,0059]) et musicien expérimenté (0,0030 [0,0014 ; 0,0046]). Pour les quatre autres familles, pas de différence démontrée.

**Elo fait mieux** (intervalle entièrement sous zéro) :

| Où | Elo − GRU | IC 95 % | Pourquoi |
|---|---|---|---|
| Écho au clavier (seul exercice de « reproduction ») | −0,0076 | [−0,0141 ; −0,0018] | Une compétence = un seul exercice : le niveau individuel d’Elo est exactement ce qu’il faut. Le GRU est un peu moins bon aux niveaux 1, 2 et 4. |
| Première question après 7 jours ou plus sans pratique | −0,0265 | [−0,0471 ; −0,0057] | Le format O08 ne contient pas la date : le GRU ne voit pas la pause. Il prévoit 0,58 là où les élèves réussissent à 0,45 (vraie probabilité 0,50). Elo, plus prudent, prévoit 0,52. Sur ces 125 questions, le naïf est le meilleur des trois. |

## 7. Expériences de robustesse

**Taille de la cohorte (L1).** Test fixe de 150 élèves, validation fixe de 100. Le GRU est entraîné sur 70 % d’une cohorte de 50, 200 ou 1 000 élèves, avec 3 graines.

| Cohorte | Élèves d’entraînement | Brier GRU (3 graines) | Brier Elo | Elo − GRU (graine 42) | IC 95 % |
|---|---|---|---|---|---|
| 50 | 35 | 0,1890 · 0,1890 · 0,1887 | 0,1858 | −0,0032 | [−0,0053 ; −0,0013] |
| 200 | 140 | 0,1838 · 0,1842 · 0,1836 | 0,1858 | 0,0020 | [0,0003 ; 0,0034] |
| 1 000 | 700 | 0,1816 · 0,1814 · 0,1814 | 0,1858 | 0,0042 | [0,0031 ; 0,0053] |

**Avec 50 élèves, Elo gagne,** pour les trois graines. Elo n’a rien à apprendre des autres élèves ; le GRU, si. À partir de 200 élèves, le GRU passe devant, et l’écart double avec 1 000 élèves. Le GRU a donc besoin d’une cohorte : c’est la condition principale de son utilité.

**Quantité d’historique.** Sur les questions où Elo s’abstient (moins de 5 réponses dans la compétence), le GRU bat le naïf dès 35 élèves d’entraînement : 0,1873 à 0,1887 contre 0,1992. Il est donc utile dès les premières réponses d’un élève, à condition d’avoir été entraîné sur d’autres élèves.

**Deuxième simulateur (B1) et réponses plus bruyantes (N1).** Le GRU entraîné sur A1 n’a vu aucun élève de B1 ni de N1 : tous leurs élèves peuvent lui servir de test.

| Population | GRU | Élèves | Elo − GRU | IC 95 % |
|---|---|---|---|---|
| B1 | entraîné sur A1 (transfert) | 199 | 0,0024 | [0,0014 ; 0,0034] |
| B1 | entraîné sur B1, test de 30 | 30 | 0,0013 | [−0,0021 ; 0,0044] |
| N1 | entraîné sur A1 (transfert) | 198 | 0,0013 | [−0,0001 ; 0,0026] |
| N1 | entraîné sur N1, test de 30 | 30 | 0,0024 | [−0,0007 ; 0,0055] |

- **Changer de lois ne casse pas le GRU :** le GRU d’A1 reste meilleur qu’Elo sur B1. Ce test n’est pas une preuve de généralité : B1 partage la logique de perception de A.
- **Sur des réponses plus bruyantes, le GRU transféré perd son avantage.** Elo devient meilleur sur la pulsation (−0,0170 [−0,0237 ; −0,0109]) et sur les questions qui suivent une pause de quelques heures à 6 jours (−0,0119 et −0,0145, intervalles sous zéro). Le GRU d’A1 a appris le niveau de bruit d’A1 et prévoit environ 0,10 de trop sur ces questions (pulsation : 0,54 prévu, 0,43 observé). Elo, qui s’ajuste à chaque élève, prévoit 0,42.

**Progression inhabituelle (B1, 28 élèves « plateau », jamais vus par le GRU).** Pas de différence de Brier : Elo − GRU = 0,0017 [−0,0006 ; 0,0039]. Sur la tendance, Elo suit un peu mieux ce plateau (61 % dans le bon sens, corrélation 0,56) que le GRU (57 %, 0,47). Comme ce plateau n’a pas décollé (section 3), l’expérience ne dit rien d’un décollage tardif.

**Une famille absente de l’entraînement (L1).** Pour chaque famille, on compare un GRU entraîné sans elle à un GRU de même taille qui l’a vue, tous deux testés sur cette famille.

- Absente, la famille est toujours un peu moins bien prévue. L’écart est le plus fort pour le musicien expérimenté (0,0913 contre 0,0838) et la bonne oreille / rythme faible (0,2006 contre 0,1951).
- Pour ces deux familles, le GRU qui ne les a pas vues passe derrière Elo (0,0899 et 0,1982), sans que l’écart soit démontré. Intervalles Elo − GRU : [−0,0032 ; 0,0004] et [−0,0069 ; 0,0014].
- Pour les familles proches des autres (débutant motivé, irrégulier, en difficulté), l’absence change peu et le GRU reste meilleur qu’Elo.

**Pour quels exercices Elo reste-t-il meilleur ?**
- l’écho au clavier ;
- la pulsation, quand les réponses sont plus bruyantes que celles de l’entraînement ;
- toute question qui suit une longue pause.

Le point commun : le niveau individuel à jour compte plus que ce que l’on apprend des autres élèves, ou le GRU manque d’une information (le temps écoulé).

## 8. Limites scientifiques

- **Ce sont des élèves simulés.** Le GRU peut apprendre les règles du simulateur. La population B (autres lois) et le transfert A → B atténuent ce risque sans le supprimer : B reste écrit par la même équipe, avec la même logique de perception.
- **Les paramètres sont surtout des hypothèses.** Seuls quelques sens et rapports viennent de la littérature ; aucun n’a été calé sur de vrais élèves DÉCLIC.
- **Le simulateur et Elo partagent une forme.** La réussite y dépend d’un niveau qui monte avec la pratique, ce qui favorise par construction les modèles à « niveau par compétence ». La conclusion pourrait changer avec de vrais élèves.
- **L’oracle est estimé par 100 tirages** (erreur type ≤ 0,05 par question). Elle se moyenne sur des dizaines de milliers de questions, mais pas question par question.
- **Huit semaines, peu de niveaux élevés.** La règle de maîtrise de DÉCLIC (80 % et p < 0,05 sur 6 ou 10 réponses) fait que la plupart des élèves restent aux premiers niveaux. Les exercices avancés sont peu représentés.
- **Peu d’élèves de test par population.** Les tests de 30 élèves ne séparent pas Elo et le GRU ; les conclusions reposent sur la validation croisée (197 élèves), les transferts (199 et 198 élèves), le test de 150 élèves de L1 et les trois populations A. Les graines donnent une idée de la variabilité, pas une garantie.
- **Le GRU ne reçoit pas le temps écoulé** (format O08 inchangé). Sa faiblesse après les pauses est une limite de ce format, pas forcément du GRU.
- **Aucun bénéfice pédagogique n’est mesuré.** Les recommandations du planificateur ne sont pas évaluées, seulement les prévisions.

## 9. Conclusions et prochaines améliorations

**Ce que montre cette étude de simulation :**
- Les deux modèles battent nettement la méthode naïve.
- Le GRU DÉCLIC fait un peu mieux qu’Elo, à condition d’avoir été entraîné sur une cohorte d’au moins 200 élèves. Il est aussi mieux calibré et suit un peu mieux les vraies tendances individuelles.
- **Avec 50 élèves, Elo gagne.** Il reste aussi meilleur après les longues pauses, sur l’écho au clavier, et quand les réponses deviennent plus bruyantes que celles vues à l’entraînement.
- L’écart Elo − GRU (environ 0,002 à 0,004 de Brier) est petit à côté de ce qui sépare les deux modèles du Brier minimal (environ 0,06). L’essentiel de cette marge vient du contenu des questions, qu’aucun modèle ne reçoit.

**Ce qu’elle ne montre pas :** que le GRU serait meilleur qu’Elo avec de vrais élèves. Tout ici vient d’un simulateur écrit pour l’occasion.

**Pour DÉCLIC aujourd’hui :** garder Elo dans la boucle d’apprentissage tant qu’il n’y a pas des centaines de vrais élèves. Ce n’est pas une décision de remplacement : c’est ce que suggère la simulation sur le besoin de données.

**Prochaines améliorations, dans l’ordre d’utilité estimée :**
1. **Donner le temps écoulé au GRU** (écart depuis la réponse précédente, en entrée). C’est sa faiblesse la plus nette ; il faut l’ajouter sans toucher au format O08 servi, donc dans un modèle DÉCLIC séparé.
2. **Donner le contenu de la question** aux modèles (pareil ou différent, taille du changement, intervalle joué). C’est la plus grande part de l’erreur restante.
3. **Elo avec une difficulté par exercice apprise sur la cohorte,** et non fixée a priori. Cela corrigerait son erreur sur la reproduction de rythme et sa sous-confiance sous 50 %. C’est la comparaison équitable suivante : un Elo qui profite aussi des autres élèves.
4. **Un troisième simulateur écrit indépendamment,** par une autre personne ou selon d’autres principes, pour tester le risque d’apprendre le simulateur.
5. **Le profil réel « Melek », plus tard et séparément,** en lecture seule et comme exploration indépendante, jamais mélangé à l’entraînement synthétique.

## Reproduire

```
python scripts/run_simulation_campaigns.py --worker 0   # A1, A2, A3, B1, N1 (≈ 70 min, 1 cœur)
python scripts/run_simulation_campaigns.py --worker 1   # L1, 1 000 élèves (≈ 70 min, 1 cœur)
python scripts/run_simulation_study.py inspect main sensitivity replicate shift size families ui
python scripts/report_simulation.py                     # régénère PHASE11_SIMULATION_RESULTS.md
python -m pytest tests/test_simulation_learners.py tests/test_simulation_models.py
node tests/browser/simulation_e2e.cjs                   # les cinq vues dans Chromium
```

- **Configuration :** `configs/simulation-study.json`. Graines des populations 1 à 5, graines du GRU 42, 17 et 83, partition 42, bootstrap 2026.
- **Bases synthétiques et vérité cachée :** `runtime/simulation/sim-2026-11/campaigns/` (non versionnées, recréées à l’identique par les commandes ci-dessus).
- **Résultats, modèles et données d’interface :** `artifacts/simulation/sim-2026-11/`. `reproduce.json` y enregistre la révision du code et l’empreinte de `runtime/learning.sqlite`.
- **Interface :** Laboratoire → « Élèves virtuels » (`/web/simulation.html`). API en lecture seule : `/api/sim`.

## Tests exécutés

| Date | Commande | Résultat |
|---|---|---|
| 2026-11-15 | `pytest tests/test_simulation_learners.py` | 14 réussis : perception (hauteur, intervalles, niveaux), apprentissage et oubli (A et B), fatigue bornée, inattention, plateau atypique, population non clonée, réponses fondées sur la seule question publique, oracle = formule exacte, base réelle refusée, isolation et reproductibilité d’une campagne, HTTP = appel direct, profils marqués SYNTHÉTIQUE |
| 2026-11-15 | `pytest tests/test_simulation_models.py` | 9 réussis : entrées = export O08, prévisions Elo/naïf antérieures aux réponses, causalité du GRU, vérité cachée inaccessible au modèle, partitions disjointes, mêmes questions pour les trois modèles, abstention, intervalles par élève, chargeur limité aux profils synthétiques, API en lecture seule |
| 2026-11-15 | `pytest tests` (suite complète) | 539 réussis, 3 ignorés (données privées absentes), 0 échec |
| 2026-11-15 | `node tests/browser/simulation_e2e.cjs` | 6 scénarios réussis : lien depuis le Laboratoire, chiffres de population = API, un élève (changement d’élève, compétences), tableau Elo/GRU/naïf = résultats mesurés, vues Expériences et Technique, onglets au clavier, liens directs et mobile sans débordement |
