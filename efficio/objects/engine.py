"""Transverse inline piston engine parts (kinematic model engine).

The crankshaft is *built up* the way model engines are made: flat webs (CNC
plate or printed) are pressed onto ground-rod journals and crankpins, so the
connecting rods can be one-piece and every rotating part stays 2.5D.  The block
is split on the crank centreline so the crank, bearings and rods drop in.

Rotating parts use local +Z as their axis.  The block, head and pistons are
modelled in world orientation: crank axis along +Y through the local origin,
cylinders pointing +Z.
"""

import math
from typing import Optional

import cadquery as cq

from efficio.measures import Measure
from efficio.objects.base import EfficioObject
from efficio.objects.drivetrain import (
    bore_cutter,
    cylinder,
    hull_of_circles,
    prism,
    wrap,
)
from efficio.objects.drivetrain_layout import DrivetrainLayout
from efficio.objects.fits import (
    M3_CLEARANCE_RADIUS_MM,
    M3_TAP_RADIUS_MM,
    PRESS_CLEARANCE_MM,
    RUNNING_CLEARANCE_MM,
    SLIDING_CLEARANCE_MM,
)
from efficio.objects.shapes import Shape

PISTON_RUNNING_CLEARANCE_MM = 0.15
PISTON_WALL_MM = 2.0
PISTON_CROWN_MM = 4.0
SPLIT_BOLT_X_MM = 17.0


def _box(
    x0: float, x1: float, y0: float, y1: float, z0: float, z1: float
) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
        .translate((x0, y0, z0))
    )


def _y_cylinder(
    radius: float, y0: float, y1: float, x: float = 0.0, z: float = 0.0
) -> cq.Workplane:
    """Cylinder whose axis is parallel to Y."""
    # Rotating -90 degrees about X maps local +Z onto world +Y.
    return (
        cq.Workplane("XY")
        .circle(radius)
        .extrude(y1 - y0)
        .rotate((0, 0, 0), (1, 0, 0), -90)
        .translate((x, y0, z))
    )


class CrankWeb(EfficioObject):
    """Crank throw plate: journal at origin, crankpin on local +X."""

    def __init__(self, layout: DrivetrainLayout):
        self.layout = layout

    def shape(self) -> Optional[Shape]:
        layout = self.layout
        t = layout.web_thickness
        throw = layout.crank_throw
        profile = hull_of_circles(
            [
                ((0.0, 0.0), layout.web_main_radius),
                ((throw, 0.0), layout.web_pin_radius),
            ]
        )
        web = prism(profile, 0.0, t)
        web = web.cut(
            cylinder(layout.crank_journal_diameter / 2 + PRESS_CLEARANCE_MM, -1, t + 1)
        )
        web = web.cut(
            cylinder(
                layout.crankpin_diameter / 2 + PRESS_CLEARANCE_MM, -1, t + 1, throw
            )
        )
        return wrap(web)


class ConnectingRod(EfficioObject):
    """One-piece rod: big end at origin, small end on local +Y; centred in Z."""

    def __init__(self, layout: DrivetrainLayout):
        self.layout = layout

    def shape(self) -> Optional[Shape]:
        layout = self.layout
        t = layout.rod_thickness
        length = layout.rod_length
        small_end_radius = layout.wrist_pin_diameter / 2 + 2.0
        profile = hull_of_circles(
            [((0.0, 0.0), layout.rod_big_end_radius), ((0.0, length), small_end_radius)]
        )
        rod = prism(profile, -t / 2, t / 2)
        rod = rod.cut(
            cylinder(layout.crankpin_diameter / 2 + RUNNING_CLEARANCE_MM, -t, t)
        )
        rod = rod.cut(
            cylinder(
                layout.wrist_pin_diameter / 2 + SLIDING_CLEARANCE_MM, -t, t, 0.0, length
            )
        )
        return wrap(rod)


class Piston(EfficioObject):
    """Hollow trunk piston; local origin is the wrist pin centre, crown on +Z."""

    def __init__(self, layout: DrivetrainLayout):
        self.layout = layout

    def shape(self) -> Optional[Shape]:
        layout = self.layout
        radius = layout.bore / 2 - PISTON_RUNNING_CLEARANCE_MM
        top = layout.piston_compression_height
        bottom = top - layout.piston_height
        inner = radius - PISTON_WALL_MM
        boss_gap = layout.rod_thickness / 2 + 0.5

        piston = cylinder(radius, bottom, top)
        piston = piston.cut(cylinder(inner, bottom - 1, top - PISTON_CROWN_MM))
        for sign in (-1.0, 1.0):
            y0, y1 = sorted((sign * boss_gap, sign * (inner + 0.5)))
            boss = _box(-4.0, 4.0, y0, y1, -4.0, 4.0).intersect(
                cylinder(radius - 0.01, bottom, top)
            )
            piston = piston.union(boss)
        # Compression ring groove.
        piston = piston.cut(
            cylinder(radius + 1, top - 3.0, top - 2.0).cut(
                cylinder(radius - 0.7, top - 3.5, top - 1.5)
            )
        )
        pin_radius = layout.wrist_pin_diameter / 2 + PRESS_CLEARANCE_MM
        piston = piston.cut(_y_cylinder(pin_radius, -radius - 1, radius + 1))
        return wrap(piston)


class EngineBlockHalf(EfficioObject):
    """Upper (cylinders) or lower (sump) half of the split crankcase.

    Local frame: crank axis on +Y from y = 0 (gearbox flange face) to the
    block length, split plane at z = 0.
    """

    def __init__(self, layout: DrivetrainLayout, upper: bool):
        self.layout = layout
        self.upper = upper

    def full_block(self) -> cq.Workplane:
        layout = self.layout
        hw = layout.block_half_width
        length = layout.engine_block.length
        wall = layout.engine_end_wall
        deck = layout.deck_height
        y0 = layout.engine_block.start
        seat = layout.crank_bearing

        block = _box(-hw, hw, 0.0, length, -hw, deck)
        block = block.cut(_y_cylinder(layout.crank_tunnel_radius, wall, length - wall))
        block = block.cut(_y_cylinder(seat.seat_radius, wall - seat.width, wall + 0.1))
        block = block.cut(
            _y_cylinder(
                seat.seat_radius, length - wall - 0.1, length - wall + seat.width
            )
        )
        block = block.cut(
            _y_cylinder(layout.crank_journal_diameter / 2 + 0.5, -1.0, length + 1.0)
        )
        for i in range(layout.cylinders):
            y = layout.cylinder_y(i) - y0
            block = block.cut(cylinder(layout.bore / 2, 10.0, deck + 1.0, 0.0, y))
            # Crankcase relief: the rod shank swings wider than the bore just
            # above the crank tunnel.
            relief = layout.crankcase_relief_half_width
            block = block.cut(
                _box(
                    -relief,
                    relief,
                    y - layout.bore / 2,
                    y + layout.bore / 2,
                    0.0,
                    layout.crankcase_relief_height,
                )
            )
        for dx, y in layout.head_bolt_positions():
            block = block.cut(
                cylinder(M3_TAP_RADIUS_MM, deck - 15.0, deck + 1.0, dx, y - y0)
            )
        for y in (wall / 2, length - wall / 2):
            for x in (-SPLIT_BOLT_X_MM, SPLIT_BOLT_X_MM):
                block = block.cut(cylinder(M3_TAP_RADIUS_MM, -0.1, 15.0, x, y))
                block = block.cut(cylinder(M3_CLEARANCE_RADIUS_MM, -hw - 1, 0.0, x, y))
                block = block.cut(cylinder(3.0, -hw - 1, -hw + 3.0, x, y))
        cx, cz = layout.crank_centre
        for bx, bz in layout.engine_flange_bolts():
            block = block.cut(
                _y_cylinder(M3_TAP_RADIUS_MM, -1.0, 10.0, bx - cx, bz - cz)
            )
        return block

    def shape(self) -> Optional[Shape]:
        layout = self.layout
        hw = layout.block_half_width
        length = layout.engine_block.length
        if self.upper:
            keep = _box(-hw - 1, hw + 1, -1, length + 1, 0.0, layout.deck_height + 1)
        else:
            keep = _box(-hw - 1, hw + 1, -1, length + 1, -hw - 1, 0.0)
        return wrap(self.full_block().intersect(keep))


class CylinderHead(EfficioObject):
    """Flat head plate with combustion recesses; local z = 0 sits on the deck."""

    def __init__(self, layout: DrivetrainLayout):
        self.layout = layout

    def shape(self) -> Optional[Shape]:
        layout = self.layout
        hw = layout.block_half_width
        length = layout.engine_block.length
        t = layout.head_thickness
        y0 = layout.engine_block.start
        head = _box(-hw, hw, 0.0, length, 0.0, t)
        for i in range(layout.cylinders):
            y = layout.cylinder_y(i) - y0
            head = head.cut(cylinder(layout.bore / 2, -1.0, 1.5, 0.0, y))
        for dx, y in layout.head_bolt_positions():
            head = head.cut(cylinder(M3_CLEARANCE_RADIUS_MM, -1.0, t + 1.0, dx, y - y0))
        return wrap(head)


class Flywheel(EfficioObject):
    """Spoked flywheel disc on a D-flat crank stub."""

    def __init__(
        self, diameter: Measure, thickness: Measure, bore: Measure, holes: int
    ):
        self.diameter = diameter
        self.thickness = thickness
        self.bore = bore
        self.holes = holes

    def shape(self) -> Optional[Shape]:
        radius = self.diameter.value() / 2
        t = self.thickness.value()
        bore = self.bore.value()
        wheel = cylinder(radius, 0.0, t)
        hole_ring = (radius + bore / 2 + 2.0) / 2
        hole_radius = (radius - bore / 2 - 6.0) / 2 * 0.8
        for i in range(self.holes):
            angle = 2 * math.pi * (i + 0.5) / self.holes
            wheel = wheel.cut(
                cylinder(
                    hole_radius,
                    -1.0,
                    t + 1.0,
                    hole_ring * math.cos(angle),
                    hole_ring * math.sin(angle),
                )
            )
        wheel = wheel.cut(bore_cutter(bore, True, -1.0, t + 1.0, SLIDING_CLEARANCE_MM))
        return wrap(wheel)
