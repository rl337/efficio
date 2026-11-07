"""External-gear pump candidate, in millimetres, shafts parallel to local Z.

Open inlet is local -Y, outlet +Y for a clockwise driver viewed from +Z.
The idler is on +X. Liquid travels around the outside of each rotor. Positive
clearances intentionally permit leakage; no displacement/pressure rating follows
from these solids. Face seals, shaft seals and bearing materials are not selected.
"""

from typing import Optional

import cadquery as cq

from efficio.measures import Millimeter
from efficio.objects.assembly import Assembly, PartSpec
from efficio.objects.base import EfficioObject
from efficio.objects.fits import Process, cross_pin_offset
from efficio.objects.gears.spur import SpurGear
from efficio.objects.powertrain.shafts import Shaft
from efficio.objects.profiles import bore_cutter, cylinder, wrap, x_cylinder
from efficio.objects.pumps.geometry import GearPumpDimensions
from efficio.objects.shapes import Shape


class GearPumpGeometry(GearPumpDimensions):
    """CAD helpers over the independently testable pump dimensions."""

    def gear(self) -> SpurGear:
        return SpurGear(
            self.module,
            self.teeth,
            Millimeter(self.width),
            Millimeter(self.shaft_diameter),
            False,
            cross_pin_diameter=Millimeter(self.rotor_pin_diameter),
            cross_pin_length=Millimeter(self.rotor_pin_length),
            backlash=Millimeter(self.backlash),
        )

    def cavity(self) -> cq.Shape:
        left = cq.Solid.makeCylinder(
            self.radius, self.depth - self.base + 0.01, cq.Vector(0, 0, self.base)
        )
        right = cq.Solid.makeCylinder(
            self.radius,
            self.depth - self.base + 0.01,
            cq.Vector(self.centres, 0, self.base),
        )
        return left.fuse(right).clean()

    def port_void(self, sign: int) -> cq.Solid:
        """Side drilling reaches the inter-rotor pocket; no blind housing feed."""
        return cq.Solid.makeCylinder(
            self.port_radius,
            self.half_height + 1,
            cq.Vector(
                self.centres / 2,
                0,
                self.base + self.width / 2 + self.face_clearance - self.port_drop,
            ),
            cq.Vector(0, sign, 0),
        )


class PumpPart(EfficioObject):
    """Separable housing/cover or round-journal shaft with outboard D flats.

    Counterbores reserve shaft-seal space; they are not installed seals. Four
    through holes are bolt/clamp interfaces. Face gasket and fasteners are TBD.
    """

    def __init__(self, geometry: GearPumpGeometry, kind: str):
        if kind not in {
            "body",
            "cover",
            "driver_shaft",
            "idler_shaft",
            "collar",
            "pin",
        }:
            raise ValueError("unknown pump part")
        self.g, self.kind = geometry, kind

    def shape(self) -> Optional[Shape]:
        g = self.g
        if self.kind == "pin":
            z = g.base + g.face_clearance + cross_pin_offset(g.rotor_pin_diameter)
            return wrap(
                x_cylinder(
                    g.rotor_pin_diameter / 2,
                    -g.rotor_pin_length / 2,
                    g.rotor_pin_length / 2,
                    z=z,
                )
            )
        if self.kind == "collar":
            body = cylinder(g.collar_radius, 0, g.collar_thickness)
            body = body.cut(
                bore_cutter(g.shaft_diameter, True, -1, g.collar_thickness + 1, 0.1)
            )
            body = body.cut(
                cq.Solid.makeCylinder(
                    g.set_screw_radius,
                    g.collar_radius + 1,
                    cq.Vector(0, 0, g.collar_thickness / 2),
                    cq.Vector(1, 0, 0),
                )
            )
            return wrap(body)
        if self.kind.endswith("shaft"):
            end = (
                g.depth
                + g.cover
                + (
                    g.shaft_extension
                    if self.kind == "driver_shaft"
                    else g.idler_extension
                )
            )
            # Round journals/seal lands; D flats exist only outside the case.
            # Assemble rotors/pins on the shaft before lowering into the open
            # body; removable collars then fit both outboard shaft ends.
            land_start = -g.collar_gap / 2
            land_end = g.depth + g.cover + g.collar_gap / 2
            pin_z = g.base + g.face_clearance + cross_pin_offset(g.rotor_pin_diameter)
            shaft = Shaft(
                Millimeter(g.shaft_diameter),
                Millimeter(land_end - land_start),
                False,
                cross_holes=(pin_z - land_start,),
                cross_hole_diameter=Millimeter(g.rotor_pin_diameter),
            ).shape()
            rear = Shaft(
                Millimeter(g.shaft_diameter),
                Millimeter(g.rear_extension + land_start),
                True,
            ).shape()
            front = Shaft(
                Millimeter(g.shaft_diameter), Millimeter(end - land_end), True
            ).shape()
            if shaft is None or rear is None or front is None:
                raise ValueError("shaft has no geometry")
            body = shaft.workplane().translate((0, 0, land_start))
            body = body.union(rear.workplane().translate((0, 0, -g.rear_extension)))
            body = body.union(front.workplane().translate((0, 0, land_end)))
            return wrap(body)
        z0, z1 = (0.0, g.depth) if self.kind == "body" else (g.depth, g.depth + g.cover)
        body = (
            cq.Workplane("XY")
            .box(g.centres + 2 * g.half_height, 2 * g.half_height, z1 - z0)
            .translate((g.centres / 2, 0, (z0 + z1) / 2))
        )
        if self.kind == "body":
            body = (
                body.cut(cq.Workplane("XY").newObject([g.cavity()]))
                .cut(g.port_void(-1))
                .cut(g.port_void(1))
            )
        for x in (0.0, g.centres):
            body = body.cut(
                cylinder(
                    g.shaft_diameter / 2 + g.journal_clearance, z0 - 1, z1 + 1, x=x
                )
            )
            start = z0 if self.kind == "body" else z1 - g.seal_pocket_depth
            body = body.cut(
                cylinder(g.seal_pocket_radius, start, start + g.seal_pocket_depth, x=x)
            )
        for x, y in g.bolt_points:
            body = body.cut(cylinder(g.bolt_radius, z0 - 1, z1 + 1, x=x, y=y))
        return wrap(body)


def gear_pump_assembly(g: GearPumpGeometry, angle: float = 0.0) -> Assembly:
    """Driver angle is CCW about +Z; inlet -Y requires decreasing angle."""
    root = Assembly("External gear pump")
    for name, color in [
        ("body", (72, 124, 157)),
        ("cover", (125, 183, 207)),
        ("driver_shaft", (115, 118, 126)),
        ("idler_shaft", (115, 118, 126)),
    ]:
        child = root.add_subassembly(Assembly(name, color))
        obj = PumpPart(g, name)
        spec = PartSpec(
            "pump_" + name,
            obj,
            (Process.RESIN_CAST,),
            "material and finish unqualified",
            "Seal pockets and clamp holes only; seals, bearing liners and retention hardware not selected",
        )
        phase = angle if name == "driver_shaft" else g.idler_phase(angle)
        x = g.centres if name == "idler_shaft" else 0
        child.place_world(spec, spec.name, x, 0, 0)
        if name.endswith("shaft"):
            child.instances[0].solid = (
                spec.solid().rotate((0, 0, 0), (0, 0, 1), phase).translate((x, 0, 0))
            )
    gears = root.add_subassembly(Assembly("Rotors", (220, 164, 55)))
    gear = PartSpec(
        "pump_rotor",
        g.gear(),
        (Process.RESIN_CAST,),
        "finish-machined candidate",
        "Common involute geometry; pressure/flow untested",
    )
    for label, x, phase in [
        ("pump_driver", 0.0, angle),
        (
            "pump_idler",
            g.centres,
            g.idler_phase(angle),
        ),
    ]:
        gears.place_world(gear, label, x, 0, g.base + g.face_clearance)
        gears.instances[-1].solid = (
            gear.solid()
            .rotate((0, 0, 0), (0, 0, 1), phase)
            .translate((x, 0, g.base + g.face_clearance))
        )
    collars = root.add_subassembly(
        Assembly("Shaft retention interfaces", (90, 95, 105))
    )
    collar = PartSpec(
        "pump_shaft_collar",
        PumpPart(g, "collar"),
        (Process.CNC_PLATE,),
        "metal candidate",
        "D bore and radial set-screw pilot; screw/thread engagement unqualified",
    )
    for x, phase, label in [
        (0.0, angle, "pump_driver_collar"),
        (
            g.centres,
            g.idler_phase(angle),
            "pump_idler_collar",
        ),
    ]:
        collars.place_world(collar, label, x, 0, g.depth + g.cover + g.collar_gap)
        collars.instances[-1].solid = (
            collar.solid()
            .rotate((0, 0, 0), (0, 0, 1), phase)
            .translate((x, 0, g.depth + g.cover + g.collar_gap))
        )
    pin = PartSpec(
        "pump_rotor_pin",
        PumpPart(g, "pin"),
        (Process.ROD_STOCK,),
        "steel candidate",
        "Cross-pin transmits torque to shared gear face slot; insertion/retention requires physical trial",
    )
    for x, phase, side in [
        (0.0, angle, "driver"),
        (g.centres, g.idler_phase(angle), "idler"),
    ]:
        collars.place_world(
            collar,
            "pump_" + side + "_rear_collar",
            x,
            0,
            -g.collar_gap - g.collar_thickness,
        )
        collars.instances[-1].solid = (
            collar.solid()
            .rotate((0, 0, 0), (0, 0, 1), phase)
            .translate((x, 0, -g.collar_gap - g.collar_thickness))
        )
        gears.place_world(pin, "pump_" + side + "_pin", x, 0, 0)
        gears.instances[-1].solid = (
            pin.solid().rotate((0, 0, 0), (0, 0, 1), phase).translate((x, 0, 0))
        )
    return root
