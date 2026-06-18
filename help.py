"""Project help for the quantum-walk assertion workflow."""

from __future__ import annotations

import argparse


WORKFLOW_HELP = """\
Quantum-Walk Vanishing-State Assertion Prototype

Setup:
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt

Canonical workflow:
  1. Verify the code:
     python3 -m unittest discover

  2. Run the static scaling suite:
     python3 -m experiments.run_qwalk_scaling

  3. Evaluate selected scaling strategies under Pauli-noise traces:
     python3 -m experiments.run_qwalk_scaling_evaluation \
       --error-probability 0.01 \
       --num-trials 100 \
       --seed 2026

More help:
  python3 help.py --outputs
  python3 help.py --unused
"""


OUTPUTS_HELP = """\
Formal outputs:
  results/raw/qwalk_benchmark_suite.csv
    Scaling benchmark settings.

  results/raw/qwalk_checkpoint_landscape.csv
    Deduplicated checkpoint landscape with coverage and fault sensitivity.

  results/raw/qwalk_scaling_candidates.csv
    Full checkpoint-oracle candidate table.

  results/raw/qwalk_scaling_strategy_winners.csv
    Five selected strategies for each scaling benchmark setting.

  results/raw/qwalk_scaling_strategy_evaluation_p0_01.csv
    Noisy strategy evaluation at error probability 0.01.

  results/qwalk_vanishing_support_heatmap.png
  results/qwalk_coverage_vs_fault_sensitivity.png
  results/qwalk_oracle_cost_vs_coverage.png
  results/qwalk_detection_vs_overhead.png
  results/qwalk_strategy_ranking_across_scales.png
  results/qwalk_vanishing_ratio_by_checkpoint.png
    Formal figures used by the current report.
"""


UNUSED_HELP = """\
unused/ contains files kept out of the current report workflow:

  unused/results_legacy/
    Older Simon, fixed-qwalk, and superseded scaling outputs.

  unused/results_auxiliary/
    Optional sanity checks, probability sweeps, and oracle-noise extensions.

  unused/legacy_archive/
    Old scripts and legacy artifacts.

  unused/legacy_src/
    Simon-only source modules kept for reference.

  unused/report_notes/
    Draft notes from earlier write-up stages.

  unused/generated_cache/
    Python, matplotlib, and OS-generated cache files.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show project workflow help.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--outputs",
        action="store_true",
        help="Show current output files and their purpose.",
    )
    group.add_argument(
        "--unused",
        action="store_true",
        help="Show files moved out of the current workflow.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.outputs:
        print(OUTPUTS_HELP)
        return

    if args.unused:
        print(UNUSED_HELP)
        return

    print(WORKFLOW_HELP)


if __name__ == "__main__":
    main()
