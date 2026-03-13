"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import tempfile

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Coda-connected node configuration."""

    qpu_id: str = ""
    qpu_display_name: str = ""
    native_gate_set: str = "superconducting_cz"
    num_qubits: int = 5

    redis_url: str = ""

    jwt_private_key: str = ""
    jwt_key_id: str = ""

    webapp_url: str = Field(
        default="https://coda.conductorquantum.com",
        validation_alias="CODA_WEBAPP_URL",
    )
    webhook_path: str = "/api/internal/qpu/webhook"
    register_path: str = "/api/internal/qpu/register"
    heartbeat_path: str = "/api/internal/qpu/heartbeat"
    self_service_path: str = "/api/internal/qpu/self-service"

    host: str = "0.0.0.0"
    port: int = 8080

    vpn_required: bool = True
    vpn_check_interval_sec: int = 10
    vpn_probe_targets: list[str] = []
    vpn_interface_hint: str | None = None
    allow_degraded_startup: bool = False

    self_service_token: str = ""
    self_service_timeout_sec: int = 15
    self_service_machine_fingerprint: str = ""
    self_service_auto_vpn: bool = True
    self_service_vpn_profile_path: str = (
        f"{tempfile.gettempdir()}/coda-self-service.ovpn"
    )

    executor_factory: str = ""
    advertised_provider: str = "conductor_quantum"

    opx_host: str = "localhost"

    @model_validator(mode="after")
    def check_jwt_or_self_service(self) -> Settings:
        """Require JWT credentials unless self-service will supply them."""
        if not self.self_service_token:
            if not self.jwt_private_key:
                raise ValueError(
                    "CODA_JWT_PRIVATE_KEY must be set "
                    "(or provide CODA_SELF_SERVICE_TOKEN for auto-provisioning)"
                )
            if not self.jwt_key_id:
                raise ValueError(
                    "CODA_JWT_KEY_ID must be set "
                    "(or provide CODA_SELF_SERVICE_TOKEN for auto-provisioning)"
                )
        return self

    @property
    def callback_url(self) -> str:
        return f"{self.webapp_url}{self.webhook_path}"

    @property
    def register_url(self) -> str:
        return f"{self.webapp_url}{self.register_path}"

    @property
    def heartbeat_url(self) -> str:
        return f"{self.webapp_url}{self.heartbeat_path}"

    @property
    def vpn_probe_urls(self) -> list[str]:
        if self.vpn_probe_targets:
            return list(self.vpn_probe_targets)
        return [self.register_url, self.heartbeat_url]

    model_config = {"env_prefix": "CODA_"}
