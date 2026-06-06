from __future__ import annotations

import numpy as np


def counts_to_measurement_array(
    counts: dict[str, int],
    num_measurements: int,
    total_shots: int,
) -> np.ndarray:
    """Convert Qiskit counts into a boolean array ordered by classical bit index."""
    result = np.zeros((total_shots, num_measurements), dtype=bool)
    row_index = 0

    for bitstring, count in counts.items():
        bits_by_clbit = bitstring.replace(" ", "")[::-1]
        if len(bits_by_clbit) < num_measurements:
            raise ValueError(
                "Qiskit bitstring is shorter than requested measurement count: "
                f"{len(bits_by_clbit)} < {num_measurements}"
            )

        row = np.array(
            [bit == "1" for bit in bits_by_clbit[:num_measurements]],
            dtype=bool,
        )
        for _ in range(count):
            if row_index >= total_shots:
                raise ValueError("Counts contain more shots than total_shots")
            result[row_index] = row
            row_index += 1

    if row_index != total_shots:
        raise ValueError(f"Counts contain {row_index} shots, expected {total_shots}")

    return result
