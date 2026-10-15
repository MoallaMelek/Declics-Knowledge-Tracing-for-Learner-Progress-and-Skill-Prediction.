# Oral français - environ cinq minutes

Bonjour. Mon objectif O08 est d'utiliser plusieurs séances musicales pour repérer des difficultés
qui se répètent et prévoir une performance ultérieure. Le logiciel doit aller plus loin qu'un simple
carnet, mais il doit rester honnête sur ce qu'il sait réellement mesurer.

Nous avons trois bases musicales. SingPAD porte sur le chant et les résultats de notes par concept.
Yousician porte sur l'ukulélé et permet de prévoir le score du prochain jour actif. AMME porte sur
l'apprentissage au clavier, avec un score de similarité mélodique par bloc. Ces nombres n'ont pas
tous la même signification. Nous n'appelons pas le score AMME un pourcentage de notes correctes.

Avant cette phase, nous avions corrigé un problème de dates dans SingPAD. Cette correction est
conservée : les 18 328 groupes utiles sont dans l'ordre, sans inversion. Les anciens résultats invalides
restent identifiés. Nous avons ensuite exécuté 36 nouveaux entraînements neuronaux, sur CPU,
avec trois découpages par apprenant. Les élèves de test ne servent pas à ajuster les poids.

Voici le rôle précis du Deep Learning. Le réseau reçoit les résultats précédents et l'exercice connu,
quand la base le permet. Un GRU conserve une mémoire de la suite. Il fournit une prévision pour
la prochaine tâche. Les compteurs, les labels et les dates du futur ne sont pas fournis comme résultats
d'entrée. Les tests vérifient qu'un changement futur ne peut pas modifier une prévision antérieure.

Nous avons aussi essayé de comprendre ce qui apporte réellement de l'information. Sur SingPAD,
le GRU complet est meilleur en moyenne que des agrégats qui oublient l'ordre et qu'une fenêtre de
seulement trois groupes. Retirer les embeddings de concepts à l'attention dégrade aussi la moyenne.
Ajouter les intervalles de temps déjà observés n'améliore pas systématiquement les résultats.

Un réseau doit être comparé à des concurrents sérieux. Nous avons donc ajouté des contrôles appris,
uniquement pour la recherche. Sur SingPAD, les réseaux choisis sur validation ont une log-loss moyenne
de 0,517925, contre 0,524188 pour le contrôle choisi sur validation. Plus cette perte est petite, mieux
les probabilités correspondent aux résultats. L'avantage existe ici, mais il est modeste et exploratoire.

Nous ne cachons pas les cas moins favorables. Sur Yousician et AMME, les contrôles simples restent
très compétitifs ou meilleurs. Nous avons ajouté neuf caractéristiques historiques Yousician, comme
la difficulté précédente, la diversité des exercices et le volume évalué. Cela ne donne pas de gain
moyen convaincant. Aucun modèle actif n'a été remplacé sur la base d'un bon score de test isolé.

Dans cette démonstration, nous utilisons un vrai parcours de test sélectionné sans regarder l'erreur.
D'abord, la page montre uniquement le passé. Elle résume les concepts suffisamment observés,
ceux dont les résultats varient et ceux qui manquent de données. Ensuite, ce bouton exécute le réseau
entraîné. Enfin seulement, ce second bouton révèle le résultat réel. Vous pouvez voir les erreurs,
même importantes. Ce n'est pas une animation utilisant des nombres inventés.

Les fragilités sont des descriptions transparentes. Il faut plusieurs groupes et assez de notes.
Le logiciel n'affirme pas qu'un code SingPAD est automatiquement une compétence piano. Nous
avons préparé un circuit de revue pour qu'un enseignant puisse vérifier ces correspondances.
Les suggestions reprennent uniquement un exercice connu dans le passé et lié au concept observé.
Nous ne prétendons pas encore qu'elles améliorent l'apprentissage.

La prochaine étape la plus importante est un pilote réel. Nous avons préparé les événements
pseudonymes, le consentement déclaré, les dates, la version du modèle, l'enregistrement immuable
de prévisions et la réception ultérieure des résultats. Pour l'instant, la prévision terrain s'abstient
tant que le contrat de mesure n'est pas validé. Nous devons travailler avec un enseignant et les autres
axes, puis évaluer une nouvelle cohorte. Le résultat actuel est une démonstration complète et vérifiable
du mécanisme O08, accompagnée d'une frontière claire entre ce qui est mesuré et ce qui reste à valider.
