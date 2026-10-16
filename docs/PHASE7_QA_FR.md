# Questions techniques et réponses pour la soutenance

## Où est le Deep Learning ?

Dans la prévision : le GRU met à jour une mémoire de la suite des résultats antérieurs. Sa sortie
est un score ou une probabilité pour la prochaine cible. Les états de fragilité et les suggestions
sont ensuite des règles explicites ; nous ne les présentons pas comme un autre réseau entraîné.

## Pourquoi ne pas se contenter d'une moyenne ?

Il faut justement le vérifier. Les moyennes sont très compétitives sur AMME et Yousician. Sur les
splits SingPAD explorés, les réseaux sélectionnés gardent un petit avantage contre des contrôles
appris plus exigeants : 0,517925 contre 0,524188 de log-loss. Nous ne généralisons pas ce gain à toutes
les bases et ne promouvons pas un modèle simplement parce qu'il a le meilleur score de test.

## Qu'est-ce qui empêche le réseau de voir le futur ?

Les observations du groupe t ne sont encodées que pour les prévisions suivantes. Les cumuls sont
calculés avant l'observation cible ; les dates identiques sont groupées. L'exercice connu peut être
une entrée de requête, son résultat ne l'est pas. L'attention possède un masque causal. Les tests
modifient les labels futurs et vérifient que les sorties antérieures ne changent pas.

## Le navigateur connaît-il déjà le résultat réel ?

L'ancienne démonstration v5 conservée pour compatibilité renvoyait prévision et résultat dans une
même réponse, en cachant visuellement le résultat. Le nouveau parcours v6 est plus strict : history
et predict ne contiennent pas observed_target ; reveal nécessite un reçu signé après la prévision.
Cette séparation est testée. Le serveur possède l'exemple rétrospectif, mais le tenseur ne contient
jamais sa cible. Ce n'est pas encore une expérience prospective auprès d'un élève.

## Les concepts SingPAD sont-ils des compétences piano ?

Non. Ce sont des identifiants propres à la base de chant. Les catégories rythme, hauteur, timing,
coordination et technique sont des propositions de taxonomie. Aucune correspondance piano n'est
approuvée ou activée. Une définition musicale et une mesure compatible doivent être revues avant
d'interpréter un concept, puis un modèle doit être validé dans le domaine piano visé.

## Un score de 80 % veut-il dire 80 % de maîtrise ?

Non. SingPAD prévoit une probabilité de réussite de note dans une tâche comparable. Yousician
prévoit une fraction quotidienne de notes et accords réussis. AMME prévoit une similarité mélodique
continue. Aucun de ces nombres n'est automatiquement un pourcentage de maîtrise cognitive.

## Comment une fragilité est-elle décidée ?

La politique est publiée : trois groupes et dix notes au minimum pour SingPAD ; deux des trois
résultats récents sous 65 % et moyenne récente sous 65 % pour une faiblesse répétée. Une variabilité
demande 30 points d'étendue récente. Les tendances demandent au moins six groupes au total.
Ces seuils décrivent des observations et attendent une validation pédagogique ; ils ne sont pas
présentés comme des normes empiriquement prouvées.

## Pourquoi garder un mauvais exemple dans la démonstration ?

Parce que le choisir après lecture de son erreur serait trompeur. Le premier cas éligible est sélectionné
par une règle déterministe, sans son résultat. Une probabilité élevée peut être suivie d'une faible
fréquence sur quelques notes. Le tableau montre cet écart, tandis que l'évaluation globale utilise
les vrais poids de notes sur tous les exemples de test.

## La chronologie apporte-t-elle quelque chose ?

Dans le protocole SingPAD, le GRU complet donne 0,517819 en moyenne, contre 0,520368 pour les
agrégats sans ordre et 0,521618 pour les seuls trois groupes récents. C'est un résultat de représentation
prédictive, pas une preuve causale sur l'apprentissage. La capacité et les entrées diffèrent ; aucune
permutation ne place une observation future dans le passé.

## Pourquoi ajouter des modèles classiques si le projet doit utiliser du Deep Learning ?

La Phase 7 demande des contrôles scientifiques sérieux. Ils sont utilisés hors produit pour vérifier
la valeur ajoutée du réseau, et ne sont pas activés dans l'inférence musicale. PFA, régression logistique,
Ridge et arbres boostés évitent de comparer le réseau uniquement à une référence trop faible.

## Est-ce que les données manquantes sont remplacées par des données synthétiques ?

Non. Les stress tests cachent des observations antérieures et conservent les mêmes labels cibles.
La performance se dégrade notamment quand les groupes récents manquent. Les compteurs Yousician
contradictoires restent exclus ; leurs alternatives servent à des diagnostics descriptifs, pas à fabriquer
un résultat final fiable.

## La calibration garantit-elle une meilleure probabilité ?

Non. La température est ajustée uniquement sur validation puis testée. Elle améliore certains cas,
mais dégrade la graine 83 sélectionnée. Une ECE dépend du découpage en tranches et du poids des notes.
Une meilleure log-loss peut coexister avec un Brier légèrement moins bon. Aucun intervalle individuel
n'est inventé à partir de ces métriques de population.

## Que représente l'incertitude affichée ?

Trois informations distinctes : manque d'évidence pour décrire un parcours ; incompatibilité de domaine
qui déclenche une abstention ; incertitude statistique de benchmark, conditionnelle à ses modèles.
Les bootstrap d'apprenants Phase 6 ne décrivent pas l'intervalle d'une prévision particulière et ne
sont pas réutilisés comme si nous les avions calculés pour les nouveaux poids Phase 7.

## Pourquoi ne pas entraîner sur une masse de données générées ?

Un simulateur pourrait tester la mécanique logicielle, mais il ne crée pas de nouvelles preuves sur
de vrais musiciens. Les 59 apprenants AMME ne sont pas remplacés par des copies synthétiques. Le
pilote réel doit produire de nouvelles mesures avec consentement et avec la prévision stockée avant
le résultat. Les fixtures de tests unitaires sont explicitement des tests, pas des résultats scientifiques.

## Que manque-t-il pour des élèves réels ?

Un contrat de mesure vérifié avec les autres axes, une taxonomie revue, des règles de consentement
opérationnelles et un modèle évalué sur cette population. La collecte technique est prête, mais reste
en abstention pour la prédiction terrain. Un jeton administrateur local ne suffit pas à assurer une
authentification multi-utilisateur ni un déploiement Internet sécurisé.

## Comment vérifier et reprendre le travail ?

Lire les résultats JSON, leurs empreintes, les splits et le guide de reproduction. Chaque ensemble
de poids est associé à sa configuration et aux métriques réellement calculées. Les optimiseurs,
curseurs et caches restent privés. Les notebooks Phase 6 conservent les checkpoints Drive et la
reprise sûre. Les nouveaux runs ont été exécutés localement ; aucune session cloud permanente
n'est nécessaire pour la démonstration.
