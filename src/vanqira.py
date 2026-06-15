"""Simplified VanQiRA pipeline for the Simon case study."""

from __future__ import annotations

from qiskit import QuantumCircuit

from src.assertion import (
    VanishingAssertionSpec,
    insert_assertion,
    synthesize_minterm_oracle,
    synthesize_xor_oracle,
)
from src.simon import (
    assertion_support,
    build_baseline_circuit,
    build_core_circuit,
    vanishing_states,
)


def build_simon_assertion_spec(secret: str) -> VanishingAssertionSpec:
    """Characterize Simon vanishing states after the final H layer."""

    states = tuple(vanishing_states(secret))
    return VanishingAssertionSpec(
        num_asserted_qubits=len(secret),
        vanishing_states=states,
        description=f"Simon vanishing states for secret={secret}: y dot s = 1",
    )


def synthesize_simon_assertion_oracle(
    secret: str,
    method: str = "xor",
) -> QuantumCircuit:
    """Synthesize Ua for the Simon assertion.

    method="xor" uses the optimized ESOP form y dot s.
    method="minterm" uses explicit minterm synthesis over all vanishing states.
    """

    spec = build_simon_assertion_spec(secret)

    if method == "xor":
        return synthesize_xor_oracle(
            num_asserted_qubits=len(secret),
            support=assertion_support(secret),
            name=f"Ua_simon_xor_{secret}",
        )

    if method == "minterm":
        return synthesize_minterm_oracle(
            spec,
            name=f"Ua_simon_minterm_{secret}",
        )

    raise ValueError(f"unknown synthesis method: {method}")


def build_simon_asserted_circuit(
    secret: str = "101",
    measure: bool = True,
    method: str = "xor",
) -> QuantumCircuit:
    """Build Simon circuit with VanQiRA-style assertion insertion."""

    core = build_core_circuit(secret)
    oracle = synthesize_simon_assertion_oracle(secret, method=method)

    if not measure:
        assertion_ancilla = core.num_qubits
        circuit = QuantumCircuit(core.num_qubits + 1, name="simon_asserted")
        circuit.compose(core, qubits=range(core.num_qubits), inplace=True)
        circuit.barrier()
        circuit.compose(
            oracle,
            qubits=list(range(len(secret))) + [assertion_ancilla],
            inplace=True,
        )
        return circuit

    return insert_assertion(
        core_circuit=core,
        asserted_qubits=range(len(secret)),
        assertion_oracle=oracle,
        measured_qubits=range(len(secret)),
        name="simon_asserted",
    )


def circuit_overhead(secret: str = "101", method: str = "xor") -> list[dict[str, int | str]]:
    """Return compact baseline/asserted circuit overhead rows for reports."""

    baseline = build_baseline_circuit(secret, measure=False)
    asserted = build_simon_asserted_circuit(secret, measure=False, method=method)
    return [
        _overhead_row("baseline", baseline),
        _overhead_row(f"asserted_{method}", asserted),
    ]


def _overhead_row(label: str, circuit: QuantumCircuit) -> dict[str, int | str]:
    ops = circuit.count_ops()
    return {
        "circuit": label,
        "qubits": circuit.num_qubits,
        "depth": circuit.depth(),
        "cx_count": int(ops.get("cx", 0)),
        "h_count": int(ops.get("h", 0)),
    }
