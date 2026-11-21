# data_generation/

Le **générateur du monde simulé** : des clients avec leurs habitudes, des produits avec leurs prix, un calendrier avec les soldes et Noël, puis les trois domaines (Ventes, Service client, Finance).

On y mélange trois sortes de désordre :
1. **le normal mais inhabituel**, que le système ne doit pas signaler ;
2. **les erreurs classiques**, qu'une règle simple attrape ;
3. **les anomalies subtiles**, où l'IA doit prouver sa valeur.

La **vérité terrain** (quelle ligne est anormale, de quelle famille, de quelle difficulté) est écrite dans un fichier séparé, que seul `evaluation/` a le droit de lire.
