"""Serviceable perforated strainer: geometric openings, no filtration rating."""

import math
from typing import Optional

from efficio.objects.base import EfficioObject
from efficio.objects.profiles import cylinder, wrap
from efficio.objects.pumps.geometry import StrainerGeometry
from efficio.objects.shapes import Shape


class StrainerPart(EfficioObject):
    def __init__(self, geometry: StrainerGeometry, kind: str):
        if kind not in {"body", "cap", "screen"}:
            raise ValueError("unknown strainer part")
        self.g, self.kind = geometry, kind

    def shape(self) -> Optional[Shape]:
        g = self.g
        if self.kind == "screen":
            z = g.length / 2
            body = cylinder(g.radius - g.wall, z, z + g.screen_thickness)
            points = [(0.0, 0.0)] + [
                (
                    g.hole_circle * math.cos(i * 2 * math.pi / g.hole_count),
                    g.hole_circle * math.sin(i * 2 * math.pi / g.hole_count),
                )
                for i in range(g.hole_count)
            ]
            for x, y in points:
                body = body.cut(
                    cylinder(g.hole_radius, z - 1, z + g.screen_thickness + 1, x=x, y=y)
                )
        elif self.kind == "body":
            body = cylinder(g.radius, 0, g.length - g.end_wall).cut(
                cylinder(g.radius - g.wall, g.end_wall, g.length)
            )
            body = body.cut(cylinder(g.port_radius, -1, g.length))
        else:
            body = cylinder(g.radius, g.length - g.end_wall, g.length).cut(
                cylinder(g.port_radius, g.length - g.end_wall - 1, g.length + 1)
            )
        return wrap(body)
