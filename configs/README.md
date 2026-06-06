# Configs

Run an experiment by choosing one YAML file:

```bash
python main.py configs/demo_stim_no_noise.yaml
python main.py configs/demo_stim_simple_noise.yaml
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
