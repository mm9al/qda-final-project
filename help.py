"""Project help for the VanQiRA experiment workflow."""

from __future__ import annotations

import argparse


WORKFLOW_HELP = """\
VanQiRA Simon and Quantum Walk Experiments

Setup:
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt

Canonical workflow:
  1. Verify the code before generating formal outputs:
     python3 -m unittest discover

  2. Run Simon baseline/asserted metrics:
     python3 -m experiments.run_simon

  3. Run the qwalk checkpoint scan:
     python3 -m experiments.run_checkpoint_optimization

  4. Select qwalk checkpoint/oracle strategies:
     python3 -m experiments.run_qwalk_strategy_comparison

  5. Run the parameterized qwalk scaling suite:
     python3 -m experiments.run_qwalk_scaling

  6. Evaluate the selected qwalk strategies:
     python3 -m experiments.run_qwalk_strategy_evaluation \
       --error-probability 0.01 \
       --num-trials 1000 \
       --seed 2026

Optional auxiliary runs:
  Noiseless sanity check:
  python3 -m experiments.run_qwalk_strategy_evaluation \
    --error-probability 0 \
    --num-trials 100 \
    --seed 2026

  Apply noise to assertion-oracle gates:
  python3 -m experiments.run_qwalk_strategy_evaluation \
    --include-oracle-noise \
    --error-probability 0.01 \
    --num-trials 1000 \
    --seed 2026

  Representative noisy scaling smoke test:
  python3 -m experiments.run_qwalk_scaling_evaluation \
    --error-probability 0.01 \
    --num-trials 100 \
    --seed 2026

Move auxiliary CSV outputs from results/raw/ to results/auxiliary/raw/.

More help:
  python3 help.py --outputs
  python3 help.py --archive
"""


OUTPUTS_HELP = """\
Generated outputs:
  Main report results:
  results/raw/simon_results.csv
    Simon baseline/asserted success and assertion pass/error rates.

  results/raw/simon_overhead.csv
    Simon baseline/asserted circuit overhead.

  results/raw/qwalk_results.csv
    Candidate qwalk checkpoints and static sparsity proxy scores.

  results/raw/qwalk_strategy_comparison.csv
    Checkpoint/oracle method cost-benefit comparison.

  results/raw/qwalk_strategy_winners.csv
    Six selected qwalk strategies used by the formal evaluation.

  results/raw/qwalk_benchmark_suite.csv
    Parameterized qwalk benchmark family summary.

  results/raw/qwalk_scaling_candidates.csv
    Full scaling-suite checkpoint/oracle candidate table.

  results/raw/qwalk_scaling_strategy_winners.csv
    Six selected strategies for every scaling-suite benchmark setting.

  results/raw/qwalk_strategy_evaluation_p0_01.csv
    Formal qwalk noisy Monte Carlo evaluation at p = 0.01.

  results/qwalk_strategy_comparison.png
    Strategy cost/coverage plot.

  results/qwalk_vanishing_ratio_by_checkpoint.png
  results/qwalk_oracle_cost_vs_coverage.png
  results/qwalk_strategy_ranking_across_scales.png
    Scaling-suite figures for vanishing ratios, Pareto cost/coverage, and
    cross-scale strategy ranking.

  Auxiliary results:
  results/auxiliary/raw/qwalk_strategy_evaluation_p0_0.csv
  results/auxiliary/raw/qwalk_strategy_evaluation_p0_005.csv
  results/auxiliary/raw/qwalk_strategy_evaluation_p0_02.csv
    Sanity checks and probability sweeps for the primary qwalk noise model.

  results/auxiliary/raw/qwalk_strategy_evaluation_oracle_noise_p0_01.csv
    Optional p = 0.01 extension where assertion-oracle gates also receive
    Pauli noise.

  results/auxiliary/raw/qwalk_scaling_strategy_evaluation_*.csv
    Representative scaling-suite noisy smoke tests.
"""


ARCHIVE_HELP = """\
Archive:
  archive/ contains old demos, disabled entrypoints, and legacy outputs that are
  kept for reference only. These files are not required for the current
  reproduction workflow.

Archived experiment scripts:
  archive/experiments/run_qwalk_baseline.py
  archive/experiments/run_qwalk_assertion.py
  archive/experiments/run_simon_baseline.py
  archive/experiments/run_simon_assertion.py
  archive/experiments/plot_simon_results.py
  archive/experiments/plot_checkpoint_tradeoff.py

Archived outputs:
  archive/results/qwalk_checkpoint_tradeoff.png
  archive/results/raw/qwalk_overhead.csv
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show project workflow help.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--outputs",
        action="store_true",
        help="Show generated output files and their purpose.",
    )
    group.add_argument(
        "--archive",
        action="store_true",
        help="Show archived files that are outside the current workflow.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.outputs:
        print(OUTPUTS_HELP)
        return

    if args.archive:
        print(ARCHIVE_HELP)
        return

    print(WORKFLOW_HELP)


if __name__ == "__main__":
    main()
