"""Spoked wheel rim with a hex drive socket."""

from typing import Optional

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.fasteners.threads import MetricThread
from efficio.objects.powertrain.axles.hub import hex_socket_cutter
from efficio.objects.profiles import cylinder, hex_across_corners, prism, wrap
from efficio.objects.shapes import Shape


class Rim(EfficioObject):
    """Local z = 0 is the inboard face, where the hex socket opens.

    Behind the socket the hub has an ``axle_bore``: a screw clearance hole
    when a tapped steel axle stops at the socket (default), or a through hole
    when the axle (e.g. a dowel) runs to the outer face and takes a wood
    screw in its end.  The tyre seats between the bead lips.
    """

    def __init__(
        self,
        diameter: Measure,
        width: Measure,
        hex_across_flats: Measure,
        hex_depth: Measure,
        spokes: int,
        spoke_thickness: Measure = Millimeter(6.0),
        axle_bore: Measure = Millimeter(MetricThread.M3.spec.clearance_hole),
        rim_wall: Measure = Millimeter(2.5),
        lip_height: Measure = Millimeter(2.0),
        lip_width: Measure = Millimeter(2.0),
        spoke_width: Measure = Millimeter(6.0),
        hub_wall: Measure = Millimeter(3.0),
    ):
        self.diameter = diameter
        self.width = width
        self.hex_across_flats = hex_across_flats
        self.hex_depth = hex_depth
        self.spokes = spokes
        self.spoke_thickness = spoke_thickness
        self.axle_bore = axle_bore
        self.rim_wall = rim_wall
        self.lip_height = lip_height
        self.lip_width = lip_width
        self.spoke_width = spoke_width
        self.hub_wall = hub_wall

    def hub_length(self) -> float:
        return self.hex_depth.value() + self.spoke_thickness.value()

    def hub_radius(self) -> float:
        return (
            hex_across_corners(self.hex_across_flats.value()) / 2
            + self.hub_wall.value()
        )

    def tire_width(self) -> float:
        return self.width.value() - 2 * self.lip_width.value()

    def shape(self) -> Optional[Shape]:
        radius = self.diameter.value() / 2
        width = self.width.value()
        hex_depth = self.hex_depth.value()
        hub_length = self.hub_length()
        spoke_thickness = self.spoke_thickness.value()
        inner = radius - self.rim_wall.value()
        lip_width = self.lip_width.value()

        rim = cylinder(radius, 0.0, width).cut(cylinder(inner, -1.0, width + 1.0))
        for z0 in (0.0, width - lip_width):
            rim = rim.union(
                cylinder(radius + self.lip_height.value(), z0, z0 + lip_width).cut(
                    cylinder(inner + 0.5, z0 - 1.0, z0 + lip_width + 1.0)
                )
            )
        rim = rim.union(cylinder(self.hub_radius(), 0.0, hub_length))

        half = self.spoke_width.value() / 2
        span = inner + 0.5
        for i in range(self.spokes):
            spoke = prism(
                [(0.0, -half), (span, -half), (span, half), (0.0, half)],
                hub_length - spoke_thickness,
                hub_length,
            ).rotate((0, 0, 0), (0, 0, 1), 360.0 * i / self.spokes)
            rim = rim.union(spoke)

        rim = rim.cut(hex_socket_cutter(self.hex_across_flats.value(), hex_depth))
        rim = rim.cut(cylinder(self.axle_bore.value() / 2, -1.0, hub_length + 1.0))
        return wrap(rim)
