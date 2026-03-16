# CLI Reference

The `coda` (and `coda-self-service`) command-line interface provides
four subcommands for managing the node runtime.

## `coda start`

Start the FastAPI server.

```
coda start [--token TOKEN] [--host HOST] [--port PORT]
```

| Flag | Env Override | Description |
|---|---|---|
| `--token`, `-t` | `CODA_SELF_SERVICE_TOKEN` | Bootstrap token for first-time provisioning. |
| `--host`, `-H` | `CODA_HOST` | Bind address (default: `0.0.0.0`). |
| `--port`, `-p` | `CODA_PORT` | Bind port (default: `8080`). |

CLI flags are injected into environment variables before `Settings` is
constructed, so they take highest precedence.

On startup, a banner is printed showing the webapp URL, bind endpoint,
and bootstrap mode (`token` or `env`).

The server runs under uvicorn with `reload=False` and
`log_level="warning"`.

## `coda doctor`

Print a diagnostic summary of the local environment.

```
coda doctor
```

Checks and displays:

| Check | Source |
|---|---|
| WEBAPP | `settings.webapp_url` |
| CONNECT | `settings.connect_url` |
| REDIS | `settings.redis_url` |
| EXECUTOR | `settings.executor_factory` or `"NoopExecutor"` |
| OPENVPN | `shutil.which("openvpn")` |
| VPN IFACE | `detect_tun_interface(hint)` |
| VPN PID | Whether `OPENVPN_PID_PATH` exists |

Useful for verifying that OpenVPN is installed, the VPN interface is
active, and configuration is loaded correctly.

## `coda reset`

Clear all persisted runtime state and stop the VPN daemon.

```
coda reset
```

Actions:

1. Stops the managed OpenVPN daemon (if running).
2. Removes all persisted files:
   - `/tmp/coda.config`
   - `/tmp/coda-private-key`
   - `/tmp/coda-self-service-openvpn.pid`
   - `/tmp/coda-self-service-openvpn.log`
   - `/tmp/coda-self-service.ovpn`
   - Any additional paths referenced in the config file
     (`jwt_private_key_path`, `self_service_vpn_profile_path`).

After reset, the node must be re-bootstrapped with a fresh token.

Also available as a global flag: `coda --reset`.

## `coda stop-vpn`

Stop the managed OpenVPN daemon without clearing credentials.

```
coda stop-vpn
```

Sends `SIGTERM` (POSIX) or `taskkill` (Windows) to the managed
OpenVPN process and removes the PID file. Does not remove the VPN
profile, credentials, or runtime config.

Exit code: `0` if a daemon was stopped, `1` if no managed daemon was
found.

## Entry Points

Both `coda` and `coda-self-service` are registered as console scripts
in `pyproject.toml` and point to the same function:

```toml
[project.scripts]
coda = "self_service.server.cli:main"
coda-self-service = "self_service.server.cli:main"
```
