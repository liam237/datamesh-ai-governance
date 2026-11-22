# Références simples : résultats

Généré par `python -m evaluation.evaluate_baselines`. Ne pas modifier à la main.

## Scores globaux

| Jeu | Référence | Alertes | Vraies anomalies trouvées | Fausses alertes | Anomalies manquées | Précision | Rappel | F1 |
|---|---|---|---|---|---|---|---|---|
| conception | contrat | 515 | 515 | 0 | 344 | 1.000 | 0.600 | 0.750 |
| conception | expert | 687 | 687 | 0 | 172 | 1.000 | 0.800 | 0.889 |
| test | contrat | 504 | 504 | 0 | 404 | 1.000 | 0.555 | 0.714 |
| test | expert | 675 | 672 | 3 | 236 | 0.996 | 0.740 | 0.849 |

## Rappel par famille d'anomalies

| Famille | conception · contrat | conception · expert | test · contrat | test · expert |
|---|---|---|---|---|
| devise_incoherente | 1.00 | 1.00 | 1.00 | 1.00 |
| doublon_approche | 0.00 | 0.00 | 0.00 | 0.00 |
| doublon_exact | 1.00 | 1.00 | 1.00 | 1.00 |
| magasin_hors_horaires | 0.00 | 1.00 | 0.00 | 1.00 |
| montant_nul_ou_negatif | 1.00 | 1.00 | 1.00 | 1.00 |
| pic_client | 0.00 | 0.00 | 0.00 | 0.00 |
| prix_unitaire_aberrant | 0.00 | 1.00 | 0.00 | 1.00 |
| rafale_achats | — | — | 0.00 | 0.00 |
| valeur_hors_referentiel | 1.00 | 1.00 | 1.00 | 1.00 |
| valeur_manquante | 1.00 | 1.00 | 1.00 | 1.00 |
