"""Hex drive that keys a D-flat axle to a wheel."""

from typing import Optional

import cadquery as cq

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.powertrain.fits import (
    PINNED_BORE_CLEARANCE_MM,
    SLIDING_CLEARANCE_MM,
)
from efficio.objects.powertrain.profiles import (
    bore_cutter,
    cross_pin_slot_cutter,
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
    """Hex prism keyed to the axle; corners face local +X.

    Steel axles drive through a D-flat bore.  Round axles such as hardwood
    dowels set ``cross_pin_diameter``: a slot on the outboard face
    (``z = length``) seats a pin through the axle, captured by the wheel hub.
    """

    def __init__(
        self,
        across_flats: Measure,
        length: Measure,
        bore: Measure,
        cross_pin_diameter: Measure = Millimeter(0),
        cross_pin_length: Measure = Millimeter(0),
    ):
        self.across_flats = across_flats
        self.length = length
        self.bore = bore
        self.cross_pin_diameter = cross_pin_diameter
        self.cross_pin_length = cross_pin_length

    @property
    def pinned(self) -> bool:
        return self.cross_pin_diameter.value() > 0

    def shape(self) -> Optional[Shape]:
        length = self.length.value()
        body = hexagon(hex_across_corners(self.across_flats.value()), 0.0, length)
        if self.pinned:
            body = body.cut(
                bore_cutter(
                    self.bore.value(),
                    False,
                    -1.0,
                    length + 1.0,
                    PINNED_BORE_CLEARANCE_MM,
                )
            )
            body = body.cut(
                cross_pin_slot_cutter(
                    self.cross_pin_diameter.value(),
                    self.cross_pin_length.value(),
                    length,
                    False,
                )
            )
        else:
            body = body.cut(
                bore_cutter(
                    self.bore.value(), True, -1.0, length + 1.0, SLIDING_CLEARANCE_MM
                )
            )
        return wrap(body)
