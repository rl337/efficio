"""Flywheel disc."""

import math
from typing import Optional

from efficio.measures import Measure
from efficio.objects.base import EfficioObject
from efficio.objects.powertrain.fits import SLIDING_CLEARANCE_MM
from efficio.objects.powertrain.profiles import bore_cutter, cylinder, wrap
from efficio.objects.shapes import Shape


class Flywheel(EfficioObject):
    """Spoked flywheel disc on a D-flat crank stub."""

    def __init__(
        self, diameter: Measure, thickness: Measure, bore: Measure, holes: int
    ):
        self.diameter = diameter
        self.thickness = thickness
        self.bore = bore
        self.holes = holes

    def shape(self) -> Optional[Shape]:
        radius = self.diameter.value() / 2
        t = self.thickness.value()
        bore = self.bore.value()
        wheel = cylinder(radius, 0.0, t)
        hole_ring = (radius + bore / 2 + 2.0) / 2
        hole_radius = (radius - bore / 2 - 6.0) / 2 * 0.8
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
