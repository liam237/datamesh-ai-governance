# pipeline/

L'**enchaînement de bout en bout** : génération, contrôles à l'arrivée, nettoyage, publication, consommation, surveillance, puis évaluation.

- `run_all.py` : la commande unique (`make all`, ou `python -m pipeline.run_all`).
- Prévu à l'étape 8 : le DAG Airflow, les scripts SQL pour PostgreSQL et l'export vers le stockage objet et OpenMetadata.
