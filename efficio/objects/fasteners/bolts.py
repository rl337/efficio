"""Socket head cap screws, hex nuts, bolt + nut pairs and bolt channels.

Generic classes take a :class:`MetricThread`; the ``M3...`` classes are the
standard-level variants that fix only the thread (length stays free).
"""

from typing import Optional

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.fasteners.threads import MetricThread
from efficio.objects.primitives import Cylinder
from efficio.objects.shapes import Orientation, Shape, new_shape

DEFAULT_FASTENER_CLEARANCE = Millimeter(0.20)
DEFAULT_CHANNEL_PADDING = Millimeter(0.5)


def _clearance(has_clearance: bool, clearance: Measure) -> float:
    return clearance.value() if has_clearance else 0.0


class BoltShaft(EfficioObject):
    """Plain cylinder for a threaded shank (threads are not modelled)."""

    def __init__(
        self,
        diameter: Measure,
        length: Measure,
        has_clearance: bool,
        clearance: Measure = DEFAULT_FASTENER_CLEARANCE,
    ):
        self._diameter = diameter
        self._length = length
        self._has_clearance = has_clearance
        self._clearance = clearance

    def shape(self) -> Optional[Shape]:
        radius = self._diameter.value() / 2 + _clearance(
            self._has_clearance, self._clearance
        )
        return new_shape(Orientation.Front).circle(radius).extrude(self._length.value())

    def length(self) -> Measure:
        return self._length


class BoltHead(EfficioObject):
    """Cylindrical socket cap head."""

    def __init__(
        self,
        diameter: Measure,
        height: Measure,
        has_clearance: bool,
        clearance: Measure = DEFAULT_FASTENER_CLEARANCE,
    ):
        self._diameter = diameter
        self._height = height
        self._has_clearance = has_clearance
        self._clearance = clearance

    def shape(self) -> Optional[Shape]:
        radius = self._diameter.value() / 2 + _clearance(
            self._has_clearance, self._clearance
        )
        return new_shape(Orientation.Front).circle(radius).extrude(self._height.value())

    def height(self) -> Measure:
        return self._height


class Bolt(EfficioObject):
    """Socket head cap screw: head on z = 0, shank of ``length`` above it."""

    head: BoltHead
    shaft: BoltShaft

    def __init__(
        self,
        thread: MetricThread,
        length: Measure,
        has_clearance: bool,
        clearance: Measure = DEFAULT_FASTENER_CLEARANCE,
    ):
        spec = thread.spec
        self.thread = thread
        self.head = BoltHead(
            Millimeter(spec.head_diameter),
            Millimeter(spec.head_height),
            has_clearance,
            clearance,
        )
        self.shaft = BoltShaft(
            Millimeter(spec.major_diameter), length, has_clearance, clearance
        )

    def shape(self) -> Optional[Shape]:
        head_shape = self.head.shape()
        shaft_shape = self.shaft.shape()
        if head_shape is None or shaft_shape is None:
            return None
        shaft_shape = shaft_shape.translate(0, 0, self.head.height().value())
        return head_shape.union(shaft_shape)


class HexNut(EfficioObject):
    def __init__(
        self,
        thread: MetricThread,
        has_clearance: bool,
        clearance: Measure = DEFAULT_FASTENER_CLEARANCE,
    ):
        self.thread = thread
        self._has_clearance = has_clearance
        self._clearance = clearance

    def height(self) -> Measure:
        return Millimeter(self.thread.spec.nut_height)

    def shape(self) -> Optional[Shape]:
        spec = self.thread.spec
        corners = spec.nut_across_corners + _clearance(
            self._has_clearance, self._clearance
        )
        return new_shape(Orientation.Front).polygon(6, corners).extrude(spec.nut_height)


class BoltAssembly(EfficioObject):
    """Bolt with its nut run down to the end of the shank."""

    bolt: Bolt
    nut: HexNut

    def __init__(
        self,
        thread: MetricThread,
        length: Measure,
        has_clearance: bool,
        clearance: Measure = DEFAULT_FASTENER_CLEARANCE,
    ):
        self.bolt = Bolt(thread, length, has_clearance, clearance)
        self.nut = HexNut(thread, has_clearance, clearance)

    def shape(self) -> Optional[Shape]:
        bolt_shape = self.bolt.shape()
        nut_shape = self.nut.shape()
        if bolt_shape is None or nut_shape is None:
            return None
        top = (
            self.bolt.head.height().value()
            + self.bolt.shaft.length().value()
            - self.nut.height().value()
        )
        return bolt_shape.union(nut_shape.translate(0, 0, top))


class BoltChannel(EfficioObject):
    """Column with a bolt + nut cavity: ``shape()`` is the boss, ``cut()``
    the envelope to remove from a host part.  ``length`` is the overall
    height including the head."""

    bolt_assembly: BoltAssembly
    column: Cylinder

    def __init__(
        self,
        thread: MetricThread,
        length: Measure,
        padding: Measure = DEFAULT_CHANNEL_PADDING,
    ):
        spec = thread.spec
        shank = Millimeter(length.value() - spec.head_height)
        self.bolt_assembly = BoltAssembly(thread, shank, True)
        assembly = self.bolt_assembly.shape()
        bounds = assembly.bounds() if assembly is not None else None
        if bounds is None:
            raise ValueError("bolt assembly produced no geometry")
        width = max(bounds[3] - bounds[0], bounds[4] - bounds[1])
        self.column = Cylinder(
            Millimeter(bounds[5] - bounds[2]),
            Millimeter(width / 2 + padding.value()),
        )

    def shape(self) -> Optional[Shape]:
        channel = self.column.shape()
        assembly = self.bolt_assembly.shape()
        if channel is None or assembly is None:
            return None
        return channel.cut(assembly)

    def cut(self) -> Optional[Shape]:
        return self.column.shape()


# ---------------------------------------------------------------- standard M3
class M3BoltShaft(BoltShaft):
    def __init__(self, length: Measure, has_clearance: bool):
        super().__init__(
            Millimeter(MetricThread.M3.spec.major_diameter), length, has_clearance
        )


class M3BoltHead(BoltHead):
    def __init__(self, has_clearance: bool):
        spec = MetricThread.M3.spec
        super().__init__(
            Millimeter(spec.head_diameter), Millimeter(spec.head_height), has_clearance
        )


class M3Bolt(Bolt):
    """ISO 4762 M3 socket head cap screw of any length."""

    def __init__(self, length: Measure, has_clearance: bool):
        super().__init__(MetricThread.M3, length, has_clearance)


class M3HexNut(HexNut):
    def __init__(self, has_clearance: bool):
        super().__init__(MetricThread.M3, has_clearance)


class M3BoltAssembly(BoltAssembly):
    def __init__(self, length: Measure, has_clearance: bool):
        super().__init__(MetricThread.M3, length, has_clearance)


class M3BoltChannel(BoltChannel):
    def __init__(self, length: Measure):
        super().__init__(MetricThread.M3, length)
