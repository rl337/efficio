"""Involute spur gears built on :class:`InvoluteGearGeometry`.

``SpurGear`` is the general involute gear: module, tooth count, pressure
angle, backlash, bore (round, D-flat or cross-pinned) and hub are all
parameters. Specializations, such as the drivetrain's gears in
``efficio.objects.powertrain.gears``, fix the gear system and keep the rest.
"""

import math
from typing import List, Optional, Tuple, Union

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
from efficio.objects.gears.markings import (
    GearArcMarking,
    GearFaceMarker,
    GearMarkingStyle,
    standard_involute_markings,
)
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
        module: Union[MetricModule, float],
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
        lightening_holes: int = 0,
        minimum_web: Measure = Millimeter(3.0),
        engrave_identity: bool = False,
        marking_style: GearMarkingStyle = GearMarkingStyle(),
        marking_clearance: Measure = Millimeter(0.2),
    ):
        if cross_pin_diameter.value() > 0 and d_flat:
            raise ValueError("choose either a D-flat or a cross-pin drive")
        if not math.isfinite(thickness.value()) or thickness.value() <= 0:
            raise ValueError("Gear thickness must be finite and positive")
        if not math.isfinite(bore.value()) or bore.value() < 0:
            raise ValueError("Bore must be finite and non-negative")
        if (
            isinstance(lightening_holes, bool)
            or not isinstance(lightening_holes, int)
            or (lightening_holes != 0 and lightening_holes < 3)
        ):
            raise ValueError("Choose zero or at least three lightening holes")
        if not math.isfinite(minimum_web.value()) or minimum_web.value() <= 0:
            raise ValueError("Minimum web must be finite and positive")
        if (
            not math.isfinite(marking_clearance.value())
            or marking_clearance.value() <= 0
        ):
            raise ValueError("Marking clearance must be finite and positive")
        self.lightening_holes = lightening_holes
        self.minimum_web = minimum_web
        self.engrave_identity = engrave_identity
        self.marking_style = marking_style
        self.marking_clearance = marking_clearance
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

    @classmethod
    def from_tip_radius(
        cls,
        radius: Measure,
        teeth: int,
        thickness: Measure,
        bore: Measure = NO_HUB,
        d_flat: bool = False,
        pressure_angle: PressureAngle = PressureAngle.MODERN,
        backlash: Measure = Millimeter(0.0),
        lightening_holes: int = 0,
        minimum_web: Measure = Millimeter(3.0),
        engrave_identity: bool = False,
        marking_style: GearMarkingStyle = GearMarkingStyle(),
        marking_clearance: Measure = Millimeter(0.2),
    ) -> "SpurGear":
        """Outside-radius reference construction using the same spur implementation.

        The reference convention is 20 degrees and zero backlash; ordinary
        construction and drivetrain specializations keep their existing defaults.
        """
        geometry = InvoluteGearGeometry.from_tip_radius(
            radius.value(), teeth, float(pressure_angle.value), backlash.value()
        )
        return SpurGear(
            geometry.module,
            teeth,
            thickness,
            bore,
            d_flat,
            pressure_angle,
            backlash=backlash,
            lightening_holes=lightening_holes,
            minimum_web=minimum_web,
            engrave_identity=engrave_identity,
            marking_style=marking_style,
            marking_clearance=marking_clearance,
        )

    @property
    def pinned(self) -> bool:
        return self.cross_pin_diameter.value() > 0

    def geometry(self) -> InvoluteGearGeometry:
        return InvoluteGearGeometry(
            module=float(
                self.module.value
                if isinstance(self.module, MetricModule)
                else self.module
            ),
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

    def _proposed_markings(self) -> List[GearArcMarking]:
        style = self.marking_style
        if self.thickness.value() <= style.depth:
            return []
        profile = self.geometry()
        marker = GearFaceMarker(self.thickness.value(), style)
        limit = profile.material_disc_radius() - self.marking_clearance.value()

        def markings_at(radius: float) -> List[GearArcMarking]:
            return standard_involute_markings(
                self.teeth,
                profile.module,
                float(self.pressure_angle.value),
                radius,
                style,
            )

        # Include dot overshoot and tangential stroke corners, not merely glyph
        # height. Choose the outermost safe ring from the actual cutter bounds.
        low, high = 1e-9, limit
        if (
            high <= low
            or max(marker.radial_bounds(m)[1] for m in markings_at(low)) > limit
        ):
            return []
        for _ in range(40):
            radius = (low + high) / 2
            if (
                max(marker.radial_bounds(m)[1] for m in markings_at(radius))
                <= limit - 1e-8
            ):
                low = radius
            else:
                high = radius
        return markings_at(low)

    def _central_material_radius(self) -> float:
        bore_radius = (
            self.bore.value() / 2 + bore_allowance(self.d_flat, self.pinned)
            if self.bore.value() > 0
            else 0.0
        )
        return max(
            bore_radius, self.hub_diameter.value() / 2 if self.has_hub() else 0.0
        )

    def lightening_hole_layout(self) -> List[Tuple[float, float, float]]:
        """Actual (x, y, radius) cutter envelopes, or none when too small.

        Preserve webs at the root, centre, between neighbouring holes and
        underneath the optional identity ring. Cross-pin gears opt out because
        their drive slots need their own load-bearing envelope.
        """
        if not self.lightening_holes or self.pinned:
            return []
        profile = self.geometry()
        web = self.minimum_web.value()
        hub = max(
            self._central_material_radius(),
            2 * profile.module,
            profile.root_radius * 0.24,
        )
        inner, outer = hub + web, profile.material_disc_radius() - web
        # Reserve the same identity ring with engraving on or off, so toggling
        # identification never silently changes the load-bearing hole layout.
        if self.thickness.value() > self.marking_style.depth:
            marker = GearFaceMarker(self.thickness.value(), self.marking_style)
            markings = self._proposed_markings()
            if markings:
                outer = min(
                    outer,
                    min(marker.radial_bounds(m)[0] for m in markings)
                    - self.marking_clearance.value(),
                )
        if outer <= inner:
            return []
        centre = (inner + outer) / 2
        radius = min(
            (outer - inner) / 2,
            centre * math.sin(math.pi / self.lightening_holes) - web / 2,
        )
        if radius < web / 2:
            return []
        return [
            (
                centre * math.cos(2 * math.pi * i / self.lightening_holes),
                centre * math.sin(2 * math.pi * i / self.lightening_holes),
                radius,
            )
            for i in range(self.lightening_holes)
        ]

    def identity_markings(self) -> List[GearArcMarking]:
        """Safe automatic markings, or none when the face cannot accommodate them."""
        if not self.engrave_identity or self.pinned:
            return []
        style = self.marking_style
        clearance = self.marking_clearance.value()
        if self.thickness.value() < style.depth + max(
            clearance, self.minimum_web.value()
        ):
            return []
        marker = GearFaceMarker(self.thickness.value(), style)
        inner_material = self._central_material_radius()
        for x, y, radius in self.lightening_hole_layout():
            inner_material = max(inner_material, math.hypot(x, y) + radius)
        markings = self._proposed_markings()
        for marking in markings:
            inner, outer = marker.radial_bounds(marking)
            if (
                inner < inner_material + clearance - 1e-8
                or outer > self.geometry().material_disc_radius() - clearance
            ):
                return []
            # Ensure neighbouring glyph envelopes cannot merge into one slot.
            if len(marking.text) > 1:
                step = math.radians(marking.span_degrees / (len(marking.text) - 1))
                if (
                    2 * inner * math.sin(step / 2)
                    < marking.height * 0.6 + style.stroke_width + clearance
                ):
                    return []
        return markings

    def shape(self) -> Optional[Shape]:
        body = self.blank()
        if self.bore.value() > 0 or self.pinned:
            body = body.cut(self.bore_cutter(-1.0, self.length + 1.0))
        for x, y, radius in self.lightening_hole_layout():
            body = body.cut(cylinder(radius, -1.0, self.length + 1.0, x, y))
        shape = wrap(body)
        markings = self.identity_markings()
        if markings:
            marker = GearFaceMarker(self.thickness.value(), self.marking_style)
            for marking in markings:
                shape = marker.cut_arc(shape, marking)
        return shape


class CompoundSpurGear(EfficioObject):
    """Two spur gears on one D-flat bore: pinion from z = 0, gear above it."""

    def __init__(
        self,
        module: Union[MetricModule, float],
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
