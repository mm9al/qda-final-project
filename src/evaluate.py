"""Simulation and metrics for Simon assertion experiments."""

from __future__ import annotations

from collections.abc import Mapping

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from src.simon import legal_y


def run_counts(
    circuit: QuantumCircuit,
    shots: int = 4096,
    noise_model=None,
    seed: int = 1234,
) -> dict[str, int]:
    """Run a circuit on Aer and return measurement counts."""

    simulator = AerSimulator(noise_model=noise_model, seed_simulator=seed)
    compiled = transpile(circuit, simulator, seed_transpiler=seed)
    result = simulator.run(compiled, shots=shots).result()
    return dict(result.get_counts())


def qiskit_key_to_index_order(key: str) -> str:
    """Convert a Qiskit count key to classical-bit index order.

    Qiskit displays count keys with the highest classical bit first.  The
    experiments measure q[i] into c[i], so reversing the compact key gives the
    qubit-index order used by the secret string.
    """

    return key.replace(" ", "")[::-1]


def y_from_count_key(key: str, n: int) -> str:
    return qiskit_key_to_index_order(key)[:n]


def assertion_bit_from_count_key(key: str, n: int) -> int:
    converted = qiskit_key_to_index_order(key)
    if len(converted) <= n:
        raise ValueError("count key does not contain an assertion bit")
    return int(converted[n])


def baseline_success_rate(counts: Mapping[str, int], secret: str) -> float:
    """Fraction of all baseline shots whose measured y is legal."""

    total = sum(counts.values())
    if total == 0:
        return 0.0
    n = len(secret)
    successes = sum(
        count for key, count in counts.items() if legal_y(secret, y_from_count_key(key, n))
    )
    return successes / total


def asserted_metrics(counts: Mapping[str, int], secret: str) -> dict[str, float | int]:
    """Compute pass/error-report rates and filtered success for asserted runs."""

    total = sum(counts.values())
    if total == 0:
        return {
            "shots": 0,
            "pass_shots": 0,
            "error_report_shots": 0,
            "pass_rate": 0.0,
            "error_report_rate": 0.0,
            "filtered_success_rate": 0.0,
            "unfiltered_asserted_success_rate": 0.0,
        }

    n = len(secret)
    pass_shots = 0
    error_report_shots = 0
    filtered_successes = 0
    unfiltered_successes = 0

    for key, count in counts.items():
        y = y_from_count_key(key, n)
        assertion = assertion_bit_from_count_key(key, n)
        is_success = legal_y(secret, y)
        if is_success:
            unfiltered_successes += count
        if assertion == 0:
            pass_shots += count
            if is_success:
                filtered_successes += count
        else:
            error_report_shots += count

    return {
        "shots": total,
        "pass_shots": pass_shots,
        "error_report_shots": error_report_shots,
        "pass_rate": pass_shots / total,
        "error_report_rate": error_report_shots / total,
        "filtered_success_rate": filtered_successes / pass_shots if pass_shots else 0.0,
        "unfiltered_asserted_success_rate": unfiltered_successes / total,
    }


def evaluate_pair(
    baseline_circuit: QuantumCircuit,
    asserted_circuit: QuantumCircuit,
    secret: str,
    shots: int,
    noise_model=None,
    seed: int = 1234,
) -> dict[str, float | int]:
    """Run baseline/asserted circuits and return one CSV-ready metrics row."""

    baseline_counts = run_counts(baseline_circuit, shots, noise_model, seed)
    asserted_counts = run_counts(asserted_circuit, shots, noise_model, seed + 1)
    assertion = asserted_metrics(asserted_counts, secret)

    return {
        "shots": shots,
        "baseline_success_rate": baseline_success_rate(baseline_counts, secret),
        **assertion,
    }
