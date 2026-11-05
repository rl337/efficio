"""Pure-Python layout of a rear transaxle drivetrain.

Coordinate system (millimetres):

* ``x`` points forward, ``y`` to the vehicle's left-to-right axle direction,
  ``z`` up, ground plane at ``z = 0``.
* Every rotating shaft is parallel to ``y`` so the whole power path uses spur
  gears: crankshaft -> crank pinion -> idler gear | idler pinion -> ring gear
  on the differential carrier -> sun gears -> half-shafts -> wheels.

Gear centres are derived from pitch radii so meshing is exact, and every
clearance the solid model relies on is checked here without CadQuery.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from efficio.objects.fits import BEARING_608, BEARING_625, BEARING_6800, BallBearing
from efficio.objects.involute import (
    InvoluteGearGeometry,
    Point,
    centre_distance,
    distance,
    mesh_phase,
)


@dataclass(frozen=True)
class Span:
    """Closed interval along the y axis."""

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


@dataclass(frozen=True)
class PlanetPose:
    name: str
    centre: Point
    phase: float
    span: Span
    carrier_angle: float


@dataclass(frozen=True)
class EnginePose:
    crank_angle: float
    crankpin_centres: List[Point]
    wrist_pin_heights: List[float]
    rod_angles: List[float]


@dataclass
class DrivetrainLayout:
    # Gear train
    module: float = 1.5
    pressure_angle: float = 25.0
    backlash: float = 0.15
    crank_pinion_teeth: int = 12
    idler_gear_teeth: int = 36
    idler_pinion_teeth: int = 12
    ring_teeth: int = 46
    sun_teeth: int = 12
    planet_teeth: int = 12
    planet_pairs: int = 2
    stage_gear_width: float = 10.0
    sun_width: float = 8.0
    planet_mesh_zone: float = 8.0
    # Structure
    plate_thickness: float = 8.0
    carrier_end_wall: float = 5.0
    carrier_hub_diameter: float = 10.0
    standoff_radius: float = 3.5
    # Engine
    cylinders: int = 2
    bore: float = 22.0
    stroke: float = 20.0
    rod_length: float = 40.0
    cylinder_spacing: float = 30.0
    piston_height: float = 20.0
    piston_compression_height: float = 8.0
    web_thickness: float = 5.0
    rod_thickness: float = 4.0
    crank_journal_diameter: float = 8.0
    crankpin_diameter: float = 5.0
    wrist_pin_diameter: float = 3.0
    engine_end_wall: float = 8.0
    flywheel_diameter: float = 50.0
    flywheel_thickness: float = 8.0
    head_thickness: float = 8.0
    # Wheels and axles
    wheel_diameter: float = 110.0
    rim_diameter: float = 80.0
    wheel_width: float = 30.0
    axle_diameter: float = 5.0
    idler_shaft_diameter: float = 5.0
    hex_across_flats: float = 12.0
    hex_adapter_length: float = 8.0
    pillow_block_thickness: float = 10.0
    wheel_clearance: float = 5.0

    carrier_bearing: BallBearing = field(default=BEARING_6800)
    idler_bearing: BallBearing = field(default=BEARING_625)
    crank_bearing: BallBearing = field(default=BEARING_608)
    axle_bearing: BallBearing = field(default=BEARING_625)

    # ------------------------------------------------------------------ gears
    def gear(self, teeth: int) -> InvoluteGearGeometry:
        return InvoluteGearGeometry(
            module=self.module,
            teeth=teeth,
            pressure_angle_degrees=self.pressure_angle,
            backlash=self.backlash,
        )

    @property
    def reduction_ratio(self) -> float:
        return (self.idler_gear_teeth / self.crank_pinion_teeth) * (
            self.ring_teeth / self.idler_pinion_teeth
        )

    # -------------------------------------------------------- planar centres
    @property
    def axle_height(self) -> float:
        return self.wheel_diameter / 2.0

    @property
    def axle_centre(self) -> Point:
        return (0.0, self.axle_height)

    @property
    def idler_centre(self) -> Point:
        return (
            centre_distance(self.module, self.idler_pinion_teeth, self.ring_teeth),
            self.axle_height,
        )

    @property
    def crank_centre(self) -> Point:
        return (
            self.idler_centre[0]
            + centre_distance(
                self.module, self.crank_pinion_teeth, self.idler_gear_teeth
            ),
            self.axle_height,
        )

    @property
    def planet_orbit_radius(self) -> float:
        return centre_distance(self.module, self.sun_teeth, self.planet_teeth)

    @property
    def planet_pair_angle(self) -> float:
        """Angle (degrees) between the two meshing planets of one pair."""
        chord = centre_distance(self.module, self.planet_teeth, self.planet_teeth)
        return math.degrees(2.0 * math.asin(chord / (2.0 * self.planet_orbit_radius)))

    def planet_carrier_angles(self) -> List[Tuple[str, float]]:
        """(role, carrier-local angle) for every planet; symmetric about 0."""
        angles: List[Tuple[str, float]] = []
        half = self.planet_pair_angle / 2.0
        for pair in range(self.planet_pairs):
            centre = 360.0 * pair / self.planet_pairs
            angles.append((f"P1.{pair}", centre - half))
            angles.append((f"P2.{pair}", centre + half))
        return angles

    @property
    def carrier_cavity_radius(self) -> float:
        return self.planet_orbit_radius + self.gear(self.planet_teeth).tip_radius + 1.0

    @property
    def sun_hub_radius(self) -> float:
        inner_planet_reach = (
            self.planet_orbit_radius - self.gear(self.planet_teeth).tip_radius
        )
        return inner_planet_reach - 1.5

    def standoff_centres(self) -> List[Point]:
        ring_tip = self.gear(self.ring_teeth).tip_radius
        idler_tip = self.gear(self.idler_gear_teeth).tip_radius
        pinion_tip = self.gear(self.crank_pinion_teeth).tip_radius
        r = self.standoff_radius
        ax, az = self.axle_centre
        ix, iz = self.idler_centre
        cx, cz = self.crank_centre
        return [
            (ax - (ring_tip + r + 2.5), az),
            (ix, iz - (idler_tip + r + 2.0)),
            (ix, iz + (idler_tip + r + 2.0)),
            (cx + pinion_tip + r + 2.5, cz),
        ]

    def engine_flange_bolts(self) -> List[Point]:
        cx, cz = self.crank_centre
        return [
            (cx - 12.0, cz - 15.0),
            (cx + 12.0, cz - 15.0),
            (cx - 12.0, cz + 20.0),
            (cx + 12.0, cz + 20.0),
        ]

    # ------------------------------------------------------------ axial stack
    @property
    def plate_left(self) -> Span:
        return Span(-self.plate_thickness, 0.0)

    @property
    def carrier_cavity_length(self) -> float:
        return 2 * self.sun_width + self.planet_mesh_zone + 1.0

    @property
    def drum(self) -> Span:
        width = self.carrier_cavity_length + 2 * self.carrier_end_wall
        return Span(1.0, 1.0 + width)

    @property
    def cavity(self) -> Span:
        return Span(
            self.drum.start + self.carrier_end_wall,
            self.drum.end - self.carrier_end_wall,
        )

    @property
    def sun_a(self) -> Span:
        start = self.cavity.start + 0.5
        return Span(start, start + self.sun_width)

    @property
    def sun_b(self) -> Span:
        end = self.cavity.end - 0.5
        return Span(end - self.sun_width, end)

    @property
    def sun_hub_length(self) -> float:
        return (self.planet_mesh_zone - 1.0) / 2.0

    @property
    def planet_length(self) -> float:
        # Half a millimetre short of the opposite sun so the faces never touch.
        return self.sun_width + self.planet_mesh_zone - 0.5

    @property
    def stage_plane(self) -> Span:
        start = self.drum.end + 1.5
        return Span(start, start + self.stage_gear_width)

    @property
    def plate_right(self) -> Span:
        start = self.stage_plane.end + 1.0
        return Span(start, start + self.plate_thickness)

    @property
    def idler_pinion_span(self) -> Span:
        return Span(self.drum.start, self.stage_plane.start)

    @property
    def carrier_left_hub(self) -> Span:
        return Span(self.plate_left.start, self.drum.start)

    @property
    def carrier_right_hub(self) -> Span:
        return Span(self.drum.end, self.plate_right.end)

    @property
    def idler_shaft(self) -> Span:
        return Span(self.plate_left.start, self.plate_right.end)

    # ----------------------------------------------------------------- engine
    @property
    def crank_throw(self) -> float:
        return self.stroke / 2.0

    @property
    def engine_block(self) -> Span:
        start = self.plate_right.end
        length = 2 * self.engine_end_wall + self.cylinders * self.cylinder_spacing
        return Span(start, start + length)

    def cylinder_y(self, index: int) -> float:
        return (
            self.engine_block.start
            + self.engine_end_wall
            + self.cylinder_spacing / 2.0
            + index * self.cylinder_spacing
        )

    @property
    def web_inner_offset(self) -> float:
        return self.rod_thickness / 2.0 + 0.5

    @property
    def web_outer_offset(self) -> float:
        return self.web_inner_offset + self.web_thickness

    @property
    def web_main_radius(self) -> float:
        return 12.0

    @property
    def web_pin_radius(self) -> float:
        return self.crankpin_diameter / 2.0 + 3.0

    @property
    def rod_big_end_radius(self) -> float:
        return self.crankpin_diameter / 2.0 + 3.0

    @property
    def crank_sweep_radius(self) -> float:
        return max(
            self.web_main_radius,
            self.crank_throw + self.web_pin_radius,
            self.crank_throw + self.rod_big_end_radius,
        )

    @property
    def crank_tunnel_radius(self) -> float:
        return self.crank_sweep_radius + 2.5

    @property
    def block_half_width(self) -> float:
        return self.crank_tunnel_radius + 3.0

    @property
    def block_bottom(self) -> float:
        return self.axle_height - self.block_half_width

    @property
    def deck_height(self) -> float:
        """Crank axis to block deck."""
        return self.crank_throw + self.rod_length + self.piston_compression_height + 0.5

    @property
    def crank_stub(self) -> Span:
        seat_floor = self.plate_left.end - self.crank_bearing.width
        return Span(seat_floor, self.cylinder_y(0) - self.web_inner_offset)

    @property
    def flywheel(self) -> Span:
        start = self.engine_block.end + 2.0
        return Span(start, start + self.flywheel_thickness)

    @property
    def flywheel_stub(self) -> Span:
        return Span(
            self.cylinder_y(self.cylinders - 1) + self.web_inner_offset,
            self.flywheel.end,
        )

    def centre_journals(self) -> List[Span]:
        return [
            Span(
                self.cylinder_y(i) + self.web_inner_offset,
                self.cylinder_y(i + 1) - self.web_inner_offset,
            )
            for i in range(self.cylinders - 1)
        ]

    def head_bolt_positions(self) -> List[Point]:
        """(x offset from crank, y) for head bolts."""
        positions: List[Point] = []
        for i in range(self.cylinders):
            y = self.cylinder_y(i)
            for dy in (-10.0, 10.0):
                for dx in (-14.0, 14.0):
                    positions.append((dx, y + dy))
        return positions

    def engine_pose(self, crank_angle: float) -> EnginePose:
        cx, cz = self.crank_centre
        r = self.crank_throw
        pins: List[Point] = []
        wrist: List[float] = []
        rods: List[float] = []
        for i in range(self.cylinders):
            angle = math.radians(crank_angle + 360.0 * i / self.cylinders)
            px, pz = cx + r * math.cos(angle), cz + r * math.sin(angle)
            dx = cx - px
            height = math.sqrt(self.rod_length**2 - dx**2)
            wz = pz + height
            pins.append((px, pz))
            wrist.append(wz)
            rods.append(math.degrees(math.atan2(wz - pz, cx - px)))
        return EnginePose(crank_angle, pins, wrist, rods)

    # --------------------------------------------------------- wheels / axles
    @property
    def vehicle_centreline(self) -> float:
        return self.drum.centre

    @property
    def right_wheel(self) -> Span:
        inner = self.flywheel.end + self.wheel_clearance
        return Span(inner, inner + self.wheel_width)

    @property
    def left_wheel(self) -> Span:
        c = self.vehicle_centreline
        return Span(2 * c - self.right_wheel.end, 2 * c - self.right_wheel.start)

    @property
    def track_width(self) -> float:
        return self.right_wheel.centre - self.left_wheel.centre

    @property
    def left_half_shaft(self) -> Span:
        return Span(
            self.left_wheel.end - self.hex_adapter_length,
            self.sun_a.end + self.sun_hub_length - 0.5,
        )

    @property
    def right_half_shaft(self) -> Span:
        return Span(
            self.sun_b.start - self.sun_hub_length + 0.5,
            self.right_wheel.start + self.hex_adapter_length,
        )

    @property
    def left_pillow_block(self) -> Span:
        end = self.left_wheel.end + self.wheel_clearance + self.pillow_block_thickness
        return Span(end - self.pillow_block_thickness, end)

    @property
    def right_pillow_block(self) -> Span:
        start = (
            self.right_wheel.start - self.wheel_clearance - self.pillow_block_thickness
        )
        return Span(start, start + self.pillow_block_thickness)

    # ------------------------------------------------------------ gear phases
    def gear_phases(self, crank_angle: float) -> Dict[str, float]:
        """Rotation (degrees) of every gear for a given crank angle."""
        crank = crank_angle % (360.0 / self.crank_pinion_teeth)
        idler = mesh_phase(
            self.crank_centre,
            crank,
            self.crank_pinion_teeth,
            self.idler_centre,
            self.idler_gear_teeth,
        )
        # The compound idler is one part, so the pinion section shares the
        # rotation; the pinion teeth must also be centred on +X when built.
        ring = mesh_phase(
            self.idler_centre,
            idler,
            self.idler_pinion_teeth,
            self.axle_centre,
            self.ring_teeth,
        )
        return {
            "crank_pinion": crank_angle,
            "idler": idler,
            "carrier": ring,
            "sun_a": 0.0,
        }

    def planet_poses(
        self, carrier_phase: float, sun_a_phase: float
    ) -> List[PlanetPose]:
        poses: List[PlanetPose] = []
        ax, az = self.axle_centre
        orbit = self.planet_orbit_radius
        p1_span = Span(self.sun_a.start, self.sun_a.start + self.planet_length)
        p2_span = Span(self.sun_b.end - self.planet_length, self.sun_b.end)
        p1_phase: Dict[str, float] = {}
        for role, local in self.planet_carrier_angles():
            angle = math.radians(carrier_phase + local)
            centre = (ax + orbit * math.cos(angle), az + orbit * math.sin(angle))
            pair = role.split(".")[1]
            if role.startswith("P1"):
                phase = mesh_phase(
                    self.axle_centre,
                    sun_a_phase,
                    self.sun_teeth,
                    centre,
                    self.planet_teeth,
                )
                p1_phase[pair] = phase
                poses.append(PlanetPose(role, centre, phase, p1_span, local))
            else:
                p1 = next(p for p in poses if p.name == f"P1.{pair}")
                phase = mesh_phase(
                    p1.centre,
                    p1_phase[pair],
                    self.planet_teeth,
                    centre,
                    self.planet_teeth,
                )
                poses.append(PlanetPose(role, centre, phase, p2_span, local))
        return poses

    def sun_b_phase(self, poses: List[PlanetPose], pair: int = 0) -> float:
        p2 = next(p for p in poses if p.name == f"P2.{pair}")
        return mesh_phase(
            p2.centre, p2.phase, self.planet_teeth, self.axle_centre, self.sun_teeth
        )

    # ------------------------------------------------------------- validation
    def problems(self) -> List[str]:
        """Return human-readable violations; empty when the layout is sound."""
        issues: List[str] = []
        ring = self.gear(self.ring_teeth)
        planet = self.gear(self.planet_teeth)
        idler = self.gear(self.idler_gear_teeth)
        pinion = self.gear(self.crank_pinion_teeth)
        idler_pinion = self.gear(self.idler_pinion_teeth)

        if ring.root_radius - self.carrier_cavity_radius < 2.5:
            issues.append("ring gear wall around carrier cavity is too thin")
        if self.sun_hub_radius < self.axle_diameter / 2.0 + 1.0:
            issues.append("sun hub too thin around half-shaft")

        # Planets of neighbouring pairs must not touch in the mesh zone.
        orbit = self.planet_orbit_radius
        locals_ = [a for _, a in self.planet_carrier_angles()]
        for i, a in enumerate(locals_):
            for j, b in enumerate(locals_):
                if j <= i or (i // 2 == j // 2):
                    continue
                gap = abs(a - b) % 360.0
                gap = min(gap, 360.0 - gap)
                chord = 2 * orbit * math.sin(math.radians(gap) / 2)
                if chord < 2 * planet.tip_radius + 1.0:
                    issues.append(f"planets {i} and {j} collide")

        # Big idler gear must clear the carrier hub in the stage plane.
        hub_clear = (
            self.idler_centre[0] - idler.tip_radius - self.carrier_hub_diameter / 2
        )
        if hub_clear < 1.0:
            issues.append("idler gear hits differential carrier hub")
        # Idler pinion must clear the crank stub in the ring plane.
        stub_clear = (
            self.crank_centre[0]
            - self.idler_centre[0]
            - idler_pinion.tip_radius
            - self.crank_journal_diameter / 2
        )
        if stub_clear < 1.0:
            issues.append("idler pinion hits crank stub")
        ring_to_crank = (
            self.crank_centre[0] - ring.tip_radius - self.crank_journal_diameter / 2
        )
        if ring_to_crank < 1.0:
            issues.append("ring gear hits crank stub")

        envelopes = [
            (self.axle_centre, ring.tip_radius),
            (self.idler_centre, idler.tip_radius),
            (self.crank_centre, pinion.tip_radius),
        ]
        for s in self.standoff_centres():
            for centre, radius in envelopes:
                if distance(s, centre) < radius + self.standoff_radius + 1.0:
                    issues.append(f"standoff at {s} intersects gear at {centre}")

        if self.web_outer_offset * 2 > self.cylinder_spacing - 2.0:
            issues.append("crank webs of adjacent cylinders collide")
        if self.cylinder_spacing < self.bore + 6.0:
            issues.append("cylinder walls too thin")
        if self.block_half_width < 14.0 + 1.7 + 2.0:
            issues.append("block too narrow for head bolts")
        piston_bottom_at_bdc = (
            -self.crank_throw
            + self.rod_length
            - (self.piston_height - self.piston_compression_height)
        )
        if piston_bottom_at_bdc < self.crank_sweep_radius + 1.0:
            issues.append("piston skirt reaches crank webs at BDC")
        rod_angle = math.asin(self.crank_throw / self.rod_length)
        skirt_reach = (self.piston_height - self.piston_compression_height) * math.sin(
            rod_angle
        ) + self.rod_thickness
        if skirt_reach > self.bore / 2.0 - 2.0 - 0.3:
            issues.append("connecting rod hits piston skirt")
        if self.block_bottom < 5.0:
            issues.append("engine block too close to ground")
        if self.crank_centre[1] - self.flywheel_diameter / 2.0 < 5.0:
            issues.append("flywheel too close to ground")
        if self.right_half_shaft.start - self.left_half_shaft.end < 1.0:
            issues.append("half-shaft ends collide inside the differential")
        if self.left_pillow_block.end > self.plate_left.start - 1.0:
            issues.append("left pillow block collides with gearbox")
        if self.right_pillow_block.start < self.carrier_right_hub.end + 1.0:
            issues.append("right pillow block collides with gearbox")
        return issues
