"""Parameterized planar gasket generation, separate from sealing qualification."""

from efficio.objects.gaskets.face import (
    GasketDesign,
    GasketFace,
    GeneratedGasket,
    KeepOut,
    Opening,
    OpeningRole,
)
from efficio.objects.gaskets.geometry import GasketParameters

__all__ = [
    "GasketDesign",
    "GasketFace",
    "GeneratedGasket",
    "KeepOut",
    "Opening",
    "OpeningRole",
    "GasketParameters",
]
