from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd
from qiskit import QuantumCircuit

from src.utils import analyze_checkpoint


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


def select_best_checkpoint(
    checkpoint_results: pd.DataFrame,
    strategy: str = "balanced",
) -> pd.Series:
    """
    Supported strategies:
    - max_sparsity
    - min_overhead
    - balanced
    """
    if checkpoint_results.empty:
        raise ValueError("checkpoint_results must not be empty.")

    if strategy == "max_sparsity":
        index = checkpoint_results["sparsity"].idxmax()
    elif strategy == "min_overhead":
        index = checkpoint_results["naive_oracle_terms"].idxmin()
    elif strategy == "balanced":
        index = checkpoint_results["balanced_score"].idxmax()
    else:
        raise ValueError(f"Unsupported strategy: {strategy}")

    return checkpoint_results.loc[index]
