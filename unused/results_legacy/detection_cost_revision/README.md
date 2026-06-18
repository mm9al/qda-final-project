# Detection-Cost Revision Results

This folder contains the regenerated quantum-walk scaling results for the
detection/cost experiment revision.

Run settings:

- Static scaling scan: `position_qubits = 2,3,4,5,6`, `steps = 2,4,6,8,10,12`.
- Minterm synthesis skip threshold: `max_minterm_states = 32`.
- Noisy scaling evaluation: `position_qubits = 2,3,4,5`, `steps = 6,8,10`.
- Noise setting: `error_probability = 0.01`, `num_trials = 100`, `seed = 2026`.
- Oracle noise: disabled.

CSV outputs live in `raw/`.

- `qwalk_benchmark_suite.csv`: benchmark-family summary.
- `qwalk_scaling_candidates.csv`: every checkpoint/oracle candidate with
  static coverage, fault-sensitive detection proxy, and overhead metrics.
- `qwalk_checkpoint_landscape.csv`: deduplicated checkpoint landscape for the
  heatmap and checkpoint-structure discussion.
- `qwalk_scaling_strategy_winners.csv`: detection-oriented strategy winners.
- `qwalk_scaling_strategy_evaluation_p0_01.csv`: noisy detection evaluation.

Figure outputs live in `figures/`.

- `qwalk_vanishing_support_heatmap.png`: checkpoint-structure heatmap.
- `qwalk_coverage_vs_fault_sensitivity.png`: static coverage versus
  Pauli-fault-sensitive proxy.
- `qwalk_detection_vs_overhead.png`: main detection/cost trade-off figure.
- `qwalk_strategy_ranking_across_scales.png`: strategy summary across scales.
- `qwalk_oracle_cost_vs_coverage.png`: static oracle feasibility plot.
- `qwalk_vanishing_ratio_by_checkpoint.png`: legacy diagnostic line plot.
