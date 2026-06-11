from dataclasses import dataclass

from qiskit import QuantumCircuit


@dataclass
class QuantumWalkCircuit:
    circuit: QuantumCircuit
    checkpoints: list[int]
    checkpoint_labels: list[str]


def append_controlled_increment(
    circuit: QuantumCircuit,
    control_qubit: int,
    position_qubits: list[int],
) -> None:
    """
    Add 1 modulo 2^n to the position register when control_qubit = 1.

    position_qubits are ordered from least significant bit to
    most significant bit.
    """
    if not position_qubits:
        raise ValueError("position_qubits must not be empty.")

    for target_index in range(len(position_qubits) - 1, 0, -1):
        controls = [control_qubit, *position_qubits[:target_index]]
        target = position_qubits[target_index]
        circuit.mcx(controls, target)

    circuit.cx(control_qubit, position_qubits[0])


def append_controlled_decrement(
    circuit: QuantumCircuit,
    control_qubit: int,
    position_qubits: list[int],
) -> None:
    """
    Subtract 1 modulo 2^n from the position register
    when control_qubit = 1.
    """
    if not position_qubits:
        raise ValueError("position_qubits must not be empty.")

    circuit.cx(control_qubit, position_qubits[0])

    for target_index in range(1, len(position_qubits)):
        controls = [control_qubit, *position_qubits[:target_index]]
        target = position_qubits[target_index]
        circuit.mcx(controls, target)


def append_quantum_walk_step(
    circuit: QuantumCircuit,
    coin_qubit: int,
    position_qubits: list[int],
) -> None:
    """
    Append one discrete-time coined quantum walk step.

    coin = 1: move clockwise, position + 1
    coin = 0: move counter-clockwise, position - 1
    """
    circuit.h(coin_qubit)

    append_controlled_increment(
        circuit=circuit,
        control_qubit=coin_qubit,
        position_qubits=position_qubits,
    )

    circuit.x(coin_qubit)

    append_controlled_decrement(
        circuit=circuit,
        control_qubit=coin_qubit,
        position_qubits=position_qubits,
    )

    circuit.x(coin_qubit)


def build_cycle_quantum_walk(
    num_position_qubits: int = 2,
    num_steps: int = 4,
) -> QuantumWalkCircuit:
    """
    Construct a coined quantum walk on a cycle of size 2^num_position_qubits.

    Qubit layout:
    q0: coin
    q1...: position register
    """
    if num_position_qubits < 1:
        raise ValueError("num_position_qubits must be at least 1.")

    if num_steps < 1:
        raise ValueError("num_steps must be at least 1.")

    coin_qubit = 0
    position_qubits = list(range(1, num_position_qubits + 1))

    circuit = QuantumCircuit(1 + num_position_qubits)

    checkpoints: list[int] = []
    checkpoint_labels: list[str] = []

    for step in range(1, num_steps + 1):
        append_quantum_walk_step(
            circuit=circuit,
            coin_qubit=coin_qubit,
            position_qubits=position_qubits,
        )

        circuit.barrier()

        checkpoints.append(len(circuit.data))
        checkpoint_labels.append(f"after_walk_step_{step}")

    return QuantumWalkCircuit(
        circuit=circuit,
        checkpoints=checkpoints,
        checkpoint_labels=checkpoint_labels,
    )
