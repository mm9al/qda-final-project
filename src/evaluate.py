"""Simulation and metrics for Simon and quantum-walk assertion experiments."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector

from src.simon import legal_y
from src.utils import append_instruction_copy, basis_index_to_qubit_order_state


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


@dataclass(frozen=True)
class PauliErrorEvent:
    """One Pauli error inserted after an original circuit instruction."""

    instruction_index: int
    qubit_index: int
    pauli: str


PauliTrace = tuple[PauliErrorEvent, ...]


def generate_pauli_error_traces(
    circuit: QuantumCircuit,
    num_traces: int = 1000,
    error_probability: float = 0.01,
    seed: int = 2026,
) -> list[PauliTrace]:
    """Generate shared Pauli error traces for Monte Carlo evaluation.

    A trace contains errors sampled for the original circuit only.  For every
    non-barrier, non-measure instruction and every qubit touched by that
    instruction, an X/Y/Z error is inserted with probability
    ``error_probability``.
    """

    if num_traces < 1:
        raise ValueError("num_traces must be positive")
    if error_probability < 0 or error_probability > 1:
        raise ValueError("error_probability must be between 0 and 1")

    rng = np.random.default_rng(seed)
    traces: list[PauliTrace] = []
    paulis = np.array(["x", "y", "z"])

    for _ in range(num_traces):
        events: list[PauliErrorEvent] = []

        for instruction_index, instruction in enumerate(circuit.data):
            operation_name = instruction.operation.name
            if operation_name in {"barrier", "measure"}:
                continue

            for qubit in instruction.qubits:
                if rng.random() < error_probability:
                    events.append(
                        PauliErrorEvent(
                            instruction_index=instruction_index,
                            qubit_index=circuit.find_bit(qubit).index,
                            pauli=str(rng.choice(paulis)),
                        )
                    )

        traces.append(tuple(events))

    return traces


def _events_by_instruction(trace: PauliTrace) -> dict[int, list[PauliErrorEvent]]:
    events: dict[int, list[PauliErrorEvent]] = {}
    for event in trace:
        events.setdefault(event.instruction_index, []).append(event)
    return events


def _append_pauli_event(circuit: QuantumCircuit, event: PauliErrorEvent) -> None:
    if event.pauli == "x":
        circuit.x(event.qubit_index)
    elif event.pauli == "y":
        circuit.y(event.qubit_index)
    elif event.pauli == "z":
        circuit.z(event.qubit_index)
    else:
        raise ValueError(f"unsupported Pauli error: {event.pauli}")


def build_qwalk_trace_circuit(
    circuit: QuantumCircuit,
    checkpoint: int,
    oracle: QuantumCircuit,
    trace: PauliTrace,
    oracle_trace: PauliTrace | None = None,
) -> QuantumCircuit:
    """Build one asserted qwalk circuit with a sampled original-gate trace."""

    if checkpoint < 0 or checkpoint > len(circuit.data):
        raise ValueError("Invalid checkpoint.")

    assertion_ancilla = circuit.num_qubits
    traced = QuantumCircuit(circuit.num_qubits + 1, name="qwalk_trace")
    events = _events_by_instruction(trace)
    oracle_events = (
        _events_by_instruction(oracle_trace)
        if oracle_trace is not None
        else None
    )

    def append_oracle() -> None:
        if oracle_events is None:
            traced.compose(
                oracle,
                qubits=list(range(circuit.num_qubits)) + [assertion_ancilla],
                inplace=True,
            )
            return

        for oracle_instruction_index, oracle_instruction in enumerate(oracle.data):
            append_instruction_copy(
                target=traced,
                source=oracle,
                instruction=oracle_instruction,
            )
            for event in oracle_events.get(oracle_instruction_index, []):
                _append_pauli_event(traced, event)

    for instruction_index, instruction in enumerate(circuit.data):
        if instruction_index == checkpoint:
            traced.barrier()
            append_oracle()
            traced.barrier()

        append_instruction_copy(
            target=traced,
            source=circuit,
            instruction=instruction,
        )
        for event in events.get(instruction_index, []):
            _append_pauli_event(traced, event)

    if checkpoint == len(circuit.data):
        traced.barrier()
        append_oracle()
        traced.barrier()

    return traced


def ideal_final_support(circuit: QuantumCircuit, tolerance: float = 1e-10) -> set[str]:
    """Return basis states with nonzero ideal final probability."""

    statevector = Statevector.from_instruction(circuit)
    return {
        basis_index_to_qubit_order_state(
            index=index,
            num_qubits=circuit.num_qubits,
        )
        for index, amplitude in enumerate(statevector.data)
        if abs(amplitude) >= tolerance
    }


def sample_statevector_index(
    statevector: Statevector,
    rng: np.random.Generator,
) -> int:
    probabilities = np.abs(statevector.data) ** 2
    probabilities = probabilities / probabilities.sum()
    return int(rng.choice(len(probabilities), p=probabilities))


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def calculate_support_level_fpr(fp: int, tn: int) -> float:
    return safe_divide(fp, fp + tn)


def calculate_postselected_support_valid_rate(
    tn: int,
    fn: int,
) -> float:
    return safe_divide(tn, tn + fn)


def qwalk_confusion_metrics(
    outcomes: list[tuple[bool, bool]],
) -> dict[str, float | int]:
    """Aggregate qwalk assertion outcomes.

    Each outcome is ``(detected, final_state_valid)``.
    """

    tp = tn = fp = fn = 0

    for detected, final_state_valid in outcomes:
        if detected and not final_state_valid:
            tp += 1
        elif not detected and final_state_valid:
            tn += 1
        elif detected and final_state_valid:
            fp += 1
        else:
            fn += 1

    return {
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "Detection Rate": safe_divide(tp, tp + fn),
        "Support-Level FPR": calculate_support_level_fpr(fp, tn),
        "Post-selected Support-Valid Rate": (
            calculate_postselected_support_valid_rate(tn, fn)
        ),
    }


def evaluate_qwalk_strategy(
    circuit: QuantumCircuit,
    checkpoint: int,
    oracle: QuantumCircuit,
    traces: list[PauliTrace],
    final_support: set[str],
    seed: int = 90210,
    oracle_traces: list[PauliTrace] | None = None,
) -> dict[str, float | int]:
    """Evaluate one asserted qwalk strategy over shared Pauli traces."""

    if oracle_traces is not None and len(oracle_traces) != len(traces):
        raise ValueError("oracle_traces must have the same length as traces")

    rng = np.random.default_rng(seed)
    outcomes: list[tuple[bool, bool]] = []
    num_data_qubits = circuit.num_qubits
    data_mask = (1 << num_data_qubits) - 1

    for trace_index, trace in enumerate(traces):
        traced = build_qwalk_trace_circuit(
            circuit=circuit,
            checkpoint=checkpoint,
            oracle=oracle,
            trace=trace,
            oracle_trace=(
                oracle_traces[trace_index]
                if oracle_traces is not None
                else None
            ),
        )
        statevector = Statevector.from_instruction(traced)
        sampled_index = sample_statevector_index(statevector, rng)

        data_index = sampled_index & data_mask
        data_state = basis_index_to_qubit_order_state(
            index=data_index,
            num_qubits=num_data_qubits,
        )
        assertion_bit = (sampled_index >> num_data_qubits) & 1

        outcomes.append(
            (
                assertion_bit == 1,
                data_state in final_support,
            )
        )

    return qwalk_confusion_metrics(outcomes)
