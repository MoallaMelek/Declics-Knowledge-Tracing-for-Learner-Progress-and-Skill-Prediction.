# DÉCLIC - Stabilisation Phase 8

La [PR #4](https://github.com/MoallaMelek/Declics-Knowledge-Tracing-for-Learner-Progress-and-Skill-Prediction./pull/4) livre une version locale stabilisée des quatre expériences Phase 8. Les caches, snapshots, inspections et reçus sont liés au contenu effectif et au modèle validé ; les retours asynchrones obsolètes sont écartés ; la frise, les formulations et les liens sont cohérents.

## Clôture

**14 constats techniques corrigés et vérifiés. F09 documenté ; confirmations de droits externes encore nécessaires.** Le [registre détaillé](STABILIZATION_LEDGER.md) et son [JSON](phase8-stabilization-ledger.json) conservent cause, fichiers, réalisation, tests, commits et statut par constat. Les limites scientifiques ne sont pas effacées.

## Validation reproductible

- Suite locale : **350 réussis, 1 avertissement** (155.60 s), données privées présentes.
- Ciblage des régressions : **35 réussis**, dont deux démarrages PowerShell depuis des contextes distincts et contrôle de l’interpréteur.
- [CI du code](https://github.com/MoallaMelek/Declics-Knowledge-Tracing-for-Learner-Progress-and-Skill-Prediction./actions/runs/38884678771) : **349 réussis, 1 ignoré** (données privées absentes) et **13 scénarios Chromium** utilisant de vrais tenseurs entraînés et des historiques synthétiques déclarés.
- Même harnais navigateur : **13 scénarios réussis sur parcours réels privés** en local. Les captures de ces parcours restent locales.
- Recalcul des modèles actifs sans fit : **écart mesuré nul** avec l’audit sur log-loss/AUC SingPAD et MAE Yousician, tolérance 10⁻⁷.
- Les **36 SHA de poids Phase 7** correspondent au manifeste ; aucun artefact scientifique, notebook, donnée source, feuille CSS Phase 8 ou moteur de constellation n’est modifié.

Les résultats agrégés sont dans [la synthèse machine](validation/phase8-stabilization.json). Les journaux complets, revue et captures accompagnent le PDF livré au propriétaire. Les fichiers privés ne sont pas publiés pour rendre la CI verte.

## Révisions de réalisation

| Commit | Réalisation |
|---|---|
| 2a2ed69 | Identité canonique, validation sur octets cohérents, inférence épinglée, reçus, disponibilité, lanceur et régressions Python |
| c10419f | Epochs, identité client, agrégations compatibles, copie factuelle, liens et récupération des quatre vues |
| 64c78ae | CI HTTP/Chromium réelle, fixtures étiquetées, dépendance navigateur verrouillée et nettoyage |
| bac46e7 | Ancien état de récupération effacé après succès ; régression issue de la première CI |

La première CI navigateur (38884283670) a échoué sur un vrai défaut de récupération ; le défaut a été corrigé puis le pipeline réussi. La revue indépendante source-only a trouvé deux P2, corrigés avec régressions ; la clôture statique n’a trouvé aucune autre anomalie actionnable dans son périmètre. Codex desktop a écrit et testé ; les sessions Codex CLI étaient fraîches, en lecture seule, sans accès aux données privées.

## Lancement et limites

Suivre [START_WINDOWS.md](START_WINDOWS.md). Le lanceur refuse un port occupé sans arrêter un autre processus, affiche son identité et attend une readiness de sa propre instance. Liveness n’est pas readiness. Les modèles et parcours des deux sources doivent être prêts. Aucun compte Colab permanent n’est nécessaire pour l’inférence locale.

Les scores et cibles restent source-spécifiques. La [politique DL expérimentale](MODEL_ELIGIBILITY_POLICY.md) expose que Yousician ne bat pas le meilleur contrôle appris publié sur validation ; aucun modèle classique ne remplace le réseau. Les [droits et provenance](DATA_PROVENANCE_AND_RIGHTS.md) encore non confirmés restent externes. Pas de validation de maîtrise cognitive, de transfert piano, d’incertitude individuelle ou de bénéfice pédagogique. Production publique et nouveaux élèves demandent une validation et des protections supplémentaires.

Le rapport PDF final en français ajoute les preuves de fusion et la CI du commit main effectivement consultées après intégration. Aucune branche historique ni PR antérieure n’est supprimée.
