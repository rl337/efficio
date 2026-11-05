"""Involute spur gear geometry (pure) and solid gear parts."""

from efficio.objects.powertrain.gears.involute import (
    InvoluteGearGeometry,
    centre_distance,
    involute_function,
    mesh_phase,
)
from efficio.objects.powertrain.gears.spur import CompoundSpurGear, SpurGear

__all__ = [
    "CompoundSpurGear",
    "InvoluteGearGeometry",
    "SpurGear",
    "centre_distance",
    "involute_function",
    "mesh_phase",
]
