# VanQiRA-Style Simon and Quantum-Walk Experiments

This repository is a compact reproducibility prototype for quantum runtime
assertion experiments. It focuses on two active targets:

- Simon's algorithm with measurement-level parity validation.
- A coined quantum walk with checkpoint-based vanishing-state assertion
  oracles.

The quantum-walk workflow scans assertion checkpoints, synthesizes assertion
oracles, compares static circuit costs, selects representative strategies, and
evaluates those strategies under shared Pauli-noise traces. This is not the
full BDD-based VanQiRA framework; it is a small project artifact organized for
repeatable experiments and report-ready outputs.

## 中文簡介

本專案是一個小型、可重現的量子執行期 assertion 實驗原型，主要用來比較
Simon 演算法與 coined quantum walk 在加入 assertion 後的效果與成本。

目前正式流程會先執行測試，再產生報告用結果。主要輸出放在
`results/raw/` 與 `results/`；sanity check、noise sweep、oracle-noise
extension 等輔助實驗結果則放在 `results/auxiliary/raw/`，不視為主報告表格。

若只想重跑專案，照著下方 **Setup** 和 **Canonical Reproduction Workflow**
執行即可。各結果檔案的用途請看 `results/README.md`。

## Quick Start / 快速重跑

最短流程是先建立 Python 環境，跑測試確認程式狀態，再依序產生正式結果：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 -m unittest discover
python3 -m experiments.run_simon
python3 -m experiments.run_checkpoint_optimization
python3 -m experiments.run_qwalk_strategy_comparison
python3 -m experiments.run_qwalk_scaling
python3 -m experiments.run_qwalk_strategy_evaluation \
  --error-probability 0.01 \
  --num-trials 1000 \
  --seed 2026
```

上述流程會把正式 CSV 寫到 `results/raw/`，把正式圖檔寫到 `results/`。
最後可用 `results/README.md` 對照每個檔案的用途與主要欄位。

## Project Layout

```text
QDA-FINAL-PROJECT/
├── archive/       legacy scripts and old outputs kept for reference
├── experiments/   active command-line experiment entrypoints
├── report/        notes and write-up material
├── results/       formal figures, CSV outputs, and auxiliary runs
├── src/           circuit builders, assertion synthesis, evaluation utilities
├── tests/         unit tests
├── help.py        command-line workflow summary
└── requirements.txt
```

Detailed output tiers are documented in `results/README.md`.

## Setup

Use `python3`; the local environment does not provide `python`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Canonical Reproduction Workflow

Run tests before generating the formal outputs. The commands should be run from
the project root in this order:

| Step | Command | Effect / 指令效果 | Main outputs |
| --- | --- | --- | --- |
| 1 | `python3 -m unittest discover` | Runs unit tests for core circuit, assertion, and strategy-selection logic. 先確認核心邏輯與策略選擇測試通過。 | No result files; pass/fail only. |
| 2 | `python3 -m experiments.run_simon` | Runs Simon baseline and asserted circuits across several noise levels. 產生 Simon 成功率、pass rate、error-report rate 與 circuit overhead。 | `results/raw/simon_results.csv`, `results/raw/simon_overhead.csv` |
| 3 | `python3 -m experiments.run_checkpoint_optimization` | Scans quantum-walk checkpoints and computes sparsity/proxy scores. 掃描每個 checkpoint 的 vanishing-state coverage。 | `results/raw/qwalk_results.csv` |
| 4 | `python3 -m experiments.run_qwalk_strategy_comparison` | Compares checkpoint/oracle choices, selects six representative strategies, and plots cost versus coverage. 比較成本效益並選出正式 noisy evaluation 使用的 6 種策略。 | `results/raw/qwalk_strategy_comparison.csv`, `results/raw/qwalk_strategy_winners.csv`, `results/qwalk_strategy_comparison.png` |
| 5 | `python3 -m experiments.run_qwalk_scaling` | Runs the parameterized scaling suite across position-qubit sizes and walk steps. 產生不同規模下的 candidate、winner 與 scaling 圖。 | `results/raw/qwalk_benchmark_suite.csv`, `results/raw/qwalk_scaling_candidates.csv`, `results/raw/qwalk_scaling_strategy_winners.csv`, scaling figures in `results/` |
| 6 | `python3 -m experiments.run_qwalk_strategy_evaluation --error-probability 0.01 --num-trials 1000 --seed 2026` | Evaluates selected quantum-walk strategies under shared Pauli-noise traces. 用相同 noise traces 做正式 noisy Monte Carlo 評估。 | `results/raw/qwalk_strategy_evaluation_p0_01.csv` |

The full command for step 6 is:

```bash
python3 -m experiments.run_qwalk_strategy_evaluation \
  --error-probability 0.01 \
  --num-trials 1000 \
  --seed 2026
```

The canonical workflow writes formal report outputs to `results/raw/` and
figures to `results/`.

## How to Read the Results / 結果怎麼看

- Simon results: start with `baseline_success_rate`,
  `filtered_success_rate`, `pass_rate`, and `error_report_rate` in
  `results/raw/simon_results.csv`. These show how often the baseline succeeds,
  how assertion post-selection changes the accepted success rate, and how often
  the assertion reports an error.
- Quantum-walk strategy comparison: use `coverage`, `asserted_cx_overhead`,
  `normalized_cost`, and `benefit_cost_score` in
  `results/raw/qwalk_strategy_comparison.csv` and
  `results/raw/qwalk_strategy_winners.csv`. Higher coverage means more
  vanishing states are checked; lower CX overhead and normalized cost mean the
  assertion is cheaper.
- Noisy quantum-walk evaluation: use `Detection Rate`, `Support-Level FPR`, and
  `Post-selected Support-Valid Rate` in
  `results/raw/qwalk_strategy_evaluation_p0_01.csv`. These summarize how well a
  selected assertion catches injected errors, how often it rejects support-valid
  outcomes, and how clean the accepted outputs are.
- Scaling suite: use the three scaling CSVs and figures to compare behavior as
  position qubits and walk steps grow. The plots summarize vanishing-state
  ratio by checkpoint, oracle cost versus coverage, and strategy ranking across
  scales.

Simon 表格主要看 assertion 是否提高通過後的成功率，以及錯誤回報
比例是否合理；quantum walk 表格主要看 assertion coverage 與額外 CX 成本之間的
取捨；noisy evaluation 表格主要看偵測率、誤報率與 post-selected 結果品質；
scaling suite 則用來說明這些策略在不同 problem size 下是否仍有一致趨勢。

## Formal Outputs

Main report CSVs:

```text
results/raw/simon_results.csv
results/raw/simon_overhead.csv
results/raw/qwalk_results.csv
results/raw/qwalk_strategy_comparison.csv
results/raw/qwalk_strategy_winners.csv
results/raw/qwalk_strategy_evaluation_p0_01.csv
```

Static scaling-suite CSVs:

```text
results/raw/qwalk_benchmark_suite.csv
results/raw/qwalk_scaling_candidates.csv
results/raw/qwalk_scaling_strategy_winners.csv
```

Formal figures:

```text
results/qwalk_strategy_comparison.png
results/qwalk_vanishing_ratio_by_checkpoint.png
results/qwalk_oracle_cost_vs_coverage.png
results/qwalk_strategy_ranking_across_scales.png
```

## Optional Auxiliary Runs

These commands are useful for sanity checks and extensions, but their CSVs are
not main report tables.

以下指令只用來做 sanity check、noise probability sweep 或延伸實驗，
不屬於正式主報告表格。若這些指令把 CSV 寫到 `results/raw/`，請在完成後移到
`results/auxiliary/raw/`，讓 `results/raw/` 保持只放正式輸出。

Noiseless sanity check:

```bash
python3 -m experiments.run_qwalk_strategy_evaluation \
  --error-probability 0 \
  --num-trials 100 \
  --seed 2026
```

Oracle-noise extension:

```bash
python3 -m experiments.run_qwalk_strategy_evaluation \
  --include-oracle-noise \
  --error-probability 0.01 \
  --num-trials 1000 \
  --seed 2026
```

Representative noisy scaling smoke test:

```bash
python3 -m experiments.run_qwalk_scaling_evaluation \
  --error-probability 0.01 \
  --num-trials 100 \
  --seed 2026
```

After running auxiliary commands, move their CSV outputs from `results/raw/` to
`results/auxiliary/raw/`. Auxiliary outputs include:

```text
qwalk_strategy_evaluation_p0_0.csv
qwalk_strategy_evaluation_p0_005.csv
qwalk_strategy_evaluation_p0_02.csv
qwalk_strategy_evaluation_oracle_noise_p0_01.csv
qwalk_scaling_strategy_evaluation_*.csv
```

## Help Commands

The root helper prints the workflow and output index:

```bash
python3 help.py
python3 help.py --outputs
python3 help.py --archive
```

## Verification

Use this check before relying on regenerated outputs:

```bash
python3 -m unittest discover
python3 -m py_compile src/*.py experiments/*.py help.py
```

The full static scaling suite should produce:

```text
30 benchmark settings
420 candidate rows
336 successful candidates
84 skipped large-minterm candidates
180 strategy winners
```
