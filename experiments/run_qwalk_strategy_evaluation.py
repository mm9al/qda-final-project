"""Evaluate quantum-walk assertion strategy winners under shared Pauli traces.

Run from the project root:

    python3 -m experiments.run_qwalk_strategy_evaluation \
      --error-probability 0.01 \
      --num-trials 1000

Optional realistic extension with oracle noise:

    python3 -m experiments.run_qwalk_strategy_evaluation \
      --include-oracle-noise \
      --error-probability 0.01 \
      --num-trials 1000 \
      --seed 2026
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import pandas as pd

from src.assertion import VanishingAssertionSpec, synthesize_vanishing_oracle
from src.evaluate import (
    evaluate_qwalk_strategy,
    generate_pauli_error_traces,
    ideal_final_support,
)
from src.quantum_walk import build_cycle_quantum_walk
from src.utils import analyze_checkpoint


RAW_DIR = PROJECT_ROOT / "results" / "raw"
WINNERS_PATH = RAW_DIR / "qwalk_strategy_winners.csv"
PUBLIC_COLUMNS = [
    "Strategy",
    "Checkpoint",
    "Oracle Method",
    "Coverage",
    "Oracle Gates",
    "CX Overhead",
    "TP",
    "TN",
    "FP",
    "FN",
    "Detection Rate",
    "Support-Level FPR",
    "Post-selected Support-Valid Rate",
]


def _candidate_seed(seed: int, checkpoint: int, oracle_method: str, offset: int) -> int:
    method_value = sum(
        (index + 1) * ord(character)
        for index, character in enumerate(oracle_method)
    )
    return seed + offset + checkpoint * 1009 + method_value


def _build_oracle(circuit, checkpoint: int, label: str, oracle_method: str):
    analysis = analyze_checkpoint(
        circuit=circuit,
        checkpoint=checkpoint,
    )
    spec = VanishingAssertionSpec(
        num_asserted_qubits=circuit.num_qubits,
        vanishing_states=tuple(analysis.vanishing_states),
        description=label,
    )
    return synthesize_vanishing_oracle(
        spec=spec,
        method=oracle_method,
    )


def run_evaluation(
    num_trials: int = 1000,
    error_probability: float = 0.01,
    seed: int = 2026,
    include_oracle_noise: bool = False,
    *,
    shots: int | None = None,
) -> pd.DataFrame:
    if shots is not None:
        num_trials = shots

    if not WINNERS_PATH.exists():
        raise FileNotFoundError(
            f"{WINNERS_PATH} does not exist. Run "
            "`python3 -m experiments.run_qwalk_strategy_comparison` first."
        )

    quantum_walk = build_cycle_quantum_walk(
        num_position_qubits=2,
        num_steps=5,
    )
    winners = pd.read_csv(WINNERS_PATH)
    support = ideal_final_support(quantum_walk.circuit)
    traces = generate_pauli_error_traces(
        circuit=quantum_walk.circuit,
        num_traces=num_trials,
        error_probability=error_probability,
        seed=seed,
    )

    metric_cache: dict[tuple[int, str], dict[str, float | int]] = {}
    unique_candidates = winners.drop_duplicates(
        subset=["checkpoint", "oracle_method"],
        keep="first",
    )

    for _, winner in unique_candidates.iterrows():
        checkpoint = int(winner["checkpoint"])
        label = str(winner["label"])
        oracle_method = str(winner["oracle_method"])
        candidate_key = (checkpoint, oracle_method)
        oracle = _build_oracle(
            circuit=quantum_walk.circuit,
            checkpoint=checkpoint,
            label=label,
            oracle_method=oracle_method,
        )

        oracle_traces = None
        if include_oracle_noise:
            oracle_traces = generate_pauli_error_traces(
                circuit=oracle,
                num_traces=num_trials,
                error_probability=error_probability,
                seed=_candidate_seed(
                    seed=seed,
                    checkpoint=checkpoint,
                    oracle_method=oracle_method,
                    offset=1009,
                ),
            )

        metric_cache[candidate_key] = evaluate_qwalk_strategy(
            circuit=quantum_walk.circuit,
            checkpoint=checkpoint,
            oracle=oracle,
            traces=traces,
            final_support=support,
            seed=_candidate_seed(
                seed=seed,
                checkpoint=checkpoint,
                oracle_method=oracle_method,
                offset=4096,
            ),
            oracle_traces=oracle_traces,
        )

    rows: list[dict[str, float | int | str]] = []

    for _, winner in winners.iterrows():
        strategy = str(winner["strategy"])
        checkpoint = int(winner["checkpoint"])
        label = str(winner["label"])
        oracle_method = str(winner["oracle_method"])
        metrics = metric_cache[(checkpoint, oracle_method)]

        rows.append(
            {
                "Strategy": strategy,
                "Checkpoint": label,
                "Oracle Method": oracle_method,
                "Coverage": float(winner["coverage"]),
                "Oracle Gates": int(winner["oracle_gate_count"]),
                "CX Overhead": int(winner["asserted_cx_overhead"]),
                **metrics,
            }
        )

    return pd.DataFrame(rows, columns=PUBLIC_COLUMNS)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate qwalk assertion strategies under shared Pauli noise.",
    )
    parser.add_argument(
        "--include-oracle-noise",
        action="store_true",
        help="Also inject Pauli noise into assertion-oracle gates.",
    )
    parser.add_argument(
        "--error-probability",
        type=float,
        default=0.01,
        help="Pauli error probability per touched qubit after each gate.",
    )
    parser.add_argument(
        "--num-trials",
        type=int,
        default=1000,
        help="Number of shared Monte Carlo traces.",
    )
    parser.add_argument(
        "--shots",
        dest="num_trials",
        type=int,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=2026,
        help="Random seed controlling reproducibility.",
    )
    return parser.parse_args(argv)


def output_path_for_run(
    *,
    error_probability: float,
    include_oracle_noise: bool,
) -> Path:
    probability_tag = str(error_probability).replace(".", "_")
    if include_oracle_noise:
        output_filename = (
            f"qwalk_strategy_evaluation_oracle_noise_p{probability_tag}.csv"
        )
    else:
        output_filename = f"qwalk_strategy_evaluation_p{probability_tag}.csv"

    return RAW_DIR / output_filename


def main() -> None:
    args = parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    results = run_evaluation(
        num_trials=args.num_trials,
        error_probability=args.error_probability,
        seed=args.seed,
        include_oracle_noise=args.include_oracle_noise,
    )
    output_path = output_path_for_run(
        error_probability=args.error_probability,
        include_oracle_noise=args.include_oracle_noise,
    )
    results.to_csv(output_path, index=False)

    if args.include_oracle_noise:
        print("\n=== Quantum Walk Strategy Evaluation With Oracle Noise ===")
    else:
        print("=== Quantum Walk Strategy Evaluation ===")
    print(results.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print(f"\nWrote {output_path}")


if __name__ == "__main__":
    main()
