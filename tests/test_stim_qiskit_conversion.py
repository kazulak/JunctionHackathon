from __future__ import annotations

import unittest

import numpy as np
import stim

from qec_pipeline.codes.surface_code import build_surface_code_circuit
from qec_pipeline.conversion import stim_to_qiskit_minimal
from qec_pipeline.conversion_checks import (
    convert_and_sample,
    sample_qiskit_measurements,
    validate_conversion_metadata,
)
from qec_pipeline.measurements import virtualize_omitted_repeated_resets
from qec_pipeline.syndrome_extraction import extract_syndromes


NO_NOISE = {"model": "no_noise", "parameters": {}}
SURFACE_D3_R1 = {
    "family": "surface_code",
    "distance": 3,
    "rounds": 1,
    "basis": "both",
    "reset_mode": "reset",
}


class StimToQiskitConversionTests(unittest.TestCase):
    def test_generated_surface_code_metadata_matches_for_z_and_x(self) -> None:
        for basis in ("memory_z", "memory_x"):
            stim_circuit, _detector_model, _measurement_order, _info = build_surface_code_circuit(
                SURFACE_D3_R1,
                NO_NOISE,
                basis,
            )
            qiskit_circuit, stim_to_dense, qiskit_measurement_order = stim_to_qiskit_minimal(
                stim_circuit
            )

            problems = validate_conversion_metadata(
                stim_circuit,
                qiskit_circuit,
                stim_to_dense,
                qiskit_measurement_order,
            )

            self.assertEqual(problems, [])
            self.assertEqual(qiskit_circuit.num_clbits, stim_circuit.num_measurements)
            self.assertEqual(len(qiskit_measurement_order), stim_circuit.num_measurements)

    def test_generated_no_noise_qiskit_samples_have_no_syndromes(self) -> None:
        small_code = {
            "family": "surface_code",
            "distance": 3,
            "rounds": 1,
            "basis": "both",
            "reset_mode": "reset",
        }

        for basis in ("memory_z", "memory_x"):
            stim_circuit, _detector_model, _measurement_order, _info = build_surface_code_circuit(
                small_code,
                NO_NOISE,
                basis,
            )
            qiskit_circuit, _stim_to_dense, _qiskit_measurement_order = stim_to_qiskit_minimal(
                stim_circuit
            )

            measurements = sample_qiskit_measurements(qiskit_circuit, shots=8, seed=5)
            result = extract_syndromes(
                measurements,
                stim_circuit,
            )

            self.assertEqual(int(result["det_events"].sum()), 0)
            self.assertEqual(int(result["obs_flips"].sum()), 0)

    def test_generated_no_reset_qiskit_samples_virtualize_to_no_syndromes(self) -> None:
        small_code = {
            "family": "surface_code",
            "distance": 3,
            "rounds": 2,
            "basis": "both",
            "reset_mode": "reset",
        }

        for basis in ("memory_z", "memory_x"):
            stim_circuit, _detector_model, _measurement_order, _info = build_surface_code_circuit(
                small_code,
                NO_NOISE,
                basis,
            )
            qiskit_circuit, _stim_to_dense, qiskit_measurement_order = stim_to_qiskit_minimal(
                stim_circuit,
                omit_initial_resets=True,
                omit_repeated_resets=True,
            )

            physical_measurements = sample_qiskit_measurements(qiskit_circuit, shots=8, seed=5)
            virtual_measurements = virtualize_omitted_repeated_resets(
                physical_measurements,
                qiskit_measurement_order,
            )
            result = extract_syndromes(
                virtual_measurements,
                stim_circuit,
            )

            self.assertEqual(qiskit_circuit.count_ops().get("reset", 0), 0)
            self.assertEqual(int(result["det_events"].sum()), 0)
            self.assertEqual(int(result["obs_flips"].sum()), 0)

    def test_z_measure_reset_matches_stim(self) -> None:
        stim_circuit = stim.Circuit(
            """
            R 0
            X 0
            MR 0
            M 0
            """
        )

        stim_samples, qiskit_samples, *_ = convert_and_sample(stim_circuit, shots=32, seed=1)

        expected = np.tile(np.array([[True, False]], dtype=bool), (32, 1))
        np.testing.assert_array_equal(stim_samples, expected)
        np.testing.assert_array_equal(qiskit_samples, expected)

    def test_terminal_mr_does_not_add_unused_reset(self) -> None:
        stim_circuit = stim.Circuit(
            """
            R 0
            X 0
            MR 0
            """
        )

        _stim_samples, qiskit_samples, qiskit_circuit, *_ = convert_and_sample(
            stim_circuit,
            shots=16,
            seed=1,
        )

        expected = np.ones((16, 1), dtype=bool)
        np.testing.assert_array_equal(qiskit_samples, expected)
        self.assertEqual(qiskit_circuit.count_ops().get("reset", 0), 1)

    def test_initial_resets_can_be_omitted(self) -> None:
        stim_circuit = stim.Circuit(
            """
            R 0
            RX 1
            M 0
            MX 1
            """
        )

        qiskit_circuit, stim_to_dense, measurement_order = stim_to_qiskit_minimal(
            stim_circuit,
            omit_initial_resets=True,
        )
        problems = validate_conversion_metadata(
            stim_circuit,
            qiskit_circuit,
            stim_to_dense,
            measurement_order,
        )
        measurements = sample_qiskit_measurements(qiskit_circuit, shots=16, seed=1)

        expected = np.zeros((16, 2), dtype=bool)
        self.assertEqual(problems, [])
        self.assertEqual(qiskit_circuit.count_ops().get("reset", 0), 0)
        np.testing.assert_array_equal(measurements, expected)

    def test_x_measurement_preserves_state_when_qubit_is_reused(self) -> None:
        stim_circuit = stim.Circuit(
            """
            RX 0
            MX 0
            TICK
            MX 0
            """
        )

        stim_samples, qiskit_samples, *_ = convert_and_sample(stim_circuit, shots=64, seed=2)

        expected = np.zeros((64, 2), dtype=bool)
        np.testing.assert_array_equal(stim_samples, expected)
        np.testing.assert_array_equal(qiskit_samples, expected)

    def test_mrx_measures_x_then_resets_to_plus(self) -> None:
        stim_circuit = stim.Circuit(
            """
            RX 0
            Z 0
            MRX 0
            MX 0
            """
        )

        stim_samples, qiskit_samples, *_ = convert_and_sample(stim_circuit, shots=32, seed=3)

        expected = np.tile(np.array([[True, False]], dtype=bool), (32, 1))
        np.testing.assert_array_equal(stim_samples, expected)
        np.testing.assert_array_equal(qiskit_samples, expected)

    def test_qiskit_counts_are_converted_to_clbit_measurement_order(self) -> None:
        stim_circuit = stim.Circuit(
            """
            R 5 9
            X 5
            M 5 9
            """
        )

        _stim_samples, qiskit_samples, _qc, _mapping, measurement_order = convert_and_sample(
            stim_circuit,
            shots=16,
            seed=4,
        )

        expected = np.tile(np.array([[True, False]], dtype=bool), (16, 1))
        np.testing.assert_array_equal(qiskit_samples, expected)
        self.assertEqual(measurement_order, [5, 9])

    def test_inverted_measurement_targets_fail_loudly(self) -> None:
        stim_circuit = stim.Circuit("M !0")

        with self.assertRaisesRegex(ValueError, "Inverted measurement target"):
            stim_to_qiskit_minimal(stim_circuit)


if __name__ == "__main__":
    unittest.main()
