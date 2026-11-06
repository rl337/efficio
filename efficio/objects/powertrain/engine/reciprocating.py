"""Pistons and connecting rods."""

from typing import Optional

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.powertrain.engine.geometry import EngineGeometry
from efficio.objects.powertrain.fits import (
    PRESS_CLEARANCE_MM,
    RUNNING_CLEARANCE_MM,
    SLIDING_CLEARANCE_MM,
)
from efficio.objects.powertrain.planar import hull_of_circles
from efficio.objects.powertrain.profiles import box, cylinder, prism, wrap, y_cylinder
from efficio.objects.shapes import Shape

PISTON_WALL_MM = 2.0
PISTON_CROWN_MM = 4.0
PISTON_BOSS_HALF_SIZE_MM = 4.0


class ConnectingRod(EfficioObject):
    """One-piece rod: big end on the origin, small end on local +Y, centred in Z."""

    def __init__(
        self,
        centre_distance: Measure,
        crankpin_diameter: Measure,
        wrist_pin_diameter: Measure,
        thickness: Measure,
        big_end_radius: Measure,
        small_end_radius: Measure,
    ):
        self.centre_distance = centre_distance
        self.crankpin_diameter = crankpin_diameter
        self.wrist_pin_diameter = wrist_pin_diameter
        self.thickness = thickness
        self.big_end_radius = big_end_radius
        self.small_end_radius = small_end_radius

    @classmethod
    def from_engine(cls, engine: EngineGeometry) -> "ConnectingRod":
        return cls(
            Millimeter(engine.rod_length),
            Millimeter(engine.crankpin_diameter),
            Millimeter(engine.wrist_pin_diameter),
            Millimeter(engine.rod_thickness),
            Millimeter(engine.rod_big_end_radius),
            Millimeter(engine.rod_small_end_radius),
        )

    def shape(self) -> Optional[Shape]:
        t = self.thickness.value()
        length = self.centre_distance.value()
        profile = hull_of_circles(
            [
                ((0.0, 0.0), self.big_end_radius.value()),
                ((0.0, length), self.small_end_radius.value()),
            ]
        )
        rod = prism(profile, -t / 2, t / 2)
        big = self.crankpin_diameter.value() / 2 + RUNNING_CLEARANCE_MM
        small = self.wrist_pin_diameter.value() / 2 + SLIDING_CLEARANCE_MM
        rod = rod.cut(cylinder(big, -t, t))
        rod = rod.cut(cylinder(small, -t, t, 0.0, length))
        return wrap(rod)


class Piston(EfficioObject):
    """Hollow trunk piston; local origin at the wrist pin, crown toward +Z.

    The wrist pin runs along local Y between two internal bosses separated by
    ``boss_gap`` either side of the rod.
    """

    def __init__(
        self,
        bore: Measure,
        height: Measure,
        compression_height: Measure,
        wrist_pin_diameter: Measure,
        boss_gap: Measure,
        clearance: Measure = Millimeter(0.15),
    ):
        self.bore = bore
        self.height = height
        self.compression_height = compression_height
        self.wrist_pin_diameter = wrist_pin_diameter
        self.boss_gap = boss_gap
        self.clearance = clearance

    @classmethod
    def from_engine(cls, engine: EngineGeometry) -> "Piston":
        return cls(
            Millimeter(engine.bore),
            Millimeter(engine.piston_height),
            Millimeter(engine.piston_compression_height),
            Millimeter(engine.wrist_pin_diameter),
            Millimeter(engine.piston_boss_gap),
            Millimeter(engine.piston_clearance),
        )

    def shape(self) -> Optional[Shape]:
        radius = self.bore.value() / 2 - self.clearance.value()
        top = self.compression_height.value()
        bottom = top - self.height.value()
        inner = radius - PISTON_WALL_MM
        gap = self.boss_gap.value()
        boss = PISTON_BOSS_HALF_SIZE_MM

        piston = cylinder(radius, bottom, top)
        piston = piston.cut(cylinder(inner, bottom - 1, top - PISTON_CROWN_MM))
        for sign in (-1.0, 1.0):
            y0, y1 = sorted((sign * gap, sign * (inner + 0.5)))
            piston = piston.union(
                box(-boss, boss, y0, y1, -boss, boss).intersect(
                    cylinder(radius - 0.01, bottom, top)
                )
            )
        # Compression ring groove.
        piston = piston.cut(
            cylinder(radius + 1, top - 3.0, top - 2.0).cut(
                cylinder(radius - 0.7, top - 3.5, top - 1.5)
            )
        )
        pin = self.wrist_pin_diameter.value() / 2 + PRESS_CLEARANCE_MM
        piston = piston.cut(y_cylinder(pin, -radius - 1, radius + 1))
        return wrap(piston)
