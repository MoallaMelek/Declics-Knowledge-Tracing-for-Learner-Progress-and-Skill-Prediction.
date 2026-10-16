# Vérifications de livraison Phase 7

## Tests et régressions

La suite complète locale a réussi 315 tests en 24,22 secondes. Un avertissement de dépréciation
Starlette/httpx demeure ; il n'est pas présenté comme un échec de test. Les tests couvrent notamment
la causalité des caractéristiques, l'équivalence des sorties/gradients de l'attention optimisée,
la provenance de rapports réutilisés, les nouveaux états, la taxonomie non approuvée, le ledger
prospectif, l'idempotence, l'absence de fuite de résultats futurs, les contrôles d'accès et de taille,
la rétention même après refus, les suppressions et les régressions des APIs historiques.

La syntaxe des interfaces est vérifiée localement et la CI inclut désormais web/o08.js. La CI finale,
le SHA effectivement livré et la date de génération sont indiqués sur la couverture du PDF. Le statut
de la CI est vérifié après le push ; aucun merge main n'est effectué. Les dossiers personnels non liés
au projet, déjà présents dans le checkout, sont exclus des commits.

## Vérifications scientifiques et artefacts

Les 33 réseaux principaux et les trois extensions Yousician ont terminé. Les trente-six ensembles
de poids sont exportés avec empreintes, métriques et paramètres. Les formats PyTorch state_dict
sont rechargés avec weights_only=True, leurs dimensions et leurs valeurs finies sont vérifiées.
Les splits et empreintes d'archives correspondent à la Phase 6 avant les comparaisons aux contrôles
historiques. Les métriques incluent les observations négatives et tous les hyperparamètres sont
choisis sur validation. L'entraînement dense d'attention interrompu est explicitement exclu.

Les tableaux détaillent 18 recalibrages SingPAD, trois analyses de manque de passé à quatre conditions,
les contrôles appris sur trois splits de trois bases et une CV externe AMME à cinq groupes d'apprenants.
Les compteurs de cibles restent identiques dans les stress tests. Les 270 concepts apparaissent tous
dans train pour les trois splits SingPAD : aucune mesure de concept naturellement nouveau n'est inventée.
L'audit d'exclusion Yousician retrouve les compteurs Phase 6 et ajoute les strates demandées.

## Démonstration et interface réellement contrôlées

Les deux instruments de la démonstration ont été utilisés dans le navigateur. La prévision SingPAD
et son résultat défavorable sont visibles ; le score Yousician prévu vaut environ 78,4/100 et son résultat
révélé environ 88,1/100. La prévision appelle les vrais poids actifs. Les réponses history/predict
n'envoient pas observed_target ; une demande reveal sans reçu de prévision est refusée.

Le navigateur a affiché la vue mobile à 391 pixels CSS effectifs, avec largeur de document 371 pixels
et aucun débordement horizontal, y compris après prévision et révélation Yousician. La vue bureau,
les six sections de recherche, les états descriptifs, les recommandations SingPAD et l'abstention de
recommandation Yousician ont été inspectés. Il ne s'agit pas d'un audit WCAG exhaustif ni d'une étude UX.

Un benchmark HTTP local de quinze requêtes par source mesure médiane chaude et p95 dans
artifacts/phase7/inference-benchmark.json. Il vérifie également le circuit complet en trois étapes.
La première requête mesurée n'est pas nécessairement froide. Aucun débit multi-utilisateur n'est revendiqué.

## Limites de l'acceptation finale

Le circuit O08 rétrospectif est démontrable. La collecte prospective peut enregistrer de vrais événements
avec consentement déclaré et isoler ce qui était disponible au moment d'une prévision. Le modèle
terrain reste en abstention tant que les mesures et leur domaine ne sont pas validés. Il n'y a donc
ni prévision prospective terrain validée, ni étude d'intervention, ni approbation d'un expert musical
à annoncer. La Phase 7 demeure partielle pour ces critères scientifiques et externes précis.
