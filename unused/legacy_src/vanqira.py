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
    validate_secret,
    vanishing_states,
)


def build_simon_assertion_spec(secret: str) -> VanishingAssertionSpec:
    """Characterize Simon vanishing states after the final H layer."""

    validate_secret(secret)
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

    validate_secret(secret)
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

    raise ValueError(f"unknown Simon assertion method: {method}")


def build_simon_asserted_circuit(
    secret: str = "101",
    measure: bool = True,
    method: str = "xor",
) -> QuantumCircuit:
    """Build Simon circuit with VanQiRA-style assertion insertion."""

    validate_secret(secret)
    core = build_core_circuit(secret)
    oracle = synthesize_simon_assertion_oracle(secret, method=method)
    n = len(secret)

    if not measure:
        assertion_ancilla = core.num_qubits
        circuit = QuantumCircuit(core.num_qubits + 1, name=f"simon_asserted_{method}")
        circuit.compose(core, qubits=range(core.num_qubits), inplace=True)
        circuit.barrier()
        circuit.compose(
            oracle,
            qubits=list(range(n)) + [assertion_ancilla],
            inplace=True,
        )
        return circuit

    return insert_assertion(
        core_circuit=core,
        asserted_qubits=range(n),
        assertion_oracle=oracle,
        measured_qubits=range(n),
        name=f"simon_asserted_{method}",
    )


def _gate_count(circuit: QuantumCircuit) -> int:
    ignored_ops = {"barrier", "measure"}
    return sum(
        count
        for name, count in circuit.count_ops().items()
        if name not in ignored_ops
    )


def circuit_overhead(
    secret: str = "101",
    method: str = "xor",
) -> list[dict[str, int | str]]:
    """Return compact baseline/asserted Simon circuit overhead rows."""

    baseline = build_baseline_circuit(secret, measure=False)
    asserted = build_simon_asserted_circuit(secret, measure=False, method=method)
    rows: list[dict[str, int | str]] = []

    for name, circuit in (
        ("baseline", baseline),
        (f"asserted_{method}", asserted),
    ):
        counts = circuit.count_ops()
        rows.append(
            {
                "circuit": name,
                "qubits": circuit.num_qubits,
                "depth": circuit.depth(),
                "cx_count": int(counts.get("cx", 0)),
                "h_count": int(counts.get("h", 0)),
                "gate_count": _gate_count(circuit),
            }
        )

    return rows
