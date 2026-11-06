"""Split crankcase / cylinder block and cylinder head.

Both are modelled in the engine-local frame of :class:`EngineGeometry`: crank
axis on +Y from the flange face (y = 0), split plane z = 0, cylinders on +Z.
"""

from typing import Optional

import cadquery as cq

from efficio.objects.base import EfficioObject
from efficio.objects.powertrain.engine.geometry import EngineGeometry
from efficio.objects.powertrain.fits import M3_CLEARANCE_RADIUS_MM, M3_TAP_RADIUS_MM
from efficio.objects.powertrain.profiles import (
    bearing_seat_cutter,
    box,
    cylinder,
    wrap,
    x_cylinder,
    y_cylinder,
)
from efficio.objects.shapes import Shape

HEAD_BOLT_DEPTH_MM = 15.0
SPLIT_BOLT_TAP_DEPTH_MM = 15.0
FLANGE_BOLT_DEPTH_MM = 10.0
COUNTERBORE_RADIUS_MM = 3.0
COUNTERBORE_DEPTH_MM = 3.0


def _y_axis(workplane: cq.Workplane, y: float, toward_positive_y: bool) -> cq.Workplane:
    """Re-orient a +Z cutter onto the crank axis, starting at ``y``."""
    angle = -90 if toward_positive_y else 90
    return workplane.rotate((0, 0, 0), (1, 0, 0), angle).translate((0, y, 0))


class EngineBlockHalf(EfficioObject):
    """Upper (cylinders) or lower (sump) half of the split crankcase."""

    def __init__(self, engine: EngineGeometry, upper: bool):
        self.engine = engine
        self.upper = upper

    def full_block(self) -> cq.Workplane:
        e = self.engine
        hw = e.block_half_width
        length = e.block_length
        wall = e.end_wall
        deck = e.deck_height
        journal_clearance = e.crank_journal_diameter / 2 + 0.5

        block = box(-hw, hw, 0.0, length, -hw, deck)
        block = block.cut(y_cylinder(e.crank_tunnel_radius, wall, length - wall))
        # Main bearings pocketed from the inside of each end wall.
        for y, outward in ((wall, False), (length - wall, True)):
            seat = bearing_seat_cutter(e.main_bearing, wall, journal_clearance)
            block = block.cut(_y_axis(seat, y, outward))

        relief = e.crankcase_relief_half_width
        for i in range(e.cylinders):
            y = e.cylinder_y(i)
            block = block.cut(cylinder(e.bore / 2, e.bore_floor, deck + 1.0, 0.0, y))
            # The rod shank swings wider than the bore just above the tunnel.
            block = block.cut(
                box(
                    -relief,
                    relief,
                    y - e.bore / 2,
                    y + e.bore / 2,
                    0.0,
                    e.crankcase_relief_height,
                )
            )
        for x, y in e.head_bolt_positions():
            block = block.cut(
                cylinder(M3_TAP_RADIUS_MM, deck - HEAD_BOLT_DEPTH_MM, deck + 1, x, y)
            )
        for x, y in e.split_bolt_positions():
            block = block.cut(
                cylinder(M3_TAP_RADIUS_MM, -0.1, SPLIT_BOLT_TAP_DEPTH_MM, x, y)
            )
            block = block.cut(cylinder(M3_CLEARANCE_RADIUS_MM, -hw - 1, 0.0, x, y))
            block = block.cut(
                cylinder(
                    COUNTERBORE_RADIUS_MM, -hw - 1, -hw + COUNTERBORE_DEPTH_MM, x, y
                )
            )
        if e.front_flange:
            for x, z in e.flange_bolt_offsets():
                block = block.cut(
                    y_cylinder(M3_TAP_RADIUS_MM, -1.0, FLANGE_BOLT_DEPTH_MM, x, z)
                )
        depth = e.side_mount_depth
        for y, z in e.side_mount_positions():
            block = block.cut(x_cylinder(M3_TAP_RADIUS_MM, -hw - 1, -hw + depth, y, z))
            block = block.cut(x_cylinder(M3_TAP_RADIUS_MM, hw - depth, hw + 1, y, z))
        return block

    def shape(self) -> Optional[Shape]:
        e = self.engine
        hw = e.block_half_width
        length = e.block_length
        if self.upper:
            keep = box(-hw - 1, hw + 1, -1, length + 1, 0.0, e.deck_height + 1)
        else:
            keep = box(-hw - 1, hw + 1, -1, length + 1, -hw - 1, 0.0)
        return wrap(self.full_block().intersect(keep))


class CylinderHead(EfficioObject):
    """Flat head plate with combustion recesses; local z = 0 sits on the deck."""

    RECESS_DEPTH_MM = 1.5

    def __init__(self, engine: EngineGeometry):
        self.engine = engine

    def shape(self) -> Optional[Shape]:
        e = self.engine
        hw = e.block_half_width
        t = e.head_thickness
        head = box(-hw, hw, 0.0, e.block_length, 0.0, t)
        for i in range(e.cylinders):
            head = head.cut(
                cylinder(e.bore / 2, -1.0, self.RECESS_DEPTH_MM, 0.0, e.cylinder_y(i))
            )
        for x, y in e.head_bolt_positions():
            head = head.cut(cylinder(M3_CLEARANCE_RADIUS_MM, -1.0, t + 1.0, x, y))
        return wrap(head)
