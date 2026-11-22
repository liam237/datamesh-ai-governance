# datamesh-ai-governance

**Gouvernance fédérée computationnelle par l'intelligence artificielle pour un Data Mesh** — version novembre 2026.

Projet de William Vanel Fonkui Kamgang. Il reprend de fond en comble la version 2 du prototype de mémoire, avec la même idée de départ et une démonstration plus rigoureuse.

---

## La question de départ

Les grandes organisations ont centralisé leurs données pendant trente ans, d'abord dans des Data Warehouses puis dans des Data Lakes. Résultat : des équipes data centrales débordées et des données mal documentées.

Le **Data Mesh** propose de décentraliser. Chaque domaine métier devient propriétaire de ses données et les publie comme des produits. Mais une question se pose alors :

> Une fois les données décentralisées, comment garantir la qualité, la sécurité et la cohérence entre domaines, sans recréer une bureaucratie centrale ?

**Thèse défendue :** l'IA rend ce contrôle praticable à grande échelle, et les humains gardent la décision finale (*human-in-the-loop*).

## Le scénario

Il s'agit d'une entreprise de e-commerce fictive, organisée en trois domaines :

| Domaine | Rôle | Données |
|---|---|---|
| Ventes | Producteur | Transactions (ventes et remboursements) |
| Service client | Producteur | Fiches clients et tickets en texte libre |
| Finance | Consommateur | Reporting construit à partir des deux |

Deux **contrats de données** (dossier `contracts/`) fixent ce que la Finance attend de chaque producteur. Dix mécanismes vérifient automatiquement ces contrats, en suivant le parcours d'une donnée :

| Étape du parcours | Mécanismes | Niveau de validation visé |
|---|---|---|
| 1. À l'arrivée | 1. Détection d'anomalies · 4. Données personnelles | Prouvé |
| 2. Au nettoyage | 3. Auto-correction · 9. Résolution d'entités | Mesuré / Prouvé |
| 3. À la publication | 7. Documentation générée · 8. Lignage | Démontré |
| 4. À la consommation | 5. Contrôle d'accès · 6. Analyse comportementale | Mesuré |
| 5. Dans la durée | 2. Dérives · 10. FinOps | Mesuré / Démontré |

Chaque mécanisme est toujours comparé à une **référence simple** (des règles écrites à la main) et à la **combinaison** des règles et de l'IA.

## Principes de méthode

- **Vérité terrain séparée.** Les étiquettes des anomalies injectées sont rangées à part. Seul le dossier `evaluation/` les lit, jamais les mécanismes.
- **Reproductibilité.** Une graine aléatoire fixe, et une seule commande qui régénère tous les résultats.
- **Démarche visible.** Dans les notebooks, chaque analyse suit le même schéma : on regarde, on conclut, on décide.
- **Souveraineté numérique.** Les outils sont open source, gratuits et auto-hébergeables, européens de préférence (scikit-learn, spaCy, PostgreSQL, un modèle Mistral exécuté en local…).

## Organisation du dépôt

```
contracts/          Contrats de données (YAML)
data_generation/    Générateur du monde simulé et de la vérité terrain
notebooks/          Exploration, décisions de traitement, analyse des résultats
mechanisms/         Les dix mécanismes, rangés par étape du parcours
  arrival/          1. À l'arrivée
  cleaning/         2. Au nettoyage
  publication/      3. À la publication
  consumption/      4. À la consommation
  monitoring/       5. Dans la durée
baselines/          Règles simples de référence
evaluation/         Notation des mécanismes (seul dossier qui lit la vérité terrain)
pipeline/           Enchaînement de bout en bout, DAG Airflow, scripts SQL
results/metrics/    Métriques produites (une source unique pour le mémoire)
results/figures/    Graphiques produits
models/             Modèles entraînés
tests/              Tests automatiques
docs/               Documentation complémentaire (dont sources.md)
```

Chaque dossier contient un petit `README.md` qui explique son rôle.

## Démarrage

Il faut Python 3.11 ou 3.12.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # puis adapter si besoin

make test                        # lance les tests
make all                         # régénère tous les résultats
make notebooks                   # réexécute les notebooks et leurs figures
```

Sans `make` (par exemple sous Windows) : `python -m pytest` et `python -m pipeline.run_all`.

## Avancement

| Étape | Statut |
|---|---|
| 0. Cadrage | Terminé |
| 1. Initialisation du dépôt | Terminé |
| 2. Générateur de données | Terminé |
| 3. Exploration des données et variables | Terminé |
| 4. Références simples | Terminé |
| 5. Mécanismes niveau 1 | À faire |
| 6. Mécanismes niveau 2 | À faire |
| 7. Mécanismes niveau 3 | À faire |
| 8. Pipeline et déploiement | À faire |
| 9. Évaluation et résultats | À faire |
| 10 à 12. Mémoire, slides, soutenance | À faire |

## Licence

MIT, voir [LICENSE](LICENSE).
