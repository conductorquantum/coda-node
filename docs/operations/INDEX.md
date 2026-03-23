# Operations

Runtime operations cover health endpoints, graceful shutdown, the CLI,
and the exception hierarchy.

## Topics

| Document | Summary |
|---|---|
| [HEALTH_ENDPOINTS.md](HEALTH_ENDPOINTS.md) | `/health` and `/ready` endpoints for liveness and readiness probes. |
| [GRACEFUL_SHUTDOWN.md](GRACEFUL_SHUTDOWN.md) | Shutdown sequence: drain, cancel, close, cleanup. |
| [CLI.md](CLI.md) | `coda` CLI subcommands: `start`, `stop`, `status`, `logs`, `doctor`, `reset`, `stop-vpn`. |
| [ERROR_HANDLING.md](ERROR_HANDLING.md) | `CodaError` exception hierarchy and when each type is raised. |

## Key Files

| File | Role |
|---|---|
| `src/self_service/server/app.py` | FastAPI app, lifespan, `/health`, `/ready`. |
| `src/self_service/server/cli.py` | CLI entry point and subcommands. |
| `src/self_service/server/daemon.py` | Daemon process management (start, stop, status, logs). |
| `src/self_service/errors.py` | Exception hierarchy. |
