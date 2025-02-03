from typing import Optional

from efficio.measures import (
    Measure,
    Millimeter
)

from efficio.objects.base import EfficioObject
from efficio.objects.shapes import new_shape, Orientation, Shape
from efficio.objects.primitives import Cylinder
from efficio.objects.m3 import M3BoltChannel


BOX_FILLET_RADIUS = Millimeter(3)
BOX_LID_HEIGHT = Millimeter(3)
BOX_WALL_THICKNESS = Millimeter(2)
PART_SPACING = Millimeter(1)


class RoundedBox(EfficioObject):
    length: Measure
    width: Measure
    depth: Measure

    def __init__(self, width: Measure, length: Measure, depth: Measure):
        self.width = width
        self.length = length
        self.depth = depth

    def shape(self) -> Optional[Shape]:
        box_width_mm = self.width.value()
        box_length_mm = self.length.value()
        box_depth_mm = self.depth.value()

        box_shape = new_shape(Orientation.Front).box(
            box_width_mm,
            box_length_mm,
            box_depth_mm
        ).fillet_edges(BOX_FILLET_RADIUS.value())

        wall_thickness_mm = BOX_WALL_THICKNESS.value()
        wall_offset_mm = wall_thickness_mm * 2
        inside_shape = new_shape(Orientation.Front).box(
            box_width_mm - wall_offset_mm,
            box_length_mm - wall_offset_mm,
            box_depth_mm - wall_offset_mm
        ).fillet_edges(BOX_FILLET_RADIUS.value())

        hollow_box = box_shape.cut(inside_shape)
        channel = M3BoltChannel(self.depth)
        channel_cut = channel.cut()
        if channel_cut:
            hollow_box.cut(channel_cut.translate(0, 0, -box_depth_mm/2))
        channel_shape = channel.shape()
        if channel_shape:
            hollow_box.union(channel_shape.translate(0, 0, -box_depth_mm/2))


        box_top = hollow_box.cut_from_top(BOX_LID_HEIGHT.value(), clone=True).translate(
            0,
            0,
            -((box_depth_mm - BOX_LID_HEIGHT.value()) / 2)
        ).rotate(180, 0, 0).translate(
            box_width_mm + PART_SPACING.value(),
            0,
            -((box_depth_mm - BOX_LID_HEIGHT.value()) / 2)
        )
        
        box_bottom = hollow_box.cut_from_bottom(box_depth_mm - BOX_LID_HEIGHT.value())

        return box_bottom.union(box_top)
