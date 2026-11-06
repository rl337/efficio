"""Pure 2D helpers shared by gear, plate and layout code (no CadQuery)."""

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

Point = Tuple[float, float]


@dataclass(frozen=True)
class Span:
    """Closed interval along an axis (used for axial stack-ups)."""

    start: float
    end: float

    @property
    def length(self) -> float:
        return self.end - self.start

    @property
    def centre(self) -> float:
        return (self.start + self.end) / 2.0

    def overlaps(self, other: "Span") -> bool:
        return self.start < other.end and other.start < self.end

    def shifted(self, offset: float) -> "Span":
        return Span(self.start + offset, self.end + offset)


def polar(radius: float, angle: float) -> Point:
    return (radius * math.cos(angle), radius * math.sin(angle))


def circle_points(centre: Point, radius: float, samples: int = 32) -> List[Point]:
    return [
        (
            centre[0] + radius * math.cos(2 * math.pi * i / samples),
            centre[1] + radius * math.sin(2 * math.pi * i / samples),
        )
        for i in range(samples)
    ]


def convex_hull(points: Iterable[Point]) -> List[Point]:
    """Andrew's monotone chain; returns CCW hull without repeated end point."""
    unique = sorted(set((round(x, 6), round(y, 6)) for x, y in points))
    if len(unique) <= 2:
        return list(unique)

    def cross(o: Point, a: Point, b: Point) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: List[Point] = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: List[Point] = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def hull_of_circles(circles: Sequence[Tuple[Point, float]]) -> List[Point]:
    points: List[Point] = []
    for centre, radius in circles:
        points.extend(circle_points(centre, radius, 48))
    return convex_hull(points)


def densify(polygon: Sequence[Point], step: float = 0.5) -> List[Point]:
    """Insert points along each edge of a closed polygon every ``step`` mm."""
    dense: List[Point] = []
    for i, a in enumerate(polygon):
        b = polygon[(i + 1) % len(polygon)]
        steps = max(1, int(distance(a, b) / step))
        for k in range(steps):
            t = k / steps
            dense.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return dense


def distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])
