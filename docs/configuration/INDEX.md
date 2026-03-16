# Configuration

The runtime is configured through a layered system of environment
variables, persisted state, and defaults. The `Settings` class
(Pydantic Settings) manages resolution and validation.

## Topics

| Document | Summary |
|---|---|
| [settings-reference.md](settings-reference.md) | Complete field reference for the `Settings` class. |
| [environment-variables.md](environment-variables.md) | All `CODA_`-prefixed environment variables. |

## Key Files

| File | Role |
|---|---|
| `src/self_service/server/config.py` | `Settings` class, `load_persisted_runtime_config()`, file paths. |

## Precedence Order

Settings are resolved with the following priority (highest first):

1. **Environment variables** — `CODA_`-prefixed (e.g. `CODA_REDIS_URL`).
2. **Persisted runtime config** — from `/tmp/coda.config` (written
   after successful bootstrap).
3. **Hardcoded defaults** — defined on the `Settings` class.

Persisted values only apply when no `self_service_token` is set and the
environment variable is empty, `None`, or `[]`.

## Validation

The `Settings` model uses `validate_assignment=True` so that
mutations made during bundle application (e.g. `settings.qpu_id = ...`)
are validated against field types.

Two model validators enforce constraints:

### `merge_persisted_runtime_config` (mode="before")

Merges persisted config into the settings dict before field validation.
Skipped when a self-service token is present (to avoid overriding a
fresh bootstrap with stale state).

### `check_jwt_or_self_service` (mode="after")

Requires either:
- A `self_service_token` (for auto-provisioning), or
- Both `jwt_private_key` and `jwt_key_id` (for direct JWT startup).

Raises `ValueError` if neither is available.
