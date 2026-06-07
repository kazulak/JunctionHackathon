from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import stim

from qec_pipeline.analysis.metrics import binomial_standard_error
from qec_pipeline.analysis.measurement_diagnostics import build_measurement_diagnostics
from qec_pipeline.analysis.reports import write_run_artifacts
from qec_pipeline.analysis.diagnostics import build_run_diagnostics
from qec_pipeline.backends import get_backend_runner
from qec_pipeline.backends.simulator import run_simulator_backend
from qec_pipeline.codes import get_code_builder
from qec_pipeline.codes.color_code import build_color_code_circuit
from qec_pipeline.codes.surface_code_iqm import build_iqm_surface_code_circuit
from qec_pipeline.codes.surface_code import build_surface_code_circuit
from qec_pipeline.codes.surface_code_unrotated import build_unrotated_surface_code_circuit
from qec_pipeline.config import config_summary, load_experiment_config
from qec_pipeline.decoders import get_decoder
from qec_pipeline.decoders.gnn_decoder import decode_with_gnn
from qec_pipeline.decoders.ising_decoder import decode_with_ising
from qec_pipeline.decoders.observable_decoder import decode_observable_rate
from qec_pipeline.decoders.pymatching_calibrated_decoder import decode_with_calibrated_pymatching
from qec_pipeline.decoders.pymatching_decoder import (
    detector_model_with_uniform_noise,
    decode_with_pymatching,
    pymatching_noise_sweep,
)
from qec_pipeline.circuit_preparation import prepare_circuit_for_execution
from qec_pipeline.measurements import counts_to_measurement_array, virtualize_omitted_repeated_resets
from qec_pipeline.mapping.patch_selection import (
    select_calibration_best_patch,
    select_calibration_routed_layout,
    select_mapping_from_config,
    rank_calibration_best_patches,
    surface_code_patch_coordinates,
)
from qec_pipeline.pipeline import describe_pipeline, run_pipeline
from qec_pipeline.syndrome_extraction import extract_syndromes
from qec_pipeline.sweeps import round_values, run_rounds_sweep


NO_NOISE = {"model": "no_noise", "parameters": {}}
SURFACE_D3_R1 = {
    "family": "surface_code",
    "distance": 3,
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


class RegistryTests(unittest.TestCase):
    def test_pipeline_registries_return_known_modules(self) -> None:
        self.assertIs(get_code_builder("surface_code"), build_surface_code_circuit)
        self.assertIs(get_code_builder("surface_code_iqm"), build_iqm_surface_code_circuit)
        self.assertIs(get_code_builder("surface_code_unrotated"), build_unrotated_surface_code_circuit)
        self.assertIs(get_decoder("pymatching"), decode_with_pymatching)
        self.assertIs(get_decoder("pymatching_calibrated"), decode_with_calibrated_pymatching)
        self.assertIs(get_backend_runner("simulator"), run_simulator_backend)

    def test_pipeline_registries_fail_with_available_names(self) -> None:
        with self.assertRaisesRegex(ValueError, "Available"):
            get_code_builder("missing_code")
        with self.assertRaisesRegex(ValueError, "Available"):
            get_decoder("missing_decoder")
        with self.assertRaisesRegex(ValueError, "Available"):
            get_backend_runner("missing_backend")


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

    def test_virtualize_omitted_repeated_resets_xors_previous_measurement(self) -> None:
        measurements = np.array(
            [
                [False, True, True, True],
                [True, True, False, False],
            ],
            dtype=bool,
        )

        virtual = virtualize_omitted_repeated_resets(
            measurements,
            measurement_order=[2, 5, 2, 5],
        )

        expected = np.array(
            [
                [False, True, True, False],
                [True, True, True, True],
            ],
            dtype=bool,
        )
        np.testing.assert_array_equal(virtual, expected)


class CircuitAndBackendTests(unittest.TestCase):
    def test_surface_code_builder_returns_consistent_metadata(self) -> None:
        stim_circuit, detector_model, measurement_order, info = build_surface_code_circuit(
            SURFACE_D3_R1,
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
            SURFACE_D3_R1,
            noise,
            "memory_z",
        )

        circuit_text = str(stim_circuit)
        self.assertIn("DEPOLARIZE1", circuit_text)
        self.assertIn("X_ERROR", circuit_text)

    def test_no_reset_falls_back_to_active_reset_with_warning(self) -> None:
        code = dict(SURFACE_D3_R1)
        code["reset_mode"] = "no_reset"

        with self.assertWarnsRegex(RuntimeWarning, "Falling back"):
            _stim_circuit, _detector_model, _measurement_order, info = build_surface_code_circuit(
                code,
                NO_NOISE,
                "memory_z",
            )

        self.assertEqual(info["implemented_reset_mode"], "active_reset")
        self.assertTrue(info["forced_active_reset"])

    def test_simulator_backend_returns_raw_measurement_matrix(self) -> None:
        stim_circuit = stim.Circuit("R 0\nM 0")
        circuit = (stim_circuit, None, (0,), {"basis": "unit"})
        backend = {"name": "simulator", "shots": 5, "options": {"seed": 1}}

        measurements, counts, raw_info = run_simulator_backend(backend, circuit)

        self.assertIsNone(counts)
        self.assertEqual(measurements.shape, (5, 1))
        self.assertEqual(raw_info["shape"], (5, 1))

    def test_iqm_surface_code_builder_starts_clean_for_calibrated_noise(self) -> None:
        stim_circuit, _detector_model, _measurement_order, info = build_iqm_surface_code_circuit(
            {"family": "surface_code_iqm", "distance": 3, "rounds": 1, "reset_mode": "reset"},
            {"model": "iqm_calibration"},
            "memory_z",
        )

        self.assertNotIn("DEPOLARIZE", str(stim_circuit))
        self.assertEqual(info["surface_code_variant"], "rotated_iqm_calibration_first")
        self.assertEqual(info["noise_model"], "iqm_calibration")

    def test_unrotated_surface_code_builder_is_selectable(self) -> None:
        stim_circuit, detector_model, measurement_order, info = build_unrotated_surface_code_circuit(
            {"family": "surface_code_unrotated", "distance": 3, "rounds": 1, "reset_mode": "reset"},
            NO_NOISE,
            "memory_z",
        )

        self.assertIn("unrotated_memory_z", info["stim_task"])
        self.assertEqual(len(measurement_order), stim_circuit.num_measurements)
        self.assertEqual(detector_model.num_detectors, stim_circuit.num_detectors)


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

    def test_calibrated_pymatching_reports_calibration_model(self) -> None:
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
            {
                "basis": "unit",
                "num_observables": 1,
                "noise_model": "iqm_calibration",
                "implemented_noise_model": "iqm_calibration_per_qubit",
            },
        )
        syndromes = (
            np.array([[False], [True]], dtype=bool),
            np.array([[False], [True]], dtype=bool),
            {},
        )

        _predicted, failures, ler, _uncertainty, info = decode_with_calibrated_pymatching(
            {"name": "pymatching_calibrated"},
            circuit,
            syndromes,
        )

        np.testing.assert_array_equal(failures, np.array([False, False], dtype=bool))
        self.assertEqual(ler, 0.0)
        self.assertEqual(info["implemented_noise_model"], "iqm_calibration_per_qubit")

    def test_pymatching_noise_sweep_reports_ler_per_probability(self) -> None:
        stim_circuit = stim.Circuit(
            """
            X_ERROR(0.1) 0
            M 0
            DETECTOR rec[-1]
            OBSERVABLE_INCLUDE(0) rec[-1]
            """
        )
        detection_events = np.array([[False], [True]], dtype=bool)
        observable_flips = np.array([[False], [True]], dtype=bool)

        rows = pymatching_noise_sweep(
            stim_circuit,
            detection_events,
            observable_flips,
            probabilities=[0.01, 0.1],
        )
        detector_model = detector_model_with_uniform_noise(stim_circuit, 0.2)

        self.assertEqual([row["probability"] for row in rows], [0.01, 0.1])
        self.assertEqual(rows[0]["ler"], 0.0)
        self.assertEqual(detector_model.num_detectors, 1)

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
            self.assertTrue((run_dir / "measurement_diagnostics.json").exists())
            metrics_json = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics_json["ler"], 0.0)

    def test_run_pipeline_no_noise_memory_z(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "experiment": {"name": "unit_pipeline", "description": "", "seed": 1},
                "code": {
                    "family": "surface_code",
                    "distance": 3,
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
            self.assertTrue((run_dir / "memory_z" / "diagnostics.json").exists())

    def test_describe_pipeline_mentions_selected_basis(self) -> None:
        config = {
            "code": {"basis": "both"},
            "mapping": {"strategy": "none"},
        }

        plan = describe_pipeline(config)

        self.assertIn("memory_z, memory_x", "\n".join(plan))

    def test_describe_pipeline_mentions_calibration_patch_mapping(self) -> None:
        config = {
            "code": {"basis": "memory_z"},
            "mapping": {"strategy": "calibration_best_patch"},
        }

        plan = describe_pipeline(config)

        self.assertIn("select native patch", "\n".join(plan))

    def test_describe_pipeline_mentions_routed_mapping(self) -> None:
        config = {
            "code": {"basis": "memory_z"},
            "mapping": {"strategy": "calibration_routed_layout"},
        }

        plan = describe_pipeline(config)

        self.assertIn("select routed layout", "\n".join(plan))

    def test_color_code_pipeline_path_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "experiment": {"name": "unit_pipeline", "description": "", "seed": 1},
                "code": {
                    "family": "color_code",
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

            with self.assertRaisesRegex(NotImplementedError, "color-code"):
                run_pipeline(config)

    def test_calibrated_simulator_pipeline_uses_qubit_level_noise(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            calibration_path = Path(temp_dir) / "calibration.yaml"
            calibration_path.write_text(
                yaml_dump(_grid_calibration(rows=6, cols=6, low_origin=(1, 1), low_size=5)),
                encoding="utf-8",
            )
            config = {
                "experiment": {"name": "unit_calibrated_sim", "description": "", "seed": 1},
                "code": {
                    "family": "surface_code_iqm",
                    "distance": 3,
                    "rounds": 1,
                    "basis": "memory_z",
                    "reset_mode": "reset",
                },
                "backend": {"name": "simulator", "shots": 16, "options": {"seed": 1}},
                "noise": {
                    "model": "iqm_calibration",
                    "calibration_file": str(calibration_path),
                    "options": {"apply_idle": True, "qnd_scale": 0.0, "idle_scale": 0.5},
                },
                "decoder": {"name": "pymatching_calibrated", "options": {}},
                "mapping": {
                    "strategy": "calibration_best_patch",
                    "calibration_file": str(calibration_path),
                    "hardware_patch": None,
                    "weights": {"one_qubit": 1.0, "two_qubit": 1.0, "measurement": 1.0},
                },
                "artifacts": {"root": temp_dir},
            }

            run_dir, basis_results, _notes = run_pipeline(config)

            _basis, circuit, raw, _syndromes, decoded, _metrics = basis_results[0]
            stim_circuit, detector_model, _measurement_order, circuit_info = circuit
            _measurements, _counts, raw_info = raw
            _predicted, _failures, _ler, _uncertainty, decoder_info = decoded

            self.assertIn("DEPOLARIZE", str(stim_circuit))
            self.assertGreater(circuit_info["detector_model_num_errors"], 0)
            self.assertEqual(circuit_info["implemented_noise_model"], "iqm_calibration_per_qubit")
            self.assertEqual(circuit_info["calibration_noise"]["error_scales"]["qnd"], 0.0)
            self.assertEqual(circuit_info["calibration_noise"]["error_scales"]["idle"], 0.5)
            self.assertEqual(raw_info["implemented_noise_model"], "iqm_calibration_per_qubit")
            self.assertEqual(decoder_info["implemented_noise_model"], "iqm_calibration_per_qubit")
            self.assertTrue((run_dir / "memory_z" / "circuit_metadata.json").exists())

    def test_prepare_circuit_requires_mapping_for_calibrated_noise(self) -> None:
        circuit = build_iqm_surface_code_circuit(
            {"family": "surface_code_iqm", "distance": 3, "rounds": 1, "reset_mode": "reset"},
            {"model": "iqm_calibration"},
            "memory_z",
        )
        config = {
            "noise": {"model": "iqm_calibration", "calibration_file": "missing.yaml"},
            "mapping": {"strategy": "none"},
        }

        with self.assertRaisesRegex(ValueError, "requires a selected mapping"):
            prepare_circuit_for_execution(config, circuit)

    def test_iqm_pipeline_batches_both_bases_before_decoding(self) -> None:
        def fake_batch(_backend: dict, requests: list[dict]) -> list[tuple]:
            raws = []
            for request in requests:
                stim_circuit = request["circuit"][0]
                measurements = np.zeros((4, stim_circuit.num_measurements), dtype=bool)
                raws.append(
                    (
                        measurements,
                        None,
                        {
                            "backend": "iqm_hardware",
                            "shots": 4,
                            "shape": tuple(measurements.shape),
                            "batch_size": len(requests),
                        },
                    )
                )
            return raws

        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "experiment": {"name": "unit_iqm_batch", "description": "", "seed": 1},
                "code": {
                    "family": "surface_code",
                    "distance": 3,
                    "rounds": 1,
                    "basis": "both",
                    "reset_mode": "reset",
                },
                "backend": {
                    "name": "iqm_hardware",
                    "shots": 4,
                    "options": {"batch_submit": True},
                },
                "noise": NO_NOISE,
                "decoder": {"name": "pymatching", "options": {}},
                "mapping": {"strategy": "none", "hardware_patch": None},
                "artifacts": {"root": temp_dir},
            }

            with patch(
                "qec_pipeline.pipeline.run_iqm_hardware_batch_backend",
                side_effect=fake_batch,
            ) as batch_mock:
                _run_dir, basis_results, _notes = run_pipeline(config)

        self.assertEqual(len(basis_results), 2)
        self.assertEqual(batch_mock.call_count, 1)
        self.assertEqual(len(batch_mock.call_args.args[1]), 2)


class DiagnosticAndSweepTests(unittest.TestCase):
    def test_measurement_diagnostics_flags_unexpected_deterministic_measurements(self) -> None:
        stim_circuit = stim.Circuit("R 0\nM 0")
        measurements = np.ones((5, 1), dtype=bool)
        raw_info = {"meas_order": [0], "mapping": {"stim_to_hardware": {"0": "QB1"}}}

        rows = build_measurement_diagnostics(stim_circuit, measurements, raw_info)

        self.assertEqual(rows[0]["measurement_index"], 0)
        self.assertEqual(rows[0]["stim_qubit"], 0)
        self.assertEqual(rows[0]["hardware_qubit"], "QB1")
        self.assertEqual(rows[0]["deterministic_value"], 0)
        self.assertEqual(rows[0]["unexpected_rate"], 1.0)

    def test_diagnostics_warn_on_saturated_run(self) -> None:
        diagnostics = build_run_diagnostics(
            circuit_info={"num_measurements": 10, "num_qubits": 5},
            raw_info={
                "qiskit_depth": 25,
                "transpiled_depth": 592,
                "transpiled_ops": {"cz": 1410},
            },
            syndrome_info={
                "num_detectors": 4,
                "detector_firing_rate": np.array([0.45, 0.5, 0.55, 0.49]),
                "mean_syndrome_weight": 2.0,
                "observable_flip_rate": np.array([0.5]),
            },
            metrics={"basis": "memory_z", "ler": 0.51, "uncertainty": 0.02},
        )

        self.assertGreaterEqual(len(diagnostics["warnings"]), 3)
        self.assertEqual(diagnostics["two_qubit_ops_after_transpile"], 1410)

    def test_round_values_are_inclusive_and_unique(self) -> None:
        self.assertEqual(round_values(3, 15, 6), [3, 5, 8, 10, 13, 15])

        with self.assertRaisesRegex(ValueError, "duplicate"):
            round_values(1, 2, 5)

    def test_rounds_sweep_writes_csv_json_plot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "experiment": {"name": "unit_sweep", "description": "", "seed": 1},
                "code": {
                    "family": "surface_code",
                    "distance": 3,
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

            sweep_dir = run_rounds_sweep(
                config,
                rounds=[1, 2],
                output_root=Path(temp_dir),
            )

            self.assertTrue((sweep_dir / "sweep_results.csv").exists())
            self.assertTrue((sweep_dir / "sweep_results.json").exists())
            self.assertTrue((sweep_dir / "ler_vs_rounds.png").exists())
            self.assertTrue((sweep_dir / "summary.md").exists())


class PatchSelectionTests(unittest.TestCase):
    def test_surface_code_patch_coordinates_match_rotated_patch_size(self) -> None:
        code = {
            "family": "surface_code",
            "distance": 3,
            "rounds": 1,
            "basis": "memory_z",
            "reset_mode": "reset",
        }
        stim_circuit, _detector_model, _measurement_order, _info = build_surface_code_circuit(
            code,
            NO_NOISE,
            "memory_z",
        )
        stim_to_dense = _stim_to_dense(stim_circuit)

        patch_coords = surface_code_patch_coordinates(stim_circuit, stim_to_dense)

        self.assertEqual(len(patch_coords), 17)
        self.assertEqual(max(row for row, _col in patch_coords.values()), 4)
        self.assertEqual(max(col for _row, col in patch_coords.values()), 4)

    def test_select_calibration_best_patch_uses_spatial_error_data(self) -> None:
        code = {
            "family": "surface_code",
            "distance": 3,
            "rounds": 1,
            "basis": "memory_z",
            "reset_mode": "reset",
        }
        stim_circuit, _detector_model, _measurement_order, _info = build_surface_code_circuit(
            code,
            NO_NOISE,
            "memory_z",
        )
        stim_to_dense = _stim_to_dense(stim_circuit)
        calibration = _grid_calibration(rows=6, cols=6, low_origin=(1, 1), low_size=5)

        selected = select_calibration_best_patch(stim_circuit, stim_to_dense, calibration)

        self.assertEqual(selected["origin"], {"row": 1, "col": 1})
        self.assertEqual(len(selected["initial_layout"]), len(stim_to_dense))
        self.assertGreaterEqual(selected["num_candidates"], 2)

    def test_rank_calibration_best_patches_returns_sorted_candidates(self) -> None:
        code = {
            "family": "surface_code",
            "distance": 3,
            "rounds": 1,
            "basis": "memory_z",
            "reset_mode": "reset",
        }
        stim_circuit, _detector_model, _measurement_order, _info = build_surface_code_circuit(
            code,
            NO_NOISE,
            "memory_z",
        )
        stim_to_dense = _stim_to_dense(stim_circuit)
        calibration = _grid_calibration(rows=6, cols=6, low_origin=(1, 1), low_size=5)

        candidates = rank_calibration_best_patches(stim_circuit, stim_to_dense, calibration)

        scores = [candidate["score"] for candidate in candidates]
        self.assertGreaterEqual(len(candidates), 2)
        self.assertEqual(scores, sorted(scores))

    def test_select_mapping_from_config_reads_calibration_file(self) -> None:
        code = {
            "family": "surface_code",
            "distance": 3,
            "rounds": 1,
            "basis": "memory_z",
            "reset_mode": "reset",
        }
        stim_circuit, _detector_model, _measurement_order, _info = build_surface_code_circuit(
            code,
            NO_NOISE,
            "memory_z",
        )
        stim_to_dense = _stim_to_dense(stim_circuit)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.yaml"
            path.write_text(
                yaml_dump(_grid_calibration(rows=6, cols=6, low_origin=(1, 1), low_size=5)),
                encoding="utf-8",
            )

            selected = select_mapping_from_config(
                {"strategy": "calibration_best_patch", "calibration_file": str(path)},
                stim_circuit,
                stim_to_dense,
            )

        self.assertEqual(selected["origin"], {"row": 1, "col": 1})

    def test_select_mapping_from_config_uses_fixed_stim_hardware_patch(self) -> None:
        stim_circuit = stim.Circuit(
            """
            QUBIT_COORDS(0, 0) 0
            QUBIT_COORDS(2, 0) 1
            CX 0 1
            M 0 1
            """
        )
        stim_to_dense = {0: 0, 1: 1}
        calibration = {
            "dut_label": "fake_iqm_fixed",
            "observations": [
                {"dut_field": "metrics.rb.clifford.xy_sx.QB1.fidelity:par=d2", "value": 0.99},
                {"dut_field": "metrics.rb.clifford.xy_sx.QB2.fidelity:par=d2", "value": 0.99},
                {"dut_field": "metrics.irb.cz.slepian_crf.QB1__QB2.fidelity:par=d2", "value": 0.98},
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.yaml"
            path.write_text(yaml_dump(calibration), encoding="utf-8")

            selected = select_mapping_from_config(
                {
                    "strategy": "calibration_best_patch",
                    "calibration_file": str(path),
                    "hardware_patch": {
                        "stim_to_hardware": {
                            "0": "QB2",
                            "1": "QB1",
                        }
                    },
                },
                stim_circuit,
                stim_to_dense,
            )

        self.assertEqual(selected["selection"], "fixed_stim_to_hardware")
        self.assertEqual(selected["initial_layout"], [1, 0])
        self.assertEqual(selected["stim_to_hardware"], {"0": "QB2", "1": "QB1"})

    def test_select_calibration_best_patch_reads_iqm_observation_graph(self) -> None:
        stim_circuit = stim.Circuit(
            """
            QUBIT_COORDS(0, 0) 0
            QUBIT_COORDS(2, 0) 1
            QUBIT_COORDS(4, 0) 2
            CX 0 1
            CX 1 2
            M 0 1 2
            """
        )
        stim_to_dense = {0: 0, 1: 1, 2: 2}
        calibration = {
            "dut_label": "fake_iqm",
            "observations": [
                {"dut_field": "metrics.rb.clifford.xy_sx.QB1.fidelity:par=d2", "value": 0.99},
                {"dut_field": "metrics.rb.clifford.xy_sx.QB2.fidelity:par=d2", "value": 0.99},
                {"dut_field": "metrics.rb.clifford.xy_sx.QB3.fidelity:par=d2", "value": 0.99},
                {"dut_field": "metrics.ssro.measure.constant.QB1.error_0_to_1", "value": 0.01},
                {"dut_field": "metrics.ssro.measure.constant.QB2.error_0_to_1", "value": 0.01},
                {"dut_field": "metrics.ssro.measure.constant.QB3.error_0_to_1", "value": 0.01},
                {"dut_field": "metrics.irb.cz.slepian_crf.QB1__QB2.fidelity:par=d2", "value": 0.98},
                {"dut_field": "metrics.irb.cz.slepian_crf.QB2__QB3.fidelity:par=d2", "value": 0.98},
            ],
        }

        selected = select_calibration_best_patch(stim_circuit, stim_to_dense, calibration)

        self.assertEqual(selected["qpu"], "fake_iqm")
        self.assertEqual(selected["selection"], "native_graph")
        self.assertEqual(selected["source_schema"], "iqm_observation_set")
        self.assertEqual(len(selected["initial_layout"]), 3)
        self.assertEqual(selected["data_hardware"], ["QB1", "QB2", "QB3"])
        self.assertEqual(selected["ancilla_hardware"], [])
        self.assertGreaterEqual(selected["num_candidates"], 1)

    def test_select_calibration_routed_layout_allows_non_native_edges(self) -> None:
        stim_circuit = stim.Circuit(
            """
            QUBIT_COORDS(0, 0) 0
            QUBIT_COORDS(2, 0) 1
            QUBIT_COORDS(1, 2) 2
            CX 0 1
            CX 1 2
            CX 0 2
            M 0 1 2
            """
        )
        stim_to_dense = {0: 0, 1: 1, 2: 2}
        calibration = {
            "dut_label": "fake_iqm_path",
            "observations": [
                {"dut_field": "metrics.rb.clifford.xy_sx.QB1.fidelity:par=d2", "value": 0.99},
                {"dut_field": "metrics.rb.clifford.xy_sx.QB2.fidelity:par=d2", "value": 0.99},
                {"dut_field": "metrics.rb.clifford.xy_sx.QB3.fidelity:par=d2", "value": 0.99},
                {"dut_field": "metrics.irb.cz.slepian_crf.QB1__QB2.fidelity:par=d2", "value": 0.98},
                {"dut_field": "metrics.irb.cz.slepian_crf.QB2__QB3.fidelity:par=d2", "value": 0.98},
            ],
        }

        selected = select_calibration_routed_layout(
            stim_circuit,
            stim_to_dense,
            calibration,
            options={"seed": 1, "max_iterations": 100},
        )

        self.assertEqual(selected["strategy"], "calibration_routed_layout")
        self.assertEqual(selected["selection"], "routed_graph")
        self.assertEqual(len(selected["initial_layout"]), 3)
        self.assertEqual(selected["routing"]["routed_code_edges"], 1)

    def test_select_calibration_routed_layout_respects_excluded_qubits(self) -> None:
        stim_circuit = stim.Circuit(
            """
            QUBIT_COORDS(0, 0) 0
            QUBIT_COORDS(2, 0) 1
            CX 0 1
            M 0 1
            """
        )
        stim_to_dense = {0: 0, 1: 1}
        calibration = {
            "dut_label": "fake_iqm_path",
            "observations": [
                {"dut_field": "metrics.rb.clifford.xy_sx.QB1.fidelity:par=d2", "value": 0.99},
                {"dut_field": "metrics.rb.clifford.xy_sx.QB2.fidelity:par=d2", "value": 0.99},
                {"dut_field": "metrics.rb.clifford.xy_sx.QB3.fidelity:par=d2", "value": 0.99},
                {"dut_field": "metrics.irb.cz.slepian_crf.QB1__QB2.fidelity:par=d2", "value": 0.98},
                {"dut_field": "metrics.irb.cz.slepian_crf.QB2__QB3.fidelity:par=d2", "value": 0.98},
            ],
        }

        selected = select_calibration_routed_layout(
            stim_circuit,
            stim_to_dense,
            calibration,
            options={"exclude_qubits": ["QB2"], "seed": 1, "max_iterations": 20},
        )

        self.assertNotIn("QB2", selected["dense_to_hardware"].values())
        self.assertEqual(selected["excluded_qubits"], ["QB2"])


def _stim_to_dense(stim_circuit: stim.Circuit) -> dict[int, int]:
    active = sorted(
        {
            target.value
            for instruction in stim_circuit.flattened()
            for target in instruction.targets_copy()
            if target.is_qubit_target
        }
    )
    return {stim_qubit: index for index, stim_qubit in enumerate(active)}


def _grid_calibration(
    rows: int,
    cols: int,
    low_origin: tuple[int, int],
    low_size: int,
) -> dict:
    qubits = {}
    couplers = []
    low_row, low_col = low_origin
    for row in range(rows):
        for col in range(cols):
            label = f"QB{row * cols + col + 1}"
            low = low_row <= row < low_row + low_size and low_col <= col < low_col + low_size
            error = 0.001 if low else 0.1
            qubits[label] = {
                "row": row,
                "col": col,
                "index": row * cols + col,
                "errors": {
                    "one_qubit": error,
                    "measurement": error,
                    "reset": error,
                    "idle": error,
                },
            }

    for row in range(rows):
        for col in range(cols):
            current = f"QB{row * cols + col + 1}"
            if col + 1 < cols:
                right = f"QB{row * cols + col + 2}"
                couplers.append({"qubits": [current, right], "error": _coupler_error(qubits, current, right)})
            if row + 1 < rows:
                down = f"QB{(row + 1) * cols + col + 1}"
                couplers.append({"qubits": [current, down], "error": _coupler_error(qubits, current, down)})

    return {"qpu": "fake_grid", "qubits": qubits, "couplers": couplers}


def _coupler_error(qubits: dict, left: str, right: str) -> float:
    left_error = qubits[left]["errors"]["one_qubit"]
    right_error = qubits[right]["errors"]["one_qubit"]
    return 0.001 if left_error < 0.01 and right_error < 0.01 else 0.1


def yaml_dump(data: dict) -> str:
    import yaml

    return yaml.safe_dump(data, sort_keys=False)


if __name__ == "__main__":
    unittest.main()
