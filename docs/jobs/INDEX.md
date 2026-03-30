# Job Execution

The job execution pipeline connects Redis Streams to a pluggable
execution backend. It handles the full lifecycle: reading messages,
deserializing circuits, dispatching to hardware, reporting results,
and acknowledging messages.

## Topics

| Document | Summary |
|---|---|
| [CONSUMER.md](CONSUMER.md) | `RedisConsumer` — stream consumption, consumer groups, crash recovery, resilience. |
| [IR_SCHEMA.md](IR_SCHEMA.md) | `NativeGateIR` — circuit format, validation, gate sets, and target hardware. |
| [EXECUTOR.md](EXECUTOR.md) | `JobExecutor` protocol, `NoopExecutor`, device config, and custom backend integration. |

## Key Files

| File | Role |
|---|---|
| `src/coda_node/server/consumer.py` | `RedisConsumer` — main consume loop, message processing, status tracking. |
| `src/coda_node/server/ir.py` | `NativeGateIR`, `GateOp`, `IRMetadata` — circuit schema and validation. |
| `src/coda_node/server/executor.py` | `JobExecutor` protocol, `NoopExecutor`, `load_executor()`. |

## Job Lifecycle

```
Cloud enqueues          Node consumes            Node reports
─────────────          ──────────────           ─────────────
XADD to                XREADGROUP               POST webhook
qpu:{id}:jobs  ──►     parse IR        ──►      to callback_url
                       execute(ir, shots)
                       XACK message
```

### Message Flow

1. The Coda cloud enqueues a job as a Redis Stream message on
   `qpu:{qpu_id}:jobs`.
2. The `RedisConsumer` reads the message via `XREADGROUP` using a
   consumer group (`qpu:{qpu_id}:workers`).
3. The message is parsed into a `NativeGateIR` circuit.
4. The circuit is dispatched to the `JobExecutor`.
5. If the cloud cancels the job mid-flight, the node marks it
   `cancelled` and skips webhook delivery.
6. Otherwise, the result (or error) is sent back via webhook.
7. The message is `XACK`-ed.

### Message Fields

| Field | Type | Description |
|---|---|---|
| `job_id` | `string` | Unique job identifier. |
| `callback_url` | `string` | URL to POST the result back to. |
| `ir_json` | `string` | JSON-encoded `NativeGateIR` circuit. |
| `shots` | `string` | Number of measurement shots (parsed as int). |

### Job Status Tracking

Job progress is tracked in Redis hashes at `qpu:job:{job_id}:status`:

| State | When |
|---|---|
| `executing` | Job picked up, executor running. |
| `cancelled` | Cloud-side cancel signal observed before terminal webhook delivery. |
| `completed` | Execution succeeded, webhook sent. |
| `failed` | Execution or webhook failed. |
