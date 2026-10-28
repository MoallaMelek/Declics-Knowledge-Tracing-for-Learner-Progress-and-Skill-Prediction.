# Phase 10 · Audit des modèles, compatibilité des entrées, YouTube

Écrit le 27 octobre 2026 à partir du code, des checkpoints et des contrats présents dans ce dépôt (`main` après la PR Phase 10). Rien n'est supposé : chaque ligne renvoie à un fichier ou à un test.

## 1. Ce que contient ce dépôt, et ce qu'il ne contient pas

Ce dépôt est **l'axe 7 (objectif O08 : compétences de l'apprenant et performance future)**. Les six autres axes du projet sont ailleurs :
- axe 1, justesse ;
- axe 2, rythme ;
- axe 3, partition ;
- axe 4, qualité ;
- axe 5, doigté ;
- axe 6, instrument.

Ici, ils n'existent que sous forme de **contrats et de producteurs factices** :
- contrats : `axis7/contracts.py`, `axis7/team_v3.py`, `docs/INTEGRATION.md` ;
- producteurs factices : `examples/axis-*-mock-v2.json`.

**Aucun modèle d'un autre axe n'est implémenté, entraîné ni chargé dans ce dépôt.** Les statuts ci-dessous ne concernent donc que les modèles de l'axe 7.


### 1 bis. Les sept axes : ce que chacun doit produire

D'après les fiches de recherche de l'équipe (`Declic_Axis_1.pdf` à `Declic_Axis_7.pdf`, 6 octobre 2026). Ce sont des **propositions de projet**, pas des résultats.

| Axe | Tâche | Entrée prévue | Sortie prévue | Dans ce dépôt |
|---|---|---|---|---|
| 1 · Notes et hauteur | Transcription audio → notes (début, fin, hauteur) | Forme d'onde mono, piano | Événements MIDI, piano roll | Contrat seulement (producteur factice) |
| 2 · Rythme | Battue, tempo, écarts d'attaque | Audio (+ partition ou clic) | Temps, BPM, écarts signés | Contrat seulement |
| 3 · Suivi de partition | Alignement exécution ↔ partition | Audio ou MIDI + partition | Correspondances note à note, position | Contrat seulement |
| 4 · Qualité | Notes ordinales par critère | Enregistrement d'exercice standardisé | Distributions de notes + incertitude | Contrat seulement |
| 5 · Main et doigté | Vision : touches, doigts | Vidéo du clavier vue de dessus | Repères de la main, doigt par note | Contrat seulement |
| 6 · Instrument | Classification multi-étiquette | Extrait audio de 5 à 10 s | Probabilité par instrument + abstention | Contrat seulement |
| 7 · O08 (ce dépôt) | Knowledge tracing | Tentatives ordonnées, item/compétence, résultat | P(réussite) suivante, maîtrise | **Implémenté, entraîné, évalué, intégré, testé** |

**Les entrées audio et vidéo, y compris un extrait YouTube, relèvent des axes 1 à 6.** L'axe 7 ne reçoit que leurs résultats déjà notés. Tant que ces modèles n'existent pas dans l'application, aucune performance jouée ou chantée ne peut être corrigée automatiquement. C'est pourquoi les exercices DÉCLIC sans instrument produisent eux-mêmes des réponses directement notables : boutons, clavier virtuel, frappes.

## 2. Cartographie et statuts

Statuts :
- **I** = Implémenté ;
- **E** = Entraîné ;
- **Év** = Évalué (sur un jeu de test tenu à part) ;
- **In** = Intégré (servi par l'application) ;
- **T** = Testé de bout en bout (navigateur réel + serveur réel).

### 2.1 Réseaux musicaux O08 servis (Phases 6–8)

Ils sont définis dans le registre `artifacts/models/musical-cloud/active.json`.

| Modèle | Objectif réel | Architecture | Données | I | E | Év | In | T |
|---|---|---|---|---|---|---|---|---|
| `singpad-enhanced_gru-s42-8576d5ba1d6a` (actif) | Probabilité de réussite de chaque note, par concept, à l'enregistrement suivant | EnhancedGRU (GRU 48 unités, contexte 64, embeddings d'exercice, cumuls) — `axis7/cloud_training.py` | SingPAD (chant), partition par apprenant, chronologie auditée | ✓ | ✓ (Colab) | ✓ test log-loss 0,5175, Brier 0,1709, AUC 0,699 | ✓ `/api/v5/musical/forecast`, `/api/v7/o08/living` | ✓ Playwright 16/16 (poids réels, données synthétiques) et 16/16 (données réelles tenues à part, sur le PC) |
| `yousician-enhanced_gru-s42-77455ae03f05` (actif) | Fraction de réussite du prochain jour actif | EnhancedGRU, K = 1 | Yousician Open Data (ukulélé) | ✓ | ✓ | ✓ test MAE 0,0905, RMSE 0,1341 | ✓ | ✓ idem |

Autres modèles et artefacts :
- **Autres checkpoints du registre :**
  - `singpad-item_attention-*` ×2, `singpad-enhanced_gru-*-351afe…` (v1) et `yousician-*-261ac…` ;
  - statut I ✓ · E ✓ · Év ✓ · In ✗ : non actifs ;
  - le checkpoint SingPAD v1 est **refusé** par `musical_registry.validate`, car sa chronologie est invalide.
- **Phases 6 et 7, 36 entraînements CPU de recherche :**
  - fichiers `artifacts/models/phase6`, `phase7` ;
  - sources : SingPAD, Yousician, contexte Yousician et AMME ; 3 graines ;
  - statut I ✓ · E ✓ · Év ✓ (`artifacts/phase7/summary.json`) · In ✗ : non servis, résultats publiés dans le Laboratoire ;
  - sur trois partitions, SingPAD bat les contrôles choisis sur la validation (log-loss 0,5179 contre 0,5242) ; AMME et Yousician non (`docs/PHASE7_EXECUTIVE_SUMMARY_EN.md`).
- **AMME (clavier) :** I ✓ · E ✓ · Év ✓ · In ✗ ; recherche seulement, pas d'entrée active dans le registre.

### 2.2 Anciens modèles (Phases 1 à 5)

| Modèle | Données | Statut | Intégration |
|---|---|---|---|
| DKT, SAKT (3 graines), BKT, PFA, prior | `music-mock` : **données musicales simulées**, 6 compétences piano provisoires | I ✓ E ✓ Év ✓ (sur données simulées) | `/api/twin`, `/api/v2/forecast` ; page d'archive « Simulation » ; `/api/v4/forecast` s'abstient par défaut sur la musique réelle |
| Mêmes modèles | FORGET-SE (génie logiciel public) | I ✓ E ✓ Év ✓ | Archive de recherche uniquement |
| Recherche v2 (enhanced_gru, item_attention, item_pfa…) | music-mock, FORGET-SE | I ✓ E ✓ Év ✓ | Prédicteurs `v2:` des archives |

Ces modèles n'ont jamais vu de données d'apprenants musicaux réels. Ils restent des archives et ne sont pas présentés comme des modèles de l'apprenant.

### 2.3 Nouveau en Phase 10 : modèle de référence de la boucle d'apprentissage

| Modèle | Objectif | Nature | Statut |
|---|---|---|---|
| `declic-elo-v1` (`axis7/learning_model.py`) | P(réussite) à la prochaine question d'une séance DÉCLIC, par compétence | **Pas un réseau de neurones**. Elo avec terme de hasard (Pelánek 2016) : P = c + (1 − c)·σ(θ − d), mise à jour en ligne, difficulté d fixée par le niveau | I ✓ · E : sans objet (en ligne, aucun paramètre appris hors θ) · Év : mesuré **par apprenant**, en direct (Brier contre un taux de réussite naïf, calibration à partir de 30 prévisions) · In ✓ `/api/learn` · T ✓ (`tests/browser/learner_e2e.cjs`) |

Comparateur : taux de réussite au même exercice et niveau, lissé par un a priori de moyenne (1 + c)/2, à mi-chemin entre le hasard et la certitude. Battre ce comparateur n'est pas une preuve de validité, seulement un premier contrôle.

Ce modèle **s'abstient** tant qu'une compétence a moins de 5 réponses. Sa prévision est écrite *avant* l'affichage de la question ; c'est vérifié par `tests/test_learning.py::test_insufficient_data_abstains_and_enough_data_gives_preregistered_predictions`. Si le modèle plante, la question reste servie et l'échec est enregistré, jamais remplacé par une valeur (`test_reference_model_failure_is_recorded_not_replaced`).

## 3. Matrice de compatibilité des entrées

Aucun modèle de l'axe 7 ne lit d'audio, de vidéo, d'image ni de MIDI. `docs/INTEGRATION.md` le dit déjà : « No raw audio/video/image is accepted or processed by Axis 7 ». Tous prennent des **séquences de résultats déjà notés**. Transformer un son en résultat noté est le rôle des axes 1 et 2, qui ne sont pas dans ce dépôt.

| Modèle | Entrée exacte | Prétraitement (code) | Sortie | WAV / MP3 | MIDI | Vidéo YouTube | Exercices DÉCLIC sans instrument |
|---|---|---|---|---|---|---|---|
| SingPAD EnhancedGRU | Groupes chronologiques : `time` ISO local (minute), `exercise` (identifiants de partition SingPAD connus du modèle, sinon abstention), `observations` `[{concept 0–269, score ∈ {0,1}, weight}]` ; au moins 2 groupes antérieurs | `cloud_training.encode` : pour le pas t, échecs et réussites du pas précédent, `log1p` des cumuls antérieurs, exercice précédent et demandé ; fenêtre de 64 | Probabilité par concept demandé | ✗ (il faudrait d'abord une évaluation note à note) | ✗ | ✗ | ✗ : les concepts SingPAD sont des identifiants opaques de la base, sans correspondance avec les compétences DÉCLIC ; le contrat exige `instrument = voice` |
| Yousician EnhancedGRU | Un score par jour actif, entier `time` = jours depuis l'inscription, `score` = (notes + accords réussis) / (évalués) ∈ [0, 1] | idem, K = 1 | Score continu du prochain jour actif (affiché « / 100 », jamais en %) | ✗ | ✗ | ✗ | Forme compatible (un score par jour), **sens incompatible** ; le contrat exige `instrument = ukulele` et s'abstient sinon (`incompatible_domain`) |
| AMME | Score moyen de similarité de hauteur par bloc (clavier) | idem | Score du bloc suivant | ✗ | ✗ | ✗ | ✗ |
| DKT / SAKT music-mock | Événements `{skill ∈ 6 compétences piano provisoires, outcome 0/1}` | `inference.py` | P par compétence | ✗ | ✗ | ✗ | ✗ (piano provisoire, entraîné sur simulation) |
| `declic-elo-v1` | Réponses DÉCLIC `{compétence, exercice, niveau, juste}` | aucun | P(réussite) de la question suivante | ✗ | ✗ | ✗ | ✓ : c'est son domaine |

Les sorties sont exploitées ainsi :
- SingPAD et Yousician : Rejeu O08 (résumé, prochain essai, révélation, vue chercheur) et Laboratoire ;
- `declic-elo-v1` : correction de chaque question (« prévision enregistrée avant votre réponse »), bilan de séance, section « O08 sur mes données » du Parcours.

`tests/test_o08_leakage_audit.py` vérifie sur les **checkpoints actifs** :
- des groupes futurs envoyés dans la requête ne changent pas la prévision ;
- les groupes passés la changent ;
- les partitions entraînement, validation et test sont distinctes par apprenant ;
- un instrument piano, clavier ou ukulélé envoyé au modèle SingPAD produit une abstention.

S'y ajoutent les tests de causalité existants : `test_causality.py`, `test_cloud_training.py`, `test_phase6_chronology.py`, `test_phase8_living.py`.

## 4. Fuite de données O08 : vérification

- **Vraies séquences de tentatives.** SingPAD : chaque groupe est un enregistrement réel d'un utilisateur, à horodatage d'origine (`load_singpad`). Les égalités d'horodatage sont fusionnées, jamais ordonnées arbitrairement. L'audit chronologique est exigé par `validate` : 0 inversion, 0 doublon.
- **Causalité de l'encodage.** `encode` ne lit, au pas t, que les groupes antérieurs. La cible du pas t n'entre pas dans ses caractéristiques. Le premier pas (démarrage à froid) n'est pas noté.
- **Partition par apprenant.** `split_learners` ; les empreintes des trois partitions doivent différer, sinon le registre refuse le modèle. Le vocabulaire d'exercices ne vient que de l'entraînement (`test_split_disjoint_and_item_vocabulary_train_only`).
- **Côté service.** `forecast_with_model` ignore tout groupe dont l'heure est ≥ l'heure de requête. Le Rejeu sert l'état au seuil choisi sans révéler le résultat ; la révélation passe par un reçu signé.
- **Boucle DÉCLIC.** La prévision est calculée avec les seules réponses déjà données et horodatée avant la réponse. Le test SQL vérifie `created_at < answered_at` pour chaque question.

Conclusion : aucune fuite détectée par ces contrôles. Une limite demeure : la Phase 7 réutilise des partitions déjà examinées en Phase 6. Ce sont donc des preuves exploratoires, pas une cohorte de confirmation indépendante (déjà écrit dans les rapports Phase 7).

## 5. Tester vos modèles avec des données compatibles

**1. Sur des données réelles (recommandé).** Laboratoire → *Rejeu O08*. Le réseau servi rejoue des apprenants du jeu de test, jamais utilisés pour l'entraînement. On peut :
- lire la prévision ;
- la révéler ;
- inspecter la mémoire GRU.

Il faut les données privées préparées (`runtime/musical-demo`).

**2. Requête directe au format exact**, sans données privées : les poids sont dans le dépôt. Exemple SingPAD (valeurs inventées, donc **test de mécanique uniquement**) :

```powershell
$body = '{"source":"singpad","model_id":"singpad-enhanced_gru-s42-8576d5ba1d6a","instrument":"voice","query_time":"2021-03-05T10:00:00","exercise":"250","concepts":[3,7],"history":[{"time":"2021-03-01T10:00:00","exercise":"250","observations":[{"concept":3,"score":1},{"concept":7,"score":0}]},{"time":"2021-03-02T10:00:00","exercise":"250","observations":[{"concept":3,"score":0},{"concept":7,"score":1}]},{"time":"2021-03-03T10:00:00","exercise":"250","observations":[{"concept":3,"score":1},{"concept":7,"score":1}]}]}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8781/api/v5/musical/forecast -ContentType 'application/json' -Body $body
```

Réponse obtenue le 27/10/2026 : `status = source_benchmark_only`, `predictions = {"3": 0.792, "7": 0.770}`.

Yousician (même mécanique) : `{"source":"yousician","model_id":"yousician-enhanced_gru-s42-77455ae03f05","instrument":"ukulele","query_time":6,"concepts":[0],"history":[{"time":0,"observations":[{"concept":0,"score":0.55}]},{"time":1,"observations":[{"concept":0,"score":0.6}]},{"time":3,"observations":[{"concept":0,"score":0.7}]},{"time":4,"observations":[{"concept":0,"score":0.72}]}]}`. Réponse : `0.714`, prévision du score du prochain jour actif.

Contrôles d'abstention vérifiés :
- `instrument: "piano"` → `incompatible_domain` ;
- requête SingPAD sans `exercise` → `query_exercise_required` ;
- exercice inconnu → `unseen_exercise`.

**3. Vos propres réponses DÉCLIC.** Parcours → « Exporter mes tentatives (format O08) ». Le fichier contient :
- vos réponses ;
- les prévisions enregistrées ;
- les mêmes groupes au format `{learner, time, exercise, obs: [[compétence, résultat, poids]]}` lu par `cloud_training.encode`.

L'export vérifie lui-même que `encode` les accepte (`encode_check`). C'est la passerelle vers un futur réseau O08 *natif DÉCLIC*. L'entraîner demande les réponses de **nombreux** apprenants, avec consentement et une partition par apprenant ; un seul profil ne suffit pas. Nous ne l'avons pas fait.

**4. Tests automatisés :**

```
python -m pytest -q tests/test_o08_leakage_audit.py tests/test_learning.py
```

## 6. YouTube : possible ou non ?

**Techniquement.** Aucun modèle O08 ne lit de vidéo ni d'audio (section 3). Il faudrait toute une chaîne, que ce dépôt ne contient pas :
1. extraire l'audio ;
2. le transcrire en notes (axe 1) et en attaques (axe 2) ;
3. aligner sur une partition de référence (axe 3) ;
4. noter chaque note juste ou fausse ;
5. alors seulement, produire des groupes au format SingPAD ou au format DÉCLIC.

Même ainsi, une vidéo d'un musicien expert donne **ses** résultats, pas les vôtres. Elle peut servir de **démonstration technique** ou de **référence** (le son cible), jamais de mesure de votre compétence. DÉCLIC sépare donc trois choses :
- démonstrations techniques (Rejeu O08, requêtes au format exact) ;
- données de référence (les sons et partitions générés par les exercices) ;
- performances réelles de l'apprenant (vos réponses, seules à entrer dans votre parcours).

**Juridiquement.** Les Conditions d'utilisation de YouTube interdisent d'accéder au contenu, de le copier, de le télécharger ou de le distribuer, sauf si le service le permet expressément, si les ayants droit l'autorisent par écrit ou si la loi le permet. Elles interdisent aussi l'accès automatisé, par robots ou scrapers ([conditions, version FR](https://www.youtube.com/static?gl=FR&template=terms)). Télécharger des vidéos pour en faire des données d'entraînement ou d'évaluation n'est donc pas une option par défaut.

Options légales :
- (a) le lecteur YouTube **intégré**, pour l'écoute seulement, sans extraction ;
- (b) des œuvres du domaine public ou sous licence ouverte, après vérification de la licence de chaque fichier ;
- (c) vos propres enregistrements, le jour où vous jouerez d'un instrument (il faudrait alors les modèles des axes 1 et 2) ;
- (d) des stimuli générés : c'est le choix de DÉCLIC, car les sons des exercices sont synthétisés par le navigateur à partir de paramètres connus. La correction est donc exacte, et la question des droits ne se pose pas ;
- (e) des données synthétiques, **pour tester les pipelines uniquement**, jamais comme validation.

Je ne suis pas juriste : en cas d'usage public ou commercial, faites valider le choix des sources.
