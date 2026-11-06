"""Involute spur gears built on :class:`InvoluteGearGeometry`.

``SpurGear`` is the general involute gear: module, tooth count, pressure
angle, backlash, bore (round, D-flat or cross-pinned) and hub are all
parameters. Specializations, such as the drivetrain's gears in
``efficio.objects.powertrain.gears``, fix the gear system and keep the rest.
"""

from typing import Optional

import cadquery as cq

from efficio.measures import Measure, Millimeter
from efficio.objects.base import EfficioObject
from efficio.objects.fits import (
    PINNED_BORE_CLEARANCE_MM,
    RUNNING_CLEARANCE_MM,
    SLIDING_CLEARANCE_MM,
)
from efficio.objects.gears.base import AbstractCogwheel
from efficio.objects.gears.involute import InvoluteGearGeometry
from efficio.objects.gears.standards import MetricModule, PressureAngle
from efficio.objects.profiles import (
    bore_cutter,
    cross_pin_slot_cutter,
    cylinder,
    prism,
    wrap,
)
from efficio.objects.shapes import Shape

DEFAULT_BACKLASH = Millimeter(0.15)
NO_HUB = Millimeter(0)


def bore_allowance(d_flat: bool, pinned: bool = False) -> float:
    """D-flat bores drive the gear so they fit closely; pinned round bores
    (e.g. on a dowel) are snug; plain round bores run free."""
    if d_flat:
        return SLIDING_CLEARANCE_MM
    return PINNED_BORE_CLEARANCE_MM if pinned else RUNNING_CLEARANCE_MM


class SpurGear(AbstractCogwheel):
    """Involute spur gear, optional plain hub, round or D-flat bore.

    Teeth occupy ``0 <= z <= thickness``; the hub (if any) continues to
    ``thickness + hub_length``.  Tooth 0 and the D-flat both face local +X.
    A non-zero ``cross_pin_diameter`` drives the gear from a round shaft
    instead: a slot along local X on the ``z = 0`` face seats a pin through
    the shaft.
    """

    def __init__(
        self,
        module: MetricModule,
        teeth: int,
        thickness: Measure,
        bore: Measure,
        d_flat: bool,
        pressure_angle: PressureAngle = PressureAngle.HIGH_TORQUE,
        hub_diameter: Measure = NO_HUB,
        hub_length: Measure = NO_HUB,
        backlash: Measure = DEFAULT_BACKLASH,
        cross_pin_diameter: Measure = NO_HUB,
        cross_pin_length: Measure = NO_HUB,
    ):
        if cross_pin_diameter.value() > 0 and d_flat:
            raise ValueError("choose either a D-flat or a cross-pin drive")
        self.module = module
        self.teeth = teeth
        self.thickness = thickness
        self.bore = bore
        self.d_flat = d_flat
        self.pressure_angle = pressure_angle
        self.hub_diameter = hub_diameter
        self.hub_length = hub_length
        self.backlash = backlash
        self.cross_pin_diameter = cross_pin_diameter
        self.cross_pin_length = cross_pin_length
        super().__init__(Millimeter(self.geometry().tip_radius), teeth, thickness)

    @property
    def pinned(self) -> bool:
        return self.cross_pin_diameter.value() > 0

    def geometry(self) -> InvoluteGearGeometry:
        return InvoluteGearGeometry(
            module=float(self.module.value),
            teeth=self.teeth,
            pressure_angle_degrees=float(self.pressure_angle.value),
            backlash=self.backlash.value(),
        )

    @property
    def length(self) -> float:
        return self.thickness.value() + max(self.hub_length.value(), 0.0)

    def has_hub(self) -> bool:
        return self.hub_diameter.value() > 0 and self.hub_length.value() > 0

    def blank(self, z0: float = 0.0) -> cq.Workplane:
        """Teeth and hub without the bore, starting at ``z0``."""
        t = self.thickness.value()
        body = prism(self.geometry().outline(), z0, z0 + t)
        if self.has_hub():
            body = body.union(
                cylinder(
                    self.hub_diameter.value() / 2,
                    z0 + t - 0.5,
                    z0 + t + self.hub_length.value(),
                )
            )
        return body

    def bore_cutter(self, z0: float, z1: float) -> cq.Workplane:
        allowance = bore_allowance(self.d_flat, self.pinned)
        cutter = bore_cutter(self.bore.value(), self.d_flat, z0, z1, allowance)
        if self.pinned:
            cutter = cutter.union(
                cross_pin_slot_cutter(
                    self.cross_pin_diameter.value(),
                    self.cross_pin_length.value(),
                    0.0,
                    True,
                )
            )
        return cutter

    def shape(self) -> Optional[Shape]:
        return wrap(self.blank().cut(self.bore_cutter(-1.0, self.length + 1.0)))


class CompoundSpurGear(EfficioObject):
    """Two spur gears on one D-flat bore: pinion from z = 0, gear above it."""

    def __init__(
        self,
        module: MetricModule,
        pinion_teeth: int,
        pinion_thickness: Measure,
        gear_teeth: int,
        gear_thickness: Measure,
        bore: Measure,
        pressure_angle: PressureAngle = PressureAngle.HIGH_TORQUE,
        backlash: Measure = DEFAULT_BACKLASH,
    ):
        self.pinion = SpurGear(
            module,
            pinion_teeth,
            pinion_thickness,
            bore,
            True,
            pressure_angle,
            backlash=backlash,
        )
        self.gear = SpurGear(
            module,
            gear_teeth,
            gear_thickness,
            bore,
            True,
            pressure_angle,
            backlash=backlash,
        )

    def shape(self) -> Optional[Shape]:
        offset = self.pinion.length
        total = offset + self.gear.length
        body = self.pinion.blank().union(self.gear.blank(offset))
        return wrap(body.cut(self.pinion.bore_cutter(-1.0, total + 1.0)))
