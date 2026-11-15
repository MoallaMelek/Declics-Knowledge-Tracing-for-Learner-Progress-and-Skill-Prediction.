# Phase 11 · Élèves virtuels : étude de simulation Elo vs GRU sur DÉCLIC

> **Étude de simulation.** Les élèves sont simulés. Un modèle entraîné sur eux peut apprendre les règles du simulateur au lieu de vraies habitudes d’apprentissage musical. Rien ici ne démontre qu’un modèle est meilleur avec de vrais élèves. Les chiffres détaillés sont dans [PHASE11_SIMULATION_RESULTS.md](PHASE11_SIMULATION_RESULTS.md), généré automatiquement depuis `artifacts/simulation/sim-2026-11/`.

<!-- RESULTS-SUMMARY -->

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

<!-- RESULTS-DISCUSSION -->

## 9. Limites scientifiques

- **Ce sont des élèves simulés.** Le GRU peut apprendre les règles du simulateur. La population B (autres lois) et le transfert A → B atténuent ce risque sans le supprimer : B reste écrit par la même équipe, avec la même logique de perception.
- **Les paramètres sont surtout des hypothèses.** Seuls quelques sens et rapports viennent de la littérature ; aucun n’a été calé sur de vrais élèves DÉCLIC.
- **Le simulateur et Elo partagent une forme.** La réussite y dépend d’un niveau qui monte avec la pratique, ce qui favorise par construction les modèles à « niveau par compétence ». La conclusion pourrait changer avec de vrais élèves.
- **L’oracle est estimé par 100 tirages** (erreur type ≤ 0,05 par question). Elle se moyenne sur des dizaines de milliers de questions, mais pas question par question.
- **Huit semaines, peu de niveaux élevés.** La règle de maîtrise de DÉCLIC (80 % et p < 0,05 sur 6 ou 10 réponses) fait que la plupart des élèves restent aux premiers niveaux. Les exercices avancés sont peu représentés.
- **Une seule partition principale par population.** Les graines du GRU, trois populations A, la validation croisée et la population B donnent une idée de la variabilité, pas une garantie.
- **Aucun bénéfice pédagogique n’est mesuré.** Les recommandations du planificateur ne sont pas évaluées, seulement les prévisions.
