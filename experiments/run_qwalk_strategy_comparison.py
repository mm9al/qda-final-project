"""Compare quantum-walk assertion checkpoint and oracle strategies.

Run from the project root:

    python3 -m experiments.run_qwalk_strategy_comparison
"""

from __future__ import annotations

from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

matplotlib_config_dir = PROJECT_ROOT / "results" / ".matplotlib"
matplotlib_config_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_config_dir))
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_ROOT / "results" / ".cache"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from src.optimizer import (
    scan_checkpoint_strategy_comparison,
    select_strategy_winners,
)
from src.quantum_walk import build_cycle_quantum_walk


RAW_DIR = PROJECT_ROOT / "results" / "raw"
RESULTS_DIR = PROJECT_ROOT / "results"


def write_strategy_plot(comparison, winners) -> Path:
    output_path = RESULTS_DIR / "qwalk_strategy_comparison.png"

    fig, ax = plt.subplots(figsize=(8.5, 5))

    for oracle_method, group in comparison.groupby("oracle_method"):
        ax.scatter(
            group["normalized_cost"],
            group["coverage"],
            s=70,
            label=oracle_method,
            alpha=0.85,
        )

        for _, row in group.iterrows():
            ax.annotate(
                row["label"].replace("after_walk_", ""),
                (row["normalized_cost"], row["coverage"]),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=8,
                alpha=0.75,
            )

    cost_benefit = winners[winners["strategy"] == "cost_benefit"].iloc[0]
    ax.scatter(
        [cost_benefit["normalized_cost"]],
        [cost_benefit["coverage"]],
        s=160,
        facecolors="none",
        edgecolors="#111827",
        linewidths=2,
        label="cost_benefit winner",
    )

    ax.set_xlabel("Normalized cost")
    ax.set_ylabel("Coverage / sparsity")
    ax.set_title("Quantum walk assertion strategy comparison")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")

    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)

    return output_path


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    quantum_walk = build_cycle_quantum_walk(
        num_position_qubits=2,
        num_steps=5,
    )

    comparison = scan_checkpoint_strategy_comparison(
        circuit=quantum_walk.circuit,
        checkpoints=quantum_walk.checkpoints,
        checkpoint_labels=quantum_walk.checkpoint_labels,
    )
    winners = select_strategy_winners(comparison)

    comparison_path = RAW_DIR / "qwalk_strategy_comparison.csv"
    winners_path = RAW_DIR / "qwalk_strategy_winners.csv"
    comparison.to_csv(comparison_path, index=False)
    winners.to_csv(winners_path, index=False)
    plot_path = write_strategy_plot(comparison, winners)

    display_columns = [
        "strategy",
        "label",
        "oracle_method",
        "coverage",
        "oracle_gate_count",
        "asserted_depth_overhead",
        "asserted_cx_overhead",
        "normalized_cost",
        "benefit_cost_score",
    ]

    print("=== Quantum Walk Strategy Winners ===")
    print(
        winners[display_columns].to_string(
            index=False,
            float_format=lambda value: f"{value:.4f}",
        )
    )
    print(f"\nWrote {comparison_path}")
    print(f"Wrote {winners_path}")
    print(f"Wrote {plot_path}")


if __name__ == "__main__":
    main()
