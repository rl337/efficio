"""Pure-math involute spur gear geometry and planar helpers.

Nothing in this module depends on CadQuery so gear sizing, meshing phase and
layout clearances can be validated quickly and independently of the solid
modelling kernel.
"""

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

Point = Tuple[float, float]


def involute_function(angle: float) -> float:
    """inv(a) = tan(a) - a."""
    return math.tan(angle) - angle


@dataclass(frozen=True)
class InvoluteGearGeometry:
    """Standard (unshifted) external involute spur gear.

    ``backlash`` is the circular-thickness reduction applied to *each* tooth at
    the pitch circle, giving running clearance between meshing printed teeth.
    """

    module: float
    teeth: int
    pressure_angle_degrees: float = 25.0
    backlash: float = 0.15
    addendum_coefficient: float = 1.0
    dedendum_coefficient: float = 1.25

    def __post_init__(self) -> None:
        if self.teeth < 6:
            raise ValueError("Involute gears require at least six teeth")
        if self.module <= 0:
            raise ValueError("Gear module must be positive")

    @property
    def pressure_angle(self) -> float:
        return math.radians(self.pressure_angle_degrees)

    @property
    def pitch_radius(self) -> float:
        return self.module * self.teeth / 2.0

    @property
    def base_radius(self) -> float:
        return self.pitch_radius * math.cos(self.pressure_angle)

    @property
    def tip_radius(self) -> float:
        return self.pitch_radius + self.addendum_coefficient * self.module

    @property
    def root_radius(self) -> float:
        return self.pitch_radius - self.dedendum_coefficient * self.module

    @property
    def angular_pitch(self) -> float:
        return 2.0 * math.pi / self.teeth

    def half_thickness_angle(self, radius: float) -> float:
        """Angular half-thickness of a tooth at ``radius`` (>= base radius)."""
        circular_thickness = math.pi * self.module / 2.0 - self.backlash
        psi_pitch = circular_thickness / (2.0 * self.pitch_radius)
        phi = math.acos(min(1.0, self.base_radius / radius))
        return (
            psi_pitch + involute_function(self.pressure_angle) - involute_function(phi)
        )

    def tip_land_width(self) -> float:
        return 2.0 * self.tip_radius * self.half_thickness_angle(self.tip_radius)

    def outline(self, flank_samples: int = 6, root_samples: int = 3) -> List[Point]:
        """Closed (implicitly) CCW outline; tooth 0 is centred on +X."""
        if self.tip_land_width() <= 0:
            raise ValueError("Gear teeth are pointed; reduce backlash or addendum")

        flank_start = max(self.base_radius, self.root_radius)
        radii = [
            flank_start + (self.tip_radius - flank_start) * i / flank_samples
            for i in range(flank_samples + 1)
        ]
        psi_start = self.half_thickness_angle(flank_start)

        points: List[Point] = []
        for tooth in range(self.teeth):
            centre = tooth * self.angular_pitch

            if self.root_radius < flank_start:
                points.append(_polar(self.root_radius, centre - psi_start))
            for radius in radii:
                points.append(
                    _polar(radius, centre - self.half_thickness_angle(radius))
                )
            points.append(_polar(self.tip_radius, centre))
            for radius in reversed(radii):
                points.append(
                    _polar(radius, centre + self.half_thickness_angle(radius))
                )
            if self.root_radius < flank_start:
                points.append(_polar(self.root_radius, centre + psi_start))

            # Root land between this tooth and the next one.
            gap_start = centre + psi_start
            gap_end = centre + self.angular_pitch - psi_start
            for i in range(1, root_samples + 1):
                angle = gap_start + (gap_end - gap_start) * i / (root_samples + 1)
                points.append(_polar(self.root_radius, angle))

        return points


def centre_distance(module: float, teeth_a: int, teeth_b: int) -> float:
    return module * (teeth_a + teeth_b) / 2.0


def mesh_phase(
    driver_centre: Point,
    driver_phase_degrees: float,
    driver_teeth: int,
    driven_centre: Point,
    driven_teeth: int,
) -> float:
    """Rotation (degrees) for the driven gear so its gaps receive the driver.

    Both gears use the convention that tooth 0 is centred on local +X before
    rotation.  The returned angle is normalised to one angular pitch.
    """
    alpha = math.degrees(
        math.atan2(
            driven_centre[1] - driver_centre[1], driven_centre[0] - driver_centre[0]
        )
    )
    phase = (
        alpha
        + 180.0
        + 180.0 / driven_teeth
        - (driver_teeth / driven_teeth) * (driver_phase_degrees - alpha)
    )
    pitch = 360.0 / driven_teeth
    return phase % pitch


def _polar(radius: float, angle: float) -> Point:
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


def distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])
