"""Treaded tyre that slips between the rim bead lips (print in TPU)."""

import math
from typing import Optional

from efficio.measures import Measure
from efficio.objects.base import EfficioObject
from efficio.objects.powertrain.profiles import cylinder, prism, wrap
from efficio.objects.shapes import Shape


class Tire(EfficioObject):
    """TPU tyre with transverse tread grooves; slips between the rim lips."""

    def __init__(
        self,
        outer_diameter: Measure,
        inner_diameter: Measure,
        width: Measure,
        tread_blocks: int,
    ):
        self.outer_diameter = outer_diameter
        self.inner_diameter = inner_diameter
        self.width = width
        self.tread_blocks = tread_blocks

    def shape(self) -> Optional[Shape]:
        outer = self.outer_diameter.value() / 2
        inner = self.inner_diameter.value() / 2
        width = self.width.value()
        tire = cylinder(outer, 0.0, width).cut(cylinder(inner, -1.0, width + 1.0))
        groove_depth = min(2.5, (outer - inner) / 4)
        groove_width = 2.0 * math.pi * outer / self.tread_blocks / 3
        for i in range(self.tread_blocks):
            angle = 360.0 * i / self.tread_blocks
            groove = prism(
                [
                    (outer - groove_depth, -groove_width / 2),
                    (outer + 1.0, -groove_width / 2),
                    (outer + 1.0, groove_width / 2),
                    (outer - groove_depth, groove_width / 2),
                ],
                -1.0,
                width + 1.0,
            ).rotate((0, 0, 0), (0, 0, 1), angle)
            tire = tire.cut(groove)
        return wrap(tire)
