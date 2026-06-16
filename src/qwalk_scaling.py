"""Parameterized quantum-walk benchmark suite utilities."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Iterable

import pandas as pd

from src.assertion import VanishingAssertionSpec, synthesize_vanishing_oracle
from src.evaluate import (
    evaluate_qwalk_strategy,
    generate_pauli_error_traces,
    ideal_final_support,
)
from src.optimizer import (
    DEFAULT_BASIS_GATES,
    DEFAULT_ORACLE_METHODS,
    build_asserted_checkpoint_circuit,
    select_strategy_winners,
)
from src.optimizer import _gate_count, _metric_overhead, _normalized_cost
from src.quantum_walk import build_cycle_quantum_walk
from src.utils import analyze_checkpoint


DEFAULT_POSITION_QUBITS = (2, 3, 4, 5, 6)
DEFAULT_WALK_STEPS = (2, 4, 6, 8, 10, 12)
DEFAULT_EVALUATION_POSITION_QUBITS = (2, 3, 4, 5)
DEFAULT_EVALUATION_WALK_STEPS = (6, 8, 10)
DEFAULT_NOISE_PROBABILITIES = (0.005, 0.01, 0.02)
DEFAULT_STRATEGIES = (
    "max_sparsity",
    "min_oracle_cost",
    "balanced_proxy",
    "cost_benefit",
    "early_checkpoint",
    "late_checkpoint",
)


@dataclass(frozen=True)
class BenchmarkSetting:
    position_qubits: int
    steps: int

    @property
    def total_qubits(self) -> int:
        return self.position_qubits + 1

    @property
    def basis_states(self) -> int:
        return 2 ** self.total_qubits


def benchmark_settings(
    position_qubits: Iterable[int] = DEFAULT_POSITION_QUBITS,
    walk_steps: Iterable[int] = DEFAULT_WALK_STEPS,
) -> list[BenchmarkSetting]:
    return [
        BenchmarkSetting(position_qubits=position_qubit, steps=steps)
        for position_qubit in position_qubits
        for steps in walk_steps
    ]


def benchmark_suite_table(
    position_qubits: Iterable[int] = DEFAULT_POSITION_QUBITS,
    walk_steps: Iterable[int] = DEFAULT_WALK_STEPS,
) -> pd.DataFrame:
    steps = tuple(walk_steps)
    return pd.DataFrame(
        [
            {
                "position_qubits": position_qubit,
                "total_qubits": position_qubit + 1,
                "basis_states": 2 ** (position_qubit + 1),
                "steps_tested": ",".join(str(step) for step in steps),
                "checkpoints": "all",
            }
            for position_qubit in position_qubits
        ]
    )


def _transpiled_metrics(circuit, basis_gates: tuple[str, ...]) -> dict[str, int]:
    from qiskit import transpile

    transpiled = transpile(
        circuit,
        basis_gates=list(basis_gates),
        optimization_level=1,
        seed_transpiler=2026,
    )
    counts = transpiled.count_ops()
    return {
        "depth": transpiled.depth(),
        "cx_count": int(counts.get("cx", 0)),
        "gate_count": _gate_count(transpiled),
    }


def _empty_candidate_row(
    *,
    setting: BenchmarkSetting,
    checkpoint: int,
    checkpoint_step: int,
    label: str,
    relative_position: float,
    oracle_method: str,
    total_states: int,
    num_vanishing_states: int,
    coverage: float,
    sparsity: float,
    balanced_score: float,
    status: str,
    error_message: str = "",
) -> dict[str, int | float | str | None]:
    return {
        "position_qubits": setting.position_qubits,
        "total_qubits": setting.total_qubits,
        "basis_states": setting.basis_states,
        "steps": setting.steps,
        "checkpoint_step": checkpoint_step,
        "checkpoint": checkpoint,
        "label": label,
        "relative_position": relative_position,
        "oracle_method": oracle_method,
        "total_states": total_states,
        "num_vanishing_states": num_vanishing_states,
        "coverage": coverage,
        "sparsity": sparsity,
        "balanced_score": balanced_score,
        "oracle_depth": None,
        "oracle_gate_count": None,
        "oracle_cx_count": None,
        "asserted_depth": None,
        "asserted_cx_count": None,
        "asserted_gate_count": None,
        "asserted_depth_overhead": None,
        "asserted_cx_overhead": None,
        "asserted_gate_overhead": None,
        "normalized_cost": None,
        "benefit_cost_score": None,
        "runtime_seconds": None,
        "status": status,
        "error_message": error_message,
    }


def scan_scaling_candidates(
    position_qubits: Iterable[int] = DEFAULT_POSITION_QUBITS,
    walk_steps: Iterable[int] = DEFAULT_WALK_STEPS,
    oracle_methods: tuple[str, ...] = DEFAULT_ORACLE_METHODS,
    overhead_weight: float = 0.05,
    basis_gates: tuple[str, ...] = DEFAULT_BASIS_GATES,
    max_minterm_states: int = 32,
    progress: bool = False,
) -> pd.DataFrame:
    """Scan every benchmark setting, checkpoint, and oracle method.

    Large explicit minterm oracles can dominate runtime.  When the number of
    monitored vanishing states exceeds ``max_minterm_states``, the row is kept
    with ``status=skipped_too_many_minterms`` so the benchmark table remains
    complete without silently omitting hard cases.
    """

    rows: list[dict[str, int | float | str | None]] = []

    for setting in benchmark_settings(position_qubits, walk_steps):
        if progress:
            print(
                "Scanning "
                f"p={setting.position_qubits}, T={setting.steps} "
                f"({setting.basis_states} basis states)",
                flush=True,
            )

        quantum_walk = build_cycle_quantum_walk(
            num_position_qubits=setting.position_qubits,
            num_steps=setting.steps,
        )
        circuit = quantum_walk.circuit
        baseline_metrics = _transpiled_metrics(circuit, basis_gates)

        for checkpoint_step, (checkpoint, label) in enumerate(
            zip(quantum_walk.checkpoints, quantum_walk.checkpoint_labels),
            start=1,
        ):
            if progress:
                print(f"  {label}", flush=True)

            analysis = analyze_checkpoint(circuit=circuit, checkpoint=checkpoint)
            total_states = len(analysis.vanishing_states) + len(
                analysis.non_vanishing_states
            )
            num_vanishing_states = len(analysis.vanishing_states)
            coverage = num_vanishing_states / max(total_states, 1)
            balanced_score = (
                analysis.sparsity
                - overhead_weight
                * (num_vanishing_states / max(len(circuit.data), 1))
            )
            relative_position = checkpoint / len(circuit.data)
            spec = VanishingAssertionSpec(
                num_asserted_qubits=circuit.num_qubits,
                vanishing_states=tuple(analysis.vanishing_states),
                description=label,
            )

            for oracle_method in oracle_methods:
                row = _empty_candidate_row(
                    setting=setting,
                    checkpoint=checkpoint,
                    checkpoint_step=checkpoint_step,
                    label=label,
                    relative_position=relative_position,
                    oracle_method=oracle_method,
                    total_states=total_states,
                    num_vanishing_states=num_vanishing_states,
                    coverage=coverage,
                    sparsity=analysis.sparsity,
                    balanced_score=balanced_score,
                    status="ok",
                )

                if (
                    oracle_method == "minterm"
                    and num_vanishing_states > max_minterm_states
                ):
                    row["status"] = "skipped_too_many_minterms"
                    row["error_message"] = (
                        f"{num_vanishing_states} vanishing states exceeds "
                        f"max_minterm_states={max_minterm_states}"
                    )
                    rows.append(row)
                    continue

                start_time = perf_counter()
                try:
                    oracle = synthesize_vanishing_oracle(
                        spec=spec,
                        method=oracle_method,
                    )
                    asserted = build_asserted_checkpoint_circuit(
                        circuit=circuit,
                        checkpoint=checkpoint,
                        oracle=oracle,
                    )
                    oracle_metrics = _transpiled_metrics(oracle, basis_gates)
                    asserted_metrics = _transpiled_metrics(asserted, basis_gates)
                    normalized_cost = _normalized_cost(
                        oracle_metrics=oracle_metrics,
                        baseline_metrics=baseline_metrics,
                        asserted_metrics=asserted_metrics,
                    )

                    row.update(
                        {
                            "oracle_depth": oracle_metrics["depth"],
                            "oracle_gate_count": oracle_metrics["gate_count"],
                            "oracle_cx_count": oracle_metrics["cx_count"],
                            "asserted_depth": asserted_metrics["depth"],
                            "asserted_cx_count": asserted_metrics["cx_count"],
                            "asserted_gate_count": asserted_metrics["gate_count"],
                            "asserted_depth_overhead": _metric_overhead(
                                asserted_metrics=asserted_metrics,
                                baseline_metrics=baseline_metrics,
                                metric="depth",
                            ),
                            "asserted_cx_overhead": _metric_overhead(
                                asserted_metrics=asserted_metrics,
                                baseline_metrics=baseline_metrics,
                                metric="cx_count",
                            ),
                            "asserted_gate_overhead": _metric_overhead(
                                asserted_metrics=asserted_metrics,
                                baseline_metrics=baseline_metrics,
                                metric="gate_count",
                            ),
                            "normalized_cost": normalized_cost,
                            "benefit_cost_score": coverage
                            / max(normalized_cost, 1e-12),
                            "runtime_seconds": perf_counter() - start_time,
                        }
                    )
                except Exception as exc:  # pragma: no cover - depends on qiskit internals
                    row["status"] = "error"
                    row["error_message"] = f"{type(exc).__name__}: {exc}"
                    row["runtime_seconds"] = perf_counter() - start_time

                rows.append(row)

    return pd.DataFrame(rows)


def ok_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    return candidates[candidates["status"] == "ok"].copy()


def pareto_frontier(
    candidates: pd.DataFrame,
    *,
    coverage_column: str = "coverage",
    cost_column: str = "asserted_cx_overhead",
) -> pd.DataFrame:
    """Return candidates not dominated by higher coverage and lower cost."""

    valid = candidates.dropna(subset=[coverage_column, cost_column]).copy()
    valid = valid[valid["status"] == "ok"] if "status" in valid.columns else valid
    frontier_indices: list[int] = []

    for index, row in valid.iterrows():
        dominated = (
            (valid[coverage_column] >= row[coverage_column])
            & (valid[cost_column] <= row[cost_column])
            & (
                (valid[coverage_column] > row[coverage_column])
                | (valid[cost_column] < row[cost_column])
            )
        ).any()
        if not dominated:
            frontier_indices.append(index)

    return valid.loc[frontier_indices].sort_values(
        [coverage_column, cost_column],
        ascending=[True, True],
    )


def select_scaling_strategy_winners(
    candidates: pd.DataFrame,
    strategies: tuple[str, ...] = DEFAULT_STRATEGIES,
) -> pd.DataFrame:
    rows = []
    valid = ok_candidates(candidates)
    valid = valid[valid["num_vanishing_states"] > 0]

    for (position_qubits, steps), group in valid.groupby(
        ["position_qubits", "steps"],
        sort=True,
    ):
        winners = select_strategy_winners(group, strategies=strategies)
        winners["position_qubits"] = position_qubits
        winners["total_qubits"] = int(group["total_qubits"].iloc[0])
        winners["basis_states"] = int(group["basis_states"].iloc[0])
        winners["steps"] = steps
        rows.append(winners)

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True)


def _candidate_seed(
    seed: int,
    position_qubits: int,
    steps: int,
    checkpoint: int,
    oracle_method: str,
    offset: int,
) -> int:
    method_value = sum(
        (index + 1) * ord(character)
        for index, character in enumerate(oracle_method)
    )
    return (
        seed
        + offset
        + position_qubits * 1_000_003
        + steps * 10_007
        + checkpoint * 1009
        + method_value
    )


def evaluate_scaling_strategy_winners(
    winners: pd.DataFrame,
    *,
    position_qubits: Iterable[int] = DEFAULT_EVALUATION_POSITION_QUBITS,
    walk_steps: Iterable[int] = DEFAULT_EVALUATION_WALK_STEPS,
    error_probability: float = 0.01,
    num_trials: int = 100,
    seed: int = 2026,
    include_oracle_noise: bool = False,
    progress: bool = False,
) -> pd.DataFrame:
    """Evaluate selected strategy winners on a representative noisy subset."""

    allowed_p = set(position_qubits)
    allowed_steps = set(walk_steps)
    subset = winners[
        winners["position_qubits"].isin(allowed_p)
        & winners["steps"].isin(allowed_steps)
    ].copy()

    rows: list[dict[str, int | float | str]] = []

    for (position_qubit, steps), group in subset.groupby(
        ["position_qubits", "steps"],
        sort=True,
    ):
        if progress:
            print(
                f"Evaluating p={position_qubit}, T={steps}, "
                f"strategies={len(group)}, trials={num_trials}",
                flush=True,
            )

        quantum_walk = build_cycle_quantum_walk(
            num_position_qubits=int(position_qubit),
            num_steps=int(steps),
        )
        circuit = quantum_walk.circuit
        support = ideal_final_support(circuit)
        traces = generate_pauli_error_traces(
            circuit=circuit,
            num_traces=num_trials,
            error_probability=error_probability,
            seed=_candidate_seed(
                seed=seed,
                position_qubits=int(position_qubit),
                steps=int(steps),
                checkpoint=0,
                oracle_method="shared",
                offset=17,
            ),
        )

        metric_cache: dict[tuple[int, str], dict[str, float | int]] = {}
        unique_candidates = group.drop_duplicates(
            subset=["checkpoint", "oracle_method"],
            keep="first",
        )

        for _, candidate in unique_candidates.iterrows():
            checkpoint = int(candidate["checkpoint"])
            oracle_method = str(candidate["oracle_method"])
            if progress:
                print(
                    "  candidate "
                    f"{candidate['label']} / {oracle_method}",
                    flush=True,
                )

            analysis = analyze_checkpoint(circuit=circuit, checkpoint=checkpoint)
            spec = VanishingAssertionSpec(
                num_asserted_qubits=circuit.num_qubits,
                vanishing_states=tuple(analysis.vanishing_states),
                description=str(candidate["label"]),
            )
            oracle = synthesize_vanishing_oracle(spec=spec, method=oracle_method)

            oracle_traces = None
            if include_oracle_noise:
                oracle_traces = generate_pauli_error_traces(
                    circuit=oracle,
                    num_traces=num_trials,
                    error_probability=error_probability,
                    seed=_candidate_seed(
                        seed=seed,
                        position_qubits=int(position_qubit),
                        steps=int(steps),
                        checkpoint=checkpoint,
                        oracle_method=oracle_method,
                        offset=1009,
                    ),
                )

            metric_cache[(checkpoint, oracle_method)] = evaluate_qwalk_strategy(
                circuit=circuit,
                checkpoint=checkpoint,
                oracle=oracle,
                traces=traces,
                final_support=support,
                seed=_candidate_seed(
                    seed=seed,
                    position_qubits=int(position_qubit),
                    steps=int(steps),
                    checkpoint=checkpoint,
                    oracle_method=oracle_method,
                    offset=4096,
                ),
                oracle_traces=oracle_traces,
            )

        for _, winner in group.iterrows():
            checkpoint = int(winner["checkpoint"])
            oracle_method = str(winner["oracle_method"])
            metrics = metric_cache[(checkpoint, oracle_method)]
            rows.append(
                {
                    "position_qubits": int(position_qubit),
                    "total_qubits": int(winner["total_qubits"]),
                    "basis_states": int(winner["basis_states"]),
                    "steps": int(steps),
                    "strategy": str(winner["strategy"]),
                    "checkpoint_step": int(winner["checkpoint_step"]),
                    "checkpoint": checkpoint,
                    "label": str(winner["label"]),
                    "oracle_method": oracle_method,
                    "coverage": float(winner["coverage"]),
                    "oracle_gate_count": int(winner["oracle_gate_count"]),
                    "asserted_cx_overhead": int(winner["asserted_cx_overhead"]),
                    **metrics,
                }
            )

    return pd.DataFrame(rows)
