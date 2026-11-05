"""Two-part rounded boxes with a bolt channel."""

from typing import Optional

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.fasteners import BoltChannel, MetricThread
from efficio.objects.shapes import Orientation, Shape, new_shape


class RoundedBox(EfficioObject):
    """Filleted box split into a base and a lid, laid side by side.

    A bolt channel for ``fastener`` runs through the middle so the lid can be
    screwed to the base.
    """

    def __init__(
        self,
        width: Measure,
        length: Measure,
        depth: Measure,
        fillet_radius: Measure = Millimeter(3),
        wall_thickness: Measure = Millimeter(2),
        lid_height: Measure = Millimeter(3),
        part_spacing: Measure = Millimeter(1),
        fastener: MetricThread = MetricThread.M3,
    ):
        self.width = width
        self.length = length
        self.depth = depth
        self.fillet_radius = fillet_radius
        self.wall_thickness = wall_thickness
        self.lid_height = lid_height
        self.part_spacing = part_spacing
        self.fastener = fastener

    def shape(self) -> Optional[Shape]:
        width = self.width.value()
        length = self.length.value()
        depth = self.depth.value()
        fillet = self.fillet_radius.value()
        wall = self.wall_thickness.value()
        lid = self.lid_height.value()

        outside = (
            new_shape(Orientation.Front).box(width, length, depth).fillet_edges(fillet)
        )
        inside = (
            new_shape(Orientation.Front)
            .box(width - 2 * wall, length - 2 * wall, depth - 2 * wall)
            .fillet_edges(fillet)
        )
        hollow = outside.cut(inside)

        channel = BoltChannel(self.fastener, self.depth)
        channel_cut = channel.cut()
        if channel_cut:
            hollow.cut(channel_cut.translate(0, 0, -depth / 2))
        channel_shape = channel.shape()
        if channel_shape:
            hollow.union(channel_shape.translate(0, 0, -depth / 2))

        top = (
            hollow.cut_from_top(lid, clone=True)
            .translate(0, 0, -((depth - lid) / 2))
            .rotate(180, 0, 0)
            .translate(width + self.part_spacing.value(), 0, -((depth - lid) / 2))
        )
        bottom = hollow.cut_from_bottom(depth - lid)
        return bottom.union(top)
