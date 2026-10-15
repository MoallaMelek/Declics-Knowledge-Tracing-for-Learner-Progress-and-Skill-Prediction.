> Historique Phase 5 : les résultats SingPAD ci-dessous sont méthodologiquement invalides en raison du tri des dates. Les anciens modèles sont retirés. Voir [la correction et les limites Phase 6](PHASE6_SCIENCE_FR.md).

# Phase 5 — résultats réellement exécutés

Entraînements exécutés localement sur CPU, sur les archives fournies. Aucun résultat GPU/Colab
n'est déduit de ces résultats locaux. Les architectures sont choisies sur la validation uniquement.

| Base | Architecture | Époques | Mesure test | Référence constante test | Contrôle |
|---|---|---:|---:|---:|---|
| amme | enhanced_gru | 12 | mae: 0.1857 | 0.1958 | recherche seulement |
| singpad | dkt | 12 | log_loss: 0.5214 | 0.5685 | accepté pour le benchmark |
| singpad | enhanced_gru | 10 | log_loss: 0.5216 | 0.5685 | accepté pour le benchmark |
| singpad | item_attention | 12 | log_loss: 0.5200 | 0.5685 | accepté pour le benchmark |
| yousician | enhanced_gru | 12 | mae: 0.0905 | 0.1092 | accepté pour le benchmark |

Sélection sur validation : amme: enhanced_gru, singpad: item_attention, yousician: enhanced_gru.

Pour SingPAD, la ROC-AUC, la PR-AUC, le Brier et les classes de calibration sont dans
`artifacts/phase5/report.json`. AMME manque de cibles de validation/test pour le seuil
de 30 et reste en recherche. Les moyennes constantes sont calculées sur l’entraînement.

Un seul découpage nouveaux apprenants et une seule graine : pas d’intervalle de confiance,
pas de preuve de bénéfice pédagogique ni de transfert vers le piano personnel.

Le rapport JSON contient les checksums des archives et les audits de nettoyage.
