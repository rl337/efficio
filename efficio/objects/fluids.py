"""Parameterized hollow tube networks; geometry does not establish fluid flow."""

import math
from typing import List, Optional, Tuple

import cadquery as cq

from efficio.objects.base import EfficioObject
from efficio.objects.profiles import wrap
from efficio.objects.shapes import Shape

Point3 = Tuple[float, float, float]


class TubeNetwork(EfficioObject):
    """Union of round segments with spherical internal bends and open ends.

    A branch must meet another branch geometrically; bore_solid() permits explicit
    connectivity checks. Bend radii, fittings and fabrication are not qualified.
    """

    def __init__(self, paths: List[List[Point3]], bore_radius: float, wall: float):
        if not paths or any(len(p) < 2 for p in paths):
            raise ValueError("tube paths need at least two points")
        if not all(math.isfinite(v) and v > 0 for v in (bore_radius, wall)):
            raise ValueError("tube radii must be positive and finite")
        if any(not all(math.isfinite(v) for v in p) for path in paths for p in path):
            raise ValueError("tube coordinates must be finite")
        if any(a == b for path in paths for a, b in zip(path, path[1:])):
            raise ValueError("tube segments must have positive length")
        self.paths, self.bore_radius, self.wall = paths, bore_radius, wall

    def envelope(self, radius: float) -> cq.Shape:
        pieces: List[cq.Shape] = []
        for path in self.paths:
            for a, b in zip(path, path[1:]):
                start = cq.Vector(*a)
                delta = cq.Vector(*b) - start
                pieces.append(
                    cq.Solid.makeCylinder(
                        radius, delta.Length, start, delta.normalized()
                    )
                )
            pieces.extend(
                cq.Solid.makeSphere(radius, cq.Vector(*p), angleDegrees1=-90)
                for p in path[1:-1]
            )
        result = pieces[0]
        for piece in pieces[1:]:
            result = result.fuse(piece)
        return result.clean()

    def bore_solid(self) -> cq.Shape:
        return self.envelope(self.bore_radius)

    def shape(self) -> Optional[Shape]:
        solid = (
            self.envelope(self.bore_radius + self.wall).cut(self.bore_solid()).clean()
        )
        return wrap(cq.Workplane("XY").newObject([solid]))
