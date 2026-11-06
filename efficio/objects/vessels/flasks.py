from typing import Optional

from efficio.measures import Measure
from efficio.objects.base import EfficioObject
from efficio.objects.shapes import Orientation, Shape, new_shape


class TriangularFlaskVase(EfficioObject):
    """Simple triangular flask master: broad triangular body plus narrow neck.

    ``body_fraction`` is the share of the height taken by the body.
    """

    def __init__(
        self,
        width: Measure,
        height: Measure,
        depth: Measure,
        neck: Measure,
        body_fraction: float = 0.72,
    ):
        if not 0.0 < body_fraction < 1.0:
            raise ValueError("body_fraction must be between 0 and 1")
        if min(width.value(), height.value(), depth.value(), neck.value()) <= 0:
            raise ValueError("Flask dimensions must be positive")
        if neck.value() > width.value():
            raise ValueError("Neck must not be wider than the body")
        self.width = width
        self.height = height
        self.depth = depth
        self.neck = neck
        self.body_fraction = body_fraction

    def shape(self) -> Optional[Shape]:
        width = self.width.value()
        height = self.height.value()
        depth = self.depth.value()
        neck = self.neck.value()
        body_height = height * self.body_fraction

        body = (
            new_shape(Orientation.Front)
            .polyline(
                [
                    (-width / 2, 0),
                    (width / 2, 0),
                    (neck / 2, body_height),
                    (-neck / 2, body_height),
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
