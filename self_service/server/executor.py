"""Execution backend protocol and loader."""

from __future__ import annotations

import importlib
import inspect
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from self_service.server.ir import NativeGateIR

if TYPE_CHECKING:
    from self_service.server.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    counts: dict[str, int]
    execution_time_ms: float
    shots_completed: int


class JobExecutor(Protocol):
    async def run(self, ir: NativeGateIR, shots: int) -> ExecutionResult:
        """Execute a Coda job and return measurement counts."""


class NoopExecutor:
    """Deterministic executor used for scaffolding and integration smoke tests."""

    async def run(self, ir: NativeGateIR, shots: int) -> ExecutionResult:
        bitstring = "0" * len(ir.measurements)
        return ExecutionResult(
            counts={bitstring: shots},
            execution_time_ms=0.0,
            shots_completed=shots,
        )


def _load_attr(import_path: str) -> Any:
    module_name, sep, attr_name = import_path.partition(":")
    if not sep or not module_name or not attr_name:
        raise ValueError(
            "CODA_EXECUTOR_FACTORY must look like 'package.module:factory_name'"
        )
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


def load_executor(settings: Settings) -> JobExecutor:
    """Load a configured executor factory or fall back to ``NoopExecutor``."""
    if not settings.executor_factory:
        logger.warning("CODA_EXECUTOR_FACTORY unset; using NoopExecutor")
        return NoopExecutor()

    target = _load_attr(settings.executor_factory)
    if hasattr(target, "run"):
        return cast(JobExecutor, target)

    if not callable(target):
        raise TypeError(
            f"Executor target {settings.executor_factory!r} is not callable"
        )

    parameters = inspect.signature(target).parameters
    executor = target(settings) if parameters else target()
    if not hasattr(executor, "run"):
        raise TypeError(
            f"Executor factory {settings.executor_factory!r} did not return a runner"
        )
    return cast(JobExecutor, executor)
