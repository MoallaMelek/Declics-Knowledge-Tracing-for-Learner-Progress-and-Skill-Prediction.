# DÉCLIC Phase 7 - rapport scientifique et technique

## Objectif officiel O08

Utiliser plusieurs séances musicales pour estimer les fragilités soutenues par les observations et
prévoir une performance ultérieure. L'entrée est une suite de résultats, de concepts et d'exercices ;
la sortie distingue un bilan du passé, un état descriptif, une prévision statistique et une suggestion
de pratique. Une amélioration prédictive ne prouve ni une maîtrise cognitive ni un bénéfice pédagogique.

Cette livraison comprend 36 entraînements neuronaux CPU réellement terminés : 33 dans le programme
principal et trois dans une extension Yousician. Un entraînement dense d'attention interrompu après
cinq époques reste exclu des tableaux. Les 22 entraînements historiques de Phase 6 sont conservés
séparément : ils ne sont pas recomptés dans les 36 nouveaux entraînements.

## Référence réellement vérifiée

Le dépôt était sur phase6/scientific-validation, commit
40351233d5652be9c6c8e1af5f6ea79d0cee8361. Le SHA distant était identique et l'exécution CI
38747446308 était terminée avec succès. Le rapport PDF Phase 6 existe, avec 109 924 octets.
La nouvelle branche est phase7/personalized-musical-learning. Aucun merge vers main n'est réalisé.

Les 279 tests historiques annoncés sont corroborés par la CI Phase 6. La première suite locale de
Phase 7 a réussi 290 tests, comprenant les 279 précédents et 11 nouveaux tests scientifiques.
Une suite intermédiaire plus complète a ensuite réussi 311 tests. Le décompte final et la CI exacte
de livraison sont consignés dans le bilan de vérification ; un ancien décompte ne remplace pas ce contrôle.

Les fichiers de protocole AI_TEAM.md/AGENTS.md du projet et les modèles ~/.Codex/templates étaient
absents. Leur contenu n'a pas été inventé. Une revue indépendante en lecture seule a signalé quatre
points utiles : rétention annulée par rollback, cache scientifique insuffisamment vérifié, stress test
manquant après interruption, et clé de reçu non partagée entre workers. Les corrections sont décrites
ci-dessous et couvertes par des tests ciblés lorsqu'elles peuvent l'être localement.

## Bases, unités et limites de mesure

| Base | Apprenants utiles | Groupes utiles | Cible réellement prédite |
|---|---:|---:|---|
| AMME | 59 | 212 blocs | Moyenne du scoretype 7 au prochain bloc |
| SingPAD | 1 042 | 18 328 groupes temporels | Réussite d'une note par concept au prochain groupe |
| Yousician | 999 | 12 596 jours actifs | Fraction de notes et accords réussis au prochain jour actif |

AMME contient 4 184 lignes brutes ; trois apprenants avec un seul groupe sont exclus du modèle
longitudinal. Le scoretype 7 est une similarité mélodique ajustée par couverture, entre 0 et 1.
Il ne représente pas un pourcentage de notes correctes. Les blocs sont des unités ordinales ; leur
numéro n'est pas converti en durée d'apprentissage. AMME reste recherche seulement.

L'import SingPAD lit 19 892 enregistrements et 1 081 876 labels de notes avant le filtre longitudinal.
Les enregistrements de même date sont cachés ensemble ; les dates locales sont analysées avec le
prétraitement singpad-datetime-v2. L'audit confirme zéro inversion et zéro doublon de groupe sur les
18 328 groupes utiles. Les 270 indices de concepts apparaissent tous dans l'entraînement de chacun
des trois splits : aucun concept naturellement absent de l'entraînement n'est disponible ici pour
mesurer une généralisation à une compétence nouvelle. L'absence d'un concept dans l'historique
individuel est étudiée séparément et ne doit pas être appelée concept inconnu de l'entraînement.

Yousician contient 415 461 lignes brutes ; 478 doublons exacts et 31 275 lignes en mode practice sont
retirés. Les compteurs répétés entre parties ne sont comptés qu'une fois par groupe cohérent.
101 368 groupes sont retenus et 23 955 groupes contradictoires sont exclus, soit environ 19,1 %
des groupes pertinents. Un apprenant avec un seul jour est exclu du modèle longitudinal. Il n'existe
pas d'identifiant d'essai unique fiable : le prochain exercice individuel ne peut pas être reconstruit
sans supposition. La cible reste le prochain jour actif, sans prétendre prévoir le jour du retour.

## Programme expérimental

Les graines 42, 17 et 83 définissent les mêmes partitions par apprenant que la Phase 6. À l'intérieur
de chaque partition, entraînement, validation et test sont disjoints. Les partitions entre répétitions
peuvent partager des apprenants : l'écart-type n'est pas celui de trois populations indépendantes.
Les empreintes des splits, des archives et les nombres de cibles sont vérifiés avant toute comparaison.
Le protocole principal a été publié dans le commit 9641219 avant l'exécution. L'extension de métadonnées
Yousician a son propre protocole, publié dans 4be1ec2 avant ses trois entraînements.

Les nouveaux réseaux utilisent au maximum huit époques, une patience de trois, AdamW avec taux
0,001 et régularisation 0,001, hidden 48, batch 16 et fenêtre 64. La perte est binaire pondérée par le
nombre de notes pour SingPAD ; elle est quadratique pour les scores continus. L'époque et l'architecture
sont choisies sur validation, selon log-loss ou MAE. Le budget est distinct des douze époques de Phase 6.
Ces résultats CPU sont donc décrits séparément du modèle GPU Tesla T4 déjà actif.

Pour SingPAD, six conditions sont exécutées sur trois graines : GRU complet, agrégats sans ordre,
GRU limité aux trois groupes antérieurs, attention, attention sans embeddings de concepts et GRU
avec intervalles déjà observés. Yousician reçoit GRU, agrégats et intervalles passés. AMME reçoit GRU
et agrégats ; aucun intervalle physique n'est inventé à partir des numéros de blocs.

Les agrégats utilisent exclusivement les cumuls disponibles à la cible : changer l'ordre des observations
du passé ne change pas cette entrée. La fenêtre récente réinitialise la mémoire pour chaque cible,
omet les cumuls complets et conserve les mêmes résultats à évaluer. L'ablation d'embeddings garde
l'architecture d'attention et fixe les vecteurs de concepts à zéro. Le nombre de paramètres entraînables
est publié ; supprimer un embedding réduit la capacité et n'isole pas une causalité pédagogique.
Les intervalles utilisent les deux dernières dates déjà observées, jamais la date du résultat futur.

L'attention dense était le coût dominant. Le calcul a été limité aux requêtes de concepts évalués,
sans interaction entre requêtes. L'égalité des sorties et gradients en évaluation est testée contre le
calcul dense. Le dropout en entraînement peut suivre une trajectoire numérique différente. Les deux
empreintes exécutées restent conservées, et la partie interrompue n'est pas utilisée comme résultat.

## Contrôles réellement appris

Les contrôles historiques Phase 6 restent présents : moyenne d'entraînement, dernier résultat,
moyenne des trois derniers, moyenne exponentielle et fréquence lissée. S'ajoutent une régression
logistique régularisée SingPAD, une adaptation PFA avec intercept et cumuls par concept, Ridge pour
les scores continus et des arbres boostés. Ces modèles classiques sont des contrôles de recherche ;
l'inférence musicale de l'application reste fondée sur les réseaux PyTorch déjà validés.

Les paramètres de régularisation sont choisis parmi 0,01, 1 et 100 sur validation. Les arbres utilisent
7 ou 15 feuilles, 100 itérations, taux 0,05, régularisation 1, sans arrêt implicite sur le test. Les modèles
binaires sont ajustés avec les vrais effectifs de réussites et d'échecs, sans transformer une fraction
continue en faux label correct/incorrect. Les caractéristiques globales sont ajustées sur train seulement.
Les contrôles ne reçoivent ni identifiant d'apprenant, ni résultat cible, ni difficulté future.

## Résultats principaux et interprétation

| Base | Perte moyenne du réseau choisi sur validation | Contrôle choisi sur validation | Écart-type réseau |
|---|---:|---:|---:|
| AMME, MAE | 0,186280 | 0,172455 | 0,013539 |
| Yousician, MAE | 0,090890 | 0,090296 | 0,003716 |
| SingPAD, log-loss | 0,517925 | 0,524188 | 0,005359 |

Sur SingPAD, les réseaux choisis sur validation battent le contrôle appris sélectionné dans chacun
des trois tests. L'avantage moyen absolu est d'environ 0,006264 de log-loss. Il est plus modeste que
l'avantage sur la seule fréquence historique. Sans nouvelle cohorte confirmatoire, cet écart reste
une observation exploratoire. Le modèle GPU actif Phase 6 conserve sa log-loss 0,517529 et son
ROC-AUC 0,699104 ; aucune nouvelle expérience CPU ne remplace silencieusement ces valeurs.

Le GRU complet donne 0,517819 en moyenne sur les trois tests SingPAD, les agrégats sans ordre
0,520368, la fenêtre récente seule 0,521618. Les séquences complètes sont favorables dans ce protocole,
mais leurs représentations et capacités diffèrent : ce n'est pas une preuve que l'ordre cause un gain
d'apprentissage. L'attention passe de 0,518210 à 0,521239 sans embeddings de concepts. Les intervalles
passés ne donnent pas de gain moyen ici : 0,518182 contre 0,517819 pour le GRU sans ces intervalles.

Sur Yousician, la simplicité reste compétitive. Les variables de difficulté et de pratique passée ont
été reconstruites uniquement après vérification de l'identité des cibles avec Phase 6. Trois GRU enrichis
ajoutent difficulté précédente, indicateur d'absence, diversité d'exercices et de séances, volume évalué,
cumuls, intervalle passé et moyenne récente. Des arbres reçoivent exactement les mêmes variables.
La MAE moyenne enrichie vaut 0,091059, contre 0,090822 pour ces arbres : pas de gain moyen convaincant.
Cette extension ne justifie pas de promouvoir un nouveau réseau.

AMME reste fragile statistiquement. Une analyse complémentaire utilise cinq folds d'apprenants,
avec choix de la régularisation sur une validation interne par apprenant. Ridge obtient une MAE
moyenne 0,166888. Ce protocole ne remplace pas la comparaison à trois splits et ne permet pas de
prétendre à une supériorité contre un modèle évalué sur d'autres folds. Les erreurs médianes, p90 et
par nombre de groupes antérieurs sont publiées. Aucun apprenant synthétique ne complète l'échantillon.

## Historiques incomplets, calibration et incertitude

Les stress tests gardent tous les labels cibles et leurs poids : seuls des éléments du passé sont retirés.
Le GRU graine 42 est gelé. La suppression aléatoire de 30 % du passé est tirée pour chaque contexte de
requête ; elle ne simule pas un mécanisme identifié de collecte réelle. Deux autres conditions cachent
les deux derniers groupes ou les observations historiques des concepts ciblés.

| Passé fourni au GRU SingPAD | Log-loss test |
|---|---:|
| Intact | 0,517922 |
| 30 % de groupes passés absents | 0,523715 |
| Deux groupes récents absents | 0,539041 |
| Concepts ciblés absents du passé personnel | 0,544356 |

Yousician se dégrade également : MAE 0,090861 intacte, 0,096133 avec absence aléatoire, 0,111137 sans
les deux derniers jours et 0,150166 sans l'historique du concept global. Sur AMME, la petite variation
aléatoire améliore légèrement la MAE d'un seul test ; ce résultat négatif pour une conclusion universelle
est conservé. Les conditions de faible historique sont décrites sans les assimiler à un niveau débutant.

La température est ajustée sur validation uniquement pour les 18 réseaux SingPAD. Les probabilités
de test sont évaluées avec dix tranches fixes et disjointes. L'ECE est la moyenne pondérée par notes
de l'écart absolu entre probabilité moyenne et fréquence observée par tranche. La décomposition
groupée du Brier publie fiabilité, résolution, incertitude de population et résidu intratranche : le
résidu n'est pas caché derrière une fausse identité exacte pour les probabilités non regroupées.

Pour les architectures sélectionnées, la calibration réduit la log-loss des graines 42 et 17 mais
augmente celle de la graine 83, de 0,512568 à 0,512703. Le Brier de la graine 17 augmente légèrement
malgré une meilleure log-loss. Aucun calibrateur n'est automatiquement appliqué au modèle actif.
Les intervalles bootstrap d'apprenants Phase 6 restent consultables pour leurs modèles historiques ;
ils ne sont pas attribués aux nouveaux réseaux et ne deviennent pas des intervalles individuels.
La confiance individuelle n'est pas validée. Un manque d'observations, une prévision incertaine et un
instrument hors domaine sont trois problèmes distincts, affichés sans fabriquer de score de confiance.

## Cadre des états de compétence

La couche observation expose résultats historiques et récents, succès/échecs lorsque binaires,
poids d'évaluation, groupes distincts, couverture d'exercices, dernière date et récence. Le nombre de
groupes sans observation d'un concept est explicite ; il n'est pas interprété comme un échec ni comme
une mesure certaine des séances réellement manquantes.

La couche prédiction expose séparément probabilité de note ou score continu, concept, exercice,
instrument, horizon, version du modèle, taille du contexte et restrictions. L'état descriptif emploie
la règle source-skill-state-v1 : au moins trois groupes, au moins dix notes pour SingPAD ; fragilité
si deux des trois derniers résultats sont sous 65 % et moyenne récente sous 65 % ; régularité élevée
si les trois résultats sont au moins à 80 % ; variabilité si l'étendue récente atteint 30 points. Une
tendance demande trois groupes antérieurs en plus des trois récents et un écart d'au moins 15 points.
La priorité est insuffisance, puis tendance, puis faiblesse, régularité élevée, variabilité et absence
de motif net. Les états utilisent les observations ; le nombre prédit reste visible dans une couche
distincte au lieu d'être converti en pourcentage arbitraire de maîtrise.

Ces seuils sont des politiques descriptives explicites, pas des normes validées par un professeur.
Les concepts SingPAD restent des identifiants de la source. Le workflow de taxonomie propose rythme,
hauteur, timing, reproduction mélodique, coordination, technique et régularité comme catégories
candidates. Les correspondances proposées et approuvées restent vides. Une revue doit documenter
définition, preuve source, qualification, identité du reviewer, date et version. Le validateur de fichier
ne vérifie pas à lui seul l'identité professionnelle d'un expert. Même une correspondance sémantique
approuvée ne validerait pas automatiquement un modèle de prévision piano.

## Recommandations et démonstration O08

Le catalogue de démonstration contient uniquement les exercices déjà observés dans le passé fourni.
Un bundle d'exercices reste atomique. Les propositions relient un exercice existant à un concept avec
variabilité, baisse ou faiblesse suffisamment observée. Le classement est déterministe : nombre de
concepts concernés, puis nombre de groupes disponibles, puis identifiant. Sans contenu connu, le
système s'abstient. Un identifiant d'exercice source n'est pas une partition redistribuée : l'accès
au contenu original reste nécessaire. Aucun gain éducatif n'est affirmé.

La page /web/o08.html présente un véritable parcours de test choisi selon la procédure Phase 6 :
premier apprenant éligible avec trois groupes antérieurs et exercice connu, sans sélectionner selon
l'erreur du modèle. L'API history envoie le passé et les états, sans résultat futur. Le bouton de prévision
exécute réellement les poids actifs et renvoie un reçu signé. L'API reveal n'accepte qu'un reçu produit
après la prévision. Les reçus expirent après trente minutes et sont liés à l'empreinte de l'exemple.
Un changement du fichier exige de recommencer ; un changement du résultat caché ne change pas
la prévision, ce qui est testé. Les anciens endpoints v5 restent compatibles.

Le panneau technique décrit le tenseur [lot, temps, 4K], la fenêtre, l'architecture GRU, les paramètres,
le modèle, la métrique et le temps de cette requête. Le futur n'entre pas dans le tenseur. La révélation
montre aussi les erreurs importantes du premier exemple SingPAD : par exemple environ 85,5 % prévus
pour le concept 15 contre 40 % observés dans ce groupe. Ce cas n'a pas été remplacé par un exemple flatteur.

Le français, le graphique avec tableau équivalent, les états sans fausse animation d'IA, le focus clavier,
les états d'erreur et une mise en page mobile sont livrés. La largeur mobile effectivement mesurée est
391 pixels CSS après prise en compte de l'échelle du navigateur. Les captures et contrôles de débordement
documentent cette vérification ; ce n'est pas une certification d'accessibilité exhaustive.

## Infrastructure prospective et frontière d'intégration

Le schéma o08-practice-v1 couvre pseudonyme, instrument, exercice et version, concept, essai,
séance, instant observé, instant de disponibilité du résultat, producteur/version, définition du score,
échelle, résultats et provenance. Les dates doivent avoir un fuseau ; les observations futures et les
champs inconnus sont refusés. Les données n'enregistrent ni nom réel, ni courriel, ni audio, ni vidéo.
Le champ de confiance reste nul tant qu'aucune définition validée ne le soutient.

La collecte locale est désactivée sans DECLIC_O08_ADMIN_TOKEN d'au moins 32 caractères. Le jeton
administrateur donne accès à tous les dossiers locaux autorisés ; il ne remplace pas une authentification
par élève. Le consentement est une déclaration de l'opérateur, avec version et rétention 1 à 365 jours,
30 par défaut. Les doublons identiques sont idempotents ; un payload différent ou un second résultat
pour le même essai est refusé. Les événements et prévisions sont liés transactionnellement au consentement.

Une prévision planifiée reçoit un horodatage serveur, un modèle demandé et une définition de cible.
Elle doit être créée avant l'essai prévu, ne peut écraser une prévision antérieure et refuse un essai
dont le résultat est déjà stocké. Les résultats ultérieurs peuvent être rapprochés par apprenant,
essai, exercice/version, instrument, échelle et définition, en contrôlant les dates. Les abstentions
ne sont jamais évaluées comme de vraies prévisions. Le stockage du terrain reste en abstention car
aucun contrat d'évaluation terrain n'a encore été validé : aucune étude prospective n'est inventée.

L'adaptateur a été écrit à partir du véritable AttemptV3 existant. Il conserve uniquement des mesures
directes de producteur cohérent, refuse les données synthétiques et conserve un namespace provisoire
distinct des concepts SingPAD. Une enveloppe par axe préserve sa version ; les identifiants d'essai sont
explicitement suffixés par axe, ce qui doit être repris par un futur contrat multi-évaluation. Le mapping
historique d'objectifs v3 est mis en cache depuis une ancienne version : il n'est pas réécrit silencieusement
pour prétendre refléter la nouvelle numérotation O08. La coordination de ce contrat reste à valider avec l'équipe.

L'export et la suppression par apprenant couvrent consentement, événements et prévisions de la base
active. L'audit n'enregistre pas de payload de notes ; il conserve un condensat du pseudonyme et l'action,
pendant au plus 90 jours lorsqu'il est entretenu par les opérations. La rétention des dossiers expire à
l'usage de la base ; sa suppression est commitée avant une requête susceptible d'échouer. Une application
arrêtée ne lance pas de nettoyage physique en arrière-plan. Les sauvegardes externes restent à gérer
par l'opérateur : effacer la base active ne garantit pas leur effacement.

## Qualité d'ingénierie et sécurité

L'API v6 est ajoutée à côté de v3/v4/v5. Le registre actif, les restrictions d'instrument et le cache
d'inférence existants sont préservés. Les poids de recherche Phase 7 sont exportés avec empreintes et
configurations sans activation automatique. Les checkpoints avec optimiseur et caches privés restent
hors Git. Les contrôles classiques ne sont pas chargés en production via des pickle externes.

Les requêtes O08 sont bornées à 512 KiB avant décodage JSON, y compris sans Content-Length.
Les erreurs de validation v6 n'échoient pas le contenu d'entrée. L'interface construit les textes via
textContent et n'insère pas le contenu des réponses comme HTML. Les journaux HTTP locaux peuvent
conserver des URL ; le lancement montré reste strictement sur 127.0.0.1. Les autres endpoints historiques
ne deviennent pas magiquement authentifiés grâce au jeton de collecte : ce service reste une démonstration
locale, pas une plateforme multi-utilisateur sécurisée pour l'Internet.

Les reçus utilisent une clé aléatoire par processus en mode local. Un déploiement à plusieurs workers
doit définir une même DECLIC_DEMO_SIGNING_KEY forte ; le lancement fourni utilise un seul worker.
Les arrêts de serveur invalident normalement les anciens reçus si la clé n'est pas persistée.
La comparaison HMAC de l'autorisation tolère proprement les caractères non ASCII sans erreur 500.

Les rapports réutilisés doivent correspondre à l'archive, au split, au protocole, aux versions et à une
empreinte de code explicitement compatible. Un stress test interrompu est repris séparément du
rapport déjà terminé. Les checkpoints utilisent deux générations avec empreintes, état d'optimiseur,
curseur et générateurs aléatoires. La preuve d'interruption exacte CPU Phase 6 reste préservée ; aucune
coupure volontaire GPU Phase 7 n'est prétendue. Les nouveaux runs sont CPU locaux ; aucune session
Colab permanente ni dépense cloud n'est nécessaire pour l'inférence.

Les quinze mesures HTTP par source ont donné environ 15 ms et 13 ms de médiane chaude sur cette
machine pour SingPAD et Yousician. Ce n'est pas une mesure de charge ni une garantie de latence.
L'inférence était déjà suffisamment rapide ; son architecture n'a pas été réécrite pour afficher un gain
non démontré. L'optimisation utile porte sur les requêtes d'attention pendant la recherche.

## Statut des jalons et travaux restants

| Jalon | État livré | Partie restant à valider |
|---|---|---|
| Référence Phase 6 | Vérifiée, branche dédiée, preuves conservées | Aucun merge main autorisé |
| Robustesse scientifique | 36 réseaux, contrôles appris, calibration, manque de passé, CV AMME | Cohorte confirmatoire indépendante ; incertitude individuelle |
| Intelligence de compétences | États et règles descriptives testés | Validation pédagogique des seuils et des constructions |
| Collecte réelle | Schémas, consentement, accès local, ledger, export/suppression | Contrat de mesure terrain, modèle terrain, étude prospective réelle |
| Recommandations | Catalogue historique, classement explicite, abstention | Catalogue distribué/validé et étude d'intervention |
| Produit et démonstration | Prévision réelle, révélation séparée, vue mobile et recherche | Évaluation d'usage avec professeur et élèves |
| Fiabilité | Tests, limites de payload, rétention corrigée, artefacts versionnés | Authentification multi-utilisateur et audit externe pour déploiement |
| Livraison académique | Rapport, résumé anglais, oral, Q&A, guides et GitHub | Revue externe des conclusions |

La Phase 7 ne doit pas être déclarée entièrement achevée au sens d'une validation pédagogique et
d'un déploiement terrain. Les composants techniques et expériences livrés sont identifiés avec leurs
preuves. Les prochains travaux prioritaires sont : faire approuver le contrat et la taxonomie par un
enseignant ; fixer la définition de chaque résultat avec les autres axes ; collecter un petit pilote
consenti avec séparation chronologique des prévisions ; évaluer une nouvelle cohorte sans choix sur
le test ; ensuite seulement réexaminer la promotion, l'incertitude et l'efficacité des recommandations.

Les investigations suivantes n'ont pas été exécutées dans cette livraison : validation croisée neuronale AMME, comparaison systématique des fenêtres et traitement robuste des valeurs extrêmes, ajustement BKT et validation de la couverture d'intervalles individuels. La CV AMME livrée porte sur Ridge ; les quantiles d'erreur ne prouvent pas une incertitude individuelle calibrée. Ces pistes restent des travaux complémentaires, sans résultats à leur attribuer.

## Références méthodologiques vérifiées

Température et calibration : Guo et al., On Calibration of Modern Neural Networks, ICML 2017,
https://proceedings.mlr.press/v70/guo17a.html . La méthode est utilisée ici comme recalibrage de logits,
pas comme une promesse d'amélioration systématique ni une estimation de confiance individuelle.

Courbes de fiabilité et décomposition du Brier : documentation officielle scikit-learn,
https://scikit-learn.org/stable/modules/calibration.html . Les résultats et poids proviennent de nos
exécutions ; la documentation explique la méthode et ne fournit pas les chiffres DÉCLIC.

Arbres de contrôle : documentation officielle HistGradientBoostingClassifier,
https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html .
Les méthodes sont des contrôles scientifiques, sans activation de modèles classiques dans le produit.
