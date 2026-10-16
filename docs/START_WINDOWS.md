# Lancer la Phase 8 sur Windows

Dans le dossier du dépôt (ou depuis ailleurs avec le chemin absolu du script) :

```powershell
.\Launch.ps1
```

Le script cherche `.venv`, puis l’environnement du checkout principal retrouvé par Git, puis Python du PATH. Il vérifie Python 3.12+ et les dépendances, sans installation silencieuse. Dans ce projet préparé, il retrouve aussi le dossier `work/.venv` et les données privées du checkout principal, même depuis un worktree. Le terminal indique l’interpréteur réellement utilisé.

Configuration explicite, conservée pour les prochains lancements dans votre terminal si nécessaire :

```powershell
$env:DECLIC_PYTHON = 'CHEMIN\VERS\ENVIRONNEMENT\Scripts\python.exe'
.\Launch.ps1 -PreparedData 'CHEMIN\VERS\DONNEES_PREPAREES' -Port 8781
```

Le dossier de données contient `singpad-prepared.json.gz` et `yousician-prepared.json.gz`, reconstruits avec les scripts et archives décrits dans PHASE7_REPRODUCTION.md. Un port occupé produit un refus explicite ; le lanceur ne ferme aucun autre processus. Choisir un autre port avec `-Port 8782` puis utiliser l’URL affichée.

Sur un nouveau checkout, préparer l’environnement une fois :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[test]' --extra-index-url https://download.pytorch.org/whl/cpu
```

Aucune dépendance n’est installée dans un autre environnement par le lanceur. Les données privées ne sont pas livrées par Git. Sans elles, le démarrage normal refuse de dire « prêt ». `-AllowPartial` permet de consulter les diagnostics sans déclarer la démonstration disponible.

## Vérifier avant une soutenance

Le terminal donne dépôt, commit, branche, Python, version, hôte et port. `/api/health` signifie seulement « processus vivant ». `/api/readiness` doit retourner HTTP 200, `application=declic-phase8`, `identity_contract=living-generation-v1`, les deux sources prêtes et une inférence réussie. Une réponse 503 détaille modèles, données ou inférence manquants sans exposer de chemins personnels. Un vieux serveur ne passe pas ce contrat.

Ouvrir **l’URL `/web/living.html` affichée par le lanceur**. Garder le terminal ouvert ; Ctrl+C arrête uniquement son backend enfant. En cas d’erreur réseau, lire le diagnostic repliable et utiliser « Réessayer le chargement » après restauration du service. Pas de reconnexion automatique infinie.

Une session conserve des snapshots identifiés ; un changement de génération exige le rechargement explicite du parcours. Les révélations et inspections incompatibles sont refusées. Les parcours de plus de 500 pas sont exclus explicitement de cette interface, sans tronquer silencieusement l’historique scientifique.
