from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import os

matplotlib_config_dir = PROJECT_ROOT / "results" / ".matplotlib"
matplotlib_config_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_config_dir))
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_ROOT / "results" / ".cache"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


def main() -> None:
    input_path = PROJECT_ROOT / "results" / "raw" / "qwalk_results.csv"
    if not input_path.exists():
        raise FileNotFoundError(
            "Run experiments/run_checkpoint_optimization.py before plotting."
        )

    results = pd.read_csv(input_path)

    output_dir = PROJECT_ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "qwalk_checkpoint_tradeoff.png"

    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    ax2 = ax1.twinx()

    ax1.plot(
        results["label"],
        results["sparsity"],
        marker="o",
        label="Sparsity",
        color="#2563eb",
    )
    ax2.plot(
        results["label"],
        results["overhead_ratio_proxy"],
        marker="s",
        label="Overhead proxy",
        color="#dc2626",
    )

    ax1.set_xlabel("Checkpoint")
    ax1.set_ylabel("Sparsity")
    ax2.set_ylabel("Overhead ratio proxy")
    ax1.set_ylim(0, 1)
    ax1.tick_params(axis="x", rotation=30)
    ax1.grid(True, axis="y", alpha=0.3)

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc="best")

    fig.tight_layout()
    fig.savefig(output_path, dpi=200)

    print(f"Saved plot to: {output_path}")


if __name__ == "__main__":
    main()
