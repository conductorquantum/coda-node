# Device Configuration

`CODA_DEVICE_CONFIG` points to a YAML file that describes the hardware
setup.  The file's schema and validation are owned entirely by the
backend package (e.g. `coda-qubic`), not by `coda-self-service`.

## How It Works

`coda-self-service` stores `CODA_DEVICE_CONFIG` as a plain string on
`Settings.device_config`.  It does not parse, validate, or interpret
the file.  The executor factory reads `settings.device_config`, loads
the YAML, and builds the executor from it.

### Default Path

If `CODA_DEVICE_CONFIG` is not set and `./site/device.yaml` exists in
the working directory, the runtime uses it automatically and logs an
info message.  Explicit `CODA_DEVICE_CONFIG` always takes precedence.

## Example

### QubiC device config (`site/device.yaml`)

```yaml
target: superconducting_cnot
num_qubits: 3
calibration_path: ./qubitcfg.json
channel_config_path: ./channel_config.json
classifier_path: ./gmm_classifier_sim.pkl

runner_mode: rpc
rpc_host: 192.168.1.120
rpc_port: 9095
```

The schema above is defined by `QubiCConfig` in `coda-qubic`.  Other
backend packages define their own YAML schemas.

### Running

```bash
CODA_DEVICE_CONFIG=./site/device.yaml \
uv run coda start --token <your-token>
```

Or, if `./site/device.yaml` exists, simply:

```bash
uv run coda start --token <your-token>
```

## Path Resolution

Paths inside the YAML file (e.g. `calibration_path`) are resolved by
the backend package, not by `coda-self-service`.  Typically they are
relative to the YAML file's parent directory.

## Writing a Device Config for a New Backend

Each backend package defines its own Pydantic model for the device
config.  The factory function reads `settings.device_config`, loads
the file, validates it against the model, and builds the executor.

See [framework-protocol.md](framework-protocol.md) for a complete
example.
