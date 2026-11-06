"""Pure-math involute spur gear geometry and planar helpers.

Nothing in this module depends on CadQuery so gear sizing, meshing phase and
layout clearances can be validated quickly and independently of the solid
modelling kernel.
"""

import math
from dataclasses import dataclass
from typing import List

from efficio.objects.planar import Point, polar


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
        if isinstance(self.teeth, bool) or not isinstance(self.teeth, int):
            raise ValueError("Tooth count must be an integer")
        if self.teeth < 6:
            raise ValueError("Involute gears require at least six teeth")
        if not math.isfinite(self.module) or self.module <= 0:
            raise ValueError("Gear module must be finite and positive")
        if not 0 < self.pressure_angle_degrees < 90:
            raise ValueError("Pressure angle must be between zero and 90 degrees")
        if not 0 <= self.backlash < math.pi * self.module / 2:
            raise ValueError(
                "Backlash must leave positive pitch-circle tooth thickness"
            )
        if (
            not math.isfinite(self.addendum_coefficient)
            or self.addendum_coefficient <= 0
        ):
            raise ValueError("Addendum coefficient must be finite and positive")
        if not 0 < self.dedendum_coefficient < self.teeth / 2:
            raise ValueError("Dedendum coefficient must leave a positive root radius")

    @classmethod
    def from_tip_radius(
        cls,
        tip_radius: float,
        teeth: int,
        pressure_angle_degrees: float = 20.0,
        backlash: float = 0.0,
        addendum_coefficient: float = 1.0,
        dedendum_coefficient: float = 1.25,
    ) -> "InvoluteGearGeometry":
        """Specify the outside envelope without maintaining separate profile math."""
        if not math.isfinite(tip_radius) or tip_radius <= 0:
            raise ValueError("Tip radius must be finite and positive")
        if not math.isfinite(addendum_coefficient) or addendum_coefficient <= 0:
            raise ValueError("Addendum coefficient must be finite and positive")
        if isinstance(teeth, bool) or not isinstance(teeth, int) or teeth < 6:
            raise ValueError(
                "Involute gears require an integer tooth count of at least six"
            )
        return cls(
            tip_radius / (teeth / 2 + addendum_coefficient),
            teeth,
            pressure_angle_degrees,
            backlash,
            addendum_coefficient,
            dedendum_coefficient,
        )

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
        if not math.isfinite(radius) or radius < self.base_radius:
            raise ValueError("The involute is undefined below its base circle")
        circular_thickness = math.pi * self.module / 2.0 - self.backlash
        psi_pitch = circular_thickness / (2.0 * self.pitch_radius)
        phi = math.acos(min(1.0, self.base_radius / radius))
        return (
            psi_pitch + involute_function(self.pressure_angle) - involute_function(phi)
        )

    def tip_land_width(self) -> float:
        return 2.0 * self.tip_radius * self.half_thickness_angle(self.tip_radius)

    def material_disc_radius(self) -> float:
        """Guaranteed solid disc inside the sampled outline used by spur blanks.

        Root lands are chords, so their clearance envelope is slightly smaller
        than the analytic root circle. Use actual segments for fabrication webs.
        """
        points = self.outline()
        minimum = self.root_radius
        for start, end in zip(points, points[1:] + points[:1]):
            dx, dy = end[0] - start[0], end[1] - start[1]
            length_squared = dx * dx + dy * dy
            fraction = (
                max(0.0, min(1.0, -(start[0] * dx + start[1] * dy) / length_squared))
                if length_squared
                else 0.0
            )
            minimum = min(
                minimum, math.hypot(start[0] + fraction * dx, start[1] + fraction * dy)
            )
        return minimum

    def flank_point(self, radius: float, side: int) -> Point:
        """Point on tooth zero's lower (-1) or upper (+1) involute flank."""
        if side not in (-1, 1):
            raise ValueError("side must be -1 or +1")
        return polar(radius, side * self.half_thickness_angle(radius))

    def _tooth_outline_at(self, centre: float, flank_samples: int) -> List[Point]:
        flank_start = max(self.base_radius, self.root_radius)
        radii = [
            flank_start + (self.tip_radius - flank_start) * i / flank_samples
            for i in range(flank_samples + 1)
        ]
        psi_start = self.half_thickness_angle(flank_start)
        points: List[Point] = []
        if self.root_radius < flank_start:
            points.append(polar(self.root_radius, centre - psi_start))
        for radius in radii:
            points.append(polar(radius, centre - self.half_thickness_angle(radius)))
        points.append(polar(self.tip_radius, centre))
        for radius in reversed(radii):
            points.append(polar(radius, centre + self.half_thickness_angle(radius)))
        if self.root_radius < flank_start:
            points.append(polar(self.root_radius, centre + psi_start))
        return points

    def _validate_sampling(self, flank_samples: int) -> None:
        if (
            isinstance(flank_samples, bool)
            or not isinstance(flank_samples, int)
            or flank_samples < 2
        ):
            raise ValueError("flank_samples must be an integer of at least two")
        if self.tip_land_width() <= 0:
            raise ValueError("Gear teeth are pointed; reduce backlash or addendum")

    def tooth_outline(self, flank_samples: int = 6) -> List[Point]:
        """Implicitly closed CCW single tooth, centred on +X.

        The closing chord joins the two root endpoints inside the root disc.
        Below-base segments are radial extensions, not generated root fillets.
        This profile is independent of any extrusion or future sweep path.
        """
        self._validate_sampling(flank_samples)
        return self._tooth_outline_at(0.0, flank_samples)

    def outline(self, flank_samples: int = 6, root_samples: int = 3) -> List[Point]:
        """Closed (implicitly) CCW outline; tooth 0 is centred on +X."""
        self._validate_sampling(flank_samples)
        if (
            isinstance(root_samples, bool)
            or not isinstance(root_samples, int)
            or root_samples < 0
        ):
            raise ValueError("root_samples must be a non-negative integer")
        psi_start = self.half_thickness_angle(max(self.base_radius, self.root_radius))
        points: List[Point] = []
        for tooth in range(self.teeth):
            centre = tooth * self.angular_pitch
            points.extend(self._tooth_outline_at(centre, flank_samples))
            gap_start = centre + psi_start
            gap_end = centre + self.angular_pitch - psi_start
            for i in range(1, root_samples + 1):
                angle = gap_start + (gap_end - gap_start) * i / (root_samples + 1)
                points.append(polar(self.root_radius, angle))
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
