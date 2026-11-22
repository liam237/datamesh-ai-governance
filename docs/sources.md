# Sources

Bibliographie tenue au fil du projet. Chaque source est rattachée à l'étape où elle a servi ; elle sera reprise dans la bibliographie du mémoire.

## Étape 2 : contrats de données

- Bitol (Linux Foundation). *Open Data Contract Standard (ODCS)*, version 3.1.0. Documentation : https://bitol-io.github.io/open-data-contract-standard/latest/home ; règles de qualité : https://bitol-io.github.io/open-data-contract-standard/latest/data-quality ; dépôt et schéma JSON : https://github.com/bitol-io/open-data-contract-standard
- OpenMetadata. *ODCS import and export* (versions et champs pris en charge par le catalogue) : https://docs.open-metadata.org/v2.0.x/how-to-guides/data-contracts/odcs.md
- Règlement (UE) 2016/679 du 27 avril 2016 (RGPD), article 5.1.c : principe de minimisation des données.
- Code de commerce, article L123-22 : conservation des documents comptables et pièces justificatives pendant dix ans.

## Étape 5 : mécanisme 1, détection d'anomalies

- Han, S., Hu, X., Huang, H., Jiang, M., Zhao, Y. *ADBench: Anomaly Detection Benchmark*. NeurIPS 2022, Datasets and Benchmarks. https://arxiv.org/abs/2206.09426 (aucune méthode non supervisée n'est meilleure en général ; 1 % d'étiquettes suffit aux méthodes semi-supervisées pour dépasser la meilleure non supervisée).
- Grinsztajn, L., Oyallon, E., Varoquaux, G. *Why do tree-based models still outperform deep learning on typical tabular data?* NeurIPS 2022. https://arxiv.org/abs/2207.08815
- Iglewicz, B., Hoaglin, D. *How to Detect and Handle Outliers*. ASQC Quality Press, 1993 (score z modifié, médiane et MAD).
- Rousseeuw, P. J., Van Driessen, K. *A fast algorithm for the minimum covariance determinant estimator*. Technometrics, 41(3), 1999.
- Liu, F. T., Ting, K. M., Zhou, Z.-H. *Isolation Forest*. IEEE ICDM 2008.
- Breunig, M. M., Kriegel, H.-P., Ng, R. T., Sander, J. *LOF: Identifying Density-Based Local Outliers*. ACM SIGMOD 2000.
- Schölkopf, B., Platt, J. C., Shawe-Taylor, J., Smola, A. J., Williamson, R. C. *Estimating the Support of a High-Dimensional Distribution*. Neural Computation, 13(7), 2001.
- Friedman, J. H. *Greedy Function Approximation: A Gradient Boosting Machine*. Annals of Statistics, 29(5), 2001.
- Chen, T., Guestrin, C. *XGBoost: A Scalable Tree Boosting System*. KDD 2016. https://arxiv.org/abs/1603.02754
- Saito, T., Rehmsmeier, M. *The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets*. PLOS ONE, 10(3), 2015.
- Wilcoxon, F. *Individual Comparisons by Ranking Methods*. Biometrics Bulletin, 1(6), 1945.
- Labovitz, G., Chang, Y. S., Rosansky, V. *Making Quality Work: A Leadership Guide for the Results-Driven Manager*. HarperBusiness, 1993. Origine couramment citée de la règle « 1-10-100 » (prévention 1, correction 10, défaillance 100), qui fonde le critère de coût du mécanisme 1. Présentation : https://martech.org/assessing-impact-poor-data-1-10-100-rule (référence du livre à vérifier sur un exemplaire avant le mémoire).
