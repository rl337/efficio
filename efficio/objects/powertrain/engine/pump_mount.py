"""Engine-side pump mounting adapter; drilling and bracket parameters explicit."""

from dataclasses import dataclass
from typing import Optional

from efficio.objects.base import EfficioObject
from efficio.objects.profiles import box, wrap, y_cylinder
from efficio.objects.shapes import Shape


@dataclass(frozen=True)
class PumpMountGeometry:
    pump_holes: tuple[tuple[float, float], ...]
    engine_holes: tuple[tuple[float, float], ...]
    plate_x: tuple[float, float]
    plate_z: tuple[float, float]
    crossbar_x: tuple[float, float]
    crossbar_z: tuple[float, float]
    back_y: float
    plate_thickness: float
    pump_face_y: float
    engine_face_y: float
    hole_radius: float
    spacer_radius: float


class PumpMount(EfficioObject):
    def __init__(self, geometry: PumpMountGeometry):
        self.g = geometry

    def shape(self) -> Optional[Shape]:
        g = self.g
        face = g.back_y + g.plate_thickness
        body = box(*g.plate_x, g.back_y, face, *g.plate_z).union(
            box(*g.crossbar_x, g.back_y, face, *g.crossbar_z)
        )
        for points, end in [
            (g.pump_holes, g.pump_face_y),
            (g.engine_holes, g.engine_face_y),
        ]:
            for x, z in points:
                body = body.union(y_cylinder(g.spacer_radius, face, end, x=x, z=z))
                body = body.cut(
                    y_cylinder(g.hole_radius, g.back_y - 1, end + 1, x=x, z=z)
                )
        return wrap(body)


class DrilledSupport(EfficioObject):
    """Variant preserves the original support except for actual mounting holes."""

    def __init__(
        self,
        original: EfficioObject,
        holes: tuple[tuple[float, float], ...],
        radius: float,
        y_start: float,
        y_end: float,
    ):
        self.original, self.holes, self.radius = original, holes, radius
        self.y_start, self.y_end = y_start, y_end

    def shape(self) -> Optional[Shape]:
        shape = self.original.shape()
        if shape is None:
            raise ValueError("support has no geometry")
        body = shape.workplane()
        for x, z in self.holes:
            body = body.cut(y_cylinder(self.radius, self.y_start, self.y_end, x=x, z=z))
        return wrap(body)
