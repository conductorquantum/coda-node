# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-20

### Added

- FastAPI server runtime with lifespan management and health/readiness endpoints.
- RS256 JWT authentication with automatic keypair generation and token signing.
- Redis Streams job consumer with consumer-group crash recovery.
- Pluggable executor protocol (`JobExecutor`) with auto-discovery of installed backends.
- `NoopExecutor` fallback for scaffolding and integration smoke tests.
- NativeGateIR schema with validation for superconducting, trapped-ion, and silicon-spin gate sets.
- OpenQASM 3.0 to NativeGateIR round-trip conversion.
- Authenticated webhook delivery with exponential-backoff retry.
- Periodic QPU heartbeat client with connectivity and Redis health reporting.
- Self-service provisioning: one-time token exchange for JWT credentials, Redis URL, and VPN config.
- OpenVPN tunnel management with automatic startup, health monitoring, and profile sanitization.
- VPN preflight checks with platform-specific interface detection (macOS, Linux, Windows).
- CLI (`coda-self-service`) with `start`, `stop`, `status`, `doctor`, `reset`, `stop-vpn`, and `logs` subcommands.
- Background daemon mode with PID tracking and log redirection.
- Pydantic-based configuration with environment variables (`CODA_*`), persisted state, and defaults.
- PEP 561 `py.typed` marker for downstream type checking.

[0.1.0]: https://github.com/conductorquantum/coda-self-service/releases/tag/v0.1.0
