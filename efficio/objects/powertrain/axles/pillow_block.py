"""Flanged bearing housing for an axle."""

from typing import Optional

import cadquery as cq

from efficio.measures import Measure
from efficio.objects.base import EfficioObject
from efficio.objects.powertrain.bearings import StandardBearing
from efficio.objects.powertrain.fits import M3_CLEARANCE_RADIUS_MM
from efficio.objects.powertrain.profiles import (
    bearing_seat_cutter,
    cylinder,
    prism,
    wrap,
)
from efficio.objects.shapes import Shape

FLANGE_HEIGHT_MM = 4.0
BOSS_WALL_MM = 3.0
FLANGE_OVERHANG_MM = 9.0


class PillowBlock(EfficioObject):
    """Bearing on the local Z axis; mounting face at local y = -centre_height
    (world -Z when the block is placed with its axis on world Y)."""

    def __init__(
        self,
        shaft_diameter: Measure,
        bearing: StandardBearing,
        centre_height: Measure,
        thickness: Measure,
    ):
        self.shaft_diameter = shaft_diameter
        self.bearing = bearing
        self.centre_height = centre_height
        self.thickness = thickness

    def mounting_hole_offset(self) -> float:
        return self.bearing.spec.seat_radius + BOSS_WALL_MM + FLANGE_OVERHANG_MM / 2

    def shape(self) -> Optional[Shape]:
        t = self.thickness.value()
        h = self.centre_height.value()
        bearing = self.bearing.spec
        boss = bearing.seat_radius + BOSS_WALL_MM
        flange = boss + FLANGE_OVERHANG_MM

        body = cylinder(boss, 0.0, t)
        body = body.union(
            prism([(-boss, -h), (boss, -h), (boss, 0.0), (-boss, 0.0)], 0.0, t)
        )
        body = body.union(
            prism(
                [
                    (-flange, -h),
                    (flange, -h),
                    (flange, -h + FLANGE_HEIGHT_MM),
                    (-flange, -h + FLANGE_HEIGHT_MM),
                ],
                0.0,
                t,
            )
        )
        body = body.cut(
            bearing_seat_cutter(bearing, t, self.shaft_diameter.value() / 2 + 0.5)
        )
        for x in (-self.mounting_hole_offset(), self.mounting_hole_offset()):
            hole: cq.Workplane = (
                cylinder(M3_CLEARANCE_RADIUS_MM, 0.0, FLANGE_HEIGHT_MM + 2.0)
                .rotate((0, 0, 0), (1, 0, 0), -90)
                .translate((x, -h - 1.0, t / 2))
            )
            body = body.cut(hole)
        return wrap(body)
