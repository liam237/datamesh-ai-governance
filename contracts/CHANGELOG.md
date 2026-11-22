# Historique des contrats

Un contrat de données évolue comme un logiciel : chaque modification change son numéro de version, selon la convention `majeur.mineur.correctif`.

- **Majeur** (2.0.0) : un changement qui casse les usages existants, par exemple une colonne supprimée ou renommée.
- **Mineur** (1.1.0) : un ajout compatible, par exemple une nouvelle règle de qualité.
- **Correctif** (1.0.1) : une correction sans effet sur le fond, par exemple une faute dans une description.

Les versions antérieures sont conservées dans `history/`, pour pouvoir rejouer une évaluation avec le contrat tel qu'il était.

## Contrat n° 1 : Ventes vers Finance (`ventes_vers_finance.yaml`)

### 1.1.0 — 22/11/2026
- **Ajout** de la règle `q-magasin-horaires` : une vente du canal Magasin doit avoir lieu entre 9 h et 20 h.
- **Origine :** l'exploration des données (notebook `01_exploration.ipynb`, section 7, figure 6) a révélé 69 ventes « en magasin » entre 1 h et 5 h du matin. Le contrat 1.0.0 ne disait rien des horaires, donc aucune règle ne les attrapait.
- **Décision :** proposée par l'analyse, validée par le propriétaire du contrat (rôle tenu par William dans ce projet).
- **Ce que cela illustre :** la gouvernance fédérée en action. Une découverte faite sur les données fait évoluer la règle commune, au lieu que celle-ci reste figée.

### 1.0.0 — 21/11/2026
- Version initiale. Conservée dans `history/ventes_vers_finance_v1.0.0.yaml`.

## Contrat n° 2 : Service client vers Finance (`service_client_vers_finance.yaml`)

### 1.0.0 — 21/11/2026
- Version initiale.
