# Vérification cloud — 15 octobre 2026

Le notebook AMME a été importé dans Google Colab depuis le navigateur et son
exécution a été lancée. La première cellule s'est terminée en 24 secondes :

```text
PyTorch 2.11.0+cu130 | GPU: True
Tesla T4
Code revision: 9d970da55dc3f1d1ea696a65e9ad01f9acdc0081
```

Cela confirme le clonage de la branche, l'installation des dépendances et l'accès
à un GPU réel. Ce résultat n'est pas une mesure d'entraînement du modèle.
La cellule suivante attend le montage Google Drive. L'utilisateur a explicitement
autorisé cette permission ; le navigateur a validé le bouton de connexion, mais
aucune confirmation de montage n'a encore été observée.

Les modèles publiés à cette date proviennent des entraînements **locaux CPU**
documentés dans [PHASE5_RESULTS.md](PHASE5_RESULTS.md). Aucun modèle ni score
GPU n'est revendiqué avant la fin effective d'un entraînement et de son évaluation.
Les notebooks SingPAD et Yousician sont préparés et testés ; leur exécution cloud
n'est pas encore confirmée.

Validation locale : **232 tests passent**. La
[validation GitHub Actions](https://github.com/MoallaMelek/Declics-Knowledge-Tracing-for-Learner-Progress-and-Skill-Prediction./actions/runs/38649780082)
du commit ci-dessus est également terminée avec succès.

Si l'autorisation Google ne se termine pas dans le navigateur intégré, ouvrir le
notebook dans son navigateur habituel, interrompre la cellule de montage puis la
relancer et terminer la connexion Google. Fournir l'archive demandée au premier
lancement seulement. Les fichiers de données et de reprise restent dans Drive.
