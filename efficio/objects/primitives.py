from typing import Optional

from efficio.measures import Measure
from efficio.objects.base import EfficioObject
from efficio.objects.shapes import Orientation, Shape, new_shape


class Cylinder(EfficioObject):
    length: Measure
    radius: Measure

    def __init__(self, length: Measure, radius: Measure):
        self.length = length
        self.radius = radius

    def shape(self) -> Optional[Shape]:
        length_mm = self.length.value()
        radius_mm = self.radius.value()

        shaft_shape = new_shape(Orientation.Front).circle(radius_mm).extrude(length_mm)

        return shaft_shape


class Box(EfficioObject):
    width: Measure
    length: Measure
    depth: Measure

    def __init__(self, width: Measure, length: Measure, depth: Measure):
        self.width = width
        self.length = length
        self.depth = depth

    def shape(self) -> Optional[Shape]:
        width_mm = self.width.value()
        length_mm = self.length.value()
        depth_mm = self.depth.value()

        shaft_shape = new_shape(Orientation.Front).box(width_mm, length_mm, depth_mm)

        return shaft_shape


class Sphere(EfficioObject):
    radius: Measure

    def __init__(self, radius: Measure):
        self.radius = radius

    def shape(self) -> Optional[Shape]:
        radius_mm = self.radius.value()

        return new_shape(Orientation.Front).sphere(radius_mm)
