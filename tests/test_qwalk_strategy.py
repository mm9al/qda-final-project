from __future__ import annotations

import unittest

import pandas as pd
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from experiments.run_qwalk_strategy_evaluation import (
    PUBLIC_COLUMNS,
    output_path_for_run,
    parse_args,
    run_evaluation,
)
from experiments.run_qwalk_scaling_evaluation import (
    output_path_for_run as scaling_output_path_for_run,
)
from src.assertion import (
    VanishingAssertionSpec,
    synthesize_minterm_oracle,
    synthesize_simplified_boolean_oracle,
    synthesize_vanishing_oracle,
)
from src.evaluate import (
    generate_pauli_error_traces,
    qwalk_confusion_metrics,
)
from src.quantum_walk import build_cycle_quantum_walk
from src.optimizer import select_best_checkpoint
from src.qwalk_scaling import (
    DEFAULT_POSITION_QUBITS,
    DEFAULT_STRATEGIES,
    DEFAULT_WALK_STEPS,
    benchmark_settings,
    benchmark_suite_table,
    pareto_frontier,
    scan_scaling_candidates,
    select_scaling_strategy_winners,
)
from src.utils import analyze_checkpoint, append_instruction_copy


def assertion_output_for_state(oracle: QuantumCircuit, state: str) -> int:
    num_asserted_qubits = len(state)
    circuit = QuantumCircuit(num_asserted_qubits + 1)

    for qubit, bit in enumerate(state):
        if bit == "1":
            circuit.x(qubit)

    circuit.compose(oracle, inplace=True)
    statevector = Statevector.from_instruction(circuit)
    index = int(max(
        range(len(statevector.data)),
        key=lambda idx: abs(statevector.data[idx]),
    ))

    return (index >> num_asserted_qubits) & 1


def assertion_probability_for_ideal_prefix(
    circuit: QuantumCircuit,
    checkpoint: int,
    oracle: QuantumCircuit,
) -> float:
    assertion_ancilla = circuit.num_qubits
    asserted = QuantumCircuit(circuit.num_qubits + 1)

    for instruction in circuit.data[:checkpoint]:
        append_instruction_copy(
            target=asserted,
            source=circuit,
            instruction=instruction,
        )

    asserted.compose(
        oracle,
        qubits=list(range(circuit.num_qubits)) + [assertion_ancilla],
        inplace=True,
    )

    statevector = Statevector.from_instruction(asserted)
    return sum(
        abs(amplitude) ** 2
        for index, amplitude in enumerate(statevector.data)
        if (index >> assertion_ancilla) & 1
    )


class AssertionOracleTests(unittest.TestCase):
    def test_simplified_boolean_matches_minterm_oracle(self) -> None:
        spec = VanishingAssertionSpec(
            num_asserted_qubits=3,
            vanishing_states=("000", "011", "101", "110"),
        )
        minterm = synthesize_minterm_oracle(spec)
        simplified = synthesize_simplified_boolean_oracle(spec)

        for index in range(2**spec.num_asserted_qubits):
            state = format(index, f"0{spec.num_asserted_qubits}b")
            expected = int(state in spec.vanishing_states)

            self.assertEqual(
                assertion_output_for_state(minterm, state),
                expected,
            )
            self.assertEqual(
                assertion_output_for_state(minterm, state),
                assertion_output_for_state(simplified, state),
            )

    def test_invalid_state_raises(self) -> None:
        spec = VanishingAssertionSpec(
            num_asserted_qubits=3,
            vanishing_states=("010", "12"),
        )

        with self.assertRaises(ValueError):
            synthesize_simplified_boolean_oracle(spec)


class StrategySelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.results = pd.DataFrame(
            [
                {
                    "checkpoint": 8,
                    "oracle_method": "minterm",
                    "num_vanishing_states": 2,
                    "sparsity": 0.75,
                    "balanced_score": 0.72,
                    "naive_oracle_terms": 2,
                    "oracle_gate_count": 40,
                    "benefit_cost_score": 0.9,
                },
                {
                    "checkpoint": 8,
                    "oracle_method": "simplified_boolean",
                    "num_vanishing_states": 2,
                    "sparsity": 0.75,
                    "balanced_score": 0.72,
                    "naive_oracle_terms": 2,
                    "oracle_gate_count": 10,
                    "benefit_cost_score": 0.8,
                },
                {
                    "checkpoint": 16,
                    "oracle_method": "minterm",
                    "num_vanishing_states": 4,
                    "sparsity": 0.50,
                    "balanced_score": 0.49,
                    "naive_oracle_terms": 4,
                    "oracle_gate_count": 12,
                    "benefit_cost_score": 1.1,
                },
                {
                    "checkpoint": 16,
                    "oracle_method": "simplified_boolean",
                    "num_vanishing_states": 4,
                    "sparsity": 0.50,
                    "balanced_score": 0.49,
                    "naive_oracle_terms": 4,
                    "oracle_gate_count": 1,
                    "benefit_cost_score": 1.2,
                },
                {
                    "checkpoint": 32,
                    "oracle_method": "minterm",
                    "num_vanishing_states": 7,
                    "sparsity": 0.875,
                    "balanced_score": 0.86,
                    "naive_oracle_terms": 7,
                    "oracle_gate_count": 55,
                    "benefit_cost_score": 0.7,
                },
                {
                    "checkpoint": 32,
                    "oracle_method": "simplified_boolean",
                    "num_vanishing_states": 7,
                    "sparsity": 0.875,
                    "balanced_score": 0.86,
                    "naive_oracle_terms": 7,
                    "oracle_gate_count": 14,
                    "benefit_cost_score": 0.6,
                },
            ]
        )

    def test_select_best_checkpoint_strategies(self) -> None:
        expected = {
            "max_sparsity": 32,
            "min_oracle_cost": 16,
            "balanced_proxy": 32,
            "cost_benefit": 16,
            "early_checkpoint": 8,
            "late_checkpoint": 32,
        }

        for strategy, checkpoint in expected.items():
            with self.subTest(strategy=strategy):
                row = select_best_checkpoint(self.results, strategy=strategy)
                self.assertEqual(row["checkpoint"], checkpoint)

    def test_checkpoint_only_strategies_choose_cheapest_method(self) -> None:
        for strategy in (
            "max_sparsity",
            "balanced_proxy",
            "early_checkpoint",
            "late_checkpoint",
        ):
            with self.subTest(strategy=strategy):
                row = select_best_checkpoint(self.results, strategy=strategy)
                self.assertEqual(row["oracle_method"], "simplified_boolean")

    def test_cost_strategies_select_global_candidate(self) -> None:
        min_cost = select_best_checkpoint(
            self.results,
            strategy="min_oracle_cost",
        )
        cost_benefit = select_best_checkpoint(
            self.results,
            strategy="cost_benefit",
        )

        self.assertEqual(min_cost["checkpoint"], 16)
        self.assertEqual(min_cost["oracle_method"], "simplified_boolean")
        self.assertEqual(cost_benefit["checkpoint"], 16)
        self.assertEqual(cost_benefit["oracle_method"], "simplified_boolean")

    def test_empty_results_raise(self) -> None:
        with self.assertRaises(ValueError):
            select_best_checkpoint(pd.DataFrame(), strategy="cost_benefit")

    def test_unknown_strategy_raises(self) -> None:
        with self.assertRaises(ValueError):
            select_best_checkpoint(self.results, strategy="unknown")


class QWalkScalingSuiteTests(unittest.TestCase):
    def test_benchmark_grid_matches_requested_suite(self) -> None:
        settings = benchmark_settings()
        suite = benchmark_suite_table()

        self.assertEqual(
            len(settings),
            len(DEFAULT_POSITION_QUBITS) * len(DEFAULT_WALK_STEPS),
        )
        self.assertEqual(
            sum(setting.steps for setting in settings),
            len(DEFAULT_POSITION_QUBITS) * sum(DEFAULT_WALK_STEPS),
        )
        self.assertEqual(list(suite["position_qubits"]), list(DEFAULT_POSITION_QUBITS))
        self.assertTrue(
            (
                suite["basis_states"]
                == suite["total_qubits"].map(lambda qubits: 2**qubits)
            ).all()
        )

    def test_scaling_candidates_include_required_metadata(self) -> None:
        candidates = scan_scaling_candidates(
            position_qubits=(2,),
            walk_steps=(2,),
            max_minterm_states=8,
        )
        required_columns = {
            "position_qubits",
            "total_qubits",
            "basis_states",
            "steps",
            "checkpoint_step",
            "num_vanishing_states",
            "coverage",
            "oracle_gate_count",
            "oracle_cx_count",
            "oracle_depth",
            "asserted_depth_overhead",
            "asserted_cx_overhead",
            "normalized_cost",
            "benefit_cost_score",
            "status",
        }

        self.assertTrue(required_columns.issubset(candidates.columns))
        self.assertEqual(len(candidates), 4)
        self.assertTrue((candidates["basis_states"] == 8).all())
        self.assertTrue((candidates["total_qubits"] == 3).all())
        self.assertTrue((candidates["status"] == "ok").all())

    def test_scaling_winners_select_one_row_per_strategy_per_setting(self) -> None:
        candidates = scan_scaling_candidates(
            position_qubits=(2,),
            walk_steps=(2, 4),
            max_minterm_states=8,
        )
        winners = select_scaling_strategy_winners(candidates)

        grouped = winners.groupby(["position_qubits", "steps", "strategy"]).size()
        self.assertTrue((grouped == 1).all())
        self.assertEqual(
            set(winners["strategy"]),
            set(DEFAULT_STRATEGIES),
        )
        self.assertEqual(len(winners), 2 * len(DEFAULT_STRATEGIES))

    def test_pareto_frontier_excludes_dominated_candidates(self) -> None:
        frame = pd.DataFrame(
            [
                {"coverage": 0.5, "asserted_cx_overhead": 10, "status": "ok"},
                {"coverage": 0.7, "asserted_cx_overhead": 8, "status": "ok"},
                {"coverage": 0.7, "asserted_cx_overhead": 12, "status": "ok"},
                {"coverage": 0.9, "asserted_cx_overhead": 20, "status": "ok"},
                {"coverage": 1.0, "asserted_cx_overhead": 1, "status": "error"},
            ]
        )
        frontier = pareto_frontier(frame)

        self.assertNotIn(2, set(frontier.index))
        self.assertNotIn(4, set(frontier.index))
        for _, row in frontier.iterrows():
            dominated = (
                (frontier["coverage"] >= row["coverage"])
                & (frontier["asserted_cx_overhead"] <= row["asserted_cx_overhead"])
                & (
                    (frontier["coverage"] > row["coverage"])
                    | (
                        frontier["asserted_cx_overhead"]
                        < row["asserted_cx_overhead"]
                    )
                )
            ).any()
            self.assertFalse(dominated)

    def test_scaling_output_path_is_probability_tagged(self) -> None:
        primary_path = scaling_output_path_for_run(
            error_probability=0.005,
            include_oracle_noise=False,
        )
        oracle_noise_path = scaling_output_path_for_run(
            error_probability=0.02,
            include_oracle_noise=True,
        )

        self.assertEqual(
            primary_path.name,
            "qwalk_scaling_strategy_evaluation_p0_005.csv",
        )
        self.assertEqual(
            oracle_noise_path.name,
            "qwalk_scaling_strategy_evaluation_oracle_noise_p0_02.csv",
        )


class QWalkEvaluationTests(unittest.TestCase):
    def test_cli_defaults(self) -> None:
        args = parse_args([])

        self.assertFalse(args.include_oracle_noise)
        self.assertEqual(args.error_probability, 0.01)
        self.assertEqual(args.num_trials, 1000)
        self.assertEqual(args.seed, 2026)

    def test_cli_accepts_num_trials_and_legacy_shots(self) -> None:
        args = parse_args(["--error-probability", "0", "--num-trials", "100"])
        legacy_args = parse_args(["--shots", "25"])

        self.assertEqual(args.error_probability, 0.0)
        self.assertEqual(args.num_trials, 100)
        self.assertEqual(legacy_args.num_trials, 25)

    def test_parameterized_output_path(self) -> None:
        primary_path = output_path_for_run(
            error_probability=0.0,
            include_oracle_noise=False,
        )
        oracle_noise_path = output_path_for_run(
            error_probability=0.01,
            include_oracle_noise=True,
        )

        self.assertEqual(primary_path.name, "qwalk_strategy_evaluation_p0_0.csv")
        self.assertEqual(
            oracle_noise_path.name,
            "qwalk_strategy_evaluation_oracle_noise_p0_01.csv",
        )

    def test_pauli_trace_generation_is_deterministic(self) -> None:
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        first = generate_pauli_error_traces(
            circuit=circuit,
            num_traces=5,
            error_probability=0.5,
            seed=123,
        )
        second = generate_pauli_error_traces(
            circuit=circuit,
            num_traces=5,
            error_probability=0.5,
            seed=123,
        )

        self.assertEqual(first, second)

    def test_pauli_trace_generation_can_be_shared(self) -> None:
        circuit = QuantumCircuit(1)
        circuit.h(0)

        traces = generate_pauli_error_traces(
            circuit=circuit,
            num_traces=3,
            error_probability=1.0,
            seed=2026,
        )

        self.assertIs(traces, traces)
        self.assertEqual(len(traces), 3)
        self.assertTrue(all(len(trace) == 1 for trace in traces))

    def test_qwalk_confusion_metrics(self) -> None:
        metrics = qwalk_confusion_metrics(
            [
                (True, False),
                (False, True),
                (True, True),
                (False, False),
                (True, False),
            ]
        )

        self.assertEqual(metrics["TP"], 2)
        self.assertEqual(metrics["TN"], 1)
        self.assertEqual(metrics["FP"], 1)
        self.assertEqual(metrics["FN"], 1)
        self.assertAlmostEqual(metrics["Detection Rate"], 2 / 3)
        self.assertAlmostEqual(metrics["Support-Level FPR"], 1 / 2)
        self.assertAlmostEqual(
            metrics["Post-selected Support-Valid Rate"],
            1 / 2,
        )

    def test_checkpoint_oracles_do_not_flag_ideal_prefixes(self) -> None:
        quantum_walk = build_cycle_quantum_walk(
            num_position_qubits=2,
            num_steps=5,
        )

        for checkpoint, label in zip(
            quantum_walk.checkpoints,
            quantum_walk.checkpoint_labels,
        ):
            analysis = analyze_checkpoint(
                circuit=quantum_walk.circuit,
                checkpoint=checkpoint,
            )
            spec = VanishingAssertionSpec(
                num_asserted_qubits=quantum_walk.circuit.num_qubits,
                vanishing_states=tuple(analysis.vanishing_states),
                description=label,
            )

            for method in ("minterm", "simplified_boolean"):
                with self.subTest(label=label, method=method):
                    oracle = synthesize_vanishing_oracle(
                        spec=spec,
                        method=method,
                    )

                    self.assertAlmostEqual(
                        assertion_probability_for_ideal_prefix(
                            circuit=quantum_walk.circuit,
                            checkpoint=checkpoint,
                            oracle=oracle,
                        ),
                        0.0,
                    )

    def test_noiseless_strategy_evaluation_has_no_false_positives(self) -> None:
        results = run_evaluation(
            shots=10,
            error_probability=0.0,
            seed=1234,
        )

        self.assertTrue((results["FP"] == 0).all())
        self.assertTrue((results["FN"] == 0).all())
        self.assertTrue((results["Detection Rate"] == 0.0).all())
        self.assertTrue((results["Support-Level FPR"] == 0.0).all())
        self.assertTrue(
            (results["Post-selected Support-Valid Rate"] == 1.0).all()
        )

    def test_strategy_evaluation_output_columns(self) -> None:
        results = run_evaluation(
            shots=2,
            error_probability=0.0,
            seed=1234,
        )

        self.assertEqual(list(results.columns), PUBLIC_COLUMNS)

    def test_duplicate_candidates_reuse_evaluation_metrics(self) -> None:
        results = run_evaluation(
            shots=4,
            error_probability=0.01,
            seed=1234,
        )
        metric_columns = [
            "TP",
            "TN",
            "FP",
            "FN",
            "Detection Rate",
            "Support-Level FPR",
            "Post-selected Support-Valid Rate",
        ]

        duplicate_group_count = 0
        for _, group in results.groupby(["Checkpoint", "Oracle Method"]):
            if len(group) < 2:
                continue

            duplicate_group_count += 1
            first_metrics = group.iloc[0][metric_columns].to_dict()
            for _, row in group.iloc[1:].iterrows():
                self.assertEqual(
                    row[metric_columns].to_dict(),
                    first_metrics,
                )

        self.assertGreater(duplicate_group_count, 0)


if __name__ == "__main__":
    unittest.main()
