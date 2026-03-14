"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from self_service.server import config as config_module


@pytest.fixture(autouse=True)
def _isolate_persisted_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Prevent tests from reading or writing real persisted state."""
    monkeypatch.setattr(
        config_module, "PERSISTED_CONFIG_PATH", tmp_path / "coda.config"
    )
    monkeypatch.setattr(
        config_module, "PERSISTED_PRIVATE_KEY_PATH", tmp_path / "coda-private-key"
    )
