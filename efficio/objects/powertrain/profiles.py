"""CadQuery building blocks shared by every powertrain part.

Conventions: prisms extrude along local +Z; ``y_cylinder`` runs along +Y.
"""

import math
from typing import List, Sequence

import cadquery as cq

from efficio.objects.powertrain.bearings import BallBearing
from efficio.objects.powertrain.fits import CROSS_PIN_SLOT_CLEARANCE_MM
from efficio.objects.powertrain.planar import Point
from efficio.objects.shapes import Orientation, Shape, WorkplaneShape


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


def y_cylinder(
    radius: float, y0: float, y1: float, x: float = 0.0, z: float = 0.0
) -> cq.Workplane:
    """Cylinder whose axis is parallel to Y (rotating -90 about X maps Z to Y)."""
    return (
        cq.Workplane("XY")
        .circle(radius)
        .extrude(y1 - y0)
        .rotate((0, 0, 0), (1, 0, 0), -90)
        .translate((x, y0, z))
    )


def x_cylinder(
    radius: float, x0: float, x1: float, y: float = 0.0, z: float = 0.0
) -> cq.Workplane:
    """Cylinder whose axis is parallel to X (rotating +90 about Y maps Z to X)."""
    return (
        cq.Workplane("XY")
        .circle(radius)
        .extrude(x1 - x0)
        .rotate((0, 0, 0), (0, 1, 0), 90)
        .translate((x0, y, z))
    )


def box(
    x0: float, x1: float, y0: float, y1: float, z0: float, z1: float
) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
        .translate((x0, y0, z0))
    )


def hex_across_corners(across_flats: float) -> float:
    return across_flats / math.cos(math.radians(30))


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
    """Round or D-flat hole for a shaft of nominal ``diameter``."""
    if d_flat:
        return prism(d_profile(diameter, allowance), z0, z1)
    return cylinder(diameter / 2.0 + allowance, z0, z1)


def bearing_seat_cutter(
    bearing: BallBearing,
    thickness: float,
    through_radius: float,
    x: float = 0.0,
    y: float = 0.0,
) -> cq.Workplane:
    """Bearing pocket from the z = 0 face plus a through hole for the shaft.

    When the housing is thinner than the bearing the pocket goes straight
    through and the bearing must be retained some other way.
    """
    depth = min(bearing.width, thickness + 1.0)
    pocket = cylinder(bearing.seat_radius, -1.0, depth, x, y)
    return pocket.union(cylinder(through_radius, -1.0, thickness + 1.0, x, y))


def cross_pin_slot_cutter(
    pin_diameter: float, pin_length: float, face_z: float, toward_positive_z: bool
) -> cq.Workplane:
    """Slot across a bore, on the face at ``face_z``, that seats a cross pin
    driven through the shaft along local X."""
    width = pin_diameter + 2 * CROSS_PIN_SLOT_CLEARANCE_MM
    half = pin_length / 2 + 0.2
    if toward_positive_z:
        return box(-half, half, -width / 2, width / 2, face_z - 1.0, face_z + width)
    return box(-half, half, -width / 2, width / 2, face_z - width, face_z + 1.0)
