# contracts/

Les **contrats de données** entre domaines. Un contrat décrit ce que le consommateur (la Finance) **attend** d'un producteur. Il n'affirme pas que les données sont parfaites : ce sont les mécanismes du projet qui vérifient qu'il est respecté. En cas de violation, ils mettent les lignes suspectes en quarantaine et alertent le propriétaire.

| Fichier | Producteur | Consommateur | Contenu |
|---|---|---|---|
| `ventes_vers_finance.yaml` | Ventes | Finance | Transactions (ventes et remboursements) |
| `service_client_vers_finance.yaml` | Service client | Finance | Référentiel clients et tickets |

## Le format : ODCS v3.1.0

Les contrats suivent l'**Open Data Contract Standard (ODCS)**, en version 3.1.0. Ce standard ouvert est publié par le projet Bitol, hébergé par la Linux Foundation. Deux raisons à ce choix :

- **Ne pas inventer un format maison.** Un standard reconnu se lit, se vérifie et se réutilise par d'autres outils.
- **La compatibilité avec le catalogue du projet.** OpenMetadata importe nativement l'ODCS v3.1.0, et transforme les règles de qualité en tests.

Le schéma officiel du standard est copié dans `schema/odcs-json-schema-v3.1.0.json` (licence Apache 2.0, projet Bitol). Les tests (`tests/test_contracts.py`) vérifient à chaque modification que les deux contrats le respectent.

## Comment lire un contrat

Un contrat est organisé en sept blocs :

| Bloc | Question à laquelle il répond | Exemple |
|---|---|---|
| En-tête (`apiVersion`, `id`, `version`, `status`, `domain`) | De quel contrat parle-t-on, et dans quelle version ? | `c1-ventes-transactions`, version 1.0.0 |
| `description` | À quoi servent ces données, et quelles sont leurs limites ? | Calcul du chiffre d'affaires net |
| `team` | Qui en est responsable ? | Le Data Product Owner Ventes (`owner`), alerté en cas de violation |
| `roles` | Qui peut y accéder, et qui l'autorise ? | `finance_analyste`, en lecture |
| `slaProperties` | Quels engagements de service ? | Livraison quotidienne, disponible avant 8 h |
| `schema` → `properties` | Quelles colonnes, de quel type, avec quelles contraintes ? | `montant` : nombre, obligatoire |
| `quality` | Quelles règles de qualité ? | Une vente a un montant strictement positif |

## Les quatre sortes de règles de qualité

| Sorte | Principe | Exemple dans nos contrats | Qui l'exécute |
|---|---|---|---|
| `metric` (bibliothèque ODCS) | Une mesure standard : valeurs nulles, valeurs invalides, doublons, nombre de lignes | `devise` doit valoir EUR ou CHF | Une règle simple (dossier `baselines/`) |
| `type: sql` | Une requête qui compte les lignes fautives ; le résultat doit valoir 0 | Aucun remboursement avec un montant positif | Une règle simple, ou PostgreSQL |
| `type: custom` | Un contrôle trop subtil pour une règle fixe, confié à un mécanisme d'IA du projet | Montant anormal pour ce client → mécanisme 1 | Les mécanismes (dossier `mechanisms/`) |
| `type: text` | Une règle écrite pour les humains, non exécutée | (pas utilisée pour l'instant) | Personne |

Cette répartition est au cœur de la thèse : **les règles simples traitent ce qui est prévisible, l'IA traite ce qui ne l'est pas**, et les deux se complètent.

## Trois choix à savoir défendre

1. **Un montant négatif n'est pas toujours une erreur.** C'est normal pour un remboursement. Le contrat ne dit donc pas « montant > 0 », mais « une vente est positive, un remboursement est négatif ». Une règle trop stricte produirait de fausses alertes sur des données correctes.
2. **La minimisation des données personnelles (RGPD, article 5.1.c).** La Finance n'a pas besoin du nom, de l'e-mail ni du téléphone des clients pour son reporting. Ces données restent dans le domaine Service client ; le référentiel publié ne contient qu'un identifiant pseudonymisé, le segment, la ville et la date de création. La résolution des doublons (mécanisme 9) se fait donc dans le domaine Service client, avant publication.
3. **La cohérence entre domaines.** Des règles vérifient que les domaines « se parlent » correctement : chaque client d'une transaction existe au Service client, et chaque transaction citée dans un ticket existe aux Ventes. C'est précisément la « cohérence inter-domaines » de la problématique.

## Sources

- Bitol (Linux Foundation), *Open Data Contract Standard*, version 3.1.0 : [standard et documentation](https://bitol-io.github.io/open-data-contract-standard/latest/home), [règles de qualité](https://bitol-io.github.io/open-data-contract-standard/latest/data-quality), [dépôt GitHub et schéma JSON](https://github.com/bitol-io/open-data-contract-standard).
- OpenMetadata, *ODCS import and export* : [documentation de l'import ODCS](https://docs.open-metadata.org/v2.0.x/how-to-guides/data-contracts/odcs.md), qui précise les versions et les champs pris en charge.
- Règlement (UE) 2016/679 (RGPD), article 5.1.c, sur la minimisation des données.
- Code de commerce, article L123-22, sur la conservation des documents comptables pendant dix ans.
