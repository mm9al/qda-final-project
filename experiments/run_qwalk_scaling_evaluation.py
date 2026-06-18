"""Evaluate scaling-suite strategy winners under shared Pauli traces.

Run from the project root:

    python3 -m experiments.run_qwalk_scaling_evaluation --error-probability 0.01
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

matplotlib_config_dir = PROJECT_ROOT / "results" / ".matplotlib"
matplotlib_config_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_config_dir))
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_ROOT / "results" / ".cache"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from experiments.run_qwalk_scaling import write_strategy_ranking_plot
from src.qwalk_scaling import (
    DEFAULT_EVALUATION_POSITION_QUBITS,
    DEFAULT_EVALUATION_WALK_STEPS,
    evaluate_scaling_strategy_winners,
)


RAW_DIR = PROJECT_ROOT / "results" / "raw"
RESULTS_DIR = PROJECT_ROOT / "results"
WINNERS_PATH = RAW_DIR / "qwalk_scaling_strategy_winners.csv"


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def probability_tag(error_probability: float) -> str:
    return str(error_probability).replace(".", "_")


def output_path_for_run(
    *,
    error_probability: float,
    include_oracle_noise: bool,
) -> Path:
    tag = probability_tag(error_probability)
    if include_oracle_noise:
        return RAW_DIR / f"qwalk_scaling_strategy_evaluation_oracle_noise_p{tag}.csv"
    return RAW_DIR / f"qwalk_scaling_strategy_evaluation_p{tag}.csv"


def _pareto_detection_frontier(results: pd.DataFrame) -> pd.DataFrame:
    valid = results.dropna(
        subset=["normalized_cx_overhead", "Detection Rate"]
    ).copy()
    frontier_indices: list[int] = []

    for index, row in valid.iterrows():
        dominated = (
            (valid["Detection Rate"] >= row["Detection Rate"])
            & (valid["normalized_cx_overhead"] <= row["normalized_cx_overhead"])
            & (
                (valid["Detection Rate"] > row["Detection Rate"])
                | (
                    valid["normalized_cx_overhead"]
                    < row["normalized_cx_overhead"]
                )
            )
        ).any()
        if not dominated:
            frontier_indices.append(index)

    return valid.loc[frontier_indices].sort_values(
        ["normalized_cx_overhead", "Detection Rate"],
        ascending=[True, True],
    )


def write_detection_cost_tradeoff_plot(results: pd.DataFrame) -> Path:
    output_path = RESULTS_DIR / "qwalk_detection_vs_overhead.png"
    fig, ax = plt.subplots(figsize=(8.5, 5.4))

    for oracle_method, group in results.groupby("oracle_method"):
        scatter = ax.scatter(
            group["normalized_cx_overhead"],
            group["Detection Rate"],
            s=64,
            alpha=0.82,
            label=oracle_method,
            c=group["checkpoint_step"],
            cmap="viridis",
            vmin=results["checkpoint_step"].min(),
            vmax=results["checkpoint_step"].max(),
        )

    frontier = _pareto_detection_frontier(results)
    if not frontier.empty:
        baseline = pd.DataFrame(
            [
                {
                    "normalized_cx_overhead": 0.0,
                    "Detection Rate": 0.0,
                }
            ]
        )
        display_frontier = pd.concat(
            [baseline, frontier],
            ignore_index=True,
        ).sort_values("normalized_cx_overhead")
        ax.plot(
            display_frontier["normalized_cx_overhead"],
            display_frontier["Detection Rate"],
            color="#111827",
            linewidth=2,
            marker="o",
            markersize=4,
            label="Pareto frontier",
        )

    ax.scatter(
        [0.0],
        [0.0],
        s=90,
        marker="x",
        color="#dc2626",
        linewidths=2,
        label="no assertion",
    )
    colorbar = fig.colorbar(scatter, ax=ax)
    colorbar.set_label("Checkpoint step")
    ax.set_xlabel("Normalized added CX overhead")
    ax.set_ylabel("Detection rate")
    ax.set_title("Detection rate versus normalized assertion overhead")
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlim(left=-0.02)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate qwalk scaling-suite strategies under Pauli noise.",
    )
    parser.add_argument(
        "--position-qubits",
        type=_parse_int_list,
        default=DEFAULT_EVALUATION_POSITION_QUBITS,
        help="Comma-separated evaluation position-qubit sizes.",
    )
    parser.add_argument(
        "--steps",
        type=_parse_int_list,
        default=DEFAULT_EVALUATION_WALK_STEPS,
        help="Comma-separated evaluation walk-step counts.",
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
        default=100,
        help="Number of shared Monte Carlo traces per benchmark setting.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=2026,
        help="Random seed controlling reproducibility.",
    )
    parser.add_argument(
        "--include-oracle-noise",
        action="store_true",
        help="Also inject Pauli noise into assertion-oracle gates.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-setting progress output.",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if not WINNERS_PATH.exists():
        raise FileNotFoundError(
            f"{WINNERS_PATH} does not exist. Run "
            "`python3 -m experiments.run_qwalk_scaling` first."
        )

    winners = pd.read_csv(WINNERS_PATH)
    results = evaluate_scaling_strategy_winners(
        winners,
        position_qubits=args.position_qubits,
        walk_steps=args.steps,
        error_probability=args.error_probability,
        num_trials=args.num_trials,
        seed=args.seed,
        include_oracle_noise=args.include_oracle_noise,
        progress=not args.quiet,
    )
    output_path = output_path_for_run(
        error_probability=args.error_probability,
        include_oracle_noise=args.include_oracle_noise,
    )
    results.to_csv(output_path, index=False)
    figure_path = write_strategy_ranking_plot(winners, results)
    tradeoff_path = write_detection_cost_tradeoff_plot(results)

    print("=== Quantum-Walk Scaling Strategy Evaluation ===")
    print(
        results.to_string(
            index=False,
            float_format=lambda value: f"{value:.4f}",
        )
    )
    print(f"\nWrote {output_path}")
    print(f"Wrote {figure_path}")
    print(f"Wrote {tradeoff_path}")


if __name__ == "__main__":
    main()
