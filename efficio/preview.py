"""Camera, shading and painter ordering for colour previews (pure Python).

World convention matches the powertrain layout: +X forward, +Y left to
right along the axle, +Z up.  Every view keeps +Z (or +Y for the top view)
pointing up the page.
"""

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from efficio.objects.base import Color

Vec3 = Tuple[float, float, float]
Triangle = Tuple[Vec3, Vec3, Vec3]
ScreenPolygon = Tuple[List[Tuple[float, float]], Color, float]


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def normalize(v: Vec3) -> Vec3:
    length = math.sqrt(_dot(v, v))
    if length == 0:
        raise ValueError("cannot normalise a zero vector")
    return (v[0] / length, v[1] / length, v[2] / length)


@dataclass(frozen=True)
class View:
    """Orthographic camera looking back along ``toward_camera``."""

    title: str
    toward_camera: Vec3
    up_hint: Vec3

    @property
    def forward(self) -> Vec3:
        return normalize(self.toward_camera)

    @property
    def right(self) -> Vec3:
        return normalize(_cross(self.up_hint, self.forward))

    @property
    def up(self) -> Vec3:
        return _cross(self.forward, self.right)

    def project(self, point: Vec3) -> Tuple[float, float, float]:
        """(screen x, screen y with +up, depth with +toward camera)."""
        return (
            _dot(point, self.right),
            _dot(point, self.up),
            _dot(point, self.forward),
        )

    @property
    def light(self) -> Vec3:
        """Key light from over the viewer's left shoulder."""
        f, r, u = self.forward, self.right, self.up
        return normalize(
            (
                f[0] + 0.6 * u[0] - 0.4 * r[0],
                f[1] + 0.6 * u[1] - 0.4 * r[1],
                f[2] + 0.6 * u[2] - 0.4 * r[2],
            )
        )


TOP = View("TOP (looking down, forward to the right)", (0, 0, 1), (0, 1, 0))
FRONT = View("FRONT (from ahead, left wheel on the left)", (1, 0, 0), (0, 0, 1))
SIDE = View("LEFT SIDE (forward to the right)", (0, -1, 0), (0, 0, 1))
ISOMETRIC = View("ISOMETRIC (front-left, above)", (1, -1.2, 0.9), (0, 0, 1))
STANDARD_VIEWS: Tuple[View, ...] = (TOP, FRONT, SIDE, ISOMETRIC)


def shade(color: Color, normal: Vec3, view: View, ambient: float = 0.38) -> Color:
    """Lambert shading; two-sided so triangle winding does not matter."""
    try:
        n = normalize(normal)
    except ValueError:
        return color
    intensity = ambient + (1.0 - ambient) * abs(_dot(n, view.light))
    return (
        min(255, int(round(color[0] * intensity))),
        min(255, int(round(color[1] * intensity))),
        min(255, int(round(color[2] * intensity))),
    )


def triangle_normal(triangle: Triangle) -> Vec3:
    a, b, c = triangle
    return _cross(_sub(b, a), _sub(c, a))


@dataclass(frozen=True)
class Viewport:
    """Maps projected coordinates into a pixel rectangle, preserving aspect."""

    scale: float
    offset_x: float
    offset_y: float

    @staticmethod
    def fit(
        points: Iterable[Tuple[float, float]],
        width: int,
        height: int,
        margin: int,
    ) -> "Viewport":
        xs: List[float] = []
        ys: List[float] = []
        for x, y in points:
            xs.append(x)
            ys.append(y)
        if not xs:
            raise ValueError("nothing to fit")
        span_x = max(max(xs) - min(xs), 1e-6)
        span_y = max(max(ys) - min(ys), 1e-6)
        scale = min((width - 2 * margin) / span_x, (height - 2 * margin) / span_y)
        centre_x = (max(xs) + min(xs)) / 2
        centre_y = (max(ys) + min(ys)) / 2
        return Viewport(
            scale, width / 2 - centre_x * scale, height / 2 + centre_y * scale
        )

    def to_pixels(self, x: float, y: float) -> Tuple[float, float]:
        # Screen y grows downward in images, so flip.
        return (self.offset_x + x * self.scale, self.offset_y - y * self.scale)


def paint_order(
    triangles: Sequence[Tuple[Triangle, Color]],
    view: View,
    width: int,
    height: int,
    margin: int,
) -> Tuple[List[ScreenPolygon], Viewport]:
    """Shaded screen polygons sorted far-to-near (painter's algorithm)."""
    projected: List[Tuple[List[Tuple[float, float, float]], Color, Vec3]] = []
    for triangle, color in triangles:
        projected.append(
            ([view.project(p) for p in triangle], color, triangle_normal(triangle))
        )
    viewport = Viewport.fit(
        ((x, y) for points, _, _ in projected for x, y, _ in points),
        width,
        height,
        margin,
    )
    polygons: List[ScreenPolygon] = []
    for points, color, normal in projected:
        depth = sum(p[2] for p in points) / 3.0
        pixels = [viewport.to_pixels(x, y) for x, y, _ in points]
        polygons.append((pixels, shade(color, normal, view), depth))
    polygons.sort(key=lambda polygon: polygon[2])
    return polygons, viewport
