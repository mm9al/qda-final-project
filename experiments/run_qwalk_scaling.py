"""Run the parameterized quantum-walk scaling benchmark suite.

Run from the project root:

    python3 -m experiments.run_qwalk_scaling
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
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
import pandas as pd

from src.qwalk_scaling import (
    DEFAULT_POSITION_QUBITS,
    DEFAULT_WALK_STEPS,
    benchmark_suite_table,
    pareto_frontier,
    scan_scaling_candidates,
    select_scaling_strategy_winners,
)


RAW_DIR = PROJECT_ROOT / "results" / "raw"
RESULTS_DIR = PROJECT_ROOT / "results"


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def write_vanishing_ratio_plot(candidates: pd.DataFrame) -> Path:
    output_path = RESULTS_DIR / "qwalk_vanishing_ratio_by_checkpoint.png"
    unique_checkpoints = candidates.drop_duplicates(
        subset=["position_qubits", "steps", "checkpoint_step"],
        keep="first",
    )
    grouped = (
        unique_checkpoints.groupby(["position_qubits", "checkpoint_step"])["coverage"]
        .mean()
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(8.5, 5))
    for position_qubits, group in grouped.groupby("position_qubits"):
        ax.plot(
            group["checkpoint_step"],
            group["coverage"],
            marker="o",
            linewidth=2,
            label=f"p={position_qubits}",
        )

    ax.set_xlabel("Checkpoint step")
    ax.set_ylabel("Average vanishing-state ratio")
    ax.set_title("Vanishing-state ratio across quantum-walk checkpoints")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.3)
    ax.legend(title="Position qubits", loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def write_vanishing_support_heatmap(candidates: pd.DataFrame) -> Path:
    output_path = RESULTS_DIR / "qwalk_vanishing_support_heatmap.png"
    unique_checkpoints = candidates.drop_duplicates(
        subset=["position_qubits", "steps", "checkpoint_step"],
        keep="first",
    )
    landscape = (
        unique_checkpoints.groupby(["position_qubits", "checkpoint_step"])["coverage"]
        .mean()
        .reset_index()
    )
    heatmap = landscape.pivot(
        index="position_qubits",
        columns="checkpoint_step",
        values="coverage",
    ).sort_index()

    fig_width = max(7.5, 0.58 * len(heatmap.columns) + 2.5)
    fig_height = max(4.2, 0.5 * len(heatmap.index) + 2.2)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    image = ax.imshow(
        heatmap.to_numpy(),
        aspect="auto",
        cmap="viridis",
        vmin=0,
        vmax=1,
    )

    ax.set_xticks(range(len(heatmap.columns)))
    ax.set_xticklabels([str(column) for column in heatmap.columns])
    ax.set_yticks(range(len(heatmap.index)))
    ax.set_yticklabels([f"p={index}" for index in heatmap.index])
    ax.set_xlabel("Checkpoint step")
    ax.set_ylabel("Position qubits")
    ax.set_title("Vanishing-support landscape across checkpoints")

    for row_index, position_qubits in enumerate(heatmap.index):
        for column_index, checkpoint_step in enumerate(heatmap.columns):
            value = heatmap.loc[position_qubits, checkpoint_step]
            if pd.notna(value):
                text_color = "white" if value < 0.55 else "#111827"
                ax.text(
                    column_index,
                    row_index,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=text_color,
                )

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Average vanishing-state ratio")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def checkpoint_landscape_table(candidates: pd.DataFrame) -> pd.DataFrame:
    unique_checkpoints = candidates.drop_duplicates(
        subset=["position_qubits", "steps", "checkpoint_step"],
        keep="first",
    )
    table = unique_checkpoints[
        [
            "position_qubits",
            "total_qubits",
            "basis_states",
            "steps",
            "checkpoint_step",
            "checkpoint",
            "label",
            "coverage",
            "num_vanishing_states",
            "fault_sensitive_detection",
            "bit_flip_detection",
            "phase_detection",
        ]
    ].copy()
    table["active_support_size"] = (
        table["basis_states"] - table["num_vanishing_states"]
    )
    return table.sort_values(
        ["position_qubits", "steps", "checkpoint_step"],
        ignore_index=True,
    )


def write_cost_coverage_plot(candidates: pd.DataFrame) -> Path:
    output_path = RESULTS_DIR / "qwalk_oracle_cost_vs_coverage.png"
    ok = candidates[candidates["status"] == "ok"].dropna(
        subset=["coverage", "asserted_cx_overhead"]
    )
    frontier = pareto_frontier(ok, cost_column="asserted_cx_overhead")

    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    for oracle_method, group in ok.groupby("oracle_method"):
        ax.scatter(
            group["coverage"],
            group["asserted_cx_overhead"],
            s=34,
            alpha=0.62,
            label=oracle_method,
        )

    if not frontier.empty:
        frontier = frontier.sort_values(["coverage", "asserted_cx_overhead"])
        ax.plot(
            frontier["coverage"],
            frontier["asserted_cx_overhead"],
            color="#111827",
            linewidth=2,
            marker="o",
            markersize=4,
            label="Pareto frontier",
        )

    ax.set_xlabel("Coverage / vanishing-state ratio")
    ax.set_ylabel("Added CX gates")
    ax.set_title("Oracle cost versus assertion coverage")
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def write_coverage_fault_sensitivity_plot(candidates: pd.DataFrame) -> Path:
    output_path = RESULTS_DIR / "qwalk_coverage_vs_fault_sensitivity.png"
    ok = candidates[candidates["status"] == "ok"].dropna(
        subset=["coverage", "fault_sensitive_detection"]
    )
    unique_checkpoints = ok.drop_duplicates(
        subset=["position_qubits", "steps", "checkpoint"],
        keep="first",
    )

    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    for position_qubits, group in unique_checkpoints.groupby("position_qubits"):
        ax.scatter(
            group["coverage"],
            group["fault_sensitive_detection"],
            s=46,
            alpha=0.78,
            label=f"p={position_qubits}",
        )

    ax.plot([0, 1], [0, 1], color="#6b7280", linewidth=1, linestyle="--", alpha=0.6)
    ax.set_xlabel("Coverage / vanishing-state ratio")
    ax.set_ylabel("Fault-sensitive detection proxy")
    ax.set_title("Static coverage versus Pauli-fault-sensitive coverage")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.3)
    ax.legend(title="Position qubits", loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def write_strategy_ranking_plot(
    winners: pd.DataFrame,
    evaluation: pd.DataFrame | None = None,
) -> Path:
    output_path = RESULTS_DIR / "qwalk_strategy_ranking_across_scales.png"
    static_summary = (
        winners.groupby("strategy")
        .agg(
            avg_coverage=("coverage", "mean"),
            avg_fault_sensitive_detection=("fault_sensitive_detection", "mean"),
            avg_added_cx=("asserted_cx_overhead", "mean"),
        )
        .reset_index()
    )

    if evaluation is not None and not evaluation.empty:
        eval_summary = (
            evaluation.groupby("strategy")
            .agg(
                avg_detection=("Detection Rate", "mean"),
                avg_fpr=("Support-Level FPR", "mean"),
            )
            .reset_index()
        )
        summary = static_summary.merge(eval_summary, on="strategy", how="left")
        metrics = [
            ("avg_coverage", "Average coverage"),
            ("avg_fault_sensitive_detection", "Average fault-sensitive proxy"),
            ("avg_added_cx", "Average added CX"),
            ("avg_detection", "Average detection rate"),
            ("avg_fpr", "Average FPR"),
        ]
    else:
        summary = static_summary
        metrics = [
            ("avg_coverage", "Average coverage"),
            ("avg_fault_sensitive_detection", "Average fault-sensitive proxy"),
            ("avg_added_cx", "Average added CX"),
        ]

    label_map = {
        "balanced_proxy": "balanced",
        "best_detection_cost_proxy": "detection/cost",
        "cost_benefit": "cost/benefit",
        "late_checkpoint": "late",
        "max_coverage": "max coverage",
        "max_fault_sensitivity": "max fault proxy",
        "max_sparsity": "max sparsity",
        "min_cost": "min cost",
        "min_oracle_cost": "min oracle",
    }
    summary = summary.copy()
    summary["strategy_label"] = summary["strategy"].map(label_map).fillna(
        summary["strategy"]
    )

    fig, axes = plt.subplots(
        1,
        len(metrics),
        figsize=(5.2 * len(metrics), 4.8),
        squeeze=False,
    )
    for axis, (column, title) in zip(axes[0], metrics):
        axis.bar(
            summary["strategy_label"],
            summary[column],
            color="#2563eb",
            alpha=0.82,
        )
        axis.set_title(title)
        axis.tick_params(axis="x", labelrotation=25)
        axis.grid(True, axis="y", alpha=0.25)
        if column != "avg_added_cx":
            axis.set_ylim(0, 1.02)
        else:
            axis.set_ylim(bottom=0)

    fig.suptitle("Checkpoint-selection strategy ranking across scales")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run parameterized quantum-walk scaling benchmark.",
    )
    parser.add_argument(
        "--position-qubits",
        type=_parse_int_list,
        default=DEFAULT_POSITION_QUBITS,
        help="Comma-separated position-qubit sizes.",
    )
    parser.add_argument(
        "--steps",
        type=_parse_int_list,
        default=DEFAULT_WALK_STEPS,
        help="Comma-separated walk-step counts.",
    )
    parser.add_argument(
        "--max-minterm-states",
        type=int,
        default=32,
        help="Skip explicit minterm synthesis above this vanishing-state count.",
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

    suite = benchmark_suite_table(
        position_qubits=args.position_qubits,
        walk_steps=args.steps,
    )
    candidates = scan_scaling_candidates(
        position_qubits=args.position_qubits,
        walk_steps=args.steps,
        max_minterm_states=args.max_minterm_states,
        progress=not args.quiet,
    )
    winners = select_scaling_strategy_winners(candidates)

    suite_path = RAW_DIR / "qwalk_benchmark_suite.csv"
    candidates_path = RAW_DIR / "qwalk_scaling_candidates.csv"
    winners_path = RAW_DIR / "qwalk_scaling_strategy_winners.csv"
    landscape_path = RAW_DIR / "qwalk_checkpoint_landscape.csv"
    suite.to_csv(suite_path, index=False)
    candidates.to_csv(candidates_path, index=False)
    winners.to_csv(winners_path, index=False)
    checkpoint_landscape_table(candidates).to_csv(landscape_path, index=False)

    figure_paths = [
        write_vanishing_support_heatmap(candidates),
        write_vanishing_ratio_plot(candidates),
        write_coverage_fault_sensitivity_plot(candidates),
        write_cost_coverage_plot(candidates),
        write_strategy_ranking_plot(winners),
    ]

    ok_count = int((candidates["status"] == "ok").sum())
    skipped_count = int((candidates["status"] != "ok").sum())
    print("=== Quantum-Walk Scaling Benchmark ===")
    print(f"Settings: {len(suite) * len(args.steps)}")
    print(f"Candidate rows: {len(candidates)}")
    print(f"Successful candidates: {ok_count}")
    print(f"Non-ok candidates: {skipped_count}")
    print(f"Wrote {suite_path}")
    print(f"Wrote {candidates_path}")
    print(f"Wrote {winners_path}")
    print(f"Wrote {landscape_path}")
    for figure_path in figure_paths:
        print(f"Wrote {figure_path}")


if __name__ == "__main__":
    main()
