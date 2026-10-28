# Phase 10 · Recherche pédagogique et bibliothèque d'exercices

Ce document justifie les exercices de DÉCLIC. Chaque affirmation renvoie à une source qu'on peut ouvrir ; la fin du document reproduit la fiche en 10 champs de chaque exercice, générée à partir du code (`axis7/learning_catalog.py`). Ce qui n'est **pas** prouvé est signalé : aucun exercice n'a été validé par un enseignant, et les seuils marqués « provisoires » sont des choix DÉCLIC.

## 1. Ce que dit la recherche, sujet par sujet

**Perception et discrimination des hauteurs.** Micheyl et al. (2006) mesurent des seuils de discrimination de hauteur plus de six fois plus grands chez des non-musiciens que chez des musiciens classiques ; après 4 à 8 heures d'entraînement adaptatif, des non-musiciens rejoignent les musiciens ([Hearing Research, doi:10.1016/j.heares.2006.05.004](https://doi.org/10.1016/j.heares.2006.05.004)). Conséquences pour DÉCLIC : la compétence s'entraîne (exercice *Plus aigu ou plus grave ?*), et elle se **mesure** avec une procédure adaptative. La règle « 2 bonnes réponses → plus difficile, 1 erreur → plus facile » de Levitt (1971) converge vers 70,7 % de réussite ([JASA, doi:10.1121/1.1912375](https://doi.org/10.1121/1.1912375)) : c'est la *Mesure du seuil de hauteur*. La hauteur de départ change à chaque essai pour qu'on compare deux sons, pas qu'on mémorise un son fixe.

**Reconnaissance des intervalles.** La synthèse de Stambaugh & Nichols (2020) : intervalles mélodiques plus faciles qu'harmoniques, ascendants plus faciles que descendants, octave la mieux reconnue, sixte mineure / septième mineure / triton les plus confondus ; l'identification d'intervalles prédit fortement la détection d'erreurs de hauteur (r = 0,75) ([JRME, doi:10.1177/0022429419885931](https://doi.org/10.1177/0022429419885931)). Les auteurs notent aussi qu'aucun classement fixe des intervalles par difficulté ne fait consensus : DÉCLIC ne gradue donc pas « intervalle par intervalle » mais par **nombre de choix** (le hasard passe de 25 % à 8 %), puis **sens**, puis **simultanéité**, trois facteurs documentés.

**Rythme, pulsation, synchronisation.** Le paradigme de référence est le tapotement synchronisé puis continué sans métronome ; la variabilité des intervalles entre frappes mesure la précision temporelle ([Repp 2005, doi:10.3758/BF03206433](https://www.doi.org/10.3758/BF03206433) ; [Repp & Su 2013, doi:10.3758/s13423-012-0371-2](https://doi.org/10.3758/s13423-012-0371-2)). Percevoir la pulsation et la produire sont dissociables ([Fujii & Schlaug 2013, H-BAT, doi:10.3389/fnhum.2013.00771](https://doi.org/10.3389/fnhum.2013.00771)) : DÉCLIC sépare *Rythmes pareils ou différents ?* (perception) de *Garder la pulsation* et *Reproduire un rythme* (production). **Limite technique importante** : en ligne, clavier et navigateur ajoutent 60 à 100 ms de latence variable ; l'asynchronie absolue n'est pas mesurable de façon fiable sans enregistrer le son et les frappes au micro ([Anglada-Tort et al. 2022, REPP, doi:10.3758/s13428-021-01722-2](https://doi.org/10.3758/s13428-021-01722-2)). DÉCLIC ne note donc que des grandeurs **relatives** (tempo moyen, coefficient de variation, proportions entre frappes), qu'une latence constante n'affecte pas ; la variabilité de latence reste une source de bruit, et les seuils de 8 % sont **provisoires**.

**Mémoire auditive et reconnaissance des mélodies.** Pour une mélodie nouvelle, on retient d'abord son contour (montées et descentes), pas les intervalles exacts ; un changement qui conserve le contour est plus dur à détecter, surtout après transposition ([Dowling 1978, Psychological Review 85(4)](https://labs.utdallas.edu/mpac/files/2021/03/1978-2.pdf)). Le format « pareil ou différent » sur paires de fragments mélodiques et rythmiques est celui du Musical Ear Test (Wallentin et al. 2010 ; [étude de validation décrivant le format](https://pmc.ncbi.nlm.nih.gov/articles/PMC10849222)) et de la batterie PROMS ([Law & Zentner 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3532219/)). Ces capacités varient fortement même chez les non-musiciens et se mesurent sans instrument ([Müllensiefen et al. 2014, Gold-MSI](https://research.gold.ac.uk/id/eprint/10160/)). D'où les niveaux de *Mélodies pareilles ou différentes ?* : longueur (charge mémoire), contour changé puis conservé, transposition, tonal puis atonal.

**Reconnaissance des accords, fonctions tonales, analyse.** La formation de l'oreille universitaire progresse des triades vers les accords de septième et les renversements, et des intervalles vers l'écoute fonctionnelle (degrés, cadences, progressions) ([Karpinski 2000, Aural Skills Acquisition, OUP](https://journals-upgrade.shareok.org/jmtp/article/view/720)). DÉCLIC suit cet ordre ; la difficulté vérifiable est le nombre de qualités ou de degrés possibles, la présence de renversements et le mode (majeur puis mineur harmonique).

**Lecture musicale.** La théorie de l'apprentissage de Gordon pose le son avant le symbole ([Learning Sequences in Music, GIA](https://giamusic.com/resource/learning-sequences-in-music-2012-edition-book-g2345)) et Karpinski traite l'écoute avant la lecture : la lecture de notes n'est donc pas un prérequis des exercices d'écoute, et chaque note lue est jouée après la réponse pour relier symbole et son. Difficulté : étendue, clé de sol puis de fa, lignes supplémentaires, altérations ; le temps de réponse mesure l'aisance.

**Précision temporelle et reproduction.** *Reproduire un rythme* compare les proportions entre frappes après mise à l'échelle (première et dernière frappes alignées), avec une tolérance de 45 % de la plus petite valeur du motif : elle se resserre automatiquement quand les valeurs raccourcissent (doubles croches).

**Progression et maîtrise (mastery learning).** Apprentissage par maîtrise (Bloom 1968) : avancer quand un critère est atteint, et proposer des activités correctives sinon. La méta-analyse de Kulik et al. (1990) sur 108 évaluations contrôlées trouve un effet moyen de +0,52 écart-type aux examens, pour environ 4 % de temps en plus ([RER, doi:10.3102/00346543060002265](https://doi.org/10.3102/00346543060002265)). Espacer les révisions améliore la rétention ([Cepeda et al. 2006](https://pubmed.ncbi.nlm.nih.gov/16719566/), preuve sur la mémoire verbale ; le transfert à la musique n'est pas démontré).

**Prévoir la réussite.** Le knowledge tracing prédit la réussite suivante à partir de la suite des tentatives ([Corbett & Anderson 1994](https://doi.org/10.1007/BF01099821)) ; les réseaux récurrents (DKT) en dérivent ([Piech et al. 2015](https://papers.neurips.cc/paper/2015/hash/bac9162b47c56fc8a4d2a519803d51b3-Abstract.html)) et exigent des données de nombreux apprenants. Pour un seul apprenant, le modèle Elo avec terme de hasard est un modèle de référence établi des systèmes adaptatifs ([Pelánek 2016, doi:10.1016/j.compedu.2016.03.017](https://doi.org/10.1016/j.compedu.2016.03.017)).

## 2. Comment ces résultats deviennent l'architecture de DÉCLIC

| Notion | Définition dans DÉCLIC | Où la voir |
|---|---|---|
| **Compétence** | Ce qu'on apprend : 9 compétences (hauteur, intervalles, accords, mémoire mélodique, reproduction au clavier, pulsation, rythme, lecture, fonctions tonales) | Parcours · Forces et points à travailler |
| **Exercice** | Une activité à niveaux ordonnés qui entraîne et/ou mesure **une** compétence | Exercices (fiches en 10 champs) |
| **Évaluation** | La correction serveur de chaque réponse ; et l'évaluation initiale (30 questions) qui fixe le point de départ | Séance (correction), bilan |
| **Séance** | ~10 minutes de questions choisies par le planificateur ; reprise possible | Séance |
| **Parcours** | La carte de tous les niveaux : maîtrisé, en cours, prochaine étape, prérequis | Parcours · Où j'en suis |

**Règle de maîtrise.** Un niveau est maîtrisé quand, sur ses W dernières réponses (W = 10 pour les choix, 6 pour clavier et tapotement), au moins 80 % sont justes **et** ce score est improbable au hasard (test binomial unilatéral, p < 0,05). Conséquence vérifiable : à 2 choix il faut 9/10 (8/10 donne p = 0,055), à 4 choix 8/10. Le chiffre exact figure dans la colonne « Maîtrise » de chaque fiche.

**Planificateur de séance.** Trois blocs, une compétence différente chacun : (1) étapes en cours, d'autant plus prioritaires que la réussite récente est faible ; (2) découverte d'un exercice dont les prérequis sont atteints ; (3) une compétence délaissée depuis plusieurs jours gagne en priorité. **Correctif** : moins de 50 % sur les 6 derniers essais d'un niveau → retour au niveau précédent (« Consolidation »). **Révision espacée** : un niveau maîtrisé non retravaillé depuis au moins un jour revient en fin de séance. Chaque bloc affiche « Pourquoi cet exercice ? ».

**Le parcours recommande, il n'interdit pas.** Les prérequis orientent le planificateur ; tous les niveaux restent jouables depuis la bibliothèque et comptent comme preuve.

**Développer ou mesurer.** *Entraîne* : correction après chaque réponse, réécoute permise. *Mesure* : protocole fixe sans correction pendant l'essai, résultat chiffré comparable (seuil de hauteur). *Entraîne et mesure* : chaque réponse est corrigée **et** alimente la maîtrise ; l'évaluation initiale en utilise les niveaux 1.

**Pourquoi 12 exercices et 53 niveaux, pas 200.** Chaque niveau change un paramètre mesurable, chaque réponse est générée et corrigée automatiquement (les sons sont synthétisés à partir de paramètres connus : la correction est exacte), et chaque exercice existe parce qu'une source le justifie. Le niveau « expert » n'est pas une étiquette : 12 intervalles harmoniques (8 % de hasard), 5 septièmes renversées, 9 notes atonales transposées à contour conservé, degrés en mineur harmonique, identification de progressions, lecture avec altérations sur deux clés, 6 cents de discrimination.

## 3. Ce qui reste à faire

- Revue par un enseignant de formation musicale (consignes, ordre, seuils), puis normes à partir de données réelles.
- Les seuils provisoires (tempo 8 %, tolérance rythmique 45 %) n'ont pas de norme publiée dans cette forme.
- Aucun bénéfice d'apprentissage n'est démontré pour DÉCLIC lui-même : il faudrait une étude avec plusieurs apprenants.
- Mesure fine de la synchronisation : nécessiterait l'enregistrement micro façon REPP.

## 4. Bibliothèque : les 12 fiches (générées depuis le code)

### Plus aigu ou plus grave ? (`hauteur-comparaison`)

1. **Objectif** : Affiner la perception des petites différences de hauteur, base de la justesse.
2. **Compétence évaluée** : Hauteur · **rôle** : développer
3. **Difficulté** : Écart de hauteur en cents (100 cents = un demi-ton), divisé par deux à chaque niveau. Hasard : 50 %.

   | Niveau | Ce qui change | Hasard | Maîtrise |
   |---|---|---|---|
   | 1 · 200 cents | Écart d’un ton | 50 % | 9/10 |
   | 2 · 100 cents | Écart d’un demi-ton | 50 % | 9/10 |
   | 3 · 50 cents | Quart de ton | 50 % | 9/10 |
   | 4 · 25 cents | Huitième de ton | 50 % | 9/10 |
   | 5 · 12 cents | Écart fin | 50 % | 9/10 |
   | 6 · 6 cents | Écart très fin | 50 % | 9/10 |

4. **Prérequis** : aucun
5. **Consignes** : Écoutez deux sons. Le second est-il plus aigu ou plus grave que le premier ? Vous pouvez réécouter deux fois.
6. **Entrées** : Deux sons synthétisés par le navigateur ; la hauteur de départ change à chaque essai (220–440 Hz) pour empêcher de mémoriser un son fixe.
7. **Résultat attendu** : Le sens de l’écart : plus aigu ou plus grave.
8. **Correction** : Automatique côté serveur : la réponse est comparée au sens réel de l’écart.
9. **Métriques** : taux de réussite au niveau, écart en cents réussi, temps de réponse
10. **Références** : [Micheyl, C., Delhommeau, K., Perrot, X. & Oxenham, A. J. (2006)](https://doi.org/10.1016/j.heares.2006.05.004) ; [Levitt, H. (1971)](https://doi.org/10.1121/1.1912375)

### Mesure du seuil de hauteur (`hauteur-seuil`)

1. **Objectif** : Mesurer le plus petit écart de hauteur que vous percevez de façon fiable.
2. **Compétence évaluée** : Hauteur · **rôle** : mesurer
3. **Difficulté** : Adaptative : la difficulté suit vos réponses. Résultat indicatif avec peu d’essais.

   | Niveau | Ce qui change | Hasard | Maîtrise |
   |---|---|---|---|
   | 1 · Adaptatif | Escalier 2 bonnes réponses / 1 erreur | 50 % | — |

4. **Prérequis** : aucun
5. **Consignes** : Même tâche que « Plus aigu ou plus grave ? ». L’écart diminue après deux bonnes réponses et augmente après une erreur. Pas de correction pendant la mesure.
6. **Entrées** : Deux sons synthétisés ; écart adaptatif de 400 à 3 cents.
7. **Résultat attendu** : Le sens de l’écart à chaque essai.
8. **Correction** : Escalier adaptatif (Levitt, 1971) : l’écart est divisé par deux à chaque bonne réponse jusqu’à la première erreur, puis 2 bonnes réponses → plus petit, 1 erreur → plus grand. Le seuil est la moyenne géométrique des écarts aux derniers changements de sens.
9. **Métriques** : seuil estimé en cents, nombre de changements de sens (fiabilité)
10. **Références** : [Levitt, H. (1971)](https://doi.org/10.1121/1.1912375) ; [Micheyl, C., Delhommeau, K., Perrot, X. & Oxenham, A. J. (2006)](https://doi.org/10.1016/j.heares.2006.05.004)

### Reconnaître un intervalle (`intervalles`)

1. **Objectif** : Nommer l’écart entre deux notes, compétence de base de la dictée et de la détection d’erreurs.
2. **Compétence évaluée** : Intervalles · **rôle** : développer et mesurer
3. **Difficulté** : Nombre de choix possibles (hasard = 1/nombre de choix), puis sens (montant avant descendant) et mode (mélodique avant harmonique), ordre documenté par Stambaugh & Nichols (2020).

   | Niveau | Ce qui change | Hasard | Maîtrise |
   |---|---|---|---|
   | 1 · 4 intervalles montants | Seconde majeure, tierce majeure, quinte, octave · montants · hasard 25 % | 25 % | 8/10 |
   | 2 · 7 intervalles montants | Ajout seconde mineure, tierce mineure, quarte · hasard 14 % | 14 % | 8/10 |
   | 3 · 12 intervalles montants | Tous les intervalles jusqu’à l’octave, dont triton et septièmes · hasard 8 % | 8 % | 8/10 |
   | 4 · 12 intervalles descendants | Mêmes 12 intervalles, joués en descendant | 8 % | 8/10 |
   | 5 · 12 intervalles harmoniques | Les deux notes ensemble | 8 % | 8/10 |

4. **Prérequis** : Plus aigu ou plus grave ? niveau 2
5. **Consignes** : Écoutez deux notes. Choisissez le nom de l’intervalle. Astuce : associez chaque intervalle au début d’une mélodie connue.
6. **Entrées** : Deux notes synthétisées, successives (mélodique) ou simultanées (harmonique).
7. **Résultat attendu** : Le nom de l’intervalle.
8. **Correction** : Automatique ; les confusions (ex. sixte mineure ↔ septième mineure) sont comptées pour repérer les erreurs récurrentes.
9. **Métriques** : taux de réussite, matrice de confusion des intervalles, temps de réponse
10. **Références** : [Stambaugh, L. A. & Nichols, B. E. (2020)](https://doi.org/10.1177/0022429419885931) ; [Karpinski, G. S. (2000)](https://journals-upgrade.shareok.org/jmtp/article/view/720)

### Couleur des accords (`accords`)

1. **Objectif** : Reconnaître la qualité d’un accord à l’oreille.
2. **Compétence évaluée** : Accords · **rôle** : développer et mesurer
3. **Difficulté** : Nombre de qualités possibles, puis renversements (la basse n’est plus la fondamentale), puis accords de quatre sons.

   | Niveau | Ce qui change | Hasard | Maîtrise |
   |---|---|---|---|
   | 1 · Majeur ou mineur | Deux qualités, état fondamental · hasard 50 % | 50 % | 9/10 |
   | 2 · 4 qualités de trois sons | + diminué, augmenté · hasard 25 % | 25 % | 8/10 |
   | 3 · 4 qualités renversées | Renversements aléatoires | 25 % | 8/10 |
   | 4 · 4 accords de septième | Septième majeure, de dominante, mineure, demi-diminuée · hasard 25 % | 25 % | 8/10 |
   | 5 · 5 septièmes renversées | + septième diminuée, renversements · hasard 20 % | 20 % | 8/10 |

4. **Prérequis** : Reconnaître un intervalle niveau 1
5. **Consignes** : Écoutez l’accord. Choisissez sa qualité. Majeur : lumineux et stable ; mineur : plus sombre.
6. **Entrées** : Un accord synthétisé, notes jouées ensemble.
7. **Résultat attendu** : La qualité de l’accord.
8. **Correction** : Automatique ; confusions comptées.
9. **Métriques** : taux de réussite, confusions entre qualités
10. **Références** : [Karpinski, G. S. (2000)](https://journals-upgrade.shareok.org/jmtp/article/view/720) ; [Law, L. N. C. & Zentner, M. (2012)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3532219/)

### Mélodies pareilles ou différentes ? (`melodies`)

1. **Objectif** : Retenir une mélodie courte et détecter une note changée.
2. **Compétence évaluée** : Mémoire mélodique · **rôle** : développer et mesurer
3. **Difficulté** : Longueur de la mélodie (charge mémoire), changement qui conserve ou non le contour (Dowling, 1978), transposition, tonal ou atonal. Hasard : 50 %.

   | Niveau | Ce qui change | Hasard | Maîtrise |
   |---|---|---|---|
   | 1 · 3 notes, contour changé | Le changement inverse une montée/descente | 50 % | 9/10 |
   | 2 · 5 notes, contour changé | Mélodie plus longue | 50 % | 9/10 |
   | 3 · 5 notes, contour conservé | Seule la taille d’un écart change | 50 % | 9/10 |
   | 4 · 7 notes transposées | Seconde mélodie transposée ; contour conservé | 50 % | 9/10 |
   | 5 · 9 notes atonales transposées | Sans tonalité, transposée, contour conservé | 50 % | 9/10 |

4. **Prérequis** : aucun
5. **Consignes** : Écoutez deux mélodies. Sont-elles identiques ? Aux niveaux transposés, la seconde commence plus haut ou plus bas : comparez la forme, pas la hauteur de départ.
6. **Entrées** : Deux mélodies synthétisées.
7. **Résultat attendu** : « Pareilles » ou « Différentes ».
8. **Correction** : Automatique. Le type de changement (contour conservé ou non) est enregistré pour l’analyse des erreurs.
9. **Métriques** : taux de réussite, réussite sur changements qui conservent le contour
10. **Références** : [Dowling, W. J. (1978)](https://labs.utdallas.edu/mpac/files/2021/03/1978-2.pdf) ; [Wallentin, M., Nielsen, A. H., Friis-Olivarius, M., Vuust, C. & Vuust, P. (2010)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10849222) ; [Müllensiefen, D., Gingras, B., Musil, J. & Stewart, L. (2014)](https://research.gold.ac.uk/id/eprint/10160/)

### Écho au clavier (`echo`)

1. **Objectif** : Rejouer une mélodie entendue sur le clavier de l’écran : relier l’oreille au geste, sans instrument.
2. **Compétence évaluée** : Reproduction au clavier · **rôle** : développer et mesurer
3. **Difficulté** : Nombre de notes, taille des sauts, notes hors gamme (chromatiques), départ hors de do.

   | Niveau | Ce qui change | Hasard | Maîtrise |
   |---|---|---|---|
   | 1 · 3 notes conjointes | Do–sol, pas de saut | — | 5/6 |
   | 2 · 4 notes avec sauts | Sauts jusqu’à la quarte | — | 5/6 |
   | 3 · 5 notes sur l’octave | Gamme de do, sauts jusqu’à la quinte | — | 5/6 |
   | 4 · 6 notes chromatiques | Une note hors gamme | — | 5/6 |
   | 5 · 7 notes, départ libre | Départ sur une autre note, une note hors gamme | — | 5/6 |

4. **Prérequis** : Mélodies pareilles ou différentes ? niveau 1
5. **Consignes** : Écoutez la mélodie (trois écoutes maximum). La première note est indiquée sur le clavier. Rejouez-la avec la souris ou les touches A Z E R T Y… du clavier de l’ordinateur, puis validez.
6. **Entrées** : Une mélodie synthétisée ; votre réponse : la suite de notes jouées sur le clavier virtuel.
7. **Résultat attendu** : La même suite de notes, dans le même ordre.
8. **Correction** : Comparaison note par note ; réussi si toutes les notes sont justes. Les notes justes à l’octave près sont signalées.
9. **Métriques** : proportion de notes justes, réussite complète, nombre d’écoutes
10. **Références** : [Karpinski, G. S. (2000)](https://journals-upgrade.shareok.org/jmtp/article/view/720) ; [Gordon, E. E. (2012)](https://giamusic.com/resource/learning-sequences-in-music-2012-edition-book-g2345)

### Garder la pulsation (`pulsation`)

1. **Objectif** : Taper à tempo régulier avec un métronome, puis continuer seul.
2. **Compétence évaluée** : Pulsation · **rôle** : développer et mesurer
3. **Difficulté** : Tempo (les tempos lents sont plus difficiles à tenir), longueur de la continuation, nombre de clics de référence.

   | Niveau | Ce qui change | Hasard | Maîtrise |
   |---|---|---|---|
   | 1 · 100 BPM, 8 + 8 | 8 clics puis 8 frappes seul | — | 5/6 |
   | 2 · 80 BPM, 8 + 8 | Tempo plus lent | — | 5/6 |
   | 3 · 120 BPM, 8 + 12 | Tempo rapide, continuation plus longue | — | 5/6 |
   | 4 · 60 BPM, 8 + 12 | Tempo lent | — | 5/6 |
   | 5 · 100 BPM, 4 + 16 | Peu de référence, longue continuation | — | 5/6 |

4. **Prérequis** : aucun
5. **Consignes** : Cliquez sur « Démarrer » puis tapez la barre d’espace (ou le grand bouton) avec chaque clic. Quand le métronome s’arrête, continuez au même tempo jusqu’au signal de fin. Seule la régularité compte : un petit retard constant de votre ordinateur n’est pas pénalisé.
6. **Entrées** : Clics de métronome ; vos frappes (barre d’espace ou toucher), horodatées par le navigateur.
7. **Résultat attendu** : Des frappes régulières au tempo donné pendant la phase sans métronome.
8. **Correction** : Intervalles entre frappes de la phase de continuation : écart de tempo moyen et coefficient de variation. Réussi si l’écart de tempo est ≤ 8 % et la variation ≤ 8 % (seuils provisoires DÉCLIC).
9. **Métriques** : écart de tempo (%), coefficient de variation (%), tendance à presser ou ralentir
10. **Références** : [Repp, B. H. (2005)](https://www.doi.org/10.3758/BF03206433) ; [Repp, B. H. & Su, Y.-H. (2013)](https://doi.org/10.3758/s13423-012-0371-2) ; [Fujii, S. & Schlaug, G. (2013)](https://doi.org/10.3389/fnhum.2013.00771) ; [Anglada-Tort, M., Harrison, P. M. C. & Jacoby, N. (2022)](https://doi.org/10.3758/s13428-021-01722-2)

### Rythmes pareils ou différents ? (`rythmes`)

1. **Objectif** : Percevoir la structure d’un rythme et repérer un déplacement.
2. **Compétence évaluée** : Rythme · **rôle** : développer et mesurer
3. **Difficulté** : Valeurs rythmiques utilisées : noires/croches, puis pointées, syncopes, doubles croches. Hasard : 50 %.

   | Niveau | Ce qui change | Hasard | Maîtrise |
   |---|---|---|---|
   | 1 · Noires et croches | Valeurs simples | 50 % | 9/10 |
   | 2 · Notes pointées | + noire pointée–croche | 50 % | 9/10 |
   | 3 · Syncopes | + croche–noire–croche | 50 % | 9/10 |
   | 4 · Doubles croches | + quatre doubles croches, croche–deux doubles | 50 % | 9/10 |

4. **Prérequis** : aucun
5. **Consignes** : Écoutez deux rythmes d’une mesure. Sont-ils identiques ?
6. **Entrées** : Deux motifs rythmiques synthétisés à 90 BPM.
7. **Résultat attendu** : « Pareils » ou « Différents ».
8. **Correction** : Automatique ; le type de modification est enregistré.
9. **Métriques** : taux de réussite
10. **Références** : [Wallentin, M., Nielsen, A. H., Friis-Olivarius, M., Vuust, C. & Vuust, P. (2010)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10849222) ; [Fujii, S. & Schlaug, G. (2013)](https://doi.org/10.3389/fnhum.2013.00771)

### Reproduire un rythme (`rythme-echo`)

1. **Objectif** : Rejouer en tapant un rythme entendu.
2. **Compétence évaluée** : Rythme · **rôle** : développer et mesurer
3. **Difficulté** : Mêmes valeurs rythmiques que l’exercice précédent : la tolérance se resserre avec les valeurs plus courtes.

   | Niveau | Ce qui change | Hasard | Maîtrise |
   |---|---|---|---|
   | 1 · Noires et croches | Valeurs simples | — | 5/6 |
   | 2 · Notes pointées | Valeurs pointées | — | 5/6 |
   | 3 · Syncopes | Syncopes | — | 5/6 |
   | 4 · Doubles croches | Valeurs courtes | — | 5/6 |

4. **Prérequis** : Rythmes pareils ou différents ? niveau 1, Garder la pulsation niveau 1
5. **Consignes** : Écoutez le décompte puis le rythme. Au signal, tapez le même rythme avec la barre d’espace. Le tempo peut être un peu différent : seules les proportions comptent.
6. **Entrées** : Un motif rythmique synthétisé ; vos frappes horodatées.
7. **Résultat attendu** : Le même nombre de frappes, dans les mêmes proportions.
8. **Correction** : Les frappes sont mises à l’échelle du motif (première et dernière alignées) ; chaque frappe doit tomber à moins de 45 % de la plus petite valeur du motif.
9. **Métriques** : proportion de frappes bien placées, erreur maximale en temps
10. **Références** : [Repp, B. H. (2005)](https://www.doi.org/10.3758/BF03206433) ; [Anglada-Tort, M., Harrison, P. M. C. & Jacoby, N. (2022)](https://doi.org/10.3758/s13428-021-01722-2)

### Lire une note (`lecture`)

1. **Objectif** : Nommer rapidement une note écrite sur la portée.
2. **Compétence évaluée** : Lecture de notes · **rôle** : développer et mesurer
3. **Difficulté** : Étendue des notes, clé (sol puis fa), lignes supplémentaires, altérations. Hasard : 14 %, puis 5 % avec altérations.

   | Niveau | Ce qui change | Hasard | Maîtrise |
   |---|---|---|---|
   | 1 · Clé de sol, do–sol | Cinq notes autour du do central | 14 % | 8/10 |
   | 2 · Clé de sol, portée | Du do central au la aigu | 14 % | 8/10 |
   | 3 · Clé de fa, portée | Du mi grave au do central | 14 % | 8/10 |
   | 4 · Deux clés, lignes supplémentaires | Notes au-dessus et au-dessous de la portée | 14 % | 8/10 |
   | 5 · Deux clés, altérations | Dièses et bémols | 5 % | 8/10 |

4. **Prérequis** : aucun
5. **Consignes** : Une note s’affiche sur la portée. Choisissez son nom (et son altération au dernier niveau). Après la réponse, la note est jouée.
6. **Entrées** : Une portée dessinée par la page ; réponse par boutons.
7. **Résultat attendu** : Le nom de la note.
8. **Correction** : Automatique ; le temps de réponse mesure l’aisance de lecture.
9. **Métriques** : taux de réussite, temps de réponse médian, confusions (ex. mi ↔ sol)
10. **Références** : [Karpinski, G. S. (2000)](https://journals-upgrade.shareok.org/jmtp/article/view/720) ; [Gordon, E. E. (2012)](https://giamusic.com/resource/learning-sequences-in-music-2012-edition-book-g2345)

### Degré dans la tonalité (`degres`)

1. **Objectif** : Situer une note par rapport à la tonique après une cadence (oreille fonctionnelle).
2. **Compétence évaluée** : Fonctions tonales · **rôle** : développer et mesurer
3. **Difficulté** : Nombre de degrés possibles, puis mode mineur.

   | Niveau | Ce qui change | Hasard | Maîtrise |
   |---|---|---|---|
   | 1 · Degrés 1, 3, 5 | Notes de l’accord de tonique · hasard 33 % | 33 % | 8/10 |
   | 2 · Degrés 1 à 5 | · hasard 20 % | 20 % | 8/10 |
   | 3 · Sept degrés, majeur | · hasard 14 % | 14 % | 8/10 |
   | 4 · Sept degrés, mineur | Mineur harmonique | 14 % | 8/10 |

4. **Prérequis** : Reconnaître un intervalle niveau 2
5. **Consignes** : Une courte cadence installe la tonalité. Puis une note est jouée : quel degré de la gamme est-ce ?
6. **Entrées** : Cadence I–IV–V–I puis une note, synthétisées ; tonalité changée à chaque essai.
7. **Résultat attendu** : Le degré de la note (1 à 7).
8. **Correction** : Automatique ; confusions de degrés comptées.
9. **Métriques** : taux de réussite, confusions de degrés
10. **Références** : [Karpinski, G. S. (2000)](https://journals-upgrade.shareok.org/jmtp/article/view/720) ; [Gordon, E. E. (2012)](https://giamusic.com/resource/learning-sequences-in-music-2012-edition-book-g2345)

### Fins de phrase (cadences) (`cadences`)

1. **Objectif** : Reconnaître comment une phrase harmonique se termine.
2. **Compétence évaluée** : Fonctions tonales · **rôle** : développer et mesurer
3. **Difficulté** : Nombre de types possibles (2 → 4), puis identification d’une suite complète de quatre accords.

   | Niveau | Ce qui change | Hasard | Maîtrise |
   |---|---|---|---|
   | 1 · Parfaite ou demi | · hasard 50 % | 50 % | 9/10 |
   | 2 · + plagale | · hasard 33 % | 33 % | 8/10 |
   | 3 · Quatre cadences | + rompue · hasard 25 % | 25 % | 8/10 |
   | 4 · Suite d’accords | Choisir la suite parmi quatre · hasard 25 % | 25 % | 8/10 |

4. **Prérequis** : Couleur des accords niveau 1, Degré dans la tonalité niveau 1
5. **Consignes** : Écoutez quatre accords. Choisissez le type de fin, ou la suite d’accords au dernier niveau.
6. **Entrées** : Quatre accords synthétisés, tonalité changée à chaque essai.
7. **Résultat attendu** : Le type de cadence ou la suite d’accords.
8. **Correction** : Automatique.
9. **Métriques** : taux de réussite, confusions entre cadences
10. **Références** : [Karpinski, G. S. (2000)](https://journals-upgrade.shareok.org/jmtp/article/view/720)

