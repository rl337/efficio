"""Hex drive that keys a D-flat axle to a wheel."""

from typing import Optional

import cadquery as cq

from efficio.measures import Measure
from efficio.objects.base import EfficioObject
from efficio.objects.powertrain.fits import SLIDING_CLEARANCE_MM
from efficio.objects.powertrain.profiles import (
    bore_cutter,
    hex_across_corners,
    hexagon,
    wrap,
)
from efficio.objects.shapes import Shape

HEX_SOCKET_CLEARANCE_MM = 0.1


def hex_socket_cutter(across_flats: float, depth: float) -> cq.Workplane:
    """Socket that receives a :class:`HexWheelAdapter`, open at z = 0."""
    corners = hex_across_corners(across_flats + 2 * HEX_SOCKET_CLEARANCE_MM)
    return hexagon(corners, -1.0, depth)


class HexWheelAdapter(EfficioObject):
    """Hex prism with a D-flat bore; corners and flat both face local +X."""

    def __init__(self, across_flats: Measure, length: Measure, bore: Measure):
        self.across_flats = across_flats
        self.length = length
        self.bore = bore

    def shape(self) -> Optional[Shape]:
        length = self.length.value()
        body = hexagon(hex_across_corners(self.across_flats.value()), 0.0, length)
        body = body.cut(
            bore_cutter(
                self.bore.value(), True, -1.0, length + 1.0, SLIDING_CLEARANCE_MM
            )
        )
        return wrap(body)
