# VanQiRA-Style Simon and Quantum Walk Experiments

This repository contains a compact VanQiRA-style prototype for quantum runtime
assertion experiments. It is organized around two active targets:

- Simon's algorithm with measurement-level parity validation.
- A coined quantum walk with checkpoint-based vanishing-state assertion
  oracles.

The current quantum-walk workflow scans assertion checkpoints, synthesizes
assertion oracles, compares static circuit costs, selects representative
strategies, and evaluates those strategies under shared Pauli-noise traces.

This is a small reproducibility prototype, not the full BDD-based VanQiRA
framework.

---

## Quick Start

Use `python3`; the local environment does not provide `python`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the active workflow:

```bash
python3 -m experiments.run_simon
python3 -m experiments.run_checkpoint_optimization
python3 -m experiments.run_qwalk_strategy_comparison
python3 -m experiments.run_qwalk_strategy_evaluation \
  --error-probability 0.01 \
  --num-trials 1000
python3 -m experiments.run_qwalk_strategy_evaluation \
  --include-oracle-noise \
  --error-probability 0.01 \
  --num-trials 1000 \
  --seed 2026
python3 -m unittest discover
```

The root helper prints the same workflow and output index:

```bash
python3 help.py
python3 help.py --outputs
python3 help.py --archive
```

---

## Project Layout

```text
QDA-FINAL-PROJECT/
├── archive/       legacy scripts and old outputs kept for reference
├── experiments/   active command-line experiment entrypoints
├── report/        notes and write-up material
├── results/       active generated figures and CSV outputs
├── src/           circuit builders, assertion synthesis, evaluation utilities
├── tests/         unit tests
├── help.py
└── requirements.txt
```

The active result index is in `results/README.md`.

---

## Active Experiments

### 1. Simon Baseline

```bash
python3 -m experiments.run_simon
```

Outputs:

```text
results/raw/simon_results.csv
results/raw/simon_overhead.csv
```

The Simon experiment compares baseline and asserted circuits under depolarizing
noise. The asserted circuit uses a parity-style validation layer and reports
pass/error rates plus filtered and unfiltered success rates.

### 2. Quantum-Walk Checkpoint Scan

```bash
python3 -m experiments.run_checkpoint_optimization
```

Output:

```text
results/raw/qwalk_results.csv
```

This scan reports candidate checkpoint positions, vanishing-state counts,
state sparsity, a naive oracle-size proxy, and a simple balanced score. It is a
lightweight inspection pass; the later strategy comparison uses transpiled
oracle costs.

### 3. Quantum-Walk Strategy Comparison

```bash
python3 -m experiments.run_qwalk_strategy_comparison
```

Outputs:

```text
results/raw/qwalk_strategy_comparison.csv
results/raw/qwalk_strategy_winners.csv
results/qwalk_strategy_comparison.png
```

For every candidate checkpoint, the workflow extracts ideal vanishing states,
synthesizes assertion oracles, inserts the oracle into the quantum-walk
circuit, transpiles to a shared basis, and records depth, gate, and CX
overhead.

Oracle synthesis methods:

- `minterm`: one explicit matching condition per monitored vanishing state.
- `simplified_boolean`: simplified Boolean assertion function before circuit
  synthesis.

Checkpoint-selection strategies:

- `max_sparsity`: highest checkpoint sparsity.
- `min_oracle_cost`: lowest synthesized oracle gate count.
- `balanced_proxy`: highest sparsity-versus-proxy score.
- `cost_benefit`: highest coverage-versus-normalized-cost score.
- `early_checkpoint`: earliest assertable checkpoint.
- `late_checkpoint`: latest assertable checkpoint, used as an end-of-circuit
  support-filtering baseline.

Oracle methods describe how an assertion is implemented. Strategies describe
which checkpoint and oracle candidate are selected for evaluation.

### 4. Quantum-Walk Noisy Evaluation

Primary evaluation:

```bash
python3 -m experiments.run_qwalk_strategy_evaluation \
  --error-probability 0.01 \
  --num-trials 1000
```

Output:

```text
results/raw/qwalk_strategy_evaluation_p0_01.csv
```

Optional extension with noise applied to assertion-oracle gates:

```bash
python3 -m experiments.run_qwalk_strategy_evaluation \
  --include-oracle-noise \
  --error-probability 0.01 \
  --num-trials 1000 \
  --seed 2026
```

Output:

```text
results/raw/qwalk_strategy_evaluation_oracle_noise_p0_01.csv
```

The evaluator reuses the same sampled Pauli traces for all six strategies so
that strategy comparisons are not dominated by sampling variation. Parameterized
runs write probability-tagged files, for example
`qwalk_strategy_evaluation_p0_005.csv` or
`qwalk_strategy_evaluation_p0_02.csv`.

For a p = 0 sanity check:

```bash
python3 -m experiments.run_qwalk_strategy_evaluation \
  --error-probability 0 \
  --num-trials 100
```

---

## Current Result Snapshot

Current quantum-walk configuration:

```text
Position qubits:       2
Walk steps:            5
Strategies evaluated:  6
Primary noise:         Pauli X/Y/Z after original quantum-walk gates
Primary trials:        1000 shared traces
Primary p:             0.01
```

Static comparison highlights:

- `cost_benefit` selects `after_walk_step_2` with `simplified_boolean`.
- That candidate monitors 50.0% of basis states with 1 oracle gate and 1 added
  CX gate after transpilation.
- `max_sparsity` and `balanced_proxy` select `after_walk_step_4`, monitoring
  87.5% of basis states at higher oracle cost.
- `late_checkpoint` is a support-filtering baseline. It can score well at the
  final-support proxy but does not provide early-abort benefit.

Primary p = 0.01 noisy-evaluation highlights:

| Strategy | Checkpoint | Detection Rate | Support FPR | Post-selected Valid Rate |
| --- | --- | ---: | ---: | ---: |
| `max_sparsity` | `after_walk_step_4` | 0.8489 | 0.1118 | 0.9287 |
| `min_oracle_cost` | `after_walk_step_2` | 0.2115 | 0.0029 | 0.7361 |
| `balanced_proxy` | `after_walk_step_4` | 0.8489 | 0.1118 | 0.9287 |
| `cost_benefit` | `after_walk_step_2` | 0.2115 | 0.0029 | 0.7361 |
| `early_checkpoint` | `after_walk_step_1` | 0.1891 | 0.0087 | 0.7294 |
| `late_checkpoint` | `after_walk_step_5` | 1.0000 | 0.0000 | 1.0000 |

The late-checkpoint row should be described as an end-of-circuit support filter,
not as the best runtime assertion strategy.

---

## Metric Definitions

The quantum-walk evaluation uses final measurement-support validity as a
measurement-level proxy. A sampled final data state is support-valid if it
belongs to the ideal noiseless final support.

This is weaker than full state equivalence: two states can have the same
measurement support while differing in amplitudes or phases.

Confusion-matrix columns:

- `TP`: assertion reports an error and final data state is outside support.
- `TN`: assertion passes and final data state is inside support.
- `FP`: assertion reports an error but final data state is inside support.
- `FN`: assertion passes but final data state is outside support.
- `Detection Rate`: `TP / (TP + FN)`.
- `Support-Level FPR`: `FP / (FP + TN)`.
- `Post-selected Support-Valid Rate`: `TN / (TN + FN)`.

Static comparison metrics:

- `Coverage`: monitored vanishing states divided by total basis states.
- `Normalized Cost`: average of oracle-gate, added-depth, and added-CX ratios.
- `Benefit-Cost Score`: `Coverage / Normalized Cost`.

Coverage is static. Detection rate and false-positive rate come from noisy
Monte Carlo evaluation.

---

## Tests

```bash
python3 -m unittest discover
```

The tests cover assertion synthesis, oracle correctness, strategy selection,
quantum-walk evaluation, and shared-trace reproducibility.

---

## Scope and Limitations

- The implementation uses state-vector simulation rather than a BDD backend.
- Quantum-walk correctness is measured with final support validity, not full
  quantum-state equivalence.
- The current workflow focuses on single-point assertions.
- Vanishing-state enhancement circuits (`Uv`) are not implemented.
- ESOP-based synthesis from the original VanQiRA framework is approximated by
  the current oracle synthesis methods.
- Experiments use simulated Pauli noise rather than physical quantum hardware.
- The Simon experiment is a measurement-level validation baseline.

Possible extensions include state-fidelity evaluation, state-level TP/TN/FP/FN
metrics, partial-coverage experiments, Pareto-frontier analysis, multiple
assertion points, `Uv` circuits, BDD-based state representation, and device
experiments.

---

## Archive

`archive/` contains old demos, disabled entrypoints, and legacy outputs kept
for reference only. These files are not part of the current reproduction
workflow.

Archived experiment scripts:

```text
archive/experiments/run_qwalk_baseline.py
archive/experiments/run_qwalk_assertion.py
archive/experiments/run_simon_baseline.py
archive/experiments/run_simon_assertion.py
archive/experiments/plot_simon_results.py
archive/experiments/plot_checkpoint_tradeoff.py
```

Archived outputs:

```text
archive/results/qwalk_checkpoint_tradeoff.png
archive/results/raw/qwalk_overhead.csv
```
