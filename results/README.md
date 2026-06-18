# Results Index

This directory contains the formal outputs for the current quantum-walk
vanishing-state assertion workflow. Legacy, auxiliary, and generated-cache
files were moved to `../unused/`.

## Formal CSV Outputs

| File | Purpose |
| --- | --- |
| `raw/qwalk_benchmark_suite.csv` | Lists the scaling benchmark settings: position qubits, total qubits, basis states, and tested walk steps. |
| `raw/qwalk_checkpoint_landscape.csv` | One row per checkpoint with coverage, vanishing-state count, active support size, and Pauli-fault-sensitive proxy values. |
| `raw/qwalk_scaling_candidates.csv` | Full checkpoint-oracle candidate table for both synthesis methods, including synthesis status, static cost, and detection-cost proxy scores. |
| `raw/qwalk_scaling_strategy_winners.csv` | Five selected checkpoint strategies for every `(position_qubits, steps)` setting. |
| `raw/qwalk_scaling_strategy_evaluation_p0_01.csv` | Noisy evaluation of selected strategies under shared Pauli-noise traces at error probability `0.01`. |

Expected counts:

```text
30 benchmark settings
420 checkpoint-oracle candidates
150 strategy winners
```

## Formal Figures

| File | Purpose |
| --- | --- |
| `qwalk_vanishing_support_heatmap.png` | Average vanishing-state coverage by position-qubit size and checkpoint step. |
| `qwalk_coverage_vs_fault_sensitivity.png` | Static coverage compared with the Pauli-fault-sensitive detection proxy. |
| `qwalk_oracle_cost_vs_coverage.png` | Oracle cost versus coverage, including the Pareto frontier. |
| `qwalk_detection_vs_overhead.png` | Noisy detection rate versus normalized added-CX overhead. |
| `qwalk_strategy_ranking_across_scales.png` | Cross-scale summary of the selected strategies. |
| `qwalk_vanishing_ratio_by_checkpoint.png` | Line-plot companion view of vanishing-state ratio by checkpoint. |

## Key Columns

| Column | Meaning |
| --- | --- |
| `coverage` | Fraction of computational-basis states that are vanishing at the checkpoint. |
| `fault_sensitive_detection` | Static Pauli-fault proxy: average probability that a single-qubit `X/Y/Z` fault moves the state into the vanishing subspace. |
| `bit_flip_detection` | `X/Y` component of the fault-sensitive proxy. |
| `phase_detection` | `Z` component of the fault-sensitive proxy; usually near zero for this basis-support assertion. |
| `asserted_cx_overhead` | Additional CX gates introduced by the asserted circuit compared with the baseline walk circuit. |
| `normalized_cx_overhead` | `asserted_cx_overhead / baseline_cx_count`. |
| `normalized_cost` | Average of normalized oracle gate count, depth overhead, and CX overhead. |
| `detection_cost_score` | `fault_sensitive_detection / normalized_cost`; used by `best_detection_cost_proxy`. |
| `Detection Rate` | In noisy evaluation, fraction of invalid final-support outcomes rejected by the assertion. |
| `Support-Level FPR` | False-positive rate against outcomes that still land in the ideal final support. |
| `Post-selected Support-Valid Rate` | Fraction of accepted outputs that remain in the ideal final support. |

## Strategy Set

The current report uses five strategies:

```text
min_cost
max_coverage
max_fault_sensitivity
best_detection_cost_proxy
late_checkpoint
```
