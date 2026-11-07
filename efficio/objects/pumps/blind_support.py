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


def beveled_cylinder(
    radius: float,
    z0: float,
    z1: float,
    bevel: float,
    bottom: bool,
    x: float = 0,
    y: float = 0,
) -> cq.Shape:
    """45-degree exposed-end rim; build before union to avoid cusp chamfer failures."""
    if bevel == 0:
        return cylinder(radius, z0, z1, x, y)
    low, high = (z0 + bevel, z1) if bottom else (z0, z1 - bevel)
    cone = cq.Solid.makeCone(
        radius - bevel if bottom else radius,
        radius if bottom else radius - bevel,
        bevel,
        cq.Vector(x, y, z0 if bottom else z1 - bevel),
    )
    return cylinder(radius, low, high, x, y).fuse(cone).clean()


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
        if d.exterior_offset:
            bottom = self.kind == "body"
            solid = (
                beveled_cylinder(g.radius + d.exterior_offset, z0, z1, d.bevel, bottom)
                .fuse(
                    beveled_cylinder(
                        g.radius + d.exterior_offset,
                        z0,
                        z1,
                        d.bevel,
                        bottom,
                        x=g.centres,
                    ),
                    *(
                        beveled_cylinder(
                            d.boss_radius, z0, z1, d.bevel, bottom, x=x, y=y
                        )
                        for x, y in d.bolt_points
                    ),
                )
                .clean()
            )
        else:
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


def measured_housing_interfaces(d: BlindSupportDimensions) -> dict[str, float]:
    """Exact BRep wire distances at selected critical sections, in mm.

    This is not a global minimum-wall search: ports/openings, 3D junction
    stresses, permeability, tolerances and surface defects need other checks.
    """
    parts: dict[str, cq.Shape] = {}
    for kind in ("body", "cover", "gasket"):
        result = BlindSupportPart(d, kind).shape()
        assert result is not None
        value = result.workplane().val()
        assert isinstance(value, cq.Shape)
        parts[kind] = value

    def outer(solid: cq.Shape, side: str) -> cq.Wire:
        faces = cq.Workplane("XY").newObject([solid]).faces(side).vals()
        wires = [f.outerWire() for f in faces if isinstance(f, cq.Face)]
        return max(wires, key=lambda w: w.BoundingBox().xlen)

    measured = {
        "gasket_outer_waist_vertical": outer(parts["body"], ">Z").distance(
            outer(parts["gasket"], ">Z")
        )
    }
    distances = []
    for kind, side, z in (
        ("body", "<Z", 0.0),
        ("cover", ">Z", d.pump.depth + d.pump.cover),
    ):
        rim = outer(parts[kind], side)
        for x, y in d.bolt_points:
            hole = cq.Wire.makeCircle(
                d.pump.bolt_radius, cq.Vector(x, y, z), cq.Vector(0, 0, 1)
            )
            distances.append(rim.distance(hole))
    measured["bolt_boss_ligament"] = min(distances)
    return measured
