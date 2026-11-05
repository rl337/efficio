"""Spur-gear (planet-pair) differential: pure geometry plus solid parts."""

from efficio.objects.powertrain.differential.geometry import (
    PlanetPose,
    SpurDifferentialGeometry,
)
from efficio.objects.powertrain.differential.parts import (
    SpurDifferentialCarrierHalf,
    planet_gear,
    ring_gear,
    sun_gear,
)

__all__ = [
    "PlanetPose",
    "SpurDifferentialCarrierHalf",
    "SpurDifferentialGeometry",
    "planet_gear",
    "ring_gear",
    "sun_gear",
]
