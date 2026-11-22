# baselines/

Les **références simples** : des règles, sans IA, auxquelles on compare les mécanismes. Un mécanisme d'IA n'est jugé utile que s'il fait mieux qu'elles, seul ou combiné avec elles.

| Référence | Règles | Ce qu'elle représente |
|---|---|---|
| **contrat** | Celles du contrat n° 1 en version **1.0.0** (`contracts/history/`) | Ce qu'on savait **avant** d'explorer les données |
| **expert** | Celles du contrat **actuel** (1.1.0, avec les horaires d'ouverture) **plus** une règle d'analyste : « pas plus de 5 articles pour un particulier ou un client Premium » | Ce qu'un analyste attentif aurait écrit **après** l'exploration |

## Comment ça marche

Les règles ne sont **pas recopiées à la main** : `rules.py` lit le fichier YAML du contrat et applique chaque règle ligne par ligne :
- les colonnes obligatoires, les formats (expressions régulières) et les minimums ;
- les mesures standard du format ODCS : valeurs manquantes, valeurs hors liste, doublons ;
- les requêtes SQL du contrat, exécutées avec DuckDB et transformées pour renvoyer les lignes fautives.

Les règles de type `custom` sont ignorées : elles sont confiées aux mécanismes d'IA. Une ligne part en **quarantaine** dès qu'une règle au moins la signale, et la colonne `motifs` dit lesquelles.

Si le contrat change, la référence change avec lui. Un test le vérifie.

## Résultats

Ils sont calculés par `python -m evaluation.evaluate_baselines` et écrits dans `results/metrics/baselines.md` (et `.json`), sur les deux jeux de données : conception (graine 42) et test (graine 2026).
