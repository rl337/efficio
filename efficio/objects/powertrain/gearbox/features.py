"""Plate features expressed in plate coordinates (pure Python)."""

from dataclasses import dataclass

from efficio.objects.powertrain.bearings import BallBearing
from efficio.objects.powertrain.planar import Point


@dataclass(frozen=True)
class PlateSeat:
    """Bearing pocketed from the inner face, with a shaft hole through."""

    centre: Point
    bearing: BallBearing
    through_radius: float
    boss_margin: float = 4.0

    @property
    def outline_radius(self) -> float:
        return self.bearing.seat_radius + self.boss_margin


@dataclass(frozen=True)
class PlateHole:
    """Plain through hole (fastener, shaft clearance) with a boss of material."""

    centre: Point
    radius: float
    boss_margin: float = 4.5

    @property
    def outline_radius(self) -> float:
        return self.radius + self.boss_margin
