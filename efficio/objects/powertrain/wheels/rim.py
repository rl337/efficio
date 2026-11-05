"""Spoked wheel rim with a hex drive socket."""

from typing import Optional

from efficio.measures import Measure
from efficio.objects.base import EfficioObject
from efficio.objects.powertrain.axles.hub import hex_socket_cutter
from efficio.objects.powertrain.fits import M3_CLEARANCE_RADIUS_MM
from efficio.objects.powertrain.profiles import (
    cylinder,
    hex_across_corners,
    prism,
    wrap,
)
from efficio.objects.shapes import Shape

RIM_WALL_MM = 2.5
RIM_LIP_HEIGHT_MM = 2.0
RIM_LIP_WIDTH_MM = 2.0
SPOKE_WIDTH_MM = 6.0
SPOKE_THICKNESS_MM = 6.0


class Rim(EfficioObject):
    """Local z = 0 is the inboard face, where the hex socket opens.

    An M3 screw through the hub into the tapped axle end retains the wheel.
    Tyre seats between the bead lips (``tire_width()`` wide).
    """

    def __init__(
        self,
        diameter: Measure,
        width: Measure,
        hex_across_flats: Measure,
        hex_depth: Measure,
        spokes: int,
    ):
        self.diameter = diameter
        self.width = width
        self.hex_across_flats = hex_across_flats
        self.hex_depth = hex_depth
        self.spokes = spokes

    def hub_radius(self) -> float:
        return hex_across_corners(self.hex_across_flats.value()) / 2 + 3.0

    def tire_width(self) -> float:
        return self.width.value() - 2 * RIM_LIP_WIDTH_MM

    def shape(self) -> Optional[Shape]:
        radius = self.diameter.value() / 2
        width = self.width.value()
        hex_depth = self.hex_depth.value()
        hub_length = hex_depth + SPOKE_THICKNESS_MM
        inner = radius - RIM_WALL_MM

        rim = cylinder(radius, 0.0, width).cut(cylinder(inner, -1.0, width + 1.0))
        for z0 in (0.0, width - RIM_LIP_WIDTH_MM):
            rim = rim.union(
                cylinder(radius + RIM_LIP_HEIGHT_MM, z0, z0 + RIM_LIP_WIDTH_MM).cut(
                    cylinder(inner + 0.5, z0 - 1.0, z0 + RIM_LIP_WIDTH_MM + 1.0)
                )
            )
        rim = rim.union(cylinder(self.hub_radius(), 0.0, hub_length))

        half = SPOKE_WIDTH_MM / 2
        span = inner + 0.5
        for i in range(self.spokes):
            spoke = prism(
                [(0.0, -half), (span, -half), (span, half), (0.0, half)],
                hub_length - SPOKE_THICKNESS_MM,
                hub_length,
            ).rotate((0, 0, 0), (0, 0, 1), 360.0 * i / self.spokes)
            rim = rim.union(spoke)

        rim = rim.cut(hex_socket_cutter(self.hex_across_flats.value(), hex_depth))
        rim = rim.cut(cylinder(M3_CLEARANCE_RADIUS_MM, -1.0, hub_length + 1.0))
        return wrap(rim)
