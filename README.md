# Quantum-Walk Vanishing-State Assertions

This project implements a reproducible vanishing-state assertion prototype for
coined quantum-walk circuits. It evaluates how checkpoint placement affects
vanishing support, error detection, and circuit cost.

## Research Questions

1. Do quantum-walk checkpoints provide useful vanishing support?
2. Can assertion oracles be synthesized with reasonable overhead?
3. How should assertion checkpoints be chosen under a coverage-cost trade-off?

## Workflow

```text
Build quantum-walk circuit
Scan candidate checkpoints
Extract vanishing states at each checkpoint
Synthesize assertion oracle
  - minterm: directly enumerate all vanishing states
  - simplified_boolean: simplify the vanishing-state predicate before synthesis
Insert assertion oracle at the checkpoint
Evaluate:
  - static analysis: vanishing states, oracle cost, and checkpoint scores
  - noisy evaluation: selected strategies under shared Pauli-noise traces
```

The quantum walk uses one coin qubit and `position_qubits` position qubits, so
`total_qubits = position_qubits + 1` and `basis_states = 2 ** total_qubits`.

## Experiment Setting

The scaling suite evaluates:

```text
position_qubits = 2, 3, 4, 5, 6
steps           = 2, 4, 6, 8, 10, 12
oracle methods  = minterm, simplified_boolean
strategies      = min_cost, max_coverage, max_fault_sensitivity,
                  best_detection_cost_proxy, late_checkpoint
```

This creates:

```text
30 benchmark settings
420 checkpoint-oracle candidates
150 strategy winners
```

For `minterm`, candidates with more than 32 vanishing states are retained in the
CSV but marked as skipped.

## Main Results

### RQ1: Vanishing States Across Checkpoints

| Position qubits `p` | Basis states | Mean coverage `C_t` | Pauli-fault hit rate | Average reachable states |
| ---: | ---: | ---: | ---: | ---: |
| 2 | 8 | 0.705 | 0.492 | 2.36 |
| 3 | 16 | 0.670 | 0.379 | 5.29 |
| 4 | 32 | 0.737 | 0.401 | 8.40 |
| 5 | 64 | 0.858 | 0.477 | 9.07 |
| 6 | 128 | 0.929 | 0.508 | 9.07 |

`coverage` is the fraction of basis states with zero amplitude at a checkpoint.
The Pauli-fault hit rate is the checkpoint-local proxy
`avg_{q,P in {X,Y,Z}} || Pi_V P_q |psi_t> ||^2`, where `V` is the vanishing
subspace.

### RQ2: Oracle Synthesis Cost

| Oracle method | Success | Skipped | Mean CX overhead |
| --- | ---: | ---: | ---: |
| `minterm` | 126 / 210 | 84 | 710.0 |
| `simplified_boolean` | 210 / 210 | 0 | 36.4 |

`minterm` builds one multi-controlled term per vanishing basis state.
`simplified_boolean` converts the same predicate into algebraic normal form
before emitting XOR-of-products gates.

### RQ3: Checkpoint Selection Strategies

| Strategy | Relative checkpoint | Coverage | Norm. CX | Detection rate |
| --- | ---: | ---: | ---: | ---: |
| `late_checkpoint` | 1.000 | 0.633 | 0.032 | 1.000 |
| `best_detection_cost_proxy` | 0.621 | 0.594 | 0.003 | 0.579 |
| `min_cost` | 0.332 | 0.698 | 0.003 | 0.330 |
| `max_coverage` | 0.228 | 0.914 | 0.120 | 0.276 |
| `max_fault_sensitivity` | 0.131 | 0.883 | 0.079 | 0.175 |

`relative checkpoint` is `checkpoint_step / steps`. `Norm. CX` is
`asserted_cx_overhead / baseline_cx_count`. The detection rate comes from noisy
Monte Carlo evaluation under shared Pauli-noise traces.

## Reproduce

Use Python 3 from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 -m unittest discover
python3 -m experiments.run_qwalk_scaling
python3 -m experiments.run_qwalk_scaling_evaluation \
  --error-probability 0.01 \
  --num-trials 100 \
  --seed 2026
```

The main CSV outputs are written to `results/raw/`. Main figures are written to
`results/`.

## Important Files

```text
src/quantum_walk.py        quantum-walk circuit construction
src/utils.py               checkpoint statevector and Pauli-fault analysis
src/assertion.py           minterm and simplified Boolean assertion oracles
src/qwalk_scaling.py       scaling-suite scan, strategy selection, evaluation
src/optimizer.py           checkpoint insertion and cost metrics
src/evaluate.py            shared Pauli-noise trace evaluation
experiments/               command-line experiment entrypoints
tests/                     unit tests
results/raw/               formal CSV outputs for the current report
results/                   formal figures for the current report
unused/                    legacy, auxiliary, and generated-cache files
```

## Current Output Files

```text
results/raw/qwalk_benchmark_suite.csv
results/raw/qwalk_checkpoint_landscape.csv
results/raw/qwalk_scaling_candidates.csv
results/raw/qwalk_scaling_strategy_winners.csv
results/raw/qwalk_scaling_strategy_evaluation_p0_01.csv

results/qwalk_vanishing_support_heatmap.png
results/qwalk_coverage_vs_fault_sensitivity.png
results/qwalk_oracle_cost_vs_coverage.png
results/qwalk_detection_vs_overhead.png
results/qwalk_strategy_ranking_across_scales.png
results/qwalk_vanishing_ratio_by_checkpoint.png
```
