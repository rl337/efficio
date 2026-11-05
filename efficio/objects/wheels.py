"""Wheels, tyres, hex drive adapters and axle pillow blocks."""

import math
from typing import Optional

from efficio.measures import Measure
from efficio.objects.base import EfficioObject
from efficio.objects.drivetrain import bore_cutter, cylinder, hexagon, prism, wrap
from efficio.objects.fits import M3_CLEARANCE_RADIUS_MM, SLIDING_CLEARANCE_MM
from efficio.objects.shapes import Shape

RIM_WALL_MM = 2.5
RIM_LIP_HEIGHT_MM = 2.0
RIM_LIP_WIDTH_MM = 2.0
HEX_SOCKET_CLEARANCE_MM = 0.1


def hex_across_corners(across_flats: float) -> float:
    return across_flats / math.cos(math.radians(30))


class HexWheelAdapter(EfficioObject):
    """Hex drive that keys a D-flat axle to the wheel's hex socket."""

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


class Rim(EfficioObject):
    """Spoked rim with tyre bead lips and a hex socket on the inner face.

    Local z = 0 is the inboard face.  An M3 screw through the hub into the
    tapped axle end retains the wheel.
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

    def shape(self) -> Optional[Shape]:
        radius = self.diameter.value() / 2
        width = self.width.value()
        hex_depth = self.hex_depth.value()
        hub_radius = self.hub_radius()
        hub_length = hex_depth + 6.0
        inner = radius - RIM_WALL_MM

        rim = cylinder(radius, 0.0, width).cut(cylinder(inner, -1.0, width + 1.0))
        for z0 in (0.0, width - RIM_LIP_WIDTH_MM):
            rim = rim.union(
                cylinder(radius + RIM_LIP_HEIGHT_MM, z0, z0 + RIM_LIP_WIDTH_MM).cut(
                    cylinder(inner + 0.5, z0 - 1.0, z0 + RIM_LIP_WIDTH_MM + 1.0)
                )
            )
        rim = rim.union(cylinder(hub_radius, 0.0, hub_length))

        spoke_width = 6.0
        spoke_z0 = hub_length - 6.0
        span = inner + 0.5
        for i in range(self.spokes):
            angle = 360.0 * i / self.spokes
            spoke = prism(
                [
                    (0.0, -spoke_width / 2),
                    (span, -spoke_width / 2),
                    (span, spoke_width / 2),
                    (0.0, spoke_width / 2),
                ],
                spoke_z0,
                hub_length,
            ).rotate((0, 0, 0), (0, 0, 1), angle)
            rim = rim.union(spoke)

        socket = hex_across_corners(
            self.hex_across_flats.value() + 2 * HEX_SOCKET_CLEARANCE_MM
        )
        rim = rim.cut(hexagon(socket, -1.0, hex_depth))
        rim = rim.cut(cylinder(M3_CLEARANCE_RADIUS_MM, -1.0, hub_length + 1.0))
        return wrap(rim)


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


class PillowBlock(EfficioObject):
    """Flanged bearing block for an axle; local origin on the bearing axis.

    The mounting face is at local y = -centre_height (maps to world -Z when
    the block is placed with its axis on world Y).
    """

    def __init__(
        self,
        shaft_diameter: Measure,
        bearing_outer_diameter: Measure,
        bearing_width: Measure,
        centre_height: Measure,
        thickness: Measure,
    ):
        self.shaft_diameter = shaft_diameter
        self.bearing_outer_diameter = bearing_outer_diameter
        self.bearing_width = bearing_width
        self.centre_height = centre_height
        self.thickness = thickness

    def shape(self) -> Optional[Shape]:
        t = self.thickness.value()
        h = self.centre_height.value()
        seat = self.bearing_outer_diameter.value() / 2 + 0.05
        boss = seat + 3.0
        flange_half = boss + 9.0
        flange_height = 4.0

        body = cylinder(boss, 0.0, t)
        body = body.union(
            prism([(-boss, -h), (boss, -h), (boss, 0.0), (-boss, 0.0)], 0.0, t)
        )
        body = body.union(
            prism(
                [
                    (-flange_half, -h),
                    (flange_half, -h),
                    (flange_half, -h + flange_height),
                    (-flange_half, -h + flange_height),
                ],
                0.0,
                t,
            )
        )
        body = body.cut(cylinder(seat, -1.0, self.bearing_width.value()))
        body = body.cut(cylinder(self.shaft_diameter.value() / 2 + 0.5, -1.0, t + 1.0))
        for x in (-(boss + 4.5), boss + 4.5):
            hole = (
                cylinder(M3_CLEARANCE_RADIUS_MM, 0.0, flange_height + 2.0)
                .rotate((0, 0, 0), (1, 0, 0), -90)
                .translate((x, -h - 1.0, t / 2))
            )
            body = body.cut(hole)
        return wrap(body)
