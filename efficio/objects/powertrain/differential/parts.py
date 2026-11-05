"""Solid parts of the spur differential.

Sun and planet gears are plain :class:`SpurGear` instances sized from the
geometry; the ring teeth on the carrier are a ``SpurGear`` blank too.
"""

import math
from typing import Optional

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.gears import MetricModule, PressureAngle
from efficio.objects.powertrain.differential.geometry import SpurDifferentialGeometry
from efficio.objects.powertrain.fits import (
    NUT_POCKET_CLEARANCE_MM,
    NUT_POCKET_DEPTH_CLEARANCE_MM,
    RUNNING_CLEARANCE_MM,
)
from efficio.objects.powertrain.gears.spur import SpurGear
from efficio.objects.powertrain.profiles import cylinder, hexagon, wrap
from efficio.objects.shapes import Shape


def _gear(
    geometry: SpurDifferentialGeometry,
    teeth: int,
    thickness: float,
    bore: float,
    d_flat: bool,
    hub_diameter: float = 0.0,
    hub_length: float = 0.0,
    cross_pin: bool = False,
) -> SpurGear:
    return SpurGear(
        MetricModule(geometry.module),
        teeth,
        Millimeter(thickness),
        Millimeter(bore),
        d_flat,
        PressureAngle(geometry.pressure_angle),
        hub_diameter=Millimeter(hub_diameter),
        hub_length=Millimeter(hub_length),
        backlash=Millimeter(geometry.backlash),
        cross_pin_diameter=Millimeter(
            geometry.axle_cross_pin_diameter if cross_pin else 0.0
        ),
        cross_pin_length=Millimeter(
            geometry.axle_cross_pin_length if cross_pin else 0.0
        ),
    )


def sun_gear(geometry: SpurDifferentialGeometry) -> SpurGear:
    """Output gear on the half-shaft; its hub is the thrust spacer.

    D-flat bore for steel axles, or a cross-pin slot on the outer (z = 0)
    face for round axles such as dowels.
    """
    return _gear(
        geometry,
        geometry.sun_teeth,
        geometry.sun_width,
        geometry.axle_diameter,
        not geometry.pinned_axles,
        hub_diameter=2 * geometry.sun_hub_radius,
        hub_length=geometry.sun_hub_length,
        cross_pin=geometry.pinned_axles,
    )


def planet_gear(geometry: SpurDifferentialGeometry) -> SpurGear:
    """Long planet running on the planet pin (a bolt shank, geometry.planet_bolt)."""
    return _gear(
        geometry,
        geometry.planet_teeth,
        geometry.planet_length,
        geometry.planet_pin_diameter,
        False,
    )


def ring_gear(geometry: SpurDifferentialGeometry, width: float) -> SpurGear:
    return _gear(geometry, geometry.ring_teeth, width, geometry.axle_diameter, False)


class SpurDifferentialCarrierHalf(EfficioObject):
    """Half of the carrier, carrying its share of the ring teeth.

    Local z = 0 is the split face, the end wall is at ``z = drum_width / 2``
    and the bearing hub projects beyond it by ``hub_length``.  Planet pin holes
    get a nut/head pocket on the outer face, so both halves are the same part
    apart from hub length.
    """

    def __init__(self, geometry: SpurDifferentialGeometry, hub_length: Measure):
        self.geometry = geometry
        self.hub_length = hub_length

    def shape(self) -> Optional[Shape]:
        g = self.geometry
        half = g.drum_width / 2.0
        hub_end = half + self.hub_length.value()

        body = ring_gear(g, half).blank()
        body = body.union(cylinder(g.hub_diameter / 2.0, half - 0.5, hub_end))
        body = body.cut(cylinder(g.cavity_radius, -1.0, half - g.end_wall))
        body = body.cut(
            cylinder(g.axle_diameter / 2.0 + RUNNING_CLEARANCE_MM, -1.0, hub_end + 1)
        )
        pin_hole = g.planet_pin_diameter / 2.0 + RUNNING_CLEARANCE_MM
        bolt = g.planet_bolt.spec
        pocket = bolt.pocket_across_corners(NUT_POCKET_CLEARANCE_MM)
        pocket_depth = bolt.pocket_depth(NUT_POCKET_DEPTH_CLEARANCE_MM)
        for _, angle in g.planet_carrier_angles():
            x = g.planet_orbit_radius * math.cos(math.radians(angle))
            y = g.planet_orbit_radius * math.sin(math.radians(angle))
            body = body.cut(cylinder(pin_hole, -1.0, half + 1.0, x, y))
            body = body.cut(
                hexagon(
                    pocket,
                    half - pocket_depth,
                    half + 1.0,
                    x,
                    y,
                )
            )
        return wrap(body)
