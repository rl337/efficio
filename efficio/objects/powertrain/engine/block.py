"""Split crankcase / cylinder block and cylinder head.

Both are modelled in the engine-local frame of :class:`EngineGeometry`: crank
axis on +Y from the flange face (y = 0), split plane z = 0, cylinders on +Z.
"""

from typing import Optional

import cadquery as cq

from efficio.objects.base import EfficioObject
from efficio.objects.powertrain.engine.geometry import EngineGeometry
from efficio.objects.profiles import (
    bearing_seat_cutter,
    box,
    cylinder,
    wrap,
    x_cylinder,
    y_cylinder,
)
from efficio.objects.shapes import Shape


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
        journal_clearance = e.crank_journal_diameter / 2 + e.journal_hole_clearance
        bolt = e.fastener.spec
        tap, clear = bolt.tap_radius, bolt.clearance_radius
        counterbore = bolt.head_radius + 0.25

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
            block = block.cut(cylinder(tap, deck - e.head_bolt_depth, deck + 1, x, y))
        for x, y in e.split_bolt_positions():
            block = block.cut(cylinder(tap, -0.1, e.split_bolt_tap_depth, x, y))
            block = block.cut(cylinder(clear, -hw - 1, 0.0, x, y))
            block = block.cut(
                cylinder(counterbore, -hw - 1, -hw + bolt.head_height, x, y)
            )
        if e.front_flange:
            for x, z in e.flange_bolt_offsets():
                block = block.cut(y_cylinder(tap, -1.0, e.flange_bolt_depth, x, z))
        depth = e.side_mount_depth
        for y, z in e.side_mount_positions():
            block = block.cut(x_cylinder(tap, -hw - 1, -hw + depth, y, z))
            block = block.cut(x_cylinder(tap, hw - depth, hw + 1, y, z))
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

    def __init__(self, engine: EngineGeometry):
        self.engine = engine

    def shape(self) -> Optional[Shape]:
        e = self.engine
        hw = e.block_half_width
        t = e.head_thickness
        head = box(-hw, hw, 0.0, e.block_length, 0.0, t)
        for i in range(e.cylinders):
            head = head.cut(
                cylinder(e.bore / 2, -1.0, e.head_recess_depth, 0.0, e.cylinder_y(i))
            )
        for x, y in e.head_bolt_positions():
            head = head.cut(
                cylinder(e.fastener.spec.clearance_radius, -1.0, t + 1.0, x, y)
            )
        return wrap(head)
