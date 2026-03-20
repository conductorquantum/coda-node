"""Tests for executor loading (factory and noop fallback)."""

from __future__ import annotations

from pathlib import Path

import pytest

from self_service.errors import ExecutorError
from self_service.server.executor import NoopExecutor, load_executor


class TestLoadExecutor:
    def test_executor_factory_import_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CODA_SELF_SERVICE_TOKEN", "test-token")
        monkeypatch.setenv(
            "CODA_EXECUTOR_FACTORY",
            "self_service.server.executor:NoopExecutor",
        )

        from self_service.server.config import Settings

        settings = Settings()
        executor = load_executor(settings)
        assert hasattr(executor, "run")

    def test_no_config_returns_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CODA_SELF_SERVICE_TOKEN", "test-token")
        monkeypatch.delenv("CODA_EXECUTOR_FACTORY", raising=False)

        from self_service.server.config import Settings

        settings = Settings()
        executor = load_executor(settings)
        assert isinstance(executor, NoopExecutor)

    def test_bad_factory_path_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CODA_SELF_SERVICE_TOKEN", "test-token")
        monkeypatch.setenv("CODA_EXECUTOR_FACTORY", "nonexistent.module:factory")

        from self_service.server.config import Settings

        settings = Settings()
        with pytest.raises((ExecutorError, ModuleNotFoundError)):
            load_executor(settings)

    def test_malformed_factory_path_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CODA_SELF_SERVICE_TOKEN", "test-token")
        monkeypatch.setenv("CODA_EXECUTOR_FACTORY", "no_colon_here")

        from self_service.server.config import Settings

        settings = Settings()
        with pytest.raises(ExecutorError, match="must look like"):
            load_executor(settings)
