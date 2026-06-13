# Quantum Walk Assertion Strategy Comparison

The original quantum-walk checkpoint optimization mostly followed the number of
vanishing states. Its balanced score subtracts a small proxy cost from sparsity,
but that proxy is still based on the number of explicit minterms rather than the
actual assertion circuit overhead.

The new comparison evaluates every checkpoint after a walk step with two oracle
synthesis methods:

- `minterm`: one explicit controlled term per vanishing basis state.
- `simplified_boolean`: an exact ESOP/ANF Boolean oracle that toggles the
  assertion ancilla with a simplified XOR-of-products representation.

All oracle and asserted-circuit costs are measured after transpilation to the
same basis gates. The generated files are:

- `results/raw/qwalk_strategy_comparison.csv`
- `results/raw/qwalk_strategy_winners.csv`
- `results/qwalk_strategy_comparison.png`

For the current setting (`num_position_qubits=2`, `num_steps=5`), the best
cost-benefit result is:

- Strategy: `cost_benefit`
- Checkpoint: `after_walk_step_2`
- Oracle: `simplified_boolean`
- Coverage: `0.5000`
- Oracle gate count: `1`
- Normalized cost: `0.0106`
- Benefit-cost score: `47.1492`

The highest-sparsity checkpoint remains `after_walk_step_4` with coverage
`0.8750`, but the selected oracle implementation should be the cheapest method
available at that checkpoint. This keeps checkpoint-only strategies from
implicitly preferring whichever oracle method appears first in the CSV.

The `late_checkpoint` strategy should be reported as
`late_checkpoint (end-of-circuit support-filtering baseline)`. It can achieve
perfect support-level filtering because it checks near the final support, but
it does not provide early-abort benefit and should not be described as the best
runtime assertion strategy.
