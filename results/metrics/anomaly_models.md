# Mécanisme 1 : comparaison des méthodes de détection

Généré par `python -m evaluation.compare_anomaly_models`. Ne pas modifier à la main.

## Jeu de conception : 10 découpages 70 / 30 (médianes)

Hasard : AUC-PR = 0.020, AUC-ROC = 0,5. Budget : 1% des ventes examinées en plus de la quarantaine de l'expert.

| Méthode | Type | AUC-PR (min – max) | AUC-ROC | Rappel au budget | Rappel sur ce que l'expert rate | Précision de ces alertes |
|---|---|---|---|---|---|---|
| Score z robuste | non supervisé | 0.318 (0.283 – 0.357) | 0.790 | 0.243 | 0.009 | 0.005 |
| Mahalanobis robuste | non supervisé | 0.031 (0.030 – 0.035) | 0.661 | 0.005 | 0.009 | 0.005 |
| Isolation Forest | non supervisé | 0.217 (0.177 – 0.250) | 0.789 | 0.180 | 0.271 | 0.150 |
| LOF | non supervisé | 0.056 (0.044 – 0.105) | 0.585 | 0.082 | 0.110 | 0.058 |
| One-Class SVM | non supervisé | 0.248 (0.183 – 0.291) | 0.787 | 0.207 | 0.085 | 0.044 |
| HistGradientBoosting | supervisé (repère) | 0.613 (0.591 – 0.661) | 0.855 | 0.452 | 0.878 | 0.442 |
| XGBoost | supervisé (repère) | 0.641 (0.589 – 0.676) | 0.867 | 0.469 | 0.876 | 0.437 |

## Choix (règle fixée à l'avance)

- Premier : Score z robuste ; deuxième : One-Class SVM.
- Wilcoxon apparié : p = 0.0020 (écart significatif).
- **Gagnant : Score z robuste.**

## Examen unique sur le jeu de test

Hasard : AUC-PR = 0.022.

| Système | AUC-PR | AUC-ROC | Alertes IA en plus | Précision | Rappel | F1 |
|---|---|---|---|---|---|---|
| Expert seul | — | — | 0 | 0.996 | 0.740 | 0.849 |
| Expert + Score z robuste **(gagnant)** | 0.305 | 0.768 | 369 | 0.646 | 0.742 | 0.691 |
| Expert + Mahalanobis robuste | 0.031 | 0.636 | 365 | 0.647 | 0.741 | 0.691 |
| Expert + Isolation Forest | 0.164 | 0.763 | 377 | 0.679 | 0.786 | 0.729 |
| Expert + LOF | 0.055 | 0.561 | 355 | 0.674 | 0.764 | 0.716 |
| Expert + One-Class SVM | 0.206 | 0.759 | 333 | 0.704 | 0.782 | 0.741 |
| Expert + HistGradientBoosting | 0.567 | 0.829 | 332 | 0.817 | 0.906 | 0.860 |
| Expert + XGBoost | 0.529 | 0.805 | 928 | 0.511 | 0.902 | 0.652 |

## Rappel par famille sur le jeu de test

| Famille | Expert seul | Expert + Score z robuste | Expert + HistGradientBoosting | Expert + XGBoost |
|---|---|---|---|---|
| devise_incoherente | 1.00 | 1.00 | 1.00 | 1.00 |
| doublon_approche | 0.00 | 0.00 | 1.00 | 1.00 |
| doublon_exact | 1.00 | 1.00 | 1.00 | 1.00 |
| magasin_hors_horaires | 1.00 | 1.00 | 1.00 | 1.00 |
| montant_nul_ou_negatif | 1.00 | 1.00 | 1.00 | 1.00 |
| pic_client | 0.00 | 0.02 | 0.83 | 0.76 |
| prix_unitaire_aberrant | 1.00 | 1.00 | 1.00 | 1.00 |
| rafale_achats | 0.00 | 0.00 | 0.00 | 0.04 |
| valeur_hors_referentiel | 1.00 | 1.00 | 1.00 | 1.00 |
| valeur_manquante | 1.00 | 1.00 | 1.00 | 1.00 |
