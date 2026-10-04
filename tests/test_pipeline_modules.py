from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pymatching
import stim

from qec_pipeline.analysis.diagnostics import build_run_diagnostics
from qec_pipeline.analysis.measurement_diagnostics import build_measurement_diagnostics
from qec_pipeline.analysis.metrics import binomial_standard_error, fit_per_round_error, wilson_interval
from qec_pipeline.analysis.reports import write_run_artifacts
from qec_pipeline.artifacts import utc_timestamp
from qec_pipeline.backends import get_backend_runner
from qec_pipeline.backends.iqm_hardware import (
    _check_layout_matches_mapping,
    circuit_compilation_options,
    physical_loci,
    run_iqm_hardware_batch_backend,
)
from qec_pipeline.backends.simulator import run_simulator_backend
from qec_pipeline.circuit_preparation import prepare_circuit_for_execution
from qec_pipeline.codes import get_code_builder
from qec_pipeline.codes.color_code import build_color_code_circuit
from qec_pipeline.codes.surface_code import build_surface_code_circuit
from qec_pipeline.codes.surface_code_iqm import build_iqm_surface_code_circuit
from qec_pipeline.codes.surface_code_unrotated import build_unrotated_surface_code_circuit
from qec_pipeline.config import config_summary, load_experiment_config
from qec_pipeline.conversion_checks import convert_and_sample
from qec_pipeline.decoders import get_decoder
from qec_pipeline.decoders.gnn_decoder import decode_with_gnn
from qec_pipeline.decoders.ising_decoder import decode_with_ising
from qec_pipeline.decoders.observable_decoder import decode_observable_rate
from qec_pipeline.decoders.pymatching_auto_decoder import _select_candidate, decode_with_pymatching_auto
from qec_pipeline.decoders.pymatching_calibrated_decoder import decode_with_calibrated_pymatching
from qec_pipeline.decoders.pymatching_decoder import (
    decode_with_pymatching,
    detector_model_with_uniform_noise,
    pymatching_noise_sweep,
)
from qec_pipeline.decoders.pymatching_pij_decoder import estimate_edge_probabilities
from qec_pipeline.mapping import parse_hardware_calibration
from qec_pipeline.mapping.patch_selection import (
    rank_calibration_best_patches,
    select_calibration_best_patch,
    select_calibration_routed_layout,
    select_mapping_from_config,
    surface_code_patch_coordinates,
)
from qec_pipeline.measurements import (
    counts_to_measurement_array,
    memory_to_measurement_array,
)
from qec_pipeline.noise.iqm_calibration import _IqmNoiseBuilder
from qec_pipeline.pipeline import build_basis_metrics, describe_pipeline, run_pipeline
from qec_pipeline.provenance import uuid7_time
from qec_pipeline.sweeps import pin_sweep_mapping, redecode_sweep, round_values, run_rounds_sweep
from qec_pipeline.syndrome_extraction import extract_syndromes
from qec_pipeline.syndromes import extract_detection_events

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

    def test_pymatching_auto_supports_full_shot_decoder_improvements(self) -> None:
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
            np.array([[False], [True], [True]], dtype=bool),
            np.array([False, True, True], dtype=bool),
            {},
        )

        _predicted, failures, ler, _uncertainty, info = decode_with_pymatching_auto(
            {
                "name": "pymatching_auto",
                "options": {
                    "include_correlated_matching": True,
                    "include_matching_ensembles": True,
                    "gated_no_correction_quantiles": [0.5],
                    "uniform_probabilities": [0.01, 0.1],
                },
            },
            circuit,
            syndromes,
        )

        candidate_names = {candidate["name"] for candidate in info["candidates"]}
        self.assertIn("correlated_calibrated_or_configured", candidate_names)
        self.assertIn("ensemble_all_mwpm", candidate_names)
        self.assertEqual(info["postselection_fraction"], 1.0)
        np.testing.assert_array_equal(failures, np.array([False, False, False], dtype=bool))
        self.assertEqual(ler, 0.0)

    def test_pymatching_auto_can_report_on_holdout_split(self) -> None:
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
            np.array([[False], [True], [False], [True]], dtype=bool),
            np.array([False, True, False, True], dtype=bool),
            {},
        )

        _predicted, failures, _ler, _uncertainty, info = decode_with_pymatching_auto(
            {
                "name": "pymatching_auto",
                "options": {
                    "candidate_selection_mode": "holdout",
                    "selection_fraction": 0.5,
                    "selection_seed": 1,
                    "include_correlated_matching": True,
                    "uniform_probabilities": [0.01],
                },
            },
            circuit,
            syndromes,
        )

        self.assertEqual(info["candidate_selection"], "holdout")
        self.assertEqual(info["selection_shots"], 2)
        self.assertEqual(info["evaluation_shots"], 2)
        self.assertEqual(info["shots"], 2)
        self.assertEqual(len(failures), 2)
        self.assertIn("selected_candidate_evaluation_ler", info)

    def test_pymatching_auto_can_report_with_kfold_selection(self) -> None:
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
            np.array([[False], [True], [False], [True], [False], [True]], dtype=bool),
            np.array([False, True, False, True, False, True], dtype=bool),
            {},
        )

        _predicted, failures, _ler, _uncertainty, info = decode_with_pymatching_auto(
            {
                "name": "pymatching_auto",
                "options": {
                    "candidate_selection_mode": "kfold",
                    "candidate_selection_folds": 3,
                    "selection_seed": 1,
                    "include_correlated_matching": True,
                    "uniform_probabilities": [0.01],
                },
            },
            circuit,
            syndromes,
        )

        self.assertEqual(info["candidate_selection"], "kfold")
        self.assertEqual(info["candidate_selection_folds"], 3)
        self.assertEqual(info["shots"], 6)
        self.assertEqual(len(failures), 6)
        self.assertEqual(len(info["fold_selected_candidates"]), 3)

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

            write_run_artifacts(
                run_dir,
                circuit,
                raw,
                syndromes,
                metrics,
                {"save_raw_measurements": True, "save_syndromes": True},
            )

            self.assertTrue((run_dir / "circuit.stim").exists())
            self.assertTrue((run_dir / "metrics.json").exists())
            self.assertTrue((run_dir / "counts.json").exists())
            self.assertTrue((run_dir / "qiskit_circuit.txt").exists())
            self.assertTrue((run_dir / "measurement_diagnostics.json").exists())
            self.assertTrue((run_dir / "raw_measurements.npz").exists())
            self.assertTrue((run_dir / "syndromes.npz").exists())
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
            provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
            self.assertIn("git_commit", provenance)
            self.assertIn("stim", provenance["packages"])
            self.assertIn("## Provenance", (run_dir / "summary.md").read_text(encoding="utf-8"))

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
            sweep_json = json.loads((sweep_dir / "sweep_results.json").read_text(encoding="utf-8"))
            self.assertIn("provenance", sweep_json)


class CalibratedNoiseScalingTests(unittest.TestCase):
    """Regression tests for the idle-noise scaling bug (ERRATA E1)."""

    def test_num_ticks_counts_ticks_inside_repeat_blocks(self) -> None:
        for rounds in [1, 3, 5, 7]:
            code = {"family": "surface_code", "distance": 3, "rounds": rounds, "basis": "memory_z"}
            stim_circuit, _model, _order, circuit_info = build_surface_code_circuit(code, NO_NOISE, "memory_z")
            flattened = sum(1 for item in stim_circuit.flattened() if item.name == "TICK")
            self.assertEqual(circuit_info["num_ticks"], flattened)

    def test_idle_noise_per_round_does_not_depend_on_round_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            calibration_path = Path(temp_dir) / "calibration.yaml"
            calibration_path.write_text(
                yaml_dump(_grid_calibration(rows=6, cols=6, low_origin=(1, 1), low_size=5)),
                encoding="utf-8",
            )
            idle_per_round = []
            for rounds in [1, 3, 5, 7]:
                config = {
                    "code": {"family": "surface_code_iqm", "distance": 3, "rounds": rounds},
                    "noise": {
                        "model": "iqm_calibration",
                        "calibration_file": str(calibration_path),
                        # Only idle noise, so every DEPOLARIZE1 below is an idle location.
                        "options": {
                            "apply_idle": True,
                            "one_qubit_scale": 0.0,
                            "two_qubit_scale": 0.0,
                            "measurement_scale": 0.0,
                            "reset_scale": 0.0,
                            "qnd_scale": 0.0,
                        },
                    },
                    "mapping": {
                        "strategy": "calibration_best_patch",
                        "calibration_file": str(calibration_path),
                        "hardware_patch": None,
                    },
                }
                circuit = build_iqm_surface_code_circuit(config["code"], config["noise"], "memory_z")
                noisy, _model, _order, _info = prepare_circuit_for_execution(config, circuit)
                totals: dict[int, float] = {}
                for item in noisy.flattened():
                    if item.name == "DEPOLARIZE1":
                        probability = item.gate_args_copy()[0]
                        for target in item.targets_copy():
                            totals[target.value] = totals.get(target.value, 0.0) + probability
                idle_per_round.append({qubit: total / rounds for qubit, total in totals.items()})

            for per_round in idle_per_round[1:]:
                self.assertEqual(set(per_round), set(idle_per_round[0]))
                for qubit, value in per_round.items():
                    self.assertAlmostEqual(value, idle_per_round[0][qubit], places=12)

    def test_calibrated_simulator_error_per_round_is_stationary(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        base = load_experiment_config(repo_root / "configs" / "sweep_d3_baseline_sim.yaml")
        calibration_file = str(repo_root / base["noise"]["calibration_file"])
        error_per_round = {}
        for rounds in [3, 7]:
            config = json.loads(json.dumps(base))
            config["code"]["rounds"] = rounds
            config["noise"]["calibration_file"] = calibration_file
            config["mapping"]["calibration_file"] = calibration_file
            circuit = get_code_builder(config["code"]["family"])(config["code"], config["noise"], "memory_z")
            circuit = prepare_circuit_for_execution(config, circuit)
            raw = run_simulator_backend({"name": "simulator", "shots": 20000, "options": {"seed": 7}}, circuit)
            syndromes = extract_detection_events(circuit, raw)
            _predicted, _failures, ler, _sigma, _info = decode_with_calibrated_pymatching(
                {"name": "pymatching_calibrated"}, circuit, syndromes
            )
            error_per_round[rounds] = (1.0 - (1.0 - 2.0 * ler) ** (1.0 / rounds)) / 2.0

        # Before the fix this difference was ~0.095 (0.069 -> 0.163); after it, ~0.002.
        self.assertLess(abs(error_per_round[7] - error_per_round[3]), 0.006)


class DecoderSelectionAndStatisticsTests(unittest.TestCase):
    """Regression tests for ERRATA E3/E6: selection leaks, defaults, and statistics."""

    @staticmethod
    def _candidate(name: str, failures: np.ndarray) -> dict:
        failures = np.asarray(failures, dtype=bool)
        return {
            "name": name,
            "predicted_observables": np.zeros((len(failures), 1), dtype=bool),
            "logical_failures": failures,
            "ler": float(failures.mean()),
            "uncertainty": 0.0,
        }

    def test_holdout_tie_break_does_not_use_evaluation_split(self) -> None:
        shots = 10
        rng = np.random.default_rng(1)
        indices = np.arange(shots)
        rng.shuffle(indices)
        evaluation_shot = indices[-1]  # selection uses the first half of the shuffled shots
        first = np.zeros(shots, dtype=bool)
        first[evaluation_shot] = True
        candidates = [self._candidate("first", first), self._candidate("second", np.zeros(shots))]

        reported, info = _select_candidate(
            candidates,
            {"candidate_selection_mode": "holdout", "selection_fraction": 0.5, "selection_seed": 1},
        )

        # Both tie on the selection split; the earlier candidate must win even though
        # the second one looks better on the evaluation split.
        self.assertEqual(reported["name"], "first")
        self.assertFalse(info["selection_is_in_sample"])

    def test_kfold_tie_break_does_not_use_evaluation_fold(self) -> None:
        shots = 10
        first = np.zeros(shots, dtype=bool)
        first[3] = True
        candidates = [self._candidate("first", first), self._candidate("second", np.zeros(shots))]

        reported, info = _select_candidate(
            candidates,
            {"candidate_selection_mode": "kfold", "candidate_selection_folds": 5, "selection_seed": 1},
        )

        # In the fold containing shot 3 both candidates tie on the other folds, so the
        # first candidate is chosen and its evaluation failure is reported honestly.
        self.assertEqual(int(reported["logical_failures"].sum()), 1)
        self.assertFalse(info["selection_is_in_sample"])

    def test_pymatching_auto_defaults_to_kfold_selection(self) -> None:
        stim_circuit = stim.Circuit(
            """
            X_ERROR(0.1) 0
            M 0
            DETECTOR rec[-1]
            OBSERVABLE_INCLUDE(0) rec[-1]
            """
        )
        circuit = (stim_circuit, stim_circuit.detector_error_model(), (0,), {"num_observables": 1})
        events = np.array([[False], [True]] * 5, dtype=bool)
        syndromes = (events, events[:, 0].copy(), {})

        _predicted, _failures, _ler, _sigma, info = decode_with_pymatching_auto(
            {"name": "pymatching_auto", "options": {"uniform_probabilities": [0.01]}},
            circuit,
            syndromes,
        )
        self.assertEqual(info["candidate_selection"], "kfold")
        self.assertFalse(info["selection_is_in_sample"])

        _predicted, _failures, _ler, _sigma, info = decode_with_pymatching_auto(
            {"name": "pymatching_auto", "options": {"candidate_selection_mode": "current_batch"}},
            circuit,
            syndromes,
        )
        self.assertTrue(info["selection_is_in_sample"])

    def test_wilson_interval_has_positive_upper_bound_at_zero_failures(self) -> None:
        low, high = wilson_interval(0, 1000)
        self.assertEqual(low, 0.0)
        self.assertGreater(high, 0.0)
        low, high = wilson_interval(50, 1000)
        self.assertLess(low, 0.05)
        self.assertGreater(high, 0.05)

    def test_per_round_fit_recovers_known_error(self) -> None:
        rng = np.random.default_rng(3)
        true_error, amplitude, shots = 0.03, 0.95, 20000
        rows = []
        for rounds in [1, 3, 5, 7, 9]:
            probability = 0.5 * (1 - amplitude * (1 - 2 * true_error) ** rounds)
            rows.append(
                {"rounds": rounds, "shots": shots, "logical_failures": int(rng.binomial(shots, probability))}
            )

        fit = fit_per_round_error(rows)

        self.assertEqual(fit["fit_points"], 5)
        sigma = fit["fitted_logical_error_per_round_uncertainty"]
        self.assertIsNotNone(sigma)
        self.assertLess(abs(fit["fitted_logical_error_per_round"] - true_error), 2 * sigma)

    def test_postselected_rows_have_no_per_round_ler_and_are_not_fitted(self) -> None:
        decoder_info = {
            "logical_failures": 10,
            "shots": 500,
            "original_shots": 1000,
            "kept_shots": 500,
            "postselection_fraction": 0.5,
        }
        syndrome_info = {
            "mean_detector_firing_rate": 0.1,
            "max_detector_firing_rate": 0.2,
            "mean_syndrome_weight": 1.0,
        }
        metrics = build_basis_metrics("memory_z", 5, (None, None, 0.02, 0.006, decoder_info), syndrome_info)
        self.assertIsNone(metrics["logical_error_per_round"])
        self.assertGreater(metrics["ler_ci_high"], metrics["ler"])

        fit = fit_per_round_error(
            [
                {"rounds": 1, "shots": 500, "logical_failures": 5, "postselection_fraction": 0.5},
                {"rounds": 3, "shots": 400, "logical_failures": 9, "postselection_fraction": 0.4},
            ]
        )
        self.assertEqual(fit["fit_points"], 0)
        self.assertEqual(len(fit["excluded_points"]), 2)
        # Failed and successful fits must share keys (they are written to one CSV).
        ok_fit = fit_per_round_error(
            [{"rounds": 1, "shots": 500, "logical_failures": 5}, {"rounds": 3, "shots": 500, "logical_failures": 15}]
        )
        self.assertEqual(set(fit), set(ok_fit))


class NoiseModelTests(unittest.TestCase):
    """Calibration-informed noise model (ERRATA E2)."""

    CALIBRATION = {
        "dut_label": "fake_iqm",
        "observations": [
            {"dut_field": "metrics.rb.prx.drag_crf_sx.QB1.fidelity:par=d2", "value": 0.999},
            {"dut_field": "metrics.rb.prx.drag_crf_sx.QB2.fidelity:par=d2", "value": 0.999},
            {"dut_field": "metrics.irb.cz.crf_crf.QB1__QB2.fidelity:par=d2", "value": 0.99},
            {"dut_field": "metrics.ssro.measure.constant.QB1.error_0_to_1", "value": 0.01},
            {"dut_field": "metrics.ssro.measure.constant.QB1.error_1_to_0", "value": 0.03},
            {"dut_field": "metrics.ssro.measure.constant.QB1.fidelity", "value": 0.5},
            {"dut_field": "metrics.ssro.measure.constant.QB2.error_0_to_1", "value": 0.01},
            {"dut_field": "metrics.ssro.measure.constant.QB2.error_1_to_0", "value": 0.03},
            {"dut_field": "metrics.qndness.measure.constant.QB1.qndness_0", "value": 0.9},
            {"dut_field": "characterization.model.QB1.t1_time", "value": 50e-6},
            {"dut_field": "characterization.model.QB1.t2_echo_time", "value": 40e-6},
        ],
    }

    def _noisy(self, circuit_text: str, options: dict | None = None) -> stim.Circuit:
        hardware = parse_hardware_calibration(self.CALIBRATION)
        builder = _IqmNoiseBuilder(
            hardware=hardware,
            mapping_info={"stim_to_hardware": {"0": "QB1", "1": "QB2"}},
            rounds=1,
            num_ticks=1,
            options=options or {},
        )
        return builder.noisy_copy(stim.Circuit(circuit_text))

    @staticmethod
    def _args(circuit: stim.Circuit, name: str) -> list[list[float]]:
        return [item.gate_args_copy() for item in circuit if item.name == name]

    def test_parser_uses_mean_assignment_error_for_readout(self) -> None:
        hardware = parse_hardware_calibration(self.CALIBRATION)
        self.assertAlmostEqual(hardware["qubits"]["QB1"]["errors"]["measurement"], 0.02)

    def test_rb_infidelity_is_converted_to_pauli_probability(self) -> None:
        noisy = self._noisy("H 0\nCX 0 1\nM 0 1")
        self.assertAlmostEqual(self._args(noisy, "DEPOLARIZE1")[0][0], 1.5 * 0.001)
        self.assertAlmostEqual(self._args(noisy, "DEPOLARIZE2")[0][0], 1.25 * 0.01)

        raw = self._noisy("H 0\nCX 0 1\nM 0 1", {"rb_to_pauli": False})
        self.assertAlmostEqual(self._args(raw, "DEPOLARIZE2")[0][0], 0.01)

    def test_idle_uses_pauli_twirled_t1_t2(self) -> None:
        noisy = self._noisy("TICK\nM 0")
        px, py, pz = self._args(noisy, "PAULI_CHANNEL_1")[0]
        decay_1 = 1 - np.exp(-1e-6 / 50e-6)
        decay_2 = 1 - np.exp(-1e-6 / 40e-6)
        self.assertAlmostEqual(px, decay_1 / 4)
        self.assertAlmostEqual(py, decay_1 / 4)
        self.assertAlmostEqual(pz, decay_2 / 2 - decay_1 / 4)

    def test_qnd_flip_only_when_measured_qubit_is_reused_without_reset(self) -> None:
        reused = self._noisy("M 0\nH 0\nM 0")
        # Readout is a classical flip on each measurement, M(0.02); the non-QND flip
        # (0.1) acts on the qubit after the first M only, because it is reused.
        readout = [args[0] for args in self._args(reused, "M")]
        self.assertEqual(len(readout), 2)
        for actual in readout:
            self.assertAlmostEqual(actual, 0.02)
        qnd = [args[0] for args in self._args(reused, "X_ERROR")]
        self.assertEqual(len(qnd), 1)
        self.assertAlmostEqual(qnd[0], 0.1)

        # MR resets the qubit, so the post-measurement state never matters.
        reset_mode = self._noisy("MR 0\nH 0\nM 0")
        self.assertEqual(self._args(reset_mode, "X_ERROR"), [])
        self.assertAlmostEqual(self._args(reset_mode, "MR")[0][0], 0.02)

    def test_terminal_and_mid_circuit_readout_use_their_own_calibration(self) -> None:
        calibration = {
            "dut_label": "fake_iqm",
            "observations": list(self.CALIBRATION["observations"])
            + [
                {"dut_field": "metrics.ssro.measure_fidelity.shelved_constant.QB1.error_0_to_1", "value": 0.004},
                {"dut_field": "metrics.ssro.measure_fidelity.shelved_constant.QB1.error_1_to_0", "value": 0.006},
            ],
        }
        hardware = parse_hardware_calibration(calibration)
        self.assertAlmostEqual(hardware["qubits"]["QB1"]["errors"]["measurement"], 0.02)
        self.assertAlmostEqual(hardware["qubits"]["QB1"]["errors"]["measurement_terminal"], 0.005)
        builder = _IqmNoiseBuilder(
            hardware=hardware,
            mapping_info={"stim_to_hardware": {"0": "QB1", "1": "QB2"}},
            rounds=1,
            num_ticks=1,
            options={},
        )
        noisy = builder.noisy_copy(stim.Circuit("M 0\nH 0\nM 0"))
        readout = [args[0] for args in self._args(noisy, "M")]
        self.assertAlmostEqual(readout[0], 0.02)  # mid-circuit
        self.assertAlmostEqual(readout[1], 0.005)  # terminal

    def test_fit_recovers_known_two_qubit_scale(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "fit_noise_to_hardware", repo_root / "scripts" / "fit_noise_to_hardware.py"
        )
        fit_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fit_module)

        config = load_experiment_config(repo_root / "configs" / "sweep_d3_baseline_sim.yaml")
        calibration_file = str(repo_root / config["noise"]["calibration_file"])
        config["noise"]["calibration_file"] = calibration_file
        config["mapping"]["calibration_file"] = calibration_file
        truth = {"two_qubit_scale": 2.0, "measurement_scale": 1.0, "idle_scale": 1.0}
        shots = 20000
        targets = {"bases": {}}
        for basis in ["memory_z", "memory_x"]:
            rates = fit_module.simulated_rates(config, basis, truth, shots, seed=11)
            counts = np.rint(rates * shots).astype(int)
            targets["bases"][basis] = {
                "shots": shots,
                "detector_counts": counts[:-1].tolist(),
                "observable_flip_count": int(counts[-1]),
            }

        grid = {"two_qubit_scale": [1.0, 2.0, 3.0], "measurement_scale": [1.0], "idle_scale": [1.0]}
        result = fit_module.fit_scales(config, targets, grid, shots=shots, seed=5)

        self.assertEqual(result["best"]["scales"]["two_qubit_scale"], 2.0)


class HardwarePathTests(unittest.TestCase):
    """IQM path robustness (ERRATA E6 and audit phase 6); runs offline."""

    def test_memory_conversion_keeps_shot_order(self) -> None:
        memory = ["01", "10", "11", "00"]  # little-endian: clbit 0 is the rightmost bit
        array = memory_to_measurement_array(memory, num_measurements=2)
        np.testing.assert_array_equal(
            array,
            np.array([[True, False], [False, True], [True, True], [False, False]], dtype=bool),
        )

    def test_moved_reset_options_fail_before_connecting(self) -> None:
        for option in ("omit_repeated_resets", "mid_circuit_reset"):
            backend = {"name": "iqm_hardware", "shots": 1, "options": {option: True}}
            with self.assertRaises(ValueError):
                run_iqm_hardware_batch_backend(backend, [])

    def test_compilation_options_enable_active_reset_and_native_dd(self) -> None:
        try:
            from iqm.iqm_client import DDMode
        except ImportError:
            self.skipTest("IQM client is not installed")
        options = circuit_compilation_options({"active_reset_cycles": 2, "dynamical_decoupling": True})
        self.assertEqual(options.active_reset_cycles, 2)
        self.assertEqual(options.dd_mode, DDMode.ENABLED)
        default = circuit_compilation_options({})
        self.assertIsNone(default.active_reset_cycles)
        self.assertEqual(default.dd_mode, DDMode.DISABLED)

    def test_sweep_pins_one_layout_for_all_round_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            calibration_path = Path(temp_dir) / "calibration.yaml"
            calibration_path.write_text(
                yaml_dump(_grid_calibration(rows=6, cols=6, low_origin=(1, 1), low_size=5)),
                encoding="utf-8",
            )
            config = {
                "experiment": {"name": "unit_pinned_sweep", "description": "", "seed": 1},
                "code": {
                    "family": "surface_code_iqm",
                    "distance": 3,
                    "rounds": 1,
                    "basis": "memory_z",
                    "reset_mode": "reset",
                },
                "backend": {"name": "simulator", "shots": 16, "options": {"seed": 1}},
                "noise": {"model": "iqm_calibration", "calibration_file": str(calibration_path), "options": {}},
                "decoder": {"name": "pymatching_calibrated", "options": {}},
                "mapping": {
                    "strategy": "calibration_best_patch",
                    "calibration_file": str(calibration_path),
                    "hardware_patch": None,
                },
                "artifacts": {"root": temp_dir},
            }

            pinned = pin_sweep_mapping(config)
            self.assertTrue(pinned["mapping"]["hardware_patch"]["stim_to_hardware"])
            self.assertIsNone(config["mapping"]["hardware_patch"])  # input is not mutated

            sweep_dir = run_rounds_sweep(config, rounds=[1, 3], output_root=Path(temp_dir))
            layouts = {
                json.dumps(json.loads(path.read_text(encoding="utf-8"))["mapping"]["stim_to_hardware"])
                for path in sweep_dir.glob("runs/*/*/memory_z/circuit_metadata.json")
            }
            self.assertEqual(len(layouts), 1)

    def test_physical_loci_follow_initial_layout_and_guard_rejects_mismatch(self) -> None:
        try:
            from iqm.qiskit_iqm.fake_backends.fake_garnet import IQMFakeGarnet
            from qiskit import QuantumCircuit, transpile
        except ImportError:
            self.skipTest("IQM qiskit packages are not installed")

        backend = IQMFakeGarnet()
        neighbours = sorted(backend.coupling_map.neighbors(13))
        layout = [13, neighbours[0]]
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure([0, 1], [0, 1])
        transpiled = transpile(circuit, backend, initial_layout=layout, optimization_level=3, seed_transpiler=1)

        loci = physical_loci(transpiled, backend)
        expected = sorted(backend.index_to_qubit_name(index) for index in layout)
        self.assertEqual(sorted(loci["physical_qubits"]), expected)
        self.assertEqual(sorted(loci["measured_qubits"]), expected)

        matching = {"dense_to_hardware": {"0": expected[0], "1": expected[1]}}
        _check_layout_matches_mapping(loci, matching)
        wrong = {"dense_to_hardware": {"0": "QB1", "1": "QB2"}}
        with self.assertRaises(RuntimeError):
            _check_layout_matches_mapping(loci, wrong)


class MidcircuitProbeTests(unittest.TestCase):
    """The mid-circuit probe used to diagnose ERRATA E5."""

    def test_noiseless_probe_never_flips_data_in_any_mode(self) -> None:
        for mode in ["measure_reset", "measure", "none"]:
            with tempfile.TemporaryDirectory() as temp_dir:
                config = {
                    "experiment": {"name": f"unit_probe_{mode}", "description": "", "seed": 1},
                    "code": {
                        "family": "midcircuit_probe",
                        "probe_mode": mode,
                        "distance": 3,
                        "rounds": 3,
                        "basis": "both",
                        "reset_mode": "reset",
                    },
                    "backend": {"name": "simulator", "shots": 64, "options": {"seed": 1}},
                    "noise": NO_NOISE,
                    "decoder": {"name": "observable_rate", "options": {}},
                    "mapping": {"strategy": "none", "hardware_patch": None},
                    "artifacts": {"root": temp_dir},
                }
                _run_dir, basis_results, _notes = run_pipeline(config)
                for _basis, _circuit, _raw, _syndromes, decoded, metrics in basis_results:
                    self.assertEqual(decoded[2], 0.0)
                    self.assertFalse(metrics["memory_experiment"])
                    self.assertIsNone(metrics["logical_error_per_round"])

    def test_probe_uses_surface_code_qubits_and_converts_to_qiskit(self) -> None:
        probe, *_ = get_code_builder("midcircuit_probe")(
            {"distance": 3, "rounds": 2, "probe_mode": "measure_reset"}, NO_NOISE, "memory_z"
        )
        surface, *_ = build_surface_code_circuit(
            {"family": "surface_code", "distance": 3, "rounds": 2}, NO_NOISE, "memory_z"
        )
        self.assertEqual(probe.get_final_qubit_coordinates(), surface.get_final_qubit_coordinates())

        for mode in ["measure_reset", "measure"]:
            probe, *_ = get_code_builder("midcircuit_probe")(
                {"distance": 3, "rounds": 2, "probe_mode": mode}, NO_NOISE, "memory_x"
            )
            _stim_samples, qiskit_samples, *_ = convert_and_sample(probe, shots=8, seed=1)
            detections, observables = probe.compile_m2d_converter().convert(
                measurements=qiskit_samples, separate_observables=True
            )
            self.assertFalse(detections.any())
            self.assertFalse(observables.any())


class ResetStrategyTests(unittest.TestCase):
    """Mid-circuit reset strategies encoded in Stim (Gehér et al., arXiv:2408.00758)."""

    @staticmethod
    def _circuit(strategy: str, rounds: int = 5, basis: str = "memory_z") -> stim.Circuit:
        code = {"family": "surface_code", "distance": 3, "rounds": rounds, "mid_circuit_reset": strategy}
        return build_surface_code_circuit(code, NO_NOISE, basis)[0]

    def test_all_strategies_have_deterministic_detectors(self) -> None:
        for strategy in ["reset", "feedforward", "none"]:
            for basis in ["memory_z", "memory_x"]:
                for rounds in [1, 2, 4]:
                    circuit = self._circuit(strategy, rounds, basis)
                    circuit.detector_error_model()  # raises on non-deterministic detectors
                    detections, observables = circuit.compile_detector_sampler(seed=1).sample(
                        64, separate_observables=True
                    )
                    self.assertFalse(detections.any())
                    self.assertFalse(observables.any())

    def test_readout_classification_error_spans_two_rounds_without_unconditional_reset(self) -> None:
        def readout_edge_gaps(strategy: str) -> set[float]:
            circuit = stim.Circuit()
            for instruction in self._circuit(strategy).flattened():
                if instruction.name in {"M", "MR"}:
                    circuit.append(instruction.name, instruction.targets_copy(), [0.01])
                else:
                    circuit.append(instruction)
            coords = circuit.get_detector_coordinates()
            gaps = set()
            for error in circuit.detector_error_model(decompose_errors=True).flattened():
                if error.type != "error":
                    continue
                dets = [t.val for t in error.targets_copy() if t.is_relative_detector_id()]
                if len(dets) == 2 and coords[dets[0]][:2] == coords[dets[1]][:2]:
                    gaps.add(abs(coords[dets[0]][2] - coords[dets[1]][2]))
            return gaps

        self.assertEqual(readout_edge_gaps("reset"), {1.0})
        self.assertIn(2.0, readout_edge_gaps("feedforward"))
        self.assertIn(2.0, readout_edge_gaps("none"))

    def test_unknown_strategy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self._circuit("sometimes")


class PijDecoderTests(unittest.TestCase):
    """p_ij edge estimation from detection events (Google, Nature 595/614)."""

    def test_edge_estimates_track_true_probabilities_and_fix_a_wrong_prior(self) -> None:
        truth = stim.Circuit.generated(
            "surface_code:rotated_memory_x",
            distance=3,
            rounds=3,
            after_clifford_depolarization=0.006,
            before_measure_flip_probability=0.01,
        )
        wrong = stim.Circuit.generated(
            "surface_code:rotated_memory_x",
            distance=3,
            rounds=3,
            after_clifford_depolarization=0.02,
            before_measure_flip_probability=0.001,
        )
        detections, _observables = truth.compile_detector_sampler(seed=2).sample(60000, separate_observables=True)
        prior = pymatching.Matching.from_detector_error_model(wrong.detector_error_model(decompose_errors=True))
        estimates, summary = estimate_edge_probabilities(prior, detections)
        exact = {
            (a, b): data["error_probability"]
            for a, b, data in pymatching.Matching.from_detector_error_model(
                truth.detector_error_model(decompose_errors=True)
            ).edges()
        }
        shared = [key for key in estimates if key in exact]
        estimated_mean = np.mean([estimates[key] for key in shared])
        exact_mean = np.mean([exact[key] for key in shared])
        prior_mean = summary["mean_prior_probability"]
        self.assertLess(abs(estimated_mean - exact_mean), 0.25 * exact_mean)
        self.assertGreater(abs(prior_mean - exact_mean), abs(estimated_mean - exact_mean))

    def test_pij_decoder_cross_fits_and_is_registered(self) -> None:
        circuit_stim = stim.Circuit.generated(
            "surface_code:rotated_memory_z", distance=3, rounds=3, after_clifford_depolarization=0.005
        )
        model = circuit_stim.detector_error_model(decompose_errors=True)
        detections, observables = circuit_stim.compile_detector_sampler(seed=3).sample(4000, separate_observables=True)
        circuit = (circuit_stim, model, (), {"num_observables": 1})
        _p, failures, ler, _sigma, info = get_decoder("pymatching_pij")(
            {"name": "pymatching_pij", "options": {"folds": 2}}, circuit, (detections, observables, {})
        )
        self.assertEqual(info["folds"], 2)
        self.assertEqual(len(info["fold_summaries"]), 2)
        self.assertEqual(info["fold_summaries"][0]["training_shots"], 2000)
        self.assertEqual(len(failures), 4000)
        self.assertLess(ler, 0.2)
        with self.assertRaises(ValueError):
            get_decoder("pymatching_pij")(
                {"name": "pymatching_pij", "options": {"folds": 1}}, circuit, (detections, observables, {})
            )

    def test_redecode_sweep_reuses_saved_raw_measurements(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "experiment": {"name": "unit_redecode", "description": "", "seed": 1},
                "code": {
                    "family": "surface_code",
                    "distance": 3,
                    "rounds": 1,
                    "basis": "memory_z",
                    "reset_mode": "reset",
                },
                "backend": {"name": "simulator", "shots": 200, "options": {"seed": 1}},
                "noise": {
                    "model": "simple_depolarizing",
                    "parameters": {"one_qubit_error": 0.005, "measurement_error": 0.01},
                },
                "decoder": {"name": "pymatching", "options": {}},
                "mapping": {"strategy": "none", "hardware_patch": None},
                "artifacts": {"root": temp_dir, "save_raw_measurements": True},
            }
            sweep_dir = run_rounds_sweep(config, rounds=[1, 3], output_root=Path(temp_dir))
            decoder = {"name": "pymatching_pij", "options": {"folds": 2}}
            output = redecode_sweep(sweep_dir, decoder, Path(temp_dir) / "redo")
            payload = json.loads((output / "sweep_results.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(row["rounds"] for row in payload["rows"]), [1, 3])
            self.assertTrue(all(row["shots"] == 200 for row in payload["rows"]))


class ProvenanceTests(unittest.TestCase):
    def test_uuid7_time_decodes_iqm_job_submit_time(self) -> None:
        submitted = uuid7_time("019e9fa6-c559-77a0-821e-462fcebccfba")
        self.assertEqual(submitted.isoformat(timespec="seconds"), "2026-06-07T01:16:07+00:00")

    def test_utc_timestamp_includes_microseconds(self) -> None:
        self.assertRegex(utc_timestamp(), r"^\d{8}T\d{6}_\d{6}Z$")


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
