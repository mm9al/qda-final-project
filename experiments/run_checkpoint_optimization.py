from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.optimizer import scan_checkpoints, select_best_checkpoint
from src.quantum_walk import build_cycle_quantum_walk

RAW_DIR = PROJECT_ROOT / "results" / "raw"


def main() -> None:
    quantum_walk = build_cycle_quantum_walk(
        num_position_qubits=2,
        num_steps=5,
    )

    results = scan_checkpoints(
        circuit=quantum_walk.circuit,
        checkpoints=quantum_walk.checkpoints,
        checkpoint_labels=quantum_walk.checkpoint_labels,
    )

    print("=== Candidate Checkpoints ===")
    print(results.to_string(index=False))

    print("\n=== Best Checkpoint: Max Sparsity ===")
    print(
        select_best_checkpoint(
            checkpoint_results=results,
            strategy="max_sparsity",
        )
    )

    print("\n=== Best Checkpoint: Balanced ===")
    print(
        select_best_checkpoint(
            checkpoint_results=results,
            strategy="balanced",
        )
    )

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    output_path = RAW_DIR / "qwalk_results.csv"
    results.to_csv(output_path, index=False)

    print(f"\nSaved results to: {output_path}")


if __name__ == "__main__":
    main()
