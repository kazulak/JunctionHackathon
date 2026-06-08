# Module Integration

The pipeline is registry-based. To add a new implementation:

1. Add one file with the expected function.
2. Register it in the package `__init__.py`.
3. Select it from YAML.

## Code Builder

Function shape:

```python
def build_my_code_circuit(code: dict, noise: dict, basis: str) -> tuple:
    return stim_circuit, detector_model, measurement_order, circuit_info
```

Register in:

```text
qec_pipeline/codes/__init__.py
```

YAML:

```yaml
code:
  family: my_code
```

Current code families:

- `surface_code`
- `surface_code_iqm`
- `surface_code_unrotated`
- `color_code` placeholder

## Decoder

Function shape:

```python
def decode_with_my_decoder(decoder: dict, circuit: tuple, syndromes: tuple) -> tuple:
    return predicted_observables, logical_failures, ler, uncertainty, decoder_info
```

Register in:

```text
qec_pipeline/decoders/__init__.py
```

YAML:

```yaml
decoder:
  name: my_decoder
```

Current decoders:

- `observable_rate`
- `pymatching`
- `pymatching_calibrated`
- `pymatching_auto`
- `gnn` placeholder
- `ising` placeholder

## Backend

Function shape:

```python
def run_my_backend(backend: dict, circuit: tuple) -> tuple:
    return measurements, counts, raw_info
```

Register in:

```text
qec_pipeline/backends/__init__.py
```

YAML:

```yaml
backend:
  name: my_backend
```

## Priority

1. Improve simulator LER before spending hardware credits.
2. Improve the noise model from calibration and repeated-round behavior.
3. Improve decoder experiments: calibrated MWPM, BP/UF/GNN, postselection.
4. Reduce circuit depth and routing overhead before hardware runs.
5. Add code alternatives only when the baseline surface-code flow is understood.
