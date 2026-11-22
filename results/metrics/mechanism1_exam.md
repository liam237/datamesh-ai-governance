# Mécanisme 1 : réglage et vérification de la boucle avec le Data Steward

Généré par `python -m evaluation.simulate_steward`. Ne pas modifier à la main.

## Réglages figés pour l'examen

- Filet : **Isolation Forest** (rappel sur ce que l'expert rate, médianes : Isolation Forest 0.538, Score z robuste 0.445, LOF 0.109, One-Class SVM 0.086, Mahalanobis robuste 0.009 ; Wilcoxon premier contre deuxième : p = 0.0020).
- Supervisé : **HistGradientBoosting** (F1 du dernier trimestre, conception : HistGradientBoosting 0.809, XGBoost 0.811).
- Budget : 1% des ventes de la semaine, dont 25% pour le filet ; réentraînement toutes les 4 semaines ; supervisé actif dès 20 anomalies confirmées.

## Jeu de conception (réglage)

| Période | Système | Précision | Rappel | F1 | F2 | Lignes examinées | Anomalies manquées | Coût (manquée = 10) | Coût (manquée = 100) |
|---|---|---|---|---|---|---|---|---|---|
| Année | Expert seul | 1.000 | 0.800 | 0.889 | 0.833 | 687 | 172 | 2407 | 17887 |
| Année | Expert + boucle | 0.737 | 0.885 | 0.804 | 0.851 | 1031 | 99 | 2021 | 10931 |
| Dernier trimestre | Expert seul | 1.000 | 0.785 | 0.879 | 0.820 | 186 | 51 | 696 | 5286 |
| Dernier trimestre | Expert + boucle | 0.745 | 0.886 | 0.809 | 0.854 | 282 | 27 | 552 | 2982 |

Seuil de rentabilité (une anomalie manquée doit coûter plus que ce nombre de lignes examinées pour que la boucle vaille le coup) : année 4.71, dernier trimestre 4.0.

Premier mois où la boucle coûte moins que l'expert seul : 2025-01.
Alertes par couche : {'quarantaine': 687, 'supervise': 228, 'filet': 116} ; vraies anomalies par couche : {'quarantaine': 687, 'supervise': 60, 'filet': 13}.

| Famille (dernier trimestre) | Expert seul | Expert + boucle |
|---|---|---|
| devise_incoherente | 1.00 | 1.00 |
| doublon_approche | 0.00 | 1.00 |
| doublon_exact | 1.00 | 1.00 |
| magasin_hors_horaires | 1.00 | 1.00 |
| montant_nul_ou_negatif | 1.00 | 1.00 |
| pic_client | 0.00 | 0.04 |
| prix_unitaire_aberrant | 1.00 | 1.00 |
| valeur_hors_referentiel | 1.00 | 1.00 |
| valeur_manquante | 1.00 | 1.00 |

## Jeu d'EXAMEN 2027

| Période | Système | Précision | Rappel | F1 | F2 | Lignes examinées | Anomalies manquées | Coût (manquée = 10) | Coût (manquée = 100) |
|---|---|---|---|---|---|---|---|---|---|
| Année | Expert seul | 0.999 | 0.706 | 0.827 | 0.750 | 696 | 290 | 3596 | 29696 |
| Année | Expert + boucle | 0.746 | 0.794 | 0.769 | 0.784 | 1048 | 203 | 3078 | 21348 |
| Dernier trimestre | Expert seul | 0.995 | 0.628 | 0.770 | 0.678 | 195 | 115 | 1345 | 11695 |
| Dernier trimestre | Expert + boucle | 0.775 | 0.735 | 0.754 | 0.742 | 293 | 82 | 1113 | 8493 |

Seuil de rentabilité (une anomalie manquée doit coûter plus que ce nombre de lignes examinées pour que la boucle vaille le coup) : année 4.05, dernier trimestre 2.97.

Premier mois où la boucle coûte moins que l'expert seul : 2025-01.
Alertes par couche : {'quarantaine': 696, 'supervise': 230, 'filet': 122} ; vraies anomalies par couche : {'quarantaine': 695, 'supervise': 76, 'filet': 11}.

| Famille (dernier trimestre) | Expert seul | Expert + boucle |
|---|---|---|
| devise_incoherente | 1.00 | 1.00 |
| doublon_approche | 0.00 | 0.95 |
| doublon_exact | 1.00 | 1.00 |
| magasin_hors_horaires | 1.00 | 1.00 |
| montant_nul_ou_negatif | 1.00 | 1.00 |
| pic_client | 0.00 | 0.05 |
| prix_unitaire_aberrant | 1.00 | 1.00 |
| rafale_achats | 0.00 | 0.36 |
| rejeu_lot | 0.00 | 0.00 |
| valeur_hors_referentiel | 1.00 | 1.00 |
| valeur_manquante | 1.00 | 1.00 |
