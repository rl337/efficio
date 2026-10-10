from typing import Optional

from efficio.measures import Measure
from efficio.objects.base import EfficioObject
from efficio.objects.shapes import Orientation, Shape, new_shape


class TriangularFlaskVase(EfficioObject):
    """Simple triangular flask master: broad triangular body plus narrow neck."""

    def __init__(self, width: Measure, height: Measure, depth: Measure, neck: Measure):
        self.width = width
        self.height = height
        self.depth = depth
        self.neck = neck

    def shape(self) -> Optional[Shape]:
        width = self.width.value()
        height = self.height.value()
        depth = self.depth.value()
        neck = self.neck.value()
        body_height = height * 0.72

        body = (
            new_shape(Orientation.Front)
            .polyline(
                [
                    (-width / 2, 0),
                    (width / 2, 0),
                    (0, body_height),
                ]
            )
            .extrude(depth)
        )
        neck_shape = (
            new_shape(Orientation.Front)
            .box(neck, height - body_height, depth)
            .translate(0, body_height + (height - body_height) / 2, depth / 2)
        )
        return body.union(neck_shape)
