"""Commande unique du projet : `make all` ou `python -m pipeline.run_all`.

Elle enchaîne les étapes du parcours d'une donnée, puis l'évaluation. Chaque
étape est branchée ici au fur et à mesure de son implémentation.
"""


def _generate_data() -> None:
    from data_generation.generate import build, write

    write(build())


STEPS = [
    ("Génération des données simulées", _generate_data),
    ("1. À l'arrivée : anomalies, données personnelles", None),
    ("2. Au nettoyage : auto-correction, résolution d'entités", None),
    ("3. À la publication : documentation, lignage", None),
    ("4. À la consommation : contrôle d'accès, analyse comportementale", None),
    ("5. Dans la durée : dérives, FinOps", None),
    ("Évaluation : métriques et figures", None),
]


def main() -> int:
    for name, step in STEPS:
        if step is None:
            print(f"[à venir] {name}")
        else:
            print(f"[en cours] {name}", flush=True)
            step()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
