"""Crown (face) gear solid for right-angle drives with a spur pinion."""

from typing import List, Optional

import cadquery as cq

from efficio.measures import Measure, Millimeter
from efficio.objects.gears.base import AbstractCogwheel
from efficio.objects.gears.face import FaceGearGeometry
from efficio.objects.gears.spur import DEFAULT_BACKLASH, bore_allowance
from efficio.objects.gears.standards import MetricModule, PressureAngle
from efficio.objects.profiles import bore_cutter, cylinder, wrap
from efficio.objects.shapes import Shape


class CrownGear(AbstractCogwheel):
    """Disc with face teeth on its +Z side, meshing a spur pinion at 90 deg.

    The body occupies ``0 <= z <= body_thickness``; teeth rise from the root
    plane at ``z = body_thickness``.  Tooth 0 and the D-flat face local +X.
    """

    def __init__(
        self,
        module: MetricModule,
        teeth: int,
        pinion_teeth: int,
        body_thickness: Measure,
        bore: Measure,
        d_flat: bool,
        pressure_angle: PressureAngle = PressureAngle.HIGH_TORQUE,
        backlash: Measure = DEFAULT_BACKLASH,
        addendum_coefficient: float = 0.8,
        body_rim: Measure = Millimeter(0.5),
    ):
        self.module = module
        self.teeth = teeth
        self.pinion_teeth = pinion_teeth
        self.body_thickness = body_thickness
        self.bore = bore
        self.d_flat = d_flat
        self.pressure_angle = pressure_angle
        self.backlash = backlash
        self.addendum_coefficient = addendum_coefficient
        self.body_rim = body_rim
        super().__init__(Millimeter(self.body_radius), teeth, body_thickness)

    def geometry(self) -> FaceGearGeometry:
        return FaceGearGeometry(
            module=float(self.module.value),
            teeth=self.teeth,
            pinion_teeth=self.pinion_teeth,
            pressure_angle_degrees=float(self.pressure_angle.value),
            backlash=self.backlash.value(),
            addendum_coefficient=self.addendum_coefficient,
        )

    @property
    def body_radius(self) -> float:
        return self.geometry().outer_radius + self.body_rim.value()

    @property
    def pitch_plane(self) -> float:
        """Local z of the nominal pitch plane (pinion axis sits one pinion
        pitch radius above it)."""
        return self.body_thickness.value() + self.geometry().dedendum

    @property
    def height(self) -> float:
        g = self.geometry()
        return self.body_thickness.value() + g.dedendum + g.addendum

    def tooth(self) -> cq.Solid:
        """Tooth 0, lofted through the conjugate rack sections."""
        z0 = self.pitch_plane
        wires: List[cq.Wire] = []
        for radius, points in self.geometry().sections():
            vectors = [cq.Vector(radius, s, z0 + h) for s, h in points]
            wires.append(cq.Wire.makePolygon(vectors, close=True))
        return cq.Solid.makeLoft(wires, True)

    def shape(self) -> Optional[Shape]:
        t = self.body_thickness.value()
        body = cylinder(self.body_radius, 0.0, t).val()
        assert isinstance(body, cq.Solid)
        tooth = self.tooth()
        teeth = [
            tooth.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 360.0 * i / self.teeth)
            for i in range(self.teeth)
        ]
        gear = cq.Workplane("XY").newObject([body.fuse(*teeth).clean()])
        gear = gear.cut(
            bore_cutter(
                self.bore.value(),
                self.d_flat,
                -1.0,
                self.height + 1.0,
                bore_allowance(self.d_flat),
            )
        )
        return wrap(gear)
