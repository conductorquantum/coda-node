# coda-self-service

Production-ready runtime for connecting a machine to Coda.

It boots a FastAPI service, provisions or reconnects node credentials, manages
VPN health, consumes Redis jobs, and posts signed execution results back to
Coda.

## What It Does

- Bootstraps a node from a self-service token
- Reconnects later with persisted JWT credentials
- Verifies and monitors VPN connectivity
- Consumes jobs from Redis streams
- Sends signed webhook results to Coda
- Supports a custom execution backend

## Why It Exists

`coda-self-service` is the machine-side runtime for a Coda-connected node. The
package is intentionally small: one service, one CLI, one configuration model,
and a narrow operational surface that is easy to deploy and debug.

## Install

```bash
uv sync --dev
```

The project requires Python 3.11+ and exposes two equivalent entry points:

- `coda`
- `coda-self-service`

## Quick Start

First bootstrap with a self-service token:

```bash
uv run coda start --token <bootstrap-token>
```

Or run from environment variables:

```bash
export CODA_SELF_SERVICE_TOKEN=<bootstrap-token>
uv run coda start
```

After a successful first run, the runtime persists the issued credentials and
can restart without a new bootstrap token.

## How It Works

On startup the runtime:

1. Loads configuration from `CODA_` environment variables, then persisted state,
   then defaults.
2. Connects to Coda using either a bootstrap token or persisted JWT
   credentials.
3. Brings up or validates VPN connectivity when required.
4. Starts the FastAPI service and background Redis consumer.
5. Executes jobs and sends signed webhook callbacks.

The service exposes:

- `GET /health`
- `GET /ready`

## Configuration

Configuration is driven by `CODA_` environment variables.

Common settings:

- `CODA_SELF_SERVICE_TOKEN`: bootstrap token for first-time provisioning
- `CODA_JWT_PRIVATE_KEY`: PEM private key for direct JWT-based startup
- `CODA_JWT_KEY_ID`: JWT key id
- `CODA_REDIS_URL`: Redis connection string
- `CODA_WEBAPP_URL`: Coda base URL
- `CODA_HOST`: bind host for the local FastAPI service
- `CODA_PORT`: bind port for the local FastAPI service
- `CODA_EXECUTOR_FACTORY`: import path for a custom executor factory

Direct JWT startup is supported when `CODA_JWT_PRIVATE_KEY` and
`CODA_JWT_KEY_ID` are already available. Otherwise, provide
`CODA_SELF_SERVICE_TOKEN` and let the runtime provision itself.

## Persisted State

After a successful self-service bootstrap, the runtime writes:

- `/tmp/coda.config`
- `/tmp/coda-private-key`

On POSIX systems both files are expected to use `0600` permissions.

These files allow later reconnects without a fresh token, including reuse of:

- JWT credentials
- machine fingerprint
- saved VPN profile path
- runtime connection settings

## CLI

Start the node:

```bash
uv run coda start
```

Print a local diagnostic summary:

```bash
uv run coda doctor
```

Stop the managed VPN daemon:

```bash
uv run coda stop-vpn
```

Clear persisted runtime state and VPN artifacts:

```bash
uv run coda reset
```

## Custom Executor

If `CODA_EXECUTOR_FACTORY` is unset, the runtime uses a `NoopExecutor` so the
service can boot without hardware integration.

To provide a real backend, export a factory path such as:

```bash
export CODA_EXECUTOR_FACTORY="my_project.executor:create_executor"
```

The factory should return an object implementing:

```python
from self_service.server.executor import ExecutionResult


class MyExecutor:
    async def run(self, ir, shots: int) -> ExecutionResult:
        return ExecutionResult(
            counts={"0" * len(ir.measurements): shots},
            execution_time_ms=1.0,
            shots_completed=shots,
        )


def create_executor() -> MyExecutor:
    return MyExecutor()
```

## Development

Run the local quality checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/self_service
uv run pytest --cov --cov-report=term-missing
```

Install pre-commit hooks:

```bash
uv run pre-commit install
```

Run all hooks manually:

```bash
uv run pre-commit run --all-files
```

## Design Notes

- FastAPI provides the HTTP service and application lifecycle
- Pydantic settings handle environment-driven configuration
- Redis is used for job delivery
- OpenVPN is managed as an external dependency when VPN is required

The README structure here is intentionally closer to the style of the
[FastAPI README](https://github.com/fastapi/fastapi): brief overview first,
clear install and run steps next, then only the operational details needed to
use the project in production.
