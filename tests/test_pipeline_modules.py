from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import stim

from qec_pipeline.analysis.metrics import binomial_standard_error
from qec_pipeline.analysis.reports import write_run_artifacts
from qec_pipeline.backends.simulator import run_simulator_backend
from qec_pipeline.codes.color_code import build_color_code_circuit
from qec_pipeline.codes.surface_code import build_surface_code_circuit
from qec_pipeline.config import config_summary, load_experiment_config
from qec_pipeline.decoders.gnn_decoder import decode_with_gnn
from qec_pipeline.decoders.ising_decoder import decode_with_ising
from qec_pipeline.decoders.observable_decoder import decode_observable_rate
from qec_pipeline.decoders.pymatching_decoder import decode_with_pymatching
from qec_pipeline.measurements import counts_to_measurement_array
from qec_pipeline.pipeline import describe_pipeline, run_pipeline
from qec_pipeline.syndrome_extraction import extract_syndromes


NO_NOISE = {"model": "no_noise", "parameters": {}}
SURFACE_D2_R1 = {
    "family": "surface_code",
    "distance": 2,
    "rounds": 1,
    "basis": "memory_z",
    "reset_mode": "reset",
}


class ConfigTests(unittest.TestCase):
    def test_load_config_and_summary(self) -> None:
        config_path = Path("configs/demo_stim_no_noise.yaml")

        config = load_experiment_config(config_path)

        self.assertEqual(config["experiment"]["name"], "demo_stim_no_noise")
        self.assertIn("backend: simulator", config_summary(config))

    def test_missing_config_section_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "bad.yaml"
            config_path.write_text("experiment:\n  name: bad\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Missing config section"):
                load_experiment_config(config_path)


class MeasurementTests(unittest.TestCase):
    def test_counts_to_measurement_array_uses_clbit_order(self) -> None:
        measurements = counts_to_measurement_array(
            counts={"10": 2, "01": 1},
            num_measurements=2,
            total_shots=3,
        )

        expected = np.array(
            [
                [False, True],
                [False, True],
                [True, False],
            ],
            dtype=bool,
        )
        np.testing.assert_array_equal(measurements, expected)

    def test_counts_to_measurement_array_checks_shot_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected 3"):
            counts_to_measurement_array({"0": 2}, num_measurements=1, total_shots=3)


class CircuitAndBackendTests(unittest.TestCase):
    def test_surface_code_builder_returns_consistent_metadata(self) -> None:
        stim_circuit, detector_model, measurement_order, info = build_surface_code_circuit(
            SURFACE_D2_R1,
            NO_NOISE,
            "memory_z",
        )

        self.assertEqual(info["basis"], "memory_z")
        self.assertEqual(info["num_measurements"], stim_circuit.num_measurements)
        self.assertEqual(info["num_detectors"], stim_circuit.num_detectors)
        self.assertEqual(len(measurement_order), stim_circuit.num_measurements)
        self.assertEqual(detector_model.num_detectors, stim_circuit.num_detectors)

    def test_simple_noise_adds_stim_noise_instructions(self) -> None:
        noise = {
            "model": "simple_depolarizing",
            "parameters": {
                "one_qubit_error": 0.01,
                "measurement_error": 0.02,
                "reset_error": 0.03,
                "idle_error": 0.04,
            },
        }

        stim_circuit, _detector_model, _measurement_order, _info = build_surface_code_circuit(
            SURFACE_D2_R1,
            noise,
            "memory_z",
        )

        circuit_text = str(stim_circuit)
        self.assertIn("DEPOLARIZE1", circuit_text)
        self.assertIn("X_ERROR", circuit_text)

    def test_simulator_backend_returns_raw_measurement_matrix(self) -> None:
        stim_circuit = stim.Circuit("R 0\nM 0")
        circuit = (stim_circuit, None, (0,), {"basis": "unit"})
        backend = {"name": "simulator", "shots": 5, "options": {"seed": 1}}

        measurements, counts, raw_info = run_simulator_backend(backend, circuit)

        self.assertIsNone(counts)
        self.assertEqual(measurements.shape, (5, 1))
        self.assertEqual(raw_info["shape"], (5, 1))


class SyndromeTests(unittest.TestCase):
    def test_extract_syndromes_returns_detector_events_and_observables(self) -> None:
        stim_circuit = stim.Circuit(
            """
            R 0
            X 0
            M 0
            DETECTOR rec[-1]
            OBSERVABLE_INCLUDE(0) rec[-1]
            """
        )
        raw_measurements = np.zeros((4, 1), dtype=bool)

        result = extract_syndromes(raw_measurements, stim_circuit)

        np.testing.assert_array_equal(result["det_events"], np.ones((4, 1), dtype=bool))
        np.testing.assert_array_equal(result["obs_flips"], np.ones((4, 1), dtype=bool))
        self.assertEqual(result["num_detectors"], 1)
        self.assertEqual(result["num_shots"], 4)


class DecoderTests(unittest.TestCase):
    def test_observable_rate_decoder_counts_any_observable_flip(self) -> None:
        circuit = (None, None, None, {"num_observables": 2})
        syndromes = (
            np.zeros((3, 1), dtype=bool),
            np.array([[False, False], [True, False], [False, True]], dtype=bool),
            {},
        )

        _predicted, failures, ler, uncertainty, info = decode_observable_rate(
            {"name": "observable_rate"},
            circuit,
            syndromes,
        )

        self.assertEqual(failures, [False, True, True])
        self.assertEqual(ler, 2 / 3)
        self.assertAlmostEqual(uncertainty, binomial_standard_error(2 / 3, 3))
        self.assertEqual(info["logical_failures"], 2)

    def test_pymatching_decoder_corrects_simple_detector_observable_pair(self) -> None:
        stim_circuit = stim.Circuit(
            """
            X_ERROR(0.1) 0
            M 0
            DETECTOR rec[-1]
            OBSERVABLE_INCLUDE(0) rec[-1]
            """
        )
        detector_model = stim_circuit.detector_error_model(decompose_errors=True)
        circuit = (
            stim_circuit,
            detector_model,
            (0,),
            {"basis": "unit", "num_observables": 1},
        )
        syndromes = (
            np.array([[False], [True]], dtype=bool),
            np.array([[False], [True]], dtype=bool),
            {},
        )

        _predicted, failures, ler, _uncertainty, info = decode_with_pymatching(
            {"name": "pymatching"},
            circuit,
            syndromes,
        )

        np.testing.assert_array_equal(failures, np.array([False, False], dtype=bool))
        self.assertEqual(ler, 0.0)
        self.assertEqual(info["logical_failures"], 0)

    def test_placeholder_modules_fail_clearly(self) -> None:
        with self.assertRaisesRegex(NotImplementedError, "color-code"):
            build_color_code_circuit({}, {}, "memory_z")
        with self.assertRaisesRegex(NotImplementedError, "GNN"):
            decode_with_gnn({}, (), ())
        with self.assertRaisesRegex(NotImplementedError, "NVIDIA Ising"):
            decode_with_ising({}, (), ())


class ReportingAndPipelineTests(unittest.TestCase):
    def test_write_run_artifacts_writes_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            stim_circuit = stim.Circuit("R 0\nM 0")
            circuit = (
                stim_circuit,
                None,
                (0,),
                {
                    "basis": "unit",
                    "num_qubits": 1,
                    "num_measurements": 1,
                    "num_detectors": 0,
                    "num_observables": 0,
                },
            )
            raw = (
                np.zeros((2, 1), dtype=bool),
                {"0": 2},
                {"backend": "unit", "qiskit_circuit_text": "qc"},
            )
            syndromes = (
                np.zeros((2, 0), dtype=bool),
                np.zeros((2, 0), dtype=bool),
                {"shots": 2},
            )
            metrics = {"basis": "unit", "ler": 0.0, "uncertainty": 0.0}

            write_run_artifacts(run_dir, circuit, raw, syndromes, metrics)

            self.assertTrue((run_dir / "circuit.stim").exists())
            self.assertTrue((run_dir / "metrics.json").exists())
            self.assertTrue((run_dir / "counts.json").exists())
            self.assertTrue((run_dir / "qiskit_circuit.txt").exists())
            metrics_json = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics_json["ler"], 0.0)

    def test_run_pipeline_no_noise_memory_z(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "experiment": {"name": "unit_pipeline", "description": "", "seed": 1},
                "code": {
                    "family": "surface_code",
                    "distance": 2,
                    "rounds": 1,
                    "basis": "memory_z",
                    "reset_mode": "reset",
                },
                "backend": {"name": "simulator", "shots": 8, "options": {"seed": 1}},
                "noise": NO_NOISE,
                "decoder": {"name": "pymatching", "options": {}},
                "mapping": {"strategy": "none", "hardware_patch": None},
                "artifacts": {"root": temp_dir},
            }

            run_dir, basis_results, notes = run_pipeline(config)

            self.assertEqual(len(basis_results), 1)
            self.assertIn("memory_z", notes[0])
            self.assertTrue((run_dir / "summary.md").exists())
            self.assertTrue((run_dir / "memory_z" / "metrics.json").exists())

    def test_describe_pipeline_mentions_selected_basis(self) -> None:
        config = {
            "code": {"basis": "both"},
        }

        plan = describe_pipeline(config)

        self.assertIn("memory_z, memory_x", "\n".join(plan))


if __name__ == "__main__":
    unittest.main()
