"""Tests for the CLI entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from self_service.server import cli


def test_build_parser_supports_start_flags() -> None:
    args = cli._build_parser().parse_args(
        ["start", "--token", "test-token", "-p", "9000"]
    )

    assert args.command == "start"
    assert args.self_service_token == "test-token"
    assert args.port == 9000


def test_build_parser_supports_explicit_start_short_flags() -> None:
    args = cli._build_parser().parse_args(
        ["start", "-t", "test-token", "-H", "127.0.0.1"]
    )

    assert args.command == "start"
    assert args.self_service_token == "test-token"
    assert args.host == "127.0.0.1"


def test_build_parser_supports_top_level_reset_flag() -> None:
    args = cli._build_parser().parse_args(["--reset"])

    assert args.reset is True
    assert args.command is None


def test_main_runs_server_with_start_subcommand(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli, "Settings", MagicMock(return_value=MagicMock(host="0.0.0.0", port=8080))
    )
    mock_run = MagicMock()
    fake_env: dict[str, str] = {}
    monkeypatch.setattr(cli.os, "environ", fake_env)
    monkeypatch.setattr(cli.uvicorn, "run", mock_run)
    monkeypatch.setattr("sys.argv", ["coda", "start", "--token", "token-value"])

    cli.main()
    output = capsys.readouterr().out

    assert fake_env["CODA_SELF_SERVICE_TOKEN"] == "token-value"
    assert "C O D A  ·  N O D E" in output
    assert "MODE" in output
    mock_run.assert_called_once_with(
        "self_service.server.app:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="warning",
    )


def test_main_resets_persisted_runtime_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "coda.config"
    key_path = tmp_path / "coda-private-key"
    profile_path = tmp_path / "custom.ovpn"
    pid_path = tmp_path / "coda.pid"
    log_path = tmp_path / "coda.log"

    config_path.write_text(
        json.dumps(
            {
                "jwt_private_key_path": str(key_path),
                "self_service_vpn_profile_path": str(profile_path),
            }
        )
    )
    key_path.write_text("private-key")
    profile_path.write_text("client")
    pid_path.write_text("1234")
    log_path.write_text("log")

    monkeypatch.setattr(cli, "PERSISTED_CONFIG_PATH", config_path)
    monkeypatch.setattr(cli, "PERSISTED_PRIVATE_KEY_PATH", key_path)
    monkeypatch.setattr(cli, "OPENVPN_PID_PATH", pid_path)
    monkeypatch.setattr(cli, "OPENVPN_LOG_PATH", log_path)
    monkeypatch.setattr(cli, "kill_openvpn_daemon", MagicMock(return_value=True))
    monkeypatch.setattr("sys.argv", ["coda", "--reset"])

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    output = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "Resetting persisted Coda runtime state..." in output
    assert not config_path.exists()
    assert not key_path.exists()
    assert not profile_path.exists()
    assert not pid_path.exists()
    assert not log_path.exists()
