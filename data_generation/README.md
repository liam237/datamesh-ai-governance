# data_generation/

Le **générateur du monde simulé**. On le lance avec `python -m data_generation.generate` (ou `make all`). Il faut environ 5 secondes, et une même graine (`SEED = 42` dans `config.py`) produit exactement les mêmes fichiers à chaque lancement.

## Deux jeux de données indépendants

| Jeu | Graine | Commande | Dossier | Usage |
|---|---|---|---|---|
| **Conception** | 42 | `python -m data_generation.generate` | `data/` | Exploration, choix des variables, réglages |
| **Test** | 2026 | `python -m data_generation.generate --test` | `data_test/` | Évaluation finale uniquement |

Le jeu de test est un **autre monde**, généré avec une autre graine : d'autres clients, d'autres achats, d'autres anomalies. Personne ne le regarde pendant la conception. C'est la pratique standard en apprentissage automatique : un résultat mesuré sur les données qui ont servi à concevoir le système est toujours trop optimiste.

Le jeu de test contient en plus une **famille d'anomalies « inconnue »**, la **rafale d'achats** : 4 achats en moins de 30 minutes, dans 4 catégories différentes, à des montants banals (un schéma typique d'une carte volée). Elle a été conçue **après** le choix des variables, et aucune variable n'a été pensée pour elle. Elle sert à vérifier si le système généralise au-delà de ce qu'on lui a appris à chercher : c'est la **parade contre la circularité** (voir le notebook `02_variables.ipynb`, section 10).

## Les modules

| Fichier | Rôle |
|---|---|
| `config.py` | Toutes les hypothèses chiffrées du monde, réunies pour être lues et discutées |
| `world.py` | Les clients et leurs habitudes, le calendrier (soldes, Black Friday, Noël, week-ends) |
| `sales.py` | Le domaine Ventes : les ventes, les remboursements, et un bug de prix (dérive) |
| `anomalies.py` | L'injection des anomalies dans les transactions, avec leur étiquette |
| `customer_service.py` | Le domaine Service client : les fiches en double, les homonymes, les tickets et leurs données personnelles |
| `generate.py` | L'orchestration, l'écriture des fichiers et le résumé chiffré |

## Ce qui est produit

**Ce que les domaines publient**, donc ce que les mécanismes ont le droit de lire :

| Fichier | Contenu |
|---|---|
| `data/ventes/transactions.csv` | Toutes les transactions, au schéma du contrat n° 1 |
| `data/service_client/clients_interne.csv` | Le référentiel interne du Service client, avec les données personnelles. Il ne sort jamais du domaine. |
| `data/service_client/tickets.csv` | Les tickets et leurs commentaires libres |

**La vérité terrain**, rangée à part et lue uniquement par `evaluation/` :

| Fichier | Contenu |
|---|---|
| `data/ground_truth/transactions.csv` | Pour chaque transaction : son statut, sa famille, la période, l'effet de la dérive |
| `data/ground_truth/clients_doublons.csv` | Les 60 fiches en double et leur type de variation |
| `data/ground_truth/clients_homonymes.csv` | Les paires de personnes différentes portant le même nom |
| `data/ground_truth/tickets_pii.csv` | Pour chaque ticket : présence de données personnelles, forme, type, valeur exacte, présence d'un piège |
| `data/ground_truth/clients_habitudes.csv` | Les habitudes cachées des clients, qui ont servi à générer leurs achats |

Le résumé chiffré est écrit dans `results/metrics/generation_summary.json`.

## Les trois sortes de désordre

| Sorte | Exemples | Ce que le système doit faire |
|---|---|---|
| **Normal mais inhabituel** | Remboursements (montant négatif), grosses commandes de professionnels, pics de soldes, homonymes | Ne PAS les signaler |
| **Erreurs classiques** | Montant nul ou négatif sur une vente, devise incohérente, valeur hors référentiel, valeur manquante, doublon exact | Une règle tirée du contrat suffit |
| **Anomalies subtiles** | Pic d'achat d'un client (10 fois son habitude mais banal pour la catégorie), erreur de quantité, vente en magasin à 3 h du matin, doublon à quelques minutes et quelques centimes près | Aucune règle du contrat ne les voit : c'est le terrain de l'IA |

S'y ajoute une **dérive** : pendant trois semaines de septembre, un bug fait monter de 12 % tous les prix de la catégorie Maison en France. Ligne à ligne, c'est invisible ; c'est le mécanisme 2 (dérives) qui doit la repérer.

## Les garanties vérifiées par les tests

Le fichier `tests/test_data_generation.py` vérifie notamment que :
- la même graine redonne exactement le même monde ;
- aucune étiquette ne se trouve dans les données publiées ;
- les données correctes ne violent **aucune** règle du contrat ;
- chaque erreur classique viole **au moins une** règle du contrat ;
- **aucune** anomalie subtile ne viole de règle du contrat ;
- pour un doublon, seule la copie est une anomalie : l'original reste une vente légitime ;
- les homonymes ont des adresses e-mail différentes, et chaque doublon diffère de son original par au moins un détail.

## Limites à connaître

- Ce sont des **hypothèses de simulation**, pas des statistiques réelles. Elles sont réunies dans `config.py` pour être discutées.
- Les noms, e-mails, téléphones, IBAN et numéros de sécurité sociale sont **fictifs**. Les IBAN et les numéros de sécurité sociale ont une clé de contrôle valide, pour être réalistes face à un détecteur.
- Les journaux d'accès de la Finance, qui servent aux mécanismes 5 et 6, seront générés à l'étape 6.
