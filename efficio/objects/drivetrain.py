"""Gear train, gearbox and differential parts for a printable transaxle.

All rotating parts are modelled with their rotation axis on local +Z, starting
at ``z = 0``.  That keeps every gear, plate and disc a 2.5D extrusion that can
be FDM printed flat or profile-cut / etched from plate stock on a CNC router.
"""

import math
from enum import Enum
from typing import List, Optional, Sequence

import cadquery as cq

from efficio.measures import Measure
from efficio.objects.base import EfficioObject
from efficio.objects.drivetrain_layout import DrivetrainLayout
from efficio.objects.fits import (
    M3_CLEARANCE_RADIUS_MM,
    M3_NUT_ACROSS_CORNERS_MM,
    PRESS_CLEARANCE_MM,
    RUNNING_CLEARANCE_MM,
    SLIDING_CLEARANCE_MM,
)
from efficio.objects.gears import MetricModule, PressureAngle
from efficio.objects.involute import (
    InvoluteGearGeometry,
    Point,
    circle_points,
    convex_hull,
)
from efficio.objects.shapes import Orientation, Shape, WorkplaneShape

# --------------------------------------------------------------------- helpers


def wrap(workplane: cq.Workplane) -> Shape:
    """Expose a raw CadQuery workplane through the efficio Shape API."""
    shape = WorkplaneShape(Orientation.Front)
    shape._workplane = workplane
    return shape


def prism(points: Sequence[Point], z0: float, z1: float) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .polyline(list(points))
        .close()
        .extrude(z1 - z0)
        .translate((0, 0, z0))
    )


def cylinder(
    radius: float, z0: float, z1: float, x: float = 0.0, y: float = 0.0
) -> cq.Workplane:
    return cq.Workplane("XY").circle(radius).extrude(z1 - z0).translate((x, y, z0))


def hexagon(
    across_corners: float, z0: float, z1: float, x: float = 0.0, y: float = 0.0
) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .polygon(6, across_corners)
        .extrude(z1 - z0)
        .translate((x, y, z0))
    )


def d_flat_depth(diameter: float) -> float:
    """Depth of the drive flat ground on a D-profile shaft."""
    return 0.1 * diameter


def d_profile(diameter: float, allowance: float, samples: int = 40) -> List[Point]:
    """D-shaped section with the flat facing local +X."""
    radius = diameter / 2.0 + allowance
    flat = diameter / 2.0 - d_flat_depth(diameter) + allowance
    start = math.acos(flat / radius)
    span = 2 * math.pi - 2 * start
    return [
        (
            radius * math.cos(start + span * i / samples),
            radius * math.sin(start + span * i / samples),
        )
        for i in range(samples + 1)
    ]


def bore_cutter(
    diameter: float, d_flat: bool, z0: float, z1: float, allowance: float
) -> cq.Workplane:
    if d_flat:
        return prism(d_profile(diameter, allowance), z0, z1)
    return cylinder(diameter / 2.0 + allowance, z0, z1)


def gear_prism(geometry: InvoluteGearGeometry, z0: float, z1: float) -> cq.Workplane:
    return prism(geometry.outline(), z0, z1)


def hull_of_circles(circles: Sequence[tuple[Point, float]]) -> List[Point]:
    points: List[Point] = []
    for centre, radius in circles:
        points.extend(circle_points(centre, radius, 48))
    return convex_hull(points)


def _geometry(
    module: MetricModule, teeth: int, pressure_angle: PressureAngle
) -> InvoluteGearGeometry:
    return InvoluteGearGeometry(
        module=float(module.value),
        teeth=teeth,
        pressure_angle_degrees=float(pressure_angle.value),
    )


# ----------------------------------------------------------------------- gears


class SpurGear(EfficioObject):
    """Involute spur gear with a round (running) or D-flat (driving) bore."""

    def __init__(
        self,
        module: MetricModule,
        teeth: int,
        thickness: Measure,
        bore: Measure,
        d_flat: bool,
        pressure_angle: PressureAngle = PressureAngle.HIGH_TORQUE,
    ):
        self.module = module
        self.teeth = teeth
        self.thickness = thickness
        self.bore = bore
        self.d_flat = d_flat
        self.pressure_angle = pressure_angle

    def geometry(self) -> InvoluteGearGeometry:
        return _geometry(self.module, self.teeth, self.pressure_angle)

    def shape(self) -> Optional[Shape]:
        t = self.thickness.value()
        allowance = SLIDING_CLEARANCE_MM if self.d_flat else RUNNING_CLEARANCE_MM
        body = gear_prism(self.geometry(), 0.0, t).cut(
            bore_cutter(self.bore.value(), self.d_flat, -1.0, t + 1.0, allowance)
        )
        return wrap(body)


class CompoundSpurGear(EfficioObject):
    """Pinion (z from 0) and gear (stacked above) cut as one part."""

    def __init__(
        self,
        module: MetricModule,
        pinion_teeth: int,
        pinion_thickness: Measure,
        gear_teeth: int,
        gear_thickness: Measure,
        bore: Measure,
        pressure_angle: PressureAngle = PressureAngle.HIGH_TORQUE,
    ):
        self.module = module
        self.pinion_teeth = pinion_teeth
        self.pinion_thickness = pinion_thickness
        self.gear_teeth = gear_teeth
        self.gear_thickness = gear_thickness
        self.bore = bore
        self.pressure_angle = pressure_angle

    def shape(self) -> Optional[Shape]:
        tp = self.pinion_thickness.value()
        tg = self.gear_thickness.value()
        pinion = gear_prism(
            _geometry(self.module, self.pinion_teeth, self.pressure_angle), 0.0, tp
        )
        gear = gear_prism(
            _geometry(self.module, self.gear_teeth, self.pressure_angle), tp, tp + tg
        )
        body = pinion.union(gear).cut(
            bore_cutter(
                self.bore.value(), True, -1.0, tp + tg + 1.0, SLIDING_CLEARANCE_MM
            )
        )
        return wrap(body)


# ---------------------------------------------------------------- differential


class DifferentialCarrierHalf(EfficioObject):
    """One half of the spur differential carrier with its share of ring teeth.

    Local z = 0 is the split face; the end wall is at ``z = half_width`` and the
    bearing hub projects beyond it.  Both halves are geometrically identical
    apart from hub length, so the planet pin holes are mirror-symmetric.
    """

    def __init__(self, layout: DrivetrainLayout, hub_length: Measure):
        self.layout = layout
        self.hub_length = hub_length

    def shape(self) -> Optional[Shape]:
        layout = self.layout
        half_width = layout.drum.length / 2.0
        wall = layout.carrier_end_wall
        hub_end = half_width + self.hub_length.value()
        ring = layout.gear(layout.ring_teeth)

        body = gear_prism(ring, 0.0, half_width)
        body = body.union(
            cylinder(layout.carrier_hub_diameter / 2.0, half_width - 0.5, hub_end)
        )
        body = body.cut(cylinder(layout.carrier_cavity_radius, -1.0, half_width - wall))
        body = body.cut(
            cylinder(
                layout.axle_diameter / 2.0 + RUNNING_CLEARANCE_MM, -1.0, hub_end + 1.0
            )
        )

        nut_pocket = M3_NUT_ACROSS_CORNERS_MM + 0.3
        for _, angle in layout.planet_carrier_angles():
            x = layout.planet_orbit_radius * math.cos(math.radians(angle))
            y = layout.planet_orbit_radius * math.sin(math.radians(angle))
            body = body.cut(
                cylinder(M3_CLEARANCE_RADIUS_MM, -1.0, half_width + 1.0, x, y)
            )
            body = body.cut(
                hexagon(nut_pocket, half_width - 3.2, half_width + 1.0, x, y)
            )
        return wrap(body)


class DifferentialSun(EfficioObject):
    """Sun (output) gear on a D-flat half-shaft, with a thrust hub."""

    def __init__(self, layout: DrivetrainLayout):
        self.layout = layout

    def shape(self) -> Optional[Shape]:
        layout = self.layout
        width = layout.sun_width
        hub_end = width + layout.sun_hub_length
        body = gear_prism(layout.gear(layout.sun_teeth), 0.0, width)
        body = body.union(cylinder(layout.sun_hub_radius, width - 0.5, hub_end))
        body = body.cut(
            bore_cutter(
                layout.axle_diameter, True, -1.0, hub_end + 1.0, SLIDING_CLEARANCE_MM
            )
        )
        return wrap(body)


class DifferentialPlanet(EfficioObject):
    """Long planet gear running on an M3 bolt used as the planet pin."""

    def __init__(self, layout: DrivetrainLayout):
        self.layout = layout

    def shape(self) -> Optional[Shape]:
        layout = self.layout
        length = layout.planet_length
        body = gear_prism(layout.gear(layout.planet_teeth), 0.0, length).cut(
            cylinder(1.5 + RUNNING_CLEARANCE_MM, -1.0, length + 1.0)
        )
        return wrap(body)


# --------------------------------------------------------------- gearbox frame


class PlateSide(Enum):
    LEFT = "left"
    RIGHT = "right"


class GearboxPlate(EfficioObject):
    """2.5D side plate carrying all transaxle bearings.

    Local x/y map onto world x/z (mirrored in z for the right plate because it
    is placed facing +y).  Bearing seats are pocketed from the inner face
    (local z = 0) with a shoulder on the outer face.
    """

    def __init__(self, layout: DrivetrainLayout, side: PlateSide):
        self.layout = layout
        self.side = side

    def _local(self, point: Point) -> Point:
        if self.side is PlateSide.RIGHT:
            return (point[0], -point[1])
        return point

    def outline(self) -> List[Point]:
        layout = self.layout
        circles = [
            (self._local(layout.axle_centre), layout.carrier_bearing.seat_radius + 4.0),
            (self._local(layout.idler_centre), layout.idler_bearing.seat_radius + 4.0),
            (self._local(layout.crank_centre), layout.crank_bearing.seat_radius + 4.0),
        ]
        for standoff in layout.standoff_centres():
            circles.append((self._local(standoff), layout.standoff_radius + 4.5))
        if self.side is PlateSide.RIGHT:
            for bolt in layout.engine_flange_bolts():
                circles.append((self._local(bolt), M3_CLEARANCE_RADIUS_MM + 4.5))
        return hull_of_circles(circles)

    def shape(self) -> Optional[Shape]:
        layout = self.layout
        t = layout.plate_thickness
        plate = prism(self.outline(), 0.0, t)

        def seat(centre: Point, seat_radius: float, depth: float, hole: float) -> None:
            nonlocal plate
            x, y = self._local(centre)
            plate = plate.cut(cylinder(seat_radius, -1.0, depth, x, y))
            plate = plate.cut(cylinder(hole, -1.0, t + 1.0, x, y))

        seat(
            layout.axle_centre,
            layout.carrier_bearing.seat_radius,
            layout.carrier_bearing.width,
            layout.carrier_hub_diameter / 2.0 + 0.5,
        )
        seat(
            layout.idler_centre,
            layout.idler_bearing.seat_radius,
            layout.idler_bearing.width,
            layout.idler_shaft_diameter / 2.0 + 0.5,
        )
        if self.side is PlateSide.LEFT:
            seat(
                layout.crank_centre,
                layout.crank_bearing.seat_radius,
                layout.crank_bearing.width,
                layout.crank_journal_diameter / 2.0 + 0.5,
            )
        else:
            x, y = self._local(layout.crank_centre)
            plate = plate.cut(
                cylinder(layout.crank_journal_diameter / 2.0 + 1.0, -1.0, t + 1.0, x, y)
            )
            for bolt in layout.engine_flange_bolts():
                bx, by = self._local(bolt)
                plate = plate.cut(
                    cylinder(M3_CLEARANCE_RADIUS_MM, -1.0, t + 1.0, bx, by)
                )

        for standoff in layout.standoff_centres():
            sx, sy = self._local(standoff)
            plate = plate.cut(cylinder(M3_CLEARANCE_RADIUS_MM, -1.0, t + 1.0, sx, sy))
        return wrap(plate)


class Standoff(EfficioObject):
    """Tubular spacer between gearbox plates; an M3 rod clamps the stack."""

    def __init__(self, length: Measure, outer_diameter: Measure):
        self.length = length
        self.outer_diameter = outer_diameter

    def shape(self) -> Optional[Shape]:
        length = self.length.value()
        tube = cylinder(self.outer_diameter.value() / 2.0, 0.0, length).cut(
            cylinder(M3_CLEARANCE_RADIUS_MM, -1.0, length + 1.0)
        )
        return wrap(tube)


class Shaft(EfficioObject):
    """Round or D-flat shaft cut from ground rod stock."""

    def __init__(self, diameter: Measure, length: Measure, d_flat: bool):
        self.diameter = diameter
        self.length = length
        self.d_flat = d_flat

    def shape(self) -> Optional[Shape]:
        d = self.diameter.value()
        length = self.length.value()
        if self.d_flat:
            # Shafts are nominal size; the press allowance only keeps the model
            # from sharing faces with the bores it passes through.
            return wrap(prism(d_profile(d, -PRESS_CLEARANCE_MM), 0.0, length))
        return wrap(cylinder(d / 2.0 - PRESS_CLEARANCE_MM, 0.0, length))
