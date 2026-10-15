# Phase 5 — entraînement musical et Google Colab

Les notebooks utilisent les mêmes chargeurs et modèles PyTorch que le projet.
Ils installent automatiquement les dépendances, détectent le GPU, et fonctionnent
aussi sur CPU. Aucun achat ou abonnement n'est requis. Les ressources gratuites
Colab ne sont pas garanties et une session peut être interrompue.

## Lancer

Pour éviter la limite de sessions gratuites, le [notebook des trois bases](https://colab.research.google.com/github/MoallaMelek/Declics-Knowledge-Tracing-for-Learner-Progress-and-Skill-Prediction./blob/phase5/colab-musical-training/notebooks/DECLIC_all.ipynb)
enchaîne SingPAD, AMME et Yousician sur un seul GPU. Les sorties restent séparées
par base et architecture. Les écritures Drive sont transférées avant la fin.
Le montage Drive dispose d'un délai de dix minutes et d'une reprise après une
erreur temporaire. Un montage déjà actif est conservé.

1. Ouvrir [AMME](https://colab.research.google.com/github/MoallaMelek/Declics-Knowledge-Tracing-for-Learner-Progress-and-Skill-Prediction./blob/phase5/colab-musical-training/notebooks/DECLIC_amme.ipynb),
   [SingPAD](https://colab.research.google.com/github/MoallaMelek/Declics-Knowledge-Tracing-for-Learner-Progress-and-Skill-Prediction./blob/phase5/colab-musical-training/notebooks/DECLIC_singpad.ipynb) ou
   [Yousician](https://colab.research.google.com/github/MoallaMelek/Declics-Knowledge-Tracing-for-Learner-Progress-and-Skill-Prediction./blob/phase5/colab-musical-training/notebooks/DECLIC_yousician.ipynb).
2. Choisir un GPU gratuit dans **Exécution → Modifier le type d'exécution**, s'il
   est disponible. Cliquer **Tout exécuter** et autoriser Drive quand Google le demande.
3. Au premier lancement seulement, fournir l'archive demandée, ou la déposer dans
   `Mon Drive/DECLIC/datasets/`. Le notebook la retrouve aux prochains lancements.

Archives attendues : `2gvty-osfstorage-archive.zip`, `singKT-dataset-main.zip`,
`yousician_ukulele.json.zip`. Le JSON Yousician est lu progressivement ; il n'est
pas nécessaire de l'ouvrir dans un éditeur. Les sources sont citées dans les sorties.
L'utilisateur a confirmé l'autorisation de réutilisation des données pour ce projet.

## Reprise et résultats

Les sorties sont dans `Mon Drive/DECLIC/phase5/SOURCE/seed-42/MODELE/`.
Chaque sauvegarde conserve les paramètres du modèle, l'optimiseur, le curseur
de minibatch, les états aléatoires PyTorch et les meilleurs paramètres de validation.
Elle intervient toutes les 25 minibatches, après deux minutes entre minibatches,
et à chaque époque. Deux générations vérifiées par SHA-256 sont conservées.
Le manifeste est remplacé après l'écriture du checkpoint. Une interruption lors
d'une écriture permet de revenir à la génération précédente intacte.

Relancer les mêmes cellules suffit. Modifier les données, l'architecture, les
paramètres du découpage ou la taille des minibatches provoque un refus de reprise,
plutôt qu'un mélange d'expériences. Utiliser un autre dossier pour un autre essai.
Augmenter `EPOCHS` prolonge l'entraînement, sauf si l'arrêt précoce est atteint.
La reproductibilité bit à bit est testée sur CPU ; changer de GPU/version PyTorch
peut produire des différences numériques. Ne pas lancer deux sessions écrivant
dans le même dossier. Drive doit avoir assez d'espace et rester autorisé.

`history.json` contient les résultats par époque ; `metrics.json` et `metrics.csv`
contiennent les vrais résultats de validation/test. Le paquet portable contient
`model.pt`, ces métriques et l'historique ; il ne contient pas les observations
brutes, les identifiants des apprenants ou l'optimiseur. La provenance publique
du découpage contient seulement des effectifs et empreintes de groupes. Les listes
d'identifiants restent dans les caches et checkpoints privés, sur Drive ou en local.

Pour importer le paquet téléchargé :

```text
python -m axis7.musical_registry import --bundle CHEMIN/source-benchmark-bundle.zip
python -m axis7.musical_registry list
```

L'import refuse les chemins d'archive inattendus, doublons, fichiers trop grands,
checksums incohérents, configurations incompatibles, empreintes de découpage incohérentes et
modèles qui n'ont pas passé le seuil de validation.
Un import accepté devient le modèle actif de sa base. Les anciennes versions
restent archivées ; l'interface affiche seulement la version active par base.

## Cibles et protocoles

| Base | Unité entièrement cachée | Cible | Modèles |
|---|---|---|---|
| AMME | Bloc de mesures | Moyenne du scoretype 7 au prochain bloc | EnhancedGRU, sortie continue |
| SingPAD | Enregistrement ; mêmes horodatages regroupés | Réussite des notes par concept de la source | DKT GRU, EnhancedGRU, attention causale existante |
| Yousician | Jour depuis l'inscription | Fraction de notes/accords réussis au prochain jour **actif** | EnhancedGRU, sortie continue |

AMME : le scoretype 7 est une similarité de hauteur ajustée par la couverture
alignée, pas un pourcentage de notes correctes. Les huit métriques d'une même
performance ne sont pas huit essais. L'ordre à l'intérieur du bloc n'étant pas
documenté, aucun résultat du même bloc n'est accessible à la prévision.
Ce choix prudent réduit la quantité de cibles.

SingPAD : la liste des notes est reliée aux concepts publiés dans `opernDS.csv`.
Aucune conversion vers les six compétences génériques DÉCLIC n'est inventée.
Les moyennes globales `userDS`/`opernDS` ne servent pas de variables d'entrée.
Les notes d'un enregistrement ne s'enseignent pas mutuellement avant sa prévision.
32 apprenants n'ont pas deux groupes temporels distincts et sont exclus de cette
tâche de prévision historique ; le rapport contient les effectifs réellement utilisés.

Yousician : les doublons exacts sont retirés. Les compteurs globaux répétés entre
parties d'un exercice sont comptés une fois. Les groupes dont les compteurs
diffèrent sont exclus et comptabilisés dans l'audit. Les séances `practice` et les
groupes sans évaluation ne servent pas de labels. Aucun ordre entre parties
simultanées n'est inventé. Le mélange d'exercices, la difficulté et la durée du
jour futur ne sont pas des entrées disponibles ; ce modèle prévoit un score
global du prochain jour actif, pas celui d'un exercice choisi à l'avance.

Le protocole implémenté est **nouveaux apprenants** : 70 % entraînement,
15 % validation, 15 % test, sans chevauchement, graine 42. À l'intérieur de chaque
parcours de validation/test, les résultats déjà observés conditionnent les
prévisions suivantes, sans mettre à jour les poids. La première unité sans
historique n'est pas notée. Les fenêtres ont au plus 64 groupes et gardent les
comptages de tout le passé. Le protocole « séances futures des apprenants connus »
est distinct et n'est pas revendiqué par ces métriques.

La sélection utilise seulement la validation ; les résultats test ne choisissent
ni époque ni architecture. Le seuil d'importation exige une amélioration sur la
moyenne d'entraînement et au moins 30 cibles en validation/test. Cette règle est
un contrôle technique, pas une preuve de validité pédagogique ni une certification
scientifique. Un seul découpage/graine, sans intervalle de confiance, est disponible.
La moyenne constante est une référence descriptive ; aucun nouveau modèle
classique n'est entraîné. Les anciennes expériences Phases 1–4 restent conservées.

## Intégration

`GET /api/v5/musical/models` liste les modèles importés et vérifiés.
`POST /api/v5/musical/forecast` utilise une histoire publique explicitement
structurée, sans écrire dans le carnet personnel. Les blocs/jours continus doivent
avoir une ligne agrégée de poids 1 ; SingPAD reçoit les résultats binaires des notes.
Les groupes égaux ou postérieurs au temps de requête sont cachés. L'instrument,
la cible, les concepts, les exercices connus et le nombre de groupes sont contrôlés.

L'interface [Recherche · modèles réels](/web/musical-cloud.html) présente les
résultats et les liens Colab. `/api/v4/forecast` conserve son abstention pour le
carnet piano : ses auto-évaluations ordinales ne sont pas compatibles avec ces
labels externes. On n'annonce donc ni validation ukulélé→piano, ni « maîtrise ».

## Sources

- Chmiel et al. (2025), [article AMME](https://doi.org/10.1371/journal.pone.0320055), [données OSF](https://doi.org/10.17605/OSF.IO/2GVTY).
- Zhang et al. (2024), [SingPAD, EDM](https://doi.org/10.5281/zenodo.12729828).
- [Yousician Open Data](https://yousician.com/open-data).
- [Colab FAQ](https://research.google.com/colaboratory/faq.html) pour les interruptions,
  autorisations Drive et limites des ressources gratuites. Google propose aussi
  [Colab MCP](https://github.com/googlecolab/colab-mcp) et [Colab CLI](https://github.com/googlecolab/google-colab-cli),
  mais le projet ne dépend pas d'un pont connecté en permanence.
