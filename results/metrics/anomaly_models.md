# Mécanisme 1 : comparaison des méthodes de détection

Généré par `python -m evaluation.compare_anomaly_models`. Ne pas modifier à la main.

## Jeu de conception : 10 découpages 70 / 30 (médianes)

Hasard : AUC-PR = 0.020, AUC-ROC = 0,5. Budget : 1% des ventes examinées en plus de la quarantaine de l'expert.

| Méthode | Type | AUC-PR (min – max) | AUC-ROC | Rappel au budget | Rappel sur ce que l'expert rate | Précision de ces alertes |
|---|---|---|---|---|---|---|
| Score z robuste | non supervisé | 0.378 (0.326 – 0.404) | 0.809 | 0.300 | 0.445 | 0.228 |
| Mahalanobis robuste | non supervisé | 0.032 (0.030 – 0.035) | 0.663 | 0.005 | 0.009 | 0.005 |
| Isolation Forest | non supervisé | 0.418 (0.361 – 0.436) | 0.804 | 0.317 | 0.538 | 0.277 |
| LOF | non supervisé | 0.060 (0.048 – 0.102) | 0.589 | 0.079 | 0.109 | 0.058 |
| One-Class SVM | non supervisé | 0.248 (0.184 – 0.292) | 0.787 | 0.207 | 0.085 | 0.044 |
| HistGradientBoosting | supervisé (repère) | 0.654 (0.624 – 0.693) | 0.870 | 0.469 | 0.879 | 0.447 |
| XGBoost | supervisé (repère) | 0.671 (0.646 – 0.711) | 0.877 | 0.490 | 0.881 | 0.437 |

## Choix (règle fixée à l'avance)

- Premier : Isolation Forest ; deuxième : Score z robuste.
- Wilcoxon apparié : p = 0.0137 (écart significatif).
- **Gagnant : Isolation Forest.**

## Examen unique sur le jeu de test

Hasard : AUC-PR = 0.022.

| Système | AUC-PR | AUC-ROC | Alertes IA en plus | Précision | Rappel | F1 |
|---|---|---|---|---|---|---|
| Expert seul | — | — | 0 | 0.996 | 0.740 | 0.849 |
| Expert + Score z robuste | 0.431 | 0.832 | 318 | 0.797 | 0.871 | 0.832 |
| Expert + Mahalanobis robuste | 0.031 | 0.636 | 365 | 0.647 | 0.741 | 0.691 |
| Expert + Isolation Forest **(gagnant)** | 0.374 | 0.825 | 362 | 0.729 | 0.833 | 0.777 |
| Expert + LOF | 0.112 | 0.600 | 385 | 0.689 | 0.804 | 0.742 |
| Expert + One-Class SVM | 0.210 | 0.771 | 328 | 0.708 | 0.782 | 0.743 |
| Expert + HistGradientBoosting | 0.653 | 0.862 | 405 | 0.806 | 0.959 | 0.876 |
| Expert + XGBoost | 0.574 | 0.826 | 775 | 0.579 | 0.924 | 0.712 |

## Rappel par famille sur le jeu de test

| Famille | Expert seul | Expert + Isolation Forest | Expert + HistGradientBoosting | Expert + XGBoost |
|---|---|---|---|---|
| devise_incoherente | 1.00 | 1.00 | 1.00 | 1.00 |
| doublon_approche | 0.00 | 1.00 | 1.00 | 1.00 |
| doublon_exact | 1.00 | 1.00 | 1.00 | 1.00 |
| magasin_hors_horaires | 1.00 | 1.00 | 1.00 | 1.00 |
| montant_nul_ou_negatif | 1.00 | 1.00 | 1.00 | 1.00 |
| pic_client | 0.00 | 0.17 | 0.82 | 0.75 |
| prix_unitaire_aberrant | 1.00 | 1.00 | 1.00 | 1.00 |
| rafale_achats | 0.00 | 0.00 | 0.72 | 0.35 |
| valeur_hors_referentiel | 1.00 | 1.00 | 1.00 | 1.00 |
| valeur_manquante | 1.00 | 1.00 | 1.00 | 1.00 |
