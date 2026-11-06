"""Flywheel disc."""

import math
from typing import Optional

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.fits import SLIDING_CLEARANCE_MM
from efficio.objects.profiles import bore_cutter, cylinder, wrap
from efficio.objects.shapes import Shape


class Flywheel(EfficioObject):
    """Flywheel disc on a D-flat crank stub, lightened by ``holes``.

    The lightening holes sit midway between a ``hub_wall`` around the bore
    and a ``rim_wall`` at the edge, filling ``hole_fill`` of that band.
    """

    def __init__(
        self,
        diameter: Measure,
        thickness: Measure,
        bore: Measure,
        holes: int,
        hub_wall: Measure = Millimeter(2.0),
        rim_wall: Measure = Millimeter(6.0),
        hole_fill: float = 0.8,
    ):
        self.diameter = diameter
        self.thickness = thickness
        self.bore = bore
        self.holes = holes
        self.hub_wall = hub_wall
        self.rim_wall = rim_wall
        self.hole_fill = hole_fill

    def shape(self) -> Optional[Shape]:
        radius = self.diameter.value() / 2
        t = self.thickness.value()
        bore = self.bore.value()
        wheel = cylinder(radius, 0.0, t)
        hole_ring = (radius + bore / 2 + self.hub_wall.value()) / 2
        band = radius - bore / 2 - self.rim_wall.value()
        hole_radius = band / 2 * self.hole_fill
        for i in range(self.holes):
            angle = 2 * math.pi * (i + 0.5) / self.holes
            wheel = wheel.cut(
                cylinder(
                    hole_radius,
                    -1.0,
                    t + 1.0,
                    hole_ring * math.cos(angle),
                    hole_ring * math.sin(angle),
                )
            )
        wheel = wheel.cut(bore_cutter(bore, True, -1.0, t + 1.0, SLIDING_CLEARANCE_MM))
        return wrap(wheel)
