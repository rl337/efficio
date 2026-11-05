"""Spur-gear (planet-pair) differential geometry (pure Python).

Carrier-local axial coordinate ``a`` runs along the output axis from the
left outer face of the drum (``a = 0``) to the right outer face.  Inside the
cavity:

    | sun A | mesh zone | sun B |
    | P1 (A + mesh) |
            | P2 (mesh + B) |

Each P1 meshes with sun A and with its partner P2 in the mesh zone; each P2
meshes with sun B.  Planets are identical parts (P2 is P1 turned around).
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from efficio.objects.fasteners.threads import MetricThread
from efficio.objects.powertrain.fits import cross_pin_offset
from efficio.objects.powertrain.gears.involute import (
    InvoluteGearGeometry,
    centre_distance,
    mesh_phase,
)
from efficio.objects.powertrain.planar import Point, Span


@dataclass(frozen=True)
class PlanetPose:
    name: str
    centre: Point
    phase: float
    span: Span
    carrier_angle: float


@dataclass
class SpurDifferentialGeometry:
    module: float = 1.5
    pressure_angle: float = 25.0
    backlash: float = 0.15
    ring_teeth: int = 46
    sun_teeth: int = 12
    planet_teeth: int = 12
    planet_pairs: int = 2
    sun_width: float = 8.0
    mesh_zone: float = 8.0
    end_wall: float = 5.0
    hub_diameter: float = 10.0
    axle_diameter: float = 5.0
    planet_bolt: MetricThread = MetricThread.M3
    # Clearances: end float of gears in the cavity, radial gap to the cavity
    # wall, and gap between the sun hub and the planets' tips.
    axial_clearance: float = 0.5
    radial_clearance: float = 1.0
    hub_clearance: float = 1.5
    ring_wall: float = 2.5
    # Output drive: 0 = D-flat steel axle; > 0 = round axle (e.g. a dowel)
    # driven through a cross pin seated in a slot on the sun's outer face.
    axle_cross_pin_diameter: float = 0.0
    axle_cross_pin_length: float = 9.0

    @property
    def planet_pin_diameter(self) -> float:
        """Planets run on the shank of the planet bolt."""
        return self.planet_bolt.spec.major_diameter

    @property
    def pinned_axles(self) -> bool:
        return self.axle_cross_pin_diameter > 0

    def gear(self, teeth: int) -> InvoluteGearGeometry:
        return InvoluteGearGeometry(
            module=self.module,
            teeth=teeth,
            pressure_angle_degrees=self.pressure_angle,
            backlash=self.backlash,
        )

    # ---------------------------------------------------------------- radial
    @property
    def planet_orbit_radius(self) -> float:
        return centre_distance(self.module, self.sun_teeth, self.planet_teeth)

    @property
    def planet_pair_angle(self) -> float:
        """Angle (degrees) between the two meshing planets of one pair."""
        chord = centre_distance(self.module, self.planet_teeth, self.planet_teeth)
        return math.degrees(2.0 * math.asin(chord / (2.0 * self.planet_orbit_radius)))

    def planet_carrier_angles(self) -> List[Tuple[str, float]]:
        """(role, carrier angle) for every planet; the set is symmetric about 0
        so the two carrier halves are identical parts."""
        half = self.planet_pair_angle / 2.0
        angles: List[Tuple[str, float]] = []
        for pair in range(self.planet_pairs):
            centre = 360.0 * pair / self.planet_pairs
            angles.append((f"P1.{pair}", centre - half))
            angles.append((f"P2.{pair}", centre + half))
        return angles

    @property
    def cavity_radius(self) -> float:
        return (
            self.planet_orbit_radius
            + self.gear(self.planet_teeth).tip_radius
            + self.radial_clearance
        )

    @property
    def sun_hub_radius(self) -> float:
        planet = self.gear(self.planet_teeth)
        return self.planet_orbit_radius - planet.tip_radius - self.hub_clearance

    @property
    def ring_tip_radius(self) -> float:
        return self.gear(self.ring_teeth).tip_radius

    # ----------------------------------------------------------------- axial
    @property
    def cavity_length(self) -> float:
        return 2 * self.sun_width + self.mesh_zone + 2 * self.axial_clearance

    @property
    def drum_width(self) -> float:
        return self.cavity_length + 2 * self.end_wall

    @property
    def cavity(self) -> Span:
        return Span(self.end_wall, self.drum_width - self.end_wall)

    @property
    def sun_a(self) -> Span:
        start = self.cavity.start + self.axial_clearance
        return Span(start, start + self.sun_width)

    @property
    def sun_b(self) -> Span:
        end = self.cavity.end - self.axial_clearance
        return Span(end - self.sun_width, end)

    @property
    def sun_hub_length(self) -> float:
        return (self.mesh_zone - 2 * self.axial_clearance) / 2.0

    @property
    def planet_length(self) -> float:
        # Half a millimetre short of the opposite sun so faces never touch.
        return self.sun_width + self.mesh_zone - self.axial_clearance

    @property
    def p1_span(self) -> Span:
        return Span(self.sun_a.start, self.sun_a.start + self.planet_length)

    @property
    def p2_span(self) -> Span:
        return Span(self.sun_b.end - self.planet_length, self.sun_b.end)

    @property
    def sun_a_pin(self) -> float:
        """Carrier-local axial position of sun A's cross pin (pinned axles)."""
        return self.sun_a.start + cross_pin_offset(self.axle_cross_pin_diameter)

    @property
    def sun_b_pin(self) -> float:
        return self.sun_b.end - cross_pin_offset(self.axle_cross_pin_diameter)

    @property
    def left_axle_end(self) -> float:
        """Inboard end of the left output shaft (inside sun A's hub)."""
        return self.sun_a.end + self.sun_hub_length - self.axial_clearance

    @property
    def right_axle_end(self) -> float:
        return self.sun_b.start - self.sun_hub_length + self.axial_clearance

    # ---------------------------------------------------------------- phases
    def planet_poses(
        self, centre: Point, carrier_phase: float, sun_a_phase: float
    ) -> List[PlanetPose]:
        """Planet centres/phases in the output plane; spans are carrier-local."""
        poses: List[PlanetPose] = []
        p1_phase: Dict[str, PlanetPose] = {}
        orbit = self.planet_orbit_radius
        for role, local in self.planet_carrier_angles():
            angle = math.radians(carrier_phase + local)
            position = (
                centre[0] + orbit * math.cos(angle),
                centre[1] + orbit * math.sin(angle),
            )
            pair = role.split(".")[1]
            if role.startswith("P1"):
                phase = mesh_phase(
                    centre, sun_a_phase, self.sun_teeth, position, self.planet_teeth
                )
                pose = PlanetPose(role, position, phase, self.p1_span, local)
                p1_phase[pair] = pose
            else:
                p1 = p1_phase[pair]
                phase = mesh_phase(
                    p1.centre, p1.phase, self.planet_teeth, position, self.planet_teeth
                )
                pose = PlanetPose(role, position, phase, self.p2_span, local)
            poses.append(pose)
        return poses

    def sun_b_phase(
        self, centre: Point, poses: List[PlanetPose], pair: int = 0
    ) -> float:
        p2 = next(p for p in poses if p.name == f"P2.{pair}")
        return mesh_phase(
            p2.centre, p2.phase, self.planet_teeth, centre, self.sun_teeth
        )

    # ------------------------------------------------------------ validation
    def problems(self) -> List[str]:
        issues: List[str] = []
        ring = self.gear(self.ring_teeth)
        planet = self.gear(self.planet_teeth)
        if ring.root_radius - self.cavity_radius < self.ring_wall:
            issues.append("ring gear wall around carrier cavity is too thin")
        if self.sun_hub_radius < self.axle_diameter / 2.0 + 1.0:
            issues.append("sun hub too thin around half-shaft")
        if self.hub_diameter / 2.0 < self.axle_diameter / 2.0 + 1.5:
            issues.append("carrier hub too thin around half-shaft")
        if self.pinned_axles:
            sun_root = self.gear(self.sun_teeth).root_radius
            if self.axle_cross_pin_length / 2 + 0.2 > sun_root - 1.0:
                issues.append("axle cross pin too long for the sun gear")
            if self.axle_cross_pin_length <= self.axle_diameter + 1.0:
                issues.append("axle cross pin too short to engage the sun slot")
            if self.axle_cross_pin_diameter > self.axle_diameter / 2.5:
                issues.append("axle cross pin too thick for the axle")
        if self.sun_teeth % self.planet_pairs:
            issues.append("sun teeth must divide evenly between planet pairs")
        overlap = self.p1_span.end - self.p2_span.start
        if overlap < 0.75 * self.mesh_zone:
            issues.append("planets barely overlap in the mesh zone")
        orbit = self.planet_orbit_radius
        angles = [a for _, a in self.planet_carrier_angles()]
        for i, a in enumerate(angles):
            for j in range(i + 1, len(angles)):
                if i // 2 == j // 2:
                    continue
                gap = abs(a - angles[j]) % 360.0
                gap = min(gap, 360.0 - gap)
                chord = 2 * orbit * math.sin(math.radians(gap) / 2)
                if chord < 2 * planet.tip_radius + 1.0:
                    issues.append(f"planets {i} and {j} collide")
        return issues
