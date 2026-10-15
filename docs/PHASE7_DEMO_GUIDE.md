# Démonstration professeur - cinq minutes

## Avant la séance

Lancer l'application locale et vérifier /web/o08.html. Les archives et exemples réels doivent avoir
été préparés ; aucun Colab permanent n'est nécessaire. Ouvrir SingPAD. Le professeur peut consulter
les valeurs du graphique dans le tableau et ouvrir le panneau technique au besoin.

## 0:00 à 1:00 - le passé disponible

Présenter le parcours réel de test. Les trois groupes antérieurs n'ont pas servi à ajuster les poids.
Expliquer que chaque point résume des notes réellement évaluées, pas une compétence cognitive.
Le prochain résultat ne figure pas dans la réponse reçue par cette page. Montrer les états : certains
concepts sont non évalués ou insuffisamment observés ; cette absence n'est pas un échec.

## 1:00 à 2:00 - une difficulté soutenue par l'évidence

Montrer le concept source 15 et ses résultats variables sur cet exemple. Les seuils de détection sont
consultables et provisoires. Le logiciel n'invente pas que le concept signifie rythme ou doigté piano.
Une prévision et un état descriptif seront présentés séparément. Il est acceptable qu'un concept ne
déclenche pas de fragilité : l'exemple n'est pas sélectionné pour produire artificiellement une alerte.

## 2:00 à 3:00 - le rôle précis du Deep Learning

Cliquer Lancer la prévision Deep Learning. Le réseau GRU entraîné lit l'historique et l'exercice connu.
Il produit une probabilité de réussite d'une note par concept. Ouvrir le panneau technique : entrée
[1,4,1080] pour les trois groupes et la requête de cet exemple SingPAD, 4K variables avec K=270.
Ce n'est pas une analyse audio en direct ni une simulation animée.

## 3:00 à 4:00 - révéler sans cacher l'erreur

Cliquer Révéler le résultat réel. Montrer les écarts, même importants : le concept 15 est prévu vers
85,5 % et observé à 40 % dans ce groupe. Il s'agit d'une fréquence agrégée d'un petit nombre de notes,
pas d'une preuve que le modèle se trompe de la même façon sur toute la population. L'exemple a été
choisi de façon déterministe avant lecture de l'erreur ; son observation n'est pas une entrée du calcul.

## 4:00 à 5:00 - proposer et situer scientifiquement

La suggestion reprend un exercice réellement présent dans le passé et contenant le concept concerné.
L'identifiant n'est pas une partition distribuée ; le contenu appartient à la source. Le bénéfice d'une
telle recommandation reste à tester. Ouvrir la recherche : réseaux SingPAD 0,517925 contre contrôles
0,524188, mais pas de supériorité moyenne sur Yousician/AMME. Expliquer la prochaine étape : contrat
de mesure et taxonomie revus avec un enseignant, puis un pilote consenti avec prévisions enregistrées
avant résultats. Si on passe à Yousician, parler d'un score du prochain jour actif, jamais d'une note piano.

## Incidents prévus

Après un redémarrage, recharger pour renouveler le reçu signé. Si un exemple manque, reconstruire
les données locales ; ne pas saisir des résultats inventés. Si un domaine est incompatible, montrer
l'abstention. Si aucun exercice adapté n'est connu, présenter l'absence de suggestion comme un résultat.
