"""Simon circuits for the VanQiRA reproduction experiment.

The secret string convention is qubit-index order.  For example, ``"101"``
means q[0] = 1, q[1] = 0, q[2] = 1.
"""

from __future__ import annotations

from qiskit import QuantumCircuit


def validate_secret(secret: str) -> None:
    if not secret:
        raise ValueError("secret must not be empty")
    if any(bit not in {"0", "1"} for bit in secret):
        raise ValueError("secret must be a binary string")
    if "1" not in secret:
        raise ValueError("secret must be non-zero for Simon's problem")


def legal_y(secret: str, y: str) -> bool:
    """Return whether y dot secret == 0 mod 2.

    Both strings are interpreted in qubit-index order.
    """

    validate_secret(secret)
    if len(y) != len(secret) or any(bit not in {"0", "1"} for bit in y):
        raise ValueError("y must be a binary string with the same length as secret")
    parity = sum(int(a) & int(b) for a, b in zip(secret, y)) % 2
    return parity == 0


def vanishing_states(secret: str) -> list[str]:
    """Basis states that should have zero amplitude after Simon's final H layer."""

    validate_secret(secret)
    n = len(secret)
    return [
        format(value, f"0{n}b")[::-1]
        for value in range(2**n)
        if not legal_y(secret, format(value, f"0{n}b")[::-1])
    ]


def assertion_support(secret: str) -> tuple[int, ...]:
    """Return qubit indices used by the Simon parity assertion y dot s."""

    validate_secret(secret)
    return tuple(idx for idx, bit in enumerate(secret) if bit == "1")


def _orthogonal_rows(secret: str) -> list[list[int]]:
    """Build n-1 independent rows whose nullspace is span(secret)."""

    validate_secret(secret)
    n = len(secret)
    pivot = secret.index("1")
    rows: list[list[int]] = []

    for idx in range(n):
        if idx == pivot:
            continue
        row = [0] * n
        row[idx] = 1
        if secret[idx] == "1":
            row[pivot] = 1
        rows.append(row)

    return rows


def build_simon_oracle(secret: str) -> QuantumCircuit:
    """Return a reversible oracle U_f for a Simon function with period secret.

    The function is linear, f(x) = A x, where the rows of A are orthogonal to
    the secret.  Therefore f(x) = f(x xor secret), and the measured Simon output
    y is restricted to y dot secret = 0.
    """

    validate_secret(secret)
    n = len(secret)
    oracle = QuantumCircuit(2 * n, name=f"U_f(s={secret})")

    for out_idx, row in enumerate(_orthogonal_rows(secret)):
        target = n + out_idx
        for in_idx, coeff in enumerate(row):
            if coeff:
                oracle.cx(in_idx, target)

    return oracle


def build_core_circuit(secret: str = "101") -> QuantumCircuit:
    """Build the Simon circuit before measurement and before assertion."""

    validate_secret(secret)
    n = len(secret)
    circuit = QuantumCircuit(2 * n, name="simon_core")
    x = range(n)

    circuit.h(x)
    circuit.compose(build_simon_oracle(secret), inplace=True)
    circuit.h(x)

    return circuit


def build_simon_core(secret: str = "101") -> QuantumCircuit:
    """Alias for build_core_circuit with a more explicit external name."""

    return build_core_circuit(secret)


def build_baseline_circuit(secret: str = "101", measure: bool = True) -> QuantumCircuit:
    """Build the baseline Simon circuit."""

    validate_secret(secret)
    n = len(secret)
    circuit = QuantumCircuit(2 * n, n if measure else 0, name="simon_baseline")
    core = build_core_circuit(secret)
    circuit.compose(core, qubits=range(2 * n), inplace=True)

    if measure:
        for idx in range(n):
            circuit.measure(idx, idx)

    return circuit
