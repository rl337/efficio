"""World layout of a rear transaxle with the engine above the gearbox.

Coordinate system (millimetres): ``x`` forward, ``y`` along the axle (left
to right), ``z`` up, ground at ``z = 0``.

Power path:

* The **engine** runs fore-and-aft (crank along ``x``) above the gearbox and
  extends backward, so adding cylinders makes the car longer, not wider.
* **Right-angle drive:** the crank pinion (spur, axis ``x``) meshes the
  **crown gear** on the gearbox input shaft (axis ``y``).
* **Gearbox:** the input shaft's spur pinion drives an **idler gear**, which
  drives the **ring gear** on the differential carrier.  The shafts are
  stacked so the engine block clears the ring and idler below it.
* **Differential** -> **half-shafts** -> **wheels**.

The engine and differential keep their own geometry
(:class:`EngineGeometry`, :class:`SpurDifferentialGeometry`).  The engine is
modelled in its local frame and placed by :meth:`DrivetrainLayout.engine_frame`.
"""

import math
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from efficio.objects.powertrain.bearings import StandardBearing
from efficio.objects.powertrain.differential.geometry import (
    PlanetPose,
    SpurDifferentialGeometry,
)
from efficio.objects.powertrain.dowels import StandardDowel
from efficio.objects.powertrain.engine.geometry import EngineGeometry
from efficio.objects.powertrain.fits import (
    M3_CLEARANCE_RADIUS_MM,
    RUNNING_CLEARANCE_MM,
    cross_pin_offset,
)
from efficio.objects.powertrain.gearbox.features import PlateHole, PlateSeat
from efficio.objects.powertrain.gears.face import FaceGearGeometry, crown_mesh_phase
from efficio.objects.powertrain.gears.involute import (
    InvoluteGearGeometry,
    centre_distance,
    mesh_phase,
)
from efficio.objects.powertrain.planar import Point, Span, distance


class PlateSide(Enum):
    LEFT = "left"
    RIGHT = "right"


class AxleStock(Enum):
    """What the half-shafts are made of and how they are driven."""

    STEEL_D_FLAT = "steel_d_flat"  # ground steel rod, D-flat drive, tapped end
    WOOD_DOWEL = "wood_dowel"  # hardwood dowel, cross-pin drive, wood screw end


# Bearings and carrier hubs that suit each dowel size (dowel runs in the
# carrier hub bore; the hub runs in the gearbox plate bearing).
DOWEL_AXLE_BEARINGS: Dict[StandardDowel, Tuple[StandardBearing, StandardBearing]] = {
    StandardDowel.D_1_4: (StandardBearing.R4, StandardBearing.B6801),
    StandardDowel.D_5_16: (StandardBearing.B608, StandardBearing.B6801),
    StandardDowel.D_3_8: (StandardBearing.R6, StandardBearing.B6802),
}

Box2 = Tuple[float, float, float, float]  # xmin, zmin, xmax, zmax


@dataclass(frozen=True)
class EngineFrame:
    """Engine-local -> world: rotate about +Z, then translate.

    Engine-local +Y (the crank, front face at y = 0) maps to world -X, so
    the engine extends backward from ``origin[0]``.
    """

    origin: Tuple[float, float, float]
    rotate_z: float = 90.0

    def to_world(self, local: Tuple[float, float, float]) -> Tuple[float, float, float]:
        angle = math.radians(self.rotate_z)
        x, y, z = local
        wx = x * math.cos(angle) - y * math.sin(angle)
        wy = x * math.sin(angle) + y * math.cos(angle)
        return (wx + self.origin[0], wy + self.origin[1], z + self.origin[2])


def _box_distance(point: Point, box: Box2) -> float:
    dx = max(box[0] - point[0], 0.0, point[0] - box[2])
    dz = max(box[1] - point[1], 0.0, point[1] - box[3])
    return math.hypot(dx, dz)


@dataclass
class DrivetrainLayout:
    # Gear train: crank pinion -> crown | input pinion -> idler -> ring.
    module: float = 1.5
    pressure_angle: float = 25.0
    backlash: float = 0.15
    crank_pinion_teeth: int = 12
    crown_teeth: int = 48
    crown_addendum: float = 0.8
    crown_body_thickness: float = 5.0
    input_pinion_teeth: int = 16
    idler_teeth: int = 24
    stage_gear_width: float = 10.0
    input_shaft_diameter: float = 5.0
    idler_shaft_diameter: float = 5.0
    idler_forward: bool = True
    # Subsystems.
    engine: EngineGeometry = field(default_factory=EngineGeometry)
    differential: SpurDifferentialGeometry = field(
        default_factory=SpurDifferentialGeometry
    )
    # Gearbox frame.
    plate_thickness: float = 8.0
    standoff_radius: float = 3.5
    engine_mount_gap: float = 3.0
    engine_clearance: float = 2.0
    carrier_bearing: StandardBearing = StandardBearing.B6800
    input_bearing: StandardBearing = StandardBearing.B625
    idler_bearing: StandardBearing = StandardBearing.B625
    # Flywheel.
    flywheel_diameter: float = 50.0
    flywheel_thickness: float = 8.0
    flywheel_holes: int = 4
    # Wheels and axles.
    wheel_diameter: float = 110.0
    rim_diameter: float = 80.0
    wheel_width: float = 30.0
    min_track_width: float = 240.0
    rim_spokes: int = 5
    tire_tread_blocks: int = 24
    hex_across_flats: float = 12.0
    hex_adapter_length: float = 8.0
    axle_bearing: StandardBearing = StandardBearing.B625
    pillow_block_thickness: float = 10.0
    pillow_centre_height: float = 15.0
    wheel_clearance: float = 5.0
    rim_spoke_thickness: float = 6.0
    axle_stock: AxleStock = AxleStock.STEEL_D_FLAT
    axle_dowel: StandardDowel = StandardDowel.D_1_4

    @classmethod
    def with_dowel_axles(
        cls,
        dowel: StandardDowel = StandardDowel.D_1_4,
        cross_pin_diameter: float = 2.0,
        cross_pin_length: float = 9.0,
        differential: Optional[SpurDifferentialGeometry] = None,
        **overrides: Any,
    ) -> "DrivetrainLayout":
        """Layout whose half-shafts are hardwood dowels.

        The sun gears and wheel hex adapters are bored for the dowel and
        driven by a cross pin; the carrier hub and bearings are resized so the
        dowel passes through.
        """
        if dowel not in DOWEL_AXLE_BEARINGS:
            raise ValueError(f"no bearing pairing for a {dowel.spec.nominal} in dowel")
        axle_bearing, carrier_bearing = DOWEL_AXLE_BEARINGS[dowel]
        base = differential or SpurDifferentialGeometry()
        diff = replace(
            base,
            axle_diameter=dowel.spec.diameter,
            hub_diameter=carrier_bearing.spec.bore,
            axle_cross_pin_diameter=cross_pin_diameter,
            axle_cross_pin_length=cross_pin_length,
        )
        options: Dict[str, Any] = {
            "axle_stock": AxleStock.WOOD_DOWEL,
            "axle_dowel": dowel,
            "differential": diff,
            "axle_bearing": axle_bearing,
            "carrier_bearing": carrier_bearing,
        }
        options.update(overrides)
        return cls(**options)

    # ------------------------------------------------------------------ gears
    def gear(self, teeth: int) -> InvoluteGearGeometry:
        return InvoluteGearGeometry(
            module=self.module,
            teeth=teeth,
            pressure_angle_degrees=self.pressure_angle,
            backlash=self.backlash,
        )

    @property
    def crown(self) -> FaceGearGeometry:
        return FaceGearGeometry(
            module=self.module,
            teeth=self.crown_teeth,
            pinion_teeth=self.crank_pinion_teeth,
            pressure_angle_degrees=self.pressure_angle,
            backlash=self.backlash,
            addendum_coefficient=self.crown_addendum,
        )

    @property
    def crown_radius(self) -> float:
        """Outer radius of the crown gear body (teeth stop just inside)."""
        return self.crown.outer_radius + 0.5

    @property
    def reduction_ratio(self) -> float:
        return (self.crown_teeth / self.crank_pinion_teeth) * (
            self.differential.ring_teeth / self.input_pinion_teeth
        )

    @property
    def dowel_axles(self) -> bool:
        return self.axle_stock is AxleStock.WOOD_DOWEL

    @property
    def axle_diameter(self) -> float:
        if self.dowel_axles:
            return self.axle_dowel.spec.diameter
        return self.differential.axle_diameter

    @property
    def cross_pin_diameter(self) -> float:
        return self.differential.axle_cross_pin_diameter

    @property
    def cross_pin_length(self) -> float:
        return self.differential.axle_cross_pin_length

    # ------------------------------------------------------ side-view (x, z)
    @property
    def axle_height(self) -> float:
        return self.wheel_diameter / 2.0

    @property
    def axle_centre(self) -> Point:
        return (0.0, self.axle_height)

    @property
    def ring_tip_radius(self) -> float:
        return self.differential.ring_tip_radius

    @property
    def crank_height(self) -> float:
        """Crank axis height: the block bottom just clears the ring gear."""
        return (
            self.axle_height
            + self.ring_tip_radius
            + self.engine_clearance
            + self.engine.block_half_width
        )

    @property
    def input_centre(self) -> Point:
        """Gearbox input shaft (carries the crown gear), level with the crank."""
        if abs(self.differential.module - self.module) > 1e-9:
            raise ValueError("idler and ring gear need the same module")
        rise = self.crank_height - self.axle_height
        reach = self.ring_tip_radius + self.crown_radius + 2.0
        run = math.sqrt(max(reach**2 - rise**2, 0.0))
        return (run, self.crank_height)

    @property
    def input_to_idler(self) -> float:
        return centre_distance(self.module, self.input_pinion_teeth, self.idler_teeth)

    @property
    def idler_to_ring(self) -> float:
        return centre_distance(
            self.module, self.idler_teeth, self.differential.ring_teeth
        )

    @property
    def idler_centre(self) -> Point:
        """Where the idler meshes both the input pinion and the ring gear."""
        a, n = self.axle_centre, self.input_centre
        d = distance(a, n)
        r1, r2 = self.idler_to_ring, self.input_to_idler
        if not abs(r1 - r2) < d < r1 + r2:
            raise ValueError("idler cannot reach both the input pinion and ring")
        along = (r1**2 - r2**2 + d**2) / (2 * d)
        across = math.sqrt(r1**2 - along**2)
        ux, uz = (n[0] - a[0]) / d, (n[1] - a[1]) / d
        # Perpendicular pointing forward-down (or backward-up).
        sign = 1.0 if self.idler_forward else -1.0
        px, pz = uz * sign, -ux * sign
        return (a[0] + along * ux + across * px, a[1] + along * uz + across * pz)

    @property
    def engine_front(self) -> float:
        """World x of the engine's front face (just behind the crown gear)."""
        return self.input_centre[0] - self.crown_radius - 2.0

    @property
    def crank_pinion_span(self) -> Span:
        """World x extent of the crank pinion across the crown face."""
        n = self.input_centre[0]
        crown = self.crown
        return Span(n - crown.outer_radius - 1.0, n - crown.inner_radius + 1.0)

    @property
    def crank_pinion_box(self) -> Box2:
        tip = self.gear(self.crank_pinion_teeth).tip_radius
        span = self.crank_pinion_span
        z = self.crank_height
        return (span.start, z - tip, span.end, z + tip)

    @property
    def engine_block_box(self) -> Box2:
        front = self.engine_front
        hw = self.engine.block_half_width
        z = self.crank_height
        top = z + self.engine.deck_height + self.engine.head_thickness
        return (front - self.engine.block_length, z - hw, front, top)

    def rotating_envelopes(self) -> List[Tuple[str, Point, float]]:
        """(name, centre, radius) of every gear between the plates."""
        return [
            ("ring", self.axle_centre, self.ring_tip_radius),
            ("idler", self.idler_centre, self.gear(self.idler_teeth).tip_radius),
            (
                "input pinion",
                self.input_centre,
                self.gear(self.input_pinion_teeth).tip_radius,
            ),
            ("crown", self.input_centre, self.crown_radius),
        ]

    def _standoff_clear(self, point: Point) -> bool:
        r = self.standoff_radius
        for _, centre, radius in self.rotating_envelopes():
            if distance(point, centre) < radius + r + 1.0:
                return False
        if _box_distance(point, self.engine_block_box) < r + 1.0:
            return False
        if _box_distance(point, self.crank_pinion_box) < r + 1.0:
            return False
        return point[1] - r - 4.5 >= 3.0

    def standoff_centres(self) -> List[Point]:
        """Tie-rod positions hugging the ring, idler and crown.

        For each gear, the first clear spot found sweeping around it from the
        preferred direction.  They never pass through a gear or the engine.
        """
        r = self.standoff_radius
        anchors = [
            (self.axle_centre, self.ring_tip_radius, 180.0),
            (self.axle_centre, self.ring_tip_radius, -50.0),
            (self.idler_centre, self.gear(self.idler_teeth).tip_radius, -20.0),
            (self.input_centre, self.crown_radius, 0.0),
        ]
        sweep = [0, 15, -15, 30, -30, 45, -45, 60, -60, 75, -75, 90, -90]
        centres: List[Point] = []
        for centre, radius, preferred in anchors:
            reach = radius + r + 2.5
            for offset in sweep:
                angle = math.radians(preferred + offset)
                point = (
                    centre[0] + reach * math.cos(angle),
                    centre[1] + reach * math.sin(angle),
                )
                if self._standoff_clear(point) and all(
                    distance(point, c) > 4 * r for c in centres
                ):
                    centres.append(point)
                    break
            else:
                raise ValueError(f"no clear standoff position near {centre}")
        return centres

    def engine_mount_centres(self) -> List[Point]:
        """World (x, z) of the engine mounts (one each side of the block)."""
        frame = self.engine_frame()
        return [
            (frame.to_world((0.0, y, z))[0], frame.to_world((0.0, y, z))[2])
            for y, z in self.engine.side_mount_positions()
        ]

    # ------------------------------------------------------------ axial stack
    @property
    def plate_left(self) -> Span:
        return Span(-self.plate_thickness, 0.0)

    @property
    def carrier_offset(self) -> float:
        """World y of the differential's carrier-local origin."""
        return self.plate_left.end + 1.0

    @property
    def drum(self) -> Span:
        return Span(0.0, self.differential.drum_width).shifted(self.carrier_offset)

    @property
    def sun_a(self) -> Span:
        return self.differential.sun_a.shifted(self.carrier_offset)

    @property
    def sun_b(self) -> Span:
        return self.differential.sun_b.shifted(self.carrier_offset)

    @property
    def crank_y(self) -> float:
        """Engine centreline: a mount gap inside the left plate."""
        return (
            self.plate_left.end + self.engine_mount_gap + self.engine.block_half_width
        )

    @property
    def engine_block_span(self) -> Span:
        hw = self.engine.block_half_width
        return Span(self.crank_y - hw, self.crank_y + hw)

    @property
    def crown_span(self) -> Span:
        """Crown gear body + teeth; its pitch plane is one pinion pitch radius
        to the left of the crank axis, teeth facing +y."""
        crown = self.crown
        pitch_plane = self.crank_y - crown.pinion_pitch_radius
        start = pitch_plane - crown.dedendum - self.crown_body_thickness
        return Span(start, pitch_plane + crown.addendum)

    @property
    def stage_plane(self) -> Span:
        """Plane of the input pinion and idler (must overlap the ring)."""
        start = self.crown_span.end + 1.5
        return Span(start, start + self.stage_gear_width)

    @property
    def plate_right(self) -> Span:
        start = max(
            self.engine_block_span.end + self.engine_mount_gap,
            self.drum.end + 1.0,
            self.stage_plane.end + 1.0,
        )
        return Span(start, start + self.plate_thickness)

    @property
    def plate_gap(self) -> Span:
        return Span(self.plate_left.end, self.plate_right.start)

    @property
    def carrier_left_hub(self) -> Span:
        return Span(self.plate_left.start, self.drum.start)

    @property
    def carrier_right_hub(self) -> Span:
        return Span(self.drum.end, self.plate_right.end)

    @property
    def through_shaft(self) -> Span:
        """Input and idler shafts run plate face to plate face."""
        return Span(self.plate_left.start, self.plate_right.end)

    def engine_mount_spans(self) -> List[Span]:
        block = self.engine_block_span
        return [
            Span(self.plate_left.end, block.start),
            Span(block.end, self.plate_right.start),
        ]

    # ----------------------------------------------------------------- engine
    def engine_frame(self) -> EngineFrame:
        return EngineFrame((self.engine_front, self.crank_y, self.crank_height))

    @property
    def crank_stub_local(self) -> Span:
        """Output stub in engine-local y: from the pinion's front end to the
        first throw (negative y is ahead of the block)."""
        ahead = self.crank_pinion_span.end - self.engine_front
        return Span(-ahead, self.engine.output_journal_end)

    @property
    def flywheel_local(self) -> Span:
        start = self.engine.block_length + 2.0
        return Span(start, start + self.flywheel_thickness)

    @property
    def flywheel_stub_local(self) -> Span:
        return Span(self.engine.flywheel_journal_start, self.flywheel_local.end)

    # --------------------------------------------------------- wheels / axles
    @property
    def vehicle_centreline(self) -> float:
        return self.drum.centre

    @property
    def right_wheel(self) -> Span:
        by_track = (
            self.vehicle_centreline + self.min_track_width / 2 - self.wheel_width / 2
        )
        by_parts = (
            self.carrier_right_hub.end
            + 1.0
            + self.pillow_block_thickness
            + self.wheel_clearance
        )
        inner = max(by_track, by_parts)
        return Span(inner, inner + self.wheel_width)

    @property
    def left_wheel(self) -> Span:
        c = self.vehicle_centreline
        return Span(2 * c - self.right_wheel.end, 2 * c - self.right_wheel.start)

    @property
    def track_width(self) -> float:
        return self.right_wheel.centre - self.left_wheel.centre

    @property
    def rim_hub_length(self) -> float:
        return self.hex_adapter_length + self.rim_spoke_thickness

    @property
    def axle_wheel_engagement(self) -> float:
        """How far the axle runs into the wheel from its inboard face.

        Steel axles stop at the hex adapter (tapped end, screw through hub);
        dowels run through the hub so a wood screw can go into end grain.
        """
        return self.rim_hub_length if self.dowel_axles else self.hex_adapter_length

    @property
    def rim_axle_bore(self) -> float:
        if self.dowel_axles:
            return self.axle_diameter + 2 * RUNNING_CLEARANCE_MM
        return 2 * M3_CLEARANCE_RADIUS_MM

    @property
    def left_half_shaft(self) -> Span:
        return Span(
            self.left_wheel.end - self.axle_wheel_engagement,
            self.carrier_offset + self.differential.left_axle_end,
        )

    @property
    def right_half_shaft(self) -> Span:
        return Span(
            self.carrier_offset + self.differential.right_axle_end,
            self.right_wheel.start + self.axle_wheel_engagement,
        )

    def axle_cross_pins(self) -> Dict[str, float]:
        """World y of each cross pin, keyed by position (pinned axles only)."""
        if not self.differential.pinned_axles:
            return {}
        offset = cross_pin_offset(self.cross_pin_diameter)
        return {
            "sun_left": self.carrier_offset + self.differential.sun_a_pin,
            "sun_right": self.carrier_offset + self.differential.sun_b_pin,
            "wheel_left": self.left_wheel.end - self.hex_adapter_length + offset,
            "wheel_right": self.right_wheel.start + self.hex_adapter_length - offset,
        }

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
        """Rotation (degrees) of every gear for a given crank angle.

        ``crank`` angles are in the YZ plane (from +Y toward +Z); the others
        are in the XZ plane (from +X toward +Z).
        """
        pitch = 360.0 / self.crank_pinion_teeth
        crown = crown_mesh_phase(
            crank_angle % pitch, self.crank_pinion_teeth, self.crown_teeth
        )
        idler = mesh_phase(
            self.input_centre,
            crown,
            self.input_pinion_teeth,
            self.idler_centre,
            self.idler_teeth,
        )
        carrier = mesh_phase(
            self.idler_centre,
            idler,
            self.idler_teeth,
            self.axle_centre,
            self.differential.ring_teeth,
        )
        return {
            "crank": crank_angle,
            "crown": crown,
            "idler": idler,
            "carrier": carrier,
            "sun_a": 0.0,
        }

    def planet_poses(
        self, carrier_phase: float, sun_a_phase: float
    ) -> List[PlanetPose]:
        """Planet poses with world axial spans."""
        poses = self.differential.planet_poses(
            self.axle_centre, carrier_phase, sun_a_phase
        )
        return [
            PlanetPose(
                p.name,
                p.centre,
                p.phase,
                p.span.shifted(self.carrier_offset),
                p.carrier_angle,
            )
            for p in poses
        ]

    def sun_b_phase(self, poses: List[PlanetPose], pair: int = 0) -> float:
        return self.differential.sun_b_phase(self.axle_centre, poses, pair)

    # ---------------------------------------------------------- plate design
    def plate_features(
        self, side: PlateSide
    ) -> Tuple[List[PlateSeat], List[PlateHole]]:
        """Seats and holes in plate coordinates for one gearbox side plate.

        Plate x/y map onto world x/z; the right plate faces +y when placed, so
        its features are mirrored in z.
        """

        def local(point: Point) -> Point:
            return (point[0], -point[1]) if side is PlateSide.RIGHT else point

        seats = [
            PlateSeat(
                local(self.axle_centre),
                self.carrier_bearing.spec,
                self.differential.hub_diameter / 2.0 + 0.5,
            ),
            PlateSeat(
                local(self.idler_centre),
                self.idler_bearing.spec,
                self.idler_shaft_diameter / 2.0 + 0.5,
            ),
            PlateSeat(
                local(self.input_centre),
                self.input_bearing.spec,
                self.input_shaft_diameter / 2.0 + 0.5,
            ),
        ]
        holes = [
            PlateHole(local(s), M3_CLEARANCE_RADIUS_MM) for s in self.standoff_centres()
        ]
        holes += [
            PlateHole(local(m), M3_CLEARANCE_RADIUS_MM, boss_margin=6.0)
            for m in self.engine_mount_centres()
        ]
        return seats, holes

    # ------------------------------------------------------------- validation
    def problems(self) -> List[str]:
        """Human-readable violations; empty when the layout is sound."""
        issues = list(self.engine.problems()) + list(self.differential.problems())
        issues += self.crown.problems()
        try:
            self.idler_centre
        except ValueError as error:
            return issues + [str(error)]
        issues += self._gear_train_problems()
        issues += self._packaging_problems()
        issues += self._axle_problems()
        issues.extend(self._axle_stock_problems())
        return issues

    def _gear_train_problems(self) -> List[str]:
        issues: List[str] = []
        journal = self.engine.crank_journal_diameter
        pinion = self.gear(self.crank_pinion_teeth)
        if pinion.root_radius < journal / 2.0 + 1.5:
            issues.append("crank pinion too small for the crank journal")
        input_pinion = self.gear(self.input_pinion_teeth)
        if input_pinion.root_radius < self.input_shaft_diameter / 2.0 + 1.5:
            issues.append("input pinion too small for its shaft")
        if distance(self.input_centre, self.axle_centre) < (
            self.ring_tip_radius + self.crown_radius + 1.0
        ):
            issues.append("crown gear hits the differential ring gear")
        if (
            self.stage_plane.end > self.drum.end
            or self.stage_plane.start < self.drum.start
        ):
            issues.append("idler plane does not overlap the ring gear")
        idler = self.gear(self.idler_teeth).tip_radius
        if _box_distance(self.idler_centre, self.crank_pinion_box) < idler + 1.0:
            issues.append("idler gear hits the crank pinion")
        tip = input_pinion.tip_radius
        if self.input_centre[0] - tip - self.crank_pinion_span.end < 1.0:
            issues.append("input pinion hits the crank pinion")
        if self.crank_pinion_span.start < self.engine_front + 0.5:
            issues.append("crank pinion overlaps the engine block")
        return issues

    def _packaging_problems(self) -> List[str]:
        issues: List[str] = []
        block = self.engine_block_box
        for name, centre, radius in self.rotating_envelopes():
            if name == "crown":
                gap = self.engine_front - (centre[0] - radius)
                if gap > -1.0:
                    issues.append("crown gear hits the engine block")
                continue
            if _box_distance(centre, block) < radius + 1.0:
                issues.append(f"{name} gear hits the engine block")
        try:
            standoffs = self.standoff_centres()
        except ValueError as error:
            return issues + [str(error)]
        for s in standoffs:
            for name, centre, radius in self.rotating_envelopes():
                if distance(s, centre) < radius + self.standoff_radius + 1.0:
                    issues.append(f"standoff at {s} intersects the {name}")
            if _box_distance(s, block) < self.standoff_radius + 1.0:
                issues.append(f"standoff at {s} intersects the engine")
            if _box_distance(s, self.crank_pinion_box) < self.standoff_radius + 1.0:
                issues.append(f"standoff at {s} intersects the crank pinion")
            if s[1] - self.standoff_radius - 4.5 < 3.0:
                issues.append(f"standoff at {s} drags the plates on the ground")
        for span in self.engine_mount_spans():
            if span.length < 1.0:
                issues.append("no room for engine mounts between block and plates")
        if self.crown_span.start < self.plate_left.end + 1.0:
            issues.append("crown gear hits the left gearbox plate")
        if self.axle_height - self.flywheel_diameter / 2.0 < 5.0:
            issues.append("flywheel too close to ground")
        if self.crank_height - self.flywheel_diameter / 2.0 < self.axle_height:
            issues.append("flywheel sits below the axle line")
        return issues

    def _axle_problems(self) -> List[str]:
        issues: List[str] = []
        if self.axle_height - self.ring_tip_radius < 5.0:
            issues.append("ring gear too close to ground")
        if self.right_half_shaft.start - self.left_half_shaft.end < 1.0:
            issues.append("half-shaft ends collide inside the differential")
        if self.left_pillow_block.end > self.plate_left.start - 1.0:
            issues.append("left pillow block collides with gearbox")
        if self.right_pillow_block.start < self.carrier_right_hub.end + 1.0:
            issues.append("right pillow block collides with gearbox")
        if self.rim_diameter >= self.wheel_diameter - 10.0:
            issues.append("tyre too thin")
        if abs(self.carrier_bearing.spec.bore - self.differential.hub_diameter) > 0.01:
            issues.append("carrier hub does not match its bearing bore")
        if self.axle_bearing.spec.bore + 0.3 < self.axle_diameter:
            issues.append("axle bearing bore smaller than the axle")
        if self.axle_bearing.spec.bore - self.axle_diameter > 0.3:
            issues.append("axle bearing bore much larger than the axle")
        return issues

    def _axle_stock_problems(self) -> List[str]:
        issues: List[str] = []
        diff = self.differential
        if not self.dowel_axles:
            if diff.pinned_axles:
                issues.append("steel axles use D-flat drive, not cross pins")
            return issues
        if abs(diff.axle_diameter - self.axle_diameter) > 1e-6:
            issues.append("differential is not bored for the dowel")
        if not diff.pinned_axles:
            issues.append("dowel axles need a cross-pin drive")
        hex_inscribed = self.hex_across_flats / 2
        if self.cross_pin_length / 2 + 0.2 > hex_inscribed - 1.0:
            issues.append("axle cross pin breaks out of the hex adapter")
        if self.axle_diameter / 2 + RUNNING_CLEARANCE_MM > hex_inscribed - 2.0:
            issues.append("hex adapter too small for the dowel")
        engagement = self.hex_adapter_length - cross_pin_offset(self.cross_pin_diameter)
        if engagement < 2 * self.cross_pin_diameter:
            issues.append("hex adapter too short for its cross pin")
        return issues
