# DÉCLIC O08 - dossier scientifique et soutenance

## Question et portée

Peut-on prévoir une prochaine performance musicale à partir de résultats observés dans plusieurs
séances, et repérer des concepts dont les résultats restent fragiles ? Nous évaluons des cibles propres
à chaque base. Un score prédit n’est ni une mesure identifiée de maîtrise cognitive ni une preuve
d’amélioration de l’apprentissage grâce au logiciel.

Les trois tâches sont distinctes : moyenne du score mélodique AMME au prochain bloc ; probabilité
de réussite d’une note de chant par concept au prochain groupe d’enregistrements SingPAD ; fraction
de notes/accords réussis au prochain jour actif Yousician. Le fuseau SingPAD n’est pas connu et n’est
pas inventé. Les concepts codés de la source ne sont pas renommés « rythme », « justesse » ou
« compétences piano » sans validation. `configs/source-skill-mapping.json` conserve les correspondances
validées vides.

## Correction du défaut temporel

La Phase 5 triait des chaînes non complétées de zéros : 2023/8/10 pouvait précéder 2023/8/7.
340 parcours sur 1 042 étaient concernés, avec 478 inversions entre groupes voisins. Les résultats
SingPAD Phase 5 restent archivés comme exécutés mais méthodologiquement invalides.

La Phase 6 analyse explicitement l’année, le mois, le jour, l’heure, les minutes et les secondes
optionnelles. Elle accepte les formats année/mois/jour ou année-mois-jour, séparateur heure espace
ou T, rejette les dates invalides, les formats ambigus et les fuseaux non documentés. Les dates
équivalentes sont regroupées après conversion ; les chaînes originales restent dans le cache privé.
L’audit reconstruit vérifie zéro inversion et zéro doublon de groupe sur les 18 328 groupes utiles.
Le schéma `musical-cloud-v2` et le prétraitement `singpad-datetime-v2` empêchent de reprendre les
anciens checkpoints. Le registre rejette tous les modèles SingPAD v1, même demandés directement.

## Représentation et formulation

Pour un groupe temporel t et un concept k, n(t,k) est le nombre de notes observées et s(t,k) leur
nombre de réussites. Le réseau prévoit p(t,k) à partir des groupes strictement antérieurs et, pour
les modèles enrichis, de l’exercice connu à t. La perte binaire pondérée est :

L = somme[-s(t,k) log p(t,k) - (n(t,k)-s(t,k)) log(1-p(t,k))] / somme n(t,k).

Calculer la perte sur la fraction s/n, pondérée par n, est équivalent à utiliser toutes les notes
individuelles avec une même probabilité par concept et groupe. Le Brier, ROC-AUC et PR-AUC sont
également calculés avec les effectifs de réussites/échecs. Les tests comparent ces formules aux labels
individuels développés. MAE/RMSE des fractions agrégées sont distinctes de MAE/RMSE par note ;
`mae_note` et `rmse_note` explicitent cette différence.

AMME et Yousician utilisent une erreur quadratique sur un score continu entre 0 et 1. Chaque bloc
ou jour a un poids égal. Les compteurs de notes servent à construire le score du jour, pas à donner
plus de poids aux jours longs dans cette tâche. AMME scoretype 7 est une similarité mélodique
ajustée par couverture, pas un pourcentage de notes correctes.

L’entrée enrichie contient les résultats du groupe précédent et les cumuls de réussites/échecs
strictement antérieurs, transformés par log(1+n). La dimension vaut 4K. Les embeddings d’exercice
utilisent un vocabulaire d’entraînement uniquement. La difficulté est nulle dans cette adaptation
Phase 6 ; aucune difficulté future, durée future ou choix futur de morceau n’est fourni.

## Pourquoi GRU et Knowledge Tracing ?

Un GRU entretient une mémoire récurrente des observations passées. Contrairement à une moyenne,
il peut représenter un ordre, des changements récents et des interactions entre concepts et exercices.
Cette capacité ne garantit pas qu’elle soit utile sur chaque base. Notre DKT est une adaptation
GRU de Knowledge Tracing, pas une reproduction exacte du DKT LSTM original. L’attention est une
adaptation causale existante, pas une reproduction exacte de simpleKT ou AKT.

Les données soutiennent une utilité prédictive sur SingPAD : la log-loss moyenne des architectures
choisies sur validation vaut 0,517889, contre 0,540504 pour la meilleure référence historique choisie
sur validation dans chaque répétition. Elles ne démontrent pas une supériorité universelle : Yousician
et AMME ne dépassent pas les contrôles forts en moyenne. Les quatre ablations ne montrent pas
un bénéfice systématique de chaque ajout ; retirer les cumuls ou les items peut améliorer un résultat.
On ne peut donc pas affirmer que tous ces composants sont nécessaires.

## Validation et incertitude

Les graines 42, 17 et 83 définissent trois découpages par apprenant. Dans chacun, les ensembles
d’entraînement, validation et test sont disjoints. Les poids et l’architecture sont choisis sur validation.
Les cinq contrôles prédéfinis sont : moyenne d’entraînement, dernier score, moyenne des trois derniers
groupes, moyenne exponentielle alpha 0,5 et fréquence historique avec pseudo-effectif 2. Ils voient
le même passé et les mêmes cibles. Aucun modèle classique appris n’est ajouté au produit.

Les intervalles percentiles à 95 % utilisent 1 000 tirages d’apprenants entiers. Les notes d’un élève
ne sont jamais tirées comme des élèves indépendants. Les écarts réseau-contrôle sont appariés sur
les mêmes tirages. Ces intervalles portent sur la perte du benchmark, conditionnellement aux poids
et au découpage, pas sur une prévision individuelle. Les répétitions partagent parfois des élèves :
leur écart-type ne justifie pas un test comme trois populations indépendantes.

Les analyses exposent les historiques 1-2, 3-9 et 10+ groupes, les concepts fréquents/rares, les
exercices inconnus et les plages de scores observées. Les concepts n’ont un bilan séparé qu’avec
au moins 10 apprenants et 100 notes. Le tableau de calibration compare probabilité moyenne et
fréquence observée par tranche disjointe. Il n’implique pas une calibration parfaite.

Les analyses de plages de score utilisent le résultat observé : ce sont des diagnostics après coup,
pas des critères disponibles avant la prévision. La longueur d’historique n’est pas une mesure validée
du niveau débutant/expert. Le serveur s’abstient sur les exercices inconnus, même si leur slice UNK
est décrite dans l’évaluation hors ligne.

## Estimer une fragilité sans inventer une maîtrise

Le module descriptif calcule les résultats historiques et récents, les groupes temporels observés,
le poids d’évaluation, la couverture des exercices et une tendance récente moins antérieure quand
il y a assez d’historique. Ces valeurs sont présentées séparément des probabilités du réseau.

La règle descriptive est publiée : au moins trois groupes distincts, au moins dix notes pour SingPAD,
des résultats non parfaits dans au moins deux groupes, et une fraction récente inférieure à 0,65
sur les trois derniers groupes observés. Les seuils sont des conventions de démonstration, pas un
seuil clinique ou pédagogique validé. Les états distinguent non évalué, preuve insuffisante, résultats
observés sans signal récurrent et résultats faibles récurrents. Cent notes d’un seul enregistrement
ne deviennent pas cent séances. Les suggestions reprennent des exercices déjà évalués sans promettre
de gain causal. AMME/Yousician conservent un bilan de score global, pas des compétences inventées.

## Questions difficiles - réponses courtes

**Pourquoi Deep Learning ?** Pour tester une représentation des séquences et interactions musicales.
Son intérêt doit être mesuré : SingPAD le soutient dans ce protocole ; les autres bases le limitent.

**Pourquoi GRU ?** Il est déjà implémenté, compact et adapté à des parcours ordonnés. Trois
architectures ont été comparées. Le choix primaire est fait sur la validation, pas sur la complexité.

**Pourquoi pas une régression ?** Elle pourrait être un contrôle appris supplémentaire. Cette phase
respecte la contribution DL et commence par cinq contrôles historiques causaux ; elle ne prétend
pas avoir épuisé tous les modèles classiques. Une régression non exécutée n’est pas présentée comme battue.

**Comment éviter la fuite ?** Dates analysées, égalités regroupées, apprenants séparés, labels du
groupe cible exclus des entrées, vocabulaires appris sur l’entraînement, tests de changement de futur.

**Le modèle généralise-t-il ?** Les tests portent sur des personnes absentes de l’entraînement dans
ces bases. Ils ne démontrent pas un transfert à une école, un professeur ou un autre instrument.

**Que veut dire une prévision ?** Une cible, un horizon, un instrument et une échelle explicités.
Yousician prévoit le prochain jour actif, pas la date de retour ni un exercice précisément choisi.

**Les probabilités sont-elles fiables ?** Le Brier, la log-loss et la calibration sont publiés. La
fiabilité individuelle et les situations de changement de domaine ne sont pas établies.

**Pourquoi pas l’ukulélé vers le piano ?** Instrument, exercices et labels changent. Il faut des
données piano objectives et une nouvelle validation, pas seulement modifier un nom dans l’API.

**Que manque-t-il pour un vrai déploiement ?** Validation temporelle prospective, données piano,
taxonomie approuvée par un enseignant, contrôle d’accès et consentement, suivi des dérives et de
l’efficacité pédagogique, surveillance et politique de réentraînement.

## Présentation orale - environ une minute

« Mon axe utilise plusieurs séances pour prévoir une performance future et décrire les difficultés
observées. J’ai corrigé un défaut de dates SingPAD, refait trois architectures et vérifié zéro inversion
chronologique. J’ai comparé les réseaux à cinq méthodes historiques sur trois découpages, avec
des intervalles calculés par apprenant. Sur SingPAD, les réseaux améliorent la log-loss face au
contrôle historique. Sur Yousician, la référence simple est légèrement meilleure ; AMME reste trop
petit pour une activation. L’application montre un vrai parcours de test, masque les résultats futurs,
explique la quantité de preuves et distingue une difficulté répétée d’un historique insuffisant.
Je ne présente pas ces résultats comme une validation pour tous les instruments ni comme une preuve
que les élèves apprennent mieux grâce au système. »

## Plan de présentation en six diapositives

1. Problème : historique de séances vers fragilités observées et performance suivante.
2. Données : trois bases, trois cibles distinctes, pas de taxonomie universelle inventée.
3. Réparation : mauvais tri de dates, zéro inversion après conversion, anciens modèles invalidés.
4. Expériences : trois graines, trois architectures SingPAD, cinq contrôles, quatre ablations.
5. Démonstration réelle : passé disponible, prévision, résultats cachés puis révélés, limites.
6. Conclusion scientifique : intérêt démontré dans un protocole SingPAD ; résultats négatifs
   transparents ailleurs ; validation pédagogique et piano restent à construire.

## Références primaires et sources

- Piech et al., Deep Knowledge Tracing : https://arxiv.org/abs/1506.05908
- Zhang et al., SingPAD (EDM 2024) : https://doi.org/10.5281/zenodo.12729828
- Chmiel et al., AMME (2025) : https://doi.org/10.1371/journal.pone.0320055
- Données AMME : https://doi.org/10.17605/OSF.IO/2GVTY
- Yousician Open Data : https://yousician.com/open-data
- PyTorch GRU : https://docs.pytorch.org/docs/stable/generated/torch.nn.GRU.html
- Les résultats de ce projet proviennent des artifacts Phase 6 ; aucun score d’article externe n’est
  utilisé comme un résultat DÉCLIC.
