from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


@dataclass
class StateAnalysis:
    non_vanishing_states: list[tuple[str, complex]]
    vanishing_states: list[str]
    sparsity: float


@dataclass(frozen=True)
class FaultSensitivity:
    """Single-checkpoint Pauli-fault sensitivity against vanishing states."""

    fault_sensitive_detection: float
    bit_flip_detection: float
    phase_detection: float
    num_fault_locations: int


def basis_index_to_qubit_order_state(index: int, num_qubits: int) -> str:
    """Return a basis-state label in q[0], q[1], ... order."""
    if index < 0:
        raise ValueError("basis index must be non-negative")
    if index >= 2**num_qubits:
        raise ValueError("basis index does not fit in num_qubits")

    return "".join(
        "1" if index & (1 << qubit) else "0"
        for qubit in range(num_qubits)
    )


def qubit_order_state_to_basis_index(state: str) -> int:
    """Convert a q[0], q[1], ... basis label into Qiskit's basis index."""
    if any(bit not in {"0", "1"} for bit in state):
        raise ValueError(f"invalid basis state: {state}")

    index = 0
    for qubit, bit in enumerate(state):
        if bit == "1":
            index |= 1 << qubit
    return index


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
        state = basis_index_to_qubit_order_state(
            index=index,
            num_qubits=num_qubits,
        )

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


def fault_sensitivity_at_checkpoint(
    circuit: QuantumCircuit,
    checkpoint: int,
    vanishing_states: list[str] | tuple[str, ...] | None = None,
    tolerance: float = 1e-10,
) -> FaultSensitivity:
    """Average assertion-detection probability for single-qubit Pauli faults.

    The score is the checkpoint-local proxy

        avg_{q, P in {X,Y,Z}} || Pi_V P_q |psi_t> ||^2,

    where V is the vanishing subspace at the checkpoint. X and Y have the same
    computational-basis probabilities here; Z only changes phases, so it is
    included explicitly to keep the metric aligned with a Pauli fault model.
    """

    if checkpoint < 0 or checkpoint > len(circuit.data):
        raise ValueError("Invalid checkpoint.")

    prefix = build_prefix_circuit(
        circuit=circuit,
        num_instructions=checkpoint,
    )
    statevector = Statevector.from_instruction(prefix)

    if vanishing_states is None:
        analysis = analyze_statevector(
            statevector=statevector,
            tolerance=tolerance,
        )
        vanishing_states = analysis.vanishing_states

    vanishing_indices = {
        qubit_order_state_to_basis_index(state)
        for state in vanishing_states
    }
    probabilities = np.abs(statevector.data) ** 2

    bit_flip_total = 0.0
    phase_total = 0.0
    for qubit in range(circuit.num_qubits):
        mask = 1 << qubit
        bit_flip_total += sum(
            probability
            for index, probability in enumerate(probabilities)
            if (index ^ mask) in vanishing_indices
        )
        phase_total += sum(
            probability
            for index, probability in enumerate(probabilities)
            if index in vanishing_indices
        )

    bit_flip_detection = bit_flip_total / max(circuit.num_qubits, 1)
    phase_detection = phase_total / max(circuit.num_qubits, 1)
    fault_sensitive_detection = (
        2.0 * bit_flip_total + phase_total
    ) / max(3 * circuit.num_qubits, 1)

    return FaultSensitivity(
        fault_sensitive_detection=float(fault_sensitive_detection),
        bit_flip_detection=float(bit_flip_detection),
        phase_detection=float(phase_detection),
        num_fault_locations=3 * circuit.num_qubits,
    )
