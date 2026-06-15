from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from qiskit.quantum_info import Statevector

from src.quantum_walk import build_cycle_quantum_walk


def print_nonzero_states(statevector: Statevector, tolerance: float = 1e-10) -> None:
    num_qubits = statevector.num_qubits

    for index, amplitude in enumerate(statevector.data):
        if abs(amplitude) >= tolerance:
            state = format(index, f"0{num_qubits}b")
            probability = abs(amplitude) ** 2

            print(
                f"|{state}>: "
                f"amplitude={amplitude:.4f}, "
                f"probability={probability:.4f}"
            )


def main() -> None:
    quantum_walk = build_cycle_quantum_walk(
        num_position_qubits=2,
        num_steps=4,
    )

    circuit = quantum_walk.circuit

    print("=== Quantum Walk Circuit ===")
    print(circuit.draw())

    print("\n=== Final State ===")
    statevector = Statevector.from_instruction(circuit)
    print_nonzero_states(statevector)

    total_probability = sum(abs(amplitude) ** 2 for amplitude in statevector.data)
    print(f"\nTotal probability: {total_probability:.12f}")


if __name__ == "__main__":
    main()
