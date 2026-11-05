"""Shafts, pins, journals and tubular spacers."""

from typing import Optional, Sequence

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.powertrain.fits import M3_CLEARANCE_RADIUS_MM, PRESS_CLEARANCE_MM
from efficio.objects.powertrain.profiles import (
    cylinder,
    d_profile,
    prism,
    wrap,
    y_cylinder,
)
from efficio.objects.shapes import Shape


class Shaft(EfficioObject):
    """Round or D-flat shaft along local +Z: steel rod or hardwood dowel.

    Used for axles, the idler shaft, crank journals, crankpins, wrist pins
    and cross pins.  ``cross_holes`` are axial positions of holes drilled
    through along local X (for cross pins that drive dowel axles).  The model
    is a hair under nominal so it never shares faces with bores.
    """

    def __init__(
        self,
        diameter: Measure,
        length: Measure,
        d_flat: bool,
        cross_holes: Sequence[float] = (),
        cross_hole_diameter: Measure = Millimeter(2.0),
    ):
        self.diameter = diameter
        self.length = length
        self.d_flat = d_flat
        self.cross_holes = tuple(cross_holes)
        self.cross_hole_diameter = cross_hole_diameter

    def shape(self) -> Optional[Shape]:
        d = self.diameter.value()
        length = self.length.value()
        if self.d_flat:
            body = prism(d_profile(d, -PRESS_CLEARANCE_MM), 0.0, length)
        else:
            body = cylinder(d / 2.0 - PRESS_CLEARANCE_MM, 0.0, length)
        hole = self.cross_hole_diameter.value() / 2.0 + PRESS_CLEARANCE_MM
        for z in self.cross_holes:
            if not 0.0 < z < length:
                raise ValueError(f"cross hole at {z} mm is outside the shaft")
            # A Y-axis cylinder turned onto X: drill along local X at height z.
            drill = y_cylinder(hole, -d, d).rotate((0, 0, 0), (0, 0, 1), 90)
            body = body.cut(drill.translate((0, 0, z)))
        return wrap(body)


class Standoff(EfficioObject):
    """Tubular spacer clamped by a rod or bolt through its bore."""

    def __init__(
        self,
        length: Measure,
        outer_diameter: Measure,
        bore: Measure = Millimeter(2 * M3_CLEARANCE_RADIUS_MM),
    ):
        self.length = length
        self.outer_diameter = outer_diameter
        self.bore = bore

    def shape(self) -> Optional[Shape]:
        length = self.length.value()
        tube = cylinder(self.outer_diameter.value() / 2.0, 0.0, length).cut(
            cylinder(self.bore.value() / 2.0, -1.0, length + 1.0)
        )
        return wrap(tube)
