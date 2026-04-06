"""Tests for device topology helpers."""

from coda_node.server.device_topology import resolve_connectivity_from_device_spec


class _FakeDevice:
    def __init__(
        self, directed: list[tuple[int, int]] | None, logical: list[tuple[int, int]]
    ) -> None:
        self.directed_edges = directed
        self.logical_edges = logical


def test_prefers_directed_edges() -> None:
    spec = _FakeDevice([(1, 0), (2, 1)], [(0, 1)])
    assert resolve_connectivity_from_device_spec(spec) == [[1, 0], [2, 1]]


def test_falls_back_to_logical_edges() -> None:
    spec = _FakeDevice(None, [(0, 1), (1, 2)])
    assert resolve_connectivity_from_device_spec(spec) == [[0, 1], [1, 2]]


def test_none_spec() -> None:
    assert resolve_connectivity_from_device_spec(None) is None
