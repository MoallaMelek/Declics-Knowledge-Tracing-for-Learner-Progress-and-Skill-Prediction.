# Politique experimental-dl-v1

Les prédictions musicales de l’application utilisent exclusivement les réseaux enregistrés. Les contrôles appris demeurent des comparaisons de recherche ; ils ne remplacent jamais silencieusement le réseau.

Trois décisions distinctes :

1. **Intégrité et éligibilité expérimentale** : conserver les gates existants (poids/configuration, chronologie, partitions, validation meilleure que moyenne d’entraînement et effectifs suffisants). SingPAD corrigé garde sa condition supplémentaire de contrôle historique. Aucun gate existant n’est abaissé.
2. **Compétitivité sur validation** : confronter le réseau actif aux contrôles appris publiés sur la même source et partition, en choisissant leurs paramètres sur validation. Si les informations manquent, dire « non établi ». Ne lire aucun score de test pour cette décision.
3. **Validation d’un produit terrain** : ni l’éligibilité expérimentale ni une meilleure perte de validation ne prouvent une maîtrise cognitive, un transfert au piano ou un bénéfice causal.

Le réseau Yousician actif reste un **prédicteur DL expérimental de benchmark de source**. Sa MAE de validation 0,0955381028794489 est moins bonne que celle du contrôle boosted_trees publié (0,0947175630636283, partition seed 42). Son maintien satisfait le choix produit DL et le gate expérimental d’origine ; il ne signifie pas une supériorité. La légère différence favorable sur le test ne sert pas à le sélectionner. Aucun entraînement ni poids n’est changé pour « gagner » cette comparaison.

`axis7/model_eligibility.py` expose cette qualification et les valeurs de validation à la provenance de la page. Les métriques originales, y compris défavorables, sont conservées. Pour une future promotion confirmatoire, préenregistrer la règle, figer le budget et utiliser une nouvelle cohorte indépendante ; ne pas réutiliser le test exploré pour choisir le vainqueur.
