"""Compatibility helpers for the Simon VanQiRA reproduction workflow."""

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


def build_simon_asserted_circuit(
    secret: str = "101",
    method: str = "xor",
) -> QuantumCircuit:
    """Build Simon's circuit with one assertion ancilla measured last."""

    validate_secret(secret)
    core = build_core_circuit(secret)
    n = len(secret)

    if method == "xor":
        oracle = synthesize_xor_oracle(
            num_asserted_qubits=n,
            support=assertion_support(secret),
            name="Ua_simon_xor",
        )
    elif method == "minterm":
        spec = VanishingAssertionSpec(
            num_asserted_qubits=n,
            vanishing_states=tuple(vanishing_states(secret)),
            description=f"Simon vanishing states for s={secret}",
        )
        oracle = synthesize_minterm_oracle(spec, name="Ua_simon_minterm")
    else:
        raise ValueError(f"Unsupported Simon assertion method: {method}")

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


def circuit_overhead(secret: str = "101") -> list[dict[str, int | str]]:
    """Return baseline/asserted Simon circuit overhead rows."""

    baseline = build_baseline_circuit(secret)
    asserted = build_simon_asserted_circuit(secret, method="xor")
    rows: list[dict[str, int | str]] = []

    for name, circuit in (
        ("baseline", baseline),
        ("asserted_xor", asserted),
    ):
        counts = circuit.count_ops()
        rows.append(
            {
                "circuit": name,
                "qubits": circuit.num_qubits,
                "depth": circuit.depth(),
                "cx_count": counts.get("cx", 0),
                "h_count": counts.get("h", 0),
                "gate_count": _gate_count(circuit),
            }
        )

    return rows
