# Mécanisme 1 : réglage et vérification de la boucle avec le Data Steward

Généré par `python -m evaluation.simulate_steward`. Ne pas modifier à la main.

## Réglages figés pour l'examen

- Filet : **Isolation Forest** (rappel sur ce que l'expert rate, médianes : Isolation Forest 0.538, Score z robuste 0.445, LOF 0.109, One-Class SVM 0.086, Mahalanobis robuste 0.009 ; Wilcoxon premier contre deuxième : p = 0.0020).
- Supervisé : **HistGradientBoosting** (F1 du dernier trimestre, conception : HistGradientBoosting 0.809, XGBoost 0.811).
- Budget : 1% des ventes de la semaine, dont 25% pour le filet ; réentraînement toutes les 4 semaines ; supervisé actif dès 20 anomalies confirmées.

## Jeu de conception (réglage)

| Période | Système | Précision | Rappel | F1 | Lignes examinées |
|---|---|---|---|---|---|
| Année | Expert seul | 1.000 | 0.800 | 0.889 | 687 |
| Année | Expert + boucle | 0.737 | 0.885 | 0.804 | 1031 |
| Dernier trimestre | Expert seul | 1.000 | 0.785 | 0.879 | 186 |
| Dernier trimestre | Expert + boucle | 0.745 | 0.886 | 0.809 | 282 |

Premier mois où le système dépasse l'expert : None.
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

## Jeu de développement (vérification)

| Période | Système | Précision | Rappel | F1 | Lignes examinées |
|---|---|---|---|---|---|
| Année | Expert seul | 0.996 | 0.740 | 0.849 | 675 |
| Année | Expert + boucle | 0.751 | 0.838 | 0.792 | 1013 |
| Dernier trimestre | Expert seul | 0.988 | 0.743 | 0.848 | 164 |
| Dernier trimestre | Expert + boucle | 0.723 | 0.862 | 0.787 | 260 |

Premier mois où le système dépasse l'expert : None.
Alertes par couche : {'quarantaine': 675, 'supervise': 225, 'filet': 113} ; vraies anomalies par couche : {'quarantaine': 672, 'supervise': 79, 'filet': 10}.

| Famille (dernier trimestre) | Expert seul | Expert + boucle |
|---|---|---|
| devise_incoherente | 1.00 | 1.00 |
| doublon_approche | 0.00 | 1.00 |
| doublon_exact | 1.00 | 1.00 |
| magasin_hors_horaires | 1.00 | 1.00 |
| montant_nul_ou_negatif | 1.00 | 1.00 |
| pic_client | 0.00 | 0.04 |
| prix_unitaire_aberrant | 1.00 | 1.00 |
| rafale_achats | 0.00 | 0.50 |
| valeur_hors_referentiel | 1.00 | 1.00 |
| valeur_manquante | 1.00 | 1.00 |
