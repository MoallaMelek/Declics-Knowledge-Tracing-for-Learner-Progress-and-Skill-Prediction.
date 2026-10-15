# Phase 6 - reproduction et exploitation

Branche : `phase6/scientific-validation`. Aucun merge vers main.

## Exécuter les expériences fixées

Les trois archives restent privées. Exemples depuis la racine du projet :

```text
python scripts/run_phase6_experiments.py --source singpad --archive CHEMIN/singKT-dataset-main.zip --output artifacts/models/phase6/singpad --seeds 42 17 83 --ablations
python scripts/run_phase6_experiments.py --source amme --archive CHEMIN/2gvty-osfstorage-archive.zip --output artifacts/models/phase6/amme --seeds 42 17 83
python scripts/run_phase6_experiments.py --source yousician --archive CHEMIN/yousician_ukulele.json.zip --output artifacts/models/phase6/yousician --seeds 42 17 83
python scripts/report_phase6.py
```

Le protocole est dans configs/phase6-experiments.json, publié avant les résultats. Les cibles et
les choix d’époque/architecture utilisent la validation. Les ablations sont des expériences séparées,
pas des modèles promus selon le test. Les sorties CPU et GPU restent distinctes.

## Colab et versions

Les quatre notebooks utilisent la branche Phase 6. Les expériences réellement exécutées décrites
ici sont dans Drive DECLIC/phase6. Les nouveaux lancements utilisent DECLIC/phase6-EMPREINTE-CODE
pour ne pas reprendre accidentellement une ancienne version. Un clone
déjà présent n’est pas mis à jour silencieusement. Pour changer de version de code, utiliser une
session/dossier d’expérience neuf. La révision exécutée et les versions Python, torch et numpy
sont dans les rapports. Le pip freeze complet est privé sur Drive. Les versions principales
observées au réentraînement Colab sont fixées dans configs/colab-constraints.txt ; le torch installé
peut garder son suffixe CUDA local. Les ressources et versions Python proposées par Colab restent
externes : une résolution impossible doit échouer explicitement, pas changer discrètement le protocole.

Les notebooks ajoutent l’analyse des contrôles, le bootstrap et un export par architecture contenant
model.pt, metrics.json, metrics.csv, history.json et analysis.json. Ils transfèrent les écritures Drive
en fin de travail. Les sauvegardes privées incluent optimiseur/curseur/RNG, deux générations avec
empreintes et une reprise depuis une génération intacte. Après une sauvegarde récente corrompue,
la sauvegarde suivante conserve le dernier backup réellement intact. Ce cas est testé.

La reprise exacte est prouvée sur CPU dans le test d’interruption au milieu d’une époque. La reprise
des futurs checkpoints vérifie aussi les empreintes des fichiers source chargés. Les rapports historiques
enregistrent parfois le HEAD Git au moment de leur écriture, après d’autres modifications API/UI ;
`artifacts/phase6/execution-provenance.json` précise cette limite et la révision de lancement. Les nouveaux
champs d’empreinte du code ne sont pas attribués rétroactivement aux anciennes expériences. La reprise
des expériences terminées a aussi été exécutée sur Colab à l’époque 12 pour produire les analyses.
Ce n’est pas un test de coupure volontaire GPU au milieu d’un minibatch. Les différences numériques
entre CPU et GPU sont documentées ; elles ne justifient pas de remplacer une mesure par l’autre.

## Import et abstention

```text
python -m axis7.musical_registry import --bundle CHEMIN/singpad-enhanced_gru-phase6-bundle.zip
python -m axis7.musical_registry list
```

SingPAD v1 est toujours refusé. Un modèle SingPAD corrigé doit présenter l’audit temporel, le seuil
initial et une amélioration sur le meilleur contrôle historique de validation. Le modèle actif est choisi
sur validation, pas sur test. La première version GPU corrigée active est EnhancedGRU graine 42.
Les poids AMME restent recherche seulement. Yousician Phase 5 est conservé, avec comparaison
historique recalculée sur ses poids et les mêmes données ; aucune supériorité au contrôle fort annoncée.

Les modèles d’inférence sont mis en cache, mais les empreintes de poids, de rapport et d’analyse
invalident le cache en cas de changement. Un modèle non actif ne peut pas être appelé directement.
L’API v4 et le carnet piano conservent leurs restrictions. L’API v5 précise cible, horizon, échelle,
instrument, version et provenance non authentifiée d’un historique soumis par le client.

## Démonstration reproductible privée

```text
python scripts/build_musical_demo.py --source singpad --archive CHEMIN/singKT-dataset-main.zip
python scripts/build_musical_demo.py --source yousician --archive CHEMIN/yousician_ukulele.json.zip
```

Le script vérifie l’archive et les empreintes du découpage du modèle actif. Il prend le premier
apprenant de test avec trois groupes antérieurs et une requête d’exercice supportée ; il ne choisit
pas un exemple selon l’erreur ou l’effet visuel. Les données de l’exemple sont dans runtime/, ignoré
par Git. Les noms d’apprenants ne sont pas exposés ; l’API ne renvoie pas le payload brut de notes.
Le résultat du groupe cible est montré après la prévision, sans entrer dans le calcul.

Ouvrir /web/musical-demo.html. Le mode recherche est /web/musical-cloud.html.
Une absence d’archive/démonstration retourne 503 ; aucun historique fictif ne la remplace.

## Contrôles

```text
python -m pytest -q
node --check web/musical-demo.js
node --check web/musical-cloud.js
git diff --check
```

Sur Windows, un dossier temporaire explicite peut être requis par l’environnement. Les sorties
publiques contiennent effectifs et empreintes des splits, pas des identifiants individuels. Caches,
checkpoints d’optimiseur, archives et runtime sont ignorés. Aucune donnée brute ne doit être ajoutée
par git add global ; sélectionner explicitement les changements du projet.
