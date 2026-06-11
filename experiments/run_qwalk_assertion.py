from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import pandas as pd
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from src.assertion import VanishingAssertionSpec, synthesize_minterm_oracle
from src.optimizer import scan_checkpoints, select_best_checkpoint
from src.quantum_walk import build_cycle_quantum_walk
from src.utils import analyze_checkpoint, append_instruction_copy, build_prefix_circuit

RAW_DIR = PROJECT_ROOT / "results" / "raw"


def build_asserted_qwalk_circuit(
    circuit: QuantumCircuit,
    checkpoint: int,
    oracle: QuantumCircuit,
) -> QuantumCircuit:
    assertion_ancilla = circuit.num_qubits
    asserted = QuantumCircuit(circuit.num_qubits + 1, name="qwalk_asserted_minterm")

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


def circuit_overhead_rows(
    baseline: QuantumCircuit,
    asserted: QuantumCircuit,
) -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []

    for name, circuit in (
        ("baseline", baseline),
        ("asserted_minterm", asserted),
    ):
        counts = circuit.count_ops()
        rows.append(
            {
                "circuit": name,
                "qubits": circuit.num_qubits,
                "depth": circuit.depth(),
                "cx_count": counts.get("cx", 0),
                "h_count": counts.get("h", 0),
            }
        )

    return rows


def main() -> None:
    quantum_walk = build_cycle_quantum_walk(
        num_position_qubits=2,
        num_steps=4,
    )

    checkpoint_results = scan_checkpoints(
        circuit=quantum_walk.circuit,
        checkpoints=quantum_walk.checkpoints,
        checkpoint_labels=quantum_walk.checkpoint_labels,
    )
    best_checkpoint = select_best_checkpoint(
        checkpoint_results=checkpoint_results,
        strategy="balanced",
    )

    checkpoint = int(best_checkpoint["checkpoint"])
    analysis = analyze_checkpoint(
        circuit=quantum_walk.circuit,
        checkpoint=checkpoint,
    )

    spec = VanishingAssertionSpec(
        num_asserted_qubits=quantum_walk.circuit.num_qubits,
        vanishing_states=tuple(analysis.vanishing_states),
        description=str(best_checkpoint["label"]),
    )
    oracle = synthesize_minterm_oracle(spec)
    asserted_circuit = build_asserted_qwalk_circuit(
        circuit=quantum_walk.circuit,
        checkpoint=checkpoint,
        oracle=oracle,
    )

    prefix = build_prefix_circuit(
        circuit=quantum_walk.circuit,
        num_instructions=checkpoint,
    )
    prefix_state = Statevector.from_instruction(prefix)
    oracle_gate_count = sum(oracle.count_ops().values())

    print("=== Selected Quantum Walk Assertion Checkpoint ===")
    print(best_checkpoint)
    print(f"\nVanishing states: {len(analysis.vanishing_states)}")
    print(f"Non-vanishing states: {len(analysis.non_vanishing_states)}")
    print(f"Oracle gate count: {oracle_gate_count}")
    print(f"Prefix state norm: {prefix_state.probabilities().sum():.12f}")
    print("\n=== Assertion Oracle ===")
    print(oracle.draw())

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    overhead_df = pd.DataFrame(
        circuit_overhead_rows(
            baseline=quantum_walk.circuit,
            asserted=asserted_circuit,
        )
    )
    overhead_path = RAW_DIR / "qwalk_overhead.csv"
    overhead_df.to_csv(overhead_path, index=False)

    print("\n=== Circuit Overhead ===")
    print(overhead_df.to_string(index=False))
    print(f"\nSaved overhead to: {overhead_path}")


if __name__ == "__main__":
    main()
