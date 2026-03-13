"""Webhook client for sending job results back to Coda."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from self_service.server.auth import sign_token

WebhookPayloadValue = dict[str, int] | float | int | str


@dataclass(frozen=True, slots=True)
class WebhookPayload:
    job_id: str
    status: str
    counts: dict[str, int] | None = None
    execution_time_ms: float | None = None
    shots_completed: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, WebhookPayloadValue]:
        result: dict[str, WebhookPayloadValue] = {
            "job_id": self.job_id,
            "status": self.status,
        }
        if self.counts is not None:
            result["counts"] = self.counts
        if self.execution_time_ms is not None:
            result["execution_time_ms"] = self.execution_time_ms
        if self.shots_completed is not None:
            result["shots_completed"] = self.shots_completed
        if self.error is not None:
            result["error"] = self.error
        return result


class WebhookClient:
    """Send signed job results to Coda callback URLs."""

    def __init__(
        self,
        qpu_id: str,
        jwt_private_key: str,
        jwt_key_id: str,
        timeout: float = 30.0,
    ) -> None:
        self._qpu_id = qpu_id
        self._jwt_private_key = jwt_private_key
        self._jwt_key_id = jwt_key_id
        self._client = httpx.AsyncClient(timeout=timeout)

    async def send_result(self, callback_url: str, payload: WebhookPayload) -> None:
        token = sign_token(self._qpu_id, self._jwt_private_key, key_id=self._jwt_key_id)
        response = await self._client.post(
            callback_url,
            json=payload.to_dict(),
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()

    async def send_error(self, callback_url: str, job_id: str, error: str) -> None:
        await self.send_result(
            callback_url,
            WebhookPayload(job_id=job_id, status="failed", error=error),
        )

    async def close(self) -> None:
        await self._client.aclose()
