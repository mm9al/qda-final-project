# Results Index

This directory contains the active generated outputs for the current workflow.
Formal report outputs live in `results/raw/` and `results/`. Auxiliary sanity
checks and extensions live in `results/auxiliary/raw/`. Legacy outputs that are
not used by the current workflow live under `archive/results/`.

Generated cache directories such as `results/.matplotlib/` and
`results/.cache/` are ignored and are not project results.

## 中文簡介

這個資料夾是實驗輸出的索引：

- `results/raw/`：正式主報告使用的 CSV 表格。
- `results/`：正式主報告使用的圖檔。
- `results/auxiliary/raw/`：sanity check、noise sweep、oracle-noise extension
  等輔助實驗結果，不視為主報告表格。
- `archive/results/`：舊版或停用流程留下的結果，只保留作為參考。

如果只想看正式結果，優先閱讀 `results/raw/` 裡的 CSV 與本層的 PNG 圖檔。

## Fixed vs Scaling Outputs / 固定與變動條件

The fixed quantum-walk outputs come from one circuit setting:
`position_qubits=2`, one coin qubit, `total_qubits=3`, `basis_states=8`, and
`steps=5`. In these files, different rows mainly compare checkpoint choice,
oracle method, or selected strategy under the same quantum-walk size:

```text
raw/qwalk_results.csv
raw/qwalk_strategy_comparison.csv
raw/qwalk_strategy_winners.csv
raw/qwalk_strategy_evaluation_p0_01.csv
```

The scaling outputs contain many circuit settings. Read them with
`position_qubits`, `total_qubits`, `basis_states`, `steps`,
`checkpoint_step`, `label`, `oracle_method`, and `status`:

```text
raw/qwalk_benchmark_suite.csv
raw/qwalk_scaling_candidates.csv
raw/qwalk_scaling_strategy_winners.csv
```

中文提示：比較不同 checkpoint 時，是在同一個 circuit setting 下改 assertion
插入點；比較不同 `position_qubits` 或 `steps` 時，是換了 quantum walk 問題
規模。`qwalk_scaling_candidates.csv` 的每一列代表一個
`(position_qubits, steps, checkpoint, oracle_method)` candidate；
`qwalk_scaling_strategy_winners.csv` 則是每個 `(position_qubits, steps)` 都各自
選出 6 種策略。

## Main Report Results

These files are used directly for the main report tables or conclusions.

| File | Purpose |
| --- | --- |
| `raw/simon_results.csv` | Simon baseline/asserted results across noise levels. Read `baseline_success_rate`, `filtered_success_rate`, `pass_rate`, and `error_report_rate` to compare baseline behavior with assertion-filtered behavior. |
| `raw/simon_overhead.csv` | Simon baseline/asserted circuit overhead. Use this to report the added depth, CX, and gate cost of the assertion circuit. |
| `raw/qwalk_results.csv` | Quantum-walk checkpoint scan with sparsity and proxy scores. This is the first-pass view of which checkpoints expose many vanishing states. |
| `raw/qwalk_strategy_comparison.csv` | Static checkpoint/oracle cost-benefit comparison. Read `coverage`, `asserted_cx_overhead`, `normalized_cost`, and `benefit_cost_score` to compare assertion quality versus cost. |
| `raw/qwalk_strategy_winners.csv` | Six selected strategies used by the formal noisy evaluation. This file is the input strategy list for `run_qwalk_strategy_evaluation`. |
| `raw/qwalk_strategy_evaluation_p0_01.csv` | Main quantum-walk noisy Monte Carlo evaluation at `p = 0.01`. The key result columns are `Detection Rate`, `Support-Level FPR`, and `Post-selected Support-Valid Rate`. |
| `qwalk_strategy_comparison.png` | Coverage-versus-normalized-cost plot for checkpoint/oracle candidates. Use it as the visual summary of the static strategy trade-off. |

## Static Scaling-Suite Results

These are formal scaling benchmark outputs. They support the parameterized
quantum-walk analysis but are separate from the single-setting noisy evaluation
table above.

| File | Purpose |
| --- | --- |
| `raw/qwalk_benchmark_suite.csv` | Parameterized benchmark family summary. It lists the position-qubit sizes, total qubits, basis states, and walk steps included in the suite. |
| `raw/qwalk_scaling_candidates.csv` | Full scaling-suite checkpoint/oracle candidate table with synthesis status. Use it to inspect every candidate, including skipped large-minterm cases. |
| `raw/qwalk_scaling_strategy_winners.csv` | Six selected strategies for every scaling-suite `(position_qubits, steps)` setting. This is the scaling-suite counterpart of `qwalk_strategy_winners.csv`. |
| `qwalk_vanishing_ratio_by_checkpoint.png` | Vanishing-state ratio by checkpoint step and position-qubit size. Use it to see where assertions have more state-space coverage. |
| `qwalk_oracle_cost_vs_coverage.png` | Scaling-suite coverage versus added-CX trade-off with Pareto frontier. Use it to identify efficient assertion candidates. |
| `qwalk_strategy_ranking_across_scales.png` | Cross-scale strategy ranking from static winners; may include noisy metrics after an auxiliary scaling evaluation. Use it as the high-level scaling summary. |

The expected full static scaling-suite counts are:

```text
30 benchmark settings
420 candidate rows
336 successful candidates
84 skipped large-minterm candidates
180 strategy winners
```

## Key Columns

Common columns used across the result CSVs:

| Column | Meaning |
| --- | --- |
| `coverage` | Fraction of computational-basis states that are vanishing at the selected checkpoint. Higher values mean the assertion can reject a larger invalid-state region. |
| `asserted_cx_overhead` | Additional CX gates introduced by the assertion circuit compared with the baseline walk circuit. Lower values mean a cheaper assertion. |
| `normalized_cost` | Static cost proxy that combines oracle and asserted-circuit overhead into a normalized score. Lower values mean lower implementation cost. |
| `Detection Rate` | In noisy evaluation, the fraction of injected error cases correctly rejected by the assertion. Higher values mean stronger error detection. |
| `Support-Level FPR` | In noisy evaluation, the false-positive rate against outcomes that still land in the ideal final support. Lower values mean fewer support-valid outcomes are rejected. |
| `Post-selected Support-Valid Rate` | Fraction of accepted outputs that remain in the ideal final support after assertion filtering. Higher values mean cleaner accepted results. |

中文簡要解讀：`coverage` 代表 assertion 能檢查到多少 vanishing-state 區域；
`asserted_cx_overhead` 和 `normalized_cost` 代表成本；`Detection Rate` 代表錯誤
偵測能力；`Support-Level FPR` 代表誤報程度；`Post-selected Support-Valid Rate`
代表 assertion 篩選後留下的結果品質。

## Auxiliary Results

Auxiliary files are for sanity checks, probability sweeps, and extensions. They
are not main report tables unless the report explicitly says otherwise.

| File | Purpose |
| --- | --- |
| `auxiliary/raw/qwalk_strategy_evaluation_p0_0.csv` | Noiseless sanity check for the primary quantum-walk evaluator. |
| `auxiliary/raw/qwalk_strategy_evaluation_p0_005.csv` | Probability-sweep run for the primary quantum-walk noise model. |
| `auxiliary/raw/qwalk_strategy_evaluation_p0_02.csv` | Probability-sweep run for the primary quantum-walk noise model. |
| `auxiliary/raw/qwalk_strategy_evaluation_oracle_noise_p0_01.csv` | Extension where assertion-oracle gates also receive Pauli noise. |
| `auxiliary/raw/qwalk_scaling_strategy_evaluation_*.csv` | Representative noisy scaling smoke tests. |

If an auxiliary command writes to `results/raw/`, move the generated CSV into
`results/auxiliary/raw/` after the run so `results/raw/` remains reserved for
formal outputs.

## Archived Legacy Results

The `archive/results/` directory contains old demos and disabled workflow
outputs kept only for reference. These files are not required to reproduce the
current report outputs.
