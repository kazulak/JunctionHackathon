# Module Integration

The pipeline uses simple registries. A new module needs:

1. One file with the expected function signature.
2. One import plus one dictionary entry in the package `__init__.py`.
3. One YAML name change.

## Code Builder

File example:

```text
qec_pipeline/codes/my_surface_code.py
```

Function:

```python
def build_my_surface_code_circuit(code: dict, noise: dict, basis: str) -> tuple:
    return stim_circuit, detector_model, measurement_order, circuit_info
```

Register in:

```text
qec_pipeline/codes/__init__.py
```

```python
from qec_pipeline.codes.my_surface_code import build_my_surface_code_circuit

CODE_BUILDERS["my_surface_code"] = build_my_surface_code_circuit
```

Use in YAML:

```yaml
code:
  family: my_surface_code
```

Current registered code builders:

- `surface_code`: Stim rotated surface code with optional scalar Stim noise.
- `surface_code_iqm`: clean rotated surface code, with IQM calibration noise added after mapping.
- `surface_code_unrotated`: Stim unrotated surface code.
- `color_code`: placeholder.

## Decoder

File example:

```text
qec_pipeline/decoders/my_decoder.py
```

Function:

```python
def decode_with_my_decoder(decoder: dict, circuit: tuple, syndromes: tuple) -> tuple:
    return predicted_observables, logical_failures, ler, uncertainty, decoder_info
```

Register in:

```text
qec_pipeline/decoders/__init__.py
```

```python
from qec_pipeline.decoders.my_decoder import decode_with_my_decoder

DECODERS["my_decoder"] = decode_with_my_decoder
```

Use in YAML:

```yaml
decoder:
  name: my_decoder
```

Current registered decoders:

- `observable_rate`: sanity check.
- `pymatching`: MWPM from the circuit detector model.
- `pymatching_calibrated`: MWPM route for calibrated detector models.
- `gnn`: placeholder.
- `ising`: placeholder.

## Backend

File example:

```text
qec_pipeline/backends/my_backend.py
```

Function:

```python
def run_my_backend(backend: dict, circuit: tuple, mapping: dict) -> tuple:
    return measurements, counts, raw_info
```

Register in:

```text
qec_pipeline/backends/__init__.py
```

```python
from qec_pipeline.backends.my_backend import run_my_backend

BACKENDS["my_backend"] = run_my_backend
```

Use in YAML:

```yaml
backend:
  name: my_backend
```

## Current Priority

1. Hardware execution variants: reset handling, round count, mapping, QPU choice.
2. Mapping and calibration: pin good layouts, avoid bad QND/readout/CZ regions.
3. Noise/error model: build better detector-model weights from calibration data.
4. Decoder alternatives: GNN or calibration-aware MWPM.
5. Code alternatives: color code or custom surface-code schedule.
