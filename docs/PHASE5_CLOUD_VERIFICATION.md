# Vérification cloud — 15 octobre 2026

Les trois bases ont été entraînées et évaluées dans Google Colab sur un **Tesla T4**,
avec **PyTorch 2.11.0+cu130**, à partir du code `63085813d84ae30c393f7d5a61be06cc49e30c21`.
SingPAD a comparé DKT GRU, EnhancedGRU et l'attention causale existante. AMME et
Yousician ont utilisé EnhancedGRU avec une sortie continue. Aucun nouveau modèle
classique n'a été entraîné.

Les entraînements ont réutilisé le même GPU pour respecter la limite gratuite de
sessions. Les trois archives sont dans `Mon Drive/DECLIC/datasets/`. Leurs tailles
sur Drive correspondent aux fichiers locaux. Les checksums des archives contenus
dans les rapports cloud ont également été comparés aux rapports locaux.

Les checkpoints ont été sauvegardés pendant l'apprentissage. Après les exports,
`drive.flush_and_unmount` a confirmé le transfert des écritures Drive. Les paquets
ont ensuite été téléchargés et vérifiés localement : checksum des poids, configuration,
tenseurs finis, provenance du découpage et seuil de validation.

| Base | Modèle retenu sur validation | Résultat test réel | Utilisation |
|---|---|---|---|
| AMME | EnhancedGRU | MAE 0,1857 ; 23 cibles test | Recherche seulement : effectif sous le seuil de 30 |
| SingPAD | Attention causale | ROC-AUC 0,6996 ; PR-AUC 0,8599 ; log-loss 0,5198 ; Brier 0,1717 | Modèle actif du benchmark de chant |
| Yousician | EnhancedGRU | MAE 0,0905 ; RMSE 0,1341 ; 1 740 jours test | Modèle actif du benchmark d'ukulélé |

Pour Yousician, une MAE de 0,0905 représente un écart moyen de **9,1 points sur 100**
entre le score prévu et observé. La ROC-AUC SingPAD n'est pas un pourcentage de notes
réussies. Ces résultats ne démontrent ni maîtrise générale, ni bénéfice pédagogique,
ni transfert au piano personnel. Un seul découpage et une seule graine ont été utilisés.

Les rapports complets sont dans `artifacts/phase5/cloud-report.json`. Les poids et
métriques sont archivés dans `artifacts/models/phase5-cloud/`. Les expériences CPU
restent conservées. `artifacts/models/musical-cloud/active.json` désigne les deux modèles
GPU activés. L'interface affiche une version active par base et conserve l'abstention
du carnet piano.

Le [notebook commun](https://colab.research.google.com/github/MoallaMelek/Declics-Knowledge-Tracing-for-Learner-Progress-and-Skill-Prediction./blob/phase5/colab-musical-training/notebooks/DECLIC_all.ipynb)
enchaîne les trois bases dans une session. Les notebooks individuels restent disponibles.
Un montage Drive déjà valide est conservé ; sinon un délai de dix minutes et une reprise
après `mount failed` sont prévus. Les ressources et l'autorisation Google restent externes.

La reprise au milieu d'une époque est testée sur CPU et reproduit exactement les poids
et métriques d'une exécution continue. Les checkpoints GPU ont été sauvegardés sur Drive ;
une interruption volontaire du GPU en cours d'apprentissage n'est pas revendiquée comme
test. Des différences numériques entre CPU et GPU sont attendues.
