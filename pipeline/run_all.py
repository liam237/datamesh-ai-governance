"""Commande unique du projet : `make all` ou `python -m pipeline.run_all`.

Elle enchaîne les étapes du parcours d'une donnée, puis l'évaluation. Chaque
étape est branchée ici au fur et à mesure de son implémentation.
"""


def _generate_data() -> None:
    from data_generation import config as C
    from data_generation.generate import build, write

    write(build())                                          # jeu de conception
    write(build(test=True), root=C.PATHS.test_root,         # jeu de développement (ex-test)
          summary_path="results/metrics/generation_summary_test.json", seed=C.TEST_SEED)
    write(build(exam=True), root=C.PATHS.exam_root,         # jeu d'examen, sous scellé
          summary_path="results/metrics/generation_summary_exam.json", seed=C.EXAM_SEED)


def _evaluate_baselines() -> None:
    from evaluation.evaluate_baselines import main

    main()


def _compare_anomaly_models() -> None:
    from evaluation.compare_anomaly_models import main

    main()


STEPS = [
    ("Génération des données simulées (conception, développement, examen)", _generate_data),
    ("1. À l'arrivée : anomalies, données personnelles", None),
    ("2. Au nettoyage : auto-correction, résolution d'entités", None),
    ("3. À la publication : documentation, lignage", None),
    ("4. À la consommation : contrôle d'accès, analyse comportementale", None),
    ("5. Dans la durée : dérives, FinOps", None),
    ("Évaluation des références simples (contrat, expert)", _evaluate_baselines),
    ("Mécanisme 1 : comparaison des méthodes de détection d'anomalies", _compare_anomaly_models),
    ("Évaluation des autres mécanismes : métriques et figures", None),
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
