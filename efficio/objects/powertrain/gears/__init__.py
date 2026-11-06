"""Involute spur gear geometry (pure) and solid gear parts."""

from efficio.objects.powertrain.gears.crown import CrownGear
from efficio.objects.powertrain.gears.face import FaceGearGeometry, crown_mesh_phase
from efficio.objects.powertrain.gears.involute import (
    InvoluteGearGeometry,
    centre_distance,
    involute_function,
    mesh_phase,
)
from efficio.objects.powertrain.gears.spur import CompoundSpurGear, SpurGear

__all__ = [
    "CompoundSpurGear",
    "CrownGear",
    "FaceGearGeometry",
    "crown_mesh_phase",
    "InvoluteGearGeometry",
    "SpurGear",
    "centre_distance",
    "involute_function",
    "mesh_phase",
]
