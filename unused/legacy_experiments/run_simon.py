"""End-to-end Simon reproduction experiment.

Run from the project root:

    python -m experiments.run_simon
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.evaluate import evaluate_pair
from src.noise import build_depolarizing_noise_model
from src.simon import build_baseline_circuit
from src.vanqira import build_simon_asserted_circuit, circuit_overhead


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "results" / "raw"


def run_experiment(
    secret: str = "101",
    shots: int = 4096,
    one_qubit_errors: tuple[float, ...] = (0.0, 0.001, 0.003, 0.005, 0.01, 0.02, 0.03),
) -> pd.DataFrame:
    baseline = build_baseline_circuit(secret)
    asserted = build_simon_asserted_circuit(secret, method="xor")
    rows: list[dict[str, float | int | str]] = []

    for idx, p1 in enumerate(one_qubit_errors):
        p2 = min(1.0, 10.0 * p1)
        noise_model = build_depolarizing_noise_model(p1, p2)
        row = evaluate_pair(
            baseline,
            asserted,
            secret=secret,
            shots=shots,
            noise_model=noise_model,
            seed=2026 + idx * 17,
        )
        rows.append(
            {
                "secret": secret,
                "one_qubit_error": p1,
                "two_qubit_error": p2,
                **row,
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    df = run_experiment()
    results_path = RAW_DIR / "simon_results.csv"
    df.to_csv(results_path, index=False)

    overhead_df = pd.DataFrame(circuit_overhead("101"))
    overhead_path = RAW_DIR / "simon_overhead.csv"
    overhead_df.to_csv(overhead_path, index=False)

    display_columns = [
        "one_qubit_error",
        "two_qubit_error",
        "baseline_success_rate",
        "filtered_success_rate",
        "pass_rate",
        "error_report_rate",
    ]
    print("\nSimon success and assertion metrics")
    print(df[display_columns].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nCircuit overhead")
    print(overhead_df.to_string(index=False))
    print(f"\nWrote {results_path}")
    print(f"Wrote {overhead_path}")


if __name__ == "__main__":
    main()
