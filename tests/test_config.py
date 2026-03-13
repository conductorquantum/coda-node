"""Tests for environment-backed settings."""

import pytest

from self_service.server.config import Settings


@pytest.fixture(autouse=True)
def jwt_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CODA_JWT_PRIVATE_KEY",
        "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
    )
    monkeypatch.setenv("CODA_JWT_KEY_ID", "test-key-id")


class TestSettings:
    def test_defaults(self) -> None:
        settings = Settings()
        assert settings.qpu_id == ""
        assert settings.qpu_display_name == ""
        assert settings.port == 8080
        assert settings.self_service_token == ""
        assert settings.self_service_auto_vpn is True

    def test_callback_urls(self) -> None:
        settings = Settings()
        assert (
            settings.callback_url
            == "https://coda.conductorquantum.com/api/internal/qpu/webhook"
        )
        assert (
            settings.register_url
            == "https://coda.conductorquantum.com/api/internal/qpu/register"
        )
        assert (
            settings.heartbeat_url
            == "https://coda.conductorquantum.com/api/internal/qpu/heartbeat"
        )

    def test_custom_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CODA_QPU_ID", "custom-node")
        monkeypatch.setenv("CODA_PORT", "9090")
        monkeypatch.setenv("CODA_SELF_SERVICE_TOKEN", "token")
        monkeypatch.setenv("CODA_WEBAPP_URL", "https://example.test")
        monkeypatch.setenv("CODA_EXECUTOR_FACTORY", "pkg.module:create_executor")
        settings = Settings()
        assert settings.qpu_id == "custom-node"
        assert settings.port == 9090
        assert settings.self_service_token == "token"
        assert settings.webapp_url == "https://example.test"
        assert settings.executor_factory == "pkg.module:create_executor"

    def test_empty_jwt_without_self_service_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CODA_JWT_PRIVATE_KEY", "")
        monkeypatch.setenv("CODA_JWT_KEY_ID", "")
        monkeypatch.delenv("CODA_SELF_SERVICE_TOKEN", raising=False)
        with pytest.raises(Exception, match="CODA_JWT_PRIVATE_KEY must be set"):
            Settings()

    def test_empty_jwt_with_self_service_is_allowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CODA_JWT_PRIVATE_KEY", "")
        monkeypatch.setenv("CODA_JWT_KEY_ID", "")
        monkeypatch.setenv("CODA_SELF_SERVICE_TOKEN", "self-service-token")
        settings = Settings()
        assert settings.self_service_token == "self-service-token"
