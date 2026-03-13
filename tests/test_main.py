"""Tests for the FastAPI application surface."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from self_service.server.app import create_app
from self_service.vpn import ServiceState, VPNGuard


def test_health_endpoint() -> None:
    app = create_app()
    guard = VPNGuard(vpn_required=False)
    guard._state = ServiceState.READY
    consumer = MagicMock()
    consumer.redis_healthy = True
    consumer.current_job_id = None
    app.state.guard = guard
    app.state.consumer = consumer
    app.state.settings = MagicMock()
    app.state.webhook = AsyncMock()

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_endpoint() -> None:
    app = create_app()
    guard = VPNGuard(vpn_required=False)
    guard._state = ServiceState.READY
    consumer = MagicMock()
    consumer.redis_healthy = True
    consumer.current_job_id = "job-123"
    app.state.guard = guard
    app.state.consumer = consumer
    app.state.settings = MagicMock()
    app.state.webhook = AsyncMock()

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {
        "ready": True,
        "vpn_state": "ready",
        "redis_healthy": True,
        "current_job": "job-123",
    }
