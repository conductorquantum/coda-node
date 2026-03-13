"""Small CLI for serving and inspecting the node runtime."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
from pathlib import Path

import uvicorn

from self_service.server.config import Settings
from self_service.vpn import (
    OPENVPN_PID_PATH,
    _detect_tun_interface,
    kill_openvpn_daemon,
)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _build_parser() -> argparse.ArgumentParser:
    start_parent = argparse.ArgumentParser(add_help=False)
    start_parent.add_argument("-H", "--host")
    start_parent.add_argument("-p", "--port", type=int)
    start_parent.add_argument("-t", "--token", dest="self_service_token")

    parser = argparse.ArgumentParser(prog="coda")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "start", parents=[start_parent], help="Run the FastAPI server"
    )

    subparsers.add_parser("doctor", help="Print basic runtime checks")
    subparsers.add_parser("stop-vpn", help="Stop the managed OpenVPN process")
    return parser


def _apply_overrides(args: argparse.Namespace) -> None:
    host = getattr(args, "host", None)
    port = getattr(args, "port", None)
    self_service_token = getattr(args, "self_service_token", None)

    if host:
        os.environ["CODA_HOST"] = host
    if port is not None:
        os.environ["CODA_PORT"] = str(port)
    if self_service_token:
        os.environ["CODA_SELF_SERVICE_TOKEN"] = self_service_token


def _doctor() -> int:
    settings = Settings()
    openvpn_bin = shutil.which("openvpn") or shutil.which("openvpn.exe")
    iface = _detect_tun_interface(settings.vpn_interface_hint)
    pid_exists = Path(OPENVPN_PID_PATH).exists()

    print(f"webapp url:       {settings.webapp_url}")
    print(f"register url:     {settings.register_url}")
    print(f"redis url:        {settings.redis_url}")
    print(f"executor factory: {settings.executor_factory or 'NoopExecutor'}")
    print(f"openvpn binary:   {openvpn_bin or 'not found'}")
    print(f"vpn interface:    {iface or 'not detected'}")
    print(f"vpn pid file:     {'present' if pid_exists else 'absent'}")
    return 0


def main() -> None:
    _configure_logging()
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "start":
        _apply_overrides(args)
        settings = Settings()
        uvicorn.run(
            "self_service.server.app:app",
            host=settings.host,
            port=settings.port,
            reload=False,
        )
        return

    if args.command == "doctor":
        raise SystemExit(_doctor())

    if args.command == "stop-vpn":
        raise SystemExit(0 if kill_openvpn_daemon() else 1)
