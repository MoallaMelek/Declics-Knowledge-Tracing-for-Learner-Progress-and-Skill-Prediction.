# Phase 10 · DÉCLIC utilisable sans instrument : la boucle de l'apprenant

Mission (27/10/2026) : pouvoir lancer DÉCLIC, créer son profil, cliquer sur « Commencer une séance », faire de vrais exercices sans instrument, recevoir une évaluation, terminer la séance, consulter son historique, recommencer pour mesurer sa progression, et comprendre comment les résultats alimentent O08.

Documents associés :
- [PHASE10_MODEL_AUDIT.md](PHASE10_MODEL_AUDIT.md) : modèles, matrice des entrées, fuite de données, YouTube, tester ses modèles ;
- [PHASE10_PEDAGOGY.md](PHASE10_PEDAGOGY.md) : recherche, architecture pédagogique, 12 fiches ;
- [GUIDE_SANS_INSTRUMENT.md](GUIDE_SANS_INSTRUMENT.md).

Auteur et testeur : Claude (session cloud et PC relié). Revue indépendante : section 7. Vérification sur le PC : section 6.

## 1. Audit des blocages avant la Phase 10

| # | Blocage constaté | Cause trouvée dans le code | Correction |
|---|---|---|---|
| B1 | Le « Parcours » restait sur « Chargement du parcours… », sélecteur vide (capture d'Edge) | Ce texte est le texte statique de la page : il ne reste affiché que si les scripts ne s'exécutent jamais. Les pages n'avaient ni chien de garde ni en-tête de cache : un onglet restauré depuis le cache d'Edge pendant que le serveur était arrêté restait figé. Le même jour, sur le même PC, la page chargeait normalement (8 profils, réponse API en 11 ms). | Chien de garde intégré à la page : au bout de 8 s, message clair, détail de l'erreur et bouton « Recharger » (`living.html`, `seance.html`, `parcours.html`, `exercices.html`). `Cache-Control: no-cache` sur `/web/*` (`axis7/web_cache.py`). Testé dans Chromium avec des scripts bloqués volontairement. |
| B2 | Aucun moyen de « commencer une séance » sans piano | Le seul parcours apprenant était le Carnet (Phase 4) : six exercices à jouer sur un vrai piano | Séances sans instrument (12 exercices, 53 niveaux) ; le Carnet devient un outil de recherche « nécessite un piano » |
| B3 | Aucune évaluation réelle | Le Carnet enregistre une auto-évaluation (« à travailler / en progrès / à l'aise ») : rien n'est corrigé | Chaque réponse est corrigée par le serveur (`learning_catalog.evaluate`), qui garde la bonne réponse |
| B4 | Aucune prévision O08 sur ses propres données | `progression.notebook_forecast` s'abstient toujours (barème non approuvé, aucun modèle validé). Le registre prospectif v6 s'abstient et exige un jeton administrateur. Les réseaux entraînés refusent tout autre domaine (audit, section 3) | Prévision du modèle de référence `declic-elo-v1`, enregistrée avant chaque réponse puis comparée ; abstention explicite tant que les données sont insuffisantes ; abstention des réseaux expliquée réseau par réseau |
| B5 | « Parcours » incompréhensible | La page s'appelait Parcours mais rejouait les apprenants des jeux de données (« Profil de démonstration »), pas le vôtre | Renommée **Rejeu O08**, rangée dans le Laboratoire ; **Parcours** désigne désormais votre carte de progression |
| B6 | Pas d'historique durable de l'apprenant | Seul le Carnet stockait quelque chose, et seulement des auto-évaluations | `runtime/learning.sqlite` : profils, séances, questions, réponses, prévisions ; survit aux redémarrages (testé) |
| B7 | Difficulté et pertinence des exercices non justifiées | Le catalogue piano était marqué « introductory » et `teacher_approved: false`, sans critère ni référence | Fiche en 10 champs par exercice, critère vérifiable par niveau, références avec liens |

## 2. Architecture

Navigation : **Accueil · Séance · Parcours · Exercices · Laboratoire**. Les cinq notions sont définies sur la page Parcours et dans [PHASE10_PEDAGOGY.md §2](PHASE10_PEDAGOGY.md).

Backend : module additif `axis7/learning.py`, préfixe `/api/learn`, corps limité à 64 Kio. Les contrats existants ne changent pas.

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/learn/catalog` | Compétences, fiches, références, règle de maîtrise |
| POST/GET | `/api/learn/learners`, `/learners/{id}` | Créer / lister / lire un profil (séance active, évaluation faite) |
| POST | `/learners/{id}/sessions` | `auto` reprend la séance active, sinon lance l'évaluation initiale puis des séances ; `ciblee` (exercice, niveau) |
| POST | `/sessions/{id}/next` | Question suivante (ou la même si elle est restée sans réponse) ; la prévision est écrite à ce moment-là |
| POST | `/items/{id}/answer` | Correction serveur ; réponse invalide → 422 sans enregistrer d'échec ; rejouer la même réponse est idempotent ; en changer → 409 |
| POST/GET | `/sessions/{id}/finish`, `/summary` | Bilan : score, niveaux maîtrisés, seuil, prévisions, erreurs, prochaine séance |
| GET | `/learners/{id}/progress` | Carte de maîtrise, forces et faiblesses, erreurs récurrentes, jours, historique, section O08 |
| GET | `/learners/{id}/export` | Tentatives + prévisions + groupes au format de l'encodeur O08 (vérifié) |

Frontend (`web/learn/`) :
- son synthétisé en Web Audio ;
- clavier virtuel deux octaves, piloté à la souris ou par les touches physiques, AZERTY comme QWERTY ;
- zone de frappe (barre d'espace), dont les horodatages sont relatifs au premier clic ;
- portée SVG ;
- réponses aux touches 1 à 9 et Entrée.

Aucune dépendance externe : tout fonctionne hors ligne.

## 3. Comment vos résultats alimentent O08

1. À la création d'une question, le serveur calcule P(réussite) avec vos seules réponses déjà données. La prévision est horodatée et écrite avec la question.
2. Vous répondez ; le serveur corrige.
3. La prévision, la base naïve (taux de réussite au même niveau) et le résultat sont comparés. Dans Parcours → « O08 sur mes données » :
   - Brier et log-loss, modèle contre base ;
   - évolution par tranches de 10 prévisions ;
   - calibration à partir de 30 prévisions.
4. Le modèle s'abstient tant qu'une compétence a moins de 5 réponses ; ces abstentions sont comptées, jamais notées comme des prévisions.
5. Les réseaux O08 entraînés s'abstiennent sur vos données, et la page dit pourquoi. Vos tentatives sont exportables au format exact de leur encodeur, en vue d'un futur entraînement *natif DÉCLIC* sur de nombreux apprenants.

## 4. Ce qui fonctionne, ce qui est partiel, ce qui reste

| Fonctionnalité | Fonctionne | Partiel | Reste à faire |
|---|---|---|---|
| Profil persistant | Création, reprise automatique, changement de profil, historique sur plusieurs jours | Local, mono-utilisateur, sans authentification | Comptes, multi-appareils |
| Commencer / reprendre une séance | Évaluation initiale (30 questions), séances planifiées, séances ciblées, reprise sur la même question | — | — |
| Exercices sans instrument | 12 exercices, 53 niveaux, 4 modes de réponse, correction serveur | Sons de synthèse (timbre simple) ; tapotement soumis à la latence variable du clavier et du navigateur | Validation par un enseignant ; mesure micro façon REPP |
| Évaluation | Juste / pas encore, bonne réponse, réécoute, métriques (cents, tempo, variation, placement) | Seuils de tempo et de tolérance rythmique **provisoires** | Normes issues de données réelles |
| Parcours (maîtrise) | Carte des niveaux, prochaine étape, prérequis, consolidation, révision espacée | La difficulté *d* du modèle est fixée par le niveau, pas estimée | Estimer les difficultés sur de nombreux apprenants |
| Forces, faiblesses, erreurs | Réussite récente contre hasard, tendance à niveau comparable, confusions récurrentes | — | — |
| O08 sur mes données | Prévisions préenregistrées, abstention, qualité contre base, calibration, export compatible avec l'encodeur | Modèle de référence statistique, pas un réseau | Réseau O08 natif DÉCLIC (collecte multi-apprenants consentie, partition par apprenant, entraînement, évaluation) |
| Réseaux O08 entraînés | Servis, testés, rejouables sur données réelles (Rejeu), requêtables au format exact | Données réelles nécessaires pour le Rejeu (privées) | Cohorte de confirmation indépendante (déjà listé en Phase 7) |
| YouTube | Analyse technique et juridique (audit §6) | — | Rien n'est importé de YouTube, volontairement |
| Robustesse | Message clair si le serveur est arrêté, chien de garde au démarrage, 422 et 409 lisibles | — | — |

## 5. Tests et preuves

| Suite | Contenu | Résultat (cloud, 27/10/2026) |
|---|---|---|
| `pytest` (toute la suite) | dont 78 tests `test_learning.py` et 7 tests `test_o08_leakage_audit.py` | **512 réussis, 3 ignorés** (données privées absentes du cloud) |
| `tests/browser/learner_e2e.cjs` (Chromium réel + serveur réel + base neuve) | 12 scénarios (détail ci-dessous) | **12/12** |
| `tests/browser/living_e2e.cjs` | Rejeu O08, poids réels, données synthétiques | **16/16** |

Les 12 scénarios du parcours navigateur :
1. accueil → « Commencer une séance » → profil ;
2. évaluation initiale ;
3. réussites et échecs corrigés ;
4. reprise après rechargement sur la même question ;
5. tous les modes de réponse ;
6. bilan ;
7. Parcours et O08 ;
8. nouvelle séance arrêtée tôt ;
9. bibliothèque (10 champs) et niveaux experts de chaque famille ;
10. entrée invalide ;
11. serveur coupé, avec message et nouvel essai ;
12. chien de garde, puis navigation et mobile sans débordement.

Correspondance avec les cas demandés :

| Cas demandé | Preuve |
|---|---|
| Nouvel utilisateur sans compétence, sans instrument | `test_new_learner_without_instrument_first_session_is_the_initial_assessment` ; e2e scénario 1 |
| Première séance | idem ; e2e 2–4 |
| Exercice réussi / échoué | `test_success_and_failure_are_scored_on_the_server_with_feedback` ; e2e (verdict vérifié à chaque question) |
| Plusieurs tentatives successives | `test_several_attempts_lead_to_mastery_and_unlock_the_next_step`, `test_two_choice_mastery_needs_more_than_chance`, `test_failing_learner_gets_consolidation_not_a_harder_level` |
| Reprise d'une séance interrompue | `test_interrupted_session_is_resumed_on_the_same_unanswered_item`, `test_explicit_new_session_interrupts…` ; e2e « reprise après rechargement » |
| Retour après plusieurs jours | `test_return_after_several_days_keeps_history_and_schedules_spaced_review`, `test_fully_mastered_exercise_comes_back_as_spaced_review`, `test_history_persists_on_disk_across_server_restarts` |
| Historique suffisant pour O08 | `test_profile_with_long_history_reports_quality_trend_and_calibration` (35 prévisions évaluées, calibration, 3 tranches) |
| Données insuffisantes | `test_insufficient_data_abstains_and_enough_data_gives_preregistered_predictions` |
| Exercices avancés | `test_advanced_levels_are_playable_and_counted`, 53 tests paramétrés (chaque niveau généré et corrigé dans les deux sens) ; e2e « niveaux experts » |
| Entrées invalides | `test_invalid_inputs_are_refused_without_recording_a_failure` (vide, texte, NaN, trop long, 413, 409, idempotence) ; e2e « entrée invalide » |
| Modèle indisponible ou en erreur | `test_reference_model_failure_is_recorded_not_replaced` ; e2e « serveur coupé » ; abstention des réseaux : `test_o08_leakage_audit.py` |

Les réponses du « learner » scripté sont lues dans la base de test : ce sont des **tests de pipeline**, pas une preuve d'apprentissage ni de validité du modèle.

## 6. Vérification sur le PC (scénario d'acceptation)

Faite le 28/10/2026, vers 3 h du matin, sur le PC de Melek (Windows) :
- dans le navigateur intégré de l'app Claude ;
- version `main` 8cd6e3c, avec les vraies données de recherche (`private_research_data`, prêt) ;
- serveur redémarré par **Redemarrer DECLIC**. Le script a arrêté l'ancien serveur (révision b4c5cd0), et seulement lui.

Le profil de test « Verification Claude » a été supprimé ensuite, pour que le premier vrai profil parte de zéro.

| Étape du critère d'acceptation | Résultat observé sur le PC |
|---|---|
| Lancer DÉCLIC | Accueil : « DÉCLIC est prêt : séances, parcours et laboratoire disponibles » |
| Créer son profil | Pseudonyme tapé au clavier, puis **Créer mon profil** → « Bienvenue » |
| Cliquer « Commencer une séance » | Évaluation initiale, question 1 sur 30 ; contexte audio actif (48 kHz, latence de sortie annoncée 48 ms) |
| Faire de vrais exercices sans instrument | Mesure de seuil, mélodies, intervalles, rythmes, pulsation (barre d'espace), lecture sur portée (clé de sol bien rendue), écho au clavier virtuel. Une note lue à la main (« mi ») a été corrigée « Juste. C'était bien mi. » |
| Recevoir une évaluation | Verdict, bonne réponse et métriques à chaque question ; « Réponse enregistrée » pendant la mesure |
| Interruption puis reprise | Page rechargée à 10/30 → « Reprendre ma séance (10 / 30) » → reprise à la question 11 |
| Terminer la séance | Bilan « 16 réponses justes sur 30 » : seuil indicatif, détail, erreurs, prévisions, prochaine séance |
| Recommencer | « Commencer une autre séance » : séance de 12 questions composée à partir du bilan |
| O08 | Les prévisions apparaissent dès la 5ᵉ réponse d'une compétence (44 % puis 38 % puis 33 % après des échecs en lecture). 17 prévisions évaluées au total ; le modèle était **moins bon** que le taux simple (Brier 0,220 contre 0,211), et la page le dit |
| Historique | Parcours : 42 réponses, 2 séances terminées, carte des niveaux, erreurs récurrentes, historique avec liens « Bilan » |

**Défauts trouvés sur le PC, corrigés dans la foulée** (PR suivante) :
- Avec seulement deux compétences notées, le classement mettait « point fort » sur 38 % de réussite à 2 choix. Désormais, un point fort exige une réussite nettement au-dessus du hasard ((taux − hasard)/(1 − hasard) ≥ 0,6), et un point faible correspond à moins de 0,4. Un test a été ajouté.
- Le seuil s'affichait « 317.5 cents » au lieu de « 317,5 cents » (format français).
- Les accents de la console du lanceur s'affichaient mal : `Launch.ps1` est maintenant en UTF-8 avec BOM, comme l'attend Windows PowerShell 5.1.

Les réponses de cette vérification ont été données par un script (choix au hasard, frappes régulières), sauf la note lue à la main. C'est une preuve de fonctionnement, pas une mesure d'apprentissage.

## 7. Revue indépendante

Elle a été menée par une session Claude neuve, en lecture seule, sans l'historique de la conversation. Cette session a relancé les tests et sondé l'API avec ses propres scripts.

**Aucun bloquant.** Toutes les remarques ont été corrigées, avec un test de régression pour chacune.

Les quatre remarques majeures :
1. **Maîtrise.** Elle était acquise pour toujours alors que l'interface parlait des « 10 dernières réponses ». Elle est désormais jugée sur les W dernières réponses. Le nouvel état « à consolider » couvre un niveau maîtrisé puis en baisse : le planificateur y revient, mais les prérequis débloqués restent acquis.
2. **Mesure du seuil.** Elle affichait une correction. Elle montre désormais « Réponse enregistrée », sans verdict ni prévision ; le seuil n'apparaît que dans le bilan.
3. **Raccourcis clavier.** Ils ne pouvaient pas atteindre les réponses 10 à 12, et taper « 1 » validait la première réponse. Seules les réponses 1 à 9 ont désormais un raccourci.
4. **Seuil de hauteur.** Il mélangeait toutes les séances et fixait un niveau à partir d'un seul changement de sens. Il est désormais calculé sur la dernière mesure seulement, et ne place un niveau qu'avec au moins 4 changements de sens (ou une mesure sans aucune erreur).

Les remarques mineures :
- avertissement avant qu'un exercice de la bibliothèque n'interrompe la séance en cours ;
- une évaluation initiale arrêtée avant 15 réponses ne compte pas ;
- une erreur 409 renvoie à l'écran de départ ;
- une mélodie « contour changé » n'introduit plus de note répétée ;
- l'écho chromatique respecte l'amplitude des sauts ;
- les réponses aux champs inattendus sont refusées ;
- le nombre de réécoutes est plafonné ;
- un nom fait d'espaces est refusé ;
- la base naïve tient compte du hasard (moyenne a priori (1 + c) / 2) ;
- les items de mesure sont exclus des forces et faiblesses ;
- le verdict est annoncé aux lecteurs d'écran.

Limite assumée, signalée par la revue : pour dessiner la note, la page de lecture reçoit sa position sur la portée. Un utilisateur qui lit le trafic réseau peut donc en déduire la réponse. Pour les exercices d'écoute, les notes jouées sont elles aussi forcément transmises au navigateur. C'est sans conséquence pour un outil d'entraînement personnel, mais cela exclut un usage d'examen surveillé.

## 8. Lancer

Double-cliquer « Lancer DECLIC » (bureau) ou `Launch.ps1 -Open` dans le dossier du projet, puis suivre le [guide](GUIDE_SANS_INSTRUMENT.md).
