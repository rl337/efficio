"""Flanged bearing housing for an axle."""

from typing import Optional

import cadquery as cq

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.fasteners.threads import MetricThread
from efficio.objects.powertrain.bearings import StandardBearing
from efficio.objects.profiles import bearing_seat_cutter, cylinder, prism, wrap
from efficio.objects.shapes import Shape


class PillowBlock(EfficioObject):
    """Bearing on the local Z axis; mounting face at local y = -centre_height
    (world -Z when the block is placed with its axis on world Y).

    ``boss_wall`` is the wall around the bearing, ``flange_overhang`` how far
    the mounting flange extends past the boss on each side (the bolt sits in
    its middle).
    """

    def __init__(
        self,
        shaft_diameter: Measure,
        bearing: StandardBearing,
        centre_height: Measure,
        thickness: Measure,
        boss_wall: Measure = Millimeter(3.0),
        flange_height: Measure = Millimeter(4.0),
        flange_overhang: Measure = Millimeter(9.0),
        shaft_clearance: Measure = Millimeter(0.5),
        fastener: MetricThread = MetricThread.M3,
    ):
        self.shaft_diameter = shaft_diameter
        self.bearing = bearing
        self.centre_height = centre_height
        self.thickness = thickness
        self.boss_wall = boss_wall
        self.flange_height = flange_height
        self.flange_overhang = flange_overhang
        self.shaft_clearance = shaft_clearance
        self.fastener = fastener

    def boss_radius(self) -> float:
        return self.bearing.spec.seat_radius + self.boss_wall.value()

    def mounting_hole_offset(self) -> float:
        return self.boss_radius() + self.flange_overhang.value() / 2

    def shape(self) -> Optional[Shape]:
        t = self.thickness.value()
        h = self.centre_height.value()
        boss = self.boss_radius()
        flange = boss + self.flange_overhang.value()
        flange_height = self.flange_height.value()

        body = cylinder(boss, 0.0, t)
        body = body.union(
            prism([(-boss, -h), (boss, -h), (boss, 0.0), (-boss, 0.0)], 0.0, t)
        )
        body = body.union(
            prism(
                [
                    (-flange, -h),
                    (flange, -h),
                    (flange, -h + flange_height),
                    (-flange, -h + flange_height),
                ],
                0.0,
                t,
            )
        )
        through = self.shaft_diameter.value() / 2 + self.shaft_clearance.value()
        body = body.cut(bearing_seat_cutter(self.bearing.spec, t, through))
        hole_radius = self.fastener.spec.clearance_radius
        for x in (-self.mounting_hole_offset(), self.mounting_hole_offset()):
            hole: cq.Workplane = (
                cylinder(hole_radius, 0.0, flange_height + 2.0)
                .rotate((0, 0, 0), (1, 0, 0), -90)
                .translate((x, -h - 1.0, t / 2))
            )
            body = body.cut(hole)
        return wrap(body)
