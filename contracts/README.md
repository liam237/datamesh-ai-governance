# contracts/

Les **contrats de données** entre domaines, au format YAML.

Un contrat décrit ce que le consommateur (la Finance) **attend** d'un producteur : le schéma, les règles de qualité, la fraîcheur, les règles sur les données sensibles et le propriétaire à alerter. Il n'affirme pas que les données sont parfaites : ce sont les mécanismes qui vérifient qu'il est respecté.

Prévu :
- `ventes_vers_finance.yaml` : les transactions ;
- `service_client_vers_finance.yaml` : les fiches clients et les tickets.
