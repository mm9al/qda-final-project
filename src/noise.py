"""Noise models used by the Simon reproduction experiments."""

from __future__ import annotations

from qiskit_aer.noise import NoiseModel, depolarizing_error


def build_depolarizing_noise_model(
    one_qubit_error: float,
    two_qubit_error: float | None = None,
) -> NoiseModel | None:
    """Create a simple depolarizing noise model for H/CX Simon circuits.

    Passing ``one_qubit_error = 0`` and ``two_qubit_error = 0`` returns ``None``
    so Aer runs an ideal simulation.
    """

    if one_qubit_error < 0:
        raise ValueError("one_qubit_error must be non-negative")
    if two_qubit_error is None:
        two_qubit_error = min(1.0, 10.0 * one_qubit_error)
    if two_qubit_error < 0:
        raise ValueError("two_qubit_error must be non-negative")
    if one_qubit_error == 0 and two_qubit_error == 0:
        return None

    noise_model = NoiseModel()
    if one_qubit_error > 0:
        error_1q = depolarizing_error(one_qubit_error, 1)
        noise_model.add_all_qubit_quantum_error(error_1q, ["h", "x", "sx", "id"])
    if two_qubit_error > 0:
        error_2q = depolarizing_error(two_qubit_error, 2)
        noise_model.add_all_qubit_quantum_error(error_2q, ["cx"])

    return noise_model
