# Phase 11 · Résultats chiffrés de l’étude de simulation (données SYNTHÉTIQUES)

> Généré par `scripts/report_simulation.py` à partir de `artifacts/simulation/sim-2026-11/`. Aucun chiffre n’est saisi à la main. Les élèves sont simulés : ces résultats ne valident aucun modèle sur de vrais élèves.

## 1. Campagnes réellement exécutées

| Campagne | Simulateur | Élèves | Actifs ≥ 1 fois | Séances | Terminées | Questions | Justes | Abandons | Retours | Pauses | Actifs à la fin | Exports O08 acceptés | Durée (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | A | 200 | 197 | 4354 | 4109 | 48263 | 70 % | 58 | 14 | 198 | 134 | 200 | 840 |
| A2 | A | 200 | 198 | 4293 | 4067 | 47864 | 69 % | 55 | 14 | 217 | 137 | 200 | 877 |
| A3 | A | 200 | 194 | 4446 | 4214 | 49767 | 70 % | 48 | 14 | 201 | 141 | 200 | 788 |
| B1 | B | 200 | 199 | 4171 | 3969 | 46581 | 68 % | 43 | 11 | 258 | 143 | 200 | 765 |
| N1 | A ×1.5 | 200 | 198 | 4049 | 3817 | 43472 | 57 % | 58 | 17 | 232 | 137 | 200 | 648 |
| L1 | A | 1000 | 990 | 21693 | 20550 | 243162 | 70 % | 263 | 78 | 1053 | 716 | 1000 | 4180 |

### Campagne principale A1 : courbes des familles (niveau caché moyen, 0 = débutant typique, 1 = expert typique)

| Famille | Élèves | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | Gain moyen | Écart-type du gain |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Musicien expérimenté | 28 | 0,825 | 0,828 | 0,830 | 0,833 | 0,835 | 0,837 | 0,838 | 0,840 | 0,015 | 0,007 |
| Bonne oreille, rythme faible | 32 | 0,448 | 0,460 | 0,473 | 0,484 | 0,491 | 0,497 | 0,501 | 0,503 | 0,055 | 0,025 |
| Irrégulier, longues pauses | 32 | 0,345 | 0,352 | 0,356 | 0,357 | 0,358 | 0,358 | 0,356 | 0,356 | 0,011 | 0,010 |
| Bon rythme, difficultés mélodiques | 32 | 0,316 | 0,328 | 0,338 | 0,347 | 0,354 | 0,360 | 0,366 | 0,370 | 0,053 | 0,026 |
| En difficulté, progresse lentement | 32 | -0,147 | -0,140 | -0,134 | -0,130 | -0,127 | -0,125 | -0,123 | -0,122 | 0,025 | 0,015 |
| Débutant motivé | 44 | 0,124 | 0,153 | 0,178 | 0,197 | 0,211 | 0,224 | 0,236 | 0,248 | 0,123 | 0,041 |

Diversité : 200 courbes hebdomadaires distinctes sur 200 élèves ; gain individuel de -0,002 à 0,214 (écart-type 0,048).

| Exercice | Questions | Réussite | Niveau moyen | Niveau max |
|---|---|---|---|---|
| lecture | 10913 | 63 % | 1,37 | 5 |
| melodies | 9440 | 68 % | 1,22 | 4 |
| rythmes | 9152 | 62 % | 1,10 | 4 |
| pulsation | 4933 | 73 % | 1,45 | 5 |
| hauteur-comparaison | 4232 | 96 % | 1,79 | 6 |
| echo | 3155 | 60 % | 1,42 | 5 |
| hauteur-seuil | 2364 | 79 % | 1,00 | 1 |
| intervalles | 2127 | 87 % | 1,33 | 4 |
| accords | 1059 | 61 % | 1,12 | 3 |
| rythme-echo | 751 | 84 % | 1,43 | 4 |
| degres | 133 | 81 % | 1,27 | 2 |
| cadences | 4 | 100 % | 1,00 | 1 |

## 2. GRU DÉCLIC entraîné (A1)

EnhancedGRU, 19149 paramètres, mémoire 48, contexte 64, 9 compétences, 50 exercices@niveau. Élèves : 137 entraînement / 30 validation / 30 test. 12 époques, meilleure : 12, 7,9 s sur CPU. Empreinte `61b51b0e4321d945`.

## 3. Elo vs GRU vs naïf

### 3.1 Test A1 (30 élèves jamais vus, 6419 questions communes, GRU graine 42)

| Modèle | Brier | IC 95 % (élèves) | Log-loss | IC 95 % (élèves) | AUC | ECE | Élèves évalués | Couverture des prévisions |
|---|---|---|---|---|---|---|---|---|
| Elo (declic-elo-v1) | 0,1879 | [0,1726 ; 0,2008] | 0,5519 | [0,5155 ; 0,5828] | 0,717 | 0,021 | 30 | 87 % |
| GRU DÉCLIC | 0,1864 | [0,1715 ; 0,1993] | 0,5455 | [0,5091 ; 0,5764] | 0,719 | 0,021 | 30 | 100 % |
| Naïf | 0,1931 | [0,1789 ; 0,2049] | 0,5671 | [0,5335 ; 0,5956] | 0,709 | 0,054 | 30 | 100 % |

| Différence (négatif = le premier modèle a moins d’erreur) | Brier | IC 95 % | Log-loss | IC 95 % | Écart à la vraie probabilité | IC 95 % |
|---|---|---|---|---|---|---|
| Elo − GRU | 0,0015 | [-0,0021 ; 0,0047] | 0,0064 | [-0,0021 ; 0,0148] | 0,0017 | [-0,0028 ; 0,0053] |
| Elo − naïf | -0,0051 | [-0,0071 ; -0,0032] | -0,0152 | [-0,0203 ; -0,0100] | -0,0050 | [-0,0073 ; -0,0028] |
| GRU − naïf | -0,0066 | [-0,0099 ; -0,0033] | -0,0216 | [-0,0302 ; -0,0129] | -0,0068 | [-0,0110 ; -0,0024] |

| Mesure commune (probabilité de réussir la question) | Elo (declic-elo-v1) | GRU DÉCLIC | Naïf |
|---|---|---|---|
| Erreur quadratique à la vraie probabilité | 0,0580 | 0,0563 | 0,0631 |
| Corrélation avec la vraie probabilité | 0,567 | 0,577 | 0,550 |
| Tendance : même sens que la vraie évolution (143 trajectoires élève × compétence) | 64 % | 69 % | 66 % |
| Tendance : corrélation avec la vraie évolution | 0,518 | 0,530 | 0,303 |

Brier de la vraie probabilité cachée (le minimum atteignable en moyenne) : **0,1338**.

### 3.2 Les 200 élèves de A1 en validation croisée (5 plis, 41732 questions communes)

| Modèle | Brier | IC 95 % (élèves) | Log-loss | IC 95 % (élèves) | AUC | ECE | Élèves évalués | Couverture des prévisions |
|---|---|---|---|---|---|---|---|---|
| Elo (declic-elo-v1) | 0,1858 | [0,1785 ; 0,1937] | 0,5454 | [0,5277 ; 0,5644] | 0,720 | 0,021 | 197 | 86 % |
| GRU DÉCLIC | 0,1841 | [0,1767 ; 0,1919] | 0,5388 | [0,5199 ; 0,5581] | 0,724 | 0,007 | 197 | 100 % |
| Naïf | 0,1913 | [0,1845 ; 0,1986] | 0,5614 | [0,5455 ; 0,5786] | 0,708 | 0,048 | 197 | 100 % |

| Différence (négatif = le premier modèle a moins d’erreur) | Brier | IC 95 % | Log-loss | IC 95 % | Écart à la vraie probabilité | IC 95 % |
|---|---|---|---|---|---|---|
| Elo − GRU | 0,0017 | [0,0007 ; 0,0029] | 0,0066 | [0,0033 ; 0,0099] | 0,0021 | [0,0011 ; 0,0032] |
| Elo − naïf | -0,0054 | [-0,0064 ; -0,0045] | -0,0159 | [-0,0185 ; -0,0134] | -0,0054 | [-0,0064 ; -0,0045] |
| GRU − naïf | -0,0072 | [-0,0085 ; -0,0059] | -0,0226 | [-0,0265 ; -0,0185] | -0,0075 | [-0,0088 ; -0,0062] |

| Mesure commune (probabilité de réussir la question) | Elo (declic-elo-v1) | GRU DÉCLIC | Naïf |
|---|---|---|---|
| Erreur quadratique à la vraie probabilité | 0,0643 | 0,0621 | 0,0697 |
| Corrélation avec la vraie probabilité | 0,545 | 0,559 | 0,520 |
| Tendance : même sens que la vraie évolution (951 trajectoires élève × compétence) | 63 % | 69 % | 64 % |
| Tendance : corrélation avec la vraie évolution | 0,489 | 0,557 | 0,286 |

Brier de la vraie probabilité cachée (le minimum atteignable en moyenne) : **0,1225**.

### 3.3 Graines du GRU (même partition)

| Graine | Brier Elo | Brier GRU | Brier naïf | Elo − GRU | IC 95 % |
|---|---|---|---|---|---|
| 42 | 0,1879 | 0,1864 | 0,1931 | 0,0015 | [-0,0021 ; 0,0047] |
| 17 | 0,1879 | 0,1864 | 0,1931 | 0,0015 | [-0,0012 ; 0,0039] |
| 83 | 0,1879 | 0,1879 | 0,1931 | 0,0000 | [-0,0036 ; 0,0033] |

### 3.4 Autres populations du même simulateur

| Campagne | Élèves test | Questions | Brier Elo | Brier GRU | Brier naïf | Elo − GRU | IC 95 % |
|---|---|---|---|---|---|---|---|
| A2 | 30 | 5547 | 0,1941 | 0,1894 | 0,1982 | 0,0047 | [0,0027 ; 0,0068] |
| A3 | 30 | 7213 | 0,1836 | 0,1810 | 0,1879 | 0,0026 | [0,0002 ; 0,0047] |

### 3.5 Sensibilité : entraînement plus long (A1, même partition, même test)

Le réglage O08 (12 époques) s’arrêtait parfois alors que la validation progressait encore. Même chose avec au plus 40 époques et une patience de 6 :

| Graine | Meilleure époque (12 max) | Brier GRU (12 max) | Meilleure époque (40 max) | Brier GRU (40 max) | Brier Elo |
|---|---|---|---|---|---|
| 42 | 12 | 0,1864 | 16 | 0,1855 | 0,1879 |
| 17 | 10 | 0,1864 | 15 | 0,1865 | 0,1879 |
| 83 | 9 | 0,1879 | 13 | 0,1880 | 0,1879 |

### 3.6 Les questions où Elo s’abstient (moins de 5 réponses dans la compétence)

| Modèle | Questions | Élèves | Brier | Log-loss | ECE |
|---|---|---|---|---|---|
| GRU DÉCLIC | 6334 | 197 | 0,1789 | 0,5328 | 0,015 |
| Naïf | 6334 | 197 | 0,1960 | 0,5802 | 0,055 |

GRU − naïf : -0,0170 [-0,0198 ; -0,0142]. Elo ne prévoit pas ces questions : c’est sa règle d’abstention, pas une erreur.

### 3.7 Où Elo fait mieux que le GRU (intervalle entièrement sous zéro)

| Découpage | Tranche | Questions | Élèves | Brier Elo | Brier GRU | Brier naïf | Elo − GRU | IC 95 % |
|---|---|---|---|---|---|---|---|---|
| compétence | reproduction | 2558 | 100 | 0,2122 | 0,2198 | 0,2191 | -0,0076 | [-0,0141 ; -0,0018] |
| exercice | echo | 2558 | 100 | 0,2122 | 0,2198 | 0,2191 | -0,0076 | [-0,0141 ; -0,0018] |
| pause avant la question | 7 jours et plus | 125 | 89 | 0,2146 | 0,2411 | 0,2108 | -0,0265 | [-0,0471 ; -0,0057] |

## 4. Par tranche (A1, validation croisée ; Brier, le plus bas en gras ; IC par tirage d’élèves)

### Historique (réponses déjà données)

| historique (réponses déjà données) | Questions | Élèves | Réussite | Elo (declic-elo-v1) | GRU DÉCLIC | Naïf | Elo − GRU | IC 95 % | Lecture |
|---|---|---|---|---|---|---|---|---|---|
| 5–19 | 1379 | 197 | 70 % | 0,2074 | **0,2022** | 0,2372 | 0,0052 | [0,0009 ; 0,0096] | GRU meilleur |
| 20–49 | 3048 | 194 | 67 % | 0,1868 | **0,1816** | 0,1905 | 0,0051 | [0,0019 ; 0,0085] | GRU meilleur |
| 50–99 | 8239 | 187 | 66 % | 0,1948 | **0,1941** | 0,2008 | 0,0007 | [-0,0012 ; 0,0028] | pas de différence nette |
| 100–199 | 14008 | 166 | 68 % | 0,1887 | **0,1881** | 0,1941 | 0,0005 | [-0,0012 ; 0,0020] | pas de différence nette |
| 200+ | 15058 | 117 | 73 % | 0,1762 | **0,1738** | 0,1794 | 0,0024 | [0,0002 ; 0,0046] | GRU meilleur |

### Pause avant la question

| pause avant la question | Questions | Élèves | Réussite | Elo (declic-elo-v1) | GRU DÉCLIC | Naïf | Elo − GRU | IC 95 % | Lecture |
|---|---|---|---|---|---|---|---|---|---|
| même séance (< 1 h) | 38076 | 197 | 70 % | 0,1832 | **0,1813** | 0,1883 | 0,0019 | [0,0008 ; 0,0031] | GRU meilleur |
| moins de 2 jours | 2500 | 186 | 61 % | 0,2122 | **0,2122** | 0,2222 | 0,0000 | [-0,0054 ; 0,0057] | pas de différence nette |
| 2 à 6 jours | 1031 | 182 | 60 % | 0,2149 | **0,2123** | 0,2253 | 0,0026 | [-0,0054 ; 0,0103] | pas de différence nette |
| 7 jours et plus | 125 | 89 | 45 % | 0,2146 | 0,2411 | **0,2108** | -0,0265 | [-0,0471 ; -0,0057] | Elo meilleur |

### Compétence

| compétence | Questions | Élèves | Réussite | Elo (declic-elo-v1) | GRU DÉCLIC | Naïf | Elo − GRU | IC 95 % | Lecture |
|---|---|---|---|---|---|---|---|---|---|
| accords | 851 | 35 | 60 % | 0,2395 | **0,2288** | 0,2417 | 0,0107 | [0,0049 ; 0,0160] | GRU meilleur |
| hauteur | 5611 | 197 | 90 % | 0,0791 | **0,0766** | 0,0924 | 0,0026 | [0,0012 ; 0,0039] | GRU meilleur |
| intervalles | 1273 | 66 | 85 % | 0,1234 | **0,1198** | 0,1342 | 0,0036 | [0,0000 ; 0,0072] | GRU meilleur |
| lecture | 9960 | 186 | 63 % | 0,2082 | **0,2071** | 0,2124 | 0,0011 | [-0,0012 ; 0,0032] | pas de différence nette |
| memoire | 8463 | 188 | 68 % | **0,2079** | 0,2081 | 0,2107 | -0,0002 | [-0,0021 ; 0,0016] | pas de différence nette |
| pulsation | 4000 | 167 | 73 % | 0,1570 | **0,1557** | 0,1703 | 0,0013 | [-0,0034 ; 0,0056] | pas de différence nette |
| reproduction | 2558 | 100 | 60 % | **0,2122** | 0,2198 | 0,2191 | -0,0076 | [-0,0141 ; -0,0018] | Elo meilleur |
| rythme | 8929 | 192 | 64 % | 0,2164 | **0,2107** | 0,2164 | 0,0057 | [0,0028 ; 0,0085] | GRU meilleur |
| tonalite | 87 | 6 | 77 % | **0,1691** | 0,1815 | 0,1740 | -0,0125 | [-0,0227 ; 0,0155] | pas de différence nette |

### Famille

| famille | Questions | Élèves | Réussite | Elo (declic-elo-v1) | GRU DÉCLIC | Naïf | Elo − GRU | IC 95 % | Lecture |
|---|---|---|---|---|---|---|---|---|---|
| Débutant motivé | 14076 | 44 | 65 % | 0,2166 | **0,2124** | 0,2192 | 0,0042 | [0,0025 ; 0,0059] | GRU meilleur |
| En difficulté, progresse lentement | 3212 | 32 | 46 % | **0,2243** | 0,2247 | 0,2275 | -0,0003 | [-0,0037 ; 0,0027] | pas de différence nette |
| Irrégulier, longues pauses | 2439 | 31 | 66 % | 0,2076 | **0,2065** | 0,2118 | 0,0011 | [-0,0023 ; 0,0045] | pas de différence nette |
| Musicien expérimenté | 7419 | 28 | 88 % | 0,0989 | **0,0959** | 0,1122 | 0,0030 | [0,0014 ; 0,0046] | GRU meilleur |
| Bonne oreille, rythme faible | 6843 | 31 | 69 % | **0,1936** | 0,1939 | 0,1973 | -0,0003 | [-0,0039 ; 0,0029] | pas de différence nette |
| Bon rythme, difficultés mélodiques | 7743 | 31 | 71 % | **0,1836** | 0,1846 | 0,1895 | -0,0011 | [-0,0037 ; 0,0017] | pas de différence nette |

### Exercice

| exercice | Questions | Élèves | Réussite | Elo (declic-elo-v1) | GRU DÉCLIC | Naïf | Elo − GRU | IC 95 % | Lecture |
|---|---|---|---|---|---|---|---|---|---|
| accords | 851 | 35 | 60 % | 0,2395 | **0,2288** | 0,2417 | 0,0107 | [0,0049 ; 0,0160] | GRU meilleur |
| cadences | 4 | 1 | 100 % | **0,0149** | 0,0223 | 0,0290 | — | — | trop peu d’élèves |
| degres | 83 | 6 | 76 % | **0,1765** | 0,1892 | 0,1810 | -0,0127 | [-0,0240 ; 0,0155] | pas de différence nette |
| echo | 2558 | 100 | 60 % | **0,2122** | 0,2198 | 0,2191 | -0,0076 | [-0,0141 ; -0,0018] | Elo meilleur |
| hauteur-comparaison | 4232 | 190 | 96 % | 0,0374 | **0,0356** | 0,0452 | 0,0017 | [0,0005 ; 0,0029] | GRU meilleur |
| hauteur-seuil | 1379 | 197 | 70 % | 0,2074 | **0,2022** | 0,2372 | 0,0052 | [0,0009 ; 0,0096] | GRU meilleur |
| intervalles | 1273 | 66 | 85 % | 0,1234 | **0,1198** | 0,1342 | 0,0036 | [0,0000 ; 0,0072] | GRU meilleur |
| lecture | 9960 | 186 | 63 % | 0,2082 | **0,2071** | 0,2124 | 0,0011 | [-0,0012 ; 0,0032] | pas de différence nette |
| melodies | 8463 | 188 | 68 % | **0,2079** | 0,2081 | 0,2107 | -0,0002 | [-0,0021 ; 0,0016] | pas de différence nette |
| pulsation | 4000 | 167 | 73 % | 0,1570 | **0,1557** | 0,1703 | 0,0013 | [-0,0034 ; 0,0056] | pas de différence nette |
| rythme-echo | 751 | 83 | 84 % | 0,1789 | **0,1237** | 0,1736 | 0,0552 | [0,0312 ; 0,0841] | GRU meilleur |
| rythmes | 8178 | 192 | 63 % | 0,2198 | **0,2187** | 0,2203 | 0,0011 | [-0,0010 ; 0,0031] | pas de différence nette |

## 5. Expériences de robustesse

### 5.1 Taille de la cohorte (L1 : test fixe de 150 élèves)

| Cohorte | Élèves d’entraînement | Graine | Brier GRU | Brier Elo | Brier naïf | Elo − GRU | IC 95 % | Époques |
|---|---|---|---|---|---|---|---|---|
| 50 | 35 | 42 | 0,1890 | 0,1858 | 0,1905 | -0,0032 | [-0,0053 ; -0,0013] | 12 |
| 50 | 35 | 17 | 0,1890 | 0,1858 | 0,1905 | -0,0032 | [-0,0056 ; -0,0011] | 12 |
| 50 | 35 | 83 | 0,1887 | 0,1858 | 0,1905 | -0,0029 | [-0,0049 ; -0,0012] | 12 |
| 200 | 140 | 42 | 0,1838 | 0,1858 | 0,1905 | 0,0020 | [0,0003 ; 0,0034] | 12 |
| 200 | 140 | 17 | 0,1842 | 0,1858 | 0,1905 | 0,0016 | [0,0001 ; 0,0029] | 12 |
| 200 | 140 | 83 | 0,1836 | 0,1858 | 0,1905 | 0,0022 | [0,0008 ; 0,0034] | 12 |
| 1000 | 700 | 42 | 0,1816 | 0,1858 | 0,1905 | 0,0042 | [0,0031 ; 0,0053] | 12 |
| 1000 | 700 | 17 | 0,1814 | 0,1858 | 0,1905 | 0,0044 | [0,0033 ; 0,0054] | 12 |
| 1000 | 700 | 83 | 0,1814 | 0,1858 | 0,1905 | 0,0044 | [0,0033 ; 0,0054] | 12 |

### 5.2 Autre simulateur (B1) et réponses plus bruyantes (N1)

| Population | GRU | Questions | Brier Elo | Brier GRU | Brier naïf | Elo − GRU | IC 95 % | GRU → vérité | Elo → vérité |
|---|---|---|---|---|---|---|---|---|---|
| B1 | GRU entraîné sur A1 (transfert), 30 élèves test | 6290 | 0,1876 | 0,1854 | 0,1933 | 0,0022 | [-0,0003 ; 0,0048] | 0,0671 | 0,0703 |
| B1 | GRU entraîné sur B1, 30 élèves test | 6290 | 0,1876 | 0,1864 | 0,1933 | 0,0013 | [-0,0021 ; 0,0044] | 0,0678 | 0,0703 |
| B1 | GRU entraîné sur A1 (transfert), tous les élèves | 40123 | 0,1899 | 0,1875 | 0,1938 | 0,0024 | [0,0014 ; 0,0034] | 0,0714 | 0,0739 |
| N1 | GRU entraîné sur A1 (transfert), 30 élèves test | 5497 | 0,2108 | 0,2115 | 0,2137 | -0,0007 | [-0,0050 ; 0,0030] | 0,0768 | 0,0769 |
| N1 | GRU entraîné sur N1, 30 élèves test | 5497 | 0,2108 | 0,2084 | 0,2137 | 0,0024 | [-0,0007 ; 0,0055] | 0,0754 | 0,0769 |
| N1 | GRU entraîné sur A1 (transfert), tous les élèves | 37274 | 0,2105 | 0,2092 | 0,2122 | 0,0013 | [-0,0001 ; 0,0026] | 0,0817 | 0,0825 |

Où Elo fait mieux que le GRU transféré, N1 (tous les élèves, intervalle entièrement sous zéro) :

| Découpage | Tranche | Questions | Élèves | Brier Elo | Brier GRU | Brier naïf | Elo − GRU | IC 95 % |
|---|---|---|---|---|---|---|---|---|
| compétence | pulsation | 4644 | 177 | 0,1729 | 0,1899 | 0,1747 | -0,0170 | [-0,0237 ; -0,0109] |
| exercice | pulsation | 4644 | 177 | 0,1729 | 0,1899 | 0,1747 | -0,0170 | [-0,0237 ; -0,0109] |
| pause avant la question | moins de 2 jours | 2250 | 187 | 0,2052 | 0,2170 | 0,2064 | -0,0119 | [-0,0188 ; -0,0047] |
| pause avant la question | 2 à 6 jours | 1025 | 182 | 0,1936 | 0,2081 | 0,1968 | -0,0145 | [-0,0248 ; -0,0048] |

### 5.3 Progression atypique (famille de B1, jamais vue par le GRU entraîné sur A1)

| Élèves | Questions | Brier Elo | Brier GRU | Brier naïf | Elo − GRU | IC 95 % |
|---|---|---|---|---|---|---|
| 28 | 6203 | 0,2266 | 0,2248 | 0,2265 | 0,0017 | [-0,0006 ; 0,0039] |

| Tendance (152 trajectoires élève × compétence) | Elo (declic-elo-v1) | GRU DÉCLIC | Naïf |
|---|---|---|---|
| Même sens que la vraie évolution | 61 % | 57 % | 66 % |
| Corrélation avec la vraie évolution | 0,562 | 0,472 | 0,272 |

### 5.4 Une famille absente de l’entraînement (L1)

| Famille testée | Élèves testés | Brier GRU sans la famille | Brier GRU avec (même taille) | Brier Elo | Brier naïf |
|---|---|---|---|---|---|
| Débutant motivé | 30 | 0,2079 | 0,2065 | 0,2116 | 0,2131 |
| Musicien expérimenté | 19 | 0,0913 | 0,0838 | 0,0899 | 0,1036 |
| Bonne oreille, rythme faible | 31 | 0,2006 | 0,1951 | 0,1982 | 0,2015 |
| Bon rythme, difficultés mélodiques | 24 | 0,1838 | 0,1821 | 0,1847 | 0,1889 |
| Irrégulier, longues pauses | 27 | 0,1954 | 0,1952 | 0,1996 | 0,2077 |
| En difficulté, progresse lentement | 19 | 0,2291 | 0,2251 | 0,2329 | 0,2346 |

