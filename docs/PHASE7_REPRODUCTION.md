# Phase 7 - reproduction et exploitation

## Environnement et frontières

Les expériences livrées sont CPU, PyTorch 2.14.1+cpu et NumPy 2.5.3 dans l'environnement local.
Les autres versions observées sont consignées dans artifacts/phase7/execution-provenance.json.
Ne pas confondre ces versions avec le GPU Phase 6 : PyTorch 2.11.0+cu130 et contraintes Colab propres.
Le fichier de versions observées ne prouve pas une installation indépendante depuis un index public.
Les dépendances et leur disponibilité peuvent varier ; un changement doit créer une expérience distincte.

Les trois archives sont locales et privées. Aucun téléchargement ou compte cloud payant n'est nécessaire
pour reproduire les données déjà présentes. Les notebooks Phase 6 restent disponibles avec sauvegardes
Drive et empreintes ; la Phase 7 n'en dépend pas pour servir les poids exportés. Aucun entraînement
Phase 7 n'est présenté comme exécuté sur Colab. Aucun nouveau notebook Phase 7 GPU n'a été prétendu.

## Programme principal

Depuis la racine du dépôt et dans l'environnement scientifique approprié :

```text
python scripts/run_phase7_research.py --source singpad --archive CHEMIN/singKT-dataset-main.zip
python scripts/run_phase7_research.py --source amme --archive CHEMIN/2gvty-osfstorage-archive.zip
python scripts/run_phase7_research.py --source yousician --archive CHEMIN/yousician_ukulele.json.zip
```

Les graines par défaut sont 42, 17 et 83. Les rapports vont dans artifacts/phase7/SOURCE ; les caches,
identifiants d'apprenants, curseurs et optimiseurs restent dans tmp/phase7-private/SOURCE, hors Git.
Les rapports déjà présents ne sont réutilisés qu'après contrôle du dataset, des splits, de la condition,
des versions, du protocole et d'une empreinte de code explicitement admise. Les versions dense/sparse
de l'attention sont documentées dans configs/phase7-compatible-implementations.json. Une empreinte
inconnue n'est pas acceptée silencieusement. Les checkpoints de nouvelles implémentations ont un dossier
séparé ; une reprise incompatible est refusée. Pour une nouvelle étude avec versions différentes,
archiver les sorties de recherche précédentes dans un autre checkout et garder les tableaux historiques.

Si un rapport GRU existe mais que son stress test manque, le script recharge les poids correspondant
à l'empreinte du rapport et reprend cette analyse. Un fichier de métriques seul ne prouve pas que toutes
les analyses ont terminé. Les poids sont des state_dict PyTorch ; ne jamais charger un pickle externe
présenté comme un checkpoint d'optimiseur. La reprise privée concerne les fichiers produits par ce code.

## Contrôles et analyses complémentaires

```text
python scripts/phase7_strong_controls.py singpad CHEMIN/singKT-dataset-main.zip
python scripts/phase7_strong_controls.py amme CHEMIN/2gvty-osfstorage-archive.zip
python scripts/phase7_strong_controls.py yousician CHEMIN/yousician_ukulele.json.zip
python scripts/phase7_additional_audits.py CHEMIN/2gvty-osfstorage-archive.zip CHEMIN/yousician_ukulele.json.zip
python scripts/train_yousician_context.py CHEMIN/yousician_ukulele.json.zip
python scripts/report_phase7.py
```

Le dernier script vérifie archives, splits et nombres de cibles avant de réunir les 33 runs principaux
et les trois extensions. Les poids portables sont dans artifacts/models/phase7 ; les compteurs de
partitions et leurs condensats sont publics, les identifiants individuels ne le sont pas. Les modèles
de cette collection sont réservés à la recherche et ne sont pas ajoutés au registre actif v5.
Les scores publiés avant les contrôles ne sont pas effacés selon qu'ils sont favorables ou non.

La validation AMME comporte cinq folds externes d'apprenants, avec validation interne par apprenant
pour Ridge. L'audit Yousician donne difficulté, nombre de jours antérieurs, indice de séance et plages
des compteurs alternatifs. Ces plages ne sont pas des labels fiables reconstruits pour les exclus.
La durée réelle de pratique et l'ordre unique d'essais contradictoires restent indisponibles.

## Application et démonstration

```text
python -m uvicorn axis7.server:app --host 127.0.0.1 --port 8773
```

Ouvrir /web/o08.html. La page utilise /api/v6/o08/demo/history, /predict et /reveal. Le premier appel
ne donne pas le résultat futur au navigateur. Le second calcule les poids actifs et signe un reçu ;
le troisième révèle l'observation. Après redémarrage, recharger la page pour obtenir de nouveaux reçus.
Un seul worker est prévu par défaut. Pour plusieurs workers, configurer la même DECLIC_DEMO_SIGNING_KEY
aléatoire forte sur tous les workers ; ne jamais la committer. Ne pas confondre cette clé et le jeton
administrateur de collecte. Les tickets ne constituent pas une authentification d'élève.

Les exemples proviennent de runtime/musical-demo, reconstruit avec les scripts Phase 6 depuis les
archives locales et le registre actif. Un exemple absent ou incompatible provoque un message d'erreur,
jamais un remplacement par un parcours fictif. La sélection déterministe ne dépend pas de l'erreur.

La mesure HTTP locale est reproductible avec :

```text
python scripts/benchmark_o08.py --url http://127.0.0.1:8773 --count 15 --output artifacts/phase7/inference-benchmark.json
```

Les requêtes de révélation sont contrôlées après prévision, les réponses avant révélation ne contiennent
pas observed_target. Les temps sont des observations locales ; la première mesure n'est pas forcément
un démarrage à froid et aucune extrapolation de capacité multi-utilisateur n'est justifiée.

## Collecte prospective volontaire

La collecte est désactivée sans jeton local de 32 caractères minimum. Générer un secret aléatoire de
forte entropie dans l'environnement de lancement et définir DECLIC_O08_ADMIN_TOKEN sans le publier.
Chaque requête de collecte utilise Authorization: Bearer SECRET. Ne pas le placer dans une URL.
Les endpoints historiques et la démonstration ne deviennent pas sécurisés pour Internet grâce à ce jeton.

Ordre des opérations : enregistrer le consentement/version et la durée de rétention ; ingérer des
événements passés mesurés ; demander une prévision pour un essai futur ; observer ensuite l'essai ;
ingérer son résultat ; exporter le dossier et les évaluations. Le modèle terrain reste en abstention
tant que le contrat de mesure n'est pas validé. Ne pas déclarer ce flux comme une étude d'efficacité.

| Endpoint administratif | Fonction |
|---|---|
| POST /api/v6/o08/consent | Consentement déclaré et rétention locale |
| POST /api/v6/o08/events | Événement validé, doublon idempotent, conflit refusé |
| POST /api/v6/o08/predictions | Plan futur et prévision/abstention immuable horodatée |
| GET /api/v6/o08/learners/ID/export | Événements chronologiques, reçus serveur, prévisions et évaluations |
| DELETE /api/v6/o08/learners/ID | Effacement de la base active, avec trace d'audit minimale |

Les schémas JSON publiés sont o08-practice-v1, o08-plan-v1 et o08-consent-v1. Les pseudonymes ont la
forme learner_ suivie de seize caractères hexadécimaux aléatoires. L'identité réelle éventuelle doit
rester séparée et n'est pas collectée ici. L'adaptateur adapt_v3 prend le véritable contrat AttemptV3,
un pseudonyme fourni et la disponibilité de mesure : il refuse les données synthétiques et ne crée
aucune correspondance avec les concepts d'un modèle musical entraîné.

La suppression automatique est opportuniste à l'ouverture d'une opération, indépendamment de son
succès ensuite. Il n'y a pas de tâche de nettoyage quand l'application est arrêtée. Les sauvegardes
externes, la vérification humaine du consentement et une véritable autorisation par élève ne sont pas
gérées par le jeton administrateur local. Une mise en ligne nécessite ces travaux avant tout pilote public.

## Revue des correspondances de compétences

Un enseignant peut préparer un fichier conforme à MappingReview : dataset, concept source,
catégorie candidate, définition, preuves, version et statut. Pour une approbation, il faut identité,
qualification, date et preuves, à vérifier réellement par le responsable du projet.

```text
python scripts/review_skill_mapping.py REVUE.json --output ARCHIVE_DE_REVUE_VERSIONNEE.json
```

Le script valide la structure et refuse d'écraser un fichier existant. Il ne déclare pas qu'une revue
externe a eu lieu et n'active aucune correspondance dans les prévisions. Les listes approuvées restent
vides dans la livraison actuelle. La prochaine étape est une vraie revue musicale, puis une validation
du construit et de la mesure, puis une évaluation prédictive sur le domaine visé.

## Vérifications finales

```text
python -m pytest -q
node --check web/o08.js
node --check web/musician.js
git diff --check
```

Sur Windows, spécifier un répertoire temporaire unique si nécessaire. La vérification navigateur porte
sur l'interface réellement servie, ses deux sources, la révélation différée, les erreurs, le panneau
recherche et le format mobile effectif. Après modification de JS/CSS, recharger la page et conserver
un suffixe de version d'asset cohérent. Les versions de tests et les hashes Git/CI exacts sont consignés
dans la livraison ; ne pas inférer un succès à partir du seul lancement d'une commande.
