# Provenance et droits des trois sources musicales

État vérifié le 16 octobre 2026, à partir des archives locales fournies par le propriétaire et des preuves de l’audit E09. La disponibilité publique n’établit pas, seule, une autorisation de réutilisation ou de redistribution. Aucun statut « illégal » n’est déduit des lacunes documentaires. Aucun jeu ni modèle n’est retiré pour cette seule raison.

| Source | Version effectivement identifiée | Acquisition et provenance | Conditions établies / limites |
|---|---|---|---|
| AMME | `2gvty-osfstorage-archive.zip`, SHA-256 `2a8fb3f213f6472f0020383aa68e12a23001547715bb071903b0616ad7db2e18` | Archive locale fournie par l’utilisateur ; date et méthode de téléchargement initiales non certifiées. [Dépôt OSF](https://osf.io/2gvty/), référencé par [Chmiel et al., PLOS One, DOI 10.1371/journal.pone.0320055](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0320055). | README RTF explique variables/alias ; article sous CC BY, mais ce grant ne remplace pas celui des données. Accès OSF refusé 403 lors de l’audit ; autorisation propre à l’archive non confirmée. |
| SingPAD / SingKT | `singKT-dataset-main.zip`, SHA-256 `9e87e3ccb4bbc6e90a571a28a989168f0c7e49a332c633de328e5c5660773b64` | Archive locale utilisateur du [dépôt officiel itec-hust/singKT-dataset](https://github.com/itec-hust/singKT-dataset) ; branche main, commit d’acquisition non conservé dans le ZIP. | Aucune licence explicite trouvée dans l’inventaire ; champ GitHub license null à l’audit. [Zenodo 12729828](https://zenodo.org/records/12729828) contient l’article, sans établir un grant de toutes les données brutes. |
| Yousician ukulélé | `yousician_ukulele.json.zip`, SHA-256 `9e4b6fe3d11381de02d197fe6dbd84676d6e48e25d9d0d364bb43d0a400dc52e` | JSON utilisateur, 584 790 578 octets décompressés ; [source Open Data annoncée](https://yousician.com/open-data). Date/acquisition initiales non certifiées. | Aucun fichier de licence dans l’archive ; page Open Data 403 dans l’outil d’audit. Conditions actuelles, périmètre académique et redistribution non certifiés. |

## Transformations et publication

Préparations inchangées : AMME blocs scoretype 7 ; SingPAD dates locales parsées v2 et regroupement des instants égaux ; Yousician groupes de compteurs cohérents puis jours actifs. Les exclusions, effectifs et partitions restent dans les rapports scientifiques existants. Le hash d’archive décrit l’entrée historique déclarée. La stabilisation ajoute une identité séparée du contenu effectivement préparé ; cette identité ne prouve pas à elle seule les droits ou l’authenticité de la source.

Les données et caches préparés restent privés/ignorés par Git. Les checkpoints déjà publiés restent préservés ; leur présence publique n’établit pas un droit universel de réutilisation. Les nouvelles fixtures de CI sont générées, identifiées comme synthétiques, sans identifiants source ; elles ne servent pas de validation scientifique.

## Décision externe restant nécessaire (F09)

Le dossier de provenance technique est documenté. Les droits non établis restent **Requires external decision** : obtenir les conditions officielles applicables à chaque version, ou une autorisation écrite du détenteur, précisant recherche, dérivés et redistribution ; conserver date, URL/texte et périmètre de l’accord. Aucun contact avec les auteurs n’a été envoyé. Ne pas annoncer de redistribution générale autorisée tant que ces éléments manquent. Ne pas confondre cette réserve avec un défaut du moteur d’inférence.
