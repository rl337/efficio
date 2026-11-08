"""Inline piston engine geometry and kinematics (pure Python).

Engine-local frame: the crank axis is the +Y axis through the origin, from the
flange face at ``y = 0`` to the far end of the block; cylinders point +Z.
Every bolt pattern and clearance is derived from the primary dimensions so a
different bore, stroke or cylinder count stays self-consistent.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple

from efficio.objects.fasteners.threads import MetricThread
from efficio.objects.planar import Point, Span, circle_points, convex_hull, densify
from efficio.objects.powertrain.bearings import BEARING_608, BallBearing


@dataclass(frozen=True)
class EnginePose:
    """Engine-local positions (relative to the crank axis) at a crank angle."""

    crank_angle: float
    throw_angles: List[float]
    crankpin_centres: List[Point]
    wrist_pin_heights: List[float]
    rod_angles: List[float]


@dataclass
class EngineGeometry:
    cylinders: int = 4
    bore: float = 22.0
    stroke: float = 20.0
    rod_length: float = 40.0
    cylinder_spacing: float = 30.0
    piston_height: float = 20.0
    piston_compression_height: float = 8.0
    piston_clearance: float = 0.15
    web_thickness: float = 5.0
    rod_thickness: float = 4.0
    rod_side_clearance: float = 0.5
    crank_journal_diameter: float = 8.0
    crankpin_diameter: float = 5.0
    wrist_pin_diameter: float = 3.0
    end_wall: float = 8.0
    block_wall: float = 3.0
    head_thickness: float = 8.0
    deck_clearance: float = 0.5
    main_bearing: BallBearing = field(default=BEARING_608)
    # How the block is held: bolts into the front face (bolted to a plate)
    # and/or engine mounts bolted into the side walls.
    front_flange: bool = False
    side_mounts: bool = True
    side_mount_depth: float = 8.0
    fastener: MetricThread = MetricThread.M3
    # Part proportions (walls and bosses around holes).
    web_counterweight_margin: float = 8.0  # journal boss beyond the journal
    web_pin_wall: float = 3.0
    rod_big_end_wall: float = 3.0
    rod_small_end_wall: float = 2.0
    wrist_pin_inset: float = 1.0  # each end, inside the piston skirt
    tunnel_clearance: float = 2.5  # crank sweep to crankcase wall
    relief_height_margin: float = 4.0  # relief pocket above the tunnel
    piston_wall: float = 2.0
    piston_crown: float = 4.0
    piston_boss_half_size: float = 4.0
    ring_groove_from_crown: float = 2.0
    ring_groove_width: float = 1.0
    ring_groove_depth: float = 0.7
    head_recess_depth: float = 1.5
    # Bolt patterns and hole depths.
    head_bolt_offset: float = 3.0  # outside the bore, across the block
    head_bolt_pitch_inset: float = 1.0  # along the block, inside the bore radius
    head_bolt_depth: float = 15.0
    split_bolt_inset: float = 4.0  # from the block side
    split_bolt_tap_depth: float = 15.0
    flange_bolt_offset: float = 1.0  # outside the bore
    flange_bolt_low_inset: float = 6.0  # above the block bottom
    flange_bolt_high_offset: float = 2.0  # above the crank tunnel
    flange_bolt_depth: float = 10.0
    sweep_clearance: float = 0.5  # rod to bore / relief during the sweep
    journal_hole_clearance: float = 0.5  # crank journal through the end walls
    # Demonstration-only lightening: expose the mechanism, retain guide arcs.
    windowed_block: bool = False
    window_width_fraction: float = 0.45  # opening width along Y / bore diameter
    frame_rail: float = 4.0  # bottom, split-face and deck rails
    mount_bridge_height: float = 8.0  # uncut horizontal band around side mounts

    def block_windows(self) -> List[Tuple[float, float, float, float]]:
        """Through-X windows as (y0, y1, z0, z1); never cut bearing end walls.

        Fore/aft bore arcs guide the piston. Continuous split/deck/base rails
        and the side-mount bridge join the remaining webs. This describes CAD
        topology, not a structural rating or a combustion-capable cylinder.
        """
        if not self.windowed_block:
            return []
        spans = [(-self.block_half_width + self.frame_rail, -self.frame_rail)]
        upper = (self.frame_rail, self.deck_height - self.frame_rail)
        if self.side_mounts:
            spans.extend(
                [
                    (upper[0], self.side_mount_height - self.mount_bridge_height / 2),
                    (self.side_mount_height + self.mount_bridge_height / 2, upper[1]),
                ]
            )
        else:
            spans.append(upper)
        half = self.bore * self.window_width_fraction / 2
        return [
            (self.cylinder_y(i) - half, self.cylinder_y(i) + half, z0, z1)
            for i in range(self.cylinders)
            for z0, z1 in spans
        ]

    # ---------------------------------------------------------- crank train
    @property
    def crank_throw(self) -> float:
        return self.stroke / 2.0

    def throw_offsets(self) -> List[float]:
        """Standard four-stroke crank layouts (720/n deg firing interval).

        Even counts are mirror-symmetric for balance: inline-4 is the
        flat-plane 0/180/180/0 crank, inline-6 is 0/120/240/240/120/0.  Odd
        counts space the throws evenly (inline-3: 0/240/120).
        """
        n = self.cylinders
        interval = 720.0 / n
        if n % 2:
            return [(i * interval) % 360.0 for i in range(n)]
        half = [(i * interval) % 360.0 for i in range(n // 2)]
        return half + list(reversed(half))

    def throw_angle(self, cylinder: int, crank_angle: float) -> float:
        return crank_angle + self.throw_offsets()[cylinder]

    @property
    def web_inner_offset(self) -> float:
        return self.rod_thickness / 2.0 + self.rod_side_clearance

    @property
    def web_outer_offset(self) -> float:
        return self.web_inner_offset + self.web_thickness

    @property
    def web_journal_radius(self) -> float:
        """Journal boss doubles as the counterweight."""
        return self.crank_journal_diameter / 2.0 + self.web_counterweight_margin

    @property
    def web_pin_radius(self) -> float:
        return self.crankpin_diameter / 2.0 + self.web_pin_wall

    @property
    def rod_big_end_radius(self) -> float:
        return self.crankpin_diameter / 2.0 + self.rod_big_end_wall

    @property
    def rod_small_end_radius(self) -> float:
        return self.wrist_pin_diameter / 2.0 + self.rod_small_end_wall

    @property
    def piston_boss_gap(self) -> float:
        return self.web_inner_offset

    @property
    def wrist_pin_length(self) -> float:
        return self.bore - 2 * self.wrist_pin_inset

    @property
    def crank_sweep_radius(self) -> float:
        return max(
            self.web_journal_radius,
            self.crank_throw + self.web_pin_radius,
            self.crank_throw + self.rod_big_end_radius,
        )

    # ---------------------------------------------------------------- block
    @property
    def block_length(self) -> float:
        return 2 * self.end_wall + self.cylinders * self.cylinder_spacing

    def cylinder_y(self, index: int) -> float:
        return (
            self.end_wall + self.cylinder_spacing / 2.0 + index * self.cylinder_spacing
        )

    @property
    def crank_tunnel_radius(self) -> float:
        return self.crank_sweep_radius + self.tunnel_clearance

    @property
    def block_half_width(self) -> float:
        return self.crank_tunnel_radius + self.block_wall

    @property
    def deck_height(self) -> float:
        """Crank axis to block deck."""
        return (
            self.crank_throw
            + self.rod_length
            + self.piston_compression_height
            + self.deck_clearance
        )

    @property
    def bore_floor(self) -> float:
        """Height above the crank axis where the cylinder bore starts."""
        return self.crank_throw

    @property
    def crankcase_relief_half_width(self) -> float:
        return self.block_half_width - 2 * self.block_wall

    @property
    def crankcase_relief_height(self) -> float:
        return self.crank_tunnel_radius + self.relief_height_margin

    def head_bolt_positions(self) -> List[Point]:
        """Engine-local (x, y) of head bolts, four around each bore."""
        dx = self.bore / 2.0 + self.head_bolt_offset
        dy = self.bore / 2.0 - self.head_bolt_pitch_inset
        return [
            (sx * dx, self.cylinder_y(i) + sy * dy)
            for i in range(self.cylinders)
            for sy in (-1.0, 1.0)
            for sx in (-1.0, 1.0)
        ]

    def split_bolt_positions(self) -> List[Point]:
        """Engine-local (x, y) of the vertical bolts joining the block halves."""
        x = self.block_half_width - self.split_bolt_inset
        return [
            (sx * x, y)
            for y in (self.end_wall / 2.0, self.block_length - self.end_wall / 2.0)
            for sx in (-1.0, 1.0)
        ]

    def flange_bolt_offsets(self) -> List[Point]:
        """(x, z) relative to the crank axis of bolts into the y = 0 face."""
        x = self.bore / 2.0 + self.flange_bolt_offset
        below = -(self.block_half_width - self.flange_bolt_low_inset)
        above = self.crank_tunnel_radius + self.flange_bolt_high_offset
        return [(-x, below), (x, below), (-x, above), (x, above)]

    @property
    def side_mount_height(self) -> float:
        """Mount bolts go into the solid wall beside the bores, above the
        crank tunnel."""
        return (self.crank_tunnel_radius + self.deck_height) / 2.0

    def side_mount_positions(self) -> List[Point]:
        """Engine-local (y, z) of the tapped mount holes on each side wall."""
        if not self.side_mounts:
            return []
        cylinders = sorted({0, min(1, self.cylinders - 1)})
        return [(self.cylinder_y(i), self.side_mount_height) for i in cylinders]

    def centre_journals(self) -> List[Span]:
        return [
            Span(
                self.cylinder_y(i) + self.web_inner_offset,
                self.cylinder_y(i + 1) - self.web_inner_offset,
            )
            for i in range(self.cylinders - 1)
        ]

    @property
    def output_journal_end(self) -> float:
        """Engine-local y where the output stub ends inside the first throw."""
        return self.cylinder_y(0) - self.web_inner_offset

    @property
    def flywheel_journal_start(self) -> float:
        return self.cylinder_y(self.cylinders - 1) + self.web_inner_offset

    # ----------------------------------------------------------- kinematics
    def pose(self, crank_angle: float) -> EnginePose:
        r = self.crank_throw
        throws: List[float] = []
        pins: List[Point] = []
        wrist: List[float] = []
        rods: List[float] = []
        for i in range(self.cylinders):
            throw = self.throw_angle(i, crank_angle)
            angle = math.radians(throw)
            px, pz = r * math.cos(angle), r * math.sin(angle)
            wz = pz + math.sqrt(self.rod_length**2 - px**2)
            throws.append(throw)
            pins.append((px, pz))
            wrist.append(wz)
            rods.append(math.degrees(math.atan2(wz - pz, -px)))
        return EnginePose(crank_angle, throws, pins, wrist, rods)

    def rod_outline(self, crank_angle: float, cylinder: int = 0) -> List[Point]:
        """Engine-local (x, z) outline of a connecting rod, densely sampled."""
        pose = self.pose(crank_angle)
        pin = pose.crankpin_centres[cylinder]
        wrist = (0.0, pose.wrist_pin_heights[cylinder])
        points = circle_points(pin, self.rod_big_end_radius, 48)
        points += circle_points(wrist, self.rod_small_end_radius, 48)
        return densify(convex_hull(points))

    def rod_clearance_problems(self, step: float = 5.0) -> List[str]:
        """Sweep a rod through one revolution against the bore and relief."""
        angle = 0.0
        while angle < 360.0:
            for x, z in self.rod_outline(angle):
                if z > self.crankcase_relief_height:
                    limit = self.bore / 2.0 - self.sweep_clearance
                elif z > self.crank_tunnel_radius - 3.0:
                    limit = self.crankcase_relief_half_width - self.sweep_clearance
                else:
                    continue
                if abs(x) > limit:
                    return [f"connecting rod hits block at {angle:g} deg"]
            angle += step
        return []

    def problems(self) -> List[str]:
        issues: List[str] = []
        if self.windowed_block:
            if not all(
                math.isfinite(v) and v > 0
                for v in (
                    self.window_width_fraction,
                    self.frame_rail,
                    self.mount_bridge_height,
                )
            ):
                issues.append("window dimensions must be positive and finite")
            elif not 0 < self.window_width_fraction < 1:
                issues.append("windows must retain fore/aft piston guide arcs")
            else:
                half = self.bore * self.window_width_fraction / 2
                bolt_y = self.bore / 2 - self.head_bolt_pitch_inset
                if (
                    half + self.fastener.spec.clearance_radius + self.block_wall
                    > bolt_y
                ):
                    issues.append("windows leave too little material around head bolts")
                if self.side_mounts and self.mount_bridge_height < 2 * (
                    self.fastener.spec.clearance_radius + self.block_wall / 2
                ):
                    issues.append("side mount bridge too thin around bolt holes")
                if any(
                    y0 < self.end_wall
                    or y1 > self.block_length - self.end_wall
                    or z0 >= z1
                    for y0, y1, z0, z1 in self.block_windows()
                ):
                    issues.append(
                        "windows must clear end walls and retain positive height"
                    )
        if self.cylinders < 1:
            issues.append("engine needs at least one cylinder")
        if self.rod_length <= self.crank_throw * 2:
            issues.append("connecting rod too short for the stroke")
        if self.web_outer_offset * 2 > self.cylinder_spacing - 2.0:
            issues.append("crank webs of adjacent cylinders collide")
        if self.cylinder_y(0) - self.web_outer_offset < self.end_wall + 1.0:
            issues.append("first crank web hits the block end wall")
        if self.cylinder_spacing < self.bore + 6.0:
            issues.append("cylinder walls too thin")
        head_bolt_x = self.bore / 2.0 + self.head_bolt_offset
        clearance = self.fastener.spec.clearance_radius
        if self.block_half_width < head_bolt_x + clearance + 2.0:
            issues.append("block too narrow for head bolts")
        if self.main_bearing.seat_radius > self.block_half_width - 2.0:
            issues.append("main bearing does not fit the block end wall")
        if self.main_bearing.width >= self.end_wall:
            issues.append("end wall too thin for the main bearing")
        piston_bottom_at_bdc = (
            -self.crank_throw
            + self.rod_length
            - (self.piston_height - self.piston_compression_height)
        )
        if piston_bottom_at_bdc < self.crank_sweep_radius + 1.0:
            issues.append("piston skirt reaches crank webs at BDC")
        wall_beside_bore = self.block_half_width - self.bore / 2.0
        if self.side_mounts and self.side_mount_depth > wall_beside_bore - 1.0:
            issues.append("engine mount bolts would break into the cylinder bores")
        if self.crankcase_relief_height + self.piston_height > self.deck_height + 4:
            issues.append("bore too short to guide the piston")
        issues.extend(self.rod_clearance_problems())
        return issues
