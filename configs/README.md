# Configs

Run an experiment by choosing one YAML file:

```bash
python main.py configs/demo_stim_no_noise.yaml
python main.py configs/demo_stim_simple_noise.yaml
python main.py configs/demo_stim_simple_noise_pymatching.yaml
```

## Simple Choices

Choose basis:

```yaml
code:
  basis: memory_z
```

```yaml
code:
  basis: memory_x
```

```yaml
code:
  basis: both
```

Choose no noise:

```yaml
noise:
  model: no_noise
  parameters: {}
```

Choose simple Stim noise:

```yaml
noise:
  model: simple_depolarizing
  parameters:
    one_qubit_error: 0.003
    two_qubit_error: 0.003
    measurement_error: 0.003
    reset_error: 0.003
    idle_error: 0.003
```

Current simulator:

```yaml
backend:
  name: simulator
```

Current first decoder:

```yaml
decoder:
  name: observable_rate
```

`observable_rate` counts logical observable flips directly. It is a sanity
check, not the final decoder.

First real decoder:

```yaml
decoder:
  name: pymatching
```

Minimal IQM baseline:

```bash
python main.py configs/iqm_surface_d3_baseline.yaml
```

For IQM authentication, prefer an environment variable:

```powershell
$env:IQM_TOKEN="your-token"
python main.py configs/iqm_surface_d3_baseline.yaml
```

Do not set `IQM_TOKEN` and also put `backend.options.token` in YAML at the same
time. IQM rejects mixed authentication sources.
