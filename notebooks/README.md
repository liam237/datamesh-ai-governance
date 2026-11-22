# notebooks/

Les **notebooks Jupyter numérotés**, qui rendent la démarche d'analyse visible. Chaque analyse suit le même schéma :

> **On regarde** (un graphique ou un tableau) → **on conclut** (une phrase écrite) → **on décide** (un traitement ou un réglage).

| Notebook | Contenu | Statut |
|---|---|---|
| `01_exploration.ipynb` | Exploration des données publiées : qualité, saisonnalité, montants, remboursements, quantités, heures, habitudes des clients, doublons, prix dans le temps, Service client. Se termine par le tableau des décisions. | Fait |
| `02_variables.ipynb` | Les huit variables relatives (écart à la catégorie, prix unitaire, quantité au segment, habitude du client, rareté de l'heure, délai et écart avec l'achat précédent), chacune justifiée par l'exploration ; corrélations ; sept variables retenues ; point de vigilance sur la circularité | Fait |
| `03_resultats.ipynb` | Matrices de confusion, courbes ROC et précision-rappel, comparaison règles / IA / combinaison | À venir |

## Règles

- **Une figure = une image**, enregistrée en grand dans `results/figures/<notebook>/`, pour être reprise seule dans le mémoire ou les slides.
- **Les notebooks de conception (01 et 02) ne lisent jamais la vérité terrain** (`data/ground_truth/`) : on se met dans la peau d'un analyste réel. Un test le vérifie. Seul le notebook des résultats (03) la lira.
- **Le calcul des variables est écrit une seule fois**, dans `mechanisms/arrival/features.py` : le notebook 02 l'explique, le mécanisme 1 l'utilise.
- **Les couleurs** viennent de `viz.py` : une palette fixe, validée pour le daltonisme. Chaque courbe est aussi nommée, par une légende ou une étiquette, pour ne jamais reposer sur la couleur seule.

## Les relancer

```bash
make notebooks          # ou : python -m pipeline.run_notebooks
```

Les notebooks sont réexécutés de haut en bas dans un noyau neuf. Comme les données sont générées avec une graine fixe, on retrouve exactement les mêmes chiffres et les mêmes figures. Les tests (`tests/test_notebooks.py`) vérifient qu'ils s'exécutent sans erreur.

Pour les ouvrir dans VS Code : installer l'extension Jupyter, ouvrir le fichier `.ipynb`, puis choisir l'environnement Python du projet comme noyau.
