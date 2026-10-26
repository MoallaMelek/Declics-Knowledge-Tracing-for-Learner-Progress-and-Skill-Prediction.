# Phase 9 · Refonte UX de DÉCLIC

Branche `phase9/declic-ux-rebirth`, partie de `main` @ `831ca85` (stabilisation Phase 8, durcissement du 17/10 et Phase 8 déjà fusionnés).
Périmètre : **frontend uniquement**. Aucun modèle, cible, protocole d'évaluation, jeu de données ni contrat d'API n'est modifié.

## 1. Audit de l'interface existante

### Inventaire

| Page | Ce qu'elle fait | API | Navigation propre | Identité visuelle |
|---|---|---|---|---|
| `/` (`index.html` + `musician.js`) | Carnet piano : auto-évaluation d'exercices, progression observée, export | `/api/practice/*` | Accueil · Pratiquer · Ma progression · Mon carnet + lien « Recherche & intégration » | vert forêt / crème, serif |
| `o08.html` | Démo Phase 7 : historique → prévision → révélation, états, résultats Phase 7 | `/api/v6/o08/demo/*` | 5 liens + « Recherche » | vert / crème, serif italique |
| `musical-demo.html` | Démo Phase 6 : même idée que `o08.html`, version antérieure | `/api/v5/musical/demo` | aucune (logo + lien) | vert / crème |
| `living.html` + `living/*.js` | Phase 8 : rejeu causal, constellation, empreinte, observatoire, machine à remonter le temps | `/api/v7/o08/living/*` | Démonstration O08 · Parcours vivant · Preuves Phase 6 + case « Mode recherche » | noir / or / néon |
| `musical-cloud.html` | Résultats Phase 6, liens Colab | `/api/v5/musical/models`, `/research` | aucune | vert / crème |
| `case-study.html` | Histoires de pratique piano Rach3 / PianoVAM | `/api/research/music-case-study` | aucune | vert / crème |
| `research.html` + `app.js` | « Jumeau d'apprentissage » : **simulation** musicale et étude génie logiciel FORGET-SE | `/api/twin`, `/api/v2`, `/api/simulate`… | 2 onglets | noir / blanc / rouge, mono |

Sept pages, **cinq systèmes de navigation**, quatre identités visuelles et six feuilles de style. Aucune page ne mène à toutes les autres.

### Pourquoi on se perd

1. **Pas de point d'entrée.** `/` ouvre le carnet piano, alors que la contribution O08 (le parcours Phase 8) n'est atteignable que depuis un lien de pied de page vers `o08.html`, puis un lien d'en-tête.
2. **Fonctions dupliquées.** `musical-demo.html` (v5), `o08.html` (v6) et `living.html` (v7) montrent tous « passé → prévision → résultat ». Le parcours 01 de `living.html` *est* l'apprenant de démonstration de Phase 7. Trois pages, trois vocabulaires (« groupe », « pas », « essai »).
3. **Deux « constellations » contradictoires.** `research.html` titre « Votre progression, séance après séance » et affiche des compétences nommées (Justesse, Rythme…) avec des probabilités : c'est une **simulation**. La vraie constellation SingPAD montre 270 concepts opaques. La fausse paraît plus lisible que la vraie — risque d'intégrité scientifique, pas seulement d'ergonomie.
4. **La science d'abord.** Sur `living.html`, l'utilisateur voit une constellation de 270 points numérotés, un disque polaire et un pipeline de 6 étapes (tenseurs, logits) avant toute phrase simple sur le parcours. Aucun résumé en langage courant.
5. **Catégories d'information mêlées.** Observé, interprété, prévu et révélé sont présents mais distingués seulement par des nuances de couleur sur fond noir et des notes en petit texte.
6. **Terminologie interne exposée.** « Point de coupure », « pas », « O08 », « Phase 6 », « EnhancedGRU », « source-skill-state-v1 », « log-loss par note » apparaissent au même niveau que les titres.
7. **Pages en impasse.** `musical-demo.html`, `musical-cloud.html`, `case-study.html` n'ont qu'un lien de retour vers le carnet piano. `o08.html` échoue (503) sans les données privées et n'offre pas d'autre chemin.
8. **Hiérarchie faible.** Libellés « eyebrow » en petites capitales au-dessus de chaque titre, numérotation 01/02/03 décorative, cartes de même taille : tout a le même poids.
9. **Erreurs inégales.** `living.html` a des messages français exemplaires et une reprise manuelle ; `o08.html` affiche une phrase de serveur sans action ; `research.html` mélange simulation et état réel.
10. **Démonstrations techniquement impressionnantes mais opaques** : le pipeline GRU est la meilleure preuve scientifique du projet, et le pire point d'entrée pour un élève.

### Ce qui est solide et doit être conservé

* Le moteur Phase 8 (`adapters`, `api`, `store`, `timeline`, `constellation`, `fingerprint`, `observatory`) : gardes de causalité, identité de génération, reçus HMAC, cache limité aux pas visités, abandon des requêtes obsolètes. Il est couvert par 3 harnais (DOM Node, synchronisation, Playwright).
* Les messages d'erreur français du client v7.
* Les mises en garde scientifiques : aucune n'est retirée, elles sont déplacées au bon niveau de lecture.

## 2. Nouvelle architecture

Une seule barre de navigation, identique partout, quatre destinations :

| Destination | Pour qui | Contenu | Fichier |
|---|---|---|---|
| **Accueil** | tout le monde | Ce que fait DÉCLIC en une phrase, trois portes selon le besoin, ce que l'outil ne sait pas faire | `index.html` |
| **Parcours** | élève, enseignant | Un parcours de démonstration, lu dans l'ordre : *en bref* → *prochain essai* → *remonter le temps* → *carte des concepts* → *empreinte*. La **vue chercheur** ajoute le laboratoire du calcul | `living.html` |
| **Carnet** | élève pianiste | Le carnet d'auto-évaluation piano (fonction inchangée) | `carnet.html` |
| **Laboratoire** | professeur, chercheur | État du système, le calcul d'une prévision, bancs d'essai Phase 7, modèles Phase 6, archives des anciennes interfaces | `labo.html` |

**Consolidé.** `o08.html` et `musical-demo.html` ne sont plus des destinations : leur parcours est celui de *Parcours* (même API v7, même apprenant 01). Ils restent consultables comme archives depuis le Laboratoire, avec un bandeau qui renvoie vers *Parcours*.

**Déplacé.** La simulation `research.html` passe dans les archives du Laboratoire avec un avertissement explicite « simulation, pas des données d'apprenant ». `musical-cloud.html` et `case-study.html` deviennent des sections d'archives.

**Simplifié.** Le parcours commence par une phrase. La constellation et l'empreinte deviennent des vues d'exploration expliquées ; la liste « à surveiller / régulier » sert de représentation par défaut. L'observatoire (tenseurs, GRU, logits) n'apparaît qu'en vue chercheur.

### Parcours utilisateur cible

1. Accueil → « Explorer un parcours » (action principale).
2. Choix d'un instrument et d'un parcours, présentés comme **profils de démonstration issus du jeu de test**, jamais comme « vous ».
3. *En bref* : combien de séances observées, réussite récente vs passé, concepts à surveiller, piste de pratique (ou abstention).
4. *Prochain essai* : la prévision en une phrase, avec sa cible, son unité et sa portée ; bouton pour révéler le résultat réel.
5. *Remonter le temps* : la frise fixe en bas d'écran change le moment observé ; toutes les vues suivent.
6. *Carte des concepts* et *Empreinte* : exploration, légende et lecture accessible en tableau.
7. Vue chercheur → laboratoire du calcul, provenance, références, calibration.

### Quatre catégories d'information, une grammaire visuelle

Inspirée des éditions *Urtext*, qui distinguent typographiquement le texte du compositeur et les ajouts de l'éditeur :

| Catégorie | Signification | Marque visuelle |
|---|---|---|
| **Observé** | ce qui a réellement été enregistré | encre pleine |
| **Lecture** | ce que les observations permettent de décrire | texte entre crochets d'édition, italique |
| **Prévision** | ce qu'estime le réseau entraîné | trait pointillé, couleur ocre |
| **Révélé** | le résultat réel, affiché après la prévision | trait plein vert, avec l'écart |

Chaque bloc du parcours porte l'étiquette de sa catégorie ; aucune valeur ne mélange deux catégories.
