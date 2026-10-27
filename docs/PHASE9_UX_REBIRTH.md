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

## 3. Avant / après

![Entrée : avant, `/` ouvrait le carnet piano ; après, une page d'accueil qui explique et oriente](assets/phase9/before-after-entry.png)

![Parcours : avant, la science d'abord ; après, la lecture simple d'abord](assets/phase9/before-after-journey.png)

![Recherche : avant, une simulation titrée « Votre progression » ; après, un Laboratoire alimenté par l'API et une simulation archivée et signalée](assets/phase9/before-after-research.png)

| Question d'acceptation | Avant | Après |
|---|---|---|
| Un premier visiteur comprend-il l'accueil ? | `/` montrait un carnet piano, sans lien visible vers O08 | Une phrase, une action principale, trois portes par public, l'état réel du serveur |
| L'action principale est-elle évidente ? | Non : 4 boutons de carnet + liens dispersés | « Explorer un parcours », seule action pleine |
| Atteint-on l'expérience apprenant sans deviner ? | Pied de page → `o08.html` → en-tête → `living.html` | 1 clic depuis l'accueil, et dans la barre partout |
| Les fonctions liées sont-elles reliées ? | 3 démos concurrentes, 5 navigations | Une navigation, un Parcours, chapitres liés entre eux |
| Comprend-on une prévision ? | Pipeline GRU en 6 étapes | Une phrase avec cible et unité, « ce que c'est / ce que ce n'est pas », révélation |
| Explore-t-on sans connaître l'apprentissage automatique ? | Non | Oui : *En bref*, listes de concepts, frise temporelle |
| Un professeur atteint-il les preuves techniques ? | Oui, mais mêlées au reste | Laboratoire + vue chercheur, reçu signé visible |
| Les erreurs sont-elles compréhensibles ? | Excellentes sur `living.html`, absentes ailleurs | Même niveau sur les quatre destinations, avec action de reprise |
| Un seul produit ? | Non (4 identités visuelles) | Oui (un système, une navigation) |

## 4. Système de design

Fichier : `web/declic.css`, chargé en premier par toutes les pages. Les pages ajoutent une feuille propre (`home.css`, `living.css`, `labo.css`, `carnet.css`) qui n'utilise que ses jetons.

**Monde visuel.** L'édition de partitions *Urtext* : couverture bleu pâle d'éditeur, papier froid, encre marine. Le choix vient du produit lui-même : une édition Urtext rend visible la différence entre le texte du compositeur et les ajouts de l'éditeur, exactement comme DÉCLIC doit séparer l'observé, la lecture, la prévision et le révélé. Scène d'usage : élève à la maison ou au conservatoire en journée, enseignant en cours, jury devant un projecteur ; d'où un thème clair.

**Typographie.** Bodoni Moda (titres, à partir de 1,5 rem : les pages de titre des partitions du XIXᵉ siècle) et Atkinson Hyperlegible Next (texte, chiffres, interface : conçue pour la lisibilité ; son zéro barré est volontaire). Atkinson Hyperlegible Mono uniquement pour les empreintes, identifiants et formes de tenseurs. Les trois polices sont sous licence OFL, auto-hébergées dans `web/fonts/` (aucun appel réseau, le dépôt reste hors ligne).

**Couleur.** Stratégie retenue : sobre (neutres teintés + couleurs qui portent une donnée), avec un champ de couleur assumé sur la couverture de l'accueil. Tous les textes ≥ 4,5:1 sur le papier et la feuille ; toutes les marques qui portent une valeur, états « insuffisant » et « non observé » compris, ≥ 3:1 (calcul WCAG). Seuls les repères de fond sans valeur (grille, petits points du vocabulaire non observé) restent volontairement pâles. *(Corrigé après la relecture indépendante : l'extrémité claire de l'échelle et deux états creux étaient sous 3:1.)* Les valeurs observées utilisent une seule échelle bleue qui ne rejoint jamais la couleur du papier : une valeur faible reste visible et ne se confond pas avec « non mesuré ». Les états descriptifs gardent chacun une couleur distincte, toujours accompagnée de leur nom.

**Composants.** Barre de navigation unique, en-tête de page (titre, phrase, action), boutons (principal, secondaire, discret, prévision), étiquettes de catégorie, interrupteur de vue, message d'état, bloc d'erreur avec reprise, divulgation progressive, tableaux à chiffres tabulaires, dock de la frise temporelle.

**Mouvement.** Courbe `cubic-bezier(.23, 1, .32, 1)`, 140 ms pour la pression (échelle 0,97), 200 ms pour les états, 520 ms pour le seul geste signature : le résultat révélé glisse depuis la position de la prévision, ce qui montre l'écart au lieu de seulement l'écrire. Aucune animation sur les déplacements au clavier dans la frise. `prefers-reduced-motion` coupe toutes les animations.

### Influence des skills installés

Les instructions ont été lues sur la machine de développement (`~/.agents/skills`), sans exécuter leurs scripts, binaires, hooks ni agents. Le lanceur `impeccable context` et le tirage `concept-seed` n'ont donc pas tourné ; la méthode a été appliquée à la main.

| Skill | Ce qui a été appliqué concrètement |
|---|---|
| `impeccable` (craft-floor, operate, clarify, onboard, new-work) | Suppression des libellés « eyebrow » et des numéros décoratifs (gardés seulement dans le pipeline, où l'ordre est l'information) ; aucune carte d'icônes identiques, aucun dégradé de texte, aucun verre ni lueur ; pas de bordure gauche colorée ; polices auto-hébergées plutôt que polices système ; barres de défilement, sélection et focus thémés ; chaque état (chargement, vide, erreur, abstention, fin de parcours) a un texte qui dit quoi faire ; monde choisi à partir de la culture du public, mode « Operate/Read » pour l'application et « Persuade » pour la couverture de l'accueil |
| `emil-design-eng`, `improve-animations` | Courbes ease-out fortes, durées < 300 ms en interface, `scale(.97)` à la pression, pas d'animation pour les actions clavier répétées, un seul geste signature, mouvement réduit respecté |
| `design-taste-frontend`, `redesign-existing-projects` | Idée tirée du sujet (« la distinction source / ajout d'éditeur devient la grammaire des quatre catégories ») ; titres de deux lignes au plus ; un seul élément « vivant » sur l'accueil (l'état réel du serveur) ; liste des signes « générés » évitée (crème + terracotta, néon sur noir, micro-libellés mono, hairlines partout) ; refonte sans casser la logique existante |

## 5. Ce qui a changé dans le code

* `web/index.html`, `home.css`, `home.js` : nouvel accueil. Les anciennes adresses `/?page=…` redirigent vers le carnet.
* `web/living.html`, `living.css`, `living/summary.js` : le Parcours. Le moteur Phase 8 est conservé ; `adapters.js` gagne `digest()`, `nextStep()`, `receipt()` et `score()` (purs, testés). L'observatoire n'apparaît qu'en vue chercheur. Le reçu de prévision signé est affiché (décodé, sans résultat).
* `web/labo.html`, `labo.css`, `labo.js` : Laboratoire.
* `web/carnet.html`, `carnet.css` : carnet piano (logique de `musician.js` inchangée).
* `web/archive.css` + bandeau sur les cinq anciennes pages.
* Corrigé au passage : un score Yousician observé s'affichait en « % » alors que la même grandeur prévue s'affichait « / 100 » ; les deux sont maintenant sur la même échelle partout.
* Aucun fichier de `axis7/`, `artifacts/`, `data/`, `scripts/` ni `configs/` n'est modifié.

## 6. Vérification

Environnement cloud de la session (Linux, Python 3.13, torch 2.14 depuis PyPI, Chromium préinstallé). Les données privées du jeu de test ne sont pas disponibles ici : la démonstration de bout en bout a tourné sur le **montage d'intégration synthétique** du dépôt (`scripts/integration_fixture`), avec les **vrais poids entraînés copiés** et le vrai serveur HTTP.

| Contrôle | Avant | Après |
|---|---|---|
| `pytest` complet | 425 réussis · 3 ignorés | 427 réussis · 3 ignorés (+ 2 tests du lanceur) |
| Adaptateurs et client (Node) | 43 contrôles | 49 contrôles (+ résumé, prévision simple, reçu) |
| Synchronisation des vues, Yousician | 133 | 180 (+ chapitres simples, absence de fuite et de résultat, vue chercheur, aucune valeur en %) |
| Synchronisation des vues, SingPAD | 185 | 226 |
| Carnet (Node) | 20 | 20 |
| Playwright, vrai Chromium + vrai HTTP | 13 scénarios | 16 scénarios (+ quatre destinations, + premier visiteur au clavier, + comparaison épinglée) |

Contrôles manuels en navigateur : parcours complet du carnet (création démo, exercice, évaluation, enregistrement, progression, séances) ; Parcours SingPAD et Yousician en vue simple puis chercheur, révélation, sélection d'un concept ; Laboratoire ; anciennes pages ; serveur coupé (accueil, parcours, laboratoire, carnet) ; largeur 390 px sans défilement horizontal ; clavier (lien d'évitement, frise au clavier). Une assertion du harnais de synchronisation a été réécrite : « les quatre vues sont affichées » devient « vue simple affichée, calcul masqué jusqu'à la vue chercheur, puis affiché sans requête supplémentaire ».

### Relecture indépendante

Un agent neuf, sans accès à la conversation de conception, a relu le diff en lecture seule. Ses constats, tous traités :

| Constat | Gravité | Correction |
|---|---|---|
| Des valeurs Yousician (score sur 100) restaient affichées en « % » ou appelées probabilité : info-bulles, panneau du concept, vue chercheur, libellé accessible | intégrité | Formatage selon la source partout (`adapters.score` / `forecast`), textes de la tête de sortie selon la source ; contrôle de harnais qui échoue si un « % » apparaît pour Yousician (il échouait 12 fois avant la correction) |
| Un lien `?compare=` pouvait charger une séance future jamais visitée | intégrité | Un lien ne peut épingler qu'un moment antérieur ou égal ; un moment épinglé plus loin à la main est signalé comme tel ; scénario navigateur |
| Le focus clavier tombait sur la page après « Révéler » ou un clic de concept | accessibilité | Le focus passe au résultat révélé, ou au panneau du concept, et survit aux reconstructions ; scénario navigateur au clavier |
| Échelle et deux états sous 3:1 | contraste | Couleurs recalculées ; les barres de la frise (fond sombre) ont une teinte claire unique, la hauteur portant la valeur |
| Conseil « Avancez d'une séance » donné pour toutes les abstentions | mineur | Seulement quand l'historique manque |
| SingPAD : la prévision dépend aussi de la définition du groupe suivant | mineur | Texte « Ce que c'est » précisé |
| « À surveiller » et « Fragilités récurrentes » ne comptent pas les mêmes états | mineur | Critère affiché sous « À surveiller » |
| Texte « vrais parcours » en mode synthétique | mineur | Bandeau « données synthétiques » sur le Parcours quand c'est le cas |
| Le lanceur échouait si DÉCLIC tournait déjà sur le port | mineur | Avec `-Open`, il ouvre l'instance si c'est la même révision ; sinon il refuse comme avant |

### Visites simulées

*Élève, première visite.* Accueil : la phrase et le bouton principal suffisent pour entrer. Parcours : le profil est nommé « profil de démonstration » et la page dit d'où il vient. Deux frictions trouvées puis corrigées : rien n'expliquait pourquoi on commence au groupe 3 ni comment avancer (ajout d'une phrase sous « En bref »), et « séance » alternait avec « groupe » (la correspondance est maintenant dite une fois). Friction restante : les concepts SingPAD n'ont que des numéros ; c'est une limite des données, assumée et expliquée plutôt que masquée par des noms inventés.

*Professeur, première visite.* Accueil → « Inspecter le modèle » → Laboratoire : modèle servi, génération des données, révision du code, moyennes Phase 7 et limites, sans rien ouvrir. « Ouvrir le calcul d'une prévision » mène directement à la mémoire GRU d'un vrai calcul. Manque trouvé puis corrigé : le reçu de prévision était évoqué mais jamais montré.

## 7. Ce qui reste incomplet

* ~~Validation sur les données réelles privées~~ : faite le 27/10/2026 à partir des parcours préparés de la machine de livraison (voir ci-dessous).
* ~~Le lanceur annonçait `/web/living.html`~~ : corrigé après accord. Il affiche l'accueil, l'ouvre avec `-Open`, et `Lancer DECLIC.cmd` permet un lancement en double-clic.
* Les cinq anciennes pages gardent leur présentation d'origine (archives signalées), sans refonte.
* Pas de thème sombre : la scène d'usage (jour, projecteur) a guidé le choix d'un thème clair unique.
* Les noms musicaux des concepts SingPAD restent absents tant qu'aucune correspondance n'est publiée ou approuvée.
* Aucune évaluation avec de vrais élèves ou enseignants : les visites ci-dessus sont simulées.

## 7 bis. Validation sur les données réelles (27/10/2026)

* Données : les deux fichiers préparés de la machine de livraison (`runtime/musical-demo`, SingPAD et Yousician), lus avec les poids actifs du registre, sans modification.
* `pytest` avec ces données présentes : **428 réussis**, 2 ignorés (intégration PowerShell, Windows seulement). Le test Phase 8 qui exige les données privées passe.
* Playwright en mode `real_held_out_data` : **16/16 scénarios**.
* Machine de livraison : clone principal passé sur `main` (branche locale `latest`, qui suit `origin/main` ; aucun fichier non suivi touché), lancé par double-clic. Le lanceur annonce « DÉCLIC prêt », données privées, 8 parcours par base. Visite manuelle : accueil (« Démonstration prête… parcours réels du jeu de test »), Parcours SingPAD au groupe 8 sur 28 avec révélation (prévu 77,8 %, observé 91,7 %, écart affiché), Laboratoire (modèles servis, génération, révision `b4c5cd0`).
* La copie temporaire des données utilisée pour les tests a été supprimée ensuite ; elle n'a jamais été versionnée.

## 8. Lancer

Depuis la racine du dépôt, après préparation de l'environnement (voir `docs/START_WINDOWS.md`) :

```powershell
.\Launch.ps1 -Open
```

Avec `-Open` (ou en double-cliquant `Lancer DECLIC.cmd`), le lanceur ouvre l'accueil `http://127.0.0.1:8781/` ; le Parcours est à `/web/living.html`, le Laboratoire à `/web/labo.html`, le carnet à `/web/carnet.html`.

Vérifier :

```powershell
.\.venv\Scripts\python.exe -m pytest -q
$env:DECLIC_PYTHON = (Resolve-Path .venv\Scripts\python.exe).Path
npm ci; npx playwright install chromium; npm run test:browser      # montage synthétique + vrais poids

# Données privées réelles, sur la machine de livraison (dossier préparé par scripts/build_musical_demo.py) :
$env:DECLIC_E2E_REAL = '1'; $env:DECLIC_PREPARED_DATA = (Resolve-Path runtime\musical-demo).Path
npm run test:browser
```
