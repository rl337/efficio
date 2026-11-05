"""Shafts, pins, journals and tubular spacers."""

from typing import Optional

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.powertrain.fits import M3_CLEARANCE_RADIUS_MM, PRESS_CLEARANCE_MM
from efficio.objects.powertrain.profiles import cylinder, d_profile, prism, wrap
from efficio.objects.shapes import Shape


class Shaft(EfficioObject):
    """Round or D-flat shaft cut from ground rod stock, along local +Z.

    Used for axles, the idler shaft, crank journals, crankpins and wrist pins.
    The model is a hair under nominal so it never shares faces with bores.
    """

    def __init__(self, diameter: Measure, length: Measure, d_flat: bool):
        self.diameter = diameter
        self.length = length
        self.d_flat = d_flat

    def shape(self) -> Optional[Shape]:
        d = self.diameter.value()
        length = self.length.value()
        if self.d_flat:
            return wrap(prism(d_profile(d, -PRESS_CLEARANCE_MM), 0.0, length))
        return wrap(cylinder(d / 2.0 - PRESS_CLEARANCE_MM, 0.0, length))


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
