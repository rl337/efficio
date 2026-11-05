"""World layout of a rear transaxle composed from subsystem geometries.

Coordinate system (millimetres):

* ``x`` points forward, ``y`` along the axle (left to right), ``z`` up, with
  the ground plane at ``z = 0``.
* Every shaft is parallel to ``y``, so the whole power path is spur gears:
  crankshaft -> crank pinion -> compound idler -> ring gear on the
  differential carrier -> sun gears -> half-shafts -> wheels.

The engine and differential carry their own geometry
(:class:`EngineGeometry`, :class:`SpurDifferentialGeometry`); this class only
positions them, derives shaft centres from gear pitch radii, and checks the
clearances that only exist once they are put together.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple

from efficio.objects.powertrain.bearings import StandardBearing
from efficio.objects.powertrain.differential.geometry import (
    PlanetPose,
    SpurDifferentialGeometry,
)
from efficio.objects.powertrain.engine.geometry import EngineGeometry
from efficio.objects.powertrain.fits import M3_CLEARANCE_RADIUS_MM
from efficio.objects.powertrain.gearbox.features import PlateHole, PlateSeat
from efficio.objects.powertrain.gears.involute import (
    InvoluteGearGeometry,
    centre_distance,
    mesh_phase,
)
from efficio.objects.powertrain.planar import Point, Span, distance


class PlateSide(Enum):
    LEFT = "left"
    RIGHT = "right"


@dataclass
class DrivetrainLayout:
    # Reduction gear train (crank pinion -> idler gear | idler pinion -> ring).
    module: float = 1.5
    pressure_angle: float = 25.0
    backlash: float = 0.15
    crank_pinion_teeth: int = 12
    idler_gear_teeth: int = 36
    idler_pinion_teeth: int = 12
    stage_gear_width: float = 10.0
    idler_shaft_diameter: float = 5.0
    # Subsystems.
    engine: EngineGeometry = field(default_factory=EngineGeometry)
    differential: SpurDifferentialGeometry = field(
        default_factory=SpurDifferentialGeometry
    )
    # Gearbox frame.
    plate_thickness: float = 8.0
    standoff_radius: float = 3.5
    carrier_bearing: StandardBearing = StandardBearing.B6800
    idler_bearing: StandardBearing = StandardBearing.B625
    crank_support_bearing: StandardBearing = StandardBearing.B608
    # Flywheel.
    flywheel_diameter: float = 50.0
    flywheel_thickness: float = 8.0
    flywheel_holes: int = 4
    # Wheels and axles.
    wheel_diameter: float = 110.0
    rim_diameter: float = 80.0
    wheel_width: float = 30.0
    rim_spokes: int = 5
    tire_tread_blocks: int = 24
    hex_across_flats: float = 12.0
    hex_adapter_length: float = 8.0
    axle_bearing: StandardBearing = StandardBearing.B625
    pillow_block_thickness: float = 10.0
    pillow_centre_height: float = 15.0
    wheel_clearance: float = 5.0

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
            self.differential.ring_teeth / self.idler_pinion_teeth
        )

    @property
    def axle_diameter(self) -> float:
        return self.differential.axle_diameter

    # -------------------------------------------------------- planar centres
    @property
    def axle_height(self) -> float:
        return self.wheel_diameter / 2.0

    @property
    def axle_centre(self) -> Point:
        return (0.0, self.axle_height)

    @property
    def idler_centre(self) -> Point:
        if abs(self.differential.module - self.module) > 1e-9:
            raise ValueError("idler pinion and ring gear need the same module")
        return (
            centre_distance(
                self.module, self.idler_pinion_teeth, self.differential.ring_teeth
            ),
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

    def rotating_envelopes(self) -> List[Tuple[Point, float]]:
        """(centre, tip radius) of every gear between the plates."""
        return [
            (self.axle_centre, self.differential.ring_tip_radius),
            (self.idler_centre, self.gear(self.idler_gear_teeth).tip_radius),
            (self.crank_centre, self.gear(self.crank_pinion_teeth).tip_radius),
        ]

    def standoff_centres(self) -> List[Point]:
        r = self.standoff_radius
        (ax, az), ring_tip = self.rotating_envelopes()[0]
        (ix, iz), idler_tip = self.rotating_envelopes()[1]
        (cx, cz), pinion_tip = self.rotating_envelopes()[2]
        return [
            (ax - (ring_tip + r + 2.5), az),
            (ix, iz - (idler_tip + r + 2.0)),
            (ix, iz + (idler_tip + r + 2.0)),
            (cx + pinion_tip + r + 2.5, cz),
        ]

    def engine_flange_bolts(self) -> List[Point]:
        cx, cz = self.crank_centre
        return [(cx + x, cz + z) for x, z in self.engine.flange_bolt_offsets()]

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
    def stage_plane(self) -> Span:
        start = self.drum.end + 1.5
        return Span(start, start + self.stage_gear_width)

    @property
    def plate_right(self) -> Span:
        start = self.stage_plane.end + 1.0
        return Span(start, start + self.plate_thickness)

    @property
    def plate_gap(self) -> Span:
        return Span(self.plate_left.end, self.plate_right.start)

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
    def engine_origin_y(self) -> float:
        """World y of the engine-local origin (flange face on the plate)."""
        return self.plate_right.end

    @property
    def engine_block(self) -> Span:
        return Span(0.0, self.engine.block_length).shifted(self.engine_origin_y)

    def cylinder_y(self, index: int) -> float:
        return self.engine_origin_y + self.engine.cylinder_y(index)

    @property
    def crank_stub(self) -> Span:
        seat_floor = self.plate_left.end - self.crank_support_bearing.spec.width
        return Span(seat_floor, self.engine_origin_y + self.engine.output_journal_end)

    @property
    def flywheel(self) -> Span:
        start = self.engine_block.end + 2.0
        return Span(start, start + self.flywheel_thickness)

    @property
    def flywheel_stub(self) -> Span:
        return Span(
            self.engine_origin_y + self.engine.flywheel_journal_start,
            self.flywheel.end,
        )

    def centre_journals(self) -> List[Span]:
        return [j.shifted(self.engine_origin_y) for j in self.engine.centre_journals()]

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
            self.carrier_offset + self.differential.left_axle_end,
        )

    @property
    def right_half_shaft(self) -> Span:
        return Span(
            self.carrier_offset + self.differential.right_axle_end,
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
        pitch = 360.0 / self.crank_pinion_teeth
        idler = mesh_phase(
            self.crank_centre,
            crank_angle % pitch,
            self.crank_pinion_teeth,
            self.idler_centre,
            self.idler_gear_teeth,
        )
        # The compound idler is one part: its pinion shares the rotation.
        carrier = mesh_phase(
            self.idler_centre,
            idler,
            self.idler_pinion_teeth,
            self.axle_centre,
            self.differential.ring_teeth,
        )
        return {
            "crank_pinion": crank_angle,
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

        journal = self.engine.crank_journal_diameter
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
        ]
        holes = [
            PlateHole(local(s), M3_CLEARANCE_RADIUS_MM) for s in self.standoff_centres()
        ]
        if side is PlateSide.LEFT:
            seats.append(
                PlateSeat(
                    local(self.crank_centre),
                    self.crank_support_bearing.spec,
                    journal / 2.0 + 0.5,
                )
            )
        else:
            holes.append(
                PlateHole(
                    local(self.crank_centre), journal / 2.0 + 1.0, boss_margin=10.0
                )
            )
            holes += [
                PlateHole(local(b), M3_CLEARANCE_RADIUS_MM)
                for b in self.engine_flange_bolts()
            ]
        return seats, holes

    # ------------------------------------------------------------- validation
    def problems(self) -> List[str]:
        """Human-readable violations; empty when the layout is sound."""
        issues = list(self.engine.problems()) + list(self.differential.problems())
        idler = self.gear(self.idler_gear_teeth)
        pinion = self.gear(self.crank_pinion_teeth)
        idler_pinion = self.gear(self.idler_pinion_teeth)
        ring_tip = self.differential.ring_tip_radius
        journal = self.engine.crank_journal_diameter

        if pinion.root_radius < journal / 2.0 + 1.5:
            issues.append("crank pinion too small for the crank journal")
        if idler_pinion.root_radius < self.idler_shaft_diameter / 2.0 + 1.5:
            issues.append("idler pinion too small for its shaft")
        hub = self.differential.hub_diameter / 2
        if self.idler_centre[0] - idler.tip_radius - hub < 1.0:
            issues.append("idler gear hits differential carrier hub")
        if (
            self.crank_centre[0]
            - self.idler_centre[0]
            - idler_pinion.tip_radius
            - journal / 2
            < 1.0
        ):
            issues.append("idler pinion hits crank stub")
        if self.crank_centre[0] - ring_tip - journal / 2 < 1.0:
            issues.append("ring gear hits crank stub")
        for s in self.standoff_centres():
            for centre, radius in self.rotating_envelopes():
                if distance(s, centre) < radius + self.standoff_radius + 1.0:
                    issues.append(f"standoff at {s} intersects gear at {centre}")
        if self.axle_height - self.engine.block_half_width < 5.0:
            issues.append("engine block too close to ground")
        if self.axle_height - self.flywheel_diameter / 2.0 < 5.0:
            issues.append("flywheel too close to ground")
        if self.axle_height - ring_tip < 5.0:
            issues.append("ring gear too close to ground")
        if self.right_half_shaft.start - self.left_half_shaft.end < 1.0:
            issues.append("half-shaft ends collide inside the differential")
        if self.left_pillow_block.end > self.plate_left.start - 1.0:
            issues.append("left pillow block collides with gearbox")
        if self.right_pillow_block.start < self.carrier_right_hub.end + 1.0:
            issues.append("right pillow block collides with gearbox")
        if self.rim_diameter >= self.wheel_diameter - 10.0:
            issues.append("tyre too thin")
        return issues
