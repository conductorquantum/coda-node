"""Server runtime package exports."""

from self_service.server.app import app, create_app

__all__ = ["app", "create_app"]
