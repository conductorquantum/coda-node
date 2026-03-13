"""VPN preflight and ongoing health monitoring."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import socket
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    BOOTING = "booting"
    VPN_UNAVAILABLE = "vpn_unavailable"
    READY = "ready"
    DEGRADED = "degraded"


@dataclass(frozen=True)
class ProbeResult:
    target: str
    ok: bool
    latency_ms: float | None = None
    error: str | None = None


@dataclass(frozen=True)
class VPNStatus:
    ok: bool
    interface_found: bool
    probes: list[ProbeResult] = field(default_factory=list)
    reason: str = ""


def _parse_darwin_tun_interfaces(ifconfig_output: str) -> str | None:
    current_iface: str | None = None
    for line in ifconfig_output.splitlines():
        if line and not line[0].isspace():
            current_iface = line.split(":")[0]
        elif current_iface and current_iface.startswith(("utun", "tun")):
            if line.strip().startswith("inet "):
                return current_iface
    return None


def _parse_windows_tun_interfaces(
    adapter_json: str, hint: str | None = None
) -> str | None:
    try:
        raw_adapters = json.loads(adapter_json)
    except json.JSONDecodeError:
        return None

    if isinstance(raw_adapters, dict):
        adapters = [raw_adapters]
    elif isinstance(raw_adapters, list):
        adapters = raw_adapters
    else:
        return None

    hint_lower = hint.lower() if hint else None
    for adapter in adapters:
        if not isinstance(adapter, dict):
            continue

        name = adapter.get("Name")
        description = adapter.get("InterfaceDescription")
        status = adapter.get("Status")
        if not isinstance(name, str) or not isinstance(description, str):
            continue
        if not isinstance(status, str) or status.lower() != "up":
            continue
        if (
            hint_lower
            and hint_lower not in name.lower()
            and hint_lower not in description.lower()
        ):
            continue

        description_lower = description.lower()
        if any(
            marker in description_lower
            for marker in ("tap-windows", "wintun", "openvpn", "tap adapter")
        ):
            return name
    return None


def _detect_tun_interface(hint: str | None = None) -> str | None:
    """Return the active VPN interface name, if one is detectable."""
    system = platform.system()

    if hint:
        try:
            if system == "Darwin":
                result = subprocess.run(
                    ["ifconfig", hint],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            elif system == "Windows":
                result = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        (
                            "Get-NetAdapter -IncludeHidden | "
                            "Select-Object Name,InterfaceDescription,Status | "
                            "ConvertTo-Json -Compress"
                        ),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            else:
                result = subprocess.run(
                    ["ip", "link", "show", hint],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

            if system == "Windows":
                return _parse_windows_tun_interfaces(result.stdout, hint)
            if result.returncode == 0 and (
                "UP" in result.stdout or "up" in result.stdout
            ):
                return hint
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        return None

    try:
        if system == "Darwin":
            result = subprocess.run(
                ["ifconfig"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return _parse_darwin_tun_interfaces(result.stdout)

        if system == "Windows":
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    (
                        "Get-NetAdapter -IncludeHidden | "
                        "Select-Object Name,InterfaceDescription,Status | "
                        "ConvertTo-Json -Compress"
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return _parse_windows_tun_interfaces(result.stdout)

        result = subprocess.run(
            ["ip", "-o", "link", "show", "type", "tun"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 2:
                return parts[1].strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    return None


async def _probe_target(url: str, timeout: float = 5.0) -> ProbeResult:
    import time

    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=True) as client:
            response = await client.head(url)
            latency_ms = round((time.monotonic() - started) * 1000, 1)
            return ProbeResult(
                target=url,
                ok=response.status_code < 500,
                latency_ms=latency_ms,
            )
    except Exception as exc:
        latency_ms = round((time.monotonic() - started) * 1000, 1)
        return ProbeResult(
            target=url,
            ok=False,
            latency_ms=latency_ms,
            error=str(exc)[:200],
        )


def _resolve_host(hostname: str) -> bool:
    try:
        socket.getaddrinfo(hostname, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
        return True
    except (OSError, socket.gaierror):
        return False


class VPNGuard:
    """Monitor VPN health and expose readiness state."""

    def __init__(
        self,
        probe_targets: list[str] | None = None,
        interface_hint: str | None = None,
        check_interval_sec: int = 10,
        vpn_required: bool = True,
    ) -> None:
        self._probe_targets = probe_targets or []
        self._interface_hint = interface_hint
        self._check_interval = check_interval_sec
        self._vpn_required = vpn_required
        self._state = ServiceState.BOOTING
        self._running = False

    @property
    def state(self) -> ServiceState:
        return self._state

    @property
    def is_ready(self) -> bool:
        return self._state == ServiceState.READY

    async def preflight(self) -> VPNStatus:
        iface = await asyncio.to_thread(_detect_tun_interface, self._interface_hint)
        interface_found = iface is not None

        if not interface_found and self._vpn_required:
            self._state = ServiceState.VPN_UNAVAILABLE
            return VPNStatus(
                ok=False,
                interface_found=False,
                reason="No VPN tunnel interface detected",
            )

        dns_failures: list[str] = []
        for target in self._probe_targets:
            hostname = urlparse(target).hostname
            if hostname and not await asyncio.to_thread(_resolve_host, hostname):
                dns_failures.append(hostname)

        if dns_failures and self._vpn_required:
            self._state = ServiceState.VPN_UNAVAILABLE
            return VPNStatus(
                ok=False,
                interface_found=interface_found,
                reason=f"DNS resolution failed for: {', '.join(dns_failures)}",
            )

        probes: list[ProbeResult] = []
        for target in self._probe_targets:
            probes.append(await _probe_target(target))

        failed = [probe for probe in probes if not probe.ok]
        if failed and self._vpn_required:
            self._state = ServiceState.VPN_UNAVAILABLE
            reasons = "; ".join(
                f"{probe.target}: {probe.error or 'unreachable'}" for probe in failed
            )
            return VPNStatus(
                ok=False,
                interface_found=interface_found,
                probes=probes,
                reason=f"Probe failures: {reasons}",
            )

        self._state = ServiceState.READY
        return VPNStatus(ok=True, interface_found=interface_found, probes=probes)

    async def watch(
        self,
        on_change: Callable[[ServiceState], Awaitable[None]] | None = None,
    ) -> None:
        self._running = True
        while self._running:
            await asyncio.sleep(self._check_interval)
            previous = self._state
            status = await self.preflight()

            if status.ok and previous not in (ServiceState.READY, ServiceState.BOOTING):
                if on_change:
                    await on_change(ServiceState.READY)
            elif not status.ok and previous == ServiceState.READY:
                self._state = ServiceState.DEGRADED
                if on_change:
                    await on_change(ServiceState.DEGRADED)

    def stop(self) -> None:
        self._running = False


def validate_key_permissions(path: str) -> bool:
    try:
        if platform.system() == "Windows":
            return os.path.isfile(path)
        mode = os.stat(path).st_mode & 0o777
        return mode in (0o600, 0o400)
    except OSError:
        return False
