"""DÉCLIC instrument-free exercise library (learner loop, Phase 10).

Every exercise can be done with a computer only: sounds are synthesised in the browser from
the item specification served here, answers are given with buttons, an on-screen/computer
keyboard or by tapping the space bar. The server keeps the correct answer and scores it.

Difficulty is never an arbitrary label: each level states the stimulus parameter that changes
(cents, number of alternatives, melody length, contour, direction, tempo, clef, accidentals)
and the chance level, so it can be checked. Thresholds marked "provisoire" are DÉCLIC design
choices, not published norms. No exercise here is teacher-approved.
"""
from __future__ import annotations

import math
import random
import statistics

# ---------------------------------------------------------------- references (verified links)
REFERENCES = {
    'micheyl2006': {
        'citation': 'Micheyl, C., Delhommeau, K., Perrot, X. & Oxenham, A. J. (2006). Influence of musical and psychoacoustical training on pitch discrimination. Hearing Research, 219(1–2), 36–47.',
        'url': 'https://doi.org/10.1016/j.heares.2006.05.004',
        'supports': "Les seuils de discrimination de hauteur des non-musiciens sont au départ plus de six fois ceux des musiciens classiques ; 4 à 8 h d'entraînement adaptatif suffisent à les en rapprocher. La discrimination de hauteur s'entraîne."},
    'levitt1971': {
        'citation': 'Levitt, H. (1971). Transformed up-down methods in psychoacoustics. Journal of the Acoustical Society of America, 49(2B), 467–477.',
        'url': 'https://doi.org/10.1121/1.1912375',
        'supports': "La règle « 2 bonnes réponses → plus difficile, 1 erreur → plus facile » converge vers le niveau de 70,7 % de réussite : c'est la méthode de mesure du seuil."},
    'stambaugh2020': {
        'citation': 'Stambaugh, L. A. & Nichols, B. E. (2020). The relationships among interval identification, pitch error detection, and stimulus timbre by preservice teachers. Journal of Research in Music Education, 67(4), 465–480.',
        'url': 'https://doi.org/10.1177/0022429419885931',
        'supports': "Synthèse des études : intervalles mélodiques plus faciles que les harmoniques, ascendants plus faciles que descendants, octave la mieux reconnue, sixte mineure, septième mineure et triton les plus confondus. L'identification d'intervalles prédit la détection d'erreurs de hauteur (r = 0,75)."},
    'karpinski2000': {
        'citation': 'Karpinski, G. S. (2000). Aural Skills Acquisition: The Development of Listening, Reading, and Performing Skills in College-Level Musicians. Oxford University Press.',
        'url': 'https://journals-upgrade.shareok.org/jmtp/article/view/720',
        'supports': "Ouvrage de référence de la pédagogie de la formation de l'oreille : les compétences d'écoute sont traitées avant la lecture et l'exécution. Lien : compte rendu publié dans le Journal of Music Theory Pedagogy."},
    'gordon2012': {
        'citation': 'Gordon, E. E. (2012). Learning Sequences in Music: A Contemporary Music Learning Theory. GIA Publications.',
        'url': 'https://giamusic.com/resource/learning-sequences-in-music-2012-edition-book-g2345',
        'supports': "Théorie de l'apprentissage musical fondée sur l'audiation : le son avant le symbole. Justifie que la lecture vienne après l'écoute dans le parcours."},
    'dowling1978': {
        'citation': 'Dowling, W. J. (1978). Scale and contour: Two components of a theory of memory for melodies. Psychological Review, 85(4), 341–354.',
        'url': 'https://labs.utdallas.edu/mpac/files/2021/03/1978-2.pdf',
        'supports': "Pour une mélodie nouvelle, on retient d'abord le contour (montées/descentes), pas les intervalles exacts : un changement qui conserve le contour est plus difficile à détecter, surtout après transposition."},
    'wallentin2010': {
        'citation': 'Wallentin, M., Nielsen, A. H., Friis-Olivarius, M., Vuust, C. & Vuust, P. (2010). The Musical Ear Test, a new reliable test for measuring musical competence. Learning and Individual Differences, 20(3), 188–196.',
        'url': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10849222',
        'supports': "Test « pareil ou différent » sur paires de fragments mélodiques et rythmiques (52 + 52 essais), utilisé pour mesurer la compétence musicale. Lien : étude de validation (2024) qui décrit le format du test."},
    'law2012': {
        'citation': 'Law, L. N. C. & Zentner, M. (2012). Assessing musical abilities objectively: Construction and validation of the Profile of Music Perception Skills. PLoS ONE, 7(12), e52508.',
        'url': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC3532219/',
        'supports': "Batterie de perception musicale (mélodie, accord, hauteur, rythme, tempo…) au format comparaison de paires : modèle d'une évaluation séparée par compétence."},
    'mullensiefen2014': {
        'citation': 'Müllensiefen, D., Gingras, B., Musil, J. & Stewart, L. (2014). The musicality of non-musicians: An index for assessing musical sophistication in the general population. PLoS ONE, 9(2), e89642.',
        'url': 'https://research.gold.ac.uk/id/eprint/10160/',
        'supports': "Gold-MSI : les capacités d'écoute (mémoire mélodique, perception de la pulsation) varient fortement même chez les non-musiciens. Elles se mesurent sans instrument."},
    'repp2005': {
        'citation': 'Repp, B. H. (2005). Sensorimotor synchronization: A review of the tapping literature. Psychonomic Bulletin & Review, 12(6), 969–992.',
        'url': 'https://www.doi.org/10.3758/BF03206433',
        'supports': "Paradigme de référence : taper avec un métronome puis continuer seul (synchronisation–continuation) ; la variabilité des intervalles entre frappes mesure la précision temporelle."},
    'reppsu2013': {
        'citation': 'Repp, B. H. & Su, Y.-H. (2013). Sensorimotor synchronization: A review of recent research (2006–2012). Psychonomic Bulletin & Review, 20, 403–452.',
        'url': 'https://doi.org/10.3758/s13423-012-0371-2',
        'supports': "Mise à jour de la revue : la synchronisation dépend du tempo et de l'expertise musicale."},
    'fujii2013': {
        'citation': 'Fujii, S. & Schlaug, G. (2013). The Harvard Beat Assessment Test (H-BAT): a battery for assessing beat perception and production and their dissociation. Frontiers in Human Neuroscience, 7, 771.',
        'url': 'https://doi.org/10.3389/fnhum.2013.00771',
        'supports': "Percevoir la pulsation et la produire sont deux capacités dissociables : DÉCLIC les mesure séparément (rythmes pareils/différents vs tapotement)."},
    'anglada2022': {
        'citation': 'Anglada-Tort, M., Harrison, P. M. C. & Jacoby, N. (2022). REPP: A robust cross-platform solution for online sensorimotor synchronization experiments. Behavior Research Methods, 54.',
        'url': 'https://doi.org/10.3758/s13428-021-01722-2',
        'supports': "En ligne, clavier et navigateur ajoutent 60 à 100 ms de latence variable : l'asynchronie absolue n'est pas mesurable de façon fiable. DÉCLIC ne note donc que des grandeurs relatives (tempo, régularité, proportions)."},
    'bloom1968': {
        'citation': 'Bloom, B. S. (1968). Learning for mastery. Evaluation Comment, 1(2). UCLA Center for the Study of Evaluation of Instructional Programs.',
        'url': None,
        'supports': "Apprentissage par maîtrise : avancer quand un critère est atteint, avec des activités correctives sinon. Texte original sans lien stable vérifié ; voir la méta-analyse de Kulik et al. (1990), qui évalue ce modèle."},
    'kulik1990': {
        'citation': 'Kulik, C.-L. C., Kulik, J. A. & Bangert-Drowns, R. L. (1990). Effectiveness of mastery learning programs: A meta-analysis. Review of Educational Research, 60(2), 265–299.',
        'url': 'https://doi.org/10.3102/00346543060002265',
        'supports': "108 évaluations contrôlées : effet moyen +0,52 écart-type aux examens, au prix d'environ 4 % de temps en plus. Justifie le critère de maîtrise et les retours correctifs."},
    'cepeda2006': {
        'citation': 'Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T. & Rohrer, D. (2006). Distributed practice in verbal recall tasks: A review and quantitative synthesis. Psychological Bulletin, 132(3), 354–380.',
        'url': 'https://pubmed.ncbi.nlm.nih.gov/16719566/',
        'supports': "Espacer les révisions améliore la rétention : les séances ramènent des niveaux déjà maîtrisés, surtout ceux qui n'ont pas été travaillés depuis longtemps (preuve sur la mémoire verbale, transfert à la musique non démontré)."},
    'pelanek2016': {
        'citation': 'Pelánek, R. (2016). Applications of the Elo rating system in adaptive educational systems. Computers & Education.',
        'url': 'https://doi.org/10.1016/j.compedu.2016.03.017',
        'supports': "Modèle de référence de DÉCLIC : P(réussite) = 1/k + (1 − 1/k)·σ(θ − d), mise à jour θ ← θ + U(n)·(résultat − P), U(n) = a/(1 + b·n)."},
    'corbett1994': {
        'citation': 'Corbett, A. T. & Anderson, J. R. (1994). Knowledge tracing: Modeling the acquisition of procedural knowledge. User Modeling and User-Adapted Interaction, 4, 253–278.',
        'url': 'https://doi.org/10.1007/BF01099821',
        'supports': "Origine du knowledge tracing : prédire la réussite suivante à partir de la suite des tentatives, compétence par compétence. C'est la tâche d'O08."},
    'piech2015': {
        'citation': 'Piech, C. et al. (2015). Deep Knowledge Tracing. Advances in Neural Information Processing Systems 28.',
        'url': 'https://papers.neurips.cc/paper/2015/hash/bac9162b47c56fc8a4d2a519803d51b3-Abstract.html',
        'supports': "Version réseau récurrent du knowledge tracing, dont dérivent les réseaux GRU d'O08 ; ils exigent des données de nombreux apprenants pour être entraînés."},
}

NOTE_NAMES = ['do', 'do♯', 'ré', 'ré♯', 'mi', 'fa', 'fa♯', 'sol', 'sol♯', 'la', 'la♯', 'si']
LETTERS = ['do', 'ré', 'mi', 'fa', 'sol', 'la', 'si']
LETTER_SEMITONE = [0, 2, 4, 5, 7, 9, 11]
MAJOR = [0, 2, 4, 5, 7, 9, 11]
HARMONIC_MINOR = [0, 2, 3, 5, 7, 8, 11]

INTERVALS = {1: 'seconde mineure', 2: 'seconde majeure', 3: 'tierce mineure', 4: 'tierce majeure',
             5: 'quarte juste', 6: 'triton', 7: 'quinte juste', 8: 'sixte mineure', 9: 'sixte majeure',
             10: 'septième mineure', 11: 'septième majeure', 12: 'octave'}
CHORDS = {'maj': ('accord majeur', [0, 4, 7]), 'min': ('accord mineur', [0, 3, 7]),
          'dim': ('accord diminué', [0, 3, 6]), 'aug': ('accord augmenté', [0, 4, 8]),
          'maj7': ('septième majeure', [0, 4, 7, 11]), 'dom7': ('septième de dominante', [0, 4, 7, 10]),
          'min7': ('septième mineure', [0, 3, 7, 10]), 'hdim7': ('septième demi-diminuée', [0, 3, 6, 10]),
          'dim7': ('septième diminuée', [0, 3, 6, 9])}
DEGREES = {1: '1 · tonique', 2: '2 · sus-tonique', 3: '3 · médiante', 4: '4 · sous-dominante',
           5: '5 · dominante', 6: '6 · sus-dominante', 7: '7 · sensible'}
CADENCES = {'parfaite': ('cadence parfaite (V → I)', ['I', 'IV', 'V', 'I']),
            'plagale': ('cadence plagale (IV → I)', ['I', 'V', 'IV', 'I']),
            'demi': ('demi-cadence (→ V)', ['I', 'IV', 'I', 'V']),
            'rompue': ('cadence rompue (V → vi)', ['I', 'IV', 'V', 'vi'])}
PROGRESSIONS = {'p1': ['I', 'vi', 'IV', 'V'], 'p2': ['I', 'IV', 'V', 'I'], 'p3': ['I', 'V', 'vi', 'IV'], 'p4': ['ii', 'V', 'I', 'I']}
ROMAN = {'I': [0, 4, 7], 'ii': [2, 5, 9], 'IV': [5, 9, 12], 'V': [7, 11, 14], 'vi': [9, 12, 16],
         'i': [0, 3, 7], 'iv': [5, 8, 12]}

SKILLS = [
    {'id': 'hauteur', 'label': 'Hauteur', 'description': 'Entendre si un son est plus aigu ou plus grave qu’un autre, même de très peu.'},
    {'id': 'intervalles', 'label': 'Intervalles', 'description': 'Reconnaître l’écart entre deux notes (tierce, quinte, octave…).'},
    {'id': 'accords', 'label': 'Accords', 'description': 'Reconnaître la couleur d’un accord (majeur, mineur, diminué…).'},
    {'id': 'memoire', 'label': 'Mémoire mélodique', 'description': 'Retenir une courte mélodie et repérer un changement.'},
    {'id': 'reproduction', 'label': 'Reproduction au clavier', 'description': 'Rejouer sur le clavier de l’écran une mélodie entendue.'},
    {'id': 'pulsation', 'label': 'Pulsation', 'description': 'Garder un tempo régulier en tapant, avec puis sans métronome.'},
    {'id': 'rythme', 'label': 'Rythme', 'description': 'Percevoir et reproduire des motifs rythmiques.'},
    {'id': 'lecture', 'label': 'Lecture de notes', 'description': 'Nommer une note écrite sur la portée, en clé de sol et de fa.'},
    {'id': 'tonalite', 'label': 'Fonctions tonales', 'description': 'Situer une note ou une fin de phrase dans une tonalité (degrés, cadences).'},
]
SKILL_IDS = {s['id'] for s in SKILLS}


def _lv(level, label, criteria, params, choices=None):
    return {'level': level, 'label': label, 'criteria': criteria, 'params': params, 'choices': choices}


EXERCISES = [
    {'id': 'hauteur-comparaison', 'title': 'Plus aigu ou plus grave ?', 'skill': 'hauteur', 'response': 'choice', 'purpose': 'développer',
     'objective': "Affiner la perception des petites différences de hauteur, base de la justesse.",
     'prerequisites': [], 'mastery_window': 10,
     'instructions': ["Écoutez deux sons.", "Le second est-il plus aigu ou plus grave que le premier ?", "Vous pouvez réécouter deux fois."],
     'inputs': "Deux sons synthétisés par le navigateur ; la hauteur de départ change à chaque essai (220–440 Hz) pour empêcher de mémoriser un son fixe.",
     'expected': "Le sens de l’écart : plus aigu ou plus grave.",
     'correction': "Automatique côté serveur : la réponse est comparée au sens réel de l’écart.",
     'metrics': ['taux de réussite au niveau', 'écart en cents réussi', 'temps de réponse'],
     'references': ['micheyl2006', 'levitt1971'],
     'difficulty_basis': "Écart de hauteur en cents (100 cents = un demi-ton), divisé par deux à chaque niveau. Hasard : 50 %.",
     'levels': [_lv(1, '200 cents', 'Écart d’un ton', {'cents': 200}, 2), _lv(2, '100 cents', 'Écart d’un demi-ton', {'cents': 100}, 2),
                _lv(3, '50 cents', 'Quart de ton', {'cents': 50}, 2), _lv(4, '25 cents', 'Huitième de ton', {'cents': 25}, 2),
                _lv(5, '12 cents', 'Écart fin', {'cents': 12}, 2), _lv(6, '6 cents', 'Écart très fin', {'cents': 6}, 2)]},
    {'id': 'hauteur-seuil', 'title': 'Mesure du seuil de hauteur', 'skill': 'hauteur', 'response': 'choice', 'purpose': 'mesurer',
     'objective': "Mesurer le plus petit écart de hauteur que vous percevez de façon fiable.",
     'prerequisites': [], 'mastery_window': None,
     'instructions': ["Même tâche que « Plus aigu ou plus grave ? ».", "L’écart diminue après deux bonnes réponses et augmente après une erreur.", "Pas de correction pendant la mesure."],
     'inputs': "Deux sons synthétisés ; écart adaptatif de 400 à 3 cents.",
     'expected': "Le sens de l’écart à chaque essai.",
     'correction': "Escalier adaptatif (Levitt, 1971) : l’écart est divisé par deux à chaque bonne réponse jusqu’à la première erreur, puis 2 bonnes réponses → plus petit, 1 erreur → plus grand. Le seuil est la moyenne géométrique des écarts aux derniers changements de sens.",
     'metrics': ['seuil estimé en cents', 'nombre de changements de sens (fiabilité)'],
     'references': ['levitt1971', 'micheyl2006'],
     'difficulty_basis': "Adaptative : la difficulté suit vos réponses. Résultat indicatif avec peu d’essais.",
     'levels': [_lv(1, 'Adaptatif', 'Escalier 2 bonnes réponses / 1 erreur', {'start_cents': 200}, 2)]},
    {'id': 'intervalles', 'title': 'Reconnaître un intervalle', 'skill': 'intervalles', 'response': 'choice', 'purpose': 'développer et mesurer',
     'objective': "Nommer l’écart entre deux notes, compétence de base de la dictée et de la détection d’erreurs.",
     'prerequisites': ['hauteur-comparaison niveau 2'], 'mastery_window': 10,
     'instructions': ["Écoutez deux notes.", "Choisissez le nom de l’intervalle.", "Astuce : associez chaque intervalle au début d’une mélodie connue."],
     'inputs': "Deux notes synthétisées, successives (mélodique) ou simultanées (harmonique).",
     'expected': "Le nom de l’intervalle.",
     'correction': "Automatique ; les confusions (ex. sixte mineure ↔ septième mineure) sont comptées pour repérer les erreurs récurrentes.",
     'metrics': ['taux de réussite', 'matrice de confusion des intervalles', 'temps de réponse'],
     'references': ['stambaugh2020', 'karpinski2000'],
     'difficulty_basis': "Nombre de choix possibles (hasard = 1/nombre de choix), puis sens (montant avant descendant) et mode (mélodique avant harmonique), ordre documenté par Stambaugh & Nichols (2020).",
     'levels': [_lv(1, '4 intervalles montants', 'Seconde majeure, tierce majeure, quinte, octave · montants · hasard 25 %', {'set': [2, 4, 7, 12], 'mode': 'up'}, 4),
                _lv(2, '7 intervalles montants', 'Ajout seconde mineure, tierce mineure, quarte · hasard 14 %', {'set': [1, 2, 3, 4, 5, 7, 12], 'mode': 'up'}, 7),
                _lv(3, '12 intervalles montants', 'Tous les intervalles jusqu’à l’octave, dont triton et septièmes · hasard 8 %', {'set': list(range(1, 13)), 'mode': 'up'}, 12),
                _lv(4, '12 intervalles descendants', 'Mêmes 12 intervalles, joués en descendant', {'set': list(range(1, 13)), 'mode': 'down'}, 12),
                _lv(5, '12 intervalles harmoniques', 'Les deux notes ensemble', {'set': list(range(1, 13)), 'mode': 'harmonic'}, 12)]},
    {'id': 'accords', 'title': 'Couleur des accords', 'skill': 'accords', 'response': 'choice', 'purpose': 'développer et mesurer',
     'objective': "Reconnaître la qualité d’un accord à l’oreille.",
     'prerequisites': ['intervalles niveau 1'], 'mastery_window': 10,
     'instructions': ["Écoutez l’accord.", "Choisissez sa qualité.", "Majeur : lumineux et stable ; mineur : plus sombre."],
     'inputs': "Un accord synthétisé, notes jouées ensemble.",
     'expected': "La qualité de l’accord.",
     'correction': "Automatique ; confusions comptées.",
     'metrics': ['taux de réussite', 'confusions entre qualités'],
     'references': ['karpinski2000', 'law2012'],
     'difficulty_basis': "Nombre de qualités possibles, puis renversements (la basse n’est plus la fondamentale), puis accords de quatre sons.",
     'levels': [_lv(1, 'Majeur ou mineur', 'Deux qualités, état fondamental · hasard 50 %', {'set': ['maj', 'min'], 'inversions': False}, 2),
                _lv(2, '4 qualités de trois sons', '+ diminué, augmenté · hasard 25 %', {'set': ['maj', 'min', 'dim', 'aug'], 'inversions': False}, 4),
                _lv(3, '4 qualités renversées', 'Renversements aléatoires', {'set': ['maj', 'min', 'dim', 'aug'], 'inversions': True}, 4),
                _lv(4, '4 accords de septième', 'Septième majeure, de dominante, mineure, demi-diminuée · hasard 25 %', {'set': ['maj7', 'dom7', 'min7', 'hdim7'], 'inversions': False}, 4),
                _lv(5, '5 septièmes renversées', '+ septième diminuée, renversements · hasard 20 %', {'set': ['maj7', 'dom7', 'min7', 'hdim7', 'dim7'], 'inversions': True}, 5)]},
    {'id': 'melodies', 'title': 'Mélodies pareilles ou différentes ?', 'skill': 'memoire', 'response': 'choice', 'purpose': 'développer et mesurer',
     'objective': "Retenir une mélodie courte et détecter une note changée.",
     'prerequisites': [], 'mastery_window': 10,
     'instructions': ["Écoutez deux mélodies.", "Sont-elles identiques ?", "Aux niveaux transposés, la seconde commence plus haut ou plus bas : comparez la forme, pas la hauteur de départ."],
     'inputs': "Deux mélodies synthétisées.",
     'expected': "« Pareilles » ou « Différentes ».",
     'correction': "Automatique. Le type de changement (contour conservé ou non) est enregistré pour l’analyse des erreurs.",
     'metrics': ['taux de réussite', 'réussite sur changements qui conservent le contour'],
     'references': ['dowling1978', 'wallentin2010', 'mullensiefen2014'],
     'difficulty_basis': "Longueur de la mélodie (charge mémoire), changement qui conserve ou non le contour (Dowling, 1978), transposition, tonal ou atonal. Hasard : 50 %.",
     'levels': [_lv(1, '3 notes, contour changé', 'Le changement inverse une montée/descente', {'length': 3, 'contour': 'violate', 'transpose': False, 'tonal': True}, 2),
                _lv(2, '5 notes, contour changé', 'Mélodie plus longue', {'length': 5, 'contour': 'violate', 'transpose': False, 'tonal': True}, 2),
                _lv(3, '5 notes, contour conservé', 'Seule la taille d’un écart change', {'length': 5, 'contour': 'preserve', 'transpose': False, 'tonal': True}, 2),
                _lv(4, '7 notes transposées', 'Seconde mélodie transposée ; contour conservé', {'length': 7, 'contour': 'preserve', 'transpose': True, 'tonal': True}, 2),
                _lv(5, '9 notes atonales transposées', 'Sans tonalité, transposée, contour conservé', {'length': 9, 'contour': 'preserve', 'transpose': True, 'tonal': False}, 2)]},
    {'id': 'echo', 'title': 'Écho au clavier', 'skill': 'reproduction', 'response': 'keyboard', 'purpose': 'développer et mesurer',
     'objective': "Rejouer une mélodie entendue sur le clavier de l’écran : relier l’oreille au geste, sans instrument.",
     'prerequisites': ['melodies niveau 1'], 'mastery_window': 6,
     'instructions': ["Écoutez la mélodie (trois écoutes maximum).", "La première note est indiquée sur le clavier.", "Rejouez-la avec la souris ou les touches A Z E R T Y… du clavier de l’ordinateur, puis validez."],
     'inputs': "Une mélodie synthétisée ; votre réponse : la suite de notes jouées sur le clavier virtuel.",
     'expected': "La même suite de notes, dans le même ordre.",
     'correction': "Comparaison note par note ; réussi si toutes les notes sont justes. Les notes justes à l’octave près sont signalées.",
     'metrics': ['proportion de notes justes', 'réussite complète', 'nombre d’écoutes'],
     'references': ['karpinski2000', 'gordon2012'],
     'difficulty_basis': "Nombre de notes, taille des sauts, notes hors gamme (chromatiques), départ hors de do.",
     'levels': [_lv(1, '3 notes conjointes', 'Do–sol, pas de saut', {'length': 3, 'max_leap': 2, 'chromatic': False, 'range': [60, 67], 'free_start': False}),
                _lv(2, '4 notes avec sauts', 'Sauts jusqu’à la quarte', {'length': 4, 'max_leap': 5, 'chromatic': False, 'range': [60, 67], 'free_start': False}),
                _lv(3, '5 notes sur l’octave', 'Gamme de do, sauts jusqu’à la quinte', {'length': 5, 'max_leap': 7, 'chromatic': False, 'range': [60, 72], 'free_start': False}),
                _lv(4, '6 notes chromatiques', 'Une note hors gamme', {'length': 6, 'max_leap': 7, 'chromatic': True, 'range': [60, 72], 'free_start': False}),
                _lv(5, '7 notes, départ libre', 'Départ sur une autre note, une note hors gamme', {'length': 7, 'max_leap': 7, 'chromatic': True, 'range': [60, 79], 'free_start': True})]},
    {'id': 'pulsation', 'title': 'Garder la pulsation', 'skill': 'pulsation', 'response': 'tap', 'purpose': 'développer et mesurer',
     'objective': "Taper à tempo régulier avec un métronome, puis continuer seul.",
     'prerequisites': [], 'mastery_window': 6,
     'instructions': ["Cliquez sur « Démarrer » puis tapez la barre d’espace (ou le grand bouton) avec chaque clic.", "Quand le métronome s’arrête, continuez au même tempo jusqu’au signal de fin.", "Seule la régularité compte : un petit retard constant de votre ordinateur n’est pas pénalisé."],
     'inputs': "Clics de métronome ; vos frappes (barre d’espace ou toucher), horodatées par le navigateur.",
     'expected': "Des frappes régulières au tempo donné pendant la phase sans métronome.",
     'correction': "Intervalles entre frappes de la phase de continuation : écart de tempo moyen et coefficient de variation. Réussi si l’écart de tempo est ≤ 8 % et la variation ≤ 8 % (seuils provisoires DÉCLIC).",
     'metrics': ['écart de tempo (%)', 'coefficient de variation (%)', 'tendance à presser ou ralentir'],
     'references': ['repp2005', 'reppsu2013', 'fujii2013', 'anglada2022'],
     'difficulty_basis': "Tempo (les tempos lents sont plus difficiles à tenir), longueur de la continuation, nombre de clics de référence.",
     'levels': [_lv(1, '100 BPM, 8 + 8', '8 clics puis 8 frappes seul', {'bpm': 100, 'sync': 8, 'cont': 8}),
                _lv(2, '80 BPM, 8 + 8', 'Tempo plus lent', {'bpm': 80, 'sync': 8, 'cont': 8}),
                _lv(3, '120 BPM, 8 + 12', 'Tempo rapide, continuation plus longue', {'bpm': 120, 'sync': 8, 'cont': 12}),
                _lv(4, '60 BPM, 8 + 12', 'Tempo lent', {'bpm': 60, 'sync': 8, 'cont': 12}),
                _lv(5, '100 BPM, 4 + 16', 'Peu de référence, longue continuation', {'bpm': 100, 'sync': 4, 'cont': 16})]},
    {'id': 'rythmes', 'title': 'Rythmes pareils ou différents ?', 'skill': 'rythme', 'response': 'choice', 'purpose': 'développer et mesurer',
     'objective': "Percevoir la structure d’un rythme et repérer un déplacement.",
     'prerequisites': [], 'mastery_window': 10,
     'instructions': ["Écoutez deux rythmes d’une mesure.", "Sont-ils identiques ?"],
     'inputs': "Deux motifs rythmiques synthétisés à 90 BPM.",
     'expected': "« Pareils » ou « Différents ».",
     'correction': "Automatique ; le type de modification est enregistré.",
     'metrics': ['taux de réussite'],
     'references': ['wallentin2010', 'fujii2013'],
     'difficulty_basis': "Valeurs rythmiques utilisées : noires/croches, puis pointées, syncopes, doubles croches. Hasard : 50 %.",
     'levels': [_lv(1, 'Noires et croches', 'Valeurs simples', {'values': 'simple'}, 2),
                _lv(2, 'Notes pointées', '+ noire pointée–croche', {'values': 'dotted'}, 2),
                _lv(3, 'Syncopes', '+ croche–noire–croche', {'values': 'syncopated'}, 2),
                _lv(4, 'Doubles croches', '+ quatre doubles croches, croche–deux doubles', {'values': 'sixteenths'}, 2)]},
    {'id': 'rythme-echo', 'title': 'Reproduire un rythme', 'skill': 'rythme', 'response': 'tap', 'purpose': 'développer et mesurer',
     'objective': "Rejouer en tapant un rythme entendu.",
     'prerequisites': ['rythmes niveau 1', 'pulsation niveau 1'], 'mastery_window': 6,
     'instructions': ["Écoutez le décompte puis le rythme.", "Au signal, tapez le même rythme avec la barre d’espace.", "Le tempo peut être un peu différent : seules les proportions comptent."],
     'inputs': "Un motif rythmique synthétisé ; vos frappes horodatées.",
     'expected': "Le même nombre de frappes, dans les mêmes proportions.",
     'correction': "Les frappes sont mises à l’échelle du motif (première et dernière alignées) ; chaque frappe doit tomber à moins de 45 % de la plus petite valeur du motif.",
     'metrics': ['proportion de frappes bien placées', 'erreur maximale en temps'],
     'references': ['repp2005', 'anglada2022'],
     'difficulty_basis': "Mêmes valeurs rythmiques que l’exercice précédent : la tolérance se resserre avec les valeurs plus courtes.",
     'levels': [_lv(1, 'Noires et croches', 'Valeurs simples', {'values': 'simple'}),
                _lv(2, 'Notes pointées', 'Valeurs pointées', {'values': 'dotted'}),
                _lv(3, 'Syncopes', 'Syncopes', {'values': 'syncopated'}),
                _lv(4, 'Doubles croches', 'Valeurs courtes', {'values': 'sixteenths'})]},
    {'id': 'lecture', 'title': 'Lire une note', 'skill': 'lecture', 'response': 'staff', 'purpose': 'développer et mesurer',
     'objective': "Nommer rapidement une note écrite sur la portée.",
     'prerequisites': [], 'mastery_window': 10,
     'instructions': ["Une note s’affiche sur la portée.", "Choisissez son nom (et son altération au dernier niveau).", "Après la réponse, la note est jouée."],
     'inputs': "Une portée dessinée par la page ; réponse par boutons.",
     'expected': "Le nom de la note.",
     'correction': "Automatique ; le temps de réponse mesure l’aisance de lecture.",
     'metrics': ['taux de réussite', 'temps de réponse médian', 'confusions (ex. mi ↔ sol)'],
     'references': ['karpinski2000', 'gordon2012'],
     'difficulty_basis': "Étendue des notes, clé (sol puis fa), lignes supplémentaires, altérations. Hasard : 14 %, puis 5 % avec altérations.",
     'levels': [_lv(1, 'Clé de sol, do–sol', 'Cinq notes autour du do central', {'clef': 'treble', 'range': [28, 32], 'accidentals': False}, 7),
                _lv(2, 'Clé de sol, portée', 'Du do central au la aigu', {'clef': 'treble', 'range': [28, 40], 'accidentals': False}, 7),
                _lv(3, 'Clé de fa, portée', 'Du mi grave au do central', {'clef': 'bass', 'range': [16, 28], 'accidentals': False}, 7),
                _lv(4, 'Deux clés, lignes supplémentaires', 'Notes au-dessus et au-dessous de la portée', {'clef': 'both', 'range': None, 'accidentals': False}, 7),
                _lv(5, 'Deux clés, altérations', 'Dièses et bémols', {'clef': 'both', 'range': None, 'accidentals': True}, 21)]},
    {'id': 'degres', 'title': 'Degré dans la tonalité', 'skill': 'tonalite', 'response': 'choice', 'purpose': 'développer et mesurer',
     'objective': "Situer une note par rapport à la tonique après une cadence (oreille fonctionnelle).",
     'prerequisites': ['intervalles niveau 2'], 'mastery_window': 10,
     'instructions': ["Une courte cadence installe la tonalité.", "Puis une note est jouée : quel degré de la gamme est-ce ?"],
     'inputs': "Cadence I–IV–V–I puis une note, synthétisées ; tonalité changée à chaque essai.",
     'expected': "Le degré de la note (1 à 7).",
     'correction': "Automatique ; confusions de degrés comptées.",
     'metrics': ['taux de réussite', 'confusions de degrés'],
     'references': ['karpinski2000', 'gordon2012'],
     'difficulty_basis': "Nombre de degrés possibles, puis mode mineur.",
     'levels': [_lv(1, 'Degrés 1, 3, 5', 'Notes de l’accord de tonique · hasard 33 %', {'set': [1, 3, 5], 'mode': 'major'}, 3),
                _lv(2, 'Degrés 1 à 5', '· hasard 20 %', {'set': [1, 2, 3, 4, 5], 'mode': 'major'}, 5),
                _lv(3, 'Sept degrés, majeur', '· hasard 14 %', {'set': [1, 2, 3, 4, 5, 6, 7], 'mode': 'major'}, 7),
                _lv(4, 'Sept degrés, mineur', 'Mineur harmonique', {'set': [1, 2, 3, 4, 5, 6, 7], 'mode': 'minor'}, 7)]},
    {'id': 'cadences', 'title': 'Fins de phrase (cadences)', 'skill': 'tonalite', 'response': 'choice', 'purpose': 'développer et mesurer',
     'objective': "Reconnaître comment une phrase harmonique se termine.",
     'prerequisites': ['accords niveau 1', 'degres niveau 1'], 'mastery_window': 10,
     'instructions': ["Écoutez quatre accords.", "Choisissez le type de fin, ou la suite d’accords au dernier niveau."],
     'inputs': "Quatre accords synthétisés, tonalité changée à chaque essai.",
     'expected': "Le type de cadence ou la suite d’accords.",
     'correction': "Automatique.",
     'metrics': ['taux de réussite', 'confusions entre cadences'],
     'references': ['karpinski2000'],
     'difficulty_basis': "Nombre de types possibles (2 → 4), puis identification d’une suite complète de quatre accords.",
     'levels': [_lv(1, 'Parfaite ou demi', '· hasard 50 %', {'set': ['parfaite', 'demi']}, 2),
                _lv(2, '+ plagale', '· hasard 33 %', {'set': ['parfaite', 'demi', 'plagale']}, 3),
                _lv(3, 'Quatre cadences', '+ rompue · hasard 25 %', {'set': ['parfaite', 'demi', 'plagale', 'rompue']}, 4),
                _lv(4, 'Suite d’accords', 'Choisir la suite parmi quatre · hasard 25 %', {'set': ['p1', 'p2', 'p3', 'p4'], 'progression': True}, 4)]},
]
EXERCISE_BY_ID = {e['id']: e for e in EXERCISES}


class InvalidResponse(ValueError):
    """A response that cannot be scored (malformed, empty). Never recorded as a learner failure."""


def level_spec(exercise_id, level):
    ex = EXERCISE_BY_ID.get(exercise_id)
    if ex is None:
        raise KeyError('unknown_exercise')
    for lv in ex['levels']:
        if lv['level'] == level:
            return ex, lv
    raise KeyError('unknown_level')


def chance(exercise_id, level):
    ex, lv = level_spec(exercise_id, level)
    return 1 / lv['choices'] if lv.get('choices') else 0.0


def mastery_min(window, chance_level):
    """Smallest number of correct answers out of `window` that is >= 80 % and significant vs chance (p < 0.05)."""
    for k in range(math.ceil(0.8 * window), window + 1):
        tail = sum(math.comb(window, i) * chance_level ** i * (1 - chance_level) ** (window - i) for i in range(k, window + 1)) if chance_level else 0.0
        if tail < 0.05:
            return k
    return None


def card(ex):
    """The 10-field card shown in the library."""
    return {'id': ex['id'], 'title': ex['title'], 'skill': ex['skill'], 'purpose': ex['purpose'],
            'objective': ex['objective'], 'skills_assessed': [ex['skill']],
            'difficulty': {'basis': ex['difficulty_basis'],
                           'levels': [{k: lv[k] for k in ('level', 'label', 'criteria')} | {'chance': (1 / lv['choices']) if lv.get('choices') else None,
                                       'mastery_min': mastery_min(ex['mastery_window'], (1 / lv['choices']) if lv.get('choices') else 0.0) if ex['mastery_window'] else None}
                                      for lv in ex['levels']]},
            'prerequisites': ex['prerequisites'], 'instructions': ex['instructions'], 'inputs': ex['inputs'],
            'expected': ex['expected'], 'correction': ex['correction'], 'metrics': ex['metrics'],
            'references': [{'key': k, **REFERENCES[k]} for k in ex['references']],
            'response': ex['response'], 'mastery_window': ex['mastery_window'], 'teacher_approved': False}


# ---------------------------------------------------------------- generation helpers
def _tone(t, d, midi=None, hz=None, v=0.8):
    e = {'t': round(t, 4), 'd': round(d, 4), 'v': v}
    if hz is not None:
        e['hz'] = round(hz, 4)
    else:
        e['midi'] = int(midi)
    return e


def _click(t, accent=False):
    return {'t': round(t, 4), 'd': 0.05, 'click': 'accent' if accent else 'normal'}


def _contour(seq):
    return [(b > a) - (b < a) for a, b in zip(seq, seq[1:])]


def _scale_notes(tonic, scale, low, high):
    out = []
    for octave in range(-2, 3):
        for s in scale:
            n = tonic + 12 * octave + s
            if low <= n <= high:
                out.append(n)
    return sorted(set(out))


def _melody(rng, length, tonal, low=60, high=74, max_leap=5):
    pool = _scale_notes(60, MAJOR, low, high) if tonal else list(range(low, high + 1))
    for _ in range(200):
        seq = [rng.choice(pool)]
        while len(seq) < length:
            options = [n for n in pool if 0 < abs(n - seq[-1]) <= max_leap]
            seq.append(rng.choice(options))
        if len(set(_contour(seq))) > 1 or length <= 2:
            return seq
    return seq


def _alter(rng, seq, mode, tonal, low=55, high=79):
    pool = _scale_notes(60, MAJOR, low, high) if tonal else list(range(low, high + 1))
    base = _contour(seq)
    idxs = list(range(1, len(seq)))
    rng.shuffle(idxs)
    for i in idxs:
        cands = [n for n in pool if n != seq[i] and abs(n - seq[i]) <= 7]
        rng.shuffle(cands)
        for n in cands:
            new = seq[:i] + [n] + seq[i + 1:]
            same_contour = _contour(new) == base
            if (mode == 'preserve' and same_contour) or (mode == 'violate' and not same_contour):
                return new, i
    raise RuntimeError('no alteration found')


RHYTHM_CELLS = {
    'simple': [[1], [0.5, 0.5]],
    'dotted': [[1], [0.5, 0.5], [1.5, 0.5]],
    'syncopated': [[1], [0.5, 0.5], [1.5, 0.5], [0.5, 1, 0.5]],
    'sixteenths': [[1], [0.5, 0.5], [0.25, 0.25, 0.25, 0.25], [0.5, 0.25, 0.25], [0.5, 1, 0.5]],
}


def _rhythm(rng, values):
    cells = RHYTHM_CELLS[values]
    for _ in range(200):
        durations, total = [], 0.0
        while total < 4 - 1e-9:
            fit = [c for c in cells if total + sum(c) <= 4 + 1e-9]
            cell = rng.choice(fit)
            durations += cell
            total += sum(cell)
        if len(durations) >= 4 and len(set(durations)) > 1:
            return durations
    return durations


def _onsets(durations):
    out, t = [], 0.0
    for d in durations:
        out.append(round(t, 4))
        t += d
    return out


def _rhythm_variant(rng, durations):
    for _ in range(200):
        i = rng.randrange(len(durations) - 1)
        a, b = durations[i], durations[i + 1]
        if a != b:
            new = durations[:i] + [b, a] + durations[i + 2:]
            return new, 'permutation'
        unit = min(durations)
        if a - unit > 0:
            new = durations[:i] + [a - unit, b + unit] + durations[i + 2:]
            if new != durations:
                return new, 'déplacement'
    raise RuntimeError('no rhythm variant')


def _chord_events(t, notes, d=1.6, v=0.55):
    return [_tone(t, d, midi=n, v=v) for n in notes]


def _roman_chord(tonic, roman):
    base = tonic - 12
    notes = [base + i for i in ROMAN[roman]]
    return [notes[0] - 12] + notes


def _choice_options(pairs):
    return [{'value': str(v), 'label': label} for v, label in pairs]


def generate(exercise_id, level, rng: random.Random, *, cents=None):
    """Return (served, answer). ``served`` is all the browser needs; ``answer`` stays server-side."""
    ex, lv = level_spec(exercise_id, level)
    p = lv['params']
    if exercise_id in ('hauteur-comparaison', 'hauteur-seuil'):
        c = float(cents if cents is not None else p.get('cents', p.get('start_cents', 200)))
        f0 = 220 * 2 ** rng.uniform(0, 1)
        direction = rng.choice(['higher', 'lower'])
        f1 = f0 * 2 ** ((c if direction == 'higher' else -c) / 1200)
        served = {'prompt': 'Le second son est-il plus aigu ou plus grave ?',
                  'audio': [_tone(0, 0.5, hz=f0), _tone(0.9, 0.5, hz=f1)],
                  'options': _choice_options([('higher', 'Plus aigu'), ('lower', 'Plus grave')]),
                  'replays': 2, 'detail': {'cents': round(c, 2)}}
        return served, {'value': direction, 'cents': c}
    if exercise_id == 'intervalles':
        size = rng.choice(p['set'])
        low = rng.randint(55, 67)
        if p['mode'] == 'down':
            low += size
            notes, audio = [low, low - size], [_tone(0, 0.8, midi=low), _tone(0.9, 0.8, midi=low - size)]
        elif p['mode'] == 'harmonic':
            notes, audio = [low, low + size], [_tone(0, 1.6, midi=low, v=0.6), _tone(0, 1.6, midi=low + size, v=0.6)]
        else:
            notes, audio = [low, low + size], [_tone(0, 0.8, midi=low), _tone(0.9, 0.8, midi=low + size)]
        served = {'prompt': 'Quel est cet intervalle ?', 'audio': audio, 'replays': 2,
                  'options': _choice_options([(s, INTERVALS[s]) for s in p['set']])}
        return served, {'value': str(size), 'notes': notes}
    if exercise_id == 'accords':
        quality = rng.choice(p['set'])
        root = rng.randint(50, 60)
        notes = [root + i for i in CHORDS[quality][1]]
        inversion = 0
        if p['inversions']:
            inversion = rng.randrange(len(notes))
            for _ in range(inversion):
                notes = notes[1:] + [notes[0] + 12]
        served = {'prompt': 'Quelle est la couleur de cet accord ?', 'audio': _chord_events(0, notes), 'replays': 2,
                  'options': _choice_options([(q, CHORDS[q][0]) for q in p['set']])}
        return served, {'value': quality, 'notes': notes, 'inversion': inversion}
    if exercise_id == 'melodies':
        tonal = p['tonal']
        first = _melody(rng, p['length'], tonal, 60, 74, 5 if tonal else 6)
        same = rng.random() < 0.5
        second, changed = (first[:], None) if same else _alter(rng, first, p['contour'], tonal)
        shift = 0
        if p['transpose']:
            shift = rng.choice([-5, -4, -3, 3, 4, 5])
            second = [n + shift for n in second]
        step = 0.42
        gap = step * len(first) + 1.0
        audio = [_tone(i * step, step * 0.9, midi=n) for i, n in enumerate(first)]
        audio += [_tone(gap + i * step, step * 0.9, midi=n) for i, n in enumerate(second)]
        served = {'prompt': 'Les deux mélodies sont-elles pareilles ?' + (' (la seconde est transposée)' if p['transpose'] else ''),
                  'audio': audio, 'replays': 1,
                  'options': _choice_options([('same', 'Pareilles'), ('different', 'Différentes')])}
        return served, {'value': 'same' if same else 'different', 'changed_index': changed, 'contour': p['contour'], 'shift': shift}
    if exercise_id == 'echo':
        low, high = p['range']
        tonic = 60
        if p['free_start']:
            tonic = rng.choice([62, 64, 65, 67])
        pool = _scale_notes(tonic, MAJOR, low, high)
        for _ in range(500):
            seq = [tonic if not p['free_start'] else rng.choice([n for n in pool if n <= low + 9])]
            while len(seq) < p['length']:
                options = [n for n in pool if 0 < abs(n - seq[-1]) <= p['max_leap']]
                seq.append(rng.choice(options))
            if p['chromatic']:
                i = rng.randrange(1, len(seq))
                cand = [seq[i] + d for d in (-1, 1) if low <= seq[i] + d <= high and (seq[i] + d - tonic) % 12 not in MAJOR]
                if not cand:
                    continue
                seq[i] = rng.choice(cand)
            if len(set(seq)) > 1:
                break
        step = 0.55
        served = {'prompt': 'Rejouez la mélodie sur le clavier.', 'audio': [_tone(i * step, step * 0.9, midi=n) for i, n in enumerate(seq)],
                  'replays': 2, 'keyboard': {'low': 60, 'high': 83, 'start': seq[0], 'length': len(seq)}}
        return served, {'notes': seq}
    if exercise_id == 'pulsation':
        ioi = 60 / p['bpm']
        audio = [_click(k * ioi, accent=(k == 0)) for k in range(p['sync'])]
        end = (p['sync'] + p['cont']) * ioi
        served = {'prompt': 'Tapez avec les clics, puis continuez seul jusqu’au signal de fin.', 'audio': audio, 'replays': 0,
                  'tap': {'window': round(end + ioi * 0.6, 3), 'expected': p['sync'] + p['cont'], 'ioi': round(ioi, 4), 'sync': p['sync'], 'cont': p['cont'],
                          'end_signal': round(end + ioi * 0.6, 3)}}
        return served, {'ioi': ioi, 'sync': p['sync'], 'cont': p['cont']}
    if exercise_id in ('rythmes', 'rythme-echo'):
        beat = 60 / 90
        durations = _rhythm(rng, p['values'])
        if exercise_id == 'rythmes':
            same = rng.random() < 0.5
            other, how = (durations[:], None) if same else _rhythm_variant(rng, durations)
            first = [_click(o * beat) for o in _onsets(durations)]
            second_start = 4 * beat + 2 * beat
            second = [_click(second_start + o * beat) for o in _onsets(other)]
            served = {'prompt': 'Les deux rythmes sont-ils pareils ?', 'audio': first + second, 'replays': 1,
                      'options': _choice_options([('same', 'Pareils'), ('different', 'Différents')])}
            return served, {'value': 'same' if same else 'different', 'change': how, 'durations': durations}
        count_in = [_click(k * beat, accent=True) for k in range(4)]
        pattern = [_tone(4 * beat + o * beat, 0.12, midi=76, v=0.7) for o in _onsets(durations)]
        listen_end = 8 * beat + 0.6
        served = {'prompt': 'Écoutez, puis tapez le même rythme après le signal.', 'audio': count_in + pattern, 'replays': 2,
                  'tap': {'after': round(listen_end, 3), 'expected': len(durations), 'window': 12.0, 'free': True}}
        return served, {'onsets': _onsets(durations), 'durations': durations}
    if exercise_id == 'lecture':
        clef = p['clef'] if p['clef'] != 'both' else rng.choice(['treble', 'bass'])
        if p['range']:
            lo, hi = p['range']
        else:
            lo, hi = (26, 44) if clef == 'treble' else (14, 30)
        index = rng.randint(lo, hi)
        letter, octave = index % 7, index // 7
        accidental = None
        if p['accidentals'] and rng.random() < 0.7:
            accidental = rng.choice(['sharp', 'flat'])
        midi = 12 * (octave + 1) + LETTER_SEMITONE[letter] + {'sharp': 1, 'flat': -1, None: 0}[accidental]
        served = {'prompt': 'Quelle est cette note ?', 'audio': [], 'replays': 0,
                  'staff': {'clef': clef, 'letter': letter, 'octave': octave, 'accidental': accidental},
                  'options': _choice_options([(l, l) for l in LETTERS]), 'accidentals': bool(p['accidentals'])}
        return served, {'value': LETTERS[letter], 'accidental': accidental or 'natural', 'midi': midi}
    if exercise_id == 'degres':
        minor = p['mode'] == 'minor'
        tonic = rng.choice([57, 60, 62, 64, 65, 67])
        scale = HARMONIC_MINOR if minor else MAJOR
        prog = ['i', 'iv', 'V', 'i'] if minor else ['I', 'IV', 'V', 'I']
        audio = []
        for k, roman in enumerate(prog):
            audio += _chord_events(k * 0.9, _roman_chord(tonic, roman), d=0.85, v=0.4)
        degree = rng.choice(p['set'])
        target = tonic + scale[degree - 1]
        audio.append(_tone(4 * 0.9 + 0.8, 1.2, midi=target))
        served = {'prompt': 'Quel est le degré de la dernière note ?', 'audio': audio, 'replays': 2,
                  'options': _choice_options([(d, DEGREES[d]) for d in p['set']])}
        return served, {'value': str(degree), 'tonic': tonic, 'mode': p['mode']}
    if exercise_id == 'cadences':
        tonic = rng.choice([60, 62, 65, 67])
        if p.get('progression'):
            key = rng.choice(p['set'])
            prog = PROGRESSIONS[key]
            options = _choice_options([(k, ' – '.join(PROGRESSIONS[k])) for k in p['set']])
        else:
            key = rng.choice(p['set'])
            prog = CADENCES[key][1]
            options = _choice_options([(k, CADENCES[k][0]) for k in p['set']])
        audio = []
        for k, roman in enumerate(prog):
            audio += _chord_events(k * 1.0, _roman_chord(tonic, roman), d=0.95, v=0.4)
        served = {'prompt': 'Comment se termine cette phrase ?' if not p.get('progression') else 'Quelle suite d’accords entendez-vous ?',
                  'audio': audio, 'replays': 2, 'options': options}
        return served, {'value': key, 'tonic': tonic}
    raise KeyError('unknown_exercise')


# ---------------------------------------------------------------- scoring
def _finite_list(values, cap):
    if not isinstance(values, list) or len(values) > cap:
        raise InvalidResponse('Réponse illisible.')
    out = []
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise InvalidResponse('Réponse illisible.')
        out.append(float(v))
    return out


def evaluate(exercise_id, level, served, answer, response):
    """Return {'correct','score','details','feedback','error_key'}; raise InvalidResponse if unscorable."""
    ex, lv = level_spec(exercise_id, level)
    if not isinstance(response, dict):
        raise InvalidResponse('Réponse illisible.')
    kind = ex['response']
    if kind == 'choice':
        choice = response.get('choice')
        valid = {o['value'] for o in served['options']}
        if not isinstance(choice, str) or choice not in valid:
            raise InvalidResponse('Choisissez une des réponses proposées.')
        correct = choice == answer['value']
        label = {o['value']: o['label'] for o in served['options']}
        details = {'given': choice, 'expected': answer['value'], 'given_label': label[choice], 'expected_label': label[answer['value']]}
        for k in ('cents', 'contour', 'change', 'inversion', 'shift'):
            if k in answer:
                details[k] = answer[k]
        feedback = f"Bonne réponse : {label[answer['value']]}." if correct else f"La réponse était : {label[answer['value']]}."
        error_key = None if correct else f"{label[answer['value']]} pris pour {label[choice]}"
        return {'correct': correct, 'score': 1.0 if correct else 0.0, 'details': details, 'feedback': feedback, 'error_key': error_key}
    if kind == 'staff':
        letter = response.get('choice')
        if not isinstance(letter, str) or letter not in LETTERS:
            raise InvalidResponse('Choisissez un nom de note.')
        accidental = response.get('accidental', 'natural')
        if accidental not in ('natural', 'sharp', 'flat'):
            raise InvalidResponse('Altération inconnue.')
        if not served.get('accidentals'):
            accidental = 'natural'
        correct = letter == answer['value'] and accidental == answer['accidental']
        names = {'natural': '', 'sharp': '♯', 'flat': '♭'}
        expected = answer['value'] + names[answer['accidental']]
        given = letter + names[accidental]
        return {'correct': correct, 'score': 1.0 if correct else 0.0,
                'details': {'given': given, 'expected': expected, 'clef': served['staff']['clef'], 'reveal_midi': answer['midi']},
                'feedback': f'C’était bien {expected}.' if correct else f'C’était {expected} ({"clé de sol" if served["staff"]["clef"] == "treble" else "clé de fa"}).',
                'error_key': None if correct else f'{expected} lu comme {given}'}
    if kind == 'keyboard':
        notes = response.get('notes')
        if not isinstance(notes, list) or not notes or len(notes) > 32 or any(isinstance(n, bool) or not isinstance(n, int) or not 21 <= n <= 108 for n in notes):
            raise InvalidResponse('Jouez au moins une note sur le clavier avant de valider.')
        target = answer['notes']
        right = sum(1 for a, b in zip(notes, target) if a == b)
        octave = sum(1 for a, b in zip(notes, target) if a != b and (a - b) % 12 == 0)
        correct = notes == target
        score = right / len(target)
        names = lambda seq: ' '.join(NOTE_NAMES[n % 12] for n in seq)
        if correct:
            feedback = 'Toutes les notes sont justes, dans le bon ordre.'
        elif len(notes) != len(target):
            feedback = f'{len(notes)} notes jouées pour {len(target)} attendues. La mélodie était : {names(target)}.'
        else:
            feedback = f'{right} note(s) juste(s) sur {len(target)}. La mélodie était : {names(target)}.'
        first_wrong = next((i for i, (a, b) in enumerate(zip(notes, target)) if a != b), None)
        return {'correct': correct, 'score': score,
                'details': {'given': notes, 'expected': target, 'right': right, 'octave_errors': octave, 'length_given': len(notes)},
                'feedback': feedback, 'error_key': None if correct else ('nombre de notes' if len(notes) != len(target) else
                                                                     'bonne forme, mauvaise octave' if octave and right + octave == len(target) else f'erreur à la note {first_wrong + 1}')}
    if kind == 'tap':
        taps = sorted(_finite_list(response.get('taps'), 200))
        if exercise_id == 'pulsation':
            return _score_pulse(answer, taps)
        return _score_rhythm(answer, taps)
    raise InvalidResponse('Type de réponse inconnu.')


def _score_pulse(answer, taps):
    ioi, n_sync, n_cont = answer['ioi'], answer['sync'], answer['cont']
    if len(taps) < 3:
        raise InvalidResponse('Aucune frappe détectée (ou presque). Tapez la barre d’espace avec les clics, puis recommencez.')
    boundary = (n_sync - 1) * ioi + ioi / 2
    cont = [t for t in taps if t > boundary]
    sync_last = [t for t in taps if t <= boundary][-1:]
    seq = sync_last + cont
    itis = [b - a for a, b in zip(seq, seq[1:])]
    kept = [i for i in itis if 0.4 * ioi <= i <= 1.8 * ioi]
    details = {'target_ms': round(ioi * 1000), 'continuation_taps': len(cont), 'expected_continuation': n_cont,
               'discarded_intervals': len(itis) - len(kept)}
    if len(cont) < max(3, n_cont // 2):
        details.update(reason='arrêt prématuré')
        return {'correct': False, 'score': 0.0, 'details': details,
                'feedback': f'Vous avez continué {len(cont)} frappe(s) sur {n_cont} après l’arrêt du métronome. Essayez de tenir jusqu’au signal de fin.',
                'error_key': 'arrêt prématuré'}
    if len(kept) < 2 or len(kept) < 0.75 * len(itis):
        details.update(reason='frappes irrégulières')
        return {'correct': False, 'score': 0.0, 'details': details,
                'feedback': 'Trop de frappes doublées ou oubliées pour mesurer un tempo. Une frappe par clic, régulière.',
                'error_key': 'frappes irrégulières'}
    mean = statistics.fmean(kept)
    cv = statistics.pstdev(kept) / mean
    tempo_error = (mean - ioi) / ioi
    correct = abs(tempo_error) <= 0.08 and cv <= 0.08
    score = max(0.0, 1 - max(abs(tempo_error), cv) / 0.16)
    tendency = 'presse' if tempo_error < -0.04 else 'ralentit' if tempo_error > 0.04 else 'stable'
    details.update(mean_iti_ms=round(mean * 1000, 1), tempo_error_pct=round(tempo_error * 100, 1), cv_pct=round(cv * 100, 1), tendency=tendency)
    if correct:
        feedback = f'Régulier : écart de tempo {tempo_error * 100:+.1f} %, variation {cv * 100:.1f} %.'
    else:
        parts = []
        if abs(tempo_error) > 0.08:
            parts.append(f"vous {'pressez' if tempo_error < 0 else 'ralentissez'} ({tempo_error * 100:+.1f} %)")
        if cv > 0.08:
            parts.append(f'les intervalles varient de {cv * 100:.1f} %')
        feedback = 'Pas encore : ' + ' et '.join(parts) + '. Seuil : 8 %.'
    error_key = None if correct else {'presse': 'tempo trop rapide (vous pressez)', 'ralentit': 'tempo trop lent (vous ralentissez)'}.get(tendency, 'frappes irrégulières')
    return {'correct': correct, 'score': round(score, 3), 'details': details, 'feedback': feedback, 'error_key': error_key}


def _score_rhythm(answer, taps):
    onsets = answer['onsets']
    if len(taps) < 2:
        raise InvalidResponse('Moins de deux frappes : tapez le rythme entendu avec la barre d’espace, puis validez.')
    n = len(onsets)
    details = {'taps': len(taps), 'expected': n}
    if len(taps) != n:
        return {'correct': False, 'score': 0.0, 'details': details,
                'feedback': f'{len(taps)} frappes pour {n} attendues.', 'error_key': 'nombre de frappes'}
    span_p = onsets[-1] - onsets[0]
    span_t = taps[-1] - taps[0]
    if span_t <= 0:
        raise InvalidResponse('Frappes simultanées : recommencez.')
    scaled = [(t - taps[0]) / span_t * span_p for t in taps]
    errors = [abs(s - (o - onsets[0])) for s, o in zip(scaled, onsets)]
    smallest = min(b - a for a, b in zip(onsets, onsets[1:]))
    tolerance = 0.45 * smallest
    within = sum(e <= tolerance for e in errors)
    correct = within == n
    details.update(max_error_beats=round(max(errors), 3), tolerance_beats=round(tolerance, 3), within=within,
                   tempo_ratio=round(span_t / (span_p * 60 / 90), 3))
    worst = max(range(n), key=lambda i: errors[i])
    return {'correct': correct, 'score': within / n, 'details': details,
            'feedback': 'Rythme juste.' if correct else f'{within} frappe(s) bien placée(s) sur {n} ; la plus éloignée est la n° {worst + 1}.',
            'error_key': None if correct else 'frappes mal placées'}


def staircase_threshold(trials):
    """Levitt (1971) transformed staircase on cents. trials: list of (cents, correct).

    Fast start: until the first error, each correct answer halves the gap (1-down, factor 2),
    so a short assessment reaches the useful range. From the first error on: 2-down/1-up with
    factor sqrt(2), which converges on the 70.7 % point. The threshold is the geometric mean
    of the gaps at the last four reversals (fewer if not available, flagged as indicative)."""
    cents, streak, direction, reversals, started = 200.0, 0, None, [], False
    for c, ok in trials:
        cents = c
        if ok:
            streak += 1
            if not started or streak == 2:
                streak = 0
                if direction == 'up':
                    reversals.append(cents)
                direction = 'down'
                cents = max(3.0, cents / (2 if not started else math.sqrt(2)))
        else:
            started = True
            streak = 0
            if direction == 'down':
                reversals.append(cents)
            direction = 'up'
            cents = min(400.0, cents * math.sqrt(2))
    last = reversals[-4:]
    estimate = math.exp(statistics.fmean(math.log(c) for c in last)) if last else None
    correct = [c for c, ok in trials if ok]
    return {'next_cents': round(cents, 2), 'reversals': len(reversals), 'trials': len(trials),
            'threshold_cents': round(estimate, 1) if estimate else None,
            'lowest_correct_cents': round(min(correct), 1) if correct else None,
            'reliability': 'aucun changement de sens : seuil non estimé' if not reversals else
                           'indicatif (moins de 4 changements de sens)' if len(reversals) < 4 else 'estimé sur 4 changements de sens'}
