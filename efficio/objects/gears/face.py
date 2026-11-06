"""Face (crown) gear geometry for a right-angle drive with a spur pinion.

Pure Python.  A face gear meshes a standard involute spur pinion whose axis
is perpendicular to, and intersects, the face gear axis.  At radius ``r`` the
face gear tooth section is the rack conjugate to the pinion: its linear pitch
is ``2 pi r / N`` and its pressure angle ``alpha_r`` satisfies

    cos(alpha_r) = R_p * cos(alpha_0) / r

so the base pitch equals the pinion's (``pi m cos alpha_0``) at every
radius.  The rack's pitch line sits where its pitch matches the pinion's
operating pitch circle, which moves with ``r``.  Teeth exist only between an
inner radius (flanks becoming radial) and an outer radius (tips pointed).

Local frame: the face gear axis is +Z, teeth point toward +Z (toward the
pinion), and tooth 0 is centred on +X.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple

Section = Tuple[float, List[Tuple[float, float]]]


@dataclass(frozen=True)
class FaceGearGeometry:
    module: float
    teeth: int
    pinion_teeth: int
    pressure_angle_degrees: float = 25.0
    backlash: float = 0.15
    addendum_coefficient: float = 1.0
    dedendum_coefficient: float = 1.25
    min_tip_land: float = 0.2
    min_flank_angle_degrees: float = 8.0

    def __post_init__(self) -> None:
        if self.teeth <= self.pinion_teeth:
            raise ValueError("a face gear needs more teeth than its pinion")

    @property
    def pressure_angle(self) -> float:
        return math.radians(self.pressure_angle_degrees)

    @property
    def pitch_radius(self) -> float:
        return self.module * self.teeth / 2.0

    @property
    def pinion_pitch_radius(self) -> float:
        return self.module * self.pinion_teeth / 2.0

    @property
    def addendum(self) -> float:
        return self.addendum_coefficient * self.module

    @property
    def dedendum(self) -> float:
        return self.dedendum_coefficient * self.module

    @property
    def ratio(self) -> float:
        return self.teeth / self.pinion_teeth

    def local_pressure_angle(self, radius: float) -> float:
        base = self.pitch_radius * math.cos(self.pressure_angle)
        if radius < base:
            raise ValueError(f"no face gear tooth inside r = {base:.3f}")
        return math.acos(base / radius)

    def pitch_line_height(self, radius: float) -> float:
        """Height (toward the pinion) of the local rack's pitch line."""
        return self.pinion_pitch_radius * (1.0 - radius / self.pitch_radius)

    def half_thickness(self, radius: float, height: float) -> float:
        """Half tooth thickness (tangential) at ``radius`` and ``height``."""
        pitch = 2.0 * math.pi * radius / self.teeth
        alpha = self.local_pressure_angle(radius)
        at_pitch_line = pitch / 4.0 - self.backlash / 2.0
        return at_pitch_line - (height - self.pitch_line_height(radius)) * math.tan(
            alpha
        )

    @property
    def inner_radius(self) -> float:
        base = self.pitch_radius * math.cos(self.pressure_angle)
        return base / math.cos(math.radians(self.min_flank_angle_degrees))

    @property
    def outer_radius(self) -> float:
        """Largest radius whose tooth tip land is at least ``min_tip_land``."""
        low, high = self.pitch_radius, 2.0 * self.pitch_radius
        if self.half_thickness(low, self.addendum) * 2 < self.min_tip_land:
            raise ValueError("face gear teeth are pointed at the pitch radius")
        for _ in range(60):
            mid = (low + high) / 2
            if self.half_thickness(mid, self.addendum) * 2 >= self.min_tip_land:
                low = mid
            else:
                high = mid
        return low

    @property
    def face_width(self) -> float:
        return self.outer_radius - self.inner_radius

    def root_gap(self, radius: float) -> float:
        """Space between neighbouring teeth at the root plane."""
        pitch = 2.0 * math.pi * radius / self.teeth
        return pitch - 2.0 * self.half_thickness(radius, -self.dedendum)

    def sections(self, stations: int = 7, root_overlap: float = 0.3) -> List[Section]:
        """Tooth cross-sections (tangential, height) at radial stations.

        The bottom edge dips ``root_overlap`` below the root plane so the
        teeth fuse with the gear body.
        """
        sections: List[Section] = []
        bottom = -self.dedendum - root_overlap
        top = self.addendum
        r0, r1 = self.inner_radius, self.outer_radius
        for i in range(stations):
            r = r0 + (r1 - r0) * i / (stations - 1)
            b = self.half_thickness(r, bottom)
            t = self.half_thickness(r, top)
            sections.append((r, [(-b, bottom), (b, bottom), (t, top), (-t, top)]))
        return sections

    def problems(self) -> List[str]:
        issues: List[str] = []
        try:
            if self.face_width < 3.0 * self.module:
                issues.append("face gear face width is too narrow")
        except ValueError as error:
            return [str(error)]
        if self.root_gap(self.inner_radius) < 2 * self.backlash:
            issues.append("face gear teeth merge at the inner radius")
        return issues


def crown_mesh_phase(
    pinion_phase_degrees: float,
    pinion_teeth: int,
    crown_teeth: int,
    contact_angle_degrees: float = 180.0,
) -> float:
    """Face gear rotation that receives the pinion's teeth.

    Assumes the configuration used by the transaxle: the face gear axis is
    world +Y with teeth facing +Y, the pinion sits on the +Y side with its
    axis along X through the face gear axis, at ``contact_angle_degrees``
    measured in the XZ plane (from +X toward +Z).  The pinion phase is its
    tooth-0 angle in the YZ plane (from +Y toward +Z); 180 deg points the
    tooth at the face gear.  The result is the face gear's tooth-0 angle in
    the XZ plane, normalised to one angular pitch.

    Turning the pinion by +d about +X moves its contact tooth toward -Z,
    which turns the face gear by +d * Np / Nc in the XZ angle convention.
    """
    pitch = 360.0 / crown_teeth
    phase = (
        contact_angle_degrees
        + pitch / 2.0
        + (pinion_teeth / crown_teeth) * (pinion_phase_degrees - 180.0)
    )
    return phase % pitch
