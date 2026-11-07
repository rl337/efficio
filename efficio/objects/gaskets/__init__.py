"""Parameterized planar gasket generation, separate from sealing qualification."""

from .face import (
    GasketDesign,
    GasketFace,
    GeneratedGasket,
    KeepOut,
    Opening,
    OpeningRole,
)
from .geometry import GasketParameters

__all__ = [
    "GasketDesign",
    "GasketFace",
    "GeneratedGasket",
    "KeepOut",
    "Opening",
    "OpeningRole",
    "GasketParameters",
]
