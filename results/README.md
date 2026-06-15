# Results Index

This directory contains active generated outputs for the current workflow.
Legacy outputs that are not used by the current workflow live under
`archive/results/`.

## Active Raw CSV Files

| File | Purpose |
| --- | --- |
| `raw/simon_results.csv` | Simon baseline/asserted success, pass, and error-report rates. |
| `raw/simon_overhead.csv` | Simon baseline/asserted circuit overhead. |
| `raw/qwalk_results.csv` | Baseline quantum-walk checkpoint scan with sparsity and proxy scores. |
| `raw/qwalk_strategy_comparison.csv` | Static checkpoint/oracle cost-benefit comparison. |
| `raw/qwalk_strategy_winners.csv` | Six selected strategies used for noisy evaluation. |
| `raw/qwalk_strategy_evaluation_p0_0.csv` | p = 0 sanity check. |
| `raw/qwalk_strategy_evaluation_p0_005.csv` | Primary model at p = 0.005. |
| `raw/qwalk_strategy_evaluation_p0_01.csv` | Primary model at p = 0.01. |
| `raw/qwalk_strategy_evaluation_p0_02.csv` | Primary model at p = 0.02. |
| `raw/qwalk_strategy_evaluation_oracle_noise_p0_01.csv` | Optional p = 0.01 run where assertion-oracle gates also receive Pauli noise. |

## Active Figures

| File | Purpose |
| --- | --- |
| `qwalk_strategy_comparison.png` | Coverage-versus-normalized-cost scatter plot for checkpoint/oracle candidates. |

## Current Primary Table

The main table for the report is:

```text
results/raw/qwalk_strategy_evaluation_p0_01.csv
```

Use the oracle-noise table only as an extension:

```text
results/raw/qwalk_strategy_evaluation_oracle_noise_p0_01.csv
```

Old untagged evaluation files were removed from `results/raw/` so the active
directory only contains probability-tagged evaluation outputs.
