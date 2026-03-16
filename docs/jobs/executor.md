# Execution Backends

The `JobExecutor` protocol defines the interface that all execution
backends must implement. The consumer is backend-agnostic — it only
calls `executor.run(ir, shots)`.

## JobExecutor Protocol

```python
class JobExecutor(Protocol):
    async def run(self, ir: NativeGateIR, shots: int) -> ExecutionResult:
        ...
```

### ExecutionResult

```python
@dataclass(frozen=True, slots=True)
class ExecutionResult:
    counts: dict[str, int]      # bitstring → count
    execution_time_ms: float    # wall-clock time
    shots_completed: int        # actual shots executed
```

The `counts` dictionary maps bitstrings (e.g. `"010"`) to the number
of times that outcome was observed. `shots_completed` may differ from
the requested `shots` if the backend applies shot budgeting.

## NoopExecutor

The built-in `NoopExecutor` returns a deterministic all-zeros result:

```python
class NoopExecutor:
    async def run(self, ir: NativeGateIR, shots: int) -> ExecutionResult:
        bitstring = "0" * len(ir.measurements)
        return ExecutionResult(
            counts={bitstring: shots},
            execution_time_ms=0.0,
            shots_completed=shots,
        )
```

Used when `CODA_EXECUTOR_FACTORY` is unset, allowing the service to
boot for integration testing without hardware.

## Custom Executor

### Configuration

Set `CODA_EXECUTOR_FACTORY` to a `module:attribute` import path:

```bash
export CODA_EXECUTOR_FACTORY="my_project.executor:create_executor"
```

### Resolution Order

`load_executor()` resolves the target in this order:

1. If `executor_factory` is empty → `NoopExecutor` with a warning.
2. Import the dotted module path and retrieve the named attribute.
3. If the target has a `.run` method → use it directly as an executor.
4. If the target is callable → call it as a factory:
   - If the factory accepts parameters → pass `settings`.
   - If the factory accepts no parameters → call with no args.
5. Validate the result has a `.run` method.

### Example: Simple Executor

```python
from self_service.server.executor import ExecutionResult
from self_service.server.ir import NativeGateIR


class MyExecutor:
    async def run(self, ir: NativeGateIR, shots: int) -> ExecutionResult:
        counts = await run_on_hardware(ir, shots)
        return ExecutionResult(
            counts=counts,
            execution_time_ms=42.0,
            shots_completed=shots,
        )
```

```bash
export CODA_EXECUTOR_FACTORY="my_project:MyExecutor"
```

### Example: Factory with Settings

```python
from self_service.server.config import Settings
from self_service.server.executor import ExecutionResult
from self_service.server.ir import NativeGateIR


class HardwareExecutor:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port

    async def run(self, ir: NativeGateIR, shots: int) -> ExecutionResult:
        ...


def create_executor(settings: Settings) -> HardwareExecutor:
    return HardwareExecutor(
        host=settings.opx_host,
        port=settings.opx_port,
    )
```

```bash
export CODA_EXECUTOR_FACTORY="my_project:create_executor"
```

## Error Handling

- `ExecutorError` is raised for invalid import paths, non-callable
  targets, and factories that don't return a valid runner.
- Exceptions thrown during `executor.run()` are caught by the consumer,
  logged, and reported as failed jobs via webhook.
