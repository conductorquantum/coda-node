"""Redis stream consumer for Coda job execution."""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, TypeVar, cast

import redis.asyncio as aioredis

from self_service.server.ir import NativeGateIR
from self_service.server.webhook import WebhookPayload

if TYPE_CHECKING:
    from self_service.server.executor import JobExecutor
    from self_service.server.webhook import WebhookClient

logger = logging.getLogger(__name__)
T = TypeVar("T")


async def _await_if_needed(value: T | Awaitable[T]) -> T:
    if inspect.isawaitable(value):
        return await cast(Awaitable[T], value)
    return value


@dataclass(slots=True)
class Job:
    id: str
    ir: NativeGateIR
    shots: int
    callback_url: str
    message_id: str
    retry_count: int = 0


class RedisConsumer:
    """Consume jobs from a Coda Redis stream and dispatch to an executor."""

    def __init__(
        self,
        redis: aioredis.Redis,
        runner: JobExecutor,
        webhook: WebhookClient,
        qpu_id: str,
        consumer_name: str = "worker-0",
        crash_recovery_threshold_ms: int = 60_000,
    ) -> None:
        self._redis = redis
        self._runner = runner
        self._webhook = webhook
        self._qpu_id = qpu_id
        self._consumer_name = consumer_name
        self._crash_recovery_threshold_ms = crash_recovery_threshold_ms
        self._stream = f"qpu:{qpu_id}:jobs"
        self._group = f"qpu:{qpu_id}:workers"
        self._running = False
        self.current_job_id: str | None = None
        self.last_job_at: str | None = None
        self.redis_healthy = True

    async def setup(self) -> None:
        try:
            await self._redis.xgroup_create(
                name=self._stream,
                groupname=self._group,
                id="0",
                mkstream=True,
            )
        except aioredis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def recover_pending(self) -> int:
        recovered = 0
        pending = await self._redis.xpending_range(
            name=self._stream,
            groupname=self._group,
            consumername=self._consumer_name,
            min="-",
            max="+",
            count=100,
        )

        for entry in pending:
            message_id = entry["message_id"]
            idle_ms = entry["time_since_delivered"]
            if idle_ms < self._crash_recovery_threshold_ms:
                continue

            messages = await self._redis.xrange(
                self._stream, min=message_id, max=message_id
            )
            if messages:
                _, fields = messages[0]
                await self._process_message(message_id, fields)
                recovered += 1

        return recovered

    async def consume_loop(self) -> None:
        self._running = True
        await self.setup()
        await self.recover_pending()

        while self._running:
            try:
                messages = await self._redis.xreadgroup(
                    groupname=self._group,
                    consumername=self._consumer_name,
                    streams={self._stream: ">"},
                    count=1,
                    block=5000,
                )
                self.redis_healthy = True

                if not messages:
                    continue

                for _stream_name, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        await self._process_message(message_id, fields)
            except (ConnectionError, OSError, aioredis.ConnectionError):
                self.redis_healthy = False
                logger.warning("Redis connection lost, retrying in 5s")
                await asyncio.sleep(5)
            except Exception:
                logger.exception("Consumer loop error")
                await asyncio.sleep(1)

    def stop(self) -> None:
        self._running = False

    async def _process_message(self, message_id: str, fields: dict[str, str]) -> None:
        job_id = fields["job_id"]
        callback_url = fields["callback_url"]

        status = await _await_if_needed(
            self._redis.hget(f"qpu:job:{job_id}:status", "state")
        )
        if status in ("completed", b"completed"):
            await self._redis.xack(self._stream, self._group, message_id)
            return

        self.current_job_id = job_id
        await _await_if_needed(
            self._redis.hset(
                f"qpu:job:{job_id}:status",
                mapping={
                    "state": "executing",
                    "started_at": datetime.now(UTC).isoformat(),
                    "message_id": message_id,
                    "qpu_id": self._qpu_id,
                },
            )
        )

        try:
            ir = NativeGateIR.from_json(fields["ir_json"])
            shots = int(fields["shots"])
            result = await self._runner.run(ir, shots)

            await _await_if_needed(
                self._redis.hset(
                    f"qpu:job:{job_id}:status",
                    mapping={
                        "state": "completed",
                        "completed_at": datetime.now(UTC).isoformat(),
                    },
                )
            )

            payload = WebhookPayload(
                job_id=job_id,
                status="completed",
                counts=result.counts,
                execution_time_ms=result.execution_time_ms,
                shots_completed=result.shots_completed,
            )
            await self._webhook.send_result(callback_url, payload)
            self.last_job_at = datetime.now(UTC).isoformat()
        except Exception as exc:
            logger.error("Job %s failed: %s", job_id, exc, exc_info=True)
            await _await_if_needed(
                self._redis.hset(
                    f"qpu:job:{job_id}:status",
                    mapping={
                        "state": "failed",
                        "error": str(exc)[:500],
                        "failed_at": datetime.now(UTC).isoformat(),
                    },
                )
            )
            try:
                await self._webhook.send_error(callback_url, job_id, str(exc)[:500])
            except Exception:
                logger.exception("Failed to send error webhook for job %s", job_id)
        finally:
            await self._redis.xack(self._stream, self._group, message_id)
            self.current_job_id = None
