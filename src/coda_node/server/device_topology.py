"""Extract qubit connectivity from an executor device spec for cloud reporting."""

from __future__ import annotations

__all__ = ["resolve_connectivity_from_device_spec"]


def resolve_connectivity_from_device_spec(device_spec: object | None) -> list[list[int]] | None:
    """Extract qubit connectivity from a device spec, preferring directed edges.

    Matches the shape sent in node heartbeats and connect payloads.
    """
    if device_spec is None:
        return None
    directed = getattr(device_spec, "directed_edges", None)
    if directed:
        return [list(e) for e in directed]
    return [list(e) for e in device_spec.logical_edges]  # type: ignore[attr-defined]
