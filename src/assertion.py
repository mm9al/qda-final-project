"""Vanishing-state-based runtime assertion utilities.

This file implements the assertion-related part of the simplified VanQiRA flow:
1. characterize vanishing states,
2. synthesize a Boolean assertion oracle Ua,
3. insert Ua into a quantum circuit with one assertion ancilla.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from qiskit import QuantumCircuit


@dataclass(frozen=True)
class VanishingAssertionSpec:
    """A compact description of a vanishing-state assertion.

    vanishing_states are written in qubit-index order.  For example, "101"
    means q[0] = 1, q[1] = 0, q[2] = 1.
    """

    num_asserted_qubits: int
    vanishing_states: tuple[str, ...]
    description: str = ""


def synthesize_xor_oracle(
    num_asserted_qubits: int,
    support: Sequence[int],
    name: str = "Ua_xor",
) -> QuantumCircuit:
    """Synthesize Ua for f(q) = XOR over q[i] for i in support.

    This is an ESOP-style oracle.  Each single-literal product term becomes one
    CNOT into the assertion ancilla.
    """

    target = num_asserted_qubits
    oracle = QuantumCircuit(num_asserted_qubits + 1, name=name)

    for qubit in support:
        if qubit < 0 or qubit >= num_asserted_qubits:
            raise ValueError(f"invalid qubit index in support: {qubit}")
        oracle.cx(qubit, target)

    return oracle


def synthesize_minterm_oracle(
    spec: VanishingAssertionSpec,
    name: str = "Ua_minterm",
) -> QuantumCircuit:
    """Naively synthesize Ua from explicit vanishing states.

    This is a general but non-optimized synthesis method: for each vanishing
    basis state, add one multi-controlled X.  It is useful for later extensions
    beyond Simon.
    """

    n = spec.num_asserted_qubits
    target = n
    oracle = QuantumCircuit(n + 1, name=name)
    controls = list(range(n))

    for state in spec.vanishing_states:
        if len(state) != n or any(bit not in {"0", "1"} for bit in state):
            raise ValueError(f"invalid vanishing state: {state}")

        flipped: list[int] = []
        for idx, bit in enumerate(state):
            if bit == "0":
                oracle.x(idx)
                flipped.append(idx)

        if n == 1:
            oracle.cx(0, target)
        else:
            oracle.mcx(controls, target)

        for idx in reversed(flipped):
            oracle.x(idx)

    return oracle


def insert_assertion(
    core_circuit: QuantumCircuit,
    asserted_qubits: Sequence[int],
    assertion_oracle: QuantumCircuit,
    measured_qubits: Sequence[int],
    name: str = "asserted_circuit",
) -> QuantumCircuit:
    """Insert assertion oracle after core_circuit and measure the result.

    assertion_oracle is assumed to act on [asserted_qubits..., assertion_ancilla].
    The output circuit measures measured_qubits and then measures the assertion
    ancilla as the last classical bit.
    """

    asserted_qubits = tuple(asserted_qubits)
    measured_qubits = tuple(measured_qubits)
    expected_oracle_qubits = len(asserted_qubits) + 1

    if assertion_oracle.num_qubits != expected_oracle_qubits:
        raise ValueError(
            f"oracle has {assertion_oracle.num_qubits} qubits, "
            f"but expected {expected_oracle_qubits}"
        )

    assertion_ancilla = core_circuit.num_qubits
    num_clbits = len(measured_qubits) + 1
    circuit = QuantumCircuit(core_circuit.num_qubits + 1, num_clbits, name=name)

    circuit.compose(core_circuit, qubits=list(range(core_circuit.num_qubits)), inplace=True)
    circuit.barrier()
    circuit.compose(
        assertion_oracle,
        qubits=list(asserted_qubits) + [assertion_ancilla],
        inplace=True,
    )

    for cidx, qidx in enumerate(measured_qubits):
        circuit.measure(qidx, cidx)
    circuit.measure(assertion_ancilla, len(measured_qubits))

    return circuit
