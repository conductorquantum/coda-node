"""Minimal IR validation for jobs received from Coda."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class NativeGate(StrEnum):
    RX = "rx"
    RY = "ry"
    RZ = "rz"
    CZ = "cz"
    ISWAP = "iswap"
    CP = "cp"
    RXX = "rxx"
    ID = "id"


GATE_SPECS: dict[str, dict[str, int]] = {
    "rx": {"qubits": 1, "params": 1},
    "ry": {"qubits": 1, "params": 1},
    "rz": {"qubits": 1, "params": 1},
    "cz": {"qubits": 2, "params": 0},
    "iswap": {"qubits": 2, "params": 0},
    "cp": {"qubits": 2, "params": 1},
    "rxx": {"qubits": 2, "params": 1},
    "id": {"qubits": 1, "params": 1},
}

LEGAL_GATES: dict[str, set[str]] = {
    "superconducting_cz": {"rx", "ry", "rz", "cz", "id"},
    "superconducting_iswap": {"rx", "ry", "rz", "iswap", "cp", "id"},
    "trapped_ion": {"rx", "ry", "rz", "rxx", "id"},
    "silicon_spin_cz": {"rx", "ry", "rz", "cz", "id"},
}


class GateOp(BaseModel):
    gate: NativeGate
    qubits: list[int]
    params: list[float] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_gate_shape(self) -> GateOp:
        gate = self.gate.value
        if gate in GATE_SPECS:
            expected_qubits = GATE_SPECS[gate]["qubits"]
            if len(self.qubits) != expected_qubits:
                raise ValueError(
                    f"Gate {gate} requires {expected_qubits} qubit(s), got {len(self.qubits)}"
                )

            expected_params = GATE_SPECS[gate]["params"]
            if len(self.params) != expected_params:
                raise ValueError(
                    f"Gate {gate} requires {expected_params} param(s), got {len(self.params)}"
                )
        return self


class IRMetadata(BaseModel):
    source_hash: str
    compiled_at: str
    compiler_version: str = "0.1.0"
    optimization_level: int = Field(ge=0, le=3, default=2)


class NativeGateIR(BaseModel):
    version: Literal["1.0"] = "1.0"
    target: str
    num_qubits: int = Field(ge=1, le=50)
    gates: list[GateOp]
    measurements: list[int]
    metadata: IRMetadata

    @field_validator("target")
    @classmethod
    def validate_target(cls, value: str) -> str:
        if value not in LEGAL_GATES:
            raise ValueError(
                f"Unknown target '{value}'. Valid: {list(LEGAL_GATES.keys())}"
            )
        return value

    @model_validator(mode="after")
    def validate_consistency(self) -> NativeGateIR:
        legal = LEGAL_GATES[self.target]
        for index, op in enumerate(self.gates):
            if op.gate.value not in legal:
                raise ValueError(
                    f"Gate '{op.gate.value}' not legal for target '{self.target}' at index {index}"
                )
            for qubit in op.qubits:
                if qubit < 0 or qubit >= self.num_qubits:
                    raise ValueError(
                        f"Qubit {qubit} out of range [0, {self.num_qubits}) at gate index {index}"
                    )

        for qubit in self.measurements:
            if qubit < 0 or qubit >= self.num_qubits:
                raise ValueError(
                    f"Measurement qubit {qubit} out of range [0, {self.num_qubits})"
                )
        return self

    @classmethod
    def from_json(cls, json_str: str) -> NativeGateIR:
        return cls.model_validate_json(json_str)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)
