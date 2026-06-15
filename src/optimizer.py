from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd
from qiskit import QuantumCircuit, transpile

from src.assertion import VanishingAssertionSpec, synthesize_vanishing_oracle
from src.utils import analyze_checkpoint
from src.utils import append_instruction_copy


@dataclass
class CheckpointCandidate:
    checkpoint: int
    label: str
    relative_position: float
    num_vanishing_states: int
    sparsity: float
    naive_oracle_terms: int
    overhead_ratio_proxy: float
    balanced_score: float


@dataclass
class StrategyComparisonCandidate:
    checkpoint: int
    label: str
    relative_position: float
    oracle_method: str
    total_states: int
    num_vanishing_states: int
    coverage: float
    sparsity: float
    balanced_score: float
    oracle_depth: int
    oracle_gate_count: int
    oracle_cx_count: int
    asserted_depth: int
    asserted_cx_count: int
    asserted_gate_count: int
    asserted_depth_overhead: int
    asserted_cx_overhead: int
    asserted_gate_overhead: int
    normalized_cost: float
    benefit_cost_score: float


DEFAULT_BASIS_GATES = ("x", "h", "sx", "rz", "cx")
DEFAULT_ORACLE_METHODS = ("minterm", "simplified_boolean")


def scan_checkpoints(
    circuit: QuantumCircuit,
    checkpoints: list[int],
    checkpoint_labels: list[str] | None = None,
    overhead_weight: float = 0.05,
) -> pd.DataFrame:
    """
    Analyze candidate assertion points.

    naive_oracle_terms is initially estimated as the number of monitored
    vanishing states. Later, replace it with the actual gate count produced
    by assertion.py.
    """
    if checkpoint_labels is None:
        checkpoint_labels = [
            f"checkpoint_{checkpoint}"
            for checkpoint in checkpoints
        ]

    if len(checkpoints) != len(checkpoint_labels):
        raise ValueError("checkpoints and labels must have the same length.")

    candidates: list[CheckpointCandidate] = []

    for checkpoint, label in zip(checkpoints, checkpoint_labels):
        analysis = analyze_checkpoint(
            circuit=circuit,
            checkpoint=checkpoint,
        )

        naive_oracle_terms = len(analysis.vanishing_states)

        overhead_ratio_proxy = (
            naive_oracle_terms / max(len(circuit.data), 1)
        )

        balanced_score = (
            analysis.sparsity
            - overhead_weight * overhead_ratio_proxy
        )

        candidate = CheckpointCandidate(
            checkpoint=checkpoint,
            label=label,
            relative_position=checkpoint / len(circuit.data),
            num_vanishing_states=len(analysis.vanishing_states),
            sparsity=analysis.sparsity,
            naive_oracle_terms=naive_oracle_terms,
            overhead_ratio_proxy=overhead_ratio_proxy,
            balanced_score=balanced_score,
        )

        candidates.append(candidate)

    return pd.DataFrame(
        [asdict(candidate) for candidate in candidates]
    )


def _gate_count(circuit: QuantumCircuit) -> int:
    ignored_ops = {"barrier", "measure"}
    return sum(
        count
        for name, count in circuit.count_ops().items()
        if name not in ignored_ops
    )


def _transpiled_metrics(
    circuit: QuantumCircuit,
    basis_gates: tuple[str, ...] = DEFAULT_BASIS_GATES,
) -> dict[str, int]:
    transpiled = transpile(
        circuit,
        basis_gates=list(basis_gates),
        optimization_level=1,
        seed_transpiler=2026,
    )
    counts = transpiled.count_ops()

    return {
        "depth": transpiled.depth(),
        "cx_count": counts.get("cx", 0),
        "gate_count": _gate_count(transpiled),
    }


def build_asserted_checkpoint_circuit(
    circuit: QuantumCircuit,
    checkpoint: int,
    oracle: QuantumCircuit,
) -> QuantumCircuit:
    """Insert an assertion oracle at a checkpoint without measurements."""
    if checkpoint < 0 or checkpoint > len(circuit.data):
        raise ValueError("Invalid checkpoint.")

    assertion_ancilla = circuit.num_qubits
    asserted = QuantumCircuit(
        circuit.num_qubits + 1,
        name="qwalk_asserted_checkpoint",
    )

    for instruction in circuit.data[:checkpoint]:
        append_instruction_copy(
            target=asserted,
            source=circuit,
            instruction=instruction,
        )

    asserted.barrier()
    asserted.compose(
        oracle,
        qubits=list(range(circuit.num_qubits)) + [assertion_ancilla],
        inplace=True,
    )
    asserted.barrier()

    for instruction in circuit.data[checkpoint:]:
        append_instruction_copy(
            target=asserted,
            source=circuit,
            instruction=instruction,
        )

    return asserted


def _normalized_cost(
    oracle_metrics: dict[str, int],
    baseline_metrics: dict[str, int],
    asserted_metrics: dict[str, int],
) -> float:
    baseline_depth = max(baseline_metrics["depth"], 1)
    baseline_cx = max(baseline_metrics["cx_count"], 1)
    baseline_gate_count = max(baseline_metrics["gate_count"], 1)

    depth_overhead = max(
        asserted_metrics["depth"] - baseline_metrics["depth"],
        0,
    )
    cx_overhead = max(
        asserted_metrics["cx_count"] - baseline_metrics["cx_count"],
        0,
    )

    return (
        oracle_metrics["gate_count"] / baseline_gate_count
        + depth_overhead / baseline_depth
        + cx_overhead / baseline_cx
    ) / 3.0


def scan_checkpoint_strategy_comparison(
    circuit: QuantumCircuit,
    checkpoints: list[int],
    checkpoint_labels: list[str] | None = None,
    oracle_methods: tuple[str, ...] = DEFAULT_ORACLE_METHODS,
    overhead_weight: float = 0.05,
    basis_gates: tuple[str, ...] = DEFAULT_BASIS_GATES,
) -> pd.DataFrame:
    """Analyze every checkpoint and oracle synthesis method with real costs."""
    if checkpoint_labels is None:
        checkpoint_labels = [
            f"checkpoint_{checkpoint}"
            for checkpoint in checkpoints
        ]

    if len(checkpoints) != len(checkpoint_labels):
        raise ValueError("checkpoints and labels must have the same length.")

    baseline_metrics = _transpiled_metrics(
        circuit=circuit,
        basis_gates=basis_gates,
    )
    baseline_depth = baseline_metrics["depth"]
    baseline_cx = baseline_metrics["cx_count"]
    baseline_gate_count = baseline_metrics["gate_count"]

    candidates: list[StrategyComparisonCandidate] = []

    for checkpoint, label in zip(checkpoints, checkpoint_labels):
        analysis = analyze_checkpoint(
            circuit=circuit,
            checkpoint=checkpoint,
        )
        total_states = (
            len(analysis.vanishing_states)
            + len(analysis.non_vanishing_states)
        )
        coverage = len(analysis.vanishing_states) / max(total_states, 1)
        balanced_score = (
            analysis.sparsity
            - overhead_weight
            * (len(analysis.vanishing_states) / max(len(circuit.data), 1))
        )

        spec = VanishingAssertionSpec(
            num_asserted_qubits=circuit.num_qubits,
            vanishing_states=tuple(analysis.vanishing_states),
            description=label,
        )

        for oracle_method in oracle_methods:
            oracle = synthesize_vanishing_oracle(
                spec=spec,
                method=oracle_method,
            )
            asserted = build_asserted_checkpoint_circuit(
                circuit=circuit,
                checkpoint=checkpoint,
                oracle=oracle,
            )

            oracle_metrics = _transpiled_metrics(
                circuit=oracle,
                basis_gates=basis_gates,
            )
            asserted_metrics = _transpiled_metrics(
                circuit=asserted,
                basis_gates=basis_gates,
            )

            depth_overhead = asserted_metrics["depth"] - baseline_depth
            cx_overhead = asserted_metrics["cx_count"] - baseline_cx
            gate_overhead = asserted_metrics["gate_count"] - baseline_gate_count
            normalized_cost = _normalized_cost(
                oracle_metrics=oracle_metrics,
                baseline_metrics=baseline_metrics,
                asserted_metrics=asserted_metrics,
            )
            benefit_cost_score = coverage / max(normalized_cost, 1e-12)

            candidates.append(
                StrategyComparisonCandidate(
                    checkpoint=checkpoint,
                    label=label,
                    relative_position=checkpoint / len(circuit.data),
                    oracle_method=oracle_method,
                    total_states=total_states,
                    num_vanishing_states=len(analysis.vanishing_states),
                    coverage=coverage,
                    sparsity=analysis.sparsity,
                    balanced_score=balanced_score,
                    oracle_depth=oracle_metrics["depth"],
                    oracle_gate_count=oracle_metrics["gate_count"],
                    oracle_cx_count=oracle_metrics["cx_count"],
                    asserted_depth=asserted_metrics["depth"],
                    asserted_cx_count=asserted_metrics["cx_count"],
                    asserted_gate_count=asserted_metrics["gate_count"],
                    asserted_depth_overhead=depth_overhead,
                    asserted_cx_overhead=cx_overhead,
                    asserted_gate_overhead=gate_overhead,
                    normalized_cost=normalized_cost,
                    benefit_cost_score=benefit_cost_score,
                )
            )

    return pd.DataFrame(
        [asdict(candidate) for candidate in candidates]
    )


def _pick_cheapest_method_at_checkpoint(
    checkpoint_results: pd.DataFrame,
    checkpoint: int,
) -> pd.Series:
    """
    Among oracle implementations at the same checkpoint,
    select the implementation with the lowest oracle gate count.
    """
    rows = checkpoint_results[
        checkpoint_results["checkpoint"] == checkpoint
    ]

    if rows.empty:
        raise ValueError(f"No candidate found for checkpoint {checkpoint}.")

    # Legacy checkpoint scan does not contain synthesized oracle costs.
    if "oracle_gate_count" not in rows.columns:
        return rows.iloc[0]

    index = rows["oracle_gate_count"].idxmin()
    return rows.loc[index]


def select_best_checkpoint(
    checkpoint_results: pd.DataFrame,
    strategy: str = "balanced",
) -> pd.Series:
    """
    Select a checkpoint candidate according to the requested strategy.

    For checkpoint-only strategies, the checkpoint is selected first.
    If multiple oracle methods exist at that checkpoint, the cheapest
    synthesized oracle implementation is selected.
    """
    if checkpoint_results.empty:
        raise ValueError("checkpoint_results must not be empty.")

    valid_results = checkpoint_results[
        checkpoint_results["num_vanishing_states"] > 0
    ]

    if valid_results.empty:
        raise ValueError("No assertable checkpoint found.")

    if strategy == "max_sparsity":
        checkpoint = valid_results.loc[
            valid_results["sparsity"].idxmax(),
            "checkpoint",
        ]
        return _pick_cheapest_method_at_checkpoint(
            checkpoint_results=valid_results,
            checkpoint=checkpoint,
        )

    if strategy == "min_overhead":
        index = valid_results["naive_oracle_terms"].idxmin()
        return valid_results.loc[index]

    if strategy == "min_oracle_cost":
        index = valid_results["oracle_gate_count"].idxmin()
        return valid_results.loc[index]

    if strategy in {"balanced", "balanced_proxy"}:
        checkpoint = valid_results.loc[
            valid_results["balanced_score"].idxmax(),
            "checkpoint",
        ]
        return _pick_cheapest_method_at_checkpoint(
            checkpoint_results=valid_results,
            checkpoint=checkpoint,
        )

    if strategy == "cost_benefit":
        index = valid_results["benefit_cost_score"].idxmax()
        return valid_results.loc[index]

    if strategy == "early_checkpoint":
        checkpoint = valid_results["checkpoint"].min()
        return _pick_cheapest_method_at_checkpoint(
            checkpoint_results=valid_results,
            checkpoint=checkpoint,
        )

    if strategy == "late_checkpoint":
        checkpoint = valid_results["checkpoint"].max()
        return _pick_cheapest_method_at_checkpoint(
            checkpoint_results=valid_results,
            checkpoint=checkpoint,
        )

    raise ValueError(f"Unsupported strategy: {strategy}")


def select_strategy_winners(
    checkpoint_results: pd.DataFrame,
    strategies: tuple[str, ...] = (
        "max_sparsity",
        "min_oracle_cost",
        "balanced_proxy",
        "cost_benefit",
        "early_checkpoint",
        "late_checkpoint",
    ),
) -> pd.DataFrame:
    """Return one selected row per strategy."""
    rows = []

    for strategy in strategies:
        row = select_best_checkpoint(
            checkpoint_results=checkpoint_results,
            strategy=strategy,
        ).copy()
        row["strategy"] = strategy
        rows.append(row)

    return pd.DataFrame(rows)
