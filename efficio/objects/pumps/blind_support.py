"""Rounded wet end with blind journals; seal seat is an interface, not a seal."""

from typing import Optional, cast

import cadquery as cq

from efficio.objects.base import EfficioObject
from efficio.objects.fits import cross_pin_offset
from efficio.objects.profiles import wrap, x_cylinder
from efficio.objects.pumps.external_gear import GearPumpGeometry
from efficio.objects.pumps.geometry import BlindSupportDimensions
from efficio.objects.shapes import Shape


def cylinder(
    radius: float, z0: float, z1: float, x: float = 0, y: float = 0
) -> cq.Shape:
    return cq.Solid.makeCylinder(radius, z1 - z0, cq.Vector(x, y, z0))


def capsule(centres: float, radius: float, z0: float, z1: float) -> cq.Shape:
    middle = cq.Solid.makeBox(centres, 2 * radius, z1 - z0, cq.Vector(0, -radius, z0))
    return (
        cylinder(radius, z0, z1)
        .fuse(cylinder(radius, z0, z1, x=centres), middle)
        .clean()
    )


class BlindSupportPart(EfficioObject):
    """Body, cover, compressed gasket envelope or pinned ground-rod shaft.

    Gasket geometry represents installed thickness. No elastomer deformation,
    seal lip, purchased bush or mechanical coupling is silently simulated.
    """

    def __init__(self, dimensions: BlindSupportDimensions, kind: str):
        if kind not in {"body", "cover", "gasket", "driver_shaft", "idler_shaft"}:
            raise ValueError("unknown blind-support part")
        self.d, self.kind = dimensions, kind

    def shape(self) -> Optional[Shape]:
        d = self.d
        g = GearPumpGeometry(**vars(d.pump))
        top = g.depth + g.cover
        if self.kind.endswith("shaft"):
            end = (
                top + g.shaft_extension
                if self.kind == "driver_shaft"
                else top - d.front_web - d.end_gap
            )
            solid = cylinder(d.shaft_radius, d.back_web + d.end_gap, end)
            pin_z = g.base + g.face_clearance + cross_pin_offset(g.rotor_pin_diameter)
            solid = solid.cut(
                cast(
                    cq.Shape,
                    x_cylinder(
                        g.rotor_pin_diameter / 2,
                        -g.shaft_diameter,
                        g.shaft_diameter,
                        z=pin_z,
                    ).val(),
                )
            )
            return wrap(cq.Workplane("XY").newObject([solid]))
        inside = g.radius + d.gasket_inset
        gasket = capsule(
            g.centres, inside + d.gasket_width, g.depth - d.gasket_depth, g.depth
        ).cut(
            capsule(g.centres, inside, g.depth - d.gasket_depth - 0.01, g.depth + 0.01)
        )
        if self.kind == "gasket":
            return wrap(cq.Workplane("XY").newObject([gasket]))
        z0, z1 = (0.0, g.depth) if self.kind == "body" else (g.depth, top)
        solid = capsule(g.centres, g.half_height, z0, z1)
        if self.kind == "body":
            solid = (
                solid.cut(g.cavity())
                .cut(g.port_void(-1))
                .cut(g.port_void(1))
                .cut(gasket)
            )
            for x in (0.0, g.centres):
                solid = solid.cut(
                    cylinder(
                        g.shaft_diameter / 2 + g.journal_clearance,
                        d.back_web,
                        g.base + 0.01,
                        x=x,
                    )
                )
        else:
            solid = solid.cut(
                cylinder(
                    g.shaft_diameter / 2 + g.journal_clearance, z0 - 0.01, z1 + 0.01
                )
            )
            solid = solid.cut(
                cylinder(
                    g.shaft_diameter / 2 + g.journal_clearance,
                    z0 - 0.01,
                    z1 - d.front_web,
                    x=g.centres,
                )
            )
            solid = solid.cut(cylinder(d.seal_radius, top - d.seal_depth, top + 0.01))
        for x, y in d.bolt_points:
            solid = solid.cut(cylinder(g.bolt_radius, z0 - 0.01, z1 + 0.01, x=x, y=y))
        return wrap(cq.Workplane("XY").newObject([solid.clean()]))
