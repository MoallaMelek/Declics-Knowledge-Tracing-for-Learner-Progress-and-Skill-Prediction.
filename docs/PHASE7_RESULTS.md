# Phase 7 — résultats réellement exécutés

Expériences CPU exploratoires sur les partitions par apprenant de Phase 6 ; aucune nouvelle cohorte confirmatoire indépendante.

| Base | Graine | Réseau choisi sur validation | Test réseau | Contrôle choisi sur validation | Test contrôle |
|---|---:|---|---:|---|---:|
| amme | 42 | gru | 0.188550 | historical_frequency | 0.169944 |
| amme | 17 | gru | 0.171750 | ridge | 0.176187 |
| amme | 83 | gru | 0.198541 | ridge | 0.171233 |
| yousician | 42 | past_gaps | 0.090643 | boosted_trees | 0.090578 |
| yousician | 17 | past_gaps | 0.087304 | historical_frequency | 0.085350 |
| yousician | 83 | gru | 0.094723 | boosted_trees | 0.094960 |
| singpad | 42 | gru | 0.517922 | boosted_trees | 0.524048 |
| singpad | 17 | gru | 0.523285 | boosted_trees | 0.528969 |
| singpad | 83 | attention | 0.512568 | boosted_trees | 0.519547 |

## Toutes les variantes

| Base | Graine | Condition | Validation | Test | Paramètres | Époques |
|---|---:|---|---:|---:|---:|---:|
| amme | 42 | gru | 0.171927 | 0.188550 | 12781 | 8 |
| amme | 42 | unordered | 0.174352 | 0.192143 | 781 | 8 |
| amme | 17 | gru | 0.196978 | 0.171750 | 12781 | 8 |
| amme | 17 | unordered | 0.198541 | 0.174609 | 781 | 8 |
| amme | 83 | gru | 0.184331 | 0.198541 | 12781 | 8 |
| amme | 83 | unordered | 0.184528 | 0.195065 | 781 | 4 |
| yousician | 42 | gru | 0.096128 | 0.090861 | 12781 | 8 |
| yousician | 42 | past_gaps | 0.096102 | 0.090643 | 12781 | 8 |
| yousician | 42 | unordered | 0.104940 | 0.101143 | 781 | 8 |
| yousician | 17 | gru | 0.097692 | 0.087449 | 12781 | 8 |
| yousician | 17 | past_gaps | 0.097654 | 0.087304 | 12781 | 8 |
| yousician | 17 | unordered | 0.114317 | 0.106227 | 781 | 8 |
| yousician | 83 | gru | 0.094294 | 0.094723 | 12781 | 8 |
| yousician | 83 | past_gaps | 0.094390 | 0.094972 | 12781 | 8 |
| yousician | 83 | unordered | 0.108322 | 0.106856 | 781 | 8 |
| singpad | 42 | attention | 0.509969 | 0.519155 | 86545 | 8 |
| singpad | 42 | gru | 0.509501 | 0.517922 | 207786 | 8 |
| singpad | 42 | no_concept_embedding | 0.512332 | 0.521778 | 73585 | 8 |
| singpad | 42 | past_gaps | 0.509699 | 0.518996 | 207786 | 8 |
| singpad | 42 | recent3 | 0.512561 | 0.521840 | 207786 | 8 |
| singpad | 42 | unordered | 0.510973 | 0.520559 | 40842 | 8 |
| singpad | 17 | attention | 0.549420 | 0.522908 | 86641 | 8 |
| singpad | 17 | gru | 0.547352 | 0.523285 | 207810 | 8 |
| singpad | 17 | no_concept_embedding | 0.552111 | 0.524262 | 73681 | 8 |
| singpad | 17 | past_gaps | 0.547544 | 0.523259 | 207810 | 8 |
| singpad | 17 | recent3 | 0.551548 | 0.525996 | 207810 | 8 |
| singpad | 17 | unordered | 0.549243 | 0.525581 | 40866 | 8 |
| singpad | 83 | attention | 0.500602 | 0.512568 | 86593 | 8 |
| singpad | 83 | gru | 0.501295 | 0.512251 | 207798 | 8 |
| singpad | 83 | no_concept_embedding | 0.502785 | 0.517677 | 73633 | 8 |
| singpad | 83 | past_gaps | 0.501368 | 0.512292 | 207798 | 8 |
| singpad | 83 | recent3 | 0.503606 | 0.517018 | 207798 | 8 |
| singpad | 83 | unordered | 0.503438 | 0.514963 | 40854 | 8 |

## Calibration SingPAD

| Graine | Condition | T validation | Log-loss brute | Log-loss recalibrée | ECE brute | ECE recalibrée |
|---:|---|---:|---:|---:|---:|---:|
| 42 | attention | 1.0217 | 0.519155 | 0.519206 | 0.005685 | 0.006210 |
| 42 | gru | 1.0518 | 0.517922 | 0.517804 | 0.009300 | 0.006700 |
| 42 | no_concept_embedding | 1.0506 | 0.521778 | 0.521568 | 0.009484 | 0.005101 |
| 42 | past_gaps | 1.0069 | 0.518996 | 0.519014 | 0.007974 | 0.008341 |
| 42 | recent3 | 0.9980 | 0.521840 | 0.521847 | 0.014698 | 0.014772 |
| 42 | unordered | 1.0307 | 0.520559 | 0.520509 | 0.008475 | 0.011311 |
| 17 | attention | 1.0651 | 0.522908 | 0.522868 | 0.010969 | 0.011836 |
| 17 | gru | 1.0587 | 0.523285 | 0.522985 | 0.010386 | 0.008675 |
| 17 | no_concept_embedding | 1.0660 | 0.524262 | 0.524256 | 0.013274 | 0.013266 |
| 17 | past_gaps | 1.0491 | 0.523259 | 0.523051 | 0.009999 | 0.008585 |
| 17 | recent3 | 1.0554 | 0.525996 | 0.526327 | 0.007566 | 0.013262 |
| 17 | unordered | 1.0512 | 0.525581 | 0.525226 | 0.013181 | 0.012737 |
| 83 | attention | 0.9805 | 0.512568 | 0.512703 | 0.005650 | 0.008914 |
| 83 | gru | 0.9872 | 0.512251 | 0.512307 | 0.005979 | 0.006645 |
| 83 | no_concept_embedding | 1.0605 | 0.517677 | 0.516443 | 0.025512 | 0.014840 |
| 83 | past_gaps | 0.9898 | 0.512292 | 0.512342 | 0.005600 | 0.006437 |
| 83 | recent3 | 1.0249 | 0.517018 | 0.516803 | 0.012642 | 0.008252 |
| 83 | unordered | 1.0582 | 0.514963 | 0.513993 | 0.016133 | 0.008376 |

## Extension Yousician : métadonnées passées

| Graine | Validation GRU enrichi | Test GRU enrichi | Validation arbres mêmes variables | Test arbres mêmes variables |
|---:|---:|---:|---:|---:|
| 42 | 0.096096 | 0.091899 | 0.095058 | 0.090833 |
| 17 | 0.096318 | 0.086158 | 0.097049 | 0.087327 |
| 83 | 0.094577 | 0.095121 | 0.092902 | 0.094304 |

Trois réseaux supplémentaires : 36 entraînements terminés au total. Cette extension est exploratoire et séparée du programme initial.
Moyenne MAE enrichie 0,091059 ; arbres avec les mêmes variables 0,090822. Pas de gain moyen convaincant ni de promotion.

## Limites

Les trois découpages ne sont pas trois populations indépendantes.
Huit époques et un protocole CPU exploratoire : ne pas substituer ces scores au benchmark GPU Phase 6.
Aucune supériorité pédagogique, maîtrise cognitive ou généralisation au piano démontrée.
Calibration ajustée sur validation ; aucune garantie de gain sur le test.
Prévisions terrain suspendues à la validation du contrat de mesure ; aucun résultat prospectif inventé.
AMME : petit échantillon et score mélodique continu ; recherche seulement.
