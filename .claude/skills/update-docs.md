# Skill: update-docs

Keep `docs/` and `README.md` in sync with source code changes.

## Documentation structure

```
docs/
├── INDEX.md                      # Top-level overview, architecture diagram, source layout
├── self-service/                 # Provisioning & reconnect
│   ├── INDEX.md
│   ├── connect-protocol.md
│   ├── token-lifecycle.md
│   └── credential-persistence.md
├── vpn/                          # OpenVPN tunnel management
│   ├── INDEX.md
│   ├── tunnel-lifecycle.md
│   ├── health-monitoring.md
│   └── cloud-infrastructure.md
├── jobs/                         # Job execution pipeline
│   ├── INDEX.md
│   ├── consumer.md
│   ├── ir-schema.md
│   └── executor.md
├── webhooks/                     # Result delivery
│   ├── INDEX.md
│   ├── delivery.md
│   └── payload-format.md
├── auth/                         # JWT authentication
│   ├── INDEX.md
│   ├── signing.md
│   └── keypair-lifecycle.md
├── configuration/                # Settings & env vars
│   ├── INDEX.md
│   ├── settings-reference.md
│   └── environment-variables.md
└── operations/                   # Runtime operations
    ├── INDEX.md
    ├── health-endpoints.md
    ├── graceful-shutdown.md
    ├── cli.md
    └── error-handling.md
```

## Conventions

- Each feature area has its own subdirectory with an `INDEX.md`.
- `INDEX.md` files contain: overview, topics table, key source files table, and cloud counterparts (if any).
- Topic files document: purpose, API/format details, code references, and cross-links.
- Use "self-service" (not "bootstrap") for provisioning terminology.
- Cloud-side DB identifiers (e.g. `prepare_qpu_device_from_bootstrap_token`) keep their original names with a "(cloud-side naming)" annotation.
- `README.md` is the user-facing quickstart; `docs/` is the comprehensive reference.

## How to update

1. **Identify what changed**: read the staged diff (`git diff --cached`) and determine which source files were modified.
2. **Map files to doc areas**:
   - `server/app.py` → `operations/health-endpoints.md`, `operations/graceful-shutdown.md`
   - `server/auth.py` → `auth/signing.md`, `auth/keypair-lifecycle.md`
   - `server/cli.py` → `operations/cli.md`
   - `server/config.py` → `configuration/settings-reference.md`, `configuration/environment-variables.md`
   - `server/consumer.py` → `jobs/consumer.md`
   - `server/executor.py` → `jobs/executor.md`
   - `server/ir.py` → `jobs/ir-schema.md`
   - `server/webhook.py` → `webhooks/delivery.md`, `webhooks/payload-format.md`
   - `vpn/service.py` → `self-service/connect-protocol.md`, `self-service/credential-persistence.md`, `vpn/tunnel-lifecycle.md`
   - `vpn/guard.py` → `vpn/health-monitoring.md`
   - `errors.py` → `operations/error-handling.md`
   - `pyproject.toml` → `README.md` (dependencies, scripts)
3. **Read the affected doc files** and the changed source to understand the delta.
4. **Update docs** to reflect new/changed behavior: signatures, config fields, env vars, error types, sequence diagrams.
5. **Update `README.md`** if the change affects quickstart, configuration tables, CLI flags, endpoints, or error hierarchy.
6. **Update `docs/INDEX.md`** if you add/remove/rename a feature area or the source layout changes.
7. **Print a short summary** of what was updated and why.

## Rules

- Do NOT create new feature subdirectories without clear justification.
- Do NOT add speculative documentation for unimplemented features.
- Keep doc files concise — describe behavior, not implementation details line-by-line.
- Every doc file must have a `# Title` and be linked from its area's `INDEX.md`.
- If no docs need updating (e.g. test-only changes, formatting), say so and exit.
