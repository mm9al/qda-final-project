from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


@dataclass
class StateAnalysis:
    non_vanishing_states: list[tuple[str, complex]]
    vanishing_states: list[str]
    sparsity: float


def append_instruction_copy(
    target: QuantumCircuit,
    source: QuantumCircuit,
    instruction,
) -> None:
    """
    Copy a circuit instruction from source circuit to target circuit.
    """
    qargs = [
        target.qubits[source.find_bit(qubit).index]
        for qubit in instruction.qubits
    ]

    cargs = [
        target.clbits[source.find_bit(clbit).index]
        for clbit in instruction.clbits
    ]

    target.append(
        instruction.operation,
        qargs,
        cargs,
    )


def build_prefix_circuit(
    circuit: QuantumCircuit,
    num_instructions: int,
) -> QuantumCircuit:
    """
    Return a prefix containing the first num_instructions instructions.
    """
    if num_instructions < 0 or num_instructions > len(circuit.data):
        raise ValueError("Invalid prefix length.")

    prefix = QuantumCircuit(
        circuit.num_qubits,
        circuit.num_clbits,
    )

    for instruction in circuit.data[:num_instructions]:
        append_instruction_copy(
            target=prefix,
            source=circuit,
            instruction=instruction,
        )

    return prefix


def analyze_statevector(
    statevector: Statevector,
    tolerance: float = 1e-10,
) -> StateAnalysis:
    """
    Extract vanishing states and calculate sparsity.
    """
    num_qubits = statevector.num_qubits

    non_vanishing_states: list[tuple[str, complex]] = []
    vanishing_states: list[str] = []

    for index, amplitude in enumerate(statevector.data):
        state = format(index, f"0{num_qubits}b")

        if np.abs(amplitude) < tolerance:
            vanishing_states.append(state)
        else:
            non_vanishing_states.append((state, amplitude))

    sparsity = len(vanishing_states) / len(statevector.data)

    return StateAnalysis(
        non_vanishing_states=non_vanishing_states,
        vanishing_states=vanishing_states,
        sparsity=sparsity,
    )


def analyze_checkpoint(
    circuit: QuantumCircuit,
    checkpoint: int,
    tolerance: float = 1e-10,
) -> StateAnalysis:
    """
    Simulate a prefix of the circuit and analyze its statevector.
    """
    prefix = build_prefix_circuit(
        circuit=circuit,
        num_instructions=checkpoint,
    )

    statevector = Statevector.from_instruction(prefix)

    return analyze_statevector(
        statevector=statevector,
        tolerance=tolerance,
    )
