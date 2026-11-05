"""Push-button caps: a head on a round shaft."""

from typing import Optional

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.shapes import Orientation, Shape, new_shape

DEFAULT_BUTTON_CLEARANCE = Millimeter(0.20)


def _round_prism(
    diameter: Measure, height: Measure, has_clearance: bool, clearance: Measure
) -> Shape:
    radius = diameter.value() / 2.0 + (clearance.value() if has_clearance else 0.0)
    return new_shape(Orientation.Front).circle(radius).extrude(height.value())


class ButtonShaft(EfficioObject):
    def __init__(
        self,
        length: Measure,
        diameter: Measure,
        has_clearance: bool,
        clearance: Measure = DEFAULT_BUTTON_CLEARANCE,
    ):
        self._length = length
        self._diameter = diameter
        self._has_clearance = has_clearance
        self._clearance = clearance

    def shape(self) -> Optional[Shape]:
        return _round_prism(
            self._diameter, self._length, self._has_clearance, self._clearance
        )

    def length(self) -> Measure:
        return self._length


class ButtonHead(EfficioObject):
    def __init__(
        self,
        height: Measure,
        diameter: Measure,
        has_clearance: bool,
        clearance: Measure = DEFAULT_BUTTON_CLEARANCE,
    ):
        self._height = height
        self._diameter = diameter
        self._has_clearance = has_clearance
        self._clearance = clearance

    def shape(self) -> Optional[Shape]:
        return _round_prism(
            self._diameter, self._height, self._has_clearance, self._clearance
        )

    def height(self) -> Measure:
        return self._height


class Button(EfficioObject):
    """Head on z = 0 with the shaft standing on top of it."""

    head: ButtonHead
    shaft: ButtonShaft

    def __init__(
        self,
        head_height: Measure,
        head_diameter: Measure,
        shaft_length: Measure,
        shaft_diameter: Measure,
        has_clearance: bool,
        clearance: Measure = DEFAULT_BUTTON_CLEARANCE,
    ):
        self.head = ButtonHead(head_height, head_diameter, has_clearance, clearance)
        self.shaft = ButtonShaft(shaft_length, shaft_diameter, has_clearance, clearance)

    def shape(self) -> Optional[Shape]:
        head_shape = self.head.shape()
        shaft_shape = self.shaft.shape()
        if head_shape is None or shaft_shape is None:
            return None
        # The shaft starts on top of this button's own head.
        shaft_shape = shaft_shape.translate(0, 0, self.head.height().value())
        return head_shape.union(shaft_shape)
